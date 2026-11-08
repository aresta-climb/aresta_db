# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io

import pytest
from PIL import Image
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QDialog

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa
from editor.views.widget_editor_mapas import WidgetEditorMapas


@pytest.fixture
def croqui_com_mapa(tmp_path):
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico Teste")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor A"

    mapa = setor.mapas.add()
    mapa.caminho_imagem_mapa = "imagens/mapa_setor_a.webp"
    mapa.largura_mapa = 400
    mapa.altura_mapa = 300
    poi = mapa.pontos_de_interesse.add(uid="poi_1", rotulo="1")
    poi.circulo.x = 200
    poi.circulo.y = 150
    poi.circulo.raio = 20

    buf = io.BytesIO()
    img = Image.new("RGB", (400, 300), color=(50, 100, 150))
    img.save(buf, format="WEBP")
    bytes_iniciais = buf.getvalue()

    model = CroquiModel(croqui)
    model.definir_caminho_db(tmp_path)
    model.definir_imagem_memoria("imagens/mapa_setor_a.webp", bytes_iniciais)

    return model, mapa, bytes_iniciais


class TestWidgetEditorMapasImagem:
    def test_inicializacao_botoes_imagem(self, qtbot, croqui_com_mapa):
        model, mapa, _ = croqui_com_mapa
        controller = CroquiController(model, QUndoStack())
        widget = WidgetEditorMapas(croqui_model=model, croqui_controller=controller)
        qtbot.addWidget(widget)

        assert hasattr(widget, "btn_substituir_imagem")
        assert hasattr(widget, "btn_abrir_editor_imagens")
        assert widget.btn_substituir_imagem.text() == " Substituir Imagem..."
        assert widget.btn_abrir_editor_imagens.text() == " Abrir no Editor de Imagens"

    def test_substituir_imagem_mapa_via_wizard_com_reescala_pois_e_undo_redo(
        self, qtbot, croqui_com_mapa, tmp_path, monkeypatch
    ):
        model, mapa, bytes_iniciais = croqui_com_mapa
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)
        widget = WidgetEditorMapas(croqui_model=model, croqui_controller=controller)
        qtbot.addWidget(widget)

        widget.carregar_mapa(mapa)

        nova_img_path = tmp_path / "nova_foto.png"
        img_nova = Image.new("RGB", (800, 600), color=(200, 100, 50))
        img_nova.save(nova_img_path, format="PNG")

        def fake_exec(self_dlg):
            assert self_dlg.modo_substituicao_mapa is True
            assert self_dlg.largura_mapa_antiga == 400
            assert self_dlg.altura_mapa_antiga == 300
            self_dlg.carregar_imagem_arquivo(str(nova_img_path))
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

        widget.substituir_imagem_mapa()

        bytes_substituidos = model.obter_bytes_imagem("imagens/mapa_setor_a.webp")
        assert bytes_substituidos != bytes_iniciais
        assert bytes_substituidos.startswith(b"RIFF")
        assert mapa.largura_mapa == 800
        assert mapa.altura_mapa == 600
        assert mapa.pontos_de_interesse[0].circulo.x == 400
        assert mapa.pontos_de_interesse[0].circulo.y == 300
        assert mapa.pontos_de_interesse[0].circulo.raio == 40
        assert undo_stack.count() == 1

        # Undo reverte bytes, dimensões e POIs
        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_iniciais
        assert mapa.largura_mapa == 400
        assert mapa.altura_mapa == 300
        assert mapa.pontos_de_interesse[0].circulo.x == 200
        assert mapa.pontos_de_interesse[0].circulo.y == 150
        assert mapa.pontos_de_interesse[0].circulo.raio == 20

        # Redo reaplica tudo
        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_substituidos
        assert mapa.largura_mapa == 800
        assert mapa.altura_mapa == 600
        assert mapa.pontos_de_interesse[0].circulo.x == 400

    def test_substituir_imagem_mapa_via_mapas_controller_com_undo_redo(
        self, qtbot, croqui_com_mapa, tmp_path, monkeypatch
    ):
        from editor.controllers.mapas_controller import MapasController

        model, mapa, bytes_iniciais = croqui_com_mapa
        undo_stack = QUndoStack()
        mapas_ctrl = MapasController(model, undo_stack)

        widget = WidgetEditorMapas(croqui_model=model, mapas_controller=mapas_ctrl)
        qtbot.addWidget(widget)
        widget.carregar_mapa(mapa)

        nova_img_path = tmp_path / "nova_foto_mapas_ctrl.png"
        img_nova = Image.new("RGB", (600, 400), color=(10, 200, 150))
        img_nova.save(nova_img_path, format="PNG")

        def fake_exec(self_dlg):
            self_dlg.carregar_imagem_arquivo(str(nova_img_path))
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

        widget.substituir_imagem_mapa()

        bytes_substituidos = model.obter_bytes_imagem("imagens/mapa_setor_a.webp")
        assert bytes_substituidos != bytes_iniciais
        assert mapa.largura_mapa == 600
        assert mapa.altura_mapa == 400
        assert undo_stack.count() == 1

        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_iniciais
        assert mapa.largura_mapa == 400
        assert mapa.altura_mapa == 300

        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_substituidos

    def test_sincronizacao_reativa_sinal_imagem_alterada(self, qtbot, croqui_com_mapa):
        model, mapa, _ = croqui_com_mapa
        widget = WidgetEditorMapas(croqui_model=model)
        qtbot.addWidget(widget)
        widget.carregar_mapa(mapa)

        buf = io.BytesIO()
        img = Image.new("RGB", (400, 300), color=(0, 255, 0))
        img.save(buf, format="WEBP")
        bytes_novos = buf.getvalue()

        model.definir_imagem_memoria("imagens/mapa_setor_a.webp", bytes_novos)
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_novos

    def test_abrir_no_editor_imagens_emite_foco(self, qtbot, croqui_com_mapa):
        model, mapa, _ = croqui_com_mapa
        widget = WidgetEditorMapas(croqui_model=model)
        qtbot.addWidget(widget)
        widget.carregar_mapa(mapa)

        focos = []
        model.foco_requisitado.connect(lambda ctx: focos.append(ctx))

        widget.abrir_no_editor_imagens()
        assert len(focos) == 1
        assert "page:imagens/file:mapa_setor_a.webp" in focos[0]

    def test_casos_borda_substituir_e_abrir(self, qtbot, croqui_com_mapa, monkeypatch):
        model, mapa, _ = croqui_com_mapa
        widget = WidgetEditorMapas(croqui_model=model)
        qtbot.addWidget(widget)

        widget.msg_mapa_proxy = None
        widget.substituir_imagem_mapa()
        widget.abrir_no_editor_imagens()

        widget.carregar_mapa(mapa)

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", lambda _self: QDialog.DialogCode.Rejected)
        widget.substituir_imagem_mapa()

        widget._on_imagem_alterada("imagens/outro_mapa.webp")
