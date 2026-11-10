# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Wizard / Diálogo de coleta de betas multi-fonte em background (QThread) com processamento
paralelo de escaladas via ThreadPoolExecutor, auditoria de descartes em betas_rejeitados
e ciclo de botões Iniciar Coleta -> Cancelar Coleta (com confirmação) -> Finalizar.
"""

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Protocol

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import ExtratorBlog
from coleta_de_betas.extratores.deduplicador import deduplicar_midias, normalizar_url

MAX_WORKERS_COLETA_PARALELA = 4


class ExtratorBetaProtocolo(Protocol):
    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
    ) -> list[beta_pb2.CandidatoMidiaBeta]: ...


@dataclass(frozen=True)
class InfoEscaladaColeta:
    escalada_uid: str
    nome_escalada: str
    nome_setor: str
    nome_pico: str


def _obter_nome_escalada(esc: Any) -> str:
    for campo in (
        "via_esportiva",
        "via_movel",
        "boulder",
        "via_multiplas_enfiadas",
        "highline",
    ):
        if hasattr(esc, "HasField") and esc.HasField(campo):
            sub = getattr(esc, campo)
            nome = str(getattr(sub, "nome", "") or "").strip()
            if nome:
                return nome
    return ""


def extrair_escaladas_do_croqui(croqui: Any) -> list[InfoEscaladaColeta]:
    """Percorre todos os picos, setores e grupos do croqui e extrai os metadados de cada escalada."""
    resultado: list[InfoEscaladaColeta] = []
    for pico in getattr(croqui, "picos", []):
        nome_pico = str(getattr(pico, "nome", "") or "").strip()
        for sg in getattr(pico, "setores_ou_grupos", []):
            if hasattr(sg, "HasField") and sg.HasField("setor"):
                setor = sg.setor.conteudo
                nome_setor = str(getattr(setor, "nome", "") or "").strip()
                for esc in getattr(setor, "escaladas", []):
                    uid = str(getattr(esc, "uid", "") or "").strip()
                    nome_esc = _obter_nome_escalada(esc)
                    if uid and nome_esc:
                        resultado.append(
                            InfoEscaladaColeta(
                                escalada_uid=uid,
                                nome_escalada=nome_esc,
                                nome_setor=nome_setor,
                                nome_pico=nome_pico,
                            )
                        )
            elif hasattr(sg, "HasField") and sg.HasField("grupo"):
                grupo = sg.grupo.conteudo
                for arq_setor in getattr(grupo, "setores", []):
                    setor = arq_setor.conteudo
                    nome_setor = str(getattr(setor, "nome", "") or "").strip()
                    for esc in getattr(setor, "escaladas", []):
                        uid = str(getattr(esc, "uid", "") or "").strip()
                        nome_esc = _obter_nome_escalada(esc)
                        if uid and nome_esc:
                            resultado.append(
                                InfoEscaladaColeta(
                                    escalada_uid=uid,
                                    nome_escalada=nome_esc,
                                    nome_setor=nome_setor,
                                    nome_pico=nome_pico,
                                )
                            )
    return resultado


def criar_extratores_padrao() -> list[ExtratorBetaProtocolo]:
    """
    Cria a lista padrão com o extrator web unificado (ddgs), que executa as 5 queries
    identificadas por escalada e classifica os resultados nas 8 categorias de FonteMidia.Enum.
    """
    return [ExtratorBlog()]


class WorkerColetaBetas(QThread):
    """
    Worker em background (QThread) que executa os extratores de rede e deduplicação
    em paralelo (ThreadPoolExecutor) para as escaladas selecionadas sem bloquear a GUI.
    """

    progresso_alterado = Signal(int, int, str)
    concluido = Signal(object, bool)

    def __init__(
        self,
        escaladas: Sequence[InfoEscaladaColeta],
        extratores: Sequence[ExtratorBetaProtocolo],
        max_workers: int = MAX_WORKERS_COLETA_PARALELA,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.escaladas = list(escaladas)
        self.extratores = list(extratores)
        self.max_workers = max(1, int(max_workers))
        self._cancelado = False
        self.rejeitados_por_uid: dict[str, list[beta_pb2.MidiaBeta]] = {}

    def solicitar_cancelamento(self) -> None:
        """Sinaliza cancelamento cooperativo imediato para interromper o loop de busca."""
        self._cancelado = True

    def foi_cancelado(self) -> bool:
        """Retorna True se o cancelamento cooperativo foi solicitado."""
        return self._cancelado

    def _coletar_escalada(
        self, info: InfoEscaladaColeta
    ) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
        if self._cancelado:
            return [], []

        listas_brutas: list[list[beta_pb2.CandidatoMidiaBeta]] = []
        rejeitados_brutos: list[beta_pb2.MidiaBeta] = []

        for extrator in self.extratores:
            if self._cancelado:
                break
            try:
                if hasattr(extrator, "buscar_com_rejeitados"):
                    res_cands, res_rejs = extrator.buscar_com_rejeitados(
                        nome_escalada=info.nome_escalada,
                        nome_setor=info.nome_setor,
                        nome_pico=info.nome_pico,
                    )
                    listas_brutas.append(res_cands)
                    rejeitados_brutos.extend(res_rejs)
                else:
                    res_cands = extrator.buscar(
                        nome_escalada=info.nome_escalada,
                        nome_setor=info.nome_setor,
                        nome_pico=info.nome_pico,
                    )
                    listas_brutas.append(res_cands)
            except Exception:
                continue

        candidatos_dedup = deduplicar_midias(listas_brutas)
        urls_aprovadas = {normalizar_url(c.midia.url) for c in candidatos_dedup if c.midia.url}
        rejeitados_dedup: list[beta_pb2.MidiaBeta] = []
        urls_rej_vistas: set[str] = set()
        for midia_rej in rejeitados_brutos:
            url_norm = normalizar_url(midia_rej.url)
            if not url_norm or url_norm in urls_aprovadas or url_norm in urls_rej_vistas:
                continue
            urls_rej_vistas.add(url_norm)
            copia_rej = beta_pb2.MidiaBeta()
            copia_rej.CopyFrom(midia_rej)
            copia_rej.url = url_norm
            rejeitados_dedup.append(copia_rej)

        return candidatos_dedup, rejeitados_dedup

    def run(self) -> None:
        """Executa a coleta paralela e deduplicação em memória emitindo sinais para a thread principal."""
        self.rejeitados_por_uid.clear()
        total = len(self.escaladas)
        if total == 0 or self._cancelado:
            self.concluido.emit([], self._cancelado)
            return

        ordem_uid = {info.escalada_uid: pos for pos, info in enumerate(self.escaladas)}
        resultados_coletados: list[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]] = []

        if self.max_workers == 1 or total == 1:
            for idx, info in enumerate(self.escaladas, start=1):
                if self._cancelado:
                    break
                cands, rejs = self._coletar_escalada(info)
                if cands:
                    resultados_coletados.append((info.escalada_uid, cands))
                if rejs:
                    self.rejeitados_por_uid[info.escalada_uid] = rejs
                self.progresso_alterado.emit(idx, total, info.nome_escalada)
                if self._cancelado:
                    break
        else:
            concluidas = 0
            with ThreadPoolExecutor(max_workers=min(self.max_workers, total)) as executor:
                futuros = {
                    executor.submit(self._coletar_escalada, info): info for info in self.escaladas
                }
                for futuro in as_completed(futuros):
                    if self._cancelado:
                        for f_rest in futuros:
                            f_rest.cancel()
                        break
                    info = futuros[futuro]
                    cands, rejs = futuro.result()
                    if cands:
                        resultados_coletados.append((info.escalada_uid, cands))
                    if rejs:
                        self.rejeitados_por_uid[info.escalada_uid] = rejs
                    concluidas += 1
                    self.progresso_alterado.emit(concluidas, total, info.nome_escalada)
                    if self._cancelado:
                        for f_rest in futuros:
                            f_rest.cancel()
                        break

        resultados_coletados.sort(key=lambda par: ordem_uid.get(par[0], 0))
        self.concluido.emit(resultados_coletados, self._cancelado)


class DialogoColetarBetas(QDialog):
    """
    Wizard modal para selecionar escaladas do croqui, executar a busca multi-fonte
    em background via WorkerColetaBetas(QThread) com paralelismo e barra de progresso,
    e injetar os novos candidatos em betas_nao_scorados e auto-filtrados em betas_rejeitados
    via CroquiController.
    """

    def __init__(
        self,
        model: Any,
        controller: Any,
        extratores: Sequence[ExtratorBetaProtocolo] | None = None,
        confirmador_cancelamento: Callable[[], bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.controller = controller
        self.extratores: list[ExtratorBetaProtocolo] = (
            list(extratores) if extratores is not None else criar_extratores_padrao()
        )
        self._confirmador_cancelamento = confirmador_cancelamento
        self.cancelado: bool = False
        self._estado_botoes: str = "pronto"
        self.worker_ativo: WorkerColetaBetas | None = None
        self.checkboxes_por_uid: dict[str, QCheckBox] = {}

        self.setWindowTitle("Coletar Betas para Escaladas")
        self.setMinimumSize(520, 440)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl_intro = QLabel(
            "Selecione as escaladas para buscar candidatos de beta (Instagram, YouTube, TikTok, Facebook e Blogs).\n"
            "URLs já aprovadas, pendentes ou rejeitadas serão ignoradas automaticamente."
        )
        lbl_intro.setWordWrap(True)
        layout.addWidget(lbl_intro)

        botoes_sel = QHBoxLayout()
        self.btn_marcar_todas = QPushButton("Marcar Todas")
        self.btn_desmarcar_todas = QPushButton("Desmarcar Todas")
        self.btn_marcar_todas.clicked.connect(lambda: self._definir_marcacao_todas(True))
        self.btn_desmarcar_todas.clicked.connect(lambda: self._definir_marcacao_todas(False))
        botoes_sel.addWidget(self.btn_marcar_todas)
        botoes_sel.addWidget(self.btn_desmarcar_todas)
        botoes_sel.addStretch()
        layout.addLayout(botoes_sel)

        self.scroll_escaladas = QScrollArea()
        self.scroll_escaladas.setWidgetResizable(True)
        container_esc = QWidget()
        self.layout_escaladas = QVBoxLayout(container_esc)
        self.layout_escaladas.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_escaladas.setWidget(container_esc)
        layout.addWidget(self.scroll_escaladas, stretch=1)

        croqui_ro = self.model.obter_croqui_readonly()
        self.escaladas_disponiveis = extrair_escaladas_do_croqui(croqui_ro)
        for info in self.escaladas_disponiveis:
            rotulo = f"{info.nome_escalada} ({info.nome_setor})"
            cb = QCheckBox(rotulo)
            cb.setChecked(True)
            self.checkboxes_por_uid[info.escalada_uid] = cb
            self.layout_escaladas.addWidget(cb)

        self.label_progresso = QLabel("Pronto para iniciar a coleta.")
        layout.addWidget(self.label_progresso)

        self.barra_progresso = QProgressBar()
        self.barra_progresso.setMinimum(0)
        self.barra_progresso.setMaximum(max(1, len(self.escaladas_disponiveis)))
        self.barra_progresso.setValue(0)
        layout.addWidget(self.barra_progresso)

        botoes_rodape = QHBoxLayout()
        botoes_rodape.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self._ao_clicar_cancelar)
        self.btn_iniciar = QPushButton("Iniciar Coleta")
        self.btn_iniciar.setDefault(True)
        self.btn_iniciar.clicked.connect(self.iniciar_coleta_assincrona)
        self.btn_finalizar = QPushButton("Finalizar")
        self.btn_finalizar.setVisible(False)
        self.btn_finalizar.clicked.connect(self.accept)
        botoes_rodape.addWidget(self.btn_cancelar)
        botoes_rodape.addWidget(self.btn_iniciar)
        botoes_rodape.addWidget(self.btn_finalizar)
        layout.addLayout(botoes_rodape)

        self._definir_estado_botoes("pronto")

    def _definir_estado_botoes(self, estado: str) -> None:
        self._estado_botoes = estado
        if estado == "pronto":
            self.btn_iniciar.setVisible(True)
            self.btn_iniciar.setEnabled(True)
            self.btn_cancelar.setVisible(True)
            self.btn_cancelar.setText("Cancelar")
            self.btn_finalizar.setVisible(False)
            self._definir_controles_selecao_habilitados(True)
        elif estado == "coletando":
            self.btn_iniciar.setVisible(False)
            self.btn_cancelar.setVisible(True)
            self.btn_cancelar.setText("Cancelar Coleta")
            self.btn_finalizar.setVisible(False)
            self._definir_controles_selecao_habilitados(False)
        elif estado == "concluido":
            self.btn_iniciar.setVisible(False)
            self.btn_cancelar.setVisible(False)
            self.btn_finalizar.setVisible(True)
            self.btn_finalizar.setDefault(True)
            self._definir_controles_selecao_habilitados(False)

    def _definir_marcacao_todas(self, marcado: bool) -> None:
        for cb in self.checkboxes_por_uid.values():
            cb.setChecked(marcado)

    def _definir_controles_selecao_habilitados(self, habilitado: bool) -> None:
        self.btn_marcar_todas.setEnabled(habilitado)
        self.btn_desmarcar_todas.setEnabled(habilitado)
        for cb in self.checkboxes_por_uid.values():
            cb.setEnabled(habilitado)

    def _confirmar_cancelamento_coleta(self) -> bool:
        if self._confirmador_cancelamento is not None:
            return bool(self._confirmador_cancelamento())
        resposta = QMessageBox.question(
            self,
            "Cancelar Coleta",
            "Deseja realmente interromper a coleta em andamento?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return resposta == QMessageBox.StandardButton.Yes

    def solicitar_cancelamento(self) -> None:
        self.cancelado = True
        if self.worker_ativo is not None:
            self.worker_ativo.solicitar_cancelamento()
        self.label_progresso.setText("Coleta cancelada pelo usuário.")

    def _ao_clicar_cancelar(self) -> None:
        em_andamento = self._estado_botoes == "coletando" or (
            self.worker_ativo is not None and self.worker_ativo.isRunning()
        )
        if em_andamento and not self._confirmar_cancelamento_coleta():
            return
        self.solicitar_cancelamento()
        if self.worker_ativo is not None and self.worker_ativo.isRunning():
            self.worker_ativo.wait(1500)
        self.reject()

    def _obter_escaladas_selecionadas(self) -> list[InfoEscaladaColeta]:
        return [
            info
            for info in self.escaladas_disponiveis
            if self.checkboxes_por_uid[info.escalada_uid].isChecked()
        ]

    def _aplicar_lote_coletado(
        self,
        resultados_por_uid: Sequence[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]],
        rejeitados_por_uid: dict[str, list[beta_pb2.MidiaBeta]] | None = None,
    ) -> tuple[int, int]:
        rejeitados_map = rejeitados_por_uid or {}
        if not resultados_por_uid and not rejeitados_map:
            return 0, 0
        total_adicionados = 0
        total_rejeitados = 0
        self.controller.iniciar_grupo_undo("Coletar Betas")
        try:
            for escalada_uid, candidatos_dedup in resultados_por_uid:
                if candidatos_dedup:
                    total_adicionados += self.controller.adicionar_candidatos_nao_scorados(
                        escalada_uid, candidatos_dedup
                    )
            for escalada_uid, midias_rej in rejeitados_map.items():
                if midias_rej and hasattr(self.controller, "adicionar_betas_rejeitados_lote"):
                    total_rejeitados += self.controller.adicionar_betas_rejeitados_lote(
                        escalada_uid, midias_rej
                    )
        finally:
            self.controller.finalizar_grupo_undo()
        return total_adicionados, total_rejeitados

    def iniciar_coleta_assincrona(self) -> None:
        """Dispara a coleta em uma QThread de background mantendo a interface responsiva."""
        if self.worker_ativo is not None and self.worker_ativo.isRunning():
            return
        selecionadas = self._obter_escaladas_selecionadas()
        if not selecionadas or self.cancelado:
            return

        self.barra_progresso.setMaximum(len(selecionadas))
        self.barra_progresso.setValue(0)
        self._definir_estado_botoes("coletando")

        worker = WorkerColetaBetas(
            escaladas=selecionadas,
            extratores=self.extratores,
            parent=self,
        )
        self.worker_ativo = worker
        worker.progresso_alterado.connect(self._ao_progresso_worker)
        worker.concluido.connect(self._ao_concluir_worker)
        worker.start()

    def _ao_progresso_worker(self, idx: int, total: int, nome_escalada: str) -> None:
        self.label_progresso.setText(f"Coletando ({idx}/{total}): {nome_escalada}...")
        self.barra_progresso.setValue(idx)

    def _ao_concluir_worker(
        self,
        resultados_por_uid: list[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]],
        foi_cancelado: bool,
    ) -> None:
        rejeitados_map = (
            dict(self.worker_ativo.rejeitados_por_uid) if self.worker_ativo is not None else {}
        )
        total_adicionados, total_rejeitados = self._aplicar_lote_coletado(
            resultados_por_uid, rejeitados_map
        )
        if not foi_cancelado and not self.cancelado:
            self.barra_progresso.setValue(self.barra_progresso.maximum())
            sufixo_rej = (
                f" ({total_rejeitados} item(ns) auto-filtrado(s) em rejeitados)."
                if total_rejeitados > 0
                else "."
            )
            self.label_progresso.setText(
                f"Coleta concluída: {total_adicionados} novo(s) candidato(s) adicionado(s){sufixo_rej}"
            )
            self._definir_estado_botoes("concluido")
        else:
            self.label_progresso.setText(
                f"Coleta cancelada ({total_adicionados} candidato(s) parcial(is) preservado(s))."
            )
            self._definir_estado_botoes("pronto")
        if self.worker_ativo is not None:
            self.worker_ativo.deleteLater()
            self.worker_ativo = None

    def executar_coleta_sincrona(self) -> int:
        """
        Executa a coleta de forma síncrona (útil para testes diretos) reutilizando
        o mesmo WorkerColetaBetas e a mesma injeção atômica no CroquiController.
        """
        selecionadas = self._obter_escaladas_selecionadas()
        if not selecionadas or self.cancelado:
            return 0

        self.barra_progresso.setMaximum(len(selecionadas))
        self.barra_progresso.setValue(0)
        self._definir_estado_botoes("coletando")

        worker = WorkerColetaBetas(
            escaladas=selecionadas,
            extratores=self.extratores,
        )
        resultados_capturados: list[list[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]]] = []
        worker.progresso_alterado.connect(self._ao_progresso_worker)
        worker.concluido.connect(lambda lote, _canc: resultados_capturados.append(lote))
        worker.run()

        lote_final = resultados_capturados[0] if resultados_capturados else []
        total_adicionados, total_rejeitados = self._aplicar_lote_coletado(
            lote_final, dict(worker.rejeitados_por_uid)
        )
        if not self.cancelado:
            sufixo_rej = (
                f" ({total_rejeitados} item(ns) auto-filtrado(s) em rejeitados)."
                if total_rejeitados > 0
                else "."
            )
            self.label_progresso.setText(
                f"Coleta concluída: {total_adicionados} novo(s) candidato(s) adicionado(s){sufixo_rej}"
            )
            self._definir_estado_botoes("concluido")
        return total_adicionados
