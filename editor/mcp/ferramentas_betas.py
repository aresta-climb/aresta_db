# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Ferramentas MCP para coleta multi-fonte assíncrona em background (`aresta_coletar_betas`)
com persistência incremental por micro-lote e listagem paginada e enriquecida de
candidatos pendentes (`aresta_listar_betas_nao_scorados`).
"""

import threading
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from google.protobuf.json_format import MessageToDict

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.dialogo_coletar_betas import (
    MAX_WORKERS_COLETA_PARALELA,
    ExtratorBetaProtocolo,
    InfoEscaladaColeta,
    criar_extratores_padrao,
)
from coleta_de_betas.extratores.deduplicador import deduplicar_midias, normalizar_url
from editor.controllers.croqui_controller import CroquiController
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


@dataclass(frozen=True)
class MetadadosEscaladaBetas:
    """Metadados consolidados de uma escalada para coleta e avaliação de betas."""

    escalada_uid: str
    nome: str
    dificuldade: str
    modalidade: str
    setor_uid: str
    setor_nome: str
    pico_nome: str
    conquistadores: list[str]
    ja_possui_coleta: bool


def _extrair_dados_modalidade(esc: Any) -> tuple[str, str, str, list[str]]:
    campo = esc.WhichOneof("tipo") or ""
    sub = getattr(esc, campo)
    nome = str(getattr(sub, "nome", "") or "").strip()
    desc_dif = sub.DESCRIPTOR.fields_by_name.get("dificuldade")
    valor_dif = getattr(sub, "dificuldade", 0)
    nome_dif = (
        desc_dif.enum_type.values_by_number[valor_dif].name
        if desc_dif is not None and valor_dif in desc_dif.enum_type.values_by_number
        else ""
    )
    conquistadores = [str(c) for c in getattr(sub, "conquistadores", [])]
    return campo, nome, nome_dif, conquistadores


def _iterar_setores_do_croqui(croqui: Any) -> list[tuple[str, Any]]:
    pares: list[tuple[str, Any]] = []
    for pico in croqui.picos:
        nome_pico = str(pico.nome).strip()
        for sg in pico.setores_ou_grupos:
            if sg.HasField("setor"):
                pares.append((nome_pico, sg.setor.conteudo))
            elif sg.HasField("grupo"):
                for arq_setor in sg.grupo.conteudo.setores:
                    pares.append((nome_pico, arq_setor.conteudo))
    return pares


def _coletar_metadados_escaladas(
    croqui: Any,
    alvo_setor: str = "",
) -> dict[str, MetadadosEscaladaBetas]:
    filtro_setor = alvo_setor.strip()
    uids_com_curadoria: set[str] = set()
    for ent in croqui.curadoria_betas.conteudo.escaladas:
        if ent.betas_nao_scorados or ent.betas_nao_revisados or ent.betas_rejeitados:
            uids_com_curadoria.add(ent.escalada_uid)

    setores_filtrados: list[tuple[str, Any]] = []
    for nome_pico, setor in _iterar_setores_do_croqui(croqui):
        if filtro_setor and filtro_setor not in (setor.uid, setor.nome):
            continue
        setores_filtrados.append((nome_pico, setor))

    if filtro_setor and not setores_filtrados:
        raise ValueError(f"Setor '{filtro_setor}' não encontrado no croqui.")

    mapa: dict[str, MetadadosEscaladaBetas] = {}
    for nome_pico, setor in setores_filtrados:
        for esc in setor.escaladas:
            modalidade, nome, dificuldade, conquistadores = _extrair_dados_modalidade(esc)
            ja_coletada = bool(esc.betas) or (esc.uid in uids_com_curadoria)
            mapa[esc.uid] = MetadadosEscaladaBetas(
                escalada_uid=esc.uid,
                nome=nome,
                dificuldade=dificuldade,
                modalidade=modalidade,
                setor_uid=setor.uid,
                setor_nome=setor.nome,
                pico_nome=nome_pico,
                conquistadores=conquistadores,
                ja_possui_coleta=ja_coletada,
            )
    return mapa


def _coletar_uma_escalada(
    info: InfoEscaladaColeta,
    extratores: Sequence[Any],
) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
    listas_brutas: list[list[beta_pb2.CandidatoMidiaBeta]] = []
    rejeitados_brutos: list[beta_pb2.MidiaBeta] = []

    for extrator in extratores:
        res_cands, res_rejs = extrator.buscar_com_rejeitados(
            nome_escalada=info.nome_escalada,
            nome_setor=info.nome_setor,
            nome_pico=info.nome_pico,
        )
        listas_brutas.append(res_cands)
        rejeitados_brutos.extend(res_rejs)

    candidatos_dedup = deduplicar_midias(listas_brutas)
    rejeitados_norm: list[beta_pb2.MidiaBeta] = []
    for midia_rej in rejeitados_brutos:
        copia_rej = beta_pb2.MidiaBeta()
        copia_rej.CopyFrom(midia_rej)
        copia_rej.url = normalizar_url(midia_rej.url)
        rejeitados_norm.append(copia_rej)

    return candidatos_dedup, rejeitados_norm


class GerenciadorColetaBetasMcp:
    """
    Coordena a execução em background da coleta multi-fonte de betas via MCP,
    persistindo incrementalmente micro-lotes no `CroquiController` na thread principal do Qt.
    """

    def __init__(
        self,
        servidor: ServidorMCP,
        model: CroquiModel,
        controller: CroquiController,
        extratores: Sequence[ExtratorBetaProtocolo] | None = None,
    ) -> None:
        self.servidor = servidor
        self.model = model
        self.controller = controller
        self.extratores: list[ExtratorBetaProtocolo] = (
            list(extratores) if extratores is not None else criar_extratores_padrao()
        )
        self._lock = threading.Lock()
        self._evento_finalizado = threading.Event()
        self._evento_finalizado.set()
        self._thread_worker: threading.Thread | None = None
        self._status: str = "ocioso"
        self._cancelado: bool = False
        self._total_escaladas: int = 0
        self._escaladas_processadas: int = 0
        self._novos_candidatos: int = 0
        self._novos_rejeitados: int = 0
        self._ultima_escalada: str = ""
        self._fila_flushes: list[
            tuple[str, list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]
        ] = []

    def _aplicar_lote_na_thread_qt(
        self,
        lote: list[tuple[str, list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]],
    ) -> tuple[int, int]:
        adicionados = 0
        rejeitados = 0
        self.controller.iniciar_grupo_undo("Coletar Betas (MCP)")
        try:
            for escalada_uid, cands, rejs in lote:
                if cands:
                    adicionados += self.controller.adicionar_candidatos_nao_scorados(
                        escalada_uid, cands
                    )
                if rejs:
                    rejeitados += self.controller.adicionar_betas_rejeitados_lote(
                        escalada_uid, rejs
                    )
        finally:
            self.controller.finalizar_grupo_undo()

        with self._lock:
            self._novos_candidatos += adicionados
            self._novos_rejeitados += rejeitados
        return adicionados, rejeitados

    def _drenar_flushes(self) -> None:
        with self._lock:
            if not self._fila_flushes:
                return
            lote = list(self._fila_flushes)
            self._fila_flushes.clear()
        self.servidor.despachante.executar(self._aplicar_lote_na_thread_qt, lote)

    def _contar_pendentes_globais_na_thread_qt(self) -> tuple[int, int]:
        croqui = self.model.obter_croqui_readonly()
        escaladas_com_nao_scorados = 0
        total_candidatos = 0
        for ent in croqui.curadoria_betas.conteudo.escaladas:
            qtd = len(ent.betas_nao_scorados)
            if qtd > 0:
                escaladas_com_nao_scorados += 1
                total_candidatos += qtd
        return escaladas_com_nao_scorados, total_candidatos

    def _montar_resposta_status(self) -> dict[str, Any]:
        self._drenar_flushes()
        esc_pendentes, cands_pendentes = self.servidor.despachante.executar(
            self._contar_pendentes_globais_na_thread_qt
        )
        with self._lock:
            restantes = max(0, self._total_escaladas - self._escaladas_processadas)
            return {
                "status": self._status,
                "total_escaladas": self._total_escaladas,
                "escaladas_processadas": self._escaladas_processadas,
                "escaladas_restantes": restantes,
                "novos_candidatos_adicionados": self._novos_candidatos,
                "novos_rejeitados_adicionados": self._novos_rejeitados,
                "ultima_escalada": self._ultima_escalada,
                "total_escaladas_com_nao_scorados": esc_pendentes,
                "total_candidatos_nao_scorados": cands_pendentes,
            }

    def _aguardar_ate(self, aguardar_segundos: float) -> None:
        limite = max(0.0, min(20.0, float(aguardar_segundos)))
        prazo = time.monotonic() + limite
        while not self._evento_finalizado.is_set() and time.monotonic() < prazo:
            self._drenar_flushes()
            restante = max(0.0, min(0.05, prazo - time.monotonic()))
            self._evento_finalizado.wait(timeout=restante)
        self._drenar_flushes()

    def _executar_worker(
        self,
        escaladas: list[InfoEscaladaColeta],
        tamanho_lote_flush: int,
        max_workers: int,
    ) -> None:
        buffer_local: list[
            tuple[str, list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]
        ] = []
        try:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(escaladas))) as executor:
                futuros = {
                    executor.submit(_coletar_uma_escalada, info, self.extratores): info
                    for info in escaladas
                }
                for futuro in as_completed(futuros):
                    if self._cancelado:
                        for f_rest in futuros:
                            f_rest.cancel()
                        break
                    info = futuros[futuro]
                    cands, rejs = futuro.result()
                    if cands or rejs:
                        buffer_local.append((info.escalada_uid, cands, rejs))
                    with self._lock:
                        self._escaladas_processadas += 1
                        self._ultima_escalada = info.nome_escalada
                        if len(buffer_local) >= tamanho_lote_flush:
                            self._fila_flushes.extend(buffer_local)
                            buffer_local.clear()
        finally:
            with self._lock:
                if buffer_local:
                    self._fila_flushes.extend(buffer_local)
                self._status = "cancelado" if self._cancelado else "concluido"
                self._evento_finalizado.set()

    def _selecionar_escaladas_na_thread_qt(
        self,
        alvo_setor: str,
        escaladas_uids: list[str] | None,
        apenas_sem_coleta: bool,
    ) -> list[InfoEscaladaColeta]:
        croqui = self.model.obter_croqui_readonly()
        mapa = _coletar_metadados_escaladas(croqui, alvo_setor=alvo_setor)
        if escaladas_uids is not None:
            uids_pedidos = [str(u).strip() for u in escaladas_uids if str(u).strip()]
            inexistentes = [u for u in uids_pedidos if u not in mapa]
            if inexistentes:
                raise ValueError(f"Nenhuma escalada encontrada para os UIDs: {inexistentes}.")
            itens = [mapa[u] for u in uids_pedidos]
        else:
            itens = list(mapa.values())

        if apenas_sem_coleta:
            itens = [m for m in itens if not m.ja_possui_coleta]

        return [
            InfoEscaladaColeta(
                escalada_uid=m.escalada_uid,
                nome_escalada=m.nome,
                nome_setor=m.setor_nome,
                nome_pico=m.pico_nome,
            )
            for m in itens
        ]

    def manipular_coleta(self, args: dict[str, Any]) -> dict[str, Any]:
        acao = str(args.get("acao") or "iniciar").strip().lower()
        if acao not in ("iniciar", "status", "cancelar"):
            raise ValueError(f"Ação inválida '{acao}'. Use 'iniciar', 'status' ou 'cancelar'.")

        aguardar_s = float(args.get("aguardar_segundos", 15.0))

        if acao == "status":
            if not self._evento_finalizado.is_set() and aguardar_s > 0:
                self._aguardar_ate(aguardar_s)
            return self._montar_resposta_status()

        if acao == "cancelar":
            with self._lock:
                self._cancelado = True
            if self._thread_worker is not None and self._thread_worker.is_alive():
                self._aguardar_ate(2.0)
            return self._montar_resposta_status()

        # acao == "iniciar"
        with self._lock:
            em_andamento = (
                self._thread_worker is not None
                and self._thread_worker.is_alive()
                and not self._evento_finalizado.is_set()
            )
        if em_andamento:
            self._aguardar_ate(aguardar_s)
            return self._montar_resposta_status()

        alvo_setor = str(args.get("alvo_setor") or "").strip()
        uids_raw = args.get("escaladas_uids")
        escaladas_uids = list(uids_raw) if isinstance(uids_raw, list) else None
        apenas_sem_coleta = bool(args.get("apenas_sem_coleta", True))
        tamanho_lote_flush = max(1, int(args.get("tamanho_lote_flush", 10)))
        max_workers = max(1, int(args.get("max_workers", MAX_WORKERS_COLETA_PARALELA)))

        selecionadas = self.servidor.despachante.executar(
            self._selecionar_escaladas_na_thread_qt,
            alvo_setor,
            escaladas_uids,
            apenas_sem_coleta,
        )

        with self._lock:
            self._cancelado = False
            self._total_escaladas = len(selecionadas)
            self._escaladas_processadas = 0
            self._novos_candidatos = 0
            self._novos_rejeitados = 0
            self._ultima_escalada = ""
            self._fila_flushes.clear()
            if not selecionadas:
                self._status = "concluido"
                self._evento_finalizado.set()
            else:
                self._status = "em_andamento"
                self._evento_finalizado.clear()
                self._thread_worker = threading.Thread(
                    target=self._executar_worker,
                    args=(selecionadas, tamanho_lote_flush, max_workers),
                    daemon=True,
                )
                self._thread_worker.start()

        if selecionadas and aguardar_s > 0:
            self._aguardar_ate(aguardar_s)
        return self._montar_resposta_status()


def registrar_ferramentas_betas(
    servidor: ServidorMCP,
    model: CroquiModel,
    controller: CroquiController,
    extratores: Sequence[ExtratorBetaProtocolo] | None = None,
) -> GerenciadorColetaBetasMcp:
    """
    Registra `aresta_coletar_betas` e `aresta_listar_betas_nao_scorados` no `ServidorMCP`.
    """
    gerenciador = GerenciadorColetaBetasMcp(
        servidor=servidor,
        model=model,
        controller=controller,
        extratores=extratores,
    )

    def _listar_betas_nao_scorados(args: dict[str, Any]) -> dict[str, Any]:
        offset = int(args.get("offset", 0))
        limite = int(args.get("limite", 25))
        alvo_setor = str(args.get("alvo_setor") or "").strip()

        if offset < 0:
            raise ValueError("O parâmetro 'offset' deve ser maior ou igual a 0.")
        if limite < 1 or limite > 100:
            raise ValueError("O parâmetro 'limite' deve estar entre 1 e 100.")

        croqui = model.obter_croqui_readonly()
        mapa_meta = _coletar_metadados_escaladas(croqui, alvo_setor=alvo_setor)

        pendentes: list[tuple[int, Any, MetadadosEscaladaBetas]] = []
        total_candidatos_pendentes = 0
        for idx, ent in enumerate(croqui.curadoria_betas.conteudo.escaladas):
            qtd = len(ent.betas_nao_scorados)
            if qtd == 0:
                continue
            meta = mapa_meta.get(ent.escalada_uid)
            if meta is None:
                continue
            pendentes.append((idx, ent, meta))
            total_candidatos_pendentes += qtd

        fatia = pendentes[offset : offset + limite]
        escaladas_json: list[dict[str, Any]] = []
        for idx, ent, meta in fatia:
            nao_scorados_json = [
                MessageToDict(cand, preserving_proto_field_name=True)
                for cand in ent.betas_nao_scorados
            ]
            nao_revisados_json = [
                MessageToDict(cand, preserving_proto_field_name=True)
                for cand in ent.betas_nao_revisados
            ]
            escaladas_json.append(
                {
                    "indice_curadoria": idx,
                    "escalada_uid": meta.escalada_uid,
                    "nome": meta.nome,
                    "dificuldade": meta.dificuldade,
                    "modalidade": meta.modalidade,
                    "setor_uid": meta.setor_uid,
                    "setor_nome": meta.setor_nome,
                    "pico_nome": meta.pico_nome,
                    "conquistadores": meta.conquistadores,
                    "betas_nao_scorados": nao_scorados_json,
                    "betas_nao_revisados": nao_revisados_json,
                }
            )

        return {
            "total_escaladas_pendentes": len(pendentes),
            "total_candidatos_pendentes": total_candidatos_pendentes,
            "offset": offset,
            "limite": limite,
            "tem_mais": (offset + limite) < len(pendentes),
            "escaladas": escaladas_json,
        }

    servidor.registrar_ferramenta(
        nome="aresta_coletar_betas",
        descricao=(
            "Gerencia a coleta multi-fonte de candidatos a beta em background ('iniciar', "
            "'status' ou 'cancelar') sem bloquear a UI, persistindo micro-lotes incrementalmente "
            "em `curadoria_betas.conteudo` e retornando contadores de progresso."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "acao": {
                    "type": "string",
                    "enum": ["iniciar", "status", "cancelar"],
                    "description": "Ação a executar: 'iniciar' (padrão), 'status' ou 'cancelar'.",
                },
                "alvo_setor": {
                    "type": "string",
                    "description": "Opcional: UID ou nome do setor para restringir a coleta.",
                },
                "escaladas_uids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Opcional: Lista de UIDs específicos de escaladas a coletar.",
                },
                "apenas_sem_coleta": {
                    "type": "boolean",
                    "description": (
                        "Se True (padrão), coleta apenas escaladas que ainda não possuem "
                        "entradas em curadoria_betas nem betas publicados."
                    ),
                },
                "aguardar_segundos": {
                    "type": "number",
                    "description": (
                        "Segundos para aguardar conclusão via long-polling fora da UI thread "
                        "(0 a 20s, padrão 15s)."
                    ),
                },
                "tamanho_lote_flush": {
                    "type": "integer",
                    "description": (
                        "Quantidade de escaladas concluídas por micro-lote gravado no "
                        "CroquiController (padrão 10)."
                    ),
                },
            },
        },
        manipulador=gerenciador.manipular_coleta,
        requer_croqui=True,
        executar_na_thread_qt=False,
    )

    servidor.registrar_ferramenta(
        nome="aresta_listar_betas_nao_scorados",
        descricao=(
            "Lista de forma paginada e enxuta apenas as escaladas que possuem candidatos em "
            "`betas_nao_scorados`, já enriquecidas com nome, grau, modalidade, setor, pico e "
            "`indice_curadoria`, omitindo `betas_rejeitados` para suportar croquis de 1.000+ vias."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "offset": {
                    "type": "integer",
                    "description": "Índice inicial da paginação (padrão 0).",
                },
                "limite": {
                    "type": "integer",
                    "description": "Quantidade máxima de escaladas retornadas (1 a 100, padrão 25).",
                },
                "alvo_setor": {
                    "type": "string",
                    "description": "Opcional: UID ou nome do setor para filtrar.",
                },
            },
        },
        manipulador=_listar_betas_nao_scorados,
        requer_croqui=True,
    )

    return gerenciador
