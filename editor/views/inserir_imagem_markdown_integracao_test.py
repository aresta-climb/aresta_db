# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de integração ponta a ponta:
1. Inserir imagem em Markdown via editor com histórico Undo/Redo.
2. Salvar o croqui para o disco com extrair_arquivos_e_serializar.
3. Executar rotina de limpeza de arquivos órfãos (limpar_arquivos_nao_utilizados).
4. Validar que o arquivo WebP permanece no disco em imagens/.
5. Simular reabertura do croqui validando persistência e integridade.
"""

from pathlib import Path
from PySide6.QtGui import QUndoStack, QImage
from PySide6.QtWidgets import QDialog

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
from editor.views.dialogos.dialogo_inserir_imagem_markdown import DialogoInserirImagemMarkdown
from scripts.preparar_submissao_lib import limpar_arquivos_nao_utilizados


def test_integracao_inserir_imagem_markdown_salvar_limpar_e_reabrir(qapp, tmp_path):
    # 1. Configuração inicial do ambiente de teste
    caminho_db = tmp_path
    pasta_imagens = caminho_db / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)

    croqui = Croqui()
    croqui.nome = "Pico dos Três Irmãos"
    croqui.descricao = "Área clássica de escalada esportiva."

    pico = croqui.picos.add()
    pico.nome = "Setor Central"
    pico.descricao = "Acesso pela trilha principal."

    model = CroquiModel(croqui)
    model._caminho_db_atual = caminho_db
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)

    widget_dados = WidgetEditorDados(model, controller)
    campo_desc = croqui.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(croqui, campo_desc, widget_dados.form_padrao, parent=widget_dados.form_padrao)

    # 2. Cria imagem externa simulada
    img_externa = tmp_path / "foto_drone.png"
    qimg = QImage(120, 90, QImage.Format.Format_RGB32)
    qimg.fill(0x00FF88)
    qimg.save(str(img_externa), "PNG")

    # 3. Abre o diálogo de inserção e processa a imagem
    dialogo = DialogoInserirImagemMarkdown(
        caminho_db=caminho_db,
        model=model,
        imagem_inicial=img_externa,
        parent=md_editor,
    )
    dialogo.input_nome_arquivo.setText("vista_aerea_drone.webp")
    dialogo.input_legenda.setText("Vista panorâmica de drone")
    dialogo.accept()
    assert dialogo.result() == QDialog.DialogCode.Accepted

    # Simula o fluxo de inserção pelo WidgetEditorMarkdown
    tag = dialogo.obter_tag_markdown()
    assert tag == "![Vista panorâmica de drone](imagens/vista_aerea_drone.webp)"

    texto_antigo = md_editor.editor.toPlainText()
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.insertText(f"\n\n{tag}")
    md_editor.editor.setTextCursor(cursor)
    texto_novo = md_editor.editor.toPlainText()

    controller.inserir_imagem_markdown(
        croqui,
        "descricao",
        texto_antigo,
        texto_novo,
        caminho_imagem="imagens/vista_aerea_drone.webp",
        bytes_imagem=dialogo.obter_bytes_imagem_processada(),
    )

    # Verifica se o estado em memória está consistente
    assert "![Vista panorâmica de drone](imagens/vista_aerea_drone.webp)" in croqui.descricao
    assert "imagens/vista_aerea_drone.webp" in model.obter_imagens_em_memoria()

    # 4. Salva o croqui (extrair_arquivos_e_serializar grava as imagens em memória no disco)
    croqui_yaml_data = model.extrair_arquivos_e_serializar(caminho_db)
    assert isinstance(croqui_yaml_data, dict)
    assert "descricao" in croqui_yaml_data

    arquivo_disco = pasta_imagens / "vista_aerea_drone.webp"
    assert arquivo_disco.exists(), "O arquivo WebP deve ter sido gravado na pasta imagens/"
    assert arquivo_disco.stat().st_size > 0

    # 5. Executa a limpeza de arquivos órfãos (como ocorre na compilação e salvamento)
    limpar_arquivos_nao_utilizados(caminho_db, croqui_yaml_data)

    # 6. O arquivo NÃO deve ter sido deletado pelo limpador
    assert arquivo_disco.exists(), "A imagem WebP referenciada no Markdown NÃO pode ser excluída na limpeza!"

    # 7. Simula reabertura do croqui a partir dos arquivos salvos
    bytes_lidos = arquivo_disco.read_bytes()
    assert len(bytes_lidos) > 0
    assert bytes_lidos.startswith(b"RIFF")
