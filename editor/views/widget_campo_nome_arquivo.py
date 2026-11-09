# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Componente visual para exibição somente-leitura e renomeação modal de arquivos Markdown (.md)."""

from collections.abc import Callable, Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from editor.views.dialogos.dialogo_renomear_arquivo import DialogoRenomearArquivo


class WidgetCampoNomeArquivo(QWidget):
    """Widget que exibe o nome do arquivo .md em modo somente-leitura com botão 'Modificar...'."""

    nome_alterado = Signal(str)

    def __init__(
        self,
        nome_inicial: str = "",
        provedor_arquivos_existentes: Callable[[], Sequence[str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._provedor_arquivos_existentes = provedor_arquivos_existentes

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit_nome = QLineEdit(nome_inicial, self)
        self.edit_nome.setReadOnly(True)
        self.edit_nome.setProperty("protobuf_field", "__filename__")

        self.btn_modificar = QPushButton("Modificar...", self)
        self.btn_modificar.clicked.connect(self._ao_clicar_modificar)

        layout.addWidget(self.edit_nome, 1)
        layout.addWidget(self.btn_modificar)

    def definir_nome_arquivo(self, nome: str) -> None:
        """Atualiza o texto exibido no campo somente-leitura."""
        self.edit_nome.setText(nome)

    def obter_nome_arquivo(self) -> str:
        """Retorna o nome de arquivo atualmente exibido."""
        return self.edit_nome.text()

    def definir_provedor_arquivos_existentes(
        self,
        provedor: Callable[[], Sequence[str]] | None,
    ) -> None:
        """Define a função chamada ao abrir o modal para listar os arquivos existentes no croqui."""
        self._provedor_arquivos_existentes = provedor

    def _ao_clicar_modificar(self) -> None:
        atual = self.obter_nome_arquivo()
        existentes = (
            self._provedor_arquivos_existentes()
            if self._provedor_arquivos_existentes is not None
            else ()
        )
        novo_nome, confirmado = DialogoRenomearArquivo.obter_dados(
            arquivo_atual=atual,
            arquivos_existentes=existentes,
            parent=self,
        )
        if confirmado and novo_nome != atual:
            self.definir_nome_arquivo(novo_nome)
            self.nome_alterado.emit(novo_nome)
