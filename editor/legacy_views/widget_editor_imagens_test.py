# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import os
from PySide6.QtWidgets import QApplication
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_folder(tmp_path):
    imagens_dir = tmp_path / "imagens"
    imagens_dir.mkdir()
    (imagens_dir / "imagem1.webp").write_text("dummy")
    return str(tmp_path)

def test_widget_inicializa_em_modo_integrado(qtbot, mock_folder):
    # O widget deve aceitar o modo_integrado no construtor
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder, modo_integrado=True)
        qtbot.addWidget(widget)
        
        # Verifica se o botão de salvar está oculto
        assert widget.save_btn.isHidden()

def test_widget_inicializa_em_modo_autonomo(qtbot, mock_folder):
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder, modo_integrado=False)
        qtbot.addWidget(widget)
        
        # Verifica se o botão de salvar está visível
        assert not widget.save_btn.isHidden()

def test_widget_lista_imagens_da_pasta(qtbot, mock_folder):
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder)
        qtbot.addWidget(widget)
        
        assert widget.list_widget.count() == 1
        assert "imagem1.webp" in widget.list_widget.item(0).text()

def test_widget_expoe_metodo_salvar_alteracoes(qtbot, mock_folder):
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder)
        qtbot.addWidget(widget)
        
        # Verifica se o método existe
        assert hasattr(widget, "salvar_alteracoes")
        assert callable(widget.salvar_alteracoes)


def test_rotacao_horaria_com_controller_e_undo_redo(qtbot, tmp_path):
    from PIL import Image
    import io
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste.webp"
    img = Image.new("RGB", (200, 100), color=(10, 20, 30))
    img.save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste.webp")

    # Rotação horária 90°
    widget.rotate_cw_btn.click()
    assert undo_stack.count() == 1

    bytes_rot = model.obter_bytes_imagem("imagens/teste.webp")
    assert bytes_rot is not None
    with Image.open(io.BytesIO(bytes_rot)) as im:
        assert (im.width, im.height) == (100, 200)

    # Undo
    undo_stack.undo()
    bytes_undo = model.obter_bytes_imagem("imagens/teste.webp")
    with Image.open(io.BytesIO(bytes_undo)) as im:
        assert (im.width, im.height) == (200, 100)

    # Redo
    undo_stack.redo()
    bytes_redo = model.obter_bytes_imagem("imagens/teste.webp")
    with Image.open(io.BytesIO(bytes_redo)) as im:
        assert (im.width, im.height) == (100, 200)


def test_rotacao_anti_horaria_com_controller(qtbot, tmp_path):
    from PIL import Image
    import io
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_ccw.webp"
    img = Image.new("RGB", (300, 150), color=(10, 20, 30))
    img.save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_ccw.webp")

    # Rotação anti-horária -90°
    widget.rotate_ccw_btn.click()
    assert undo_stack.count() == 1

    bytes_rot = model.obter_bytes_imagem("imagens/teste_ccw.webp")
    assert bytes_rot is not None
    with Image.open(io.BytesIO(bytes_rot)) as im:
        assert (im.width, im.height) == (150, 300)


def test_rotacao_sem_imagem_selecionada(qtbot, tmp_path):
    widget = WidgetEditorImagens(imagens_path=str(tmp_path))
    qtbot.addWidget(widget)
    widget.current_file = None

    # Não deve lançar exceção
    widget.rotate_cw_btn.click()
    widget.rotate_ccw_btn.click()


def test_modo_corte_ativacao_e_cancelamento_com_escape(qtbot, tmp_path):
    from PIL import Image
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from PySide6.QtCore import Qt

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_corte.webp"
    Image.new("RGB", (200, 200), color=(10, 20, 30)).save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_corte.webp")

    # Inicialmente não está em modo de corte
    assert getattr(widget, "modo_corte", False) is False

    # Clica no botão de corte -> ativa modo_corte
    widget.crop_btn.click()
    assert widget.modo_corte is True

    # Pressiona tecla Escape -> cancela
    qtbot.keyClick(widget.viewer, Qt.Key.Key_Escape)
    assert widget.modo_corte is False


def test_executar_corte_selecao_com_controller_e_undo_redo(qtbot, tmp_path):
    from PIL import Image
    import io
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_corte_exec.webp"
    Image.new("RGB", (200, 200), color=(10, 20, 30)).save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_corte_exec.webp")

    widget.crop_btn.click()
    assert widget.modo_corte is True

    # Executa corte de (10, 20) a (60, 80) -> largura=50, altura=60
    widget.executar_corte_selecao(10, 20, 60, 80)
    assert widget.modo_corte is False
    assert undo_stack.count() == 1

    bytes_cortados = model.obter_bytes_imagem("imagens/teste_corte_exec.webp")
    assert bytes_cortados is not None
    with Image.open(io.BytesIO(bytes_cortados)) as im:
        assert (im.width, im.height) == (50, 60)

    # Desfazer restaura tamanho original 200x200
    undo_stack.undo()
    bytes_undo = model.obter_bytes_imagem("imagens/teste_corte_exec.webp")
    with Image.open(io.BytesIO(bytes_undo)) as im:
        assert (im.width, im.height) == (200, 200)


def test_executar_corte_selecao_invalida_ou_muito_pequena_ignorada(qtbot, tmp_path):
    from PIL import Image
    import io
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_corte_pequeno.webp"
    Image.new("RGB", (200, 200), color=(10, 20, 30)).save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_corte_pequeno.webp")

    widget.crop_btn.click()

    # Seleção de apenas 5x5 pixels (menor que 10px) deve ser ignorada
    widget.executar_corte_selecao(10, 10, 15, 15)
    assert undo_stack.count() == 0

    bytes_atual = model.obter_bytes_imagem("imagens/teste_corte_pequeno.webp")
    with Image.open(io.BytesIO(bytes_atual)) as im:
        assert (im.width, im.height) == (200, 200)


def test_modo_mascara_ativacao_e_cancelamento_com_escape(qtbot, tmp_path):
    from PIL import Image
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from PySide6.QtCore import Qt

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_mask.webp"
    Image.new("RGB", (100, 100), color=(10, 20, 30)).save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_mask.webp")

    assert getattr(widget, "modo_mascara", False) is False

    widget.add_mask_btn.click()
    assert widget.modo_mascara is True

    qtbot.keyClick(widget.viewer, Qt.Key.Key_Escape)
    assert widget.modo_mascara is False


def test_modo_mascara_captura_e_preenchimento_com_undo_redo(qtbot, tmp_path):
    from PIL import Image
    import io
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_mask_exec.webp"
    img = Image.new("RGB", (100, 100), color=(0, 0, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(img).rectangle([0, 0, 10, 10], fill=(255, 0, 0))
    img.save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_mask_exec.webp")

    widget.add_mask_btn.click()
    assert widget.modo_mascara is True

    # Captura a cor do pixel (5, 5) que é vermelho
    widget.capturar_cor_ponto(5, 5)
    assert all(abs(a - b) <= 2 for a, b in zip(widget.cor_mascara_atual, (255, 0, 0)))

    # Aplica máscara retangular cobrindo (20, 20) até (60, 60)
    widget.aplicar_mascara_selecao(20, 20, 60, 60)
    assert undo_stack.count() == 1

    bytes_mascarados = model.obter_bytes_imagem("imagens/teste_mask_exec.webp")
    with Image.open(io.BytesIO(bytes_mascarados)) as im:
        # Pixel (30, 30) deve ser vermelho
        assert all(abs(a - b) <= 2 for a, b in zip(im.getpixel((30, 30))[:3], (255, 0, 0)))

    # Desfazer reverte para preto
    undo_stack.undo()
    bytes_undo = model.obter_bytes_imagem("imagens/teste_mask_exec.webp")
    with Image.open(io.BytesIO(bytes_undo)) as im:
        assert all(abs(a - b) <= 2 for a, b in zip(im.getpixel((30, 30))[:3], (0, 0, 0)))


def test_aplicar_mascara_sem_cor_capturada_ignorado(qtbot, tmp_path):
    from PIL import Image
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    caminho_img = pasta_img / "teste_mask_sem_cor.webp"
    Image.new("RGB", (100, 100), color=(0, 0, 0)).save(caminho_img, format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("teste_mask_sem_cor.webp")

    widget.cor_mascara_atual = None
    widget.aplicar_mascara_selecao(10, 10, 50, 50)
    assert undo_stack.count() == 0


def test_botoes_obsoletos_removidos_e_barra_simplificada(qtbot, tmp_path):
    from PIL import Image
    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    Image.new("RGB", (20, 20), color=(10, 20, 30)).save(pasta_img / "teste.webp", format="WEBP")

    widget = WidgetEditorImagens(imagens_path=str(pasta_img))
    qtbot.addWidget(widget)

    # Botões Resetar e Limpar Máscaras foram removidos
    assert not hasattr(widget, "reset_btn")
    assert not hasattr(widget, "clear_masks_btn")
    assert not hasattr(widget, "reset_crop")

    # Botão de corte não possui mais '(Preview)'
    assert widget.crop_btn.text() == "✂ Cortar"
    assert "Máscara" in widget.add_mask_btn.text()


def test_imagem_ajustada_ao_visualizador_ao_ser_exibido(qtbot, tmp_path):
    from PIL import Image
    from PySide6.QtWidgets import QStackedWidget

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    Image.new("RGB", (2000, 1500), color=(10, 20, 30)).save(pasta_img / "foto.webp", format="WEBP")

    stack = QStackedWidget()
    widget = WidgetEditorImagens(imagens_path=str(pasta_img))
    stack.addWidget(widget)
    qtbot.addWidget(stack)

    # Imagem carregada antes de ser exibida (como ocorre na abertura do croqui na aba de dados)
    widget.select_image_by_name("foto.webp")

    # Exibe a janela e dimensiona para tela cheia / janela ampla
    stack.resize(1000, 800)
    stack.show()
    qtbot.waitExposed(stack)

    # Verifica se a imagem no visualizador foi ajustada para cobrir a tela (não é mais minúscula)
    rect_viewport = widget.viewer.mapFromScene(widget.viewer.scene().sceneRect()).boundingRect()
    vp_w = widget.viewer.viewport().width()
    vp_h = widget.viewer.viewport().height()

    assert vp_w > 500
    assert vp_h > 400
    # A imagem deve ocupar a maior parte da área visível disponível
    assert rect_viewport.width() >= 0.7 * vp_w or rect_viewport.height() >= 0.7 * vp_h


def test_botoes_transformacao_atualizam_cena_e_visualizador(qtbot, tmp_path):
    from PIL import Image
    from PySide6.QtGui import QUndoStack
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from aresta_api.proto.generated import croqui_pb2

    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    Image.new("RGB", (200, 100), color=(10, 20, 30)).save(pasta_img / "foto_transf.webp", format="WEBP")

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
    qtbot.addWidget(widget)
    widget.select_image_by_name("foto_transf.webp")

    assert widget.viewer.scene().sceneRect().width() == 200.0
    assert widget.viewer.scene().sceneRect().height() == 100.0

    # 1. Girar 90 graus
    widget.rotate_image(90)
    assert widget.viewer.scene().sceneRect().width() == 100.0
    assert widget.viewer.scene().sceneRect().height() == 200.0

    # Undo
    undo_stack.undo()
    assert widget.viewer.scene().sceneRect().width() == 200.0
    assert widget.viewer.scene().sceneRect().height() == 100.0

    # 2. Cortar
    widget.executar_corte_selecao(10, 10, 60, 50)
    assert widget.viewer.scene().sceneRect().width() == 50.0
    assert widget.viewer.scene().sceneRect().height() == 40.0

    # Undo corte
    undo_stack.undo()
    assert widget.viewer.scene().sceneRect().width() == 200.0
    assert widget.viewer.scene().sceneRect().height() == 100.0






