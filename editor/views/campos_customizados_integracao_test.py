# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QUndoStack
from PyQt6.QtCore import QItemSelectionModel

from aresta_api.proto.generated.croqui_pb2 import Croqui, Coordenada
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from editor.views.widget_editor_dados import WidgetEditorDados
from editor.views.widget_campo_coordenada_e7 import WidgetCampoCoordenadaE7, TipoCoordenada
from editor.views.widget_mensagem_coordenada import WidgetMensagemCoordenada
from editor.views.widget_campo_imagem import WidgetCampoImagem


@pytest.fixture
def imagem_teste_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(buf, format="WEBP")
    return buf.getvalue()


class TestCamposCustomizadosIntegracao:
    def test_integracao_renderizacao_e_edicao_coordenada_e7(self, qtbot):
        croqui = Croqui()
        pico = croqui.picos.add(nome="Pico 1")
        pico.localizacao.latitude = -198980280
        pico.localizacao.longitude = -435212340

        model = CroquiModel(croqui)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget_editor = WidgetEditorDados(model, controller=controller)
        qtbot.addWidget(widget_editor)

        # Seleciona o Pico na árvore para renderizar seu formulário
        modelo = widget_editor.tree_model
        croqui_idx = modelo.index(0, 0)
        expando_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
        pico_idx = modelo.index(0, 0, expando_picos)
        widget_editor.tree_view.selectionModel().setCurrentIndex(pico_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)

        # Localiza o widget de mensagem de coordenada integrado
        widgets_coord = widget_editor.findChildren(WidgetMensagemCoordenada)
        assert len(widgets_coord) == 1, "Deve ser renderizado 1 WidgetMensagemCoordenada integrado"

        widget_coord = widgets_coord[0]
        assert widget_coord.obter_latitude_graus() == pytest.approx(-19.898028)
        assert widget_coord.obter_longitude_graus() == pytest.approx(-43.521234)
        assert widget_coord.btn_colar.text() == "Colar"
        assert widget_coord.btn_maps.text() == "Abrir no Maps"

        # Simula alteração do valor pelo widget
        widget_coord.edit_lat.setText("-20.1234567")
        widget_coord._confirmar_edicao_lat()

        assert pico.localizacao.latitude == -201234567
        assert undo_stack.canUndo() is True

        # Testa Undo
        undo_stack.undo()
        assert pico.localizacao.latitude == -198980280
        assert widget_coord.obter_latitude_graus() == pytest.approx(-19.898028)

        # Testa Redo
        undo_stack.redo()
        assert pico.localizacao.latitude == -201234567
        assert widget_coord.obter_latitude_graus() == pytest.approx(-20.1234567)

    def test_integracao_renderizacao_e_edicao_campo_imagem(self, qtbot, imagem_teste_bytes, tmp_path):
        croqui = Croqui()
        croqui.caminho_thumbnail = "imagens/capa_inicial.webp"

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget_editor = WidgetEditorDados(model, controller=controller)
        qtbot.addWidget(widget_editor)

        # Seleciona a raiz do Croqui
        croqui_idx = widget_editor.tree_model.index(0, 0)
        widget_editor.tree_view.selectionModel().setCurrentIndex(croqui_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)

        # Localiza o widget de imagem
        widgets_img = widget_editor.findChildren(WidgetCampoImagem)
        assert len(widgets_img) >= 1, "Deve ser renderizado o WidgetCampoImagem para caminho_thumbnail"

        widget_thumb = widgets_img[0]
        assert widget_thumb.obter_caminho_atual() == "imagens/capa_inicial.webp"

        # Simula troca de imagem em memória
        widget_thumb.aplicar_nova_imagem("imagens/thumbnail.webp", imagem_teste_bytes)

        assert croqui.caminho_thumbnail == "imagens/thumbnail.webp"
        assert model.obter_bytes_imagem("imagens/thumbnail.webp") == imagem_teste_bytes
        # Nenhum arquivo deve ter sido criado em disco ainda
        assert not (tmp_path / "imagens" / "thumbnail.webp").exists()

        # Testa Undo
        undo_stack.undo()
        assert croqui.caminho_thumbnail == "imagens/capa_inicial.webp"
        assert model.obter_bytes_imagem("imagens/thumbnail.webp") is None

        # Testa Redo
        undo_stack.redo()
        assert croqui.caminho_thumbnail == "imagens/thumbnail.webp"
        assert model.obter_bytes_imagem("imagens/thumbnail.webp") == imagem_teste_bytes

    def test_integracao_coordenada_vazia_e_zero(self, qtbot):
        croqui = Croqui()
        pico = croqui.picos.add(nome="Pico 2")
        # Sem coordenadas definidas inicialmente (campos ausentes)

        model = CroquiModel(croqui)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget_editor = WidgetEditorDados(model, controller=controller)
        qtbot.addWidget(widget_editor)

        # Seleciona o Pico na árvore
        modelo = widget_editor.tree_model
        croqui_idx = modelo.index(0, 0)
        expando_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
        pico_idx = modelo.index(0, 0, expando_picos)
        widget_editor.tree_view.selectionModel().setCurrentIndex(pico_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)

        widgets_coord = widget_editor.findChildren(WidgetMensagemCoordenada)
        widget_coord = widgets_coord[0]

        # Inicialmente deve estar vazio
        assert widget_coord.edit_lat.text() == ""
        assert widget_coord.obter_latitude_graus() is None
        assert widget_coord.obter_latitude_e7() is None

        # Digita 0 (Equador)
        widget_coord.edit_lat.setText("0")
        widget_coord._confirmar_edicao_lat()

        assert pico.localizacao.latitude == 0
        assert widget_coord.obter_latitude_e7() == 0
        assert widget_coord.rotulo_cardinal_lat.text() == "Equador"

        # Apaga o texto (vazio / opcional)
        widget_coord.edit_lat.setText("")
        widget_coord._confirmar_edicao_lat()

        assert not pico.localizacao.HasField("latitude")
        assert widget_coord.obter_latitude_e7() is None

