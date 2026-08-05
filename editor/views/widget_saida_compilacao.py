# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

from PyQt6.QtWidgets import QDockWidget, QTextEdit, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

class WidgetSaidaCompilacao(QDockWidget):
    """Componente de UI passivo (View) para mostrar a saída da compilação."""
    
    def __init__(self, parent=None):
        super().__init__("Saída de Compilação", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        
        self.conteudo = QWidget()
        layout = QVBoxLayout(self.conteudo)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.texto_saida = QTextEdit()
        self.texto_saida.setReadOnly(True)
        # Fundo escuro, fonte monoespaçada
        self.texto_saida.setStyleSheet(
            "font-family: Consolas, monospace; "
            "background-color: #ffffff; "
            "color: #333333; "
            "font-size: 13px;"
        )
        
        layout.addWidget(self.texto_saida)
        self.setWidget(self.conteudo)

    def atualizar_texto(self, html: str):
        """Atualiza o conteúdo do texto com a formatação já pronta vinda do controller."""
        self.texto_saida.setHtml(html)

    def exibir_painel(self):
        """Exibe e foca o painel para chamar a atenção do usuário."""
        self.show()
        self.raise_()

    def ocultar_painel(self):
        """Oculta o painel."""
        self.hide()
