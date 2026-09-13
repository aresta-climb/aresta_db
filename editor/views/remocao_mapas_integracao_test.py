# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QDialog

from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa


def criar_imagem_webp_bytes(cor=(120, 120, 120), tamanho=(300, 200)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", tamanho, color=cor)
    img.save(buf, format="WEBP")
    return buf.getvalue()


class TestRemocaoMapasIntegracao:
    def test_fluxo_integracao_adicionar_remover_e_readicionar_mapa_com_undo_redo(self, qtbot, tmp_path):
        """
        Testa o fluxo de fronteira:
        1. Adiciona mapa com imagem em RAM
        2. Remove o mapa via controller.remover_repeated
        3. Verifica que a imagem foi purgada da RAM
        4. Tenta re-adicionar no DialogoAdicionarMapa e valida ausência de erro de colisão de RAM
        5. Aciona Undo e verifica que mapa e imagem em RAM retornam
        6. Aciona Redo e verifica nova remoção completa
        """
        croqui = croqui_pb2.Croqui(nome="Croqui Teste Remoção")
        pico = croqui.picos.add(nome="Pico Central")
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        setor.nome = "Setor Fugitivos I"

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        proxy_croqui = model.obter_croqui_readonly()
        proxy_setor = proxy_croqui.picos[0].setores_ou_grupos[0].setor.conteudo

        # 1. Adiciona mapa com imagem em RAM
        caminho_mapa = "imagens/setor_fugitivos_i_p0.webp"
        bytes_img = criar_imagem_webp_bytes(cor=(200, 50, 50))
        novo_mapa = croqui_pb2.Mapa()
        novo_mapa.caminho_imagem_mapa = caminho_mapa
        novo_mapa.largura_mapa = 300
        novo_mapa.altura_mapa = 200

        caminho_abs = tmp_path / caminho_mapa
        controller.adicionar_mapa_com_arquivo(
            proxy_setor, "mapas", 0, novo_mapa, caminho_abs, bytes_img
        )

        assert len(proxy_setor.mapas) == 1
        assert caminho_mapa in model.obter_imagens_em_memoria()
        assert model.obter_imagens_em_memoria()[caminho_mapa] == bytes_img

        # 2. Remove o mapa via controller
        mapa_para_remover = proxy_setor.mapas[0]
        controller.remover_repeated(proxy_setor, "mapas", 0, mapa_para_remover)

        assert len(proxy_setor.mapas) == 0
        # 3. A imagem DEVE ter sido removida do buffer de RAM
        assert caminho_mapa not in model.obter_imagens_em_memoria()

        # 4. Tenta re-adicionar no DialogoAdicionarMapa com a mesma imagem
        img_temp_file = tmp_path / "foto_temp.png"
        Image.new("RGB", (300, 200), color=(200, 50, 50)).save(img_temp_file, format="PNG")

        dialogo = DialogoAdicionarMapa("setor_fugitivos_i_p0.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(img_temp_file))

        # Não deve haver aviso de RAM e o botão deve estar liberado
        assert "memória RAM" not in dialogo.rotulo_aviso.text()
        assert dialogo.btn_ok.isEnabled() is True

        # 5. Testa Undo: a remoção deve ser desfeita, restaurando o mapa e a imagem na RAM
        undo_stack.undo()
        assert len(proxy_setor.mapas) == 1
        assert caminho_mapa in model.obter_imagens_em_memoria()
        assert model.obter_imagens_em_memoria()[caminho_mapa] == bytes_img

        # 6. Testa Redo: refaz a remoção, descartando o mapa e a imagem da RAM novamente
        undo_stack.redo()
        assert len(proxy_setor.mapas) == 0
        assert caminho_mapa not in model.obter_imagens_em_memoria()

    def test_fluxo_integracao_deduplicacao_prefixo_ao_propor_mapa_em_setor(self, qtbot, tmp_path):
        """
        Testa que a sugestão de nome de arquivo para novo mapa não duplica 'setor_'.
        """
        croqui = croqui_pb2.Croqui(nome="Croqui Teste")
        pico = croqui.picos.add(nome="Pico 1")
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        setor.nome = "Setor Fugitivos I"

        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        from editor.views.widget_editor_dados import WidgetEditorDados
        widget_dados = WidgetEditorDados(model, controller)
        qtbot.addWidget(widget_dados)

        # Importa função de biblioteca para verificar o contrato
        from editor.core.nomes_arquivos import gerar_nome_mapa_sugerido
        nome_sugerido = gerar_nome_mapa_sugerido(setor, 0)
        assert nome_sugerido == "setor_fugitivos_i_p0.webp"
        assert "setor_setor" not in nome_sugerido
