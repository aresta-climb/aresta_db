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
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens


@pytest.fixture
def croqui_com_imagem_disco(tmp_path):
    croqui = croqui_pb2.Croqui()
    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir(parents=True, exist_ok=True)

    img_path = pasta_img / "setor_foto.webp"
    img = Image.new("RGB", (400, 300), color=(120, 60, 180))
    img.save(img_path, format="WEBP")

    model = CroquiModel(croqui)
    model.definir_caminho_db(tmp_path)

    return model, str(pasta_img), str(img_path)


class TestWidgetEditorImagensSubstituicao:
    def test_inicializacao_botao_substituir(self, qtbot, croqui_com_imagem_disco):
        model, pasta_img, _ = croqui_com_imagem_disco
        widget = WidgetEditorImagens(imagens_path=pasta_img, croqui_model=model)
        qtbot.addWidget(widget)

        assert hasattr(widget, "btn_substituir_imagem")
        assert widget.btn_substituir_imagem.text() == "Substituir Imagem..."

    def test_substituir_imagem_selecionada_com_undo_redo(self, qtbot, croqui_com_imagem_disco, tmp_path, monkeypatch):
        model, pasta_img, img_orig_path = croqui_com_imagem_disco
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)
        widget = WidgetEditorImagens(imagens_path=pasta_img, croqui_model=model, croqui_controller=controller)
        qtbot.addWidget(widget)

        widget.select_image_by_name("setor_foto.webp")
        bytes_originais = Path(img_orig_path).read_bytes()

        # Cria novo arquivo de imagem para substituir
        novo_arq = tmp_path / "nova_imagem.png"
        img_nova = Image.new("RGB", (600, 400), color=(255, 200, 0))
        img_nova.save(novo_arq, format="PNG")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(novo_arq), "PNG"))

        # Executa substituição
        widget.substituir_imagem_selecionada()

        bytes_em_ram = model.obter_bytes_imagem("imagens/setor_foto.webp")
        assert bytes_em_ram is not None
        assert bytes_em_ram != bytes_originais
        assert bytes_em_ram.startswith(b"RIFF")
        assert undo_stack.count() == 1

        # Undo
        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/setor_foto.webp") == bytes_originais

        # Redo
        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/setor_foto.webp") == bytes_em_ram

    def test_sincronizacao_reativa_ao_sinal_imagem_alterada(self, qtbot, croqui_com_imagem_disco):
        model, pasta_img, _ = croqui_com_imagem_disco
        widget = WidgetEditorImagens(imagens_path=pasta_img, croqui_model=model)
        qtbot.addWidget(widget)

        widget.select_image_by_name("setor_foto.webp")

        # Modifica externamente via model
        buf = io.BytesIO()
        img = Image.new("RGB", (300, 300), color=(0, 100, 255))
        img.save(buf, format="WEBP")
        bytes_externos = buf.getvalue()

        model.definir_imagem_memoria("imagens/setor_foto.webp", bytes_externos)

        # Deve estar carregado na memória do modelo
        assert model.obter_bytes_imagem("imagens/setor_foto.webp") == bytes_externos

    def test_casos_borda_substituicao(self, qtbot, croqui_com_imagem_disco, monkeypatch):
        model, pasta_img, _ = croqui_com_imagem_disco
        widget = WidgetEditorImagens(imagens_path=pasta_img, croqui_model=model)
        qtbot.addWidget(widget)

        # Sem imagem selecionada
        widget.current_file = None
        widget.substituir_imagem_selecionada()

        widget.select_image_by_name("setor_foto.webp")

        # Cancelar diálogo
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
        widget.substituir_imagem_selecionada()

        # Erro ao processar arquivo
        avisos = []
        monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: avisos.append(text))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("inexistente.png", "PNG"))
        widget.substituir_imagem_selecionada()
        assert len(avisos) == 1

    def test_inicializacao_botao_abrir_no_editor_mapas(self, qtbot, croqui_com_imagem_disco):
        model, pasta_img, _ = croqui_com_imagem_disco
        widget = WidgetEditorImagens(imagens_path=pasta_img, croqui_model=model)
        qtbot.addWidget(widget)

        assert hasattr(widget, "btn_abrir_no_editor_mapas")
        assert widget.btn_abrir_no_editor_mapas.text() == "Abrir no Editor de Mapas"

    def test_botao_abrir_no_editor_mapas_habilitado_apenas_para_mapas(self, qtbot, tmp_path):
        croqui = croqui_pb2.Croqui()
        pico = croqui.picos.add(nome="Pico 1")
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        setor.nome = "Setor A"
        mapa = setor.mapas.add()
        mapa.caminho_imagem_mapa = "imagens/mapa_setor.webp"

        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 200), color=(10, 20, 30)).save(pasta_img / "mapa_setor.webp", format="WEBP")
        Image.new("RGB", (200, 200), color=(50, 60, 70)).save(pasta_img / "foto_via.webp", format="WEBP")

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model)
        qtbot.addWidget(widget)

        # Seleciona foto normal (não vinculada a mapa)
        widget.select_image_by_name("foto_via.webp")
        assert widget.btn_abrir_no_editor_mapas.isEnabled() is False

        # Seleciona imagem de mapa
        widget.select_image_by_name("mapa_setor.webp")
        assert widget.btn_abrir_no_editor_mapas.isEnabled() is True

    def test_abrir_no_editor_mapas_emite_foco(self, qtbot, tmp_path):
        croqui = croqui_pb2.Croqui()
        pico = croqui.picos.add(nome="Pico 1")
        mapa_geral = pico.mapas_gerais.conteudo.mapas.add()
        mapa_geral.caminho_imagem_mapa = "imagens/mapa_geral.webp"

        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 200), color=(10, 20, 30)).save(pasta_img / "mapa_geral.webp", format="WEBP")

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model)
        qtbot.addWidget(widget)

        focos = []
        model.foco_requisitado.connect(lambda ctx: focos.append(ctx))

        widget.select_image_by_name("mapa_geral.webp")
        widget.abrir_no_editor_mapas()

        assert len(focos) == 1
        assert focos[0] == "page:mapas/file:mapa_geral.webp"

    def test_imagem_pertence_a_mapa_grupo_e_subsetor_e_casos_borda(self, qtbot, tmp_path):
        croqui = croqui_pb2.Croqui()
        pico = croqui.picos.add(nome="Pico 1")
        sg = pico.setores_ou_grupos.add()
        grupo = sg.grupo.conteudo
        grupo.nome = "Grupo Principal"
        
        mapa_g = grupo.mapas.add()
        mapa_g.caminho_imagem_mapa = "imagens/mapa_grupo.webp"

        sub = grupo.setores.add()
        sub.conteudo.nome = "Subsetor 1"
        mapa_sub = sub.conteudo.mapas.add()
        mapa_sub.caminho_imagem_mapa = "imagens/mapa_subsetor.webp"

        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (100, 100)).save(pasta_img / "mapa_grupo.webp", format="WEBP")
        Image.new("RGB", (100, 100)).save(pasta_img / "mapa_subsetor.webp", format="WEBP")

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetEditorImagens(imagens_path=str(pasta_img), croqui_model=model, croqui_controller=controller)
        qtbot.addWidget(widget)

        # Mapa de grupo
        widget.select_image_by_name("mapa_grupo.webp")
        assert widget.btn_abrir_no_editor_mapas.isEnabled() is True
        assert widget.imagem_pertence_a_mapa("mapa_grupo.webp") is True

        # Mapa de subsetor
        widget.select_image_by_name("mapa_subsetor.webp")
        assert widget.btn_abrir_no_editor_mapas.isEnabled() is True
        assert widget.imagem_pertence_a_mapa("mapa_subsetor.webp") is True

        # Testa abertura com controller setando contexto
        widget.abrir_no_editor_mapas()
        assert controller.contexto_atual_path == "page:mapas/file:mapa_subsetor.webp"

        # Casos de borda
        assert widget.imagem_pertence_a_mapa("") is False
        assert widget.imagem_pertence_a_mapa(None) is False
        
        widget.current_file = None
        widget.abrir_no_editor_mapas() # Não deve quebrar

        widget_sem_model = WidgetEditorImagens(imagens_path=str(pasta_img))
        qtbot.addWidget(widget_sem_model)
        assert widget_sem_model.imagem_pertence_a_mapa("mapa_grupo.webp") is False


