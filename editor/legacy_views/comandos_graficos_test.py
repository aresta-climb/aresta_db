import pytest
import copy
from PyQt6.QtCore import QPointF, QRectF, Qt, QPoint
from PyQt6.QtWidgets import QApplication, QLineEdit
from PyQt6.QtTest import QTest
from editor.legacy_views.area_principal import JanelaPrincipal
from editor.legacy_views.editor_mapas import CmdMoverPonto
from editor.legacy_views.widget_editor_imagens import CmdMoverImagem

def drag_item(view, item, delta):
    pos_inicial = view.mapFromScene(item.sceneBoundingRect().center())
    pos_final = pos_inicial + delta.toPoint()
    
    # QTest mouse events are headless-safe
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos_inicial)
    QApplication.processEvents()
    
    QTest.mouseMove(view.viewport(), pos_final)
    QApplication.processEvents()
    
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, pos_final)
    QApplication.processEvents()

def test_comandos_graficos_e_cross_pagina(tmp_path, qtbot):
    # 1. Configura ambiente de testes com mapa e imagem fakes
    db_path = tmp_path / "database"
    db_path.mkdir()
    
    img_path = tmp_path / "imagens"
    img_path.mkdir()
    
    # Cria imagem de teste fake
    from PIL import Image
    im = Image.new("RGB", (200, 200), "blue")
    im_file = img_path / "imagem1.png"
    im.save(im_file)
    
    # Cria arquivo markdown de mapa fake
    map_file = db_path / "setor_teste.md"
    map_content = """---
nome: Setor Teste
mapas:
  - caminho_imagem_mapa: ../imagens/imagem1.png
    pontos_de_interesse:
      - id: "P1"
        label: "Via 1"
        box:
          x: 100
          y: 100
          comprimento: 40
          largura: 40
---
Corpo do MD
"""
    map_file.write_text(map_content, encoding="utf-8")
    
    # Cria croqui.yaml fake
    croqui_file = db_path / "croqui.yaml"
    croqui_file.write_text("id: 'croqui_teste'\nnome: 'Croqui Teste'\npicos: []\n", encoding="utf-8")
    
    # Inicializa a JanelaPrincipal apontando para a pasta temporária
    janela = JanelaPrincipal(caminho_croqui=tmp_path)
    qtbot.addWidget(janela)
    janela.resize(1200, 800)
    
    # Processa eventos pendentes para carregar
    QApplication.processEvents()
    
    # 2. VALIDAÇÃO UNITÁRIA DO CMDMOVERPONTO (Mapa)
    editor_mapas = janela.pagina_mapas.editor
    assert len(editor_mapas.dados_arquivos) == 1
    chave_mapa = list(editor_mapas.dados_arquivos.keys())[0]
    dados = editor_mapas.dados_arquivos[chave_mapa]
    item_poi = dados['itens_bb'][0]
    
    estado_original_poi = copy.deepcopy(item_poi.obter_dict_atualizado())
    estado_novo_poi = copy.deepcopy(estado_original_poi)
    estado_novo_poi['box']['x'] = 150
    estado_novo_poi['box']['y'] = 150
    
    cmd_poi = CmdMoverPonto(chave_mapa, 0, estado_original_poi, estado_novo_poi, editor_mapas)
    janela.historico.executar(cmd_poi)
    
    # Verifica que mudou
    assert item_poi.pt_dict['box']['x'] == 150
    
    # Desfaz
    janela.historico.desfazer()
    assert item_poi.pt_dict['box']['x'] == 100
    
    # Refaz
    janela.historico.refazer()
    assert item_poi.pt_dict['box']['x'] == 150
    
    # Limpa pilha
    janela.historico.limpar()
    
    # 3. VALIDAÇÃO UNITÁRIA DO CMDMOVERIMAGEM (Imagem)
    editor_imagens = janela.pagina_imagens.editor
    assert editor_imagens.list_widget.count() == 1
    caminho_imagem = str(im_file)
    
    editor_imagens.load_image(caminho_imagem)
    crop_item = editor_imagens.crop_item
    
    estado_original_crop = (crop_item.rect(), crop_item.pos())
    estado_novo_crop = (QRectF(10, 10, 60, 60), QPointF(5, 5))
    
    cmd_crop = CmdMoverImagem(caminho_imagem, estado_original_crop, estado_novo_crop, editor_imagens)
    janela.historico.executar(cmd_crop)
    
    # Verifica que mudou
    assert crop_item.rect().width() == 60
    
    # Desfaz
    janela.historico.desfazer()
    assert crop_item.rect().width() == estado_original_crop[0].width()
    
    # Refaz
    janela.historico.refazer()
    assert crop_item.rect().width() == 60
    
    # Limpa pilha
    janela.historico.limpar()
    
    # 4. FLUXO INTEGRADO MULTI-PÁGINAS (CROSS-TAB)
    # Ação A: Aba de Dados - Altera nome do Croqui
    janela._trocar_pagina(0)
    editor_dados = janela.pagina_dados.editor_dados
    form = editor_dados.form_padrao
    
    # Seleciona o nó raiz na árvore
    croqui_idx = editor_dados.tree_model.index(0, 0)
    editor_dados.tree_view.selectionModel().select(
        croqui_idx,
        editor_dados.tree_view.selectionModel().SelectionFlag.ClearAndSelect
    )
    editor_dados._on_tree_selection_changed(None, None)
    
    line_edits = form.findChildren(QLineEdit)
    edit_nome = next(le for le in line_edits if le.property("protobuf_field") == "nome")
    edit_nome.setText("Nome Alterado E2E")
    
    
    assert janela.historico.obter_pilha().count() == 1
    
    # Ação B: Aba de Mapas - Arrasta o POI graficamente via QTest
    janela._trocar_pagina(2)
    QApplication.processEvents()
    view_mapa = editor_mapas.visualizador
    
    # Arrasta o POI por 50 pixels
    drag_item(view_mapa, item_poi, QPointF(50, 50))
    
    # Deve ter registrado o comando de arrasto no histórico
    assert janela.historico.obter_pilha().count() == 2
    
    # Ação C: Aba de Imagens - Arrasta a Crop Box graficamente via QTest
    janela._trocar_pagina(1)
    QApplication.processEvents()
    view_img = editor_imagens.viewer
    
    # Grava a posição inicial específica do E2E antes do drag
    pos_inicio_crop_e2e = crop_item.pos()
    
    # Arrasta o crop_item por 30 pixels
    drag_item(view_img, crop_item, QPointF(30, 30))
    
    # Deve ter registrado o comando de arrasto da imagem no histórico
    assert janela.historico.obter_pilha().count() == 3
    
    # 5. DESFAZER SEQUENCIAL CROSS-TAB
    # Desfaz 1: Deve desfazer o arraste na imagem
    janela.historico.desfazer()
    assert crop_item.pos() == pos_inicio_crop_e2e
    
    # Desfaz 2: Deve desfazer o arraste do POI no mapa
    janela.historico.desfazer()
    assert item_poi.pt_dict['box']['x'] == 150
    
    # Desfaz 3: Deve desfazer a edição de texto na aba de dados
    janela.historico.desfazer()
    janela._trocar_pagina(0)
    line_edits_pos_undo = form.findChildren(QLineEdit)
    edit_nome_pos_undo = next(le for le in line_edits_pos_undo if le.property("protobuf_field") == "nome")
    assert edit_nome_pos_undo.text() == "Croqui Teste"
    
    # 6. REFAZER SEQUENCIAL CROSS-TAB
    # Refaz 1: Restaura edição de texto
    janela.historico.refazer()
    line_edits_pos_redo = form.findChildren(QLineEdit)
    edit_nome_pos_redo = next(le for le in line_edits_pos_redo if le.property("protobuf_field") == "nome")
    assert edit_nome_pos_redo.text() == "Nome Alterado E2E"
    
    # Refaz 2: Restaura arraste do POI
    janela.historico.refazer()
    assert item_poi.pt_dict['box']['x'] != 150
    
    # Refaz 3: Restaura crop box da imagem
    janela.historico.refazer()
    assert crop_item.pos() != pos_inicio_crop_e2e
    
    # Evita que closeEvent abra a caixa de diálogo QMessageBox perguntando se deseja salvar
    janela.is_dirty = False

