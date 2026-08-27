# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

def test_container_repeated_widget_undo_redo_sync(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
    from editor.views.widget_editor_dados import WidgetEditorDados, ContainerRepeatedWidget
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
    
    croqui = Croqui()
    pico0 = croqui.picos.add()
    pico0.nome = "Pico Zero"
    pico1 = croqui.picos.add()
    pico1.nome = "Pico Um"
    pico2 = croqui.picos.add()
    pico2.nome = "Pico Dois"
    
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    # Usa o field real para evitar AttributeError em GetOptions()
    field = croqui.DESCRIPTOR.fields_by_name["picos"]
    
    container = ContainerRepeatedWidget(croqui, field, form)
    
    # 3 itens na interface
    assert container.items_layout.count() == 3
    assert container.items_layout.itemAt(0).widget().property("repeated_index") == 0
    assert container.items_layout.itemAt(1).widget().property("repeated_index") == 1
    assert container.items_layout.itemAt(2).widget().property("repeated_index") == 2
    
    # Remove index 1 via controller
    pico1_removido = croqui.picos[1]
    controller.remover_repeated(croqui, "picos", 1, pico1_removido)
    
    # 2 itens na interface
    assert container.items_layout.count() == 2
    assert container.items_layout.itemAt(0).widget().property("repeated_index") == 0
    assert container.items_layout.itemAt(1).widget().property("repeated_index") == 1
    
    # Undo (restaura index 1)
    undo_stack.undo()
    
    # 3 itens na interface
    assert container.items_layout.count() == 3
    assert container.items_layout.itemAt(0).widget().property("repeated_index") == 0
    assert container.items_layout.itemAt(1).widget().property("repeated_index") == 1
    assert container.items_layout.itemAt(2).widget().property("repeated_index") == 2
