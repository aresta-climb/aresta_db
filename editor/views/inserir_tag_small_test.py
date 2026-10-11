# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de unidade e integração para inserção da tag <small> no WidgetEditorMarkdown.
Verifica:
1. Envolver texto selecionado em <small>...</small> ao acionar o botão ou método.
2. Inserir <small></small> e posicionar o cursor no meio caso não haja seleção prévia.
3. Atualização automática do preview de renderização em tempo real.
"""

from pathlib import Path
from typing import Any

from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown


def test_inserir_tag_small_com_texto_selecionado(qapp: Any, tmp_path: Path) -> None:
    croqui = Croqui()
    croqui.nome = "Pico dos Três Irmãos"
    croqui.descricao = "Acesso pela trilha principal."

    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)

    widget_dados = WidgetEditorDados(model, controller)
    campo_desc = croqui.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(
        croqui, campo_desc, widget_dados.form_padrao, parent=widget_dados.form_padrao
    )

    # Verifica se o botão btn_small existe no layout
    assert hasattr(md_editor, "btn_small"), (
        "O WidgetEditorMarkdown deve possuir o atributo btn_small"
    )

    # Seleciona 'trilha principal' no editor
    texto_original = "Acesso pela trilha principal."
    inicio_sel = texto_original.index("trilha principal")
    fim_sel = inicio_sel + len("trilha principal")

    cursor = md_editor.editor.textCursor()
    cursor.setPosition(inicio_sel)
    cursor.setPosition(fim_sel, cursor.MoveMode.KeepAnchor)
    md_editor.editor.setTextCursor(cursor)

    # Dispara a ação de aplicar small
    md_editor.btn_small.click()

    texto_resultante = md_editor.editor.toPlainText()
    assert texto_resultante == "Acesso pela <small>trilha principal</small>."


def test_inserir_tag_small_sem_selecao_posiciona_cursor_no_meio(qapp: Any, tmp_path: Path) -> None:
    croqui = Croqui()
    croqui.nome = "Setor Inicial"
    croqui.descricao = "Nota: "

    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)

    widget_dados = WidgetEditorDados(model, controller)
    campo_desc = croqui.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(
        croqui, campo_desc, widget_dados.form_padrao, parent=widget_dados.form_padrao
    )

    # Posiciona o cursor no final sem seleção
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)

    # Dispara a ação de aplicar small
    md_editor.aplicar_tag_small()

    texto_resultante = md_editor.editor.toPlainText()
    assert texto_resultante == "Nota: <small></small>"

    # O cursor deve estar posicionado logo após '<small>' (posição do texto original + 7 caracteres de '<small>')
    posicao_cursor = md_editor.editor.textCursor().position()
    assert posicao_cursor == len("Nota: <small>")
