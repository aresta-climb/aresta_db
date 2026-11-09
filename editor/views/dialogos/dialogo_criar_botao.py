# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors


import re

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.core.formatacao import para_snake_case
from editor.core.nomes_arquivos import validar_nome_arquivo_md


class DialogoCriarBotao(QDialog):
    """Diálogo modal para criação de um novo Botão com página de Seção Textual (.md)."""

    def __init__(
        self,
        parent: QWidget | None = None,
        texto_sugerido: str = "",
        textos_existentes: list[str] | None = None,
        arquivos_existentes: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo Botão / Seção Textual")
        self.setMinimumWidth(400)

        self.textos_existentes: list[str] = [
            t.strip().lower() for t in (textos_existentes or []) if t
        ]
        self.arquivos_existentes: list[str] = [
            a.strip().lower() for a in (arquivos_existentes or []) if a
        ]
        self._arquivo_editado_manualmente: bool = False
        self._atualizando_internamente: bool = False

        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(12)

        # 1. Texto do Botão
        lbl_texto = QLabel("Texto do botão:", self)
        lbl_texto.setStyleSheet("font-weight: bold;")
        self.edit_texto = QLineEdit(self)
        self.edit_texto.setPlaceholderText("Ex: Como Chegar, Sobre o Croqui, História...")
        layout_principal.addWidget(lbl_texto)
        layout_principal.addWidget(self.edit_texto)

        # 2. Nome do Arquivo (.md)
        lbl_arquivo = QLabel("Nome do arquivo (.md):", self)
        lbl_arquivo.setStyleSheet("font-weight: bold;")
        self.edit_arquivo = QLineEdit(self)
        self.edit_arquivo.setPlaceholderText("Ex: secao_como_chegar.md")
        layout_principal.addWidget(lbl_arquivo)
        layout_principal.addWidget(self.edit_arquivo)

        # 3. Aviso de Validação / Duplicidade
        self.lbl_aviso = QLabel("", self)
        self.lbl_aviso.setStyleSheet("color: #d9534f; font-size: 9pt;")
        layout_principal.addWidget(self.lbl_aviso)

        # 4. Botões de Ação
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

        # Conexões
        self.edit_texto.textChanged.connect(self._on_texto_alterado)
        self.edit_arquivo.textChanged.connect(self._on_arquivo_alterado)

        if texto_sugerido:
            self.edit_texto.setText(texto_sugerido)

    def _on_texto_alterado(self, texto: str) -> None:
        if not self._arquivo_editado_manualmente:
            self._atualizar_proposicao_arquivo()
        self._validar()

    def _on_arquivo_alterado(self, texto: str) -> None:
        if re.search(r"\s", texto):
            pos_cursor = self.edit_arquivo.cursorPosition()
            convertido = re.sub(r"\s+", "_", texto)
            self.edit_arquivo.blockSignals(True)
            self.edit_arquivo.setText(convertido)
            self.edit_arquivo.setCursorPosition(min(pos_cursor, len(convertido)))
            self.edit_arquivo.blockSignals(False)
            texto = convertido
        if not self._atualizando_internamente:
            self._arquivo_editado_manualmente = bool(texto.strip())
        self._validar()

    def _atualizar_proposicao_arquivo(self) -> None:
        texto = self.edit_texto.text().strip()
        self._atualizando_internamente = True
        try:
            if not texto:
                self.edit_arquivo.setText("")
                return
            slug = para_snake_case(texto)
            if slug:
                self.edit_arquivo.setText(f"{slug}.md")
            else:
                self.edit_arquivo.setText("botao.md")
        finally:
            self._atualizando_internamente = False

    def _validar(self) -> None:
        texto = self.edit_texto.text().strip()
        arquivo = self.edit_arquivo.text().strip()

        if not texto:
            self.lbl_aviso.setText("")
            self.btn_criar.setEnabled(False)
            return

        if texto.lower() in self.textos_existentes:
            self.lbl_aviso.setText("Já existe um botão com este texto no croqui.")
            self.btn_criar.setEnabled(False)
            return

        valido_arq, _, erro_arq = validar_nome_arquivo_md(arquivo, self.arquivos_existentes)
        if not valido_arq:
            self.lbl_aviso.setText(erro_arq)
            self.btn_criar.setEnabled(False)
            return

        self.lbl_aviso.setText("")
        self.btn_criar.setEnabled(True)

    def obter_dados_confirmados(self) -> tuple[str, str, bool]:
        """Retorna (texto_botao, nome_arquivo_md, confirmado)."""
        valido_arq, arquivo_normalizado, _ = validar_nome_arquivo_md(
            self.edit_arquivo.text(), self.arquivos_existentes
        )
        texto = self.edit_texto.text().strip()
        ok = (
            self.result() == QDialog.DialogCode.Accepted
            and bool(texto)
            and texto.lower() not in self.textos_existentes
            and valido_arq
        )
        return texto, arquivo_normalizado, ok

    @classmethod
    def obter_dados(
        cls,
        parent: QWidget | None = None,
        texto_sugerido: str = "",
        textos_existentes: list[str] | None = None,
        arquivos_existentes: list[str] | None = None,
    ) -> tuple[str, str, bool]:
        """Método estático de conveniência."""
        dialogo = cls(
            parent=parent,
            texto_sugerido=texto_sugerido,
            textos_existentes=textos_existentes,
            arquivos_existentes=arquivos_existentes,
        )
        dialogo.exec()
        return dialogo.obter_dados_confirmados()
