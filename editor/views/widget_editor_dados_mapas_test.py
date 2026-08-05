# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import sys
from PyQt6.QtWidgets import QApplication, QPushButton
from aresta_api.proto.generated.croqui_pb2 import Pico, ArquivoMapas, ColecaoDeMapas, Mapa
from editor.views.widget_editor_dados import WidgetFormularioPadrao
from unittest.mock import MagicMock

class MockController:
    def alterar_primitivo(self, msg, campo_nome, valor_antigo, valor_novo):
        pass
    def alterar_oneof(self, msg, oneof_nome, nome_antigo, valor_antigo, nome_novo, valor_novo):
        pass

def test_pico_renders_mapas_gerais_inline(qtbot):
    pico = Pico()
    pico.nome = "Gruta da Lapinha"
    pico.mapas_gerais.conteudo.mapas.add().caminho_imagem_mapa = "mapa1.webp"
    
    controller = MockController()
    mock_model = MagicMock()
    widget = WidgetFormularioPadrao(model=mock_model, controller=controller)
    mock_node = MagicMock()
    mock_node.message = pico
    mock_node.field = None
    widget.load_node(mock_node)
    
    # We must find the collapsible widget or the label for Mapas gerais
    from PyQt6.QtWidgets import QLabel
    found_mapas_gerais = False
    for label in widget.findChildren(QLabel):
        if "Mapas gerais" in label.text() or "Mapas Gerais" in label.text():
            found_mapas_gerais = True
            break
            
    assert found_mapas_gerais, "Label 'Mapas gerais' not found inside Pico, so the field is being skipped"

def test_verify_mapas_gerais_path(qtbot, monkeypatch):
    pico = Pico()
    pico.nome = "Gruta da Lapinha"
    pico.mapas_gerais.conteudo.mapas.add().caminho_imagem_mapa = "mapa1.webp"
    
    class MockController2:
        def __init__(self):
            self.last_path = None
        def set_contexto(self, path):
            self.last_path = path
    
    controller = MockController2()
    mock_model = MagicMock()
    widget = WidgetFormularioPadrao(model=mock_model, controller=controller)
    mock_node = MagicMock()
    mock_node.message = pico
    mock_node.field = None
    
    # We must patch get_node_path
    import editor.views.widget_editor_dados
    monkeypatch.setattr(editor.views.widget_editor_dados, "get_node_path", lambda n: "expando:picos/item:0")
    
    widget.load_node(mock_node)
    
    from editor.views.widget_editor_dados import WidgetColapsavel
    for colapsavel in widget.findChildren(WidgetColapsavel):
        colapsavel.toggle_button.setChecked(True) # forces lazy loading if closed
    
    for btn in widget.findChildren(QPushButton):
        print("BTN:", btn.text())
        if btn.text() == "Abrir no Editor de Mapas":
            btn.click()
            print("PATH EMITTED:", controller.last_path)
            break
            
    assert controller.last_path is not None, "Button was not clicked or path not emitted"
            
