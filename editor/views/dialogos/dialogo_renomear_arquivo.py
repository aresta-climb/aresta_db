# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Diálogo modal para renomear arquivos Markdown (.md) com validação estrita em tempo real."""

import re
from collections.abc import Sequence

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.core.nomes_arquivos import validar_nome_arquivo_md


class DialogoRenomearArquivo(QDialog):
    """Diálogo modal que valida e normaliza o novo nome de um arquivo Markdown."""

    def __init__(
        self,
        arquivo_atual: str = "",
        arquivos_existentes: Sequence[str] = (),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modificar Nome do Arquivo")
        self.setMinimumWidth(420)

        self._arquivo_atual = arquivo_atual.strip()
        self._arquivos_existentes = tuple(arquivos_existentes)

        layout_principal = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.edit_arquivo = QLineEdit()
        self.edit_arquivo.setPlaceholderText("Ex: setor_principal.md")
        form_layout.addRow("Nome do Arquivo (.md):", self.edit_arquivo)
        layout_principal.addLayout(form_layout)

        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setStyleSheet("color: #d9534f; font-size: 11px; font-weight: bold;")
        self.lbl_aviso.setWordWrap(True)
        layout_principal.addWidget(self.lbl_aviso)

        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_confirmar = QPushButton("Confirmar")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.clicked.connect(self.accept)

        layout_botoes.addWidget(self.btn_cancelar)
        layout_botoes.addWidget(self.btn_confirmar)
        layout_principal.addLayout(layout_botoes)

        self.edit_arquivo.textChanged.connect(self._ao_alterar_texto)
        self.edit_arquivo.setText(self._arquivo_atual)
        self._validar()

    def _ao_alterar_texto(self, texto: str) -> None:
        if re.search(r"\s", texto):
            pos_cursor = self.edit_arquivo.cursorPosition()
            convertido = re.sub(r"\s+", "_", texto)
            self.edit_arquivo.blockSignals(True)
            self.edit_arquivo.setText(convertido)
            self.edit_arquivo.setCursorPosition(min(pos_cursor, len(convertido)))
            self.edit_arquivo.blockSignals(False)
        self._validar()

    def _validar(self) -> None:
        valido, _, erro = validar_nome_arquivo_md(
            self.edit_arquivo.text(),
            self._arquivos_existentes,
            arquivo_atual=self._arquivo_atual,
        )
        self.lbl_aviso.setText("" if valido else erro)
        self.btn_confirmar.setEnabled(valido)

    def obter_dados_confirmados(self) -> tuple[str, bool]:
        """Retorna a tupla (nome_normalizado, confirmado_com_sucesso)."""
        valido, normalizado, _ = validar_nome_arquivo_md(
            self.edit_arquivo.text(),
            self._arquivos_existentes,
            arquivo_atual=self._arquivo_atual,
        )
        confirmado = self.result() == QDialog.DialogCode.Accepted and valido
        return normalizado, confirmado

    @classmethod
    def obter_dados(
        cls,
        arquivo_atual: str = "",
        arquivos_existentes: Sequence[str] = (),
        parent: QWidget | None = None,
    ) -> tuple[str, bool]:
        """Abre o diálogo de forma modal e retorna (nome_normalizado, confirmado)."""
        dialogo = cls(
            arquivo_atual=arquivo_atual,
            arquivos_existentes=arquivos_existentes,
            parent=parent,
        )
        dialogo.exec()
        return dialogo.obter_dados_confirmados()
