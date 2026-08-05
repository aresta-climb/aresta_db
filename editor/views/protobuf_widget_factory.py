# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import os
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QLabel, QScrollArea
from google.protobuf.descriptor import FieldDescriptor
from aresta_api.proto.generated import croqui_pb2
from editor.core.proto_comments import get_proto_comments

class ProtobufWidgetFactory:
    @classmethod
    def _load_comments(cls):
        # Apenas para retrocompatibilidade
        return get_proto_comments()
    
    @staticmethod
    def create_widget(field_descriptor):
        """
        Creates a primitive PyQt6 widget for the given FieldDescriptor.
        """
        if field_descriptor.type in (FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_INT64,
                                     FieldDescriptor.TYPE_UINT32, FieldDescriptor.TYPE_UINT64,
                                     FieldDescriptor.TYPE_SINT32, FieldDescriptor.TYPE_SINT64):
            spin = QSpinBox()
            spin.setRange(-2147483648, 2147483647) 
            return spin
            
        if field_descriptor.type in (FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE):
            spin = QDoubleSpinBox()
            spin.setRange(-1e9, 1e9)
            return spin
            
        if field_descriptor.type == FieldDescriptor.TYPE_BOOL:
            return QCheckBox()
            
        if field_descriptor.type == FieldDescriptor.TYPE_ENUM:
            combo = QComboBox()
            for enum_val in field_descriptor.enum_type.values:
                # Usar texto_na_ui ou nome do enum valor se aplicável? 
                combo.addItem(enum_val.name, enum_val.number)
            return combo
            
        return QLineEdit()

    @staticmethod
    def get_label(descriptor):
        """
        Extrai o rótulo a partir das opções customizadas (texto_na_ui) ou usa por padrão o nome capitalizado.
        Funciona tanto para FieldDescriptor quanto para Descriptor (Message).
        """
        options = descriptor.GetOptions()
        
        # Verifica se é um campo
        if hasattr(descriptor, 'type'):
            if options.HasExtension(croqui_pb2.texto_na_ui):
                return options.Extensions[croqui_pb2.texto_na_ui]
        else:
            # É uma mensagem
            if options.HasExtension(croqui_pb2.mensagem_texto_na_ui):
                return options.Extensions[croqui_pb2.mensagem_texto_na_ui]
            
        return descriptor.name.replace("_", " ").capitalize()

    @classmethod
    def get_tooltip(cls, field_descriptor):
        """
        Extracts documentation from protobuf source comments.
        """
        cache = get_proto_comments()
        if cache and field_descriptor.containing_type:
            msg_name = field_descriptor.containing_type.name
            field_name = field_descriptor.name
            return cache.get((msg_name, field_name), "")
        return ""


class RepeatedFieldWidget(QWidget):
    """
    Widget especializado para renderizar listas dinâmicas de primitivos.
    Mantido para retrocompatibilidade caso seja importado por outros arquivos.
    """
    def __init__(self, field_descriptor, parent=None):
        super().__init__(parent)
        self.field_descriptor = field_descriptor
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.items_layout = QVBoxLayout()
        self.layout.addLayout(self.items_layout)
        
        self.btn_add = QPushButton("+ Adicionar")
        self.btn_add.clicked.connect(self.add_item)
        self.layout.addWidget(self.btn_add)
        
    def add_item(self):
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        
        inner_widget = ProtobufWidgetFactory.create_widget(self.field_descriptor)
        
        btn_remove = QPushButton("-")
        btn_remove.clicked.connect(lambda: self.remove_item(item_widget))
        
        item_layout.addWidget(inner_widget)
        item_layout.addWidget(btn_remove)
        
        self.items_layout.addWidget(item_widget)
        
    def remove_item(self, widget):
        self.items_layout.removeWidget(widget)
        widget.deleteLater()
