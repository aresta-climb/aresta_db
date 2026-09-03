# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

# Copyright (C) 2026 ARESTA
import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from editor.views.widget_editor_mapas import CenaDesenho, WidgetEditorMapas, VisualizadorMapa

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
    widget.ao_pressionar_slider_bulk('circulo')
    widget.ao_soltar_slider_bulk('circulo')
    
    assert widget.slider_circ.value() == 0
    assert widget.label_circ.text() == "0%"
    
    # Testa para box/retângulo
    widget.slider_box.setValue(50)
    widget.ao_pressionar_slider_bulk('retangulo')
    widget.ao_soltar_slider_bulk('retangulo')
    
    assert widget.slider_box.value() == 0
    assert widget.label_box.text() == "0%"

def test_configurar_lista_mapas_todos_niveis(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PySide6.QtCore import Qt
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
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidgetItem
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
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTransform
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



def test_deletar_poi_com_tecla_delete(qtbot, mocker):
    from editor.views.widget_editor_mapas import WidgetEditorMapas, ItemBoundingRetangulo
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from PySide6.QtCore import Qt

    # Configuração
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa_proto = croqui_pb2.Mapa()
    poi = mapa_proto.pontos_de_interesse.add()
    poi.id = "poi_1"
    poi.label = "POI 1"
    poi.retangulo.x = 10
    poi.retangulo.y = 10
    poi.retangulo.comprimento = 20
    poi.retangulo.largura = 20
    
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
    from PySide6.QtCore import Qt
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
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidgetItem
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
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QTransform
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
    from PySide6.QtWidgets import QDialog, QMenu
    from PySide6.QtGui import QAction
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
    mocker.patch('editor.views.widget_editor_mapas.DialogoEdicaoPOI.obter_valores', return_value=("poi_novo", "Label Novo", ""))
    
    # Mock do QMenu para simular clique em Renomear sem abrir modal nativo
    mock_menu_class = mocker.patch('editor.views.widget_editor_mapas.QMenu')
    mock_menu_inst = mock_menu_class.return_value
    mock_acao_renomear = MagicMock()
    
    def fake_add_action(text):
        if text == "Renomear Ponto de Interesse":
            return mock_acao_renomear
        return MagicMock()
        
    mock_menu_inst.addAction.side_effect = fake_add_action
    mock_menu_inst.exec.return_value = mock_acao_renomear
    
    evento = MagicMock()
    evento.screenPos.return_value = None
    
    item.tratar_menu_contexto(evento, None)
    
    # Verifica se mover_poi foi chamado com o novo id
    assert mock_controller.mover_poi.called, "mover_poi deveria ter sido chamado ao renomear o item"
    args = mock_controller.mover_poi.call_args[0]
    assert args[1] == 0  # index do poi
    assert args[3].id == "poi_novo"  # o novo poi gerado deve ter o id atualizado


def test_poi_snapping_to_integers():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from editor.views.widget_editor_mapas import ItemBoundingRetangulo, ItemBoundingCirculo, ItemBoundingQuadrado, AlcaVertice, ItemBoundingPoligono
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem
    
    cena = QGraphicsScene()
    
    # Test ItemBoundingRetangulo
    box_dict = {'retangulo': {'x': 100, 'y': 100, 'comprimento': 50, 'largura': 50}}
    box = ItemBoundingRetangulo(box_dict, lambda: None)
    cena.addItem(box)
    
    mudanca = QGraphicsRectItem.GraphicsItemChange.ItemPositionChange
    novo_valor = QPointF(10.4, 20.6)
    snapped_valor = box.itemChange(mudanca, novo_valor)
    
    assert snapped_valor.x() == 10.0
    assert snapped_valor.y() == 21.0
    
    # Test ItemBoundingCirculo
    circ_dict = {'circulo': {'x': 100, 'y': 100, 'raio': 25}}
    circ = ItemBoundingCirculo(circ_dict, lambda: None)
    cena.addItem(circ)
    
    mudanca_circ = QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange
    novo_valor_circ = QPointF(10.5, 20.4)
    snapped_valor_circ = circ.itemChange(mudanca_circ, novo_valor_circ)
    
    assert snapped_valor_circ.x() == 10.0
    assert snapped_valor_circ.y() == 20.0
    
    # Test ItemBoundingQuadrado
    quad_dict = {'quadrado': {'x': 100, 'y': 100, 'lado': 50}}
    quad = ItemBoundingQuadrado(quad_dict, lambda: None)
    cena.addItem(quad)
    
    mudanca_quad = QGraphicsRectItem.GraphicsItemChange.ItemPositionChange
    novo_valor_quad = QPointF(10.4, 20.6)
    snapped_valor_quad = quad.itemChange(mudanca_quad, novo_valor_quad)
    
    assert snapped_valor_quad.x() == 10.0
    assert snapped_valor_quad.y() == 21.0
    
    # Test Polygon (Area Livre)
    poly_dict = {'poligono': {'coordenadas': [0, 0, 10, 0, 10, 10]}}
    poly = ItemBoundingPoligono(poly_dict, lambda x: None, lambda y: None)
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

    def test_lista_mapas_expansivel_na_sidebar(self):
        from PySide6.QtWidgets import QSizePolicy
        from editor.views.widget_editor_mapas import WidgetEditorMapas
        
        widget = WidgetEditorMapas()
        
        # O list_widget deve ter politica vertical Expanding para maximizar a área útil de seleção de mapas
        self.assertEqual(widget.list_widget.sizePolicy().verticalPolicy(), QSizePolicy.Policy.Expanding)

def test_mapas_gerais_sao_listados_e_carregados(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.mapas_controller import MapasController
    from aresta_api.proto.generated.croqui_pb2 import Pico, Croqui
    from unittest.mock import MagicMock
    
    croqui = Croqui()
    pico = croqui.picos.add()
    mapa_geral = pico.mapas_gerais.conteudo.mapas.add()
    mapa_geral.caminho_imagem_mapa = "mapa_geral_1.jpg"
    
    class MockSignal:
        def connect(self, f): pass
        
    mock_model = MagicMock(spec=CroquiModel)
    mock_model.dado_alterado = MockSignal()
    mock_model.repeated_adicionado = MockSignal()
    mock_model.repeated_removido = MockSignal()
    mock_model.obter_croqui_readonly.return_value = croqui
    
    controller = MapasController(mock_model, None)
    widget = WidgetEditorMapas(mapas_controller=controller)
    widget.configurar_lista_mapas()
    
    # Check if the map is listed in the sidebar
    items = []
    for i in range(widget.list_widget.count()):
        items.append(widget.list_widget.item(i).text())
    
    assert "mapa_geral_1.jpg" in items
    
    # Simulate clicking on it
    widget.selecionar_mapa_por_indices(0, -1, 0)
    assert widget.msg_mapa_proxy is not None
    assert widget.msg_mapa_proxy.caminho_imagem_mapa == "mapa_geral_1.jpg"


def test_hover_out_em_modo_linkagem_restaura_highlight(qtbot):
    """[TDD] Garante que ao sair do hover de um card durante modo linkagem, o destaque ciano retorne."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PySide6.QtGui import QColor
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Prepara mock de mapa com 1 POI
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add()
    poi.id = "poi_1"
    poi.retangulo.x = 10
    poi.retangulo.y = 10
    poi.retangulo.comprimento = 20
    poi.retangulo.largura = 20
    
    # Cria a referência e adiciona o poi_1
    ref = mapa.referencias.add()
    ref.ids.append("poi_1")
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    # Inicia modo linkagem
    widget.iniciar_modo_linkagem(0, ref)
    
    item_visual = widget.itens_poi[0]
    
    # Verifica que ficou ciano (destacado)
    assert item_visual.brush.color() == QColor(0, 255, 255, 150)
    
    # Simula hover_in vindo do painel de referencias (fica ciano)
    widget.destacar_pois_temporariamente(["poi_1"])
    assert item_visual.brush.color() == QColor(0, 255, 255, 150)
    
    # Simula hover_out (deve voltar para ciano, não para o verde padrão)
    widget.remover_destaque_pois()
    assert item_visual.brush.color() == QColor(0, 255, 255, 150)

def test_clique_poi_atualiza_cor_imediato(qtbot):
    """[TDD] Verifica se clicar num POI no modo linkagem atualiza o highlight imediatamente."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PySide6.QtGui import QColor
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Mock do controller
    mock_controller = MagicMock()
    widget.mapas_controller = mock_controller
    
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add()
    poi.id = "poi_1"
    poi.retangulo.x = 10
    poi.retangulo.y = 10
    poi.retangulo.comprimento = 20
    poi.retangulo.largura = 20
    
    ref = mapa.referencias.add()
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    # Inicia modo linkagem
    widget.iniciar_modo_linkagem(0, ref)
    item_visual = widget.itens_poi[0]
    
    # Inicialmente não está na ref, então a cor deve ser a padrão (não ciano)
    assert item_visual.brush.color() != QColor(0, 255, 255, 150)
    
    # Simula o clique no POI no modo linkagem
    widget.tratar_clique_poi_linkagem("poi_1")
    
    # Agora deve estar ciano
    assert item_visual.brush.color() == QColor(0, 255, 255, 150)

def test_clique_poi_chama_handler_com_id_correto(qtbot):
    """[TDD] Verifica se o clique no POI chama o _clique_handler com o ID extraido do pt_dict."""
    from editor.views.widget_editor_mapas import ItemBoundingRetangulo
    from PySide6.QtCore import Qt, QPointF
    from unittest.mock import MagicMock
    
    pt_dict = {'id': 'poi_123', 'retangulo': {'x': 10, 'y': 10, 'comprimento': 20, 'largura': 20}}
    item = ItemBoundingRetangulo(pt_dict, lambda x: None)
    
    handler = MagicMock(return_value=True)
    item.set_clique_handler(handler)
    
    evento = MagicMock()
    evento.modifiers.return_value = Qt.KeyboardModifier.NoModifier
    
    item.mousePressEvent(evento)
    
    handler.assert_called_once_with('poi_123')
    evento.accept.assert_called_once()

def test_iniciar_modo_camera_nao_crash_e_cria_overlay(qtbot):
    """[TDD] Verifica se iniciar_modo_camera inicializa ItemCameraOverlay sem erros."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas, ItemCameraOverlay
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    # Isso falhava com NameError antes da correção
    widget.iniciar_modo_camera(0, ref)
    
    assert widget.modo_camera is True
    assert widget.camera_ref_idx == 0
    assert widget.referencia_camera_ativa == ref
    assert isinstance(widget.item_camera_overlay, ItemCameraOverlay)
    
    # Verifica se parando o modo a overlay é removida
    widget.parar_modo_camera()
    assert widget.modo_camera is False
    assert getattr(widget, 'item_camera_overlay', None) is None

def test_iniciar_modo_camera_destaca_pois_ciano(qtbot):
    """[TDD] Verifica se ao iniciar o modo câmera os POIs da referência ficam destacados em ciano."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PySide6.QtGui import QColor
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add()
    poi.id = "poi_cam"
    poi.retangulo.x = 10
    poi.retangulo.y = 10
    poi.retangulo.comprimento = 20
    poi.retangulo.largura = 20
    
    ref = mapa.referencias.add()
    ref.ids.append("poi_cam")
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    widget.iniciar_modo_camera(0, ref)
    
    item_visual = widget.itens_poi[0]
    assert item_visual.brush.color() == QColor(0, 255, 255, 150)

def test_salvar_ajuste_camera_converte_para_int(qtbot):
    """[TDD] Verifica se o salvamento do ajuste converte posicao_horizontal e vertical para inteiro."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mock_controller = MagicMock()
    widget.mapas_controller = mock_controller
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    widget.iniciar_modo_camera(0, ref)
    widget.salvar_ajuste_camera()
    
    mock_controller.alterar_referencia.assert_called_once()
    ref_salva = mock_controller.alterar_referencia.call_args[0][3]
    
    # Verifica se foram passados valores inteiros (no protobuf types)
    # Se os valores não dessem crash no protobuf gerado, foi validado.
    assert isinstance(ref_salva.ajuste_de_camera.posicao_horizontal, int)
    assert isinstance(ref_salva.ajuste_de_camera.posicao_vertical, int)
    
    # Verifica se o modo câmera foi finalizado e a overlay removida
    assert widget.modo_camera is False
    assert getattr(widget, 'item_camera_overlay', None) is None

def test_remover_destaque_restaura_highlight_camera(qtbot):
    """[TDD] Garante que ao sair do hover no modo câmera, o destaque ciano retorne aos POIs."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PySide6.QtGui import QColor
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add()
    poi.id = "poi_1"
    poi.retangulo.x = 10
    poi.retangulo.y = 10
    poi.retangulo.comprimento = 20
    poi.retangulo.largura = 20
    
    ref = mapa.referencias.add()
    ref.ids.append("poi_1")
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    widget.iniciar_modo_camera(0, ref)
    item_visual = widget.itens_poi[0]
    
    # Simula hover_in para outro elemento (destaca outro ou o mesmo em ciano do hover)
    widget.destacar_pois_temporariamente(["poi_1"])
    
    # Simula hover_out (tem que voltar ao estado Ciano da câmera, e não pro verde nativo)
    widget.remover_destaque_pois()
    
    assert item_visual.brush.color() == QColor(0, 255, 255, 150)

def test_hover_referencia_sem_camera_oculta_overlay_existente(qtbot):
    """[TDD] Verifica se o destaque da câmera (roxo/magenta) some quando passa o hover em uma ref sem câmera."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    
    ref_com_cam = mapa.referencias.add()
    ref_com_cam.ajuste_de_camera.posicao_horizontal = 100
    ref_com_cam.ajuste_de_camera.posicao_vertical = 100
    ref_com_cam.ajuste_de_camera.zoom = 1.0
    
    ref_sem_cam = mapa.referencias.add()
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    # 1. Hover na referência com câmera -> Desenha overlay
    widget.destacar_pois_temporariamente(ref_com_cam)
    assert getattr(widget, 'item_hover_camera_overlay', None) is not None
    assert widget.item_hover_camera_overlay.isVisible() is True
    
    # 2. Hover em uma referência sem câmera (ou a mesma referência após exclusão da câmera)
    widget.destacar_pois_temporariamente(ref_sem_cam)
    
    # O overlay precisa ficar invisível!
    assert widget.item_hover_camera_overlay.isVisible() is False


def test_set_mapa_atual_carrega_referencias(qtbot):
    """[TDD] Verifica se ao chamar set_mapa_atual as referências do mapa são carregadas no Painel de Referências."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    
    # Adiciona 2 referências ao mapa
    mapa.referencias.add()
    mapa.referencias.add()
    
    proxy_mapa = ReadOnlyProxy(mapa)
    
    # Ao setar o mapa, o painel de referências DEVE exibir 2 cards (+ o botão adicionar/spacers)
    widget.set_mapa_atual(proxy_mapa)
    
    # Vamos contar quantos widgets CardReferencia existem no layout
    from editor.views.widget_painel_referencias import CardReferencia
    cards_count = 0
    layout = widget.painel_referencias.layout_cards
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() and isinstance(item.widget(), CardReferencia):
            cards_count += 1
            
    assert cards_count == 2, "As referências não foram carregadas no Painel de Referências ao setar o mapa!"

def test_item_camera_overlay_paint_nao_crasha(qtbot):
    """[TDD] Verifica se o paint do ItemCameraOverlay executa com sucesso sem quebrar por NameError (QPainter)."""
    from editor.views.widget_editor_mapas import ItemCameraOverlay
    from PySide6.QtGui import QPainter, QImage
    from PySide6.QtCore import QRectF
    
    item = ItemCameraOverlay(QRectF(0, 0, 100, 100))
    image = QImage(200, 200, QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    
    try:
        # Chama a função paint do item gráfico
        item.paint(painter, None, None)
    except NameError as e:
        import pytest
        pytest.fail(f"O método paint quebrou com NameError: {e}")
    finally:
        painter.end()

def test_camera_overlay_cor(qtbot):
    """[TDD] Verifica se a cor da linha da câmera é #6f42c1."""
    from editor.views.widget_editor_mapas import ItemCameraOverlay
    from PySide6.QtCore import QRectF
    item = ItemCameraOverlay(QRectF(0, 0, 100, 100))
    assert item.pen().color().name() == '#6f42c1', "A cor do overlay não bate com a cor do botão (#6f42c1)"

def test_salvar_ajuste_camera_parametros(qtbot):
    """[TDD] Verifica se o salvar ajuste de câmera passa os parâmetros corretos e não crasha."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import Mock

    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    proxy = ReadOnlyProxy(mapa)
    widget.msg_mapa_proxy = proxy
    
    widget.visualizador = Mock()
    from PySide6.QtCore import QRectF
    widget.visualizador.sceneRect.return_value = QRectF(0, 0, 1000, 1000)
    widget.visualizador.scene = Mock(return_value=Mock())
    
    # Mock do item_camera_overlay
    widget.item_camera_overlay = Mock()
    mock_rect = Mock()
    mock_rect.width.return_value = 500
    mock_rect.center.return_value.x.return_value = 500
    mock_rect.center.return_value.y.return_value = 500
    widget.item_camera_overlay.sceneBoundingRect.return_value = mock_rect
    
    widget.referencia_camera_ativa = proxy.referencias[0]
    widget.camera_ref_idx = 0
    widget.modo_camera = True
    
    controller_mock = Mock()
    widget.mapas_controller = controller_mock
    
    try:
        widget.salvar_ajuste_camera()
    except TypeError as e:
        import pytest
        pytest.fail(f"Crash de TypeError: {e}")
        
    assert controller_mock.alterar_referencia.called, "alterar_referencia não foi chamado"
    args = controller_mock.alterar_referencia.call_args[0]
    assert len(args) == 4, f"alterar_referencia foi chamado com {len(args)} argumentos, esperados 4"

def test_label_modo_exibida(qtbot):
    """[TDD] Verifica se a label_modo existe e é exibida nos modos de câmera e linkagem."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from unittest.mock import Mock
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    assert hasattr(widget, 'label_modo'), "label_modo não existe, provavelmente ainda é label_desenho"
    
    # Mock inicialização
    widget.visualizador = Mock()
    from PySide6.QtCore import QRectF
    widget.visualizador.sceneRect.return_value = QRectF(0, 0, 1000, 1000)
    widget.visualizador.scene = Mock(return_value=Mock())
    
    from aresta_api.proto.generated import croqui_pb2
    ref = croqui_pb2.Mapa.Referencia()
    
    # Teste Linkagem
    widget.iniciar_modo_linkagem(0, ref)
    assert widget.label_modo.isVisibleTo(widget)
    assert "MODO LINKAGEM" in widget.label_modo.text()
    
    # Teste Camera
    widget.parar_modo_linkagem()
    widget.iniciar_modo_camera(0, ref)
    assert widget.label_modo.isVisibleTo(widget)
    assert "MODO CÂMERA" in widget.label_modo.text()

def test_linkar_pois_seleciona_pois(qtbot):
    """[TDD] Verifica se clicar em um POI no modo linkagem adiciona/remove ele da lista e chama o controller."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import Mock

    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("100") # já tem o 100
    
    widget.mapas_controller = Mock()
    widget.msg_mapa_proxy = Mock()
    
    widget.iniciar_modo_linkagem(0, ref)
    
    # 1. Clicar num POI que NÃO está na referência (ex: "200") -> DEVE ADICIONAR
    widget.tratar_clique_poi_linkagem("200")
    assert widget.mapas_controller.alterar_referencia.called
    args = widget.mapas_controller.alterar_referencia.call_args[0]
    ref_nova = args[3]
    assert "200" in ref_nova.ids
    assert "100" in ref_nova.ids
    
    # 2. Clicar no POI que JÁ ESTÁ na referência (ex: "100") -> DEVE REMOVER
    widget.mapas_controller.alterar_referencia.reset_mock()
    # como a ref_nova virou a linkagem_ref localmente:
    widget.tratar_clique_poi_linkagem("100")
    assert widget.mapas_controller.alterar_referencia.called
    args = widget.mapas_controller.alterar_referencia.call_args[0]
    ref_nova2 = args[3]
    assert "100" not in ref_nova2.ids
    assert "200" in ref_nova2.ids

def test_remover_ajuste_camera_limpa_field_e_salva(qtbot):
    """[TDD] Verifica se remover_ajuste_camera limpa a configuração de câmera e notifica o controller."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mock_controller = MagicMock()
    widget.mapas_controller = mock_controller
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.ajuste_de_camera.zoom = 2.0
    ref.ajuste_de_camera.posicao_horizontal = 50
    ref.ajuste_de_camera.posicao_vertical = 50
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    widget.remover_ajuste_camera(0)
    
    mock_controller.alterar_referencia.assert_called_once()
    ref_salva = mock_controller.alterar_referencia.call_args[0][3]
    
    # Verifica se a câmera sumiu na referência enviada pro banco
    assert not ref_salva.HasField('ajuste_de_camera')

def test_hover_referencia_desenha_camera_estatica(qtbot):
    """[TDD] Verifica se o hover desenha a caixa de câmera Magenta no mapa."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.ajuste_de_camera.zoom = 1.0
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    assert getattr(widget, 'item_hover_camera_overlay', None) is None
    
    widget.destacar_pois_temporariamente(ref)
    
    assert getattr(widget, 'item_hover_camera_overlay', None) is not None
    assert widget.item_hover_camera_overlay.scene() == widget.dados_atuais['cena']
    
    widget.remover_destaque_pois()
    assert getattr(widget, 'item_hover_camera_overlay', None) is None

def test_linkagem_signal_conectado_no_editor_mapas(qtbot):
    """[TDD] Bug 1: Verifica se o sinal de iniciar/parar modo_linkagem do painel_referencias está conectado."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    widget.painel_referencias.iniciar_modo_linkagem.emit(0, "mock_ref")
    assert getattr(widget, 'modo_linkagem', False) == True
    assert getattr(widget, 'linkagem_ref', None) == "mock_ref"
        
    widget.painel_referencias.parar_modo_linkagem.emit()
    assert getattr(widget, 'modo_linkagem', True) == False

def test_salvar_ajuste_camera_compensa_posicao_cena(qtbot):
    """[TDD] Bug 2: Verifica se o centro da câmera salvo e carregado leva em conta scene_rect().x() e y()."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import Mock, patch
    from PySide6.QtCore import QRectF
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    widget.visualizador = Mock()
    from PySide6.QtCore import QRectF
    widget.visualizador.sceneRect.return_value = QRectF(-50.0, -100.0, 1000.0, 1000.0)
    widget.visualizador.scene = Mock(return_value=Mock())
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.ajuste_de_camera.posicao_horizontal = 50
    ref.ajuste_de_camera.posicao_vertical = 50
    ref.ajuste_de_camera.zoom = 2.0
    
    widget.msg_mapa_proxy = mapa
    widget.mapas_controller = Mock()
    
    widget.iniciar_modo_camera(0, ref)
    assert widget.item_camera_overlay.scenePos().x() == 200.0
    assert abs(widget.item_camera_overlay.scenePos().y() - (-44.44444444444446)) < 0.1
    
    widget.salvar_ajuste_camera()
    args = widget.mapas_controller.alterar_referencia.call_args[0]
    ref_nova = args[3]
    assert ref_nova.ajuste_de_camera.posicao_horizontal == 50
    assert ref_nova.ajuste_de_camera.posicao_vertical == 50

def test_item_camera_overlay_resize_pela_borda(qtbot):
    """[TDD] Verifica se arrastar o canto inferior direito redimensiona a câmera."""
    from editor.views.widget_editor_mapas import ItemCameraOverlay
    from PySide6.QtCore import Qt, QPointF
    import math
    
    item = ItemCameraOverlay(None)
    item.setRect(0, 0, 100, 100 * 16/9)
    
    class MockEvent:
        def __init__(self, pos, modifiers=Qt.KeyboardModifier.NoModifier):
            self._pos = pos
            self._modifiers = modifiers
            self.accepted = False
        def pos(self): return self._pos
        def scenePos(self): return self._pos
        def modifiers(self): return self._modifiers
        def accept(self): self.accepted = True
        
    press_event = MockEvent(QPointF(90, 100 * 16/9 - 10))
    item.mousePressEvent(press_event)
    assert item.resizing_corner == True
    
    move_event = MockEvent(QPointF(200, 200))
    item.mouseMoveEvent(move_event)
    assert item.rect().width() == 200
    assert math.isclose(item.rect().height(), 200 * 16/9)

def test_carregar_mapa_salva_card_camera_ativo(qtbot):
    """[TDD] Bug 4: Verifica se carregar_mapa salva card_camera_ativo."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import Mock
    
    mapa = croqui_pb2.Mapa()
    mapa.referencias.add()
    
    painel = PainelReferencias(Mock())
    painel.msg_mapa_proxy = mapa
    painel.carregar_mapa(mapa)
    
    card = painel.layout_cards.itemAt(0).widget()
    card.btn_camera.setChecked(True)
    
    painel.carregar_mapa(mapa)
    
    assert painel.card_camera_ativo is not None
    assert not painel.card_camera_ativo.btn_salvar_camera.isHidden()
    
    painel.forcar_parada_camera()
    assert not painel.card_camera_ativo
    novo_card = painel.layout_cards.itemAt(0).widget()
    assert novo_card.btn_salvar_camera.isHidden()

def test_atualizar_lista_mapas_ignora_referencias(qtbot):
    """[TDD] Verifica se o _atualizar_lista_mapas ignora atualizações no campo 'referencias' para não recarregar o mapa inteiro."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from unittest.mock import Mock
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    widget.list_widget.clear = Mock()
    
    widget._atualizar_lista_mapas(Mock(), 'referencias')
    widget.list_widget.clear.assert_not_called()
    
    widget._atualizar_lista_mapas(Mock(), 'algum_outro')
    widget.list_widget.clear.assert_called()

def test_hover_camera_compensa_posicao_cena(qtbot):
    """[TDD] Verifica se o hover desenha a caixa de câmera levando em conta a posição da cena (x, y)."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.readonly_proxy import ReadOnlyProxy
    from PySide6.QtCore import QRectF
    from unittest.mock import Mock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    widget.visualizador = Mock()
    widget.visualizador.sceneRect.return_value = QRectF(-50.0, -100.0, 1000.0, 1000.0)
    widget.visualizador.scene = Mock(return_value=Mock())
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.ajuste_de_camera.zoom = 2.0
    ref.ajuste_de_camera.posicao_horizontal = 50
    ref.ajuste_de_camera.posicao_vertical = 50
    
    proxy_mapa = ReadOnlyProxy(mapa)
    widget.set_mapa_atual(proxy_mapa)
    
    widget.destacar_pois_temporariamente(proxy_mapa.referencias[0])
    
    assert widget.item_hover_camera_overlay.scenePos().x() == 200.0
    assert abs(widget.item_hover_camera_overlay.scenePos().y() - (-44.44444444444446)) < 0.1

def test_item_camera_overlay_resize_com_ctrl_from_center(qtbot):
    """[TDD] Verifica se o Ctrl+Drag no ItemCameraOverlay redimensiona a partir do centro sem pular."""
    from editor.views.widget_editor_mapas import ItemCameraOverlay
    from PySide6.QtCore import Qt, QPointF
    import math
    
    item = ItemCameraOverlay(None)
    item.setRect(0, 0, 100, 100 * 16/9)
    item.setPos(100, 100) # center is at scene pos (150, 100 + 1600/18)
    
    class MockEvent:
        def __init__(self, pos, modifiers=Qt.KeyboardModifier.ControlModifier):
            self._pos = pos
            self._modifiers = modifiers
            self.accepted = False
        def pos(self): return self._pos
        def scenePos(self): return self._pos
        def modifiers(self): return self._modifiers
        def accept(self): self.accepted = True
        
    # Mouse press at scene center + 10, 10
    press_event = MockEvent(QPointF(160, 110))
    item.mousePressEvent(press_event)
    assert item.resizing_center == True
    
    # Mouse move to scene center + 50, 10
    move_event = MockEvent(QPointF(200, 110))
    item.mouseMoveEvent(move_event)
    
    # Diff X from center is 50. Initial diff was 10.
    # Total added width = 2 * (50 - 10) = 80.
    # New width = 100 + 80 = 180.
    assert item.rect().width() == 180.0
    assert math.isclose(item.rect().height(), 180 * 16/9)
    # The scene position must have adjusted so the center remains the same
    expected_center_x = 150
    actual_center_x = item.scenePos().x() + item.rect().width() / 2
    assert math.isclose(actual_center_x, expected_center_x)

class TestVisualizadorMapa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

    def setUp(self):
        self.view = VisualizadorMapa()
        from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem
        self.scene = QGraphicsScene(0, 0, 1000, 1000)
        self.view.setScene(self.scene)
        self.view.resize(400, 400)
        self.view.show()
        # Preencher barras de rolagem
        self.view.horizontalScrollBar().setRange(0, 600)
        self.view.verticalScrollBar().setRange(0, 600)
        self.view.horizontalScrollBar().setValue(300)
        self.view.verticalScrollBar().setValue(300)
        
        self.item = QGraphicsRectItem(100, 100, 50, 50)
        self.scene.addItem(self.item)

    def test_arrasto_fundo_mapa(self):
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPointF
        
        # Clicar no fundo (50, 50)
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(50.0, 50.0),
            QPointF(50.0, 50.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mousePressEvent(press_event)
        
        self.assertTrue(self.view._arrastando_mapa)
        self.assertEqual(self.view.cursor().shape(), Qt.CursorShape.ClosedHandCursor)
        
        # Mover o mouse
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(20.0, 30.0), # delta de -30 e -20
            QPointF(20.0, 30.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mouseMoveEvent(move_event)
        
        # O valor original era 300
        # novo valor = 300 - (-30) = 330
        self.assertEqual(self.view.horizontalScrollBar().value(), 330)
        self.assertEqual(self.view.verticalScrollBar().value(), 320)
        
        # Soltar mouse
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(20.0, 30.0),
            QPointF(20.0, 30.0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mouseReleaseEvent(release_event)
        self.assertFalse(self.view._arrastando_mapa)
        self.assertEqual(self.view.cursor().shape(), Qt.CursorShape.OpenHandCursor)

    def test_arrasto_sobre_poi_nao_ativa_pan(self):
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPointF
        
        # Clicar no item em coordenadas da view.
        # Item em 100, 100, mas a view está em scroll 300.
        # Precisamos de um ponto onde o itemAt retorne algo.
        # Para simplificar, movemos a cena inteira ou testamos diretamente o mock/spy
        # Vamos mapear a pos.
        pos_view = self.view.mapFromScene(125, 125)
        
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(float(pos_view.x()), float(pos_view.y())),
            QPointF(float(pos_view.x()), float(pos_view.y())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mousePressEvent(press_event)
        
        self.assertFalse(self.view._arrastando_mapa)

    def test_arrasto_fundo_mapa_com_imagem(self):
        from PySide6.QtGui import QMouseEvent, QPixmap, QImage, QColor
        from PySide6.QtWidgets import QGraphicsPixmapItem
        from PySide6.QtCore import QPointF
        
        # Adicionar imagem ao fundo
        img = QImage(200, 200, QImage.Format.Format_RGB32)
        img.fill(QColor("white"))
        pixmap = QPixmap.fromImage(img)
        item_img = QGraphicsPixmapItem(pixmap)
        item_img.setPos(0, 0)
        self.scene.addItem(item_img)
        
        # Clicar na imagem
        pos_view = self.view.mapFromScene(10, 10)
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(float(pos_view.x()), float(pos_view.y())),
            QPointF(float(pos_view.x()), float(pos_view.y())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mousePressEvent(press_event)
        
        self.assertTrue(self.view._arrastando_mapa)
        self.assertEqual(self.view.cursor().shape(), Qt.CursorShape.ClosedHandCursor)

    def test_arrasto_fundo_mapa_pequeno(self):
        from PySide6.QtGui import QMouseEvent, QPixmap, QImage, QColor
        from PySide6.QtWidgets import QGraphicsPixmapItem
        from PySide6.QtCore import QPointF
        
        # Simula o comportamento do _renderizar_mapa definindo um sceneRect enorme
        self.view.scene().clear()
        self.view.scene().setSceneRect(-50000, -50000, 100000, 100000)
        
        img = QImage(100, 100, QImage.Format.Format_RGB32)
        img.fill(QColor("blue"))
        pixmap = QPixmap.fromImage(img)
        item_img = QGraphicsPixmapItem(pixmap)
        item_img.setPos(0, 0)
        self.view.scene().addItem(item_img)
        
        # Como o sceneRect é enorme, os scrollbars devem ter range > 0, 
        # permitindo o panning mesmo com uma imagem de 100x100.
        self.assertGreater(self.view.horizontalScrollBar().maximum(), 0)
        
        # Simulamos fitInView nos items
        self.view.fitInView(self.view.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        # Mapeamos o clique no centro da imagem (50, 50 em coordenadas da cena)
        pos_view = self.view.mapFromScene(50, 50)
        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(float(pos_view.x()), float(pos_view.y())),
            QPointF(float(pos_view.x()), float(pos_view.y())),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mousePressEvent(press_event)
        self.assertTrue(self.view._arrastando_mapa)
        
        h_scroll_antes = self.view.horizontalScrollBar().value()
        
        # Mover
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(float(pos_view.x() - 20), float(pos_view.y() - 20)),
            QPointF(float(pos_view.x() - 20), float(pos_view.y() - 20)),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.view.mouseMoveEvent(move_event)
        
        self.assertTrue(self.view._arrastando_mapa)
        
        h_scroll_depois = self.view.horizontalScrollBar().value()
        self.assertGreater(h_scroll_depois, h_scroll_antes)

    def test_resize_anchor(self):
        from PySide6.QtWidgets import QGraphicsView
        self.assertEqual(self.view.resizeAnchor(), QGraphicsView.ViewportAnchor.AnchorViewCenter)

def test_deletar_ou_adicionar_poi_nao_reseta_zoom(qtbot):
    """[TDD] Verifica se deletar ou adicionar um POI não reseta o zoom do mapa."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    widget.msg_mapa_proxy = MagicMock()
    widget.msg_mapa_proxy.pontos_de_interesse = [MagicMock(), MagicMock()]
    widget._renderizar_mapa = MagicMock()
    widget.visualizador = MagicMock()
    
    # Mock para dicionario itens_poi
    item_mock = MagicMock()
    widget.itens_poi = {0: item_mock}
    
    widget._on_repeated_removido(widget.msg_mapa_proxy, 'pontos_de_interesse', 0)
    widget._renderizar_mapa.assert_not_called()
    
    widget._renderizar_mapa.reset_mock()
    widget._adicionar_item_cena = MagicMock()
    
    widget._on_repeated_adicionado(widget.msg_mapa_proxy, 'pontos_de_interesse', 0)
    widget._renderizar_mapa.assert_not_called()

def test_converter_item_para_circulo(qtbot):
    """[TDD] Verifica se o item pode ser convertido para circulo via metodo do widget."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    widget.mapas_controller = MagicMock()
    widget.msg_mapa_proxy = MagicMock()
    
    item_mock = MagicMock()
    widget.itens_poi = {3: item_mock}
    
    widget.converter_item_para_circulo(item_mock)
    widget.mapas_controller.converter_boxes_para_circulos.assert_called_with(widget.msg_mapa_proxy, [3])

def test_alterar_tipo_poi_nao_reseta_zoom(qtbot):
    """[TDD] Verifica se alterar o tipo de um POI (conversao) não reseta o zoom do mapa."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas, ItemBoundingRetangulo
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    widget.msg_mapa_proxy = MagicMock()
    
    poi = croqui_pb2.Mapa.PontoDeInteresse()
    poi.circulo.raio = 10
    widget.msg_mapa_proxy.pontos_de_interesse = [poi]
    
    widget._renderizar_mapa = MagicMock()
    widget.visualizador = MagicMock()
    cena_mock = MagicMock()
    widget.visualizador.scene.return_value = cena_mock
    
    item_existente = MagicMock(spec=ItemBoundingRetangulo)
    widget.itens_poi = {0: item_existente}
    
    widget._adicionar_item_cena = MagicMock()
    
    widget._on_repeated_item_alterado(widget.msg_mapa_proxy, 'pontos_de_interesse', 0)
    
    widget._renderizar_mapa.assert_not_called()
    cena_mock.removeItem.assert_called_with(item_existente)

def test_converter_item_para_retangulo(qtbot):
    """[TDD] Verifica se o item circular pode ser convertido para retangulo via metodo do widget."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    widget.mapas_controller = MagicMock()
    widget.msg_mapa_proxy = MagicMock()
    
    item_mock = MagicMock()
    widget.itens_poi = {4: item_mock}
    
    widget.converter_item_para_retangulo(item_mock)
    widget.mapas_controller.converter_circulos_para_boxes.assert_called_with(widget.msg_mapa_proxy, [4])



def test_item_camera_overlay_is_visible_and_in_scene(qtbot):
    """[TDD] Verifica se o overlay da camera é instanciado corretamente, fica visível, é adicionado à cena e possui rect maior que zero."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    from PySide6.QtWidgets import QGraphicsScene
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Inicia a cena forçadamente sem tamanho para que a câmera teste o fallback
    cena = QGraphicsScene()
    widget.visualizador.setScene(cena)
    
    # Mocks para forçar o boundingRect() a ser vazio (0,0,0,0)
    from PySide6.QtCore import QRectF
    mock_rect = QRectF(0, 0, 0, 0)
    widget.visualizador.sceneRect = MagicMock(return_value=mock_rect)
    widget.visualizador.mapToScene = MagicMock()
    widget.visualizador.mapToScene().boundingRect.return_value = mock_rect
    
    
    # Chama o modo de câmera
    mock_ref = MagicMock()
    mock_ref.HasField.return_value = False
    widget.iniciar_modo_camera(0, mock_ref)
    
    overlay = widget.item_camera_overlay
    
    # 1.2: A cena não pode ser nula e o overlay deve estar visível
    assert overlay is not None, "O overlay da câmera não foi criado."
    assert overlay.scene() is not None, "O overlay não foi adicionado à cena."
    assert overlay.isVisible() == True, "O overlay não está visível."
    
    # 1.3: A área do rect deve ser estritamente maior que zero
    rect = overlay.rect()
    area = rect.width() * rect.height()
    assert area > 0, f"A área do overlay da câmera é zero ou menor (w={rect.width()}, h={rect.height()}). O componente não aparece na tela."

def test_poi_bloqueado_no_modo_linkagem(qtbot):
    """[TDD] Verifica se a flag ItemIsMovable dos POIs é desativada durante a iniciação do modo de linkagem."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas, ItemBoundingRetangulo
    from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene
    from unittest.mock import MagicMock
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    # Adiciona um POI mock
    box_dict = {'retangulo': {'x': 10, 'y': 10, 'comprimento': 50, 'largura': 50}, 'id': 'teste'}
    item = ItemBoundingRetangulo(box_dict, lambda: None)
    
    # Por padrão, um POI instanciado DEVE ser móvel
    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
    
    widget.itens_poi = {0: item}
    cena = QGraphicsScene()
    widget.visualizador.setScene(cena)
    widget.visualizador.scene().addItem(item)
    
    assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable, "Condição inicial: POI deveria ser móvel."
    
    # Inicia modo de linkagem
    mock_ref = MagicMock()
    mock_ref.HasField.return_value = False
    mock_ref.ids = []
    widget.iniciar_modo_linkagem(0, mock_ref)
    
    # 1.4: O POI não deve ser móvel
    assert not (item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable), "O POI não teve seu movimento bloqueado durante a linkagem!"
    
    # Para o modo de linkagem
    widget.parar_modo_linkagem()
    
    # 1.4: O POI deve voltar a ser móvel
    assert item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable, "O POI não teve seu movimento restaurado após a linkagem!"


def test_dialogo_edicao_poi_com_cor(qtbot):
    """Testa se o diálogo de edição de POI permite selecionar e obter ID, Label e Cor."""
    from editor.views.widget_editor_mapas import DialogoEdicaoPOI
    
    dialogo = DialogoEdicaoPOI(id_atual="1", label_atual="Via Principal", cor_atual="#00E676")
    qtbot.addWidget(dialogo)
    
    # Testa valores iniciais
    id_val, label_val, cor_val, _ = dialogo.obter_valores()
    assert id_val == "1"
    assert label_val == "Via Principal"
    assert cor_val == "#00E676"
    
    # Altera valores
    dialogo.input_id.setText("2")
    dialogo.input_label.setText("Variante")
    dialogo._definir_cor("#FF1744")
    
    id_val, label_val, cor_val, _ = dialogo.obter_valores()
    assert id_val == "2"
    assert label_val == "Variante"
    assert cor_val == "#FF1744"


def test_item_trajeto_linha_criacao_e_spline(qtbot):
    """Testa a renderização do ItemTrajetoLinha e criação das alças de nó."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha, AlcaNoTrajeto
    from PySide6.QtWidgets import QGraphicsScene
    from PySide6.QtCore import QPointF
    
    cena = QGraphicsScene()
    pt_dict = {
        "id": "via_1",
        "label": "Via Teste",
        "cor": "#FF6D00",
        "linha": {
            "estilo": "TRACEJADO",
            "espessura": 4,
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 10, "tipo": 1, "rotulo": "1"},
                    {"x": 50, "y": 100, "tipo": 0, "rotulo": ""},
                    {"x": 80, "y": 200, "tipo": 5, "rotulo": ""}
                ]
            }
        }
    }
    
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    cena.addItem(item_linha)
    
    assert len(item_linha.alcas) == 3
    assert not item_linha.path().isEmpty()
    assert item_linha.cor_hex == "#FF6D00"
    
    # Move uma alça e verifica se a spline é recalculada
    alca = item_linha.alcas[1]
    alca.setPos(QPointF(60, 120))
    assert pt_dict["linha"]["conteudo"]["nos"][1]["x"] == 60
    assert pt_dict["linha"]["conteudo"]["nos"][1]["y"] == 120


def test_item_trajeto_linha_alterar_tipo_no_e_estilo(qtbot):
    """Testa a alteração de tipo de nó e estilos visuais do trajeto."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import Qt
    
    pt_dict = {
        "id": "v1",
        "cor": "#FF1744",
        "linha": {
            "estilo": "SOLIDO",
            "conteudo": {
                "nos": [
                    {"x": 0, "y": 0, "tipo": 1},
                    {"x": 50, "y": 50, "tipo": 0},
                    {"x": 100, "y": 100, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    
    # Altera tipo do nó do meio para Chapeleta (tipo 3)
    item_linha.alterar_tipo_no(1, 3)
    assert item_linha.pt_dict["linha"]["conteudo"]["nos"][1]["tipo"] == 3
    
    # Altera estilo do traço para PONTILHADO
    item_linha._definir_estilo("PONTILHADO")
    assert item_linha.pen().style() == Qt.PenStyle.DotLine
    
    # Altera cor
    item_linha._definir_cor("#00E5FF")
    assert item_linha.cor_hex == "#00E5FF"


def test_item_trajeto_linha_inserir_e_remover_no(qtbot):
    """Testa inserção e remoção de nós intermediários na linha."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import QPointF
    
    pt_dict = {
        "id": "v1",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 0, "y": 0, "tipo": 1},
                    {"x": 100, "y": 100, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    assert len(item_linha.alcas) == 2
    
    # Insere nó em (50, 50)
    item_linha.inserir_no_em_posicao(QPointF(50, 50))
    assert len(item_linha.pt_dict["linha"]["conteudo"]["nos"]) == 3
    assert item_linha.pt_dict["linha"]["conteudo"]["nos"][1]["x"] == 50
    assert len(item_linha.alcas) == 3
    
    # Remove nó do meio
    item_linha.remover_no(1)
    assert len(item_linha.pt_dict["linha"]["conteudo"]["nos"]) == 2
    assert len(item_linha.alcas) == 2
    
    # Tentativa de remover abaixo de 2 nós não deve diminuir mais
    item_linha.remover_no(0)
    assert len(item_linha.pt_dict["linha"]["conteudo"]["nos"]) == 2


def test_modo_desenho_linha_fluxo_completo(qtbot, monkeypatch):
    """Testa o fluxo de criação de linha com início, nós intermediários, desfecho e mock de diálogo."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas, CenaDesenho, DialogoEdicaoPOI
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtWidgets import QDialog
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    mock_controller = MagicMock()
    widget.mapas_controller = mock_controller
    
    mapa_proto = croqui_pb2.Mapa()
    widget.msg_mapa_proxy = mapa_proto
    
    cena = CenaDesenho(widget)
    widget.visualizador.setScene(cena)
    dados = {'cena': cena, 'itens_bb': []}
    widget.dados_atuais = dados
    
    # Inicia modo de desenho de linha
    widget.iniciar_modo_desenho_linha(dados)
    assert widget.modo_desenho_linha is True
    assert not widget.label_modo.isHidden()
    
    # Adiciona pontos
    widget.adicionar_ponto_desenho_linha(QPointF(10, 10))
    widget.adicionar_ponto_desenho_linha(QPointF(30, 80))
    widget.adicionar_ponto_desenho_linha(QPointF(50, 150))
    assert len(widget.pontos_desenho_linha) == 3
    
    # Desfaz um ponto
    widget.desfazer_ponto_desenho_linha()
    assert len(widget.pontos_desenho_linha) == 2
    
    # Adiciona novamente
    widget.adicionar_ponto_desenho_linha(QPointF(60, 200))
    assert len(widget.pontos_desenho_linha) == 3
    
    # Mock do DialogoEdicaoPOI para aceitar automaticamente
    monkeypatch.setattr(DialogoEdicaoPOI, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(DialogoEdicaoPOI, "obter_valores", lambda self: ("1", "Fenda do Baú", "#00E676"))
    
    # Finaliza modo
    widget.finalizar_modo_desenho_linha()
    assert widget.modo_desenho_linha is False
    assert widget.label_modo.isHidden()
    
    # Verifica chamada no controller
    mock_controller.adicionar_linha.assert_called_once()
    args, kwargs = mock_controller.adicionar_linha.call_args
    assert kwargs["id_linha"] == "1"
    assert kwargs["label"] == "Fenda do Baú"
    assert kwargs["cor"] == "#00E676"
    assert len(kwargs["nos"]) == 3
    assert all(n["tipo"] == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM for n in kwargs["nos"])


def test_modo_desenho_linha_cancelamento_e_teclado(qtbot):
    """Testa cancelamento de linha e atalhos de teclado."""
    from editor.views.widget_editor_mapas import WidgetEditorMapas, CenaDesenho
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QKeyEvent
    
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    
    cena = CenaDesenho(widget)
    widget.visualizador.setScene(cena)
    dados = {'cena': cena, 'itens_bb': []}
    widget.dados_atuais = dados
    
    widget.iniciar_modo_desenho_linha(dados)
    widget.adicionar_ponto_desenho_linha(QPointF(20, 20))
    
    # Pressiona ESC no visualizador
    evento_esc = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    widget.visualizador.keyPressEvent(evento_esc)
    
    assert widget.modo_desenho_linha is False
    assert len(widget.pontos_desenho_linha) == 0


def test_item_trajeto_linha_mover_linha_completa_move_nos_e_alcas(qtbot):
    """TDD Item 1: Ao mover o traçado todo, os nós e alças devem mover junto e atualizar as coordenadas."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent
    from PySide6.QtCore import QPointF, QEvent, Qt
    
    pt_dict = {
        "id": "v1",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1},
                    {"x": 50, "y": 60, "tipo": 0},
                    {"x": 100, "y": 120, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    cena = QGraphicsScene()
    cena.addItem(item_linha)
    
    # As alças devem ser itens filhos de item_linha
    for alca in item_linha.alcas:
        assert alca.parentItem() == item_linha
    
    # Simula clique e arrasto da linha completa em (dx=30, dy=40)
    evento_press = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMousePress)
    evento_press.setScenePos(QPointF(50, 60))
    evento_press.setButton(Qt.MouseButton.LeftButton)
    item_linha.mousePressEvent(evento_press)
    
    item_linha.setPos(30, 40)
    
    evento_release = QGraphicsSceneMouseEvent(QEvent.Type.GraphicsSceneMouseRelease)
    evento_release.setScenePos(QPointF(80, 100))
    evento_release.setButton(Qt.MouseButton.LeftButton)
    item_linha.mouseReleaseEvent(evento_release)
    
    # Após soltar, as coordenadas dos nós devem ter sido deslocadas por (30, 40)
    nos = item_linha.pt_dict["linha"]["conteudo"]["nos"]
    assert nos[0]["x"] == 40 and nos[0]["y"] == 60
    assert nos[1]["x"] == 80 and nos[1]["y"] == 100
    assert nos[2]["x"] == 130 and nos[2]["y"] == 160
    
    # item_linha.pos() deve ser mantido normalizado em (0, 0)
    assert item_linha.pos().x() == 0 and item_linha.pos().y() == 0
    
    # E as alças na cena devem estar exatamente em (40, 60), (80, 100), (130, 160)
    assert item_linha.alcas[0].scenePos().x() == 40 and item_linha.alcas[0].scenePos().y() == 60
    assert item_linha.alcas[1].scenePos().x() == 80 and item_linha.alcas[1].scenePos().y() == 100
    assert item_linha.alcas[2].scenePos().x() == 130 and item_linha.alcas[2].scenePos().y() == 160


def test_item_trajeto_linha_mover_no_individual_mantem_outros_nos_e_spline_consistente(qtbot):
    """TDD Item 2: Ao mover um nó individual, o traçado ajusta suavemente mantendo os outros nós travados."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtWidgets import QGraphicsScene
    from PySide6.QtCore import QPointF
    
    pt_dict = {
        "id": "v1",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1},
                    {"x": 50, "y": 60, "tipo": 0},
                    {"x": 100, "y": 120, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    cena = QGraphicsScene()
    cena.addItem(item_linha)
    
    # Move apenas o nó do meio para (70, 80)
    alca_meio = item_linha.alcas[1]
    alca_meio.setPos(QPointF(70, 80))
    
    nos = item_linha.pt_dict["linha"]["conteudo"]["nos"]
    assert nos[0]["x"] == 10 and nos[0]["y"] == 20  # Inalterado
    assert nos[1]["x"] == 70 and nos[1]["y"] == 80  # Movido
    assert nos[2]["x"] == 100 and nos[2]["y"] == 120  # Inalterado
    
    # O início do path deve ser exatamente o nó 0 e o fim o nó 2
    path = item_linha.path()
    assert not path.isEmpty()
    ponto_inicial = path.pointAtPercent(0.0)
    ponto_final = path.pointAtPercent(1.0)
    assert round(ponto_inicial.x()) == 10 and round(ponto_inicial.y()) == 20
    assert round(ponto_final.x()) == 100 and round(ponto_final.y()) == 120


def test_alca_no_trajeto_formatos_semanticos_e_badge_inicio(qtbot):
    """TDD Item 3: Nós semânticos (Início/Base, Chapeleta, Top, Crux) têm formatos visuais e badge com número."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    
    pt_dict = {
        "id": "5",
        "cor": "#FF6D00",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1, "rotulo": ""},
                    {"x": 50, "y": 60, "tipo": 3, "rotulo": ""},
                    {"x": 100, "y": 120, "tipo": 5, "rotulo": ""}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    alca_inicio = item_linha.alcas[0]
    
    # Início da via deve exibir o número da via ("5") como padrão quando rótulo está vazio
    assert alca_inicio.obter_rotulo_exibicao() == "5"
    assert alca_inicio.rect().width() >= 20
    
    # Se definir um rótulo explícito, deve usá-lo
    item_linha.pt_dict["linha"]["conteudo"]["nos"][0]["rotulo"] = "5A"
    alca_inicio.atualizar_estilo()
    assert alca_inicio.obter_rotulo_exibicao() == "5A"
    
    # Testa outros tipos semânticos
    alca_chapeleta = item_linha.alcas[1]
    assert alca_chapeleta.no_dict["tipo"] == 3
    
    alca_top = item_linha.alcas[2]
    assert alca_top.no_dict["tipo"] == 5


def test_item_bounding_circulo_e_box_texto_centralizado_dentro(qtbot):
    """TDD Item 4: Círculos e retângulos exibem texto posicionado dentro da forma quando texto_visivel está presente."""
    from editor.views.widget_editor_mapas import ItemBoundingCirculo, ItemBoundingRetangulo
    
    # Círculo com texto_visivel "A"
    circ_dict = {
        "id": "A",
        "label": "Setor A",
        "texto_visivel": "A",
        "circulo": {"x": 100, "y": 100, "raio": 40}
    }
    item_circ = ItemBoundingCirculo(circ_dict, lambda item: None)
    assert item_circ.item_texto.isVisible() is True
    assert item_circ.item_texto.toPlainText() == "A"
    
    # O centro do círculo local é (0, 0). O texto deve estar centralizado ao redor de (0, 0)
    pos_texto = item_circ.item_texto.pos()
    rect_texto = item_circ.item_texto.boundingRect()
    centro_texto_x = pos_texto.x() + rect_texto.width() / 2
    centro_texto_y = pos_texto.y() + rect_texto.height() / 2
    assert abs(centro_texto_x) < 5
    assert abs(centro_texto_y) < 5
    
    # Retângulo com texto_visivel "B1"
    box_dict = {
        "id": "B1",
        "label": "Bloco 1",
        "texto_visivel": "B1",
        "retangulo": {"x": 200, "y": 200, "comprimento": 80, "largura": 50}
    }
    item_box = ItemBoundingRetangulo(box_dict, lambda item: None)
    assert item_box.item_texto.isVisible() is True
    assert item_box.item_texto.toPlainText() == "B1"
    
    # O centro do retângulo local é (40, 25)
    pos_box_t = item_box.item_texto.pos()
    rect_box_t = item_box.item_texto.boundingRect()
    centro_box_tx = pos_box_t.x() + rect_box_t.width() / 2
    centro_box_ty = pos_box_t.y() + rect_box_t.height() / 2
    assert abs(centro_box_tx - 40) < 5
    assert abs(centro_box_ty - 25) < 5


def test_poi_texto_visivel_apenas_quando_definido(qtbot):
    """Testa que o texto no mapa só é renderizado quando 'texto_visivel' for explicitamente definido."""
    from editor.views.widget_editor_mapas import ItemBoundingCirculo
    
    # 1. POI sem texto_visivel: não exibe texto no mapa
    circ_sem_texto = {
        "id": "1",
        "label": "Via da Fenda",
        "circulo": {"x": 50, "y": 50, "raio": 20}
    }
    item1 = ItemBoundingCirculo(circ_sem_texto, lambda item: None)
    assert item1.item_texto.toPlainText() == ""
    assert item1.item_texto.isVisible() is False
    # Tooltip mantém as informações para o autor
    assert "ID: 1" in item1.toolTip()
    assert "Label: Via da Fenda" in item1.toolTip()
    
    # 2. POI com texto_visivel: exibe o texto no mapa
    circ_com_texto = {
        "id": "1",
        "label": "Via da Fenda",
        "texto_visivel": "Fenda",
        "circulo": {"x": 50, "y": 50, "raio": 20}
    }
    item2 = ItemBoundingCirculo(circ_com_texto, lambda item: None)
    assert item2.item_texto.toPlainText() == "Fenda"
    assert item2.item_texto.isVisible() is True
    
    # 3. Atualização via carregar_de_dict
    item1.carregar_de_dict({
        "id": "1",
        "texto_visivel": "Novo Texto",
        "circulo": {"x": 50, "y": 50, "raio": 20}
    })
    assert item1.item_texto.toPlainText() == "Novo Texto"
    assert item1.item_texto.isVisible() is True


def test_alca_no_trajeto_menu_contexto_e_nomes_tipo(qtbot):
    """Testa nomes e descrições dos tipos de nós seguindo o padrão FEMEMG."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    
    pt_dict = {
        "id": "1",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 0},
                    {"x": 30, "y": 40, "tipo": 1},
                    {"x": 50, "y": 60, "tipo": 3},
                    {"x": 70, "y": 80, "tipo": 7},
                    {"x": 90, "y": 100, "tipo": 4},
                    {"x": 110, "y": 120, "tipo": 8},
                    {"x": 130, "y": 140, "tipo": 9},
                    {"x": 150, "y": 160, "tipo": 10},
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    alca = item_linha.alcas[0]
    
    assert alca.obter_nome_tipo(0) == "Invisível (Curva)"
    assert alca.obter_nome_tipo(1) == "Círculo Identificador"
    assert alca.obter_nome_tipo(2) == "Círculo Identificador (Sit Start)"
    assert alca.obter_nome_tipo(3) == "Proteção Fixa [X]"
    assert alca.obter_nome_tipo(4) == "Parada Intermediária [XX]"
    assert alca.obter_nome_tipo(5) == "Top / Parada Final [XX]"
    assert alca.obter_nome_tipo(6) == "Crux (Chave)"
    assert alca.obter_nome_tipo(7) == "Proteção Móvel [△]"
    assert alca.obter_nome_tipo(8) == "Píton"
    assert alca.obter_nome_tipo(9) == "Fita"
    assert alca.obter_nome_tipo(10) == "Buraco de Cliff"
    assert alca.normalizar_tipo_int("CIRCULO_IDENTIFICADOR") == 1
    assert alca.normalizar_tipo_int("INICIO_BASE") == 1


def test_alca_no_trajeto_simbolos_fememg_renderizacao(qtbot):
    """Testa renderização vetorial de todos os símbolos FEMEMG B3 sem exceções."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtGui import QPixmap, QPainter
    
    tipos_fememg = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    nos = [{"x": i * 20, "y": i * 20, "tipo": t, "rotulo": str(i) if t in (1, 2) else ""} for i, t in enumerate(tipos_fememg)]
    pt_dict = {
        "id": "7",
        "cor": "#FF6D00",
        "linha": {"conteudo": {"nos": nos}}
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    
    pixmap = QPixmap(200, 200)
    pixmap.fill()
    painter = QPainter(pixmap)
    try:
        for alca in item_linha.alcas:
            alca.paint(painter, None, None)
    finally:
        painter.end()


def test_item_trajeto_linha_estilos_fememg_incluindo_caminhada(qtbot):
    """Testa estilos de traço da norma FEMEMG B3: Tracejado, Pontilhado, Sólido e Caminhada."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import Qt
    
    pt_dict = {
        "id": "1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {"nos": [{"x": 0, "y": 0, "tipo": 0}, {"x": 50, "y": 50, "tipo": 0}]}
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    assert item_linha.pen().style() == Qt.PenStyle.CustomDashLine
    
    item_linha._definir_estilo("PONTILHADO")
    assert item_linha.pen().style() == Qt.PenStyle.DotLine
    
    item_linha._definir_estilo("SOLIDO")
    assert item_linha.pen().style() == Qt.PenStyle.SolidLine
    
    item_linha._definir_estilo("CAMINHADA")
    assert item_linha.pt_dict["linha"]["estilo"] == "CAMINHADA"


def test_dialogo_edicao_poi_com_texto_visivel(qtbot):
    """Testa inicialização e captura de valores incluindo texto_visivel em DialogoEdicaoPOI."""
    from editor.views.widget_editor_mapas import DialogoEdicaoPOI
    
    dialogo = DialogoEdicaoPOI("V1", "Via 01", "#FF6D00", "Via da Fenda")
    assert dialogo.input_id.text() == "V1"
    assert dialogo.input_label.text() == "Via 01"
    assert dialogo.cor_selecionada == "#FF6D00"
    assert dialogo.input_texto_visivel.text() == "Via da Fenda"
    
    dialogo.input_texto_visivel.setText("Novo Texto Visível")
    valores = dialogo.obter_valores()
    assert valores == ("V1", "Via 01", "#FF6D00", "Novo Texto Visível")


def test_itens_bounding_box_retangulo_quadrado_sem_texto_visivel_fica_invisivel(qtbot):
    """Testa que retângulo e quadrado sem texto_visivel ficam com texto invisível, e com texto_visivel ficam visíveis."""
    from editor.views.widget_editor_mapas import ItemBoundingRetangulo, ItemBoundingQuadrado
    
    # Retângulo sem texto_visivel
    item_ret = ItemBoundingRetangulo({"id": "R1", "label": "Bloco", "retangulo": {"x": 50, "y": 50, "comprimento": 30, "largura": 20}}, lambda item: None)
    assert item_ret.item_texto.isVisible() is False
    assert item_ret.item_texto.toPlainText() == ""
    
    # Retângulo com texto_visivel
    item_ret.carregar_de_dict({"id": "R1", "label": "Bloco", "texto_visivel": "B1", "retangulo": {"x": 50, "y": 50, "comprimento": 30, "largura": 20}})
    assert item_ret.item_texto.isVisible() is True
    assert item_ret.item_texto.toPlainText() == "B1"
    
    # Quadrado sem texto_visivel
    item_quad = ItemBoundingQuadrado({"id": "Q1", "label": "Pedra", "quadrado": {"x": 80, "y": 80, "lado": 25}}, lambda item: None)
    assert item_quad.item_texto.isVisible() is False
    assert item_quad.item_texto.toPlainText() == ""
    
    # Quadrado com texto_visivel
    item_quad.carregar_de_dict({"id": "Q1", "label": "Pedra", "texto_visivel": "Q1", "quadrado": {"x": 80, "y": 80, "lado": 25}})
    assert item_quad.item_texto.isVisible() is True
    assert item_quad.item_texto.toPlainText() == "Q1"


def test_item_trajeto_linha_definir_espessura(qtbot):
    """Testa alteração dinâmica da espessura do traço no ItemTrajetoLinha."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtWidgets import QGraphicsScene

    cena = QGraphicsScene()
    pt_dict = {
        "id": "via_1",
        "cor": "#00E676",
        "linha": {
            "estilo": "TRACEJADO",
            "espessura": 3,
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1},
                    {"x": 50, "y": 80, "tipo": 0},
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    cena.addItem(item)

    assert item.pen().width() == 3
    assert item.pt_dict["linha"]["espessura"] == 3

    # Altera espessura para 5
    item._definir_espessura(5)
    assert item.pt_dict["linha"]["espessura"] == 5
    assert item.pen().width() == 5


def test_dialogo_edicao_poi_com_espessura(qtbot):
    """Testa DialogoEdicaoPOI suportando espessura opcional para linhas."""
    from editor.views.widget_editor_mapas import DialogoEdicaoPOI

    # Diálogo com espessura
    dialogo_linha = DialogoEdicaoPOI("L1", "Linha 1", "#FF6D00", "Via 1", espessura_atual=4)
    assert dialogo_linha.obter_espessura() == 4
    dialogo_linha.input_espessura.setValue(7)
    assert dialogo_linha.obter_espessura() == 7

    # Diálogo sem espessura (POIs convencionais)
    dialogo_poi = DialogoEdicaoPOI("P1", "Ponto", "#00E676")
    assert dialogo_poi.obter_espessura() is None


def test_item_trajeto_linha_solicitar_espessura_personalizada(qtbot, monkeypatch):
    """Testa diálogo de espessura personalizada com QInputDialog."""
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtWidgets import QInputDialog, QGraphicsScene

    cena = QGraphicsScene()
    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "espessura": 3,
            "conteudo": {"nos": [{"x": 10, "y": 20}, {"x": 50, "y": 80}]}
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    cena.addItem(item)

    monkeypatch.setattr(QInputDialog, "getInt", lambda *args, **kwargs: (8, True))
    item._solicitar_espessura_personalizada()
    assert item.pt_dict["linha"]["espessura"] == 8
    assert item.pen().width() == 8

    # Se cancelar, mantém
    monkeypatch.setattr(QInputDialog, "getInt", lambda *args, **kwargs: (12, False))
    item._solicitar_espessura_personalizada()
    assert item.pt_dict["linha"]["espessura"] == 8


def test_dialogo_edicao_poi_id_obrigatorio(qtbot):
    from editor.views.widget_editor_mapas import DialogoEdicaoPOI
    from PySide6.QtWidgets import QDialogButtonBox

    dialogo = DialogoEdicaoPOI(id_atual="p1", label_atual="P1", texto_visivel_atual="", cor_atual="#FF6D00")
    qtbot.addWidget(dialogo)

    btn_ok = dialogo.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
    assert btn_ok.isEnabled() is True

    # Se apagar o ID, deve desabilitar o botão OK
    dialogo.input_id.setText("")
    assert btn_ok.isEnabled() is False

    # Se colocar apenas espaços em branco, continua desabilitado
    dialogo.input_id.setText("   ")
    assert btn_ok.isEnabled() is False

    # Se preencher, volta a habilitar
    dialogo.input_id.setText("p2")
    assert btn_ok.isEnabled() is True


def test_dialogo_edicao_poi_accept_bloqueado_sem_id(qtbot):
    from editor.views.widget_editor_mapas import DialogoEdicaoPOI
    from PySide6.QtWidgets import QDialog

    dialogo = DialogoEdicaoPOI(id_atual="", label_atual="", texto_visivel_atual="", cor_atual="#FF6D00")
    qtbot.addWidget(dialogo)
    
    dialogo.accept()
    assert dialogo.result() != QDialog.DialogCode.Accepted


def test_item_trajeto_linha_bordas_arredondadas(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import Qt

    for estilo in ["TRACEJADO", "PONTILHADO", "SOLIDO", "CAMINHADA"]:
        pt_dict = {
            "id": "via_teste",
            "linha": {
                "estilo": estilo,
                "espessura": 4,
                "conteudo": {"nos": [{"x": 0, "y": 0}, {"x": 100, "y": 100}]}
            }
        }
        item = ItemTrajetoLinha(pt_dict, lambda i: None)
        pen = item.pen()
        assert pen.capStyle() == Qt.PenCapStyle.RoundCap, f"Falha no estilo {estilo}: capStyle não é RoundCap"
        assert pen.joinStyle() == Qt.PenJoinStyle.RoundJoin, f"Falha no estilo {estilo}: joinStyle não é RoundJoin"


def test_alca_no_trajeto_tipo_string_e_int(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha, AlcaNoTrajeto

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "espessura": 3,
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": "PROTECAO_FIXA"},
                    {"x": 30, "y": 40, "tipo": 3},
                    {"x": 50, "y": 60, "tipo": "PROTECAO_MOVEL"},
                    {"x": 70, "y": 80, "tipo": 7},
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    
    alca0 = item.alcas[0]
    alca1 = item.alcas[1]
    alca2 = item.alcas[2]
    alca3 = item.alcas[3]

    # Tanto string quanto int devem retornar o mesmo valor numérico
    assert alca0.obter_tipo_int() == 3
    assert alca1.obter_tipo_int() == 3
    assert alca2.obter_tipo_int() == 7
    assert alca3.obter_tipo_int() == 7

    # Nome do tipo amigável
    assert alca0.obter_nome_tipo(alca0.obter_tipo_int()) == "Proteção Fixa [X]"
    assert alca0.obter_nome_tipo("PROTECAO_FIXA") == "Proteção Fixa [X]"
    assert alca2.obter_nome_tipo(alca2.obter_tipo_int()) == "Proteção Móvel [△]"
    assert alca2.obter_nome_tipo("PROTECAO_MOVEL") == "Proteção Móvel [△]"

    # Dimensões geométricas correspondentes
    assert alca0.rect().width() == 16
    assert alca1.rect().width() == 16
    assert alca2.rect().width() == 18
    assert alca3.rect().width() == 18


def test_alca_no_trajeto_menu_contexto_marca_tipo_ativo_string_ou_int(qtbot, monkeypatch):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtWidgets import QMenu
    from PySide6.QtCore import QPoint
    from unittest.mock import MagicMock

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": "PROTECAO_FIXA"}
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca = item.alcas[0]

    menu_exec_chamado = []
    acoes_criadas = []

    def mock_exec(self_menu, pos):
        menu_exec_chamado.append(self_menu)
        acoes_criadas.extend(self_menu.actions())

    monkeypatch.setattr(alca, "_executar_menu", mock_exec)

    evento_mock = MagicMock()
    evento_mock.screenPos.return_value = QPoint(100, 100)
    alca.contextMenuEvent(evento_mock)

    assert len(menu_exec_chamado) == 1
    # Título do menu
    assert "Tipo Atual: Proteção Fixa [X]" in acoes_criadas[0].text()

    # Verifica qual ação está marcada (checked)
    acoes_checadas = [a for a in acoes_criadas if a.isCheckable() and a.isChecked()]
    assert len(acoes_checadas) == 1
    assert "Proteção Fixa [X]" in acoes_checadas[0].text()
    assert "●" in acoes_checadas[0].text()


def test_alterar_tipo_no_atualiza_alca_e_simbolo(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 0},
                    {"x": 30, "y": 40, "tipo": 0}
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca = item.alcas[0]
    assert alca.obter_tipo_int() == 0
    assert alca.rect().width() == 8

    # Altera para PROTECAO_FIXA (3)
    item.alterar_tipo_no(0, 3)
    assert alca.obter_tipo_int() == 3
    assert alca.rect().width() == 16

    # Altera para PROTECAO_MOVEL (7)
    item.alterar_tipo_no(0, 7)
    assert alca.obter_tipo_int() == 7
    assert alca.rect().width() == 18


def test_botao_nova_linha_escalada_texto(qtbot):
    from editor.views.widget_editor_mapas import WidgetEditorMapas
    widget = WidgetEditorMapas()
    qtbot.addWidget(widget)
    assert "Nova Linha / Escalada" in widget.btn_add_linha.text()


def test_alca_no_trajeto_raio_e_tamanho_fonte_customizados(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1, "rotulo": "1"},  # Padrão
                    {"x": 50, "y": 60, "tipo": 1, "rotulo": "2", "raio": 25, "tamanho_fonte": 14},  # Customizado
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca_padrao = item.alcas[0]
    alca_custom = item.alcas[1]

    # Padrão: raio 12 (largura 24), fonte 8
    assert alca_padrao.obter_raio() == 12
    assert alca_padrao.obter_tamanho_fonte() == 8
    assert alca_padrao.rect().width() == 24
    assert alca_padrao.rect().height() == 24

    # Customizado: raio 25 (largura 50), fonte 14
    assert alca_custom.obter_raio() == 25
    assert alca_custom.obter_tamanho_fonte() == 14
    assert alca_custom.rect().width() == 50
    assert alca_custom.rect().height() == 50


def test_definir_raio_no_atualiza_alca(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1, "rotulo": "1"},
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca = item.alcas[0]
    assert alca.obter_raio() == 12

    item.definir_raio_no(0, 18)
    assert alca.obter_raio() == 18
    assert alca.rect().width() == 36
    assert alca.rect().height() == 36
    assert item.pt_dict["linha"]["conteudo"]["nos"][0]["raio"] == 18


def test_definir_tamanho_fonte_no_atualiza_alca(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1, "rotulo": "1"},
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca = item.alcas[0]
    assert alca.obter_tamanho_fonte() == 8

    item.definir_tamanho_fonte_no(0, 15)
    assert alca.obter_tamanho_fonte() == 15
    assert item.pt_dict["linha"]["conteudo"]["nos"][0]["tamanho_fonte"] == 15


def test_alca_no_trajeto_menu_contexto_opcoes_raio_e_fonte_para_circulo_identificador(qtbot, monkeypatch):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import QPoint
    from unittest.mock import MagicMock

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1, "rotulo": "1", "raio": 16, "tamanho_fonte": 10}
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca = item.alcas[0]

    acoes_criadas = []
    monkeypatch.setattr(alca, "_executar_menu", lambda m, pos: acoes_criadas.extend([a.text() for a in m.actions()]))

    evento_mock = MagicMock()
    evento_mock.screenPos.return_value = QPoint(100, 100)
    alca.contextMenuEvent(evento_mock)

    assert any("Tamanho do Círculo" in t and "16" in t for t in acoes_criadas)
    assert any("Tamanho da Fonte" in t and "10" in t for t in acoes_criadas)


def test_alca_no_trajeto_fim_top_circulo_identificador(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha, AlcaNoTrajeto
    from PySide6.QtGui import QPixmap, QPainter

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1, "rotulo": "1", "raio": 18, "tamanho_fonte": 12},  # Começo
                    {"x": 30, "y": 40, "tipo": 1, "rotulo": "P1"},  # Meio (ex: Parada 1)
                    {"x": 50, "y": 60, "tipo": 1, "rotulo": "T"},   # Fim (ex: Top)
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca_inicio = item.alcas[0]
    alca_meio = item.alcas[1]
    alca_fim = item.alcas[2]

    # Começo
    assert alca_inicio.obter_tipo_int() == 1
    assert alca_inicio.obter_nome_tipo(1) == "Círculo Identificador"
    assert alca_inicio.obter_rotulo_exibicao() == "1"
    assert alca_inicio.obter_raio() == 18
    assert alca_inicio.obter_tamanho_fonte() == 12
    assert alca_inicio.rect().width() == 36

    # Meio
    assert alca_meio.obter_tipo_int() == 1
    assert alca_meio.obter_rotulo_exibicao() == "P1"
    assert alca_meio.obter_raio() == 12
    assert alca_meio.obter_tamanho_fonte() == 8

    # Fim
    assert alca_fim.obter_tipo_int() == 1
    assert alca_fim.obter_rotulo_exibicao() == "T"

    # Renderiza todos sem erro
    pixmap = QPixmap(100, 100)
    painter = QPainter(pixmap)
    alca_inicio.paint(painter, None)
    alca_meio.paint(painter, None)
    alca_fim.paint(painter, None)
    painter.end()


def test_alterar_tipo_para_circulo_identificador_em_qualquer_posicao(qtbot):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 0},
                    {"x": 30, "y": 40, "tipo": 0},
                    {"x": 50, "y": 60, "tipo": 0},
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca_meio = item.alcas[1]
    alca_fim = item.alcas[2]
    
    # Altera nó do meio para Círculo Identificador
    item.alterar_tipo_no(1, 1)
    assert alca_meio.obter_tipo_int() == 1
    item.definir_rotulo_no(1, "Variante")
    assert alca_meio.obter_rotulo_exibicao() == "Variante"

    # Altera nó do fim para Círculo Identificador com rótulo "TOP"
    item.alterar_tipo_no(2, 1)
    assert alca_fim.obter_tipo_int() == 1
    item.definir_rotulo_no(2, "TOP")
    assert alca_fim.obter_rotulo_exibicao() == "TOP"


def test_menu_contexto_inclui_opcao_circulo_identificador_generico(qtbot, monkeypatch):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import QPoint
    from unittest.mock import MagicMock

    pt_dict = {
        "id": "via_1",
        "linha": {
            "estilo": "TRACEJADO",
            "conteudo": {
                "nos": [
                    {"x": 10, "y": 20, "tipo": 1}
                ]
            }
        }
    }
    item = ItemTrajetoLinha(pt_dict, lambda i: None)
    alca = item.alcas[0]

    acoes_criadas = []
    monkeypatch.setattr(alca, "_executar_menu", lambda m, pos: acoes_criadas.extend([a.text() for a in m.actions()]))

    evento_mock = MagicMock()
    evento_mock.screenPos.return_value = QPoint(100, 100)
    alca.contextMenuEvent(evento_mock)

    assert any("● Círculo Identificador" in t for t in acoes_criadas)
    assert not any("Início/Base" in t for t in acoes_criadas)
    assert not any("Fim/Top" in t for t in acoes_criadas)
    assert any("Tamanho do Círculo" in t for t in acoes_criadas)
    assert any("Tamanho da Fonte" in t for t in acoes_criadas)
    assert any("Definir Rótulo / Número do Nó" in t for t in acoes_criadas)


def test_item_trajeto_linha_menu_contexto_opcao_cor_personalizada(qtbot, monkeypatch):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtCore import QPointF, QPoint
    from PySide6.QtWidgets import QMenu
    from unittest.mock import MagicMock

    pt_dict = {
        "id": "v1",
        "cor": "#FF6D00",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 0, "y": 0, "tipo": 1},
                    {"x": 100, "y": 100, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)

    acoes_por_submenu = {}
    def mock_executar_menu(menu, pos):
        for action in menu.actions():
            sub = action.menu()
            if sub:
                acoes_por_submenu[action.text()] = [a.text() for a in sub.actions()]
        return None

    monkeypatch.setattr(item_linha, "_executar_menu", mock_executar_menu)

    evento_mock = MagicMock()
    evento_mock.pos.return_value = QPointF(50, 50)
    evento_mock.screenPos.return_value = QPoint(100, 100)
    item_linha.contextMenuEvent(evento_mock)

    nome_menu_cores = next((k for k in acoes_por_submenu if "Mudar Cor" in k), None)
    assert nome_menu_cores is not None, "Submenu Mudar Cor não foi encontrado"
    textos_acoes = acoes_por_submenu[nome_menu_cores]
    
    # Verifica que as cores da paleta existem e a cor atual (#FF6D00) está marcada
    assert any("Laranja" in t and "●" in t for t in textos_acoes)
    # Verifica que existe a ação de Cor Personalizada com diálogo
    assert any("Personalizada" in t for t in textos_acoes)


def test_item_trajeto_linha_solicitar_cor_personalizada_aplica_cor(qtbot, monkeypatch):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtGui import QColor

    pt_dict = {
        "id": "v1",
        "cor": "#FF6D00",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 0, "y": 0, "tipo": 1},
                    {"x": 100, "y": 100, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)
    assert item_linha.cor_hex == "#FF6D00"

    # Simula o usuário escolhendo a cor #00E5FF no diálogo
    monkeypatch.setattr(item_linha, "_obter_cor_dialogo", lambda cor_inicial: QColor("#00E5FF"))
    item_linha._solicitar_cor_personalizada()

    assert item_linha.cor_hex == "#00E5FF"
    assert item_linha.pt_dict["cor"] == "#00E5FF"


def test_item_trajeto_linha_solicitar_cor_personalizada_cancelado_mantem_cor(qtbot, monkeypatch):
    from editor.views.widget_editor_mapas import ItemTrajetoLinha
    from PySide6.QtGui import QColor

    pt_dict = {
        "id": "v1",
        "cor": "#FF6D00",
        "linha": {
            "conteudo": {
                "nos": [
                    {"x": 0, "y": 0, "tipo": 1},
                    {"x": 100, "y": 100, "tipo": 5}
                ]
            }
        }
    }
    item_linha = ItemTrajetoLinha(pt_dict, lambda item: None)

    # Simula o cancelamento do diálogo (retorna QColor inválida)
    monkeypatch.setattr(item_linha, "_obter_cor_dialogo", lambda cor_inicial: QColor())
    item_linha._solicitar_cor_personalizada()

    assert item_linha.cor_hex == "#FF6D00"
    assert item_linha.pt_dict["cor"] == "#FF6D00"







