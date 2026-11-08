# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import contextlib
import hashlib
import pickle
import sys
import threading
import traceback
from collections.abc import Iterable, Iterator
from pathlib import Path
from types import TracebackType
from typing import Any

import shiboken6

from editor.caos.receita_crash_robo import FalhaCapturadaRobo
from editor.core.diario import GerenciadorDiario
from editor.core.historico import GerenciadorHistorico
from editor.models.croqui_model import CroquiModel


def _extrair_frame_principal(tb: TracebackType | None) -> str:
    resumo = traceback.extract_tb(tb) if tb is not None else []
    if not resumo:
        return "frame_desconhecido:0"
    ultimo = resumo[-1]
    nome_arq = Path(ultimo.filename).as_posix()
    if "aresta_db/" in nome_arq:
        nome_arq = nome_arq.split("aresta_db/", 1)[1]
    return f"{nome_arq}:{ultimo.lineno}"


def calcular_hash_estado_modelo(model: CroquiModel) -> str:
    """Calcula um digest SHA-256 determinístico do Protobuf e buffers em memória do CroquiModel."""
    hasher = hashlib.sha256()
    proto = model.obter_croqui_readonly()
    hasher.update(proto.SerializeToString(deterministic=True))
    for k_img, v_img in sorted(model.obter_imagens_em_memoria().items()):
        hasher.update(k_img.encode("utf-8"))
        hasher.update(v_img)
    for k_anx, v_anx in sorted(model.obter_anexos_em_memoria().items()):
        hasher.update(k_anx.encode("utf-8"))
        hasher.update(v_anx)
    return hasher.hexdigest()


def _assinatura_comando_topo(historico: GerenciadorHistorico) -> str:
    pilha = historico.obter_pilha()
    idx = pilha.index()
    if idx <= 0:
        return ""
    cmd = pilha.command(idx - 1)
    if hasattr(cmd, "serializar"):
        return repr(cmd.serializar(anonimizado=True))
    return f"{type(cmd).__name__}:{cmd.text()}"


class OraculosCaos:
    """
    Reúne os 3 oráculos de falha do Robô Caótico:
    1. Exceções não tratadas (sys.excepthook / threading.excepthook) e objetos C++ deletados.
    2. Simetria determinística da pilha de Undo/Redo e obediência ao Princípio VIII.
    3. Integridade estrutural dos arquivos binários do GerenciadorDiario.
    """

    def __init__(self) -> None:
        self._falhas: list[FalhaCapturadaRobo] = []
        self._hashes_por_indice: dict[int, str] = {}
        self._ultimo_indice_pilha: int = 0
        self._ultima_assinatura_topo: str = ""

    def limpar_falhas(self) -> None:
        self._falhas.clear()

    def obter_primeira_falha(self) -> FalhaCapturadaRobo | None:
        return self._falhas[0] if self._falhas else None

    def registrar_excecao(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
        oraculo: str = "excecao_nao_tratada",
    ) -> FalhaCapturadaRobo:
        texto_tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        falha = FalhaCapturadaRobo(
            oraculo=oraculo,
            tipo_excecao=exc_type.__name__,
            mensagem=str(exc_value),
            frame_principal=_extrair_frame_principal(exc_tb),
            stacktrace=texto_tb,
        )
        self._falhas.append(falha)
        return falha

    @contextlib.contextmanager
    def monitorar_excecoes(self) -> Iterator[None]:
        """Intercepta sys.excepthook e threading.excepthook durante um passo do Robô Caótico."""
        hook_sys_orig = sys.excepthook
        hook_thread_orig = threading.excepthook

        def _hook_sys(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_tb: TracebackType | None,
        ) -> None:
            self.registrar_excecao(exc_type, exc_value, exc_tb)

        def _hook_thread(args: Any) -> None:
            self.registrar_excecao(args.exc_type, args.exc_value, args.exc_traceback)

        sys.excepthook = _hook_sys
        threading.excepthook = _hook_thread
        try:
            yield
        finally:
            sys.excepthook = hook_sys_orig
            threading.excepthook = hook_thread_orig

    def verificar_integridade_objetos_qt(
        self, objetos: Iterable[Any]
    ) -> FalhaCapturadaRobo | None:
        """Verifica via shiboken6.isValid se algum objeto Qt monitorado teve o C++ destruído."""
        for obj in objetos:
            if not shiboken6.isValid(obj):
                falha = FalhaCapturadaRobo(
                    oraculo="objeto_cpp_deletado",
                    tipo_excecao="RuntimeError",
                    mensagem=f"Internal C++ object ({type(obj).__name__}) already deleted.",
                    frame_principal="shiboken6.isValid",
                )
                self._falhas.append(falha)
                return falha
        return None

    def ressincronizar_estado_base(
        self, model: CroquiModel, historico: GerenciadorHistorico
    ) -> None:
        """Reinicia o mapa de hashes da QUndoStack (ex: ao abrir ou salvar/recarregar o croqui)."""
        pilha = historico.obter_pilha()
        idx_atual = pilha.index()
        hash_atual = calcular_hash_estado_modelo(model)
        self._hashes_por_indice = {idx_atual: hash_atual}
        self._ultimo_indice_pilha = idx_atual
        self._ultima_assinatura_topo = _assinatura_comando_topo(historico)

    def auditar_passo_historico(
        self,
        model: CroquiModel,
        historico: GerenciadorHistorico,
        foi_undo_ou_redo: bool = False,
    ) -> FalhaCapturadaRobo | None:
        """
        Audita a simetria determinística da QUndoStack e o cumprimento do Princípio VIII
        após a execução de um passo na JanelaPrincipal.
        """
        pilha = historico.obter_pilha()
        idx_atual = pilha.index()
        hash_atual = calcular_hash_estado_modelo(model)
        assinatura_topo = _assinatura_comando_topo(historico)

        if foi_undo_ou_redo and idx_atual in self._hashes_por_indice:
            hash_esperado = self._hashes_por_indice[idx_atual]
            if hash_atual != hash_esperado:
                cmd_ref = (
                    pilha.command(idx_atual)
                    if idx_atual < self._ultimo_indice_pilha
                    else pilha.command(max(0, idx_atual - 1))
                )
                nome_cmd = cmd_ref.text() if cmd_ref else "desconhecido"
                falha = FalhaCapturadaRobo(
                    oraculo="assimetria_undo_redo",
                    tipo_excecao="AssertionError",
                    mensagem=(
                        f"Quebra de simetria Undo/Redo no índice {idx_atual} "
                        f"(comando '{nome_cmd}'): hash {hash_atual[:12]} != {hash_esperado[:12]}"
                    ),
                    frame_principal=f"QUndoStack:{nome_cmd}",
                )
                self._falhas.append(falha)
                return falha
            self._ultimo_indice_pilha = idx_atual
            self._ultima_assinatura_topo = assinatura_topo
            return None

        if idx_atual > self._ultimo_indice_pilha:
            # Novo(s) comando(s) empilhado(s): invalida hashes futuros de redo e grava o novo topo
            for k in [k for k in self._hashes_por_indice if k > idx_atual]:
                self._hashes_por_indice.pop(k, None)
            self._hashes_por_indice[idx_atual] = hash_atual
            self._ultimo_indice_pilha = idx_atual
            self._ultima_assinatura_topo = assinatura_topo
            return None

        # idx_atual == _ultimo_indice_pilha (ou mudou sem flag de undo/redo)
        hash_anterior = self._hashes_por_indice.get(idx_atual)
        if hash_anterior is not None and hash_atual != hash_anterior:
            # Só é legítimo se houve coalescência (mergeWith) no comando do topo (idx_atual > 0)
            if idx_atual > 0 and assinatura_topo != self._ultima_assinatura_topo:
                self._hashes_por_indice[idx_atual] = hash_atual
                self._ultima_assinatura_topo = assinatura_topo
                return None

            falha = FalhaCapturadaRobo(
                oraculo="violacao_principio_viii",
                tipo_excecao="AssertionError",
                mensagem=(
                    f"Mutação direta no CroquiModel detectada no índice {idx_atual} "
                    "sem empilhamento ou coalescência na QUndoStack (Princípio VIII)."
                ),
                frame_principal="CroquiModel:QUndoStack",
            )
            self._falhas.append(falha)
            return falha

        self._hashes_por_indice[idx_atual] = hash_atual
        self._ultimo_indice_pilha = idx_atual
        self._ultima_assinatura_topo = assinatura_topo
        return None

    def verificar_integridade_diario(
        self, diario: GerenciadorDiario | None
    ) -> FalhaCapturadaRobo | None:
        """Verifica se diario_pendente.bin e diario_salvo.bin estão íntegros até o EOF."""
        if diario is None:
            return None

        for rotulo, caminho in (
            ("pendente", diario.caminho_pendente),
            ("salvo", diario.caminho_salvo),
        ):
            if not caminho.exists() or caminho.stat().st_size == 0:
                continue
            try:
                with open(caminho, "rb") as f:
                    while True:
                        try:
                            registro = pickle.load(f)
                        except EOFError:
                            break
                        if not isinstance(registro, dict) or not registro:
                            raise ValueError(
                                f"Registro de diário malformado em {rotulo}: {type(registro)}"
                            )
            except Exception as exc:
                falha = FalhaCapturadaRobo(
                    oraculo="corrupcao_diario",
                    tipo_excecao=type(exc).__name__,
                    mensagem=f"Corrupção no diário {rotulo} ({caminho.name}): {exc}",
                    frame_principal=f"GerenciadorDiario:{rotulo}",
                )
                self._falhas.append(falha)
                return falha

        return None
