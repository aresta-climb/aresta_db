# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional
from PySide6.QtWidgets import (

    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QWidget,
)
from PySide6.QtCore import Qt


class DialogoPerfilAutor(QDialog):
    """
    Diálogo para captura e confirmação do Nome Completo do autor.
    Permite pré-preenchimento inteligente a partir de dados do GitHub.
    """

    def __init__(self, nome_sugerido: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        from editor.core.storage import GerenciadorCaminhos
        from PySide6.QtGui import QIcon

        caminho_logo_janela = GerenciadorCaminhos().obter_caminho_recurso_interno("recursos/logo_app.png")
        self.setWindowIcon(QIcon(str(caminho_logo_janela)))

        self.setWindowTitle("Identificação do Autor")
        self.setMinimumWidth(420)
        self.init_ui(nome_sugerido)

    def init_ui(self, nome_sugerido: str) -> None:
        from editor.core.storage import GerenciadorCaminhos
        from PySide6.QtGui import QPixmap

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)

        # Logo Aresta Climb
        caminho_logo = GerenciadorCaminhos().obter_caminho_recurso_interno("recursos/logo_splash.png")
        if caminho_logo.exists():
            pixmap = QPixmap(str(caminho_logo))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    160, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                label_logo = QLabel()
                label_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label_logo.setPixmap(pixmap)
                layout.addWidget(label_logo)

        titulo = QLabel("Identificação do Autor")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #212529;")
        layout.addWidget(titulo)

        descricao = QLabel(
            "Para registrar a autoria das suas colaborações e croquis no banco de dados comunitário, "
            "informe seu nome completo (nome e sobrenome):"
        )
        descricao.setWordWrap(True)
        descricao.setStyleSheet("color: #495057; font-size: 13px; line-height: 1.4;")
        layout.addWidget(descricao)

        self.edit_nome = QLineEdit()
        self.edit_nome.setPlaceholderText("Ex: João da Silva")
        self.edit_nome.setText(nome_sugerido)
        self.edit_nome.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #80bdff;
            }
        """)
        layout.addWidget(self.edit_nome)

        botoes_layout = QHBoxLayout()
        botoes_layout.addStretch()

        self.btn_confirmar = QPushButton("Confirmar e Continuar")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirmar.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background: #218838; }
        """)
        self.btn_confirmar.clicked.connect(self.confirmar_e_fechar)
        botoes_layout.addWidget(self.btn_confirmar)

        layout.addLayout(botoes_layout)

    def confirmar_e_fechar(self) -> None:
        nome = self.obter_nome_completo()
        palavras = nome.split()
        if len(palavras) < 2:
            QMessageBox.warning(
                self,
                "Nome Incompleto",
                "Por favor, digite seu nome e sobrenome completos.",
            )
            return

        self.accept()

    def obter_nome_completo(self) -> str:
        return self.edit_nome.text().strip()

