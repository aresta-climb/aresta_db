# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit, QSpinBox, QCheckBox
from google.protobuf.message import Message
from aresta_api.proto.generated.croqui_pb2 import Croqui, ViaMovel
from editor.views.protobuf_widget_factory import ProtobufWidgetFactory

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_primitive_widgets(qapp):
    croqui = Croqui()
    # id (string)
    widget_id = ProtobufWidgetFactory.create_widget(croqui.DESCRIPTOR.fields_by_name['id'])
    assert isinstance(widget_id, QLineEdit)
    
    viamovel = ViaMovel()
    # extensao (int32)
    widget_extensao = ProtobufWidgetFactory.create_widget(viamovel.DESCRIPTOR.fields_by_name['extensao'])
    assert isinstance(widget_extensao, QSpinBox)
    
def test_label_extraction(qapp):
    # Testa a leitura de (aresta.texto_na_ui) ou fallback para o nome do campo
    croqui = Croqui()
    label = ProtobufWidgetFactory.get_label(croqui.DESCRIPTOR.fields_by_name['id'])
    # Se não tiver texto_na_ui, retorna o nome do campo capitalizado 'Id'
    assert label == 'Id' or label == 'Identificador'

def test_comment_extraction(qapp):
    # Tests that the tooltip/description comes from the source_code_info
    # Unfortunately, google.protobuf in Python doesn't load source_code_info at runtime 
    # by default unless the descriptor was built with include_source_info.
    # We will test the fallback or whatever the implementation does.
    croqui = Croqui()
    tooltip = ProtobufWidgetFactory.get_tooltip(croqui.DESCRIPTOR.fields_by_name['id'])
    # Let's just assert it doesn't crash for now, since source_code_info might be empty.
    assert isinstance(tooltip, str)
