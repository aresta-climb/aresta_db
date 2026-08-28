# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QScrollArea, QPushButton, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.carregador_imagens import (
    obter_pixmap_fallback,
    WorkerCarregadorImagem
)

class ItemBetaWidget(QFrame):
    """
    Widget visual que exibe um único candidato a beta com thumbnail, título,
    justificativa, score de confiança e opção de aprovação.
    """
    def __init__(self, midia: beta_pb2.MidiaBeta, nome_escalada: str = "", parent=None):
        super().__init__(parent)
        self.midia = midia
        self.nome_escalada = nome_escalada
        self._worker_imagem = None

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            ItemBetaWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-bottom: 6px;
                padding: 6px;
            }
            ItemBetaWidget:hover {
                border: 1px solid #0066cc;
            }
        """)

        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(8, 8, 8, 8)
        layout_principal.setSpacing(12)

        # Checkbox de seleção
        self.checkbox_aprovado = QCheckBox()
        self.checkbox_aprovado.setCursor(Qt.CursorShape.PointingHandCursor)
        layout_principal.addWidget(self.checkbox_aprovado, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Thumbnail
        self.label_thumbnail = QLabel()
        self.label_thumbnail.setFixedSize(120, 90)
        self.label_thumbnail.setScaledContents(True)
        pixmap_inicial = obter_pixmap_fallback(self.midia.fonte)
        self.label_thumbnail.setPixmap(pixmap_inicial)
        layout_principal.addWidget(self.label_thumbnail, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Inicia download da thumbnail se disponível
        if self.midia.thumbnail_url:
            self._worker_imagem = WorkerCarregadorImagem(self.midia.thumbnail_url, self.midia.fonte, parent=self)
            self._worker_imagem.imagem_carregada.connect(self._ao_carregar_thumbnail)
            self._worker_imagem.start()

        # Detalhes textuais
        layout_textos = QVBoxLayout()
        layout_textos.setSpacing(4)

        # Cabeçalho: Título e Score
        layout_cabecalho = QHBoxLayout()
        self.label_titulo = QLabel(self.midia.titulo or self.midia.url)
        self.label_titulo.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.label_titulo.setWordWrap(True)
        layout_cabecalho.addWidget(self.label_titulo, stretch=1)

        score = self.midia.resultado_llm.llm_confidence_score
        cor_score = "#28a745" if score >= 80 else ("#ffc107" if score >= 50 else "#dc3545")
        self.label_score = QLabel(f"Confiança: {score}%")
        self.label_score.setStyleSheet(f"""
            background-color: {cor_score};
            color: #ffffff;
            font-weight: bold;
            border-radius: 4px;
            padding: 3px 6px;
        """)
        layout_cabecalho.addWidget(self.label_score)
        layout_textos.addLayout(layout_cabecalho)

        # Link URL
        self.label_url = QLabel(f'<a href="{self.midia.url}">{self.midia.url}</a>')
        self.label_url.setOpenExternalLinks(True)
        self.label_url.setStyleSheet("color: #0066cc; font-size: 11px;")
        layout_textos.addWidget(self.label_url)

        # Justificativa IA
        self.label_reasoning = QLabel(self.midia.resultado_llm.llm_reasoning)
        self.label_reasoning.setStyleSheet("color: #555555; font-size: 11px; font-style: italic;")
        self.label_reasoning.setWordWrap(True)
        layout_textos.addWidget(self.label_reasoning)

        # Snippets coletados
        if self.midia.snippets:
            texto_snippets = " | ".join(self.midia.snippets)
            self.label_snippets = QLabel(f"Trechos: {texto_snippets}")
            self.label_snippets.setStyleSheet("color: #666666; font-size: 11px;")
            self.label_snippets.setWordWrap(True)
            layout_textos.addWidget(self.label_snippets)

        layout_principal.addLayout(layout_textos, stretch=1)

    def _ao_carregar_thumbnail(self, pixmap):
        if pixmap and not pixmap.isNull():
            self.label_thumbnail.setPixmap(pixmap)

    def esta_aprovado(self) -> bool:
        return self.checkbox_aprovado.isChecked()


class PainelCuradoria(QWidget):
    """
    Aba principal de moderação e curadoria humana de vídeos e postagens de betas.
    """
    solicitar_salvamento = pyqtSignal(dict) # Emite dict[nome_escalada, list[MidiaBeta]]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.id_croqui = ""
        self.caminho_staging = None
        self.itens_widgets: List[ItemBetaWidget] = []

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(12, 12, 12, 12)
        layout_principal.setSpacing(10)

        # Barra de ferramentas superior
        layout_acoes = QHBoxLayout()
        self.label_status = QLabel("Nenhum arquivo de betas carregado.")
        self.label_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout_acoes.addWidget(self.label_status, stretch=1)

        self.btn_auto_selecionar = QPushButton("Aprovar >= 80%")
        self.btn_auto_selecionar.clicked.connect(self._aprovar_alta_confianca)
        layout_acoes.addWidget(self.btn_auto_selecionar)

        self.btn_limpar = QPushButton("Desmarcar Todos")
        self.btn_limpar.clicked.connect(self._desmarcar_todos)
        layout_acoes.addWidget(self.btn_limpar)

        self.btn_salvar = QPushButton("Salvar Betas Aprovados")
        self.btn_salvar.setStyleSheet("""
            background-color: #28a745;
            color: #ffffff;
            font-weight: bold;
            padding: 6px 12px;
            border-radius: 4px;
        """)
        self.btn_salvar.clicked.connect(self._ao_clicar_salvar)
        layout_acoes.addWidget(self.btn_salvar)

        layout_principal.addLayout(layout_acoes)

        # Área de Scroll contendo a lista
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container_lista = QWidget()
        self.layout_lista = QVBoxLayout(self.container_lista)
        self.layout_lista.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_lista.setSpacing(8)
        self.scroll_area.setWidget(self.container_lista)

        layout_principal.addWidget(self.scroll_area, stretch=1)

    def obter_id_croqui(self) -> str:
        return self.id_croqui

    def carregar_staging(self, caminho_arquivo: Path | str):
        """
        Lê o arquivo betas_pendentes.binarypb e preenche a lista na interface.
        """
        self.caminho_staging = Path(caminho_arquivo)
        if not self.caminho_staging.exists():
            self.label_status.setText(f"Arquivo não encontrado: {self.caminho_staging.name}")
            return

        from coleta_de_betas.inteligencia.avaliador import carregar_betas_pendentes
        pendentes = carregar_betas_pendentes(self.caminho_staging)
        self.id_croqui = pendentes.id_croqui

        # Limpa lista anterior
        for widget in self.itens_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.itens_widgets.clear()

        total_candidatos = 0
        for escalada_candidatos in pendentes.candidatos_por_escalada:
            nome_esc = escalada_candidatos.nome_escalada
            nome_setor = escalada_candidatos.nome_setor
            nome_grupo = escalada_candidatos.nome_grupo

            # Grupo visual da escalada
            rotulo_grupo = f"Escalada: {nome_esc}"
            if nome_grupo and nome_setor:
                rotulo_grupo += f" ({nome_grupo} > {nome_setor})"
            elif nome_setor:
                rotulo_grupo += f" (Setor: {nome_setor})"
            elif nome_grupo:
                rotulo_grupo += f" (Grupo: {nome_grupo})"

            grupo = QGroupBox(rotulo_grupo)
            layout_grupo = QVBoxLayout(grupo)
            layout_grupo.setSpacing(6)

            # Ordena por score decrescente
            candidatos_ordenados = sorted(
                escalada_candidatos.candidatos,
                key=lambda c: c.resultado_llm.llm_confidence_score,
                reverse=True
            )

            for midia in candidatos_ordenados:
                item_widget = ItemBetaWidget(midia, nome_escalada=nome_esc, parent=grupo)
                self.itens_widgets.append(item_widget)
                layout_grupo.addWidget(item_widget)
                total_candidatos += 1

            self.layout_lista.addWidget(grupo)

        self.label_status.setText(f"Croqui: {self.id_croqui} ({total_candidatos} mídias candidatas)")

    def _aprovar_alta_confianca(self):
        for widget in self.itens_widgets:
            if widget.midia.resultado_llm.llm_confidence_score >= 80:
                widget.checkbox_aprovado.setChecked(True)

    def _desmarcar_todos(self):
        for widget in self.itens_widgets:
            widget.checkbox_aprovado.setChecked(False)

    def obter_betas_aprovados(self) -> Dict[str, List[beta_pb2.MidiaBeta]]:
        """
        Retorna um dicionário mapeando o nome da via para a lista de MidiaBeta aprovadas.
        """
        aprovados: Dict[str, List[beta_pb2.MidiaBeta]] = {}
        for widget in self.itens_widgets:
            if widget.esta_aprovado():
                nome = widget.nome_escalada
                if nome not in aprovados:
                    aprovados[nome] = []
                aprovados[nome].append(widget.midia)
        return aprovados

    def _ao_clicar_salvar(self):
        aprovados = self.obter_betas_aprovados()
        self.solicitar_salvamento.emit(aprovados)
