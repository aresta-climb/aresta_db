# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import re
from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt6.QtGui import QFont
from google.protobuf.message import Message
from google.protobuf.descriptor import FieldDescriptor
from aresta_api.proto.generated import croqui_pb2

class ProtobufNode:
    def __init__(self, name, parent=None, descriptor=None, message=None, index_in_repeated=None, is_expando=False, eh_no_adicao=False):
        self.name = name
        self.parent_node = parent
        self.children = []
        self.descriptor = descriptor
        self.message = message
        self.index_in_repeated = index_in_repeated
        self.is_expando = is_expando
        self.eh_no_adicao = eh_no_adicao
        self._is_populated = False
        
        if parent:
            parent.children.append(self)
            
    def child(self, row):
        self._populate_children()
        if 0 <= row < len(self.children):
            return self.children[row]
        return None
        
    def child_count(self):
        self._populate_children()
        return len(self.children)
        
    def row(self):
        if self.parent_node:
            try:
                return self.parent_node.children.index(self)
            except ValueError:
                return 0
        return 0

    def _resolve_transparency(self, msg):
        """
        Retorna a mensagem interna/campo se msg for uma mensagem formatada como ONEOF ou ONEOF_CONTEUDO.
        """
        if msg is None or not hasattr(msg, "DESCRIPTOR"):
            return msg
            
        options = msg.DESCRIPTOR.GetOptions()
        if options.HasExtension(croqui_pb2.mensagem_formato_na_ui):
            formato = options.Extensions[croqui_pb2.mensagem_formato_na_ui]
            if formato == croqui_pb2.MensagemFormatoUi.ONEOF:
                for oneof in msg.DESCRIPTOR.oneofs:
                    active_field = msg.WhichOneof(oneof.name)
                    if active_field:
                        val = getattr(msg, active_field)
                        if val is not None and hasattr(val, "DESCRIPTOR"):
                            return self._resolve_transparency(val)
            elif formato == croqui_pb2.MensagemFormatoUi.ONEOF_CONTEUDO:
                # ONEOF_CONTEUDO sempre usa o campo 'conteudo' em memoria.
                conteudo_field = msg.DESCRIPTOR.fields_by_name.get("conteudo")
                if conteudo_field and conteudo_field.type == FieldDescriptor.TYPE_MESSAGE:
                    if msg.HasField("conteudo"):
                        val = getattr(msg, "conteudo")
                        if val is not None and hasattr(val, "DESCRIPTOR"):
                            return self._resolve_transparency(val)
                # conteudo e string ou nao esta set: retorna o wrapper (ex: ArquivoMarkdown)
        return msg

    def _is_descriptor_eligible(self, descriptor):
        if descriptor is None:
            return False
        options = descriptor.GetOptions()
        if options.HasExtension(croqui_pb2.mensagem_formato_na_ui):
            formato = options.Extensions[croqui_pb2.mensagem_formato_na_ui]
            return formato in (
                croqui_pb2.MensagemFormatoUi.SEPARADO,
                croqui_pb2.MensagemFormatoUi.ONEOF,
                croqui_pb2.MensagemFormatoUi.ONEOF_CONTEUDO,
            )
        return False

    def _collect_eligible_under_message(self, msg):
        results = []
        if msg is None or not hasattr(msg, "DESCRIPTOR"):
            return results
            
        for field in msg.DESCRIPTOR.fields:
            if field.type != FieldDescriptor.TYPE_MESSAGE:
                continue
                
            is_repeated = field.is_repeated
            
            if is_repeated:
                repeated_container = getattr(msg, field.name)
                eligible_items = []
                for i in range(len(repeated_container)):
                    item = repeated_container[i]
                    resolved_item = self._resolve_transparency(item)
                    if resolved_item is not None and hasattr(resolved_item, "DESCRIPTOR"):
                        if self._is_descriptor_eligible(resolved_item.DESCRIPTOR):
                            eligible_items.append((resolved_item, i))
                        else:
                            # Busca recursiva para extrair elegíveis sob a mensagem intermediária
                            recursive_results = self._collect_eligible_under_message(resolved_item)
                            for rec_item in recursive_results:
                                if rec_item["is_repeated"]:
                                    for sub_msg, sub_idx in rec_item["items"]:
                                        eligible_items.append((sub_msg, i))
                                else:
                                    eligible_items.append((rec_item["message"], i))
                if eligible_items:
                    results.append({
                        "field": field,
                        "is_repeated": True,
                        "items": eligible_items
                    })
            else:
                if msg.HasField(field.name):
                    sub_msg = getattr(msg, field.name)
                    resolved_msg = self._resolve_transparency(sub_msg)
                    if resolved_msg is not None and hasattr(resolved_msg, "DESCRIPTOR"):
                        if self._is_descriptor_eligible(resolved_msg.DESCRIPTOR):
                            results.append({
                                "field": field,
                                "is_repeated": False,
                                "message": resolved_msg
                            })
                        else:
                            # Busca recursiva
                            recursive_results = self._collect_eligible_under_message(resolved_msg)
                            for rec_item in recursive_results:
                                results.append(rec_item)
        return results

    def _populate_children(self):
        if self._is_populated:
            return
        
        self._is_populated = True
        
        if self.is_expando or self.eh_no_adicao:
            return
            
        if self.message is not None:
            resolved_msg = self._resolve_transparency(self.message)
            if resolved_msg is None or not hasattr(resolved_msg, "DESCRIPTOR"):
                return
                
            eligible_children = self._collect_eligible_under_message(resolved_msg)
            
            for child_info in eligible_children:
                field = child_info["field"]
                if child_info["is_repeated"]:
                    # Criar nó expando
                    from editor.views.protobuf_widget_factory import ProtobufWidgetFactory
                    expando_name = ProtobufWidgetFactory.get_label(field)
                    
                    exp_node = ProtobufNode(
                        name=expando_name,
                        parent=self,
                        descriptor=field,
                        message=None,
                        is_expando=True
                    )
                    
                    for item_msg, i in child_info["items"]:
                        ProtobufNode(
                            name=f"[{i}]",
                            parent=exp_node,
                            descriptor=field,
                            message=item_msg,
                            index_in_repeated=i,
                            is_expando=False
                        )
                    
                    # Converte CamelCase do tipo para palavras separadas por espaço
                    # Usa o nome original do tipo (em CamelCase) e nao o retorno de get_label
                    # pois get_label aplica capitalize() que apaga as maiusculas internas
                    if hasattr(field, 'message_type') and field.message_type:
                        nome_tipo_bruto = field.message_type.name
                        # Primeiro verifica se ha texto_na_ui definido na mensagem
                        opts_msg = field.message_type.GetOptions()
                        if opts_msg.HasExtension(croqui_pb2.mensagem_texto_na_ui):
                            tipo_label = opts_msg.Extensions[croqui_pb2.mensagem_texto_na_ui]
                        else:
                            # Separa CamelCase com espacos e mantém a capitalizacao original
                            tipo_label = re.sub(r'(?<=[a-z\u00e0-\u00fa])(?=[A-Z\u00c0-\u00da])', ' ', nome_tipo_bruto)
                    else:
                        tipo_label = expando_name
                    ProtobufNode(
                        name=f"+ Adicionar {tipo_label}",
                        parent=exp_node,
                        descriptor=field,
                        message=None,
                        is_expando=False,
                        eh_no_adicao=True
                    )
                else:
                    single_msg = child_info["message"]
                    ProtobufNode(
                        name=field.name,
                        parent=self,
                        descriptor=field,
                        message=single_msg,
                        index_in_repeated=None,
                        is_expando=False
                    )


class ProtobufTreeViewAdapter(QAbstractItemModel):
    def __init__(self, root_message, parent=None):
        super().__init__(parent)
        self.root_message = root_message
        self.root_node = ProtobufNode(name="root", message=None)
        self.croqui_node = ProtobufNode(
            name="Croqui",
            parent=self.root_node,
            descriptor=self.root_message.DESCRIPTOR,
            message=self.root_message,
            is_expando=False
        )
        
    def rebuild_tree(self):
        self.beginResetModel()
        self.root_node = ProtobufNode(name="root", message=None)
        self.croqui_node = ProtobufNode(
            name="Croqui",
            parent=self.root_node,
            descriptor=self.root_message.DESCRIPTOR,
            message=self.root_message,
            is_expando=False
        )
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
            
        return parent_node.child_count()
        
    def columnCount(self, parent=QModelIndex()):
        return 1
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
            
        node = index.internalPointer()

        if role == Qt.ItemDataRole.FontRole:
            # Nó virtual de adição: fonte em itálico para distingui-lo dos itens reais
            if node.eh_no_adicao:
                fonte = QFont()
                fonte.setItalic(True)
                return fonte
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        # A partir daqui: role == DisplayRole
        # Nó virtual de adição: exibe texto fixo
        if node.eh_no_adicao:
            return node.name

        if node is self.croqui_node:
            return "Croqui"
            
        if node.is_expando:
            return node.name
            
        msg = node.message
        if msg is not None:
            resolved_msg = node._resolve_transparency(msg)
            
            # 1. Verifica se a mensagem resolvida possui algum campo com a extensão 'titulo_na_ui' setado como True
            titulo_final = None
            if hasattr(resolved_msg, "DESCRIPTOR"):
                for field in resolved_msg.DESCRIPTOR.fields:
                    options = field.GetOptions()
                    if options.HasExtension(croqui_pb2.titulo_na_ui) and options.Extensions[croqui_pb2.titulo_na_ui]:
                        val = getattr(resolved_msg, field.name)
                        if val:
                            titulo_final = str(val)
                            break
            if titulo_final:
                return titulo_final

            if hasattr(resolved_msg, "DESCRIPTOR") and resolved_msg.DESCRIPTOR.name == "ArquivoMarkdown":
                msg_markdown = resolved_msg
                active_field = msg_markdown.WhichOneof("arquivo")
                if active_field == "conteudo" and msg_markdown.conteudo:
                    # Extrai o primeiro cabeçalho H1 (texto iniciado com #)
                    for line in msg_markdown.conteudo.splitlines():
                        line_stripped = line.strip()
                        if line_stripped.startswith("#"):
                            return line_stripped.lstrip("#").strip()
                    return "Conteúdo Markdown"
                elif active_field == "caminho" and msg_markdown.caminho:
                    # Ex: "introducao.md" -> "Introdução"
                    import os
                    filename = os.path.basename(msg_markdown.caminho)
                    name_without_ext, _ = os.path.splitext(filename)
                    return name_without_ext.replace("_", " ").capitalize()
                return "Markdown sem título"

            # 2. Resolve wrappers genéricos (qualquer mensagem com um oneof ativo)
            for oneof in msg.DESCRIPTOR.oneofs:
                active_field = msg.WhichOneof(oneof.name)
                if active_field:
                    if active_field == "caminho" and hasattr(msg, "caminho") and msg.caminho:
                        import os
                        filename = os.path.basename(msg.caminho)
                        name_without_ext, _ = os.path.splitext(filename)
                        return name_without_ext.replace("_", " ").capitalize()
                        
                    inner_msg = getattr(msg, active_field)
                    if hasattr(inner_msg, "DESCRIPTOR"):
                        # Tenta obter o titulo_na_ui da sub-mensagem ativa
                        inner_title = None
                        for field in inner_msg.DESCRIPTOR.fields:
                            options = field.GetOptions()
                            if options.HasExtension(croqui_pb2.titulo_na_ui) and options.Extensions[croqui_pb2.titulo_na_ui]:
                                val = getattr(inner_msg, field.name)
                                if val:
                                    inner_title = str(val)
                                    break
                        if not inner_title and hasattr(inner_msg, "nome") and getattr(inner_msg, "nome"):
                            inner_title = getattr(inner_msg, "nome")
                        if inner_title:
                            return inner_title
            
            # Se for um wrapper puro (só possui 1 oneof e nenhum outro campo)
            is_pure_wrapper = len(msg.DESCRIPTOR.oneofs) == 1 and len(msg.DESCRIPTOR.fields) == len(msg.DESCRIPTOR.oneofs[0].fields)
            if is_pure_wrapper:
                if msg.DESCRIPTOR.name.startswith("Arquivo"):
                    return "Novo " + msg.DESCRIPTOR.name[7:]
                else:
                    return "Nova " + msg.DESCRIPTOR.name if msg.DESCRIPTOR.name.endswith("a") else "Novo " + msg.DESCRIPTOR.name

            if hasattr(msg, "nome") and getattr(msg, "nome"):
                return getattr(msg, "nome")
            if hasattr(msg, "texto") and getattr(msg, "texto"):
                return getattr(msg, "texto")
                
        if node.descriptor:
            from editor.views.protobuf_widget_factory import ProtobufWidgetFactory
            return ProtobufWidgetFactory.get_label(node.descriptor)
            
        return node.name
        
    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
            
        if not parent.isValid():
            parent_node = self.root_node
        else:
            parent_node = parent.internalPointer()
            
        child_node = parent_node.child(row)
        if child_node:
            return self.createIndex(row, column, child_node)
        return QModelIndex()
        
    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
            
        child_node = index.internalPointer()
        parent_node = child_node.parent_node
        
        if parent_node == self.root_node or parent_node is None:
            return QModelIndex()
            
        return self.createIndex(parent_node.row(), 0, parent_node)

    def find_index_for_message_id(self, msg_id, parent_idx=QModelIndex()):
        from editor.views.widget_editor_dados import _get_id
        if self.root_message and _get_id(self.root_message) == msg_id:
            return self.index(0, 0)
            
        rows = self.rowCount(parent_idx)
        for r in range(rows):
            idx = self.index(r, 0, parent_idx)
            node = idx.internalPointer()
            if node:
                if node.message is not None and _get_id(node.message) == msg_id:
                    return idx
                child_match = self.find_index_for_message_id(msg_id, idx)
                if child_match.isValid():
                    return child_match
        return QModelIndex()

    def find_index_for_path(self, path, parent_idx=QModelIndex()):
        from editor.views.widget_editor_dados import get_node_path
        
        # DEBUG
        if parent_idx == QModelIndex():
            print(f"SEARCHING FOR PATH: {path}")
            
        if self.root_message and path == "node:Croqui":
            return self.index(0, 0)
            
        rows = self.rowCount(parent_idx)
        for r in range(rows):
            idx = self.index(r, 0, parent_idx)
            node = idx.internalPointer()
            if node:
                # DEBUG
                # print(f"CHECKING PATH: {get_node_path(node)}")
                if get_node_path(node) == path:
                    print(f"FOUND PATH: {path}")
                    return idx
                child_match = self.find_index_for_path(path, idx)
                if child_match.isValid():
                    return child_match
        return QModelIndex()

    def find_expando_index(self, msg_id, campo):
        parent_idx = self.find_index_for_message_id(msg_id)
        if not parent_idx.isValid():
            return QModelIndex()
            
        parent_node = parent_idx.internalPointer()
        parent_node._populate_children()
        
        for r in range(len(parent_node.children)):
            child = parent_node.children[r]
            if child.is_expando and child.descriptor and child.descriptor.name == campo:
                return self.index(r, 0, parent_idx)
                
        return QModelIndex()

    def _on_campo_alterado(self, msg_id, campo, novo_valor):
        # Atualiza o nó se o campo modificado for relevante para o rótulo
        idx = self.find_index_for_message_id(msg_id)
        if idx.isValid():
            self.dataChanged.emit(idx, idx)

    def _on_item_adicionado(self, msg_id, campo, idx):
        exp_idx = self.find_expando_index(msg_id, campo)
        if not exp_idx.isValid():
            return
            
        exp_node = exp_idx.internalPointer()
        if not exp_node._is_populated:
            return
            
        parent_node = exp_node.parent_node
        if parent_node and parent_node.message:
            try:
                repeated_field = getattr(parent_node.message, campo)
                item_msg = repeated_field[idx]
            except (AttributeError, IndexError):
                return
                
            # 1. Corrige os índices dos filhos que estão após o novo índice
            for child in exp_node.children:
                if child.index_in_repeated is not None and child.index_in_repeated >= idx:
                    child.index_in_repeated += 1
                    child.name = f"[{child.index_in_repeated}]"
                    
            # 2. Cria o novo nó, resolvendo a transparência para o item adicionado
            resolved_msg = exp_node._resolve_transparency(item_msg)
            
            new_node = ProtobufNode(
                name=f"[{idx}]",
                parent=None,
                descriptor=exp_node.descriptor,
                message=resolved_msg,
                index_in_repeated=idx,
                is_expando=False
            )
            
            # 3. Notifica inserção
            self.beginInsertRows(exp_idx, idx, idx)
            new_node.parent_node = exp_node
            exp_node.children.insert(idx, new_node)
            self.endInsertRows()
            
            # 4. Atualiza visualmente os rótulos deslocados
            row_count = len(exp_node.children)
            if row_count > idx + 1:
                first_changed = self.index(idx + 1, 0, exp_idx)
                last_changed = self.index(row_count - 2, 0, exp_idx)
                self.dataChanged.emit(first_changed, last_changed)

    def _on_item_removido(self, msg_id, campo, idx):
        exp_idx = self.find_expando_index(msg_id, campo)
        if not exp_idx.isValid():
            return
            
        exp_node = exp_idx.internalPointer()
        if not exp_node._is_populated:
            return
            
        # 1. Encontra e remove o filho correspondente ao índice
        row_to_remove = -1
        for r in range(len(exp_node.children)):
            child = exp_node.children[r]
            if child.index_in_repeated == idx:
                row_to_remove = r
                break
                
        if row_to_remove != -1:
            self.beginRemoveRows(exp_idx, row_to_remove, row_to_remove)
            del exp_node.children[row_to_remove]
            self.endRemoveRows()
            
            # 2. Ajusta index_in_repeated dos nós restantes
            for child in exp_node.children:
                if child.index_in_repeated is not None and child.index_in_repeated > idx:
                    child.index_in_repeated -= 1
                    child.name = f"[{child.index_in_repeated}]"
                    
            # 3. Atualiza os rótulos            
            row_count = len(exp_node.children)
            if row_count > row_to_remove:
                first_changed = self.index(row_to_remove, 0, exp_idx)
                last_changed = self.index(row_count - 1, 0, exp_idx)
                self.dataChanged.emit(first_changed, last_changed)

    def _on_item_movido(self, msg_id, campo, index_from, index_to):
        exp_idx = self.find_expando_index(msg_id, campo)
        if not exp_idx.isValid():
            return
            
        exp_node = exp_idx.internalPointer()
        if not exp_node._is_populated:
            return

        # QAbstractItemModel has beginMoveRows/endMoveRows.
        # But for QTreeView we must be careful with destination index.
        dest_idx = index_to if index_to < index_from else index_to + 1
        
        self.beginMoveRows(exp_idx, index_from, index_from, exp_idx, dest_idx)
        
        child = exp_node.children.pop(index_from)
        exp_node.children.insert(index_to, child)
        
        self.endMoveRows()
        
        # Atualiza os label e index_in_repeated
        min_idx = min(index_from, index_to)
        max_idx = max(index_from, index_to)
        
        for i in range(min_idx, max_idx + 1):
            c = exp_node.children[i]
            if c.index_in_repeated is not None:
                c.index_in_repeated = i
                c.name = f"[{i}]"
                
        # Notifica mudanca visual
        first_changed = self.index(min_idx, 0, exp_idx)
        last_changed = self.index(max_idx, 0, exp_idx)
        self.dataChanged.emit(first_changed, last_changed)
