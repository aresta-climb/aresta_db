# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DialogoRecuperacaoSessao(QDialog):
    """
    Diálogo modal exibido na abertura de um croqui caso existam alterações pendentes
    no diário de comandos após uma interrupção inesperada ou crash.
    """
    def __init__(self, total_acoes: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sessão Anterior Interrompida")
        self.setModal(True)
        self.setFixedWidth(440)
        self.setFont(QFont("Segoe UI", 9))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Título
        lbl_titulo = QLabel("Recuperação de Trabalho", self)
        lbl_titulo.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(lbl_titulo)

        # Mensagem explicativa
        if total_acoes == 1:
            texto_acoes = "<b>1 ação não salva</b>"
            termo_encontrada = "Foi encontrada"
        else:
            texto_acoes = f"<b>{total_acoes} ações não salvas</b>"
            termo_encontrada = "Foram encontradas"

        texto = (
            "<p>Detectamos que o editor foi fechado antes de salvar as últimas alterações.</p>"
            f"<p>{termo_encontrada} {texto_acoes} gravadas com segurança no diário local.</p>"
            "<p>Deseja restaurar essas alterações e continuar editando de onde parou?</p>"
        )
        self.label_mensagem = QLabel(texto, self)
        self.label_mensagem.setTextFormat(Qt.TextFormat.RichText)
        self.label_mensagem.setWordWrap(True)
        layout.addWidget(self.label_mensagem)

        # Divisor
        linha = QFrame(self)
        linha.setFrameShape(QFrame.Shape.HLine)
        linha.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(linha)

        # Botões
        botoes_layout = QHBoxLayout()
        botoes_layout.setSpacing(10)
        botoes_layout.addStretch()

        self.botao_descartar = QPushButton("Descartar", self)
        self.botao_descartar.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)
        self.botao_descartar.clicked.connect(self.reject)
        botoes_layout.addWidget(self.botao_descartar)

        self.botao_recuperar = QPushButton("Recuperar Trabalho", self)
        self.botao_recuperar.setDefault(True)
        self.botao_recuperar.setStyleSheet("""
            QPushButton {
                padding: 6px 18px;
                background-color: #0066cc;
                border: 1px solid #0055aa;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0055aa;
            }
        """)
        self.botao_recuperar.clicked.connect(self.accept)
        botoes_layout.addWidget(self.botao_recuperar)

        layout.addLayout(botoes_layout)
