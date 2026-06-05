import os
import re
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QLabel, QScrollArea
from google.protobuf.descriptor import FieldDescriptor
from aresta_api.proto.generated import croqui_pb2

class ProtobufWidgetFactory:
    _comments_cache = None
    
    @classmethod
    def _load_comments(cls):
        if cls._comments_cache is not None:
            return cls._comments_cache
            
        cls._comments_cache = {}
        # Procuramos croqui.proto em localizações conhecidas
        proto_paths = [
            "aresta_api/proto/croqui.proto",
            "../aresta_api/proto/croqui.proto",
            "proto/croqui.proto"
        ]
        proto_file = None
        for p in proto_paths:
            if os.path.exists(p):
                proto_file = p
                break
                
        if not proto_file:
            # Tenta encontrar recursivamente no workspace caso executado de outro CWD
            for root, dirs, files in os.walk("."):
                if "croqui.proto" in files:
                    proto_file = os.path.join(root, "croqui.proto")
                    break
                    
        if not proto_file:
            return cls._comments_cache
            
        try:
            with open(proto_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return cls._comments_cache
            
        current_msg = None
        pending_comments = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("//"):
                content = line[2:].strip()
                if not any(content.startswith(x) for x in ("Copyright", "==", "--", "NEXT_ID", "TODO")):
                    pending_comments.append(content)
                continue
                
            msg_match = re.match(r"message\s+(\w+)", line)
            if msg_match:
                current_msg = msg_match.group(1)
                pending_comments = []
                continue
                
            if line == "}":
                current_msg = None
                pending_comments = []
                continue
                
            if current_msg:
                field_match = re.match(r"(?:repeated\s+)?([\w\.]+)\s+(\w+)\s*=", line)
                if field_match:
                    field_name = field_match.group(2)
                    if pending_comments:
                        cls._comments_cache[(current_msg, field_name)] = " ".join(pending_comments)
                    pending_comments = []
                elif line.startswith("oneof"):
                    pending_comments = []
                    
        return cls._comments_cache
    
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
        cls._load_comments()
        if cls._comments_cache and field_descriptor.containing_type:
            msg_name = field_descriptor.containing_type.name
            field_name = field_descriptor.name
            return cls._comments_cache.get((msg_name, field_name), "")
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
