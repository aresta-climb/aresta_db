# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QUndoStack

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from editor.legacy_views.area_principal import JanelaPrincipal
from editor.core.workspace import ExperimentalWorkspace


@pytest.fixture
def imagem_valida_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 200), color=(100, 150, 200))
    img.save(buf, format="WEBP")
    return buf.getvalue()


class TestAreaPrincipalImagensIntegracao:
    def test_foco_requisitado_pagina_imagens_seleciona_arquivo(self, qtbot, tmp_path):
        pasta_raiz = tmp_path / "croqui_teste"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Cria imagens no disco
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(pasta_imagens / "thumbnail.webp", format="WEBP")
        img.save(pasta_imagens / "mapa_1.webp", format="WEBP")

        # Cria croqui.yaml mínimo
        (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Teste\n", encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)

        area_principal.carregar_croqui()

        # Verifica que a lista de imagens tem os 2 arquivos
        assert area_principal.pagina_imagens.editor.list_widget.count() == 2

        # Dispara requisição de foco para imagens/mapa_1.webp
        area_principal._on_foco_requisitado("page:imagens/mapa_1.webp")

        # Deve ter trocado para a aba de imagens (índice 1)
        assert area_principal.stack.currentIndex() == 1
        item_atual = area_principal.pagina_imagens.editor.list_widget.currentItem()
        assert item_atual is not None
        assert item_atual.text() == "mapa_1.webp"

    def test_salvar_croqui_recarrega_imagens_e_mapas(self, qtbot, tmp_path, imagem_valida_bytes, monkeypatch):
        pasta_raiz = tmp_path / "croqui_teste_salvar"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Teste\n", encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)

        area_principal.carregar_croqui()

        # Define imagem em memória no croqui_model
        area_principal.croqui_model.definir_imagem_memoria("imagens/nova_foto.webp", imagem_valida_bytes)

        # Mock de compilação/salvamento do worker para não invocar Git nem compilador externo no teste
        recarregou_imagens = False
        recarregou_mapas = False

        orig_carregar_imagens = area_principal.pagina_imagens.carregar_imagens
        def mock_carregar_imagens(caminho):
            nonlocal recarregou_imagens
            recarregou_imagens = True
            orig_carregar_imagens(caminho)

        orig_carregar_mapas = area_principal.pagina_mapas.carregar_mapas
        def mock_carregar_mapas(model, pilha, caminho):
            nonlocal recarregou_mapas
            recarregou_mapas = True
            orig_carregar_mapas(model, pilha, caminho)

        monkeypatch.setattr(area_principal.pagina_imagens, "carregar_imagens", mock_carregar_imagens)
        monkeypatch.setattr(area_principal.pagina_mapas, "carregar_mapas", mock_carregar_mapas)

        # Simula resposta de sucesso do salvamento
        area_principal._on_salvar_sucesso(pasta_db, [], False, 0)

        assert recarregou_imagens is True
        assert recarregou_mapas is True

    def test_substituir_imagem_no_editor_imagens_mantem_pagina_imagens(self, qtbot, tmp_path, monkeypatch):
        from PyQt6.QtWidgets import QFileDialog

        pasta_raiz = tmp_path / "croqui_teste_subst"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Cria imagens no disco
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(pasta_imagens / "thumbnail.webp", format="WEBP")

        # Cria croqui.yaml com nó selecionado no editor de dados
        (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Teste\n", encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)

        area_principal.carregar_croqui()

        # Simula que o usuário estava anteriormente no editor de dados e selecionou um nó
        area_principal.croqui_controller.set_contexto("node:Croqui/picos/item:0")

        # Usuário clica na aba Imagens
        area_principal._trocar_pagina(1)
        assert area_principal.stack.currentIndex() == 1

        # Usuário seleciona imagem e clica em Substituir Imagem
        area_principal.pagina_imagens.editor.select_image_by_name("thumbnail.webp")

        from PyQt6.QtWidgets import QMessageBox
        monkeypatch.setattr("editor.legacy_views.area_principal.QMessageBox.question", lambda *a, **k: QMessageBox.StandardButton.Discard)

        nova_img = tmp_path / "nova_foto.png"
        Image.new("RGB", (300, 300), color=(0, 255, 100)).save(nova_img, format="PNG")
        monkeypatch.setattr("editor.legacy_views.widget_editor_imagens.QFileDialog.getOpenFileName", lambda *a, **k: (str(nova_img), "PNG"))

        area_principal.pagina_imagens.editor.substituir_imagem_selecionada()

        # DEVE continuar na aba de imagens (índice 1) e NÃO voltar para a aba de dados (índice 0)
        assert area_principal.stack.currentIndex() == 1

        # Undo também deve manter na aba de imagens
        area_principal.historico.obter_pilha().undo()
        assert area_principal.stack.currentIndex() == 1

        # Redo também deve manter na aba de imagens
        area_principal.historico.obter_pilha().redo()
        assert area_principal.stack.currentIndex() == 1

        area_principal.historico.obter_pilha().setClean()

