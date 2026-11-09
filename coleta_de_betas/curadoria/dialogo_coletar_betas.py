# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Wizard / Diálogo de coleta de betas multi-fonte em background (QThread) para escaladas selecionadas do croqui.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import ExtratorBlog
from coleta_de_betas.extratores.deduplicador import deduplicar_midias


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
    Cria a lista padrão com o extrator web unificado (ddgs), que executa 1 única
    busca aberta por escalada e classifica os resultados nas 8 categorias de FonteMidia.Enum.
    """
    return [ExtratorBlog()]


class WorkerColetaBetas(QThread):
    """
    Worker em background (QThread) que executa os extratores de rede e deduplicação
    para as escaladas selecionadas sem bloquear o loop de eventos da GUI.
    """

    progresso_alterado = Signal(int, int, str)
    concluido = Signal(object, bool)

    def __init__(
        self,
        escaladas: Sequence[InfoEscaladaColeta],
        extratores: Sequence[ExtratorBetaProtocolo],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.escaladas = list(escaladas)
        self.extratores = list(extratores)
        self._cancelado = False

    def solicitar_cancelamento(self) -> None:
        """Sinaliza cancelamento cooperativo imediato para interromper o loop de busca."""
        self._cancelado = True

    def foi_cancelado(self) -> bool:
        """Retorna True se o cancelamento cooperativo foi solicitado."""
        return self._cancelado

    def run(self) -> None:
        """Executa a coleta e deduplicação em memória emitindo sinais para a thread principal."""
        resultados_por_uid: list[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]] = []
        total = len(self.escaladas)

        for idx, info in enumerate(self.escaladas, start=1):
            if self._cancelado:
                break
            self.progresso_alterado.emit(idx, total, info.nome_escalada)
            if self._cancelado:
                break

            listas_brutas: list[list[beta_pb2.CandidatoMidiaBeta]] = []
            for extrator in self.extratores:
                if self._cancelado:
                    break
                try:
                    res = extrator.buscar(
                        nome_escalada=info.nome_escalada,
                        nome_setor=info.nome_setor,
                        nome_pico=info.nome_pico,
                    )
                    listas_brutas.append(res)
                except Exception:
                    continue

            candidatos_dedup = deduplicar_midias(listas_brutas)
            if candidatos_dedup:
                resultados_por_uid.append((info.escalada_uid, candidatos_dedup))

        self.concluido.emit(resultados_por_uid, self._cancelado)


class DialogoColetarBetas(QDialog):
    """
    Wizard modal para selecionar escaladas do croqui, executar a busca multi-fonte
    (YouTube, Instagram, Blogs) em background via WorkerColetaBetas(QThread) com barra
    de progresso e injetar os novos candidatos em betas_nao_scorados via CroquiController.
    """

    def __init__(
        self,
        model: Any,
        controller: Any,
        extratores: Sequence[ExtratorBetaProtocolo] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model = model
        self.controller = controller
        self.extratores: list[ExtratorBetaProtocolo] = (
            list(extratores) if extratores is not None else criar_extratores_padrao()
        )
        self.cancelado: bool = False
        self.worker_ativo: WorkerColetaBetas | None = None
        self.checkboxes_por_uid: dict[str, QCheckBox] = {}

        self.setWindowTitle("Coletar Betas para Escaladas")
        self.setMinimumSize(520, 440)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl_intro = QLabel(
            "Selecione as escaladas para buscar candidatos de beta (YouTube, Instagram e Blogs).\n"
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
        self.btn_cancelar = QPushButton("Cancelar / Fechar")
        self.btn_cancelar.clicked.connect(self._ao_clicar_cancelar)
        self.btn_iniciar = QPushButton("Iniciar Coleta")
        self.btn_iniciar.setDefault(True)
        self.btn_iniciar.clicked.connect(self.iniciar_coleta_assincrona)
        botoes_rodape.addWidget(self.btn_cancelar)
        botoes_rodape.addWidget(self.btn_iniciar)
        layout.addLayout(botoes_rodape)

    def _definir_marcacao_todas(self, marcado: bool) -> None:
        for cb in self.checkboxes_por_uid.values():
            cb.setChecked(marcado)

    def _definir_controles_habilitados(self, habilitado: bool) -> None:
        self.btn_iniciar.setEnabled(habilitado)
        self.btn_marcar_todas.setEnabled(habilitado)
        self.btn_desmarcar_todas.setEnabled(habilitado)
        for cb in self.checkboxes_por_uid.values():
            cb.setEnabled(habilitado)

    def solicitar_cancelamento(self) -> None:
        self.cancelado = True
        if self.worker_ativo is not None:
            self.worker_ativo.solicitar_cancelamento()
        self.label_progresso.setText("Coleta cancelada pelo usuário.")

    def _ao_clicar_cancelar(self) -> None:
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
    ) -> int:
        if not resultados_por_uid:
            return 0
        total_adicionados = 0
        self.controller.iniciar_grupo_undo("Coletar Betas")
        try:
            for escalada_uid, candidatos_dedup in resultados_por_uid:
                if candidatos_dedup:
                    total_adicionados += self.controller.adicionar_candidatos_nao_scorados(
                        escalada_uid, candidatos_dedup
                    )
        finally:
            self.controller.finalizar_grupo_undo()
        return total_adicionados

    def iniciar_coleta_assincrona(self) -> None:
        """Dispara a coleta em uma QThread de background mantendo a interface responsiva."""
        if self.worker_ativo is not None and self.worker_ativo.isRunning():
            return
        selecionadas = self._obter_escaladas_selecionadas()
        if not selecionadas or self.cancelado:
            return

        self.barra_progresso.setMaximum(len(selecionadas))
        self.barra_progresso.setValue(0)
        self._definir_controles_habilitados(False)

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
        total_adicionados = self._aplicar_lote_coletado(resultados_por_uid)
        if not foi_cancelado and not self.cancelado:
            self.barra_progresso.setValue(self.barra_progresso.maximum())
            self.label_progresso.setText(
                f"Coleta concluída: {total_adicionados} novo(s) candidato(s) adicionado(s)."
            )
        else:
            self.label_progresso.setText(
                f"Coleta cancelada ({total_adicionados} candidato(s) parcial(is) preservado(s))."
            )
        self._definir_controles_habilitados(True)
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

        worker = WorkerColetaBetas(
            escaladas=selecionadas,
            extratores=self.extratores,
        )
        resultados_capturados: list[list[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]]] = []
        worker.progresso_alterado.connect(self._ao_progresso_worker)
        worker.concluido.connect(lambda lote, _canc: resultados_capturados.append(lote))
        worker.run()

        lote_final = resultados_capturados[0] if resultados_capturados else []
        total_adicionados = self._aplicar_lote_coletado(lote_final)
        if not self.cancelado:
            self.label_progresso.setText(
                f"Coleta concluída: {total_adicionados} novo(s) candidato(s) adicionado(s)."
            )
        return total_adicionados
