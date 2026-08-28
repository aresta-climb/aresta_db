# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QApplication
from editor.core.atualizador_ui import AtualizadorUI

def test_salvar_e_restaurar_foco(qtbot):
    # qtbot é passado automaticamente pelo pytest-qt
    parent = QWidget()
    qtbot.addWidget(parent)
    
    layout = QVBoxLayout(parent)
    
    edit = QLineEdit(parent)
    edit.setText("Hello World")
    edit.setProperty("protobuf_field", "nome")
    edit.setProperty("protobuf_msg_id", 12345)
    layout.addWidget(edit)
    
    parent.show()
    edit.setFocus()
    edit.setCursorPosition(5)
    
    app = QApplication.instance()
    app.processEvents()
    
    atualizador = AtualizadorUI()
    atualizador.salvar_estado_foco(parent)
    
    assert atualizador.campo_focado == "nome"
    assert atualizador.msg_id_focada == 12345
    assert atualizador.posicao_cursor == 5
    
    # Remove do layout e define parent como None imediatamente
    layout.removeWidget(edit)
    edit.setParent(None)
    edit.deleteLater()
    app.processEvents()
    
    # Cria o novo widget na UI reconstruída
    edit_novo = QLineEdit(parent)
    edit_novo.setText("Hello Python")
    edit_novo.setProperty("protobuf_field", "nome")
    edit_novo.setProperty("protobuf_msg_id", 12345)
    layout.addWidget(edit_novo)
    
    # Garante que o novo widget está visível para poder receber foco
    edit_novo.show()
    edit_novo.clearFocus()
    app.processEvents()
    
    atualizador.restaurar_estado_foco(parent)
    app.processEvents()
    
    # Verifica que o edit_novo agora é o widget focado da janela
    assert parent.focusWidget() == edit_novo
    assert edit_novo.cursorPosition() == 5
