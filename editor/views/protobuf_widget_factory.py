# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import os
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QLabel, QScrollArea
from PyQt6.QtGui import QDoubleValidator, QRegularExpressionValidator, QValidator
from PyQt6.QtCore import QRegularExpression
from google.protobuf.descriptor import FieldDescriptor
from aresta_api.proto.generated import croqui_pb2
from editor.core.proto_comments import get_proto_comments


class SpinBoxVazio(QSpinBox):
    """
    QSpinBox que suporta estado vazio (ausente/None).
    Quando vazio, não exibe nenhum texto.
    Ao pressionar as setas para cima ou para baixo estando vazio, inicializa com 0.
    """
    VALOR_NULO = -2147483648

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(self.VALOR_NULO, 2147483647)
        self.setMaximumWidth(150)
        self.lineEdit().setPlaceholderText("Opcional")

    def textFromValue(self, val):
        if val == self.VALOR_NULO:
            return ""
        return str(val)

    def valueFromText(self, text):
        text_str = text.strip()
        if not text_str:
            return self.VALOR_NULO
        try:
            return int(text_str)
        except ValueError:
            return self.VALOR_NULO

    def validate(self, text, pos):
        text_str = text.strip()
        if not text_str:
            return (QValidator.State.Acceptable, text, pos)
        if text_str == "-":
            return (QValidator.State.Intermediate, text, pos)
        try:
            val = int(text_str)
            if self.minimum() <= val <= self.maximum():
                return (QValidator.State.Acceptable, text, pos)
            return (QValidator.State.Invalid, text, pos)
        except ValueError:
            return (QValidator.State.Invalid, text, pos)

    def stepBy(self, steps):
        if self.value() == self.VALOR_NULO:
            self.setValue(0)
        else:
            super().stepBy(steps)

    def wheelEvent(self, event):
        event.ignore()


class ComboBoxSemScroll(QComboBox):
    """
    QComboBox que ignora eventos de rolagem do mouse (wheelEvent) para
    evitar alterar a seleção acidentalmente ao rolar o formulário.
    """
    def wheelEvent(self, event):
        event.ignore()


class ProtobufWidgetFactory:
    VALOR_INTEIRO_NULO = SpinBoxVazio.VALOR_NULO

    @classmethod
    def _load_comments(cls):
        # Apenas para retrocompatibilidade
        return get_proto_comments()
    
    @staticmethod
    def get_booleano_labels(field_descriptor):
        """
        Retorna uma tupla (texto_indefinido, texto_sim, texto_nao) para um campo booleano,
        lendo anotações no FieldOptions ou usando valores padrão.
        """
        options = field_descriptor.GetOptions()
        texto_indefinido = "Não informado"
        texto_sim = "Sim"
        texto_nao = "Não"

        if options.HasExtension(croqui_pb2.booleano_texto_indefinido):
            custom_indef = options.Extensions[croqui_pb2.booleano_texto_indefinido]
            if custom_indef:
                texto_indefinido = custom_indef
        if options.HasExtension(croqui_pb2.booleano_texto_sim):
            custom_sim = options.Extensions[croqui_pb2.booleano_texto_sim]
            if custom_sim:
                texto_sim = custom_sim
        if options.HasExtension(croqui_pb2.booleano_texto_nao):
            custom_nao = options.Extensions[croqui_pb2.booleano_texto_nao]
            if custom_nao:
                texto_nao = custom_nao

        return texto_indefinido, texto_sim, texto_nao

    @staticmethod
    def create_widget(field_descriptor):
        """
        Creates a primitive PyQt6 widget for the given FieldDescriptor.
        """
        if field_descriptor.type in (FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_INT64,
                                     FieldDescriptor.TYPE_UINT32, FieldDescriptor.TYPE_UINT64,
                                     FieldDescriptor.TYPE_SINT32, FieldDescriptor.TYPE_SINT64):
            return SpinBoxVazio()
            
        if field_descriptor.type in (FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE):
            line_edit = QLineEdit()
            regex = QRegularExpression(r"^-?\d*(\.\d+)?$")
            validador = QRegularExpressionValidator(regex, line_edit)
            line_edit.setValidator(validador)
            line_edit.setPlaceholderText("Opcional")
            line_edit.setMaximumWidth(450)
            return line_edit
            
        if field_descriptor.type == FieldDescriptor.TYPE_BOOL:
            combo = ComboBoxSemScroll()
            texto_indefinido, texto_sim, texto_nao = ProtobufWidgetFactory.get_booleano_labels(field_descriptor)
            combo.addItem(texto_indefinido, None)
            combo.addItem(texto_sim, True)
            combo.addItem(texto_nao, False)
            combo.setMaximumWidth(200)
            return combo
            
        if field_descriptor.type == FieldDescriptor.TYPE_ENUM:
            combo = ComboBoxSemScroll()
            for enum_val in field_descriptor.enum_type.values:
                label = enum_val.name
                options = enum_val.GetOptions()
                if options.HasExtension(croqui_pb2.enum_texto_na_ui):
                    label = options.Extensions[croqui_pb2.enum_texto_na_ui]
                combo.addItem(label, enum_val.number)
            combo.setMaximumWidth(200)
            return combo
            
        line_edit = QLineEdit()
        line_edit.setMaximumWidth(450)
        return line_edit

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
