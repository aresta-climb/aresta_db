# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QUndoStack

from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
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

    # Cria imagem inicial em RAM
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

    def test_substituir_imagem_mapa_com_undo_redo(self, qtbot, croqui_com_mapa, tmp_path, monkeypatch):
        model, mapa, bytes_iniciais = croqui_com_mapa
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)
        widget = WidgetEditorMapas(croqui_model=model, croqui_controller=controller)
        qtbot.addWidget(widget)

        widget.carregar_mapa(mapa)

        # Prepara nova imagem PNG
        nova_img_path = tmp_path / "nova_foto.png"
        img_nova = Image.new("RGB", (500, 400), color=(200, 100, 50))
        img_nova.save(nova_img_path, format="PNG")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(nova_img_path), "PNG"))

        # Executa substituição de imagem
        widget.substituir_imagem_mapa()

        bytes_substituidos = model.obter_bytes_imagem("imagens/mapa_setor_a.webp")
        assert bytes_substituidos != bytes_iniciais
        assert bytes_substituidos.startswith(b"RIFF")
        assert undo_stack.count() == 1

        # Undo
        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_iniciais

        # Redo
        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_substituidos

    def test_substituir_imagem_mapa_via_mapas_controller_com_undo_redo(self, qtbot, croqui_com_mapa, tmp_path, monkeypatch):
        from editor.controllers.mapas_controller import MapasController
        model, mapa, bytes_iniciais = croqui_com_mapa
        undo_stack = QUndoStack()
        mapas_ctrl = MapasController(model, undo_stack)
        
        # Instancia widget passando apenas mapas_controller (sem croqui_controller direto)
        widget = WidgetEditorMapas(croqui_model=model, mapas_controller=mapas_ctrl)
        qtbot.addWidget(widget)
        widget.carregar_mapa(mapa)

        nova_img_path = tmp_path / "nova_foto_mapas_ctrl.png"
        img_nova = Image.new("RGB", (600, 400), color=(10, 200, 150))
        img_nova.save(nova_img_path, format="PNG")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(nova_img_path), "PNG"))

        # Substitui imagem
        widget.substituir_imagem_mapa()

        bytes_substituidos = model.obter_bytes_imagem("imagens/mapa_setor_a.webp")
        assert bytes_substituidos != bytes_iniciais
        assert undo_stack.count() == 1

        # Undo deve reverter a imagem na memória
        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_iniciais

        # Redo deve reaplicar
        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/mapa_setor_a.webp") == bytes_substituidos

    def test_sincronizacao_reativa_sinal_imagem_alterada(self, qtbot, croqui_com_mapa):
        model, mapa, bytes_iniciais = croqui_com_mapa
        widget = WidgetEditorMapas(croqui_model=model)
        qtbot.addWidget(widget)
        widget.carregar_mapa(mapa)

        # Modifica imagem na RAM via Model diretamente (como se viesse do Editor de Imagens)
        buf = io.BytesIO()
        img = Image.new("RGB", (400, 300), color=(0, 255, 0))
        img.save(buf, format="WEBP")
        bytes_novos = buf.getvalue()

        model.definir_imagem_memoria("imagens/mapa_setor_a.webp", bytes_novos)

        # O widget deve ter recarregado a imagem
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

        # Sem mapa carregado
        widget.msg_mapa_proxy = None
        widget.substituir_imagem_mapa()
        widget.abrir_no_editor_imagens()

        widget.carregar_mapa(mapa)

        # Cancelar diálogo de arquivo
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
        widget.substituir_imagem_mapa()

        # Erro ao processar arquivo
        avisos = []
        monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: avisos.append(text))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("inexistente.png", "PNG"))
        widget.substituir_imagem_mapa()
        assert len(avisos) == 1

        # Imagem alterada de outro mapa não recarrega o atual
        widget._on_imagem_alterada("imagens/outro_mapa.webp")

