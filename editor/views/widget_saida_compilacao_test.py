# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import Qt
from editor.views.widget_saida_compilacao import WidgetSaidaCompilacao

def test_widget_saida_compilacao_instanciacao(qtbot):
    parent = QMainWindow()
    widget = WidgetSaidaCompilacao(parent)
    qtbot.addWidget(parent)
    
    assert widget.windowTitle() == "Saída de Compilação"
    assert widget.widget() is not None
    assert widget.texto_saida.isReadOnly() is True

def test_widget_exibir_ocultar(qtbot):
    parent = QMainWindow()
    widget = WidgetSaidaCompilacao(parent)
    parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, widget)
    qtbot.addWidget(parent)
    parent.show()
    
    widget.ocultar_painel()
    assert widget.isVisible() is False
    
    widget.exibir_painel()
    assert widget.isVisible() is True
    
    widget.ocultar_painel()
    assert widget.isVisible() is False

def test_widget_atualizar_texto(qtbot):
    parent = QMainWindow()
    widget = WidgetSaidaCompilacao(parent)
    qtbot.addWidget(parent)
    
    html = '<span style="color: #D32F2F;">Erro: falha grave</span>'
    widget.atualizar_texto(html)
    
    # O toHtml() do Qt adiciona tags extra, então verificamos se o texto bruto está lá e a formatação básica.
    assert "Erro: falha grave" in widget.texto_saida.toPlainText()
    assert "#d32f2f" in widget.texto_saida.toHtml().lower() or "color" in widget.texto_saida.toHtml().lower()
