# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QLineEdit
from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from PyQt6.QtGui import QUndoStack
from editor.views.widget_editor_dados import WidgetEditorDados
from editor.legacy_views.area_principal import JanelaPrincipal

def test_widget_editor_dados_integracao_historico(qtbot):
    # 1. Cria a Janela Principal que contém o histórico e a página de dados
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.show()
    
    try:
        # Cria o Croqui inicial
        croqui = Croqui()
        croqui.nome = "Nome Inicial"
        
        from editor.models.croqui_model import CroquiModel
        from editor.controllers.croqui_controller import CroquiController
        
        model = CroquiModel(croqui)
        controller = CroquiController(model, janela.historico.obter_pilha())
        
        # Carrega os dados na janela
        janela.pagina_dados.carregar_dados(model, controller)
        
        # Processa eventos para que o singleShot(0, self._conectar_historico) execute
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        editor_dados = janela.pagina_dados.editor_dados
        form = editor_dados.form_padrao
        
        # Seleciona o nó raiz na árvore (Croqui)
        croqui_idx = editor_dados.tree_model.index(0, 0)
        editor_dados.tree_view.selectionModel().select(
            croqui_idx,
            editor_dados.tree_view.selectionModel().SelectionFlag.ClearAndSelect
        )
        editor_dados._on_tree_selection_changed(None, None)
        
        # Encontra o campo de texto do nome do Croqui
        line_edits = form.findChildren(QLineEdit)
        edit_nome = next(le for le in line_edits if le.property("protobuf_field") == "nome")
        
        # O valor na UI deve ser "Nome Inicial"
        assert edit_nome.text() == "Nome Inicial"
        
        # 2. Simula o usuário alterando o texto na UI
        edit_nome.setText("Nome Alterado")
        
        
        # O valor na mensagem Protobuf deve ter atualizado
        assert croqui.nome == "Nome Alterado"
        
        # O comando deve ter sido registrado na pilha global de histórico da janela
        assert janela.historico.obter_pilha().count() == 1
        assert janela.historico.obter_pilha().canUndo()
        
        # 3. Desfaz (Undo) via histórico da janela
        janela.historico.desfazer()
        
        # O valor no proto deve voltar ao original
        assert croqui.nome == "Nome Inicial"
        
        # A UI não deve reconstruir, o mesmo QLineEdit deve estar ativo, atualizado e com foco
        line_edits_after_undo = form.findChildren(QLineEdit)
        edit_nome_after_undo = next(le for le in line_edits_after_undo if le.property("protobuf_field") == "nome")
        assert edit_nome_after_undo.text() == "Nome Inicial"
        assert edit_nome == edit_nome_after_undo  # Confirma que é o mesmo widget em memória (incremental!)
        
        
        # 4. Refaz (Redo)
        janela.historico.refazer()
        assert croqui.nome == "Nome Alterado"
        
        line_edits_after_redo = form.findChildren(QLineEdit)
        edit_nome_after_redo = next(le for le in line_edits_after_redo if le.property("protobuf_field") == "nome")
        assert edit_nome_after_redo.text() == "Nome Alterado"
        assert edit_nome == edit_nome_after_redo  # Confirma que é o mesmo widget
        
    finally:
        # Evita que closeEvent abra a caixa de diálogo QMessageBox perguntando se deseja salvar
        janela.historico.obter_pilha().setClean()


def test_atalho_qlineedit_engole_desfazer_global_e_como_evitar(qtbot):
    from PyQt6.QtGui import QKeySequence
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.show()
    
    try:
        # Cria o Croqui inicial
        croqui = Croqui()
        croqui.nome = "Nome Inicial"
        
        model = CroquiModel(croqui)
        controller = CroquiController(model, janela.historico.obter_pilha())
        janela.pagina_dados.carregar_dados(model, controller)
        
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        editor_dados = janela.pagina_dados.editor_dados
        form = editor_dados.form_padrao
        croqui_idx = editor_dados.tree_model.index(0, 0)
        editor_dados.tree_view.selectionModel().select(
            croqui_idx,
            editor_dados.tree_view.selectionModel().SelectionFlag.ClearAndSelect
        )
        editor_dados._on_tree_selection_changed(None, None)
        
        line_edits = form.findChildren(QLineEdit)
        edit_nome = next(le for le in line_edits if le.property("protobuf_field") == "nome")
        
        # Faz uma alteração no histórico (p. ex via árvore simulada ou apenas alterando a string por código e forçando editingFinished)
        # Vamos apenas forçar a criação do comando
        controller.alterar_primitivo(croqui, "nome", "Nome Inicial", "Novo Nome")
        assert janela.historico.obter_pilha().count() == 1
        
        # Foca no QLineEdit (cujo histórico de digitação interno está limpo)
        edit_nome.setFocus()
        QApplication.processEvents()
        assert edit_nome.hasFocus()
        assert not edit_nome.isUndoAvailable() # não há texto pra desfazer no buffer interno
        
        # Dispara Ctrl+Z diretamente no QLineEdit
        QTest.keyClick(edit_nome, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        
        # O QLineEdit não deve engolir o evento se ele não tem o que desfazer!
        # A pilha global DEVE ter sido acionada, voltando a count() para 0
        assert janela.historico.obter_pilha().index() == 0, "O Ctrl+Z foi engolido pelo QLineEdit e a ação global de desfazer não rodou!"
    finally:
        janela.historico.obter_pilha().setClean()


def test_widget_editor_dados_integracao_esvaziamento_presenca_e_undo_redo(qtbot):
    """Garante que a UI não possui botões Adicionar/Remover nos cards de campos,
    que esvaziar campo limpa a presença no proto, e que a reversão via Undo/Redo
    restaura perfeitamente presença e valores."""
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PyQt6.QtWidgets import QPushButton, QComboBox, QApplication
    
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.show()
    
    try:
        setor = Setor()
        setor.nome = "Setor Estacionamento"
        setor.sinal_de_celular = True
        
        model = CroquiModel(setor)
        controller = CroquiController(model, janela.historico.obter_pilha())
        janela.pagina_dados.carregar_dados(model, controller)
        
        QApplication.processEvents()
        
        editor_dados = janela.pagina_dados.editor_dados
        form = editor_dados.form_padrao
        
        setor_idx = editor_dados.tree_model.index(0, 0)
        editor_dados.tree_view.selectionModel().select(
            setor_idx,
            editor_dados.tree_view.selectionModel().SelectionFlag.ClearAndSelect
        )
        editor_dados._on_tree_selection_changed(None, None)
        QApplication.processEvents()
        
        # 1. Verifica ausência de botões contextuais "Adicionar" e "Remover" nos cards individuais
        botoes_card = [
            btn for btn in form.findChildren(QPushButton)
            if btn.text() in ("Adicionar", "Remover")
        ]
        assert len(botoes_card) == 0, f"Não deveria haver botões Adicionar/Remover nos cards, encontrados: {botoes_card}"
        
        # 2. Esvazia o campo nome e valida ClearField
        line_edits = form.findChildren(QLineEdit)
        edit_nome = next(le for le in line_edits if le.property("protobuf_field") == "nome")
        assert edit_nome.text() == "Setor Estacionamento"
        assert setor.HasField("nome")
        
        edit_nome.setText("")
        QApplication.processEvents()
        assert not setor.HasField("nome")
        
        # Desfaz e valida restauração
        janela.historico.desfazer()
        QApplication.processEvents()
        assert setor.HasField("nome")
        assert setor.nome == "Setor Estacionamento"
        assert edit_nome.text() == "Setor Estacionamento"
        
        # Refaz e valida nova limpeza
        janela.historico.refazer()
        QApplication.processEvents()
        assert not setor.HasField("nome")
        assert edit_nome.text() == ""
        
        # 3. Altera booleano tri-state para "Não informado"
        combos = form.findChildren(QComboBox)
        combo_sinal = next(cb for cb in combos if cb.property("protobuf_field") == "sinal_de_celular")
        
        # O valor inicial era True, então não deve ser o índice 0 ("Não informado")
        assert setor.HasField("sinal_de_celular")
        assert setor.sinal_de_celular is True
        
        # Seleciona o índice 0 ("Não informado")
        combo_sinal.setCurrentIndex(0)
        QApplication.processEvents()
        assert not setor.HasField("sinal_de_celular")
        
        # Desfaz
        janela.historico.desfazer()
        QApplication.processEvents()
        assert setor.HasField("sinal_de_celular")
        assert setor.sinal_de_celular is True
        
    finally:
        janela.historico.obter_pilha().setClean()

