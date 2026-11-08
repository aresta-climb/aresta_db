# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.core.serializacao_util import carregar_yaml


class DialogoBuscaCroqui(QDialog):
    """
    Diálogo para busca e seleção de croquis oficiais.
    Lê a lista de croquis da pasta database dentro do repositório sincronizado.
    """

    def __init__(self, storage: Any | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.storage: Any | None = storage
        self.setWindowTitle("Buscar Croqui Oficial")
        self.setFixedSize(500, 400)
        self.id_selecionado: str | None = None

        self.layout_principal: QVBoxLayout = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(15, 15, 15, 15)
        self.layout_principal.setSpacing(10)

        self.campo_busca: QLineEdit = QLineEdit()
        self.campo_busca.setPlaceholderText("Digite para buscar por nome ou ID...")
        self.campo_busca.setStyleSheet(
            "padding: 8px; border: 1px solid #ced4da; border-radius: 4px;"
        )
        self.layout_principal.addWidget(self.campo_busca)

        self.lista_croquis: QListWidget = QListWidget()
        self.lista_croquis.setStyleSheet(
            "border: 1px solid #dee2e6; border-radius: 4px; background-color: #ffffff;"
        )
        self.layout_principal.addWidget(self.lista_croquis)

        self.layout_botoes: QHBoxLayout = QHBoxLayout()
        self.btn_cancelar: QPushButton = QPushButton("Cancelar")
        self.btn_confirmar: QPushButton = QPushButton("Confirmar")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.setEnabled(False)
        self.btn_confirmar.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
            QPushButton:hover:enabled {
                background-color: #0b5ed7;
            }
        """)

        self.layout_botoes.addStretch()
        self.layout_botoes.addWidget(self.btn_cancelar)
        self.layout_botoes.addWidget(self.btn_confirmar)
        self.layout_principal.addLayout(self.layout_botoes)

        # Conexões
        self.campo_busca.textChanged.connect(self.filtrar_lista)
        self.lista_croquis.itemSelectionChanged.connect(self.ao_selecionar)
        self.lista_croquis.itemDoubleClicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_confirmar.clicked.connect(self.accept)

        self.carregar_indice()

    def carregar_indice(self) -> None:
        """
        Carrega a lista de todos os croquis disponíveis a partir da pasta database no storage.
        Lê o nome de cada croqui diretamente de seu respectivo croqui.yaml e pré-seleciona o primeiro item.
        """
        if not self.storage:
            return

        caminho_repo = self.storage.obter_caminho_base_repo()
        caminho_database = caminho_repo / "database"
        if not caminho_database.is_dir():
            return

        self.lista_croquis.clear()
        pastas = sorted([p for p in caminho_database.iterdir() if p.is_dir()])

        for pasta in pastas:
            id_croqui = pasta.name
            nome = id_croqui

            croqui_yaml = pasta / "croqui.yaml"
            if croqui_yaml.is_file():
                try:
                    dados = carregar_yaml(croqui_yaml.read_text(encoding="utf-8"))
                    if isinstance(dados, dict) and "nome" in dados:
                        nome = dados["nome"]
                except Exception:
                    pass

            texto = f"{nome} ({id_croqui})"
            self.lista_croquis.addItem(texto)

        self._selecionar_primeiro_visivel()

    def _selecionar_primeiro_visivel(self) -> None:
        """Seleciona automaticamente o primeiro item visível da lista ou limpa a seleção se vazia."""
        for i in range(self.lista_croquis.count()):
            if not self.lista_croquis.isRowHidden(i):
                self.lista_croquis.setCurrentRow(i)
                self.ao_selecionar()
                return

        self.lista_croquis.setCurrentRow(-1)
        self.lista_croquis.clearSelection()
        self.ao_selecionar()

    def filtrar_lista(self, texto: str) -> None:
        """
        Filtra os itens da lista baseado no texto de busca e seleciona o primeiro item visível.
        """
        termo = texto.lower()
        for i in range(self.lista_croquis.count()):
            item = self.lista_croquis.item(i)
            ocultar = termo not in item.text().lower()
            self.lista_croquis.setRowHidden(i, ocultar)
        self._selecionar_primeiro_visivel()

    def ao_selecionar(self) -> None:
        """
        Habilita/desabilita o botão confirmar baseado na existência de um item visível selecionado.
        """
        self.btn_confirmar.setEnabled(self.obter_id_selecionado() is not None)

    def obter_id_selecionado(self) -> str | None:
        """
        Extrai o ID do texto do item selecionado e visível.
        Exemplo: "Nome (id)" -> "id"
        """
        linha = self.lista_croquis.currentRow()
        if linha < 0 or self.lista_croquis.isRowHidden(linha):
            return None

        item = self.lista_croquis.item(linha)
        texto = item.text()
        return texto.split("(")[-1][:-1]

    def accept(self) -> None:
        self.id_selecionado = self.obter_id_selecionado()
        if self.id_selecionado:
            super().accept()
