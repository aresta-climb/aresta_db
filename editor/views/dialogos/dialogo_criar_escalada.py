# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton
)
from PyQt6.QtCore import Qt


class DialogoCriarEscalada(QDialog):
    """Diálogo modal para criação de uma nova escalada com escolha de tipo e nome."""

    OPCOES_TIPO = [
        ("Via Esportiva", "via_esportiva"),
        ("Via Móvel", "via_movel"),
        ("Boulder", "boulder"),
        ("Via Múltiplas Enfiadas", "via_multiplas_enfiadas"),
        ("Highline", "highline"),
    ]

    def __init__(self, parent=None, nomes_existentes=None):
        super().__init__(parent)
        self.setWindowTitle("Nova Escalada")
        self.setMinimumWidth(380)

        self.nomes_existentes = [n.strip().lower() for n in (nomes_existentes or []) if n]

        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(12)

        # 1. Tipo de Escalada
        lbl_tipo = QLabel("Tipo de escalada:", self)
        lbl_tipo.setStyleSheet("font-weight: bold;")
        self.combo_tipo = QComboBox(self)
        for label, chave in self.OPCOES_TIPO:
            self.combo_tipo.addItem(label, chave)
        layout_principal.addWidget(lbl_tipo)
        layout_principal.addWidget(self.combo_tipo)

        # 2. Nome da Escalada
        lbl_nome = QLabel("Nome da escalada:", self)
        lbl_nome.setStyleSheet("font-weight: bold;")
        self.edit_nome = QLineEdit(self)
        self.edit_nome.setPlaceholderText("Ex: Sombra da Lua, Fissura dos Sonhos...")
        layout_principal.addWidget(lbl_nome)
        layout_principal.addWidget(self.edit_nome)

        # 3. Aviso de Validação / Duplicidade
        self.lbl_aviso = QLabel("", self)
        self.lbl_aviso.setStyleSheet("color: #d9534f; font-size: 9pt;")
        layout_principal.addWidget(self.lbl_aviso)

        # 4. Botões
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

    def obter_tipo_selecionado(self) -> str:
        """Retorna a chave do tipo selecionado (ex: 'via_esportiva', 'boulder')."""
        return self.combo_tipo.currentData() or "via_esportiva"

    def _validar(self, texto: str):
        """Valida se o nome foi preenchido e não é duplicado."""
        nome = texto.strip()
        if not nome:
            self.lbl_aviso.setText("")
            self.btn_criar.setEnabled(False)
            return

        if nome.lower() in self.nomes_existentes:
            self.lbl_aviso.setText("Já existe uma escalada com este nome neste setor.")
            self.btn_criar.setEnabled(False)
            return

        self.lbl_aviso.setText("")
        self.btn_criar.setEnabled(True)

    def obter_dados_confirmados(self) -> tuple[str, str, bool]:
        """Retorna (tipo_chave, nome, confirmado)."""
        ok = (self.result() == QDialog.DialogCode.Accepted)
        return self.obter_tipo_selecionado(), self.edit_nome.text().strip(), ok

    @classmethod
    def obter_dados(cls, parent=None, nomes_existentes=None) -> tuple[str, str, bool]:
        """Método estático de conveniência."""
        dialogo = cls(parent=parent, nomes_existentes=nomes_existentes)
        dialogo.exec()
        return dialogo.obter_dados_confirmados()
