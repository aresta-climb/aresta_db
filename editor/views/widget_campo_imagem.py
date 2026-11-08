# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para exibição de miniatura, metadados e troca de imagens
armazenadas em memória RAM ou em disco no editor.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.core.processamento_imagem_campo import (
    AREA_MAXIMA_PADRAO,
    obter_metadados_imagem,
)
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa


class WidgetCampoImagem(QWidget):
    """
    Widget de exibição de miniatura, metadados e controle de troca de imagem.
    """

    imagem_alterada = Signal(str, bytes)  # caminho_relativo, bytes_conteudo
    imagem_removida = Signal()
    abrir_no_editor = Signal(str)  # caminho_relativo

    def __init__(
        self,
        model: CroquiModel | None = None,
        caminho_imagem: str = "",
        nome_arquivo_fixo: str | None = None,
        area_maxima: int = AREA_MAXIMA_PADRAO,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: CroquiModel | None = model
        self._caminho_atual: str = caminho_imagem
        self.nome_arquivo_fixo: str | None = nome_arquivo_fixo
        self.area_maxima: int = area_maxima

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        # Card container
        self.frame_card = QFrame()
        self.frame_card.setFrameShape(QFrame.Shape.StyledPanel)
        layout_card = QHBoxLayout(self.frame_card)
        layout_card.setContentsMargins(8, 8, 8, 8)
        layout_card.setSpacing(12)

        # Preview miniatura
        self.rotulo_preview = QLabel()
        self.rotulo_preview.setFixedSize(140, 100)
        self.rotulo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_preview.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.05); border-radius: 4px;"
        )
        layout_card.addWidget(self.rotulo_preview)

        # Informações e botões
        layout_info = QVBoxLayout()
        layout_info.setSpacing(4)

        self.rotulo_status = QLabel()
        self.rotulo_status.setStyleSheet("font-weight: bold;")
        self.rotulo_metadados = QLabel()
        self.rotulo_metadados.setStyleSheet("color: #6b7280; font-size: 11px;")

        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(6)

        self.btn_trocar = QPushButton("Trocar Imagem...")
        self.btn_trocar.clicked.connect(self.selecionar_e_trocar_imagem)

        self.btn_remover = QPushButton("Remover Imagem")
        self.btn_remover.clicked.connect(self.remover_imagem)

        self.btn_abrir_editor = QPushButton("Abrir no Editor")
        self.btn_abrir_editor.clicked.connect(self._ao_clicar_abrir_editor)

        layout_botoes.addWidget(self.btn_trocar)
        layout_botoes.addWidget(self.btn_remover)
        layout_botoes.addWidget(self.btn_abrir_editor)
        layout_botoes.addStretch()

        layout_info.addWidget(self.rotulo_status)
        layout_info.addWidget(self.rotulo_metadados)
        layout_info.addStretch()
        layout_info.addLayout(layout_botoes)

        layout_card.addLayout(layout_info, stretch=1)
        layout_principal.addWidget(self.frame_card)

        if self.model is not None and hasattr(self.model, "imagem_alterada"):
            self.model.imagem_alterada.connect(self._ao_alterar_imagem_modelo)

        self.atualizar_visualizacao()

    def _ao_alterar_imagem_modelo(self, caminho_relativo: str) -> None:
        if self._caminho_atual and caminho_relativo == self._caminho_atual:
            self.atualizar_visualizacao()

    def obter_caminho_atual(self) -> str:
        return self._caminho_atual

    def definir_caminho_atual(self, caminho: str) -> None:
        self._caminho_atual = caminho
        self.atualizar_visualizacao()

    def atualizar_visualizacao(self, bytes_override: bytes | None = None) -> None:
        if not self._caminho_atual:
            self.rotulo_preview.clear()
            self.rotulo_preview.setText("Sem Imagem")
            self.rotulo_status.setText("Nenhuma imagem selecionada")
            self.rotulo_metadados.setText("Selecione um arquivo de imagem (WebP, PNG, JPG)")
            self.btn_remover.setEnabled(False)
            self.btn_abrir_editor.setEnabled(False)
            return

        bytes_img = self.model.obter_bytes_imagem(self._caminho_atual) if self.model else None
        if bytes_img is None and bytes_override is not None:
            bytes_img = bytes_override

        if bytes_img:
            pixmap = QPixmap()
            pixmap.loadFromData(bytes_img)
            if not pixmap.isNull():
                pixmap_redimensionado = pixmap.scaled(
                    self.rotulo_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.rotulo_preview.setPixmap(pixmap_redimensionado)
            else:
                self.rotulo_preview.setText("Erro Img")

            w, h, _, tam_fmt = obter_metadados_imagem(bytes_img)
            nome_arquivo = Path(self._caminho_atual).name
            self.rotulo_status.setText(nome_arquivo)
            self.rotulo_metadados.setText(f"{w} x {h} px • {tam_fmt} • {self._caminho_atual}")
            self.btn_remover.setEnabled(True)
            self.btn_abrir_editor.setEnabled(True)
        else:
            self.rotulo_preview.setText("Ausente")
            nome_arquivo = Path(self._caminho_atual).name
            self.rotulo_status.setText(f"{nome_arquivo} (Não encontrada)")
            self.rotulo_metadados.setText(f"Arquivo não encontrado: {self._caminho_atual}")
            self.btn_remover.setEnabled(True)
            self.btn_abrir_editor.setEnabled(False)

    def aplicar_nova_imagem(self, caminho_relativo: str, bytes_conteudo: bytes) -> None:
        """Emite o sinal de alteração de imagem para o controlador e atualiza o preview da View."""
        self._caminho_atual = caminho_relativo
        self.imagem_alterada.emit(caminho_relativo, bytes_conteudo)
        self.atualizar_visualizacao(bytes_override=bytes_conteudo)

    def remover_imagem(self) -> None:
        """Limpa o campo de imagem atual."""
        self._caminho_atual = ""
        self.atualizar_visualizacao()
        self.imagem_removida.emit()

    def selecionar_e_trocar_imagem(self) -> None:
        """Abre o wizard unificado de imagem para importação/seleção e processamento WebP em memória."""
        db_dir = None
        if self.model and hasattr(self.model, "_caminho_db_atual") and self.model._caminho_db_atual:
            db_dir = self.model._caminho_db_atual

        dialogo = DialogoAdicionarMapa(
            nome_sugerido=self.nome_arquivo_fixo or "",
            db_dir=db_dir,
            model=self.model,
            parent=self,
            max_area_override=self.area_maxima,
            caminho_destino_fixo=self.nome_arquivo_fixo,
            titulo_janela="Selecionar ou Importar Imagem",
            texto_botao_ok="Confirmar Imagem",
        )
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        caminho_relativo = dialogo.obter_caminho_final_relativo()
        bytes_webp = dialogo.obter_bytes_imagem_processada()
        if bytes_webp is not None:
            self.aplicar_nova_imagem(caminho_relativo, bytes_webp)

    def _ao_clicar_abrir_editor(self) -> None:
        if self._caminho_atual:
            self.abrir_no_editor.emit(self._caminho_atual)
