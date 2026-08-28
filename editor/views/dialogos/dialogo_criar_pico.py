# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton
)
from PySide6.QtCore import Qt


class DialogoCriarPico(QDialog):
    """Diálogo modal para criação de um novo Pico com validação de duplicidade."""

    def __init__(self, parent=None, nome_sugerido="", nomes_existentes=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Pico")
        self.setMinimumWidth(380)

        self.nomes_existentes = [n.strip().lower() for n in (nomes_existentes or []) if n]

        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(12)

        # 1. Nome do Pico
        lbl_nome = QLabel("Nome do pico:", self)
        lbl_nome.setStyleSheet("font-weight: bold;")
        self.edit_nome = QLineEdit(self)
        self.edit_nome.setPlaceholderText("Ex: Pedra do Baú, Cuscuzeiro...")
        layout_principal.addWidget(lbl_nome)
        layout_principal.addWidget(self.edit_nome)

        # 2. Aviso de Validação / Duplicidade
        self.lbl_aviso = QLabel("", self)
        self.lbl_aviso.setStyleSheet("color: #d9534f; font-size: 9pt;")
        layout_principal.addWidget(self.lbl_aviso)

        # 3. Botões
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()

        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_criar = QPushButton("Criar", self)
        self.btn_criar.setDefault(True)
        self.btn_criar.setEnabled(False)
        self.btn_criar.setStyleSheet("""
            QPushButton {
                background-color: #2b579a;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e3f6f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_criar.clicked.connect(self.accept)

        layout_botoes.addWidget(self.btn_cancelar)
        layout_botoes.addWidget(self.btn_criar)
        layout_principal.addLayout(layout_botoes)

        self.edit_nome.textChanged.connect(self._validar)

        if nome_sugerido:
            self.edit_nome.setText(nome_sugerido)

    def _validar(self, texto: str):
        """Valida se o nome foi preenchido e não é duplicado."""
        nome = texto.strip()
        if not nome:
            self.lbl_aviso.setText("")
            self.btn_criar.setEnabled(False)
            return

        if nome.lower() in self.nomes_existentes:
            self.lbl_aviso.setText("Já existe um pico com este nome no croqui.")
            self.btn_criar.setEnabled(False)
            return

        self.lbl_aviso.setText("")
        self.btn_criar.setEnabled(True)

    def obter_dados_confirmados(self) -> tuple[str, bool]:
        """Retorna (nome, confirmado)."""
        ok = (self.result() == QDialog.DialogCode.Accepted)
        return self.edit_nome.text().strip(), ok

    @classmethod
    def obter_dados(cls, parent=None, nome_sugerido="", nomes_existentes=None) -> tuple[str, bool]:
        """Método estático de conveniência."""
        dialogo = cls(parent=parent, nome_sugerido=nome_sugerido, nomes_existentes=nomes_existentes)
        dialogo.exec()
        return dialogo.obter_dados_confirmados()
