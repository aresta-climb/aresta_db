# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from enum import Enum
from typing import Optional, Sequence
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QWidget,
)
from PySide6.QtCore import Qt


class DecisaoConflito(Enum):
    """Opções de decisão para resolução de conflitos de sincronização."""
    MANTER_LOCAL = "manter_local"
    USAR_REMOTO = "usar_remoto"
    CANCELAR = "cancelar"


class DialogoConflitoSincronizacao(QDialog):
    """
    Diálogo para exibição e resolução de conflitos na sincronização remota de Pull Requests.
    Permite escolher entre manter as alterações locais, adotar a versão do GitHub ou cancelar.
    """

    def __init__(
        self,
        id_croqui: str,
        nome_branch: str,
        arquivos_conflito: Sequence[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.id_croqui: str = id_croqui
        self.nome_branch: str = nome_branch
        self.arquivos_conflito: list[str] = list(arquivos_conflito)
        self._decisao: DecisaoConflito = DecisaoConflito.CANCELAR

        self.setWindowTitle(f"Conflito de Sincronização - {id_croqui}")
        self.setMinimumWidth(520)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel("Conflito de Sincronização Remota")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #212529;")
        layout.addWidget(titulo)

        descricao = QLabel(
            "Foram detectadas alterações na Pull Request do GitHub que conflitam diretamente "
            "com as suas edições locais deste croqui. Veja os arquivos afetados abaixo:"
        )
        descricao.setWordWrap(True)
        descricao.setStyleSheet("color: #495057; font-size: 13px; line-height: 1.4;")
        layout.addWidget(descricao)

        self.lista_arquivos = QListWidget()
        self.lista_arquivos.setMaximumHeight(140)
        self.lista_arquivos.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px;
                font-family: monospace;
                font-size: 12px;
                color: #c92a2a;
            }
        """)
        for arq in self.arquivos_conflito:
            self.lista_arquivos.addItem(arq)
        layout.addWidget(self.lista_arquivos)

        instrucoes = QLabel(
            "Escolha como deseja resolver os conflitos. A sua decisão gerará um commit de "
            "merge preservando todo o histórico no Git sem criar arquivos temporários órfãos:"
        )
        instrucoes.setWordWrap(True)
        instrucoes.setStyleSheet("color: #495057; font-size: 12px;")
        layout.addWidget(instrucoes)

        # Botões de Ação
        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(10)

        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f5;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.botao_cancelar.clicked.connect(self._on_cancelar)
        layout_botoes.addWidget(self.botao_cancelar)

        layout_botoes.addStretch()

        self.botao_usar_remoto = QPushButton("Usar Versão do GitHub")
        self.botao_usar_remoto.setStyleSheet("""
            QPushButton {
                background-color: #1c7ed6;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 14px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1971c2;
            }
        """)
        self.botao_usar_remoto.clicked.connect(self._on_usar_remoto)
        layout_botoes.addWidget(self.botao_usar_remoto)

        self.botao_manter_local = QPushButton("Manter Minha Versão Local")
        self.botao_manter_local.setStyleSheet("""
            QPushButton {
                background-color: #2b8a3e;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 14px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #237032;
            }
        """)
        self.botao_manter_local.clicked.connect(self._on_manter_local)
        layout_botoes.addWidget(self.botao_manter_local)

        layout.addLayout(layout_botoes)

    def _on_manter_local(self) -> None:
        self._decisao = DecisaoConflito.MANTER_LOCAL
        self.accept()

    def _on_usar_remoto(self) -> None:
        self._decisao = DecisaoConflito.USAR_REMOTO
        self.accept()

    def _on_cancelar(self) -> None:
        self._decisao = DecisaoConflito.CANCELAR
        self.reject()

    def obter_decisao(self) -> DecisaoConflito:
        return self._decisao

    def obter_texto_arquivos(self) -> str:
        itens = [self.lista_arquivos.item(i).text() for i in range(self.lista_arquivos.count())]
        return "\n".join(itens)
