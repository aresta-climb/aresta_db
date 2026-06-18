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

def test_configurar_lista_mapas_todos_niveis(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PyQt6.QtCore import Qt
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Mock do controller e model
    mock_controller = MagicMock()
    mock_model = MagicMock()
    mock_controller.model = mock_model
    widget.mapas_controller = mock_controller
    
    # Construção de um Croqui real para testar campos
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()
    
    # Grupo com Mapa
    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Grupo Teste"
    mapa_grupo = sg_grupo.grupo.conteudo.mapas.add()
    mapa_grupo.caminho_imagem_mapa = "mapa_grupo.webp"
    
    # Setor dentro do Grupo com Mapa
    subsetor = sg_grupo.grupo.conteudo.setores.add()
    subsetor.conteudo.nome = "Sub-Setor Teste"
    mapa_subsetor = subsetor.conteudo.mapas.add()
    mapa_subsetor.caminho_imagem_mapa = "mapa_subsetor.webp"
    
    # Setor raiz com Mapa
    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Setor Teste"
    mapa_setor = sg_setor.setor.conteudo.mapas.add()
    mapa_setor.caminho_imagem_mapa = "mapa_setor.webp"
    
    # Retorna o proxy como o modelo real faria
    mock_model.obter_croqui_readonly.return_value = ReadOnlyProxy(croqui)
    
    # Executa o método
    widget.configurar_lista_mapas()
    
    # Verifica a lista
    assert widget.list_widget.count() == 3
    
    # Mapa do Grupo
    item_grupo = widget.list_widget.item(0)
    assert item_grupo.text() == "mapa_grupo.webp"
    assert item_grupo.data(Qt.ItemDataRole.UserRole) == ('grupo', 0, 0, 0)
    
    # Mapa do Sub-Setor (dentro do Grupo)
    item_subsetor = widget.list_widget.item(1)
    assert item_subsetor.text() == "mapa_subsetor.webp"
    assert item_subsetor.data(Qt.ItemDataRole.UserRole) == ('subsetor', 0, 0, 0, 0)
    
    # Mapa do Setor
    item_setor = widget.list_widget.item(2)
    assert item_setor.text() == "mapa_setor.webp"
    assert item_setor.data(Qt.ItemDataRole.UserRole) == ('setor', 0, 1, 0)


def test_selecao_mantida_apos_atualizacao(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QListWidgetItem
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Mock do controller e model
    mock_controller = MagicMock()
    mock_model = MagicMock()
    
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    mapa = sg.setor.conteudo.mapas.add()
    mapa.caminho_imagem_mapa = "mapa.png"
    
    mock_model.obter_croqui_readonly.return_value = ReadOnlyProxy(croqui)
    mock_controller.model = mock_model
    widget.mapas_controller = mock_controller
    
    # Preenche manualmente a lista e seleciona
    item = QListWidgetItem("mapa.png")
    item.setData(Qt.ItemDataRole.UserRole, ('setor', 0, 0, 0))
    widget.list_widget.addItem(item)
    widget.list_widget.setCurrentItem(item)
    
    # Chama _atualizar_lista_mapas. Isso deve recriar os itens, mas preservar a seleção.
    widget._atualizar_lista_mapas()
    
    assert widget.list_widget.count() == 1
    current = widget.list_widget.currentItem()
    assert current is not None
    assert current.data(Qt.ItemDataRole.UserRole) == ('setor', 0, 0, 0)


def test_zoom_nao_reseta_ao_alterar_pontos(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas, CenaDesenho
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QTransform
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Define estado atual
    msg_mapa = croqui_pb2.Mapa()
    poi = msg_mapa.pontos_de_interesse.add()
    poi.id = "p1"
    
    widget.dados_atuais = {
        'cena': CenaDesenho(widget),
        'itens_bb': []
    }
    widget.msg_mapa_proxy = msg_mapa
    
    # Configura zoom artificial
    transform = QTransform().scale(2.0, 2.0)
    widget.visualizador.setTransform(transform)
    
    # Simula chamada interna de update sem resetar zoom
    widget._renderizar_mapa(reset_zoom=False)
    
    assert widget.visualizador.transform().m11() == 2.0
    assert widget.visualizador.transform().m22() == 2.0

def test_renomear_poi_no_mapa(qtbot, mocker):
    from editor.views.widget_editor_mapas import WidgetEditorMapas, BaseItemPOI
    from PyQt6.QtWidgets import QDialog, QMenu
    from PyQt6.QtGui import QAction
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mock_controller = MagicMock()
    widget.mapas_controller = mock_controller
    
    mapa_proto = croqui_pb2.Mapa()
    poi = mapa_proto.pontos_de_interesse.add()
    poi.id = "poi_antigo"
    poi.label = "Label Antigo"
    
    widget.msg_mapa_proxy = ReadOnlyProxy(mapa_proto)
    
    class FakeScene:
        def __init__(self, editor):
            self.widget_editor = editor

    class FakeItem(BaseItemPOI):
        def __init__(self, pt_dict):
            super().__init__()
            self.pt_dict = pt_dict
            self.item_texto = MagicMock()
            self._scene = FakeScene(widget)
        def scene(self):
            return self._scene
        def setToolTip(self, text):
            pass

    item = FakeItem({'id': 'poi_antigo', 'label': 'Label Antigo'})
    widget.itens_poi = {0: item}
    widget.dados_arquivos = {"chave1": {"itens_bb": [item]}}
    
    # Mock do dialogo
    mocker.patch('editor.views.widget_editor_mapas.DialogoEdicaoPOI.exec', return_value=QDialog.DialogCode.Accepted)
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

def test_deletar_poi_com_tecla_delete(qtbot, mocker):
    from editor.views.widget_editor_mapas import WidgetEditorMapas, ItemBoundingBox
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from PyQt6.QtCore import Qt

    # Configuração
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa_proto = croqui_pb2.Mapa()
    poi = mapa_proto.pontos_de_interesse.add()
    poi.id = "poi_1"
    poi.label = "POI 1"
    poi.box.x = 10
    poi.box.y = 10
    poi.box.comprimento = 20
    poi.box.largura = 20
    
    widget.set_mapa_atual(ReadOnlyProxy(mapa_proto))
    
    # Pegar o item renderizado
    assert len(widget.itens_poi) == 1
    item = list(widget.itens_poi.values())[0]
    
    # Mock do callback_deletar
    item.callback_deletar = mocker.MagicMock()
    
    # Selecionar o item na cena
    item.setSelected(True)
    
    # Simular pressionamento da tecla Delete na cena (ou no view)
    qtbot.keyClick(widget.visualizador.viewport(), Qt.Key.Key_Delete)
    
    # Verificar se o callback foi chamado
    item.callback_deletar.assert_called_once_with(item)

def test_configurar_lista_mapas_todos_niveis(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PyQt6.QtCore import Qt
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Mock do controller e model
    mock_controller = MagicMock()
    mock_model = MagicMock()
    mock_controller.model = mock_model
    widget.mapas_controller = mock_controller
    
    # Construção de um Croqui real para testar campos
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()
    
    # Grupo com Mapa
    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Grupo Teste"
    mapa_grupo = sg_grupo.grupo.conteudo.mapas.add()
    mapa_grupo.caminho_imagem_mapa = "mapa_grupo.webp"
    
    # Setor dentro do Grupo com Mapa
    subsetor = sg_grupo.grupo.conteudo.setores.add()
    subsetor.conteudo.nome = "Sub-Setor Teste"
    mapa_subsetor = subsetor.conteudo.mapas.add()
    mapa_subsetor.caminho_imagem_mapa = "mapa_subsetor.webp"
    
    # Setor raiz com Mapa
    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Setor Teste"
    mapa_setor = sg_setor.setor.conteudo.mapas.add()
    mapa_setor.caminho_imagem_mapa = "mapa_setor.webp"
    
    # Retorna o proxy como o modelo real faria
    mock_model.obter_croqui_readonly.return_value = ReadOnlyProxy(croqui)
    
    # Executa o método
    widget.configurar_lista_mapas()
    
    # Verifica a lista
    assert widget.list_widget.count() == 3
    
    # Mapa do Grupo
    item_grupo = widget.list_widget.item(0)
    assert item_grupo.text() == "mapa_grupo.webp"
    assert item_grupo.data(Qt.ItemDataRole.UserRole) == ('grupo', 0, 0, 0)
    
    # Mapa do Sub-Setor (dentro do Grupo)
    item_subsetor = widget.list_widget.item(1)
    assert item_subsetor.text() == "mapa_subsetor.webp"
    assert item_subsetor.data(Qt.ItemDataRole.UserRole) == ('subsetor', 0, 0, 0, 0)
    
    # Mapa do Setor
    item_setor = widget.list_widget.item(2)
    assert item_setor.text() == "mapa_setor.webp"
    assert item_setor.data(Qt.ItemDataRole.UserRole) == ('setor', 0, 1, 0)


def test_selecao_mantida_apos_atualizacao(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QListWidgetItem
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Mock do controller e model
    mock_controller = MagicMock()
    mock_model = MagicMock()
    
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    mapa = sg.setor.conteudo.mapas.add()
    mapa.caminho_imagem_mapa = "mapa.png"
    
    mock_model.obter_croqui_readonly.return_value = ReadOnlyProxy(croqui)
    mock_controller.model = mock_model
    widget.mapas_controller = mock_controller
    
    # Preenche manualmente a lista e seleciona
    item = QListWidgetItem("mapa.png")
    item.setData(Qt.ItemDataRole.UserRole, ('setor', 0, 0, 0))
    widget.list_widget.addItem(item)
    widget.list_widget.setCurrentItem(item)
    
    # Chama _atualizar_lista_mapas. Isso deve recriar os itens, mas preservar a seleção.
    widget._atualizar_lista_mapas()
    
    assert widget.list_widget.count() == 1
    current = widget.list_widget.currentItem()
    assert current is not None
    assert current.data(Qt.ItemDataRole.UserRole) == ('setor', 0, 0, 0)


def test_zoom_nao_reseta_ao_alterar_pontos(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas, CenaDesenho
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QTransform
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Define estado atual
    msg_mapa = croqui_pb2.Mapa()
    poi = msg_mapa.pontos_de_interesse.add()
    poi.id = "p1"
    
    widget.dados_atuais = {
        'cena': CenaDesenho(widget),
        'itens_bb': []
    }
    widget.msg_mapa_proxy = msg_mapa
    
    # Configura zoom artificial
    transform = QTransform().scale(2.0, 2.0)
    widget.visualizador.setTransform(transform)
    
    # Simula chamada interna de update sem resetar zoom
    widget._renderizar_mapa(reset_zoom=False)
    
    assert widget.visualizador.transform().m11() == 2.0
    assert widget.visualizador.transform().m22() == 2.0

def test_renomear_poi_no_mapa(qtbot, mocker):
    from editor.views.widget_editor_mapas import WidgetEditorMapas, BaseItemPOI
    from PyQt6.QtWidgets import QDialog, QMenu
    from PyQt6.QtGui import QAction
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mock_controller = MagicMock()
    widget.mapas_controller = mock_controller
    
    mapa_proto = croqui_pb2.Mapa()
    poi = mapa_proto.pontos_de_interesse.add()
    poi.id = "poi_antigo"
    poi.label = "Label Antigo"
    
    widget.msg_mapa_proxy = ReadOnlyProxy(mapa_proto)
    
    class FakeScene:
        def __init__(self, editor):
            self.widget_editor = editor

    class FakeItem(BaseItemPOI):
        def __init__(self, pt_dict):
            super().__init__()
            self.pt_dict = pt_dict
            self.item_texto = MagicMock()
            self._scene = FakeScene(widget)
        def scene(self):
            return self._scene
        def setToolTip(self, text):
            pass
        def obter_dict_atualizado(self):
            return self.pt_dict.copy()

    item = FakeItem({'id': 'poi_antigo', 'label': 'Label Antigo'})
    widget.itens_poi = {0: item}
    widget.dados_arquivos = {"chave1": {"itens_bb": [item]}}
    
    # Mock do dialogo
    mocker.patch('editor.views.widget_editor_mapas.DialogoEdicaoPOI.exec', return_value=QDialog.DialogCode.Accepted)
    mocker.patch('editor.views.widget_editor_mapas.DialogoEdicaoPOI.obter_valores', return_value=("poi_novo", "Label Novo"))
    
    # Simulamos o QMenu para retornar a acao de renomear
    def fake_exec(self, pos):
        for act in self.actions():
            if act.text() == "Renomear Ponto de Interesse":
                return act
        return None
        
    mocker.patch('PyQt6.QtWidgets.QMenu.exec', new=fake_exec)
    
    evento = MagicMock()
    evento.screenPos.return_value = None
    
    item.tratar_menu_contexto(evento, None)
    
    # Verifica se mover_poi foi chamado com o novo id
    assert mock_controller.mover_poi.called, "mover_poi deveria ter sido chamado ao renomear o item"
    args = mock_controller.mover_poi.call_args[0]
    assert args[1] == 0  # index do poi
    assert args[3].id == "poi_novo"  # o novo poi gerado deve ter o id atualizado


def test_poi_snapping_to_integers():
    from editor.views.widget_editor_mapas import ItemBoundingBox, ItemBoundingCircular, AlcaVertice, ItemBoundingAreaLivre
    from PyQt6.QtCore import QPointF
    from PyQt6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem
    
    cena = QGraphicsScene()
    
    # Test ItemBoundingBox
    box_dict = {'box': {'x': 100, 'y': 100, 'comprimento': 50, 'largura': 50}}
    box = ItemBoundingBox(box_dict, lambda: None)
    cena.addItem(box)
    
    mudanca = QGraphicsRectItem.GraphicsItemChange.ItemPositionChange
    novo_valor = QPointF(10.4, 20.6)
    snapped_valor = box.itemChange(mudanca, novo_valor)
    
    assert snapped_valor.x() == 10.0
    assert snapped_valor.y() == 21.0
    
    # Test ItemBoundingCircular
    circ_dict = {'circular': {'x': 100, 'y': 100, 'raio': 25}}
    circ = ItemBoundingCircular(circ_dict, lambda: None)
    cena.addItem(circ)
    
    mudanca_circ = QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange
    novo_valor_circ = QPointF(10.5, 20.4)
    snapped_valor_circ = circ.itemChange(mudanca_circ, novo_valor_circ)
    
    assert snapped_valor_circ.x() == 10.0
    assert snapped_valor_circ.y() == 20.0
    
    # Test Polygon (Area Livre)
    poly_dict = {'area_livre': {'coordenadas': [0, 0, 10, 0, 10, 10]}}
    poly = ItemBoundingAreaLivre(poly_dict, lambda x: None, lambda y: None)
    cena.addItem(poly)
    
    mudanca_poly = QGraphicsPolygonItem.GraphicsItemChange.ItemPositionChange
    snapped_valor_poly = poly.itemChange(mudanca_poly, QPointF(5.9, 6.1))
    
    assert snapped_valor_poly.x() == 6.0
    assert snapped_valor_poly.y() == 6.0

class TestWidgetEditorMapasLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def test_lista_mapas_cresce_ate_conteudo(self):
        from PyQt6.QtWidgets import QSizePolicy, QAbstractScrollArea
        from editor.views.widget_editor_mapas import WidgetEditorMapas
        
        widget = WidgetEditorMapas()
        
        # O list_widget deve ter politica vertical Maximum (para não crescer infinitamente)
        self.assertEqual(widget.list_widget.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Maximum)
        
        # E deve ter o size adjust policy configurado para ajustar ao conteudo
        self.assertEqual(widget.list_widget.sizeAdjustPolicy(), QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
