import unittest
from unittest.mock import MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from editar_mapas import logic_convert_box_to_circle, DrawingScene

class TestEditarMapas(unittest.TestCase):
    def test_convert_box_to_circle_square(self):
        # Box 100x100 -> Raio 50
        pt_dict = {
            'id': 'test',
            'label': 'Test Label',
            'box': {'x': 500, 'y': 500, 'comprimento': 100, 'largura': 100}
        }
        expected = {
            'id': 'test',
            'label': 'Test Label',
            'circular': {'x': 500, 'y': 500, 'raio': 50}
        }
        self.assertEqual(logic_convert_box_to_circle(pt_dict), expected)

    def test_convert_box_to_circle_rect(self):
        # Box 100x80 -> Média 90 -> Raio 45
        pt_dict = {
            'id': '1',
            'box': {'x': 10, 'y': 20, 'comprimento': 100, 'largura': 80}
        }
        result = logic_convert_box_to_circle(pt_dict)
        self.assertEqual(result['circular']['raio'], 45)
        self.assertEqual(result['circular']['x'], 10)
        self.assertEqual(result['circular']['y'], 20)

    def test_convert_box_to_circle_rounding(self):
        # Box 10x11 -> Média 10.5 -> Raio 5.25 -> round 5
        pt_dict = {
            'box': {'x': 0, 'y': 0, 'comprimento': 10, 'largura': 11}
        }
        result = logic_convert_box_to_circle(pt_dict)
        self.assertEqual(result['circular']['raio'], 5)

    def test_invalid_input(self):
        self.assertIsNone(logic_convert_box_to_circle({}))
        self.assertIsNone(logic_convert_box_to_circle({'circular': {}}))

class TestDrawingScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Necessário para instanciar objetos QGraphicsItem
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_convert_mode_interaction_flow(self):
        """Simula o fluxo de seleção por área no modo de conversão para garantir que não há crashes."""
        mock_win = MagicMock()
        mock_win.convert_mode = True
        mock_win.drawing_mode = False
        mock_win.selection_origin = None
        
        scene = DrawingScene(mock_win)
        
        # 1. Simula Mouse Press (Início da seleção)
        event_press = MagicMock()
        event_press.button.return_value = Qt.MouseButton.LeftButton
        event_press.scenePos.return_value = QPointF(100, 100)
        scene.mousePressEvent(event_press)
        
        self.assertIsNotNone(scene.selection_item, "Item de seleção deve ser criado")
        self.assertEqual(mock_win.selection_origin, QPointF(100, 100))
        
        # 2. Simula Mouse Move (Arrastando)
        event_move = MagicMock()
        event_move.scenePos.return_value = QPointF(200, 250)
        scene.mouseMoveEvent(event_move)
        
        rect = scene.selection_item.rect()
        self.assertEqual(rect.width(), 100)
        self.assertEqual(rect.height(), 150)
        
        # 3. Simula Mouse Release (Fim da seleção)
        event_release = MagicMock()
        scene.mouseReleaseEvent(event_release)
        
        self.assertIsNone(scene.selection_item, "Item de seleção deve ser removido da cena")
        self.assertIsNone(mock_win.selection_origin, "Origin deve ser resetado")
        mock_win.finish_conversion_area.assert_called_once()
        
    def test_drawing_mode_interaction(self):
        """Garante que o modo de desenho de área livre continua funcionando sem interferência."""
        mock_win = MagicMock()
        mock_win.convert_mode = False
        mock_win.drawing_mode = True
        
        scene = DrawingScene(mock_win)
        
        event = MagicMock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.scenePos.return_value = QPointF(50, 50)
        
        scene.mousePressEvent(event)
        mock_win.add_drawing_point.assert_called_with(QPointF(50, 50))


if __name__ == '__main__':
    unittest.main()
