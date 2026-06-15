# Copyright (C) 2026 ARESTA
import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from editor.views.widget_editor_mapas import CenaDesenho, WidgetEditorMapas

class TestCenaDesenho(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_fluxo_interacao_modo_conversao(self):
        """Simula o fluxo de seleção por área no modo de conversão."""
        mock_widget = MagicMock(spec=WidgetEditorMapas)
        mock_widget.convert_mode = True
        mock_widget.drawing_mode = False
        mock_widget.selection_origin = None
        
        cena = CenaDesenho(mock_widget)
        
        # 1. Mouse Press
        evento_press = MagicMock()
        evento_press.button.return_value = Qt.MouseButton.LeftButton
        evento_press.scenePos.return_value = QPointF(100, 100)
        cena.mousePressEvent(evento_press)
        
        self.assertIsNotNone(cena.item_selecao)
        self.assertEqual(mock_widget.selection_origin, QPointF(100, 100))
        
        # 2. Mouse Move
        evento_move = MagicMock()
        evento_move.scenePos.return_value = QPointF(200, 250)
        cena.mouseMoveEvent(evento_move)
        
        rect = cena.item_selecao.rect()
        self.assertEqual(rect.width(), 100)
        self.assertEqual(rect.height(), 150)
        
        # 3. Mouse Release
        evento_release = MagicMock()
        cena.mouseReleaseEvent(evento_release)
        
        self.assertIsNone(cena.item_selecao)
        self.assertIsNone(mock_widget.selection_origin)
        mock_widget.finish_conversion_area.assert_called_once()

    def test_interacao_modo_desenho(self):
        """Garante que o modo de desenho de área livre funciona."""
        mock_widget = MagicMock(spec=WidgetEditorMapas)
        mock_widget.convert_mode = False
        mock_widget.drawing_mode = True
        
        cena = CenaDesenho(mock_widget)
        
        evento = MagicMock()
        evento.button.return_value = Qt.MouseButton.LeftButton
        evento.scenePos.return_value = QPointF(50, 50)
        
        cena.mousePressEvent(evento)
        mock_widget.add_drawing_point.assert_called_with(QPointF(50, 50))


def test_slider_bulk_vazio_reseta_para_zero(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Testa para circular
    widget.slider_circ.setValue(50)
    widget.ao_pressionar_slider_bulk('circular')
    widget.ao_soltar_slider_bulk('circular')
    
    assert widget.slider_circ.value() == 0
    assert widget.label_circ.text() == "0%"
    
    # Testa para box/retângulo
    widget.slider_box.setValue(50)
    widget.ao_pressionar_slider_bulk('box')
    widget.ao_soltar_slider_bulk('box')
    
    assert widget.slider_box.value() == 0
    assert widget.label_box.text() == "0%"
