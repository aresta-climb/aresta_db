# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Wizard / Diálogo de coleta de betas multi-fonte para escaladas selecionadas do croqui.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from PySide6.QtCore import Qt
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
from coleta_de_betas.extratores.duckduckgo import ExtratorDuckDuckGo
from coleta_de_betas.extratores.vertex import ExtratorVertexSearch
from coleta_de_betas.extratores.youtube import ExtratorYouTube


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
    """Cria a lista padrão de extratores ativos conforme credenciais disponíveis no ambiente."""
    extratores: list[ExtratorBetaProtocolo] = [
        ExtratorDuckDuckGo(),
        ExtratorBlog(),
    ]
    if os.environ.get("YOUTUBE_API_KEY"):
        extratores.insert(0, ExtratorYouTube())
    if os.environ.get("VERTEX_PROJECT_ID") and os.environ.get("VERTEX_DATA_STORE_ID"):
        extratores.append(ExtratorVertexSearch())
    return extratores


class DialogoColetarBetas(QDialog):
    """
    Wizard modal para selecionar escaladas do croqui, executar a busca multi-fonte
    (YouTube, Instagram, Blogs) com barra de progresso e injetar os novos candidatos
    em betas_nao_scorados via CroquiController.
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
        self.btn_iniciar.clicked.connect(self.executar_coleta_sincrona)
        botoes_rodape.addWidget(self.btn_cancelar)
        botoes_rodape.addWidget(self.btn_iniciar)
        layout.addLayout(botoes_rodape)

    def _definir_marcacao_todas(self, marcado: bool) -> None:
        for cb in self.checkboxes_por_uid.values():
            cb.setChecked(marcado)

    def solicitar_cancelamento(self) -> None:
        self.cancelado = True
        self.label_progresso.setText("Coleta cancelada pelo usuário.")

    def _ao_clicar_cancelar(self) -> None:
        self.solicitar_cancelamento()
        self.reject()

    def executar_coleta_sincrona(self) -> int:
        """
        Executa a coleta para todas as escaladas marcadas, atualizando a barra de progresso
        e injetando os resultados em betas_nao_scorados via CroquiController.
        """
        selecionadas = [
            info
            for info in self.escaladas_disponiveis
            if self.checkboxes_por_uid[info.escalada_uid].isChecked()
        ]
        if not selecionadas or self.cancelado:
            return 0

        self.barra_progresso.setMaximum(len(selecionadas))
        self.barra_progresso.setValue(0)
        total_adicionados = 0

        self.controller.iniciar_grupo_undo("Coletar Betas")
        try:
            for idx, info in enumerate(selecionadas, start=1):
                if self.cancelado:
                    break
                self.label_progresso.setText(
                    f"Coletando ({idx}/{len(selecionadas)}): {info.nome_escalada}..."
                )
                listas_brutas: list[list[beta_pb2.CandidatoMidiaBeta]] = []
                for extrator in self.extratores:
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
                    total_adicionados += self.controller.adicionar_candidatos_nao_scorados(
                        info.escalada_uid, candidatos_dedup
                    )
                self.barra_progresso.setValue(idx)
        finally:
            self.controller.finalizar_grupo_undo()

        if not self.cancelado:
            self.label_progresso.setText(
                f"Coleta concluída: {total_adicionados} novo(s) candidato(s) adicionado(s)."
            )
        return total_adicionados
