# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de integração ponta a ponta:
1. Inserir botão de anexo em Markdown via editor com histórico Undo/Redo.
2. Salvar o croqui para o disco com extrair_arquivos_e_serializar.
3. Executar rotina de limpeza de arquivos órfãos (limpar_arquivos_nao_utilizados) e validar que permanece.
4. Executar Undo na pilha de histórico (removendo a referência do Markdown).
5. Salvar o croqui novamente e executar limpeza de arquivos órfãos.
6. Validar que o anexo desvinculado é deletado fisicamente do disco em anexos/.
"""

from pathlib import Path
from typing import Any

from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
from scripts.preparar_submissao_lib import limpar_arquivos_nao_utilizados


def test_integracao_inserir_anexo_salvar_undo_salvar_limpa_disco(qapp: Any, tmp_path: Path) -> None:
    caminho_db = tmp_path
    pasta_anexos = caminho_db / "anexos"

    croqui = Croqui()
    croqui.nome = "Setor CEMONTA"
    croqui.descricao = "Acesso regulamentado pelo Exército."

    model = CroquiModel(croqui)
    model._caminho_db_atual = caminho_db
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)

    widget_dados = WidgetEditorDados(model, controller)
    campo_desc = croqui.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(
        croqui, campo_desc, widget_dados.form_padrao, parent=widget_dados.form_padrao
    )

    conteudo_pdf = b"%PDF-1.4 Termo de Compromisso"
    caminho_relativo = "anexos/termo_compromisso.pdf"
    tag_botao = f"[Preencher Termo de Risco]({caminho_relativo})"

    texto_antigo = md_editor.editor.toPlainText()
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    cursor.insertText(f"\n\n{tag_botao}")
    md_editor.editor.setTextCursor(cursor)
    texto_novo = md_editor.editor.toPlainText()

    # 1. Inserir botão de anexo com comando registrado no histórico (Undo/Redo)
    controller.inserir_botao_markdown(
        croqui,
        "descricao",
        texto_antigo,
        texto_novo,
        caminho_anexo=caminho_relativo,
        bytes_anexo=conteudo_pdf,
    )

    assert tag_botao in croqui.descricao
    assert model.obter_bytes_anexo(caminho_relativo) == conteudo_pdf

    # 2. Salva o croqui (grava em anexos/ no disco)
    croqui_yaml_data = model.extrair_arquivos_e_serializar(caminho_db)
    arquivo_disco = pasta_anexos / "termo_compromisso.pdf"
    assert arquivo_disco.exists(), "O arquivo do anexo deve existir após serialização"

    # 3. Executa a limpeza com anexo referenciado (não deve deletar)
    limpar_arquivos_nao_utilizados(caminho_db, croqui_yaml_data)
    assert arquivo_disco.exists(), (
        "O anexo referenciado no Markdown NÃO pode ser excluído na limpeza"
    )

    # 4. Executa Undo no histórico (remove o link do Markdown e do buffer de memória)
    assert pilha.canUndo()
    pilha.undo()
    assert tag_botao not in croqui.descricao
    assert caminho_relativo not in model.obter_anexos_em_memoria()

    # 5. Salva o croqui após Undo (o arquivo físico ainda está no disco antes da limpeza)
    croqui_yaml_apos_undo = model.extrair_arquivos_e_serializar(caminho_db)
    assert tag_botao not in croqui_yaml_apos_undo.get("descricao", "")

    # 6. Executa a limpeza de arquivos órfãos (agora o anexo está órfão)
    limpar_arquivos_nao_utilizados(caminho_db, croqui_yaml_apos_undo)

    # 7. O arquivo físico órfão deve ter sido deletado do disco
    assert not arquivo_disco.exists(), (
        "O anexo órfão após Undo DEVE ser deletado fisicamente do disco"
    )
    assert model.obter_bytes_anexo(caminho_relativo) is None
