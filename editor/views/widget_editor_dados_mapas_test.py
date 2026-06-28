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
