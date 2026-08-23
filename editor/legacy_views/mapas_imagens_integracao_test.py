# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QUndoStack

from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from editor.views.widget_editor_mapas import WidgetEditorMapas
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens


def criar_imagem_webp_bytes(cor=(100, 100, 100), tamanho=(200, 150)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", tamanho, color=cor)
    img.save(buf, format="WEBP")
    return buf.getvalue()


class TestMapasImagensIntegracao:
    def test_sincronizacao_cruzada_mapas_e_imagens_com_undo_redo(self, qtbot, tmp_path, monkeypatch):
        # 1. Setup Croqui com 1 mapa
        croqui = croqui_pb2.Croqui(nome="Croqui Teste Sincronização")
        pico = croqui.picos.add(nome="Pico 1")
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        setor.nome = "Setor Principal"
        
        mapa = setor.mapas.add()
        mapa.caminho_imagem_mapa = "imagens/mapa_setor.webp"
        mapa.largura_mapa = 200
        mapa.altura_mapa = 150

        # Ponto de interesse no mapa
        poi = mapa.pontos_de_interesse.add(id="P1", label="Via dos Sonhos")
        poi.circulo.x = 50
        poi.circulo.y = 50
        poi.circulo.raio = 20

        bytes_iniciais = criar_imagem_webp_bytes(cor=(50, 50, 200))

        # Cria pasta imagens no disco
        pasta_imagens = tmp_path / "imagens"
        pasta_imagens.mkdir(parents=True, exist_ok=True)
        (pasta_imagens / "mapa_setor.webp").write_bytes(bytes_iniciais)

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        # 2. Instancia ambos os widgets
        widget_mapas = WidgetEditorMapas(croqui_model=model, croqui_controller=controller)
        widget_imagens = WidgetEditorImagens(
            imagens_path=str(pasta_imagens),
            croqui_model=model,
            croqui_controller=controller,
        )
        qtbot.addWidget(widget_mapas)
        qtbot.addWidget(widget_imagens)

        widget_mapas.carregar_mapa(mapa)
        widget_imagens.select_image_by_name("mapa_setor.webp")

        # 3. Substitui a imagem a partir do WidgetEditorMapas
        nova_foto_1 = tmp_path / "nova_foto_1.png"
        img1 = Image.new("RGB", (300, 200), color=(255, 0, 0))
        img1.save(nova_foto_1, format="PNG")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(nova_foto_1), "PNG"))
        widget_mapas.substituir_imagem_mapa()

        bytes_alterados_1 = model.obter_bytes_imagem("imagens/mapa_setor.webp")
        assert bytes_alterados_1 != bytes_iniciais
        assert bytes_alterados_1.startswith(b"RIFF")

        # Verifica se o editor de imagens recarregou em RAM
        assert widget_imagens.states[str(pasta_imagens / "mapa_setor.webp")].working_image is not None

        # 4. Substitui a imagem a partir do WidgetEditorImagens
        nova_foto_2 = tmp_path / "nova_foto_2.png"
        img2 = Image.new("RGB", (400, 250), color=(0, 255, 0))
        img2.save(nova_foto_2, format="PNG")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(nova_foto_2), "PNG"))
        widget_imagens.substituir_imagem_selecionada()

        bytes_alterados_2 = model.obter_bytes_imagem("imagens/mapa_setor.webp")
        assert bytes_alterados_2 != bytes_alterados_1
        assert undo_stack.count() == 2

        # Os POIs no mapa continuam preservados
        assert len(widget_mapas.msg_mapa_proxy.pontos_de_interesse) == 1
        assert widget_mapas.msg_mapa_proxy.pontos_de_interesse[0].label == "Via dos Sonhos"

        # 5. Undo duplo no histórico de comandos
        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/mapa_setor.webp") == bytes_alterados_1

        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/mapa_setor.webp") == bytes_iniciais

        # 6. Redo duplo
        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/mapa_setor.webp") == bytes_alterados_1

        undo_stack.redo()
        assert model.obter_bytes_imagem("imagens/mapa_setor.webp") == bytes_alterados_2

    def test_abrir_no_editor_imagens_a_partir_de_mapas_seleciona_imagem_exata_na_ui(self, qtbot, tmp_path):
        from editor.legacy_views.area_principal import JanelaPrincipal
        from editor.core.workspace import ExperimentalWorkspace

        pasta_raiz = tmp_path / "croqui_teste_nav"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Cria 2 imagens no disco
        Image.new("RGB", (100, 100), color=(255, 0, 0)).save(pasta_imagens / "thumb.webp", format="WEBP")
        Image.new("RGB", (200, 200), color=(0, 255, 0)).save(pasta_imagens / "mapa_setor_b.webp", format="WEBP")

        # Cria croqui com mapa apontando para mapa_setor_b.webp
        yaml_content = """
id: teste_nav
nome: Teste Nav
picos:
  - nome: Pico 1
    setores_ou_grupos:
      - setor:
          conteudo:
            nome: Setor B
            mapas:
              - caminho_imagem_mapa: imagens/mapa_setor_b.webp
                largura_mapa: 200
                altura_mapa: 200
"""
        (pasta_db / "croqui.yaml").write_text(yaml_content, encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)

        area_principal.carregar_croqui()

        # Navega para a aba de Mapas
        area_principal._trocar_pagina(2)
        assert area_principal.stack.currentIndex() == 2

        # Seleciona o mapa na lista do editor de mapas
        editor_mapas = area_principal.pagina_mapas.editor
        editor_mapas.list_widget.setCurrentRow(0)
        assert editor_mapas.msg_mapa_proxy is not None

        # Clica no botão "Abrir no Editor de Imagens"
        editor_mapas.btn_abrir_editor_imagens.click()

        # Deve ter navegado para a aba de imagens (índice 1)
        assert area_principal.stack.currentIndex() == 1

        # Deve ter selecionado exatamente o arquivo 'mapa_setor_b.webp' na lista de imagens
        item_selecionado = area_principal.pagina_imagens.editor.list_widget.currentItem()
        assert item_selecionado is not None
        assert item_selecionado.text() == "mapa_setor_b.webp"
        assert "mapa_setor_b.webp" in str(area_principal.pagina_imagens.editor.current_file)

        area_principal.historico.obter_pilha().setClean()

    def test_substituir_imagem_mapa_no_editor_mapas_integrado_com_foco_sem_crash(self, qtbot, tmp_path, monkeypatch):
        from editor.legacy_views.area_principal import JanelaPrincipal
        from editor.core.workspace import ExperimentalWorkspace
        from PyQt6.QtWidgets import QMessageBox

        monkeypatch.setattr("editor.legacy_views.area_principal.QMessageBox.question", lambda *a, **k: QMessageBox.StandardButton.Discard)

        pasta_raiz = tmp_path / "croqui_subst_mapa_integrado"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Imagem original do mapa
        Image.new("RGB", (200, 200), color=(10, 20, 30)).save(pasta_imagens / "mapa_principal.webp", format="WEBP")

        yaml_content = """
id: croqui_mapa_subst
nome: Croqui Mapa Subst
picos:
  - nome: Pico 1
    setores_ou_grupos:
      - setor:
          conteudo:
            nome: Setor 1
            mapas:
              - caminho_imagem_mapa: imagens/mapa_principal.webp
                largura_mapa: 200
                altura_mapa: 200
"""
        (pasta_db / "croqui.yaml").write_text(yaml_content, encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)
        area_principal.carregar_croqui()

        # Vai para a aba de mapas
        area_principal._trocar_pagina(2)
        assert area_principal.stack.currentIndex() == 2

        # Seleciona o mapa
        editor_mapas = area_principal.pagina_mapas.editor
        editor_mapas.list_widget.setCurrentRow(0)

        # Prepara nova imagem
        nova_img = tmp_path / "nova_foto_mapa.png"
        Image.new("RGB", (350, 350), color=(100, 200, 50)).save(nova_img, format="PNG")
        monkeypatch.setattr("editor.views.widget_editor_mapas.QFileDialog.getOpenFileName", lambda *a, **k: (str(nova_img), "PNG"))

        # Executa substituição de imagem do mapa
        editor_mapas.substituir_imagem_mapa()

        # Deve permanecer na aba de mapas (índice 2) sem crash
        assert area_principal.stack.currentIndex() == 2
        assert area_principal.croqui_model.obter_bytes_imagem("imagens/mapa_principal.webp") is not None

        # Testa Undo
        area_principal.historico.obter_pilha().undo()
        assert area_principal.stack.currentIndex() == 2

        # Testa Redo
        area_principal.historico.obter_pilha().redo()
        assert area_principal.stack.currentIndex() == 2

        area_principal.historico.obter_pilha().setClean()

    def test_abrir_no_editor_mapas_a_partir_de_imagens_seleciona_mapa_na_janela_principal(self, qtbot, tmp_path):
        from editor.legacy_views.area_principal import JanelaPrincipal
        from editor.core.workspace import ExperimentalWorkspace

        pasta_raiz = tmp_path / "croqui_nav_img_para_mapa"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Cria 2 imagens no disco: uma foto avulsa e uma imagem de mapa
        Image.new("RGB", (100, 100), color=(255, 0, 0)).save(pasta_imagens / "foto_avulsa.webp", format="WEBP")
        Image.new("RGB", (200, 200), color=(0, 255, 0)).save(pasta_imagens / "mapa_setor_c.webp", format="WEBP")

        yaml_content = """
id: croqui_nav_img_mapa
nome: Croqui Nav Img Mapa
picos:
  - nome: Pico 1
    setores_ou_grupos:
      - setor:
          conteudo:
            nome: Setor C
            mapas:
              - caminho_imagem_mapa: imagens/mapa_setor_c.webp
                largura_mapa: 200
                altura_mapa: 200
"""
        (pasta_db / "croqui.yaml").write_text(yaml_content, encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)
        area_principal.carregar_croqui()

        # Vai para a aba de imagens
        area_principal._trocar_pagina(1)
        assert area_principal.stack.currentIndex() == 1

        editor_imagens = area_principal.pagina_imagens.editor

        # Seleciona foto avulsa -> botão abrir no editor de mapas desabilitado
        editor_imagens.select_image_by_name("foto_avulsa.webp")
        assert editor_imagens.btn_abrir_no_editor_mapas.isEnabled() is False

        # Seleciona imagem que é mapa -> botão abrir no editor de mapas habilitado
        editor_imagens.select_image_by_name("mapa_setor_c.webp")
        assert editor_imagens.btn_abrir_no_editor_mapas.isEnabled() is True

        # Clica no botão
        editor_imagens.btn_abrir_no_editor_mapas.click()

        # Deve ter navegado para a aba de mapas (índice 2)
        assert area_principal.stack.currentIndex() == 2

        # Deve ter selecionado o mapa correspondente
        editor_mapas = area_principal.pagina_mapas.editor
        assert editor_mapas.msg_mapa_proxy is not None
        assert "mapa_setor_c.webp" in str(editor_mapas.msg_mapa_proxy.caminho_imagem_mapa)

        area_principal.historico.obter_pilha().setClean()



