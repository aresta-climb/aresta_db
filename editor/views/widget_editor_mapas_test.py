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


class TestWidgetEditorMapas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_gerar_sidebar_de_croqui_model(self):
        """[TDD] Verifica a geração da sidebar a partir de um CroquiModel mockado (100% coverage desejado)."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.croqui_model import CroquiModel
        
        # Setup do modelo mock
        croqui_msg = croqui_pb2.Croqui()
        pico = croqui_msg.picos.add()
        pico.nome = "pico1"
        setor_wrapper = pico.setores_ou_grupos.add().setor.conteudo
        setor_wrapper.nome = "setor1"
        
        mapa1 = setor_wrapper.mapas.add()
        mapa1.caminho_imagem_mapa = "mapa1.webp"
        mapa2 = setor_wrapper.mapas.add()
        mapa2.caminho_imagem_mapa = "mapa2.webp"
        
        modelo = CroquiModel(croqui_msg)
        
        widget = WidgetEditorMapas(standalone=False)
        widget.carregar_de_modelo(modelo)
        
        # A sidebar deve conter 2 itens (mapa1 e mapa2)
        self.assertEqual(widget.list_widget.count(), 2)
        
        # O texto de exibição pode ser o caminho da imagem por enquanto
        item1 = widget.list_widget.item(0)
        self.assertIn("mapa1", item1.text())
        
        item2 = widget.list_widget.item(1)
        self.assertIn("mapa2", item2.text())

    def test_mover_poi_invoca_controller(self):
        """[TDD] Garante que interações com o WidgetEditorMapas invocam os métodos do CroquiController."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.croqui_model import CroquiModel
        from unittest.mock import MagicMock
        
        croqui_msg = croqui_pb2.Croqui()
        pico = croqui_msg.picos.add()
        pico.nome = "pico1"
        setor_wrapper = pico.setores_ou_grupos.add().setor.conteudo
        setor_wrapper.nome = "setor1"
        
        mapa = setor_wrapper.mapas.add()
        poi = mapa.pontos_de_interesse.add()
        poi.circular.x = 10
        poi.circular.y = 10
        poi.circular.raio = 5
        
        modelo = CroquiModel(croqui_msg)
        controller = MagicMock()
        
        widget = WidgetEditorMapas(standalone=False)
        widget.controller = controller
        widget.carregar_de_modelo(modelo)
        
        # Simula selecao para gerar a cena e os itens_bb
        widget.list_widget.setCurrentRow(0)
        
        # Obtem a cena e o item POI
        dados = widget.dados_atuais
        
        # Simula a criacao que deve ocorrer no futuro pelo novo MVC:
        from editor.views.widget_editor_mapas import ItemBoundingCircular
        item_visual = ItemBoundingCircular(
            pt_dict={'circular': {'x': 10, 'y': 10, 'raio': 5}},
            callback_deletar=lambda x: None
        )
        dados['cena'].addItem(item_visual)
        dados['itens_bb'].append(item_visual)
        
        from editor.views.widget_editor_mapas import registrar_movimento_final
        estado_inicial = {'circular': {'x': 10, 'y': 10, 'raio': 5}}
        item_visual.setPos(20, 20)
        
        # Simula o que o mouseReleaseEvent faria
        registrar_movimento_final(item_visual, estado_inicial)
        
        controller.alterar_repeated_item.assert_called_once()
        args = controller.alterar_repeated_item.call_args[0]
        # map_msg, "pontos_de_interesse", indice, valor_antigo, valor_novo
        self.assertEqual(args[0], mapa)
        self.assertEqual(args[1], "pontos_de_interesse")

if __name__ == '__main__':
    unittest.main()


def test_ao_selecionar_arquivo_carrega_imagem_e_pois(qtbot, tmp_path):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from PyQt6.QtWidgets import QListWidgetItem
    from PyQt6.QtCore import Qt
    import os
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Criar um mock para img path
    caminho_db = tmp_path / 'database'
    caminho_db.mkdir()
    img_path = caminho_db / 'teste.png'
    with open(img_path, 'wb') as f_img:
        f_img.write(b'fake_image_data')
    
    widget.caminho_db = str(caminho_db)
    
    # Prepara dados
    mapa_msg = croqui_pb2.Mapa()
    mapa_msg.caminho_imagem_mapa = 'teste.png'
    pt = mapa_msg.pontos_de_interesse.add()
    pt.circular.x = 100
    pt.circular.y = 100
    pt.circular.raio = 10
    
    chave = ('Pico', 'Setor', 0)
    widget.dados_arquivos[chave] = {
        'mapa_msg': mapa_msg
    }
    
    item = QListWidgetItem('Teste')
    item.setData(Qt.ItemDataRole.UserRole, chave)
    widget.list_widget.addItem(item)
    
    # Acao
    widget.ao_selecionar_arquivo(0)
    
    # Verificacoes
    dados = widget.dados_arquivos[chave]
    assert 'cena' in dados
    assert len(dados['itens_bb']) == 1
    
    # A cena deve ter os itens adicionados: a imagem (QGraphicsPixmapItem) e o circulo (ItemBoundingCircular)
    items = dados['cena'].items()
    assert len(items) >= 2
