# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QUndoStack

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
        from PySide6.QtWidgets import QFileDialog

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

        from PySide6.QtWidgets import QMessageBox
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

    def test_rotacao_imagem_integrada_com_undo_redo(self, qtbot, tmp_path):
        pasta_raiz = tmp_path / "croqui_teste_rotacao"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Cria imagem 200 de largura por 100 de altura
        img = Image.new("RGB", (200, 100), color=(10, 20, 30))
        img.save(pasta_imagens / "foto_setor.webp", format="WEBP")
        (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Teste\n", encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)
        area_principal.carregar_croqui()

        area_principal._trocar_pagina(1)
        editor = area_principal.pagina_imagens.editor
        editor.select_image_by_name("foto_setor.webp")

        pilha = area_principal.historico.obter_pilha()
        count_inicial = pilha.count()

        # Executa rotação horária de 90°
        editor.rotate_cw_btn.click()

        bytes_rot = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_setor.webp")
        assert bytes_rot is not None
        with Image.open(io.BytesIO(bytes_rot)) as img_rot:
            assert (img_rot.width, img_rot.height) == (100, 200)

        assert pilha.count() == count_inicial + 1

        # Desfazer (Undo)
        pilha.undo()
        bytes_undo = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_setor.webp")
        with Image.open(io.BytesIO(bytes_undo)) as img_undo:
            assert (img_undo.width, img_undo.height) == (200, 100)

        # Refazer (Redo)
        pilha.redo()
        bytes_redo = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_setor.webp")
        with Image.open(io.BytesIO(bytes_redo)) as img_redo:
            assert (img_redo.width, img_redo.height) == (100, 200)
        pilha.setClean()

    def test_corte_imagem_integrado_com_undo_redo(self, qtbot, tmp_path):
        pasta_raiz = tmp_path / "croqui_teste_corte"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Cria imagem 200x200
        img = Image.new("RGB", (200, 200), color=(50, 60, 70))
        img.save(pasta_imagens / "foto_corte.webp", format="WEBP")
        (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Teste\n", encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)
        area_principal.carregar_croqui()

        area_principal._trocar_pagina(1)
        editor = area_principal.pagina_imagens.editor
        editor.select_image_by_name("foto_corte.webp")

        pilha = area_principal.historico.obter_pilha()
        count_inicial = pilha.count()

        # Ativa o modo de corte e executa seleção (10, 20) até (60, 80) -> width=50, height=60
        editor.crop_btn.click()
        assert editor.modo_corte is True

        # Executa o corte através da seleção de retângulo
        editor.executar_corte_selecao(10, 20, 60, 80)

        # Modo de corte deve ser desativado após o corte
        assert editor.modo_corte is False
        assert pilha.count() == count_inicial + 1

        bytes_cortados = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_corte.webp")
        assert bytes_cortados is not None
        with Image.open(io.BytesIO(bytes_cortados)) as img_c:
            assert (img_c.width, img_c.height) == (50, 60)

        # Desfazer restaura 200x200
        pilha.undo()
        bytes_undo = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_corte.webp")
        with Image.open(io.BytesIO(bytes_undo)) as img_u:
            assert (img_u.width, img_u.height) == (200, 200)

        # Refazer reaplica 50x60
        pilha.redo()
        bytes_redo = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_corte.webp")
        with Image.open(io.BytesIO(bytes_redo)) as img_r:
            assert (img_r.width, img_r.height) == (50, 60)
        pilha.setClean()

    def test_mascara_imagem_integrada_com_undo_redo(self, qtbot, tmp_path):
        pasta_raiz = tmp_path / "croqui_teste_mascara"
        pasta_db = pasta_raiz / "database"
        pasta_db.mkdir(parents=True)
        pasta_imagens = pasta_db / "imagens"
        pasta_imagens.mkdir()

        # Imagem 100x100 preta, com uma região vermelha em [0, 0, 10, 10]
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        from PIL import ImageDraw
        ImageDraw.Draw(img).rectangle([0, 0, 10, 10], fill=(255, 0, 0))
        img.save(pasta_imagens / "foto_mascara.webp", format="WEBP")
        (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Teste\n", encoding="utf-8")

        workspace = ExperimentalWorkspace(pasta_raiz)
        area_principal = JanelaPrincipal(workspace=workspace)
        qtbot.addWidget(area_principal)
        area_principal.carregar_croqui()

        area_principal._trocar_pagina(1)
        editor = area_principal.pagina_imagens.editor
        editor.select_image_by_name("foto_mascara.webp")

        pilha = area_principal.historico.obter_pilha()
        count_inicial = pilha.count()

        # Ativa máscara e captura a cor do pixel (5, 5) que é vermelho (255, 0, 0)
        editor.add_mask_btn.click()
        assert editor.modo_mascara is True
        editor.capturar_cor_ponto(5, 5)
        assert all(abs(a - b) <= 3 for a, b in zip(editor.cor_mascara_atual, (255, 0, 0)))

        # Aplica máscara retangular cobrindo (20, 20) até (40, 40)
        editor.aplicar_mascara_selecao(20, 20, 40, 40)
        assert pilha.count() == count_inicial + 1

        bytes_mascarados = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_mascara.webp")
        with Image.open(io.BytesIO(bytes_mascarados)) as img_m:
            # O ponto (25, 25) deve ter sido pintado de vermelho
            assert all(abs(a - b) <= 3 for a, b in zip(img_m.getpixel((25, 25))[:3], (255, 0, 0)))

        # Desfazer: volta a ser preto (0, 0, 0)
        pilha.undo()
        bytes_undo = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_mascara.webp")
        with Image.open(io.BytesIO(bytes_undo)) as img_u:
            assert all(abs(a - b) <= 3 for a, b in zip(img_u.getpixel((25, 25))[:3], (0, 0, 0)))

        # Refazer: volta a ser vermelho (255, 0, 0)
        pilha.redo()
        bytes_redo = area_principal.croqui_model.obter_bytes_imagem("imagens/foto_mascara.webp")
        with Image.open(io.BytesIO(bytes_redo)) as img_r:
            assert all(abs(a - b) <= 3 for a, b in zip(img_r.getpixel((25, 25))[:3], (255, 0, 0)))
        pilha.setClean()



