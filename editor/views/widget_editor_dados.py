from PyQt6.QtWidgets import QWidget, QHBoxLayout, QTreeView, QStackedWidget, QScrollArea, QVBoxLayout, QLabel, QFrame, QPushButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QTextEdit, QTextBrowser, QMenu
from PyQt6.QtCore import Qt, QModelIndex, QUrl, QItemSelectionModel
from PyQt6.QtGui import QImage, QTextDocument, QTextCursor
from google.protobuf.descriptor import FieldDescriptor
from aresta_api.proto.generated import croqui_pb2
from editor.views.tree_view_adapter import ProtobufTreeViewAdapter
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens
from editor.views.widget_editor_mapas import WidgetEditorMapas
from editor.views.protobuf_widget_factory import ProtobufWidgetFactory
from ..core.atualizador_ui import AtualizadorUI
from google.protobuf.message_factory import GetMessageClass
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtCore import QTimer

from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtGui import QKeySequence

class GlobalUndoRedoFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            # Check for Undo
            if event.matches(QKeySequence.StandardKey.Undo):
                if True:
                    # Triggers the main window undo action
                    win = obj.window()
                    for act in win.actions():
                        if act.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut and (act.text() == "Desfazer" or act.text() == "Undo"):
                            act.trigger()
                            return True
            # Check for Redo
            elif event.matches(QKeySequence.StandardKey.Redo):
                if True:
                    # Triggers the main window redo action
                    win = obj.window()
                    for act in win.actions():
                        if act.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut and (act.text() == "Refazer" or act.text() == "Redo"):
                            act.trigger()
                            return True
        return super().eventFilter(obj, event)





def get_node_path(node):
    path = []
    curr = node
    while curr:
        if curr.eh_no_adicao:
            path.append("+adicao")
        elif curr.is_expando:
            nome_campo = curr.descriptor.name if curr.descriptor else curr.name
            path.append(f"expando:{nome_campo}")
        elif curr.index_in_repeated is not None:
            path.append(f"item:{curr.index_in_repeated}")
        else:
            path.append(f"node:{curr.name}")
        curr = curr.parent_node
    return "/".join(reversed(path))

def _get_id(obj):
    return obj.obter_id_nativo() if hasattr(obj, 'obter_id_nativo') else id(obj)

class AutoScalingTextBrowser(QTextBrowser):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scale_images()
        
    def setMarkdown(self, markdown):
        super().setMarkdown(markdown)
        self.scale_images()
        
    def scale_images(self):
        doc = self.document()
        viewport_width = self.viewport().width() - 24
        if viewport_width <= 0:
            return
            
        block = doc.begin()
        while block.isValid():
            char_it = block.begin()
            while not char_it.atEnd():
                fragment = char_it.fragment()
                if fragment.isValid():
                    fmt = fragment.charFormat()
                    if fmt.isImageFormat():
                        img_fmt = fmt.toImageFormat()
                        name = img_fmt.name()
                        
                        res = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(name))
                        if res is not None:
                            original_size = res.size()
                        else:
                            url = doc.baseUrl().resolved(QUrl(name))
                            img = QImage(url.toLocalFile())
                            if not img.isNull():
                                original_size = img.size()
                                doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), img)
                            else:
                                original_size = None
                                
                        if original_size:
                            orig_w = original_size.width()
                            orig_h = original_size.height()
                            
                            if orig_w > viewport_width:
                                new_w = viewport_width
                                new_h = int(orig_h * (viewport_width / orig_w))
                            else:
                                new_w = orig_w
                                new_h = orig_h
                                
                            if img_fmt.width() != new_w or img_fmt.height() != new_h:
                                img_fmt.setWidth(new_w)
                                img_fmt.setHeight(new_h)
                                
                                cursor = QTextCursor(doc)
                                cursor.setPosition(fragment.position())
                                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, fragment.length())
                                cursor.setCharFormat(img_fmt)
                                
                char_it += 1
            block = block.next()

class WidgetEditorMarkdown(QWidget):
    def __init__(self, msg, field, formulario, parent=None):
        super().__init__(parent)
        self.msg = msg
        self.field = field
        self.model = formulario.model
        self.controller = formulario.controller
        self.formulario = formulario
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.editor = QTextEdit()
        self.editor.setUndoRedoEnabled(False)
        self.editor.setPlaceholderText("Escreva seu Markdown aqui...")
        self.editor.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #fafafa;
                color: #333;
                padding: 8px;
            }
            QTextEdit:focus {
                border: 1px solid #2b579a;
            }
        """)
        
        self.preview = AutoScalingTextBrowser()
        self.preview.setPlaceholderText("A pré-visualização aparecerá aqui...")
        self.preview.setStyleSheet("""
            QTextBrowser {
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                font-size: 10.5pt;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #ffffff;
                color: #222;
                padding: 12px;
            }
        """)
        
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_label = QLabel("Edição (Markdown Raw)")
        left_label.setStyleSheet("color: #666; font-size: 8.5pt; font-weight: bold;")
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.editor)
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_label = QLabel("Pré-visualização (Renderizado)")
        right_label.setStyleSheet("color: #666; font-size: 8.5pt; font-weight: bold;")
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.preview)
        
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 1)
        
        self.setMinimumHeight(400)
        
        # Resolve caminho do banco de dados a partir da hierarquia de pais
        caminho_db = None
        curr = parent
        while curr:
            if hasattr(curr, "caminho_croqui") and curr.caminho_croqui:
                caminho_db = curr.caminho_croqui / "database"
                break
            curr = curr.parent() if hasattr(curr, "parent") and callable(curr.parent) else None
            
        if caminho_db:
            base_url = QUrl.fromLocalFile(str(caminho_db) + "/")
            self.preview.document().setBaseUrl(base_url)
        
        # Set initial content
        initial_val = getattr(self.msg, self.field.name)
        self.editor.setPlainText(initial_val)
        
        # Filtra o frontmatter para renderizar na preview
        preview_text = initial_val.lstrip()
        if preview_text.startswith("---"):
            parts = preview_text.split("---", 2)
            if len(parts) >= 3:
                preview_text = parts[2]
        self.preview.setMarkdown(preview_text)
        
        # Connect change signals
        from editor.views.widget_editor_dados import _get_id
        self.editor.setProperty("protobuf_field", self.field.name)
        self.editor.setProperty("protobuf_msg_id", _get_id(self.msg))
        
        self.editor.textChanged.connect(self._on_text_changed)
        
    def _on_text_changed(self):
        text = self.editor.toPlainText()
        
        # Filtra o frontmatter para renderizar na preview
        preview_text = text.lstrip()
        if preview_text.startswith("---"):
            parts = preview_text.split("---", 2)
            if len(parts) >= 3:
                preview_text = parts[2]
                
        self.preview.setMarkdown(preview_text)
        
        val_antigo = getattr(self.msg, self.field.name)
        if val_antigo != text:
            self.controller.alterar_primitivo(self.msg, self.field.name, val_antigo, text)
            self.formulario._mark_dirty()
            self.formulario._notify_tree_changed()
        
        val_antigo = getattr(self.msg, self.field.name)
        if val_antigo != text:
            self.controller.alterar_primitivo(self.msg, self.field.name, val_antigo, text)
            
            # Mark dirty
            form = self.parent()
            while form:
                if hasattr(form, "_mark_dirty"):
                    form._mark_dirty()
                    form._notify_tree_changed()
                    break
                form = form.parent() if hasattr(form, "parent") and callable(form.parent) else None

def _extrair_titulo_heuristico(msg):
    for field_name in ["nome", "titulo", "id"]:
        try:
            if msg.HasField(field_name):
                return str(getattr(msg, field_name))
        except ValueError:
            pass
    return None

class WidgetColapsavel(QWidget):
    def __init__(self, msg, title_prefix, lazy_loader_cb, parent=None):
        super().__init__(parent)
        self.msg = msg
        self.title_prefix = title_prefix
        self.lazy_loader_cb = lazy_loader_cb
        self._was_loaded = False
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        self.header_widget = QWidget(self)
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(6)
        
        from PyQt6.QtWidgets import QToolButton
        self.toggle_button = QToolButton(self)
        self.toggle_button.setStyleSheet("QToolButton { border: none; font-weight: bold; text-align: left; background-color: #e6e6e6; padding: 6px; }")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.update_title()
        self.toggle_button.setSizePolicy(self.toggle_button.sizePolicy().Policy.Expanding, self.toggle_button.sizePolicy().Policy.Fixed)
        
        self.header_layout.addWidget(self.toggle_button)
        
        self.content_area = QFrame(self)
        self.content_area.setObjectName("SubMessageFrame")
        self.content_area.setStyleSheet("""
            QFrame#SubMessageFrame {
                border: 1.5px solid #2b579a;
                border-top: none;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #fdfdfd;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(6)
        
        self.content_area.setVisible(False)
        
        self._layout.addWidget(self.header_widget)
        self._layout.addWidget(self.content_area)
        
        self.toggle_button.toggled.connect(self._on_toggled)
        
    def add_header_widget(self, widget):
        self.header_layout.addWidget(widget)
        
    def update_title(self):
        heuristico = _extrair_titulo_heuristico(self.msg)
        texto = f"▶ {self.title_prefix}"
        if heuristico:
            texto += f" - {heuristico}"
        if self.toggle_button.isChecked():
            texto = texto.replace("▶", "▼")
        self.toggle_button.setText(texto)

    def _on_toggled(self, checked):
        if checked:
            if not self._was_loaded:
                self.lazy_loader_cb(self.msg, self.content_layout)
                self._was_loaded = True
            self.content_area.setVisible(True)
        else:
            self.content_area.setVisible(False)
        self.update_title()


class ContainerRepeatedWidget(QWidget):
    def __init__(self, msg, field, formulario, parent=None):
        self.model = formulario.model
        self.controller = formulario.controller
        self.formulario = formulario
        super().__init__(parent)
        self.msg = msg
        self.field = field
        self.formulario = formulario
        self.repeated_container = getattr(msg, field.name)

        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(0, 0, 0, 0)
        self.layout_principal.setSpacing(6)

        # Cabeçalho
        self.header_layout = QHBoxLayout()
        label_text = ProtobufWidgetFactory.get_label(field)
        self.label_widget = QLabel(label_text)
        self.label_widget.setStyleSheet("font-weight: bold; color: #2b579a; font-size: 10pt;")
        self.header_layout.addWidget(self.label_widget)

        tooltip = ProtobufWidgetFactory.get_tooltip(field)
        if tooltip:
            self.desc_label = QLabel(tooltip)
            self.desc_label.setStyleSheet("color: #666666; font-size: 8pt; font-style: italic;")
            self.desc_label.setWordWrap(True)
        else:
            self.desc_label = None

        self.header_layout.addStretch()

        self.btn_add = QPushButton("Adicionar Item")
        self.btn_add.setStyleSheet("background-color: #2b579a; color: white; border-radius: 4px; padding: 4px 8px;")
        self.btn_add.clicked.connect(self._on_add_clicked)
        self.header_layout.addWidget(self.btn_add)

        self.layout_principal.addLayout(self.header_layout)
        if self.desc_label:
            self.layout_principal.addWidget(self.desc_label)

        self.items_layout = QVBoxLayout()
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(10)
        self.layout_principal.addLayout(self.items_layout)

        # Renderiza os itens iniciais
        for i in range(len(self.repeated_container)):
            self._renderizar_item_no_indice(i)

        # Conecta aos sinais estruturais do historico
        if self.model:
            self.model.repeated_adicionado.connect(self._on_item_adicionado)
            self.model.repeated_removido.connect(self._on_item_removido)

    def _on_add_clicked(self):
        f = self.field
        idx = len(self.repeated_container)
        
        # Interceptação de "Mapas"
        if f.name == "mapas":
            from pathlib import Path
            from editor.core.storage import GerenciadorCaminhos
            
            db_dir = getattr(self.formulario.model, '_caminho_db_atual', None)
            if not db_dir:
                db_dir = GerenciadorCaminhos().obter_caminho_base_repo()
                
            nome_setor = getattr(self.msg, "nome", "setor_desconhecido")
            import re
            import unicodedata
            nome_setor_fmt = unicodedata.normalize('NFKD', nome_setor).encode('ASCII', 'ignore').decode('utf-8')
            nome_setor_fmt = re.sub(r'[^a-zA-Z0-9]+', '_', nome_setor_fmt).strip('_').lower()
            
            nome_sugerido = f"setor_{nome_setor_fmt}_p{idx}.webp"
            
            from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa
            from scripts.comprimir_imagens import comprimir_imagem_para_bytes
            from google.protobuf.message_factory import GetMessageClass
            
            dialog = DialogoAdicionarMapa(nome_sugerido, db_dir, self)
            if dialog.exec() == DialogoAdicionarMapa.DialogCode.Accepted:
                caminho_img = dialog.caminho_imagem_selecionada
                with open(caminho_img, "rb") as arquivo_img:
                    raw_bytes = arquivo_img.read()
                
                # Compressao em memoria (max_area = 4194304)
                img_bytes, final_w, final_h = comprimir_imagem_para_bytes(raw_bytes, quality=85, max_area=4194304)
                
                novo_mapa = GetMessageClass(f.message_type)()
                novo_mapa.caminho_imagem_mapa = dialog.obter_caminho_final_relativo()
                novo_mapa.largura_mapa = final_w
                novo_mapa.altura_mapa = final_h
                
                self.controller.adicionar_mapa_com_arquivo(
                    msg=self.msg,
                    campo_nome=f.name,
                    index=idx,
                    valor=novo_mapa,
                    caminho_absoluto=dialog.obter_caminho_final_absoluto(),
                    img_bytes=img_bytes
                )
                self.formulario._mark_dirty()
                self.formulario._notify_tree_changed()
            return
            
        if f.type == FieldDescriptor.TYPE_MESSAGE:
            msg_class = GetMessageClass(f.message_type)
            val = msg_class()
            self.formulario.inicializar_oneofs(val)
        else:
            if f.type == FieldDescriptor.TYPE_BOOL:
                val = False
            elif f.type in (FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_INT64,
                            FieldDescriptor.TYPE_UINT32, FieldDescriptor.TYPE_UINT64,
                            FieldDescriptor.TYPE_SINT32, FieldDescriptor.TYPE_SINT64):
                val = 0
            elif f.type in (FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE):
                val = 0.0
            else:
                val = ""

        self.controller.adicionar_repeated(self.msg, f.name, idx, val)
        self.formulario._mark_dirty()
        self.formulario._notify_tree_changed()

    def _renderizar_item_no_indice(self, idx):
        item_widget = QWidget()
        item_widget.setProperty("repeated_index", idx)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)

        btn_remove = QPushButton("Remover")
        btn_remove.setStyleSheet("background-color: #d9534f; color: white; border-radius: 4px; padding: 4px 8px;")

        def on_remove_item():
            current_idx = item_widget.property("repeated_index")
            if current_idx is not None:
                self.controller.remover_repeated(self.msg, self.field.name, current_idx, getattr(self.msg, self.field.name)[current_idx])
                self.formulario._mark_dirty()
                self.formulario._notify_tree_changed()

        btn_remove.clicked.connect(on_remove_item)

        if self.field.type == FieldDescriptor.TYPE_MESSAGE:
            item_msg = self.repeated_container[idx]
            
            def lazy_loader(msg, layout):
                self.formulario._render_message_fields(msg, layout, extra_path=f"expando:{self.field.name}/item:{idx}")
                
            prefix = f"Item {idx}"
            if hasattr(self.field, "name"):
                prefix = f"{self.field.name.replace('_', ' ').capitalize()} [{idx}]"
            
            colapsavel = WidgetColapsavel(item_msg, prefix, lazy_loader, parent=self)
            colapsavel.add_header_widget(btn_remove)
            
            if not hasattr(self, "_widgets_colapsaveis"):
                self._widgets_colapsaveis = []
            self._widgets_colapsaveis.append((item_msg, colapsavel))
            
            item_layout.addWidget(colapsavel)
        else:
            widget = ProtobufWidgetFactory.create_widget(self.field)
            widget.setProperty("protobuf_field", f"{self.field.name}[{idx}]")
            widget.setProperty("protobuf_msg_id", _get_id(self.msg))
            val = self.repeated_container[idx]

            if isinstance(widget, QLineEdit):
                widget.installEventFilter(GlobalUndoRedoFilter(widget))
                widget.setText(val)
                def make_on_item_changed(w=widget):
                    def on_item_changed():
                        current_idx = item_widget.property("repeated_index")
                        if current_idx is not None:
                            val_antigo = self.repeated_container[current_idx]
                            val_novo = w.text()
                            if val_antigo != val_novo:
                                self.controller.alterar_repeated_item(self.msg, self.field.name, current_idx, val_antigo, val_novo)
                                self.formulario._mark_dirty()
                                self.formulario._notify_tree_changed()
                    return on_item_changed
                widget.textChanged.connect(make_on_item_changed())

            elif isinstance(widget, QSpinBox):
                widget.setValue(val)
                def make_on_item_changed(w=widget):
                    def on_item_changed(new_val):
                        current_idx = item_widget.property("repeated_index")
                        if current_idx is not None:
                            val_antigo = self.repeated_container[current_idx]
                            if val_antigo != new_val:
                                self.controller.alterar_repeated_item(self.msg, self.field.name, current_idx, val_antigo, new_val)
                                self.formulario._mark_dirty()
                                self.formulario._notify_tree_changed()
                    return on_item_changed
                widget.valueChanged.connect(make_on_item_changed())

            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(val)
                def make_on_item_changed(w=widget):
                    def on_item_changed(new_val):
                        current_idx = item_widget.property("repeated_index")
                        if current_idx is not None:
                            val_antigo = self.repeated_container[current_idx]
                            if val_antigo != new_val:
                                self.controller.alterar_repeated_item(self.msg, self.field.name, current_idx, val_antigo, new_val)
                                self.formulario._mark_dirty()
                                self.formulario._notify_tree_changed()
                    return on_item_changed
                widget.valueChanged.connect(make_on_item_changed())

            elif isinstance(widget, QCheckBox):
                widget.setChecked(val)
                def make_on_item_changed(w=widget):
                    def on_item_changed(checked):
                        current_idx = item_widget.property("repeated_index")
                        if current_idx is not None:
                            val_antigo = self.repeated_container[current_idx]
                            if val_antigo != checked:
                                self.controller.alterar_repeated_item(self.msg, self.field.name, current_idx, val_antigo, checked)
                                self.formulario._mark_dirty()
                                self.formulario._notify_tree_changed()
                    return on_item_changed
                widget.toggled.connect(make_on_item_changed())

            elif isinstance(widget, QComboBox):
                idx_val = widget.findData(val)
                if idx_val >= 0:
                    widget.setCurrentIndex(idx_val)
                def make_on_item_changed(w=widget):
                    def on_item_changed():
                        new_val = w.currentData()
                        if new_val is not None:
                            current_idx = item_widget.property("repeated_index")
                            if current_idx is not None:
                                val_antigo = self.repeated_container[current_idx]
                                if val_antigo != new_val:
                                    self.controller.alterar_repeated_item(self.msg, self.field.name, current_idx, val_antigo, new_val)
                                    self.formulario._mark_dirty()
                                    self.formulario._notify_tree_changed()
                    return on_item_changed
                widget.currentIndexChanged.connect(make_on_item_changed())

            item_layout.addWidget(widget)
            item_layout.addWidget(btn_remove)

        self.items_layout.insertWidget(idx, item_widget)

    def _on_item_adicionado(self, msg, campo, idx):
        if _get_id(msg) == _get_id(self.msg) and campo == self.field.name:
            # 1. Corrige os índices dos widgets existentes que vêm depois do novo índice
            for i in range(self.items_layout.count()):
                w = self.items_layout.itemAt(i).widget()
                if w:
                    cur_idx = w.property("repeated_index")
                    if cur_idx is not None and cur_idx >= idx:
                        w.setProperty("repeated_index", cur_idx + 1)
                        # Atualiza a propriedade protobuf_field se for primitivo
                        for child in w.findChildren(QWidget):
                            p_field = child.property("protobuf_field")
                            if p_field and p_field.startswith(f"{self.field.name}["):
                                child.setProperty("protobuf_field", f"{self.field.name}[{cur_idx + 1}]")

            # 2. Insere visualmente o novo item no índice
            self._renderizar_item_no_indice(idx)

    def _on_item_removido(self, msg, campo, idx):
        if _get_id(msg) == _get_id(self.msg) and campo == self.field.name:
            # 1. Encontra e deleta o widget
            widget_alvo = None
            for i in range(self.items_layout.count()):
                w = self.items_layout.itemAt(i).widget()
                if w and w.property("repeated_index") == idx:
                    widget_alvo = w
                    break

            if widget_alvo:
                self.items_layout.removeWidget(widget_alvo)
                widget_alvo.hide()  # Impede flashing no Windows
                widget_alvo.deleteLater()
                
            # 2. Corrige os índices dos widgets existentes que vinham depois do índice removido
            for i in range(self.items_layout.count()):
                w = self.items_layout.itemAt(i).widget()
                if w:
                    cur_idx = w.property("repeated_index")
                    if cur_idx is not None and cur_idx > idx:
                        w.setProperty("repeated_index", cur_idx - 1)
                        # Atualiza a propriedade protobuf_field se for primitivo
                        for child in w.findChildren(QWidget):
                            p_field = child.property("protobuf_field")
                            if p_field and p_field.startswith(f"{self.field.name}["):
                                child.setProperty("protobuf_field", f"{self.field.name}[{cur_idx - 1}]")

    def _on_item_movido(self, msg, campo, index_from, index_to):
        if _get_id(msg) == _get_id(self.msg) and campo == self.field.name:
            # 1. Encontra e remove o widget da origem sem deletar
            widget_alvo = None
            for i in range(self.items_layout.count()):
                w = self.items_layout.itemAt(i).widget()
                if w and w.property("repeated_index") == index_from:
                    widget_alvo = w
                    break
                    
            if widget_alvo:
                # Retira do layout
                self.items_layout.removeWidget(widget_alvo)
                
                # 2. Insere na nova posicao baseada nos index fisicos
                self.items_layout.insertWidget(index_to, widget_alvo)
                
                # 3. Corrige repetidos index para todos para garantir que fique consistente
                for i in range(self.items_layout.count()):
                    w = self.items_layout.itemAt(i).widget()
                    if w:
                        w.setProperty("repeated_index", i)
                        for child in w.findChildren(QWidget):
                            p_field = child.property("protobuf_field")
                            if p_field and p_field.startswith(f"{self.field.name}["):
                                child.setProperty("protobuf_field", f"{self.field.name}[{i}]")

class WidgetFormularioPadrao(QStackedWidget):
    def _on_campo_alterado(self, msg_id, campo, novo_valor):
        if campo in ["nome", "titulo", "id"]:
            for colapsavel in self.findChildren(WidgetColapsavel):
                if id(colapsavel.msg) == msg_id:
                    colapsavel.update_title()

        for widget in self.findChildren(QWidget):
            w_field = widget.property("protobuf_field")
            w_msg_id = widget.property("protobuf_msg_id")

            if w_field == campo and w_msg_id == msg_id:
                widget.blockSignals(True)
                try:
                    if isinstance(widget, QLineEdit):
                        widget.installEventFilter(GlobalUndoRedoFilter(widget))
                        if widget.text() != str(novo_valor):
                            old_text = widget.text()
                            new_text = str(novo_valor)
                            old_cursor = widget.cursorPosition()
                            
                            diff_idx = 0
                            min_len = min(len(old_text), len(new_text))
                            while diff_idx < min_len and old_text[diff_idx] == new_text[diff_idx]:
                                diff_idx += 1
                            
                            if old_cursor < diff_idx:
                                new_cursor = old_cursor
                            else:
                                new_cursor = old_cursor + (len(new_text) - len(old_text))
                            
                            widget.setText(new_text)
                            widget.setCursorPosition(max(0, min(new_cursor, len(new_text))))
                    elif isinstance(widget, QTextEdit):
                        widget.installEventFilter(GlobalUndoRedoFilter(widget))
                        if widget.toPlainText() != str(novo_valor):
                            old_text = widget.toPlainText()
                            new_text = str(novo_valor)
                            old_cursor = widget.textCursor().position()
                            
                            diff_idx = 0
                            min_len = min(len(old_text), len(new_text))
                            while diff_idx < min_len and old_text[diff_idx] == new_text[diff_idx]:
                                diff_idx += 1
                            
                            if old_cursor < diff_idx:
                                new_cursor_pos = old_cursor
                            else:
                                new_cursor_pos = max(0, min(old_cursor + len(new_text) - len(old_text), len(new_text)))
                                
                            widget.setPlainText(new_text)
                            cursor = widget.textCursor()
                            cursor.setPosition(new_cursor_pos)
                            widget.setTextCursor(cursor)
                    elif isinstance(widget, QSpinBox):
                        if widget.value() != int(novo_valor):
                            widget.setValue(int(novo_valor))
                    elif isinstance(widget, QDoubleSpinBox):
                        if widget.value() != float(novo_valor):
                            widget.setValue(float(novo_valor))
                    elif isinstance(widget, QCheckBox):
                        if widget.isChecked() != bool(novo_valor):
                            widget.setChecked(bool(novo_valor))
                    elif isinstance(widget, QComboBox):
                        idx = widget.findData(novo_valor)
                        if idx >= 0 and widget.currentIndex() != idx:
                            widget.setCurrentIndex(idx)
                    elif isinstance(widget, WidgetEditorMarkdown):
                        widget.set_conteudo(novo_valor)
                finally:
                    widget.blockSignals(False)
                break

    def _on_estrutura_campo_alterada(self, msg_id, campo_nome):
        key = (msg_id, campo_nome)
        if key in self.field_containers:
            layout, container, desc, msg = self.field_containers[key]
            if hasattr(desc, 'fields'):  # OneofDescriptor
                self._render_oneof_inner(msg, desc, layout, container)
            else:
                self._render_field_inner(msg, desc, layout, container)

    def __init__(self, model, controller, parent=None):
        super().__init__(parent)
        self.model = model
        self.controller = controller
        self.cached_forms = {}
        self.current_node = None
        self.layout = None
        self.atualizador_ui = AtualizadorUI()
        self.field_containers = {}
        
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.addWidget(QLabel("Selecione um item na árvore para editá-lo."))
        empty_layout.addStretch()
        self.addWidget(self.empty_widget)
        self.setCurrentWidget(self.empty_widget)

    def inicializar_oneofs(self, msg):
        if not msg:
            return

        # Para mensagens ONEOF_CONTEUDO: sempre inicializa 'conteudo' em memoria, sem dialog.
        msg_options = msg.DESCRIPTOR.GetOptions()
        if msg_options.HasExtension(croqui_pb2.mensagem_formato_na_ui):
            formato_msg = msg_options.Extensions[croqui_pb2.mensagem_formato_na_ui]
            if formato_msg == croqui_pb2.MensagemFormatoUi.ONEOF_CONTEUDO:
                conteudo_field = msg.DESCRIPTOR.fields_by_name.get("conteudo")
                if conteudo_field:
                    if conteudo_field.type == FieldDescriptor.TYPE_MESSAGE:
                        # CopyFrom(instancia vazia) ativa o campo no oneof sem alterar dados
                        conteudo_sub = getattr(msg, "conteudo")
                        conteudo_sub.CopyFrom(type(conteudo_sub)())
                        self.inicializar_oneofs(conteudo_sub)
                    else:
                        # campo string (ex: ArquivoMarkdown.conteudo)
                        setattr(msg, "conteudo", "")
                return  # ONEOF_CONTEUDO tratado; nao usa dialog

        for oneof in msg.DESCRIPTOR.oneofs:
            active_field = msg.WhichOneof(oneof.name)
            if active_field:
                val = getattr(msg, active_field)
                if val is not None and hasattr(val, "DESCRIPTOR"):
                    self.inicializar_oneofs(val)
                continue

            # Procura por campo default
            default_field = None
            for f in oneof.fields:
                options = f.GetOptions()
                if options.HasExtension(croqui_pb2.oneof_default) and options.Extensions[croqui_pb2.oneof_default]:
                    default_field = f
                    break
            
            if default_field:
                if default_field.type == FieldDescriptor.TYPE_MESSAGE:
                    sub = getattr(msg, default_field.name)
                    self.inicializar_oneofs(sub)
                else:
                    setattr(msg, default_field.name, default_field.default_value)
            else:
                # Sem padrão, mostra diálogo para escolher
                opcoes = []
                mapa_opcoes = {}
                for f in oneof.fields:
                    label = ProtobufWidgetFactory.get_label(f)
                    opcoes.append(label)
                    mapa_opcoes[label] = f
                
                if opcoes:
                    item_escolhido, ok = QInputDialog.getItem(
                        self,
                        "Escolher Opção",
                        f"Escolha o tipo para {oneof.name.replace('_', ' ').capitalize()}:",
                        opcoes,
                        0,
                        False
                    )
                    if ok and item_escolhido:
                        f = mapa_opcoes[item_escolhido]
                        if f.type == FieldDescriptor.TYPE_MESSAGE:
                            sub = getattr(msg, f.name)
                            self.inicializar_oneofs(sub)
                        else:
                            setattr(msg, f.name, f.default_value)


    def load_node(self, node):
        if self.currentWidget() and self.currentWidget() != self.empty_widget:
            self.atualizador_ui.salvar_estado_foco(self.currentWidget())
            
        self.current_node = node
        
        if not node or not node.message:
            self.setCurrentWidget(self.empty_widget)
            return

        msg_id = _get_id(node.message)
        if msg_id in self.cached_forms:
            self.setCurrentWidget(self.cached_forms[msg_id])
            self.atualizador_ui.restaurar_estado_foco(self.currentWidget())
            return
            
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        self.layout = QVBoxLayout(container)
        scroll_area.setWidget(container)
        
        self.addWidget(scroll_area)
        self.cached_forms[msg_id] = scroll_area
        self.setCurrentWidget(scroll_area)
            
        # Renderiza e exibe o campo do nome do arquivo (caminho_novo) da extensão do Shadow State
        msg_name = node.message.DESCRIPTOR.name
        if msg_name in ("Setor", "Grupo", "ArquivoMarkdown"):
            self._render_filename_field(node.message, msg_name, node)
            
            
        # Renderiza recursivamente os campos da mensagem ou o campo ativo de um oneof wrapper de forma direta
        options = node.message.DESCRIPTOR.GetOptions()
        is_oneof = False
        is_oneof_conteudo = False
        if options.HasExtension(croqui_pb2.mensagem_formato_na_ui):
            formato_msg = options.Extensions[croqui_pb2.mensagem_formato_na_ui]
            is_oneof = formato_msg == croqui_pb2.MensagemFormatoUi.ONEOF
            is_oneof_conteudo = formato_msg == croqui_pb2.MensagemFormatoUi.ONEOF_CONTEUDO
            
        if is_oneof:
            active_field = None
            for oneof in node.message.DESCRIPTOR.oneofs:
                active_field_name = node.message.WhichOneof(oneof.name)
                if active_field_name:
                    active_field = node.message.DESCRIPTOR.fields_by_name[active_field_name]
                    break
                    
            if active_field:
                if active_field.type == FieldDescriptor.TYPE_MESSAGE:
                    sub_msg = getattr(node.message, active_field.name)
                    self._render_message_fields(sub_msg, self.layout)
                else:
                    opts = active_field.GetOptions()
                    is_markdown = (
                        opts.HasExtension(croqui_pb2.formato_na_ui)
                        and opts.Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.MARKDOWN
                    )
                    if is_markdown:
                        widget = WidgetEditorMarkdown(node.message, active_field, self, parent=self)
                        self.layout.addWidget(widget)
                    else:
                        widget = ProtobufWidgetFactory.create_widget(active_field)
                        self._setup_primitive_widget(widget, node.message, active_field)
                        self.layout.addWidget(widget)
            else:
                self.layout.addWidget(QLabel("Nenhum campo selecionado no oneof."))
        elif is_oneof_conteudo:
            # ONEOF_CONTEUDO: renderiza sempre o campo 'conteudo' diretamente (sem combo de selecao)
            conteudo_field = node.message.DESCRIPTOR.fields_by_name.get("conteudo")
            if conteudo_field:
                if conteudo_field.type == FieldDescriptor.TYPE_STRING:
                    opts = conteudo_field.GetOptions()
                    is_markdown = (
                        opts.HasExtension(croqui_pb2.formato_na_ui)
                        and opts.Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.MARKDOWN
                    )
                    if is_markdown:
                        widget = WidgetEditorMarkdown(node.message, conteudo_field, self, parent=self)
                        self.layout.addWidget(widget)
                    else:
                        widget = ProtobufWidgetFactory.create_widget(conteudo_field)
                        self._setup_primitive_widget(widget, node.message, conteudo_field)
                        self.layout.addWidget(widget)
                elif conteudo_field.type == FieldDescriptor.TYPE_MESSAGE:
                    conteudo_msg = getattr(node.message, "conteudo")
                    self._render_message_fields(conteudo_msg, self.layout)
            else:
                self._render_message_fields(node.message, self.layout)
        else:
            self._render_message_fields(node.message, self.layout)
        self.layout.addStretch()
        self.atualizador_ui.restaurar_estado_foco(self)

    def _render_filename_field(self, msg, msg_name, node=None):
        from aresta_api.proto.generated import croqui_pb2
        
        # Encontra o wrapper (ArquivoSetor, ArquivoGrupo) que contém a extensão
        wrapper_msg = msg
        ext_desc = None
        
        if msg_name == "Setor" or msg_name == "Grupo":
            if node and node.parent_node and node.parent_node.parent_node:
                pico_node = node.parent_node.parent_node
                pico = pico_node.message
                if pico and hasattr(pico, "setores_ou_grupos") and node.index_in_repeated is not None:
                    sg = pico.setores_ou_grupos[node.index_in_repeated]
                    if msg_name == "Setor" and hasattr(sg, "HasField") and sg.HasField("setor"):
                        wrapper_msg = sg.setor
                        ext_desc = croqui_pb2.ArquivoSetor.ext_metadados_arquivo
                    elif msg_name == "Grupo" and hasattr(sg, "HasField") and sg.HasField("grupo"):
                        wrapper_msg = sg.grupo
                        ext_desc = croqui_pb2.ArquivoGrupo.ext_metadados_arquivo
        elif msg_name == "ArquivoMarkdown":
            ext_desc = croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo
            
        if not ext_desc or wrapper_msg == msg and msg_name in ("Setor", "Grupo"):
            # Se não achou a extensão ou o wrapper apropriado, não renderiza o campo (acontece em testes isolados)
            return
            
        row_layout = QHBoxLayout()
        label = QLabel("Nome do arquivo:")
        label.setStyleSheet("font-weight: bold; color: #555;")
        
        current_filename = wrapper_msg.Extensions[ext_desc].caminho_novo if wrapper_msg.HasExtension(ext_desc) else ""
        
        edit = QLineEdit(current_filename)
        if not current_filename:
            edit.setPlaceholderText("(nome será gerado automaticamente ao salvar)")
            
        edit.setProperty("protobuf_field", "__filename__")
        edit.setProperty("protobuf_msg_id", _get_id(wrapper_msg))
        
        def on_editing_finished():
            text = edit.text().strip()
            old_val = wrapper_msg.Extensions[ext_desc].caminho_novo if wrapper_msg.HasExtension(ext_desc) else ""
            if text != old_val:
                self.controller.alterar_metadados_caminho_novo(wrapper_msg, ext_desc, old_val, text)
            
        edit.editingFinished.connect(on_editing_finished)
        
        row_layout.addWidget(label)
        row_layout.addWidget(edit, 1)
        
        self.layout.addLayout(row_layout)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(line)
        self.layout.addSpacing(10)

    def _render_message_fields(self, msg, parent_layout, extra_path=None):
        if not msg:
            return
            
        options = msg.DESCRIPTOR.GetOptions()
        if options.HasExtension(croqui_pb2.mensagem_formato_na_ui):
            formato_msg = options.Extensions[croqui_pb2.mensagem_formato_na_ui]
            if formato_msg == croqui_pb2.MensagemFormatoUi.ONEOF_CONTEUDO:
                conteudo_field = msg.DESCRIPTOR.fields_by_name.get("conteudo")
                if conteudo_field:
                    if conteudo_field.type == FieldDescriptor.TYPE_MESSAGE:
                        conteudo_msg = getattr(msg, "conteudo")
                        self._render_message_fields(conteudo_msg, parent_layout, extra_path)
                    else:
                        self._render_field_container(msg, conteudo_field, parent_layout)
                else:
                    parent_layout.addWidget(QLabel("ERRO: Campo 'conteudo' não encontrado na mensagem ONEOF_CONTEUDO."))
                return
            elif formato_msg == croqui_pb2.MensagemFormatoUi.MAPA:
                btn_mapa = QPushButton("Abrir no Editor de Mapas")
                btn_mapa.setStyleSheet("padding: 8px; font-weight: bold; background-color: #4CAF50; color: white;")
                
                def go_to_map():
                    if self.current_node and self.controller:
                        path = "page:mapas/" + get_node_path(self.current_node)
                        if extra_path:
                            path += "/" + extra_path
                        self.controller.set_contexto(path)
                        if hasattr(self, 'model'):
                            self.model.notificar_foco_requisitado(path)
                        
                btn_mapa.clicked.connect(go_to_map)
                parent_layout.addWidget(btn_mapa)
                return
            
        # Mapeia campos contidos em oneofs para não renderizá-los duplicados
        oneofs = msg.DESCRIPTOR.oneofs
        oneof_fields = set()
        for oneof in oneofs:
            for f in oneof.fields:
                oneof_fields.add(f.name)
                
        # 1. Renderiza os oneofs primeiro
        for oneof in msg.DESCRIPTOR.oneofs:
            self._render_oneof_container(msg, oneof, parent_layout, extra_path)
            parent_layout.addSpacing(10)
            
        # 2. Renderiza os demais campos individuais
        for field in msg.DESCRIPTOR.fields:
            if field.name in oneof_fields:
                continue
            
            # Filtra campos marcados com formato_na_ui = INVISIVEL
            campo_opts = field.GetOptions()
            if campo_opts.HasExtension(croqui_pb2.formato_na_ui):
                formato_campo = campo_opts.Extensions[croqui_pb2.formato_na_ui]
                if formato_campo == croqui_pb2.CampoFormatoUi.INVISIVEL:
                    continue
                
            # Ignora sub-mensagens que são exibidas separadamente na árvore (SEPARADO, ONEOF ou ONEOF_CONTEUDO)
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                options = field.message_type.GetOptions()
                if options.HasExtension(croqui_pb2.mensagem_formato_na_ui):
                    formato = options.Extensions[croqui_pb2.mensagem_formato_na_ui]
                    if formato in (
                        croqui_pb2.MensagemFormatoUi.SEPARADO,
                        croqui_pb2.MensagemFormatoUi.ONEOF,
                        croqui_pb2.MensagemFormatoUi.ONEOF_CONTEUDO,
                    ):
                        continue
            
            if field.containing_oneof:
                continue
                
            if field.is_repeated:
                self._render_repeated_field(msg, field, parent_layout)
            else:
                self._render_field_container(msg, field, parent_layout, extra_path)
                
            parent_layout.addSpacing(10)

    def _render_oneof_container(self, msg, oneof, parent_layout, extra_path=None):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        parent_layout.addWidget(container)
        self.field_containers[(_get_id(msg), oneof.name)] = (container_layout, container, oneof, msg)
        self._render_oneof_inner(msg, oneof, container_layout, container, extra_path)

    def _render_oneof_inner(self, msg, oneof, layout, container, extra_path=None):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                layout_cleaner = QWidget()
                layout_cleaner.hide()
                layout_cleaner.setLayout(item.layout())
                layout_cleaner.deleteLater()
        
        header_layout = QHBoxLayout()
        
        # Rótulo amigável para o oneof
        oneof_label = QLabel(oneof.name.replace("_", " ").capitalize())
        oneof_label.setStyleSheet("font-weight: bold; font-size: 10pt; color: #2b579a;")
        header_layout.addWidget(oneof_label)
        
        combo = QComboBox()
        combo.addItem("Não selecionado", None)
        for f in oneof.fields:
            label = ProtobufWidgetFactory.get_label(f)
            combo.addItem(label, f.name)
            
        # Define seleção atual
        active_field_name = msg.WhichOneof(oneof.name)
        if active_field_name:
            idx = combo.findData(active_field_name)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        else:
            combo.setCurrentIndex(0)
            
        header_layout.addWidget(combo)
        layout.addLayout(header_layout)
        
        # Conecta sinal de mudança do combobox do oneof
        def make_on_oneof_changed(o=oneof, c=combo, m=msg):
            def on_oneof_changed():
                selected_field_name = c.currentData()
                current_active = m.WhichOneof(o.name)
                if selected_field_name == current_active:
                    return
                    
                nome_antigo = current_active
                valor_antigo = None
                if nome_antigo:
                    f_antigo = m.DESCRIPTOR.fields_by_name[nome_antigo]
                    valor_antigo = getattr(m, nome_antigo)
                
                nome_novo = selected_field_name
                valor_novo = None
                if nome_novo:
                    f_novo = m.DESCRIPTOR.fields_by_name[nome_novo]
                    if f_novo.type == FieldDescriptor.TYPE_MESSAGE:
                        msg_class = GetMessageClass(f_novo.message_type)
                        valor_novo = msg_class()
                        self.inicializar_oneofs(valor_novo)
                    else:
                        valor_novo = f_novo.default_value

                self.controller.alterar_oneof(m, o.name, nome_antigo, valor_antigo, nome_novo, valor_novo)
                
                self._mark_dirty()
                self._notify_tree_changed()
                self._render_oneof_inner(m, o, layout, container, extra_path)
            return on_oneof_changed
            
        combo.currentIndexChanged.connect(make_on_oneof_changed())
        
        # Renderiza inline o campo ativo do oneof
        if active_field_name:
            f = msg.DESCRIPTOR.fields_by_name[active_field_name]
            if f.type == FieldDescriptor.TYPE_MESSAGE:
                sub_msg = getattr(msg, active_field_name)
                
                # Borda externa delimitando a sub-mensagem inline
                frame = QFrame()
                frame.setObjectName("SubMessageFrame")
                frame.setStyleSheet("""
                    QFrame#SubMessageFrame {
                        border: 1.5px solid #2b579a;
                        border-radius: 6px;
                        background-color: #fdfdfd;
                    }
                """)
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(10, 10, 10, 10)
                frame_layout.setSpacing(6)
                
                self._render_message_fields(sub_msg, frame_layout, extra_path)
                layout.addWidget(frame)
            else:
                opts = f.GetOptions()
                is_markdown = False
                if opts.HasExtension(croqui_pb2.mime_type):
                    is_markdown = opts.Extensions[croqui_pb2.mime_type] == "text/markdown"
                if opts.HasExtension(croqui_pb2.conteudo_markdown) and opts.Extensions[croqui_pb2.conteudo_markdown]:
                    is_markdown = True
                    
                if is_markdown:
                    widget = WidgetEditorMarkdown(msg, f, self, parent=self)
                    layout.addWidget(widget)
                else:
                    widget = ProtobufWidgetFactory.create_widget(f)
                    self._setup_primitive_widget(widget, msg, f)
                    layout.addWidget(widget)

    def _render_field_container(self, msg, field, parent_layout, extra_path=None):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        parent_layout.addWidget(container)
        self.field_containers[(_get_id(msg), field.name)] = (container_layout, container, field, msg)
        self._render_field_inner(msg, field, container_layout, container, extra_path)

    def _render_field_inner(self, msg, field, layout, container, extra_path=None):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()  # Impede que o widget pisque como uma janela top-level no Windows ao perder o pai
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                layout_cleaner = QWidget()
                layout_cleaner.hide()
                layout_cleaner.setLayout(item.layout())
                layout_cleaner.deleteLater()

        # Filtra campos marcados como INVISIVEL
        campo_opts = field.GetOptions()
        if campo_opts.HasExtension(croqui_pb2.formato_na_ui):
            if campo_opts.Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.INVISIVEL:
                return

        # Cria o card (QFrame) que envolve o campo
        card = QFrame()
        card.setObjectName("CardCampo")
        card.setStyleSheet("""
            QFrame#CardCampo {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #ffffff;
                padding: 4px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        
        label_text = ProtobufWidgetFactory.get_label(field)
        label_widget = QLabel(label_text)
        label_widget.setStyleSheet("font-weight: bold; color: #333333;")
        header_layout.addWidget(label_widget)
        
        tooltip = ProtobufWidgetFactory.get_tooltip(field)
        if tooltip:
            desc_label = QLabel(tooltip)
            desc_label.setStyleSheet("color: #666666; font-size: 8pt; font-style: italic;")
            desc_label.setWordWrap(True)
        else:
            desc_label = None
            
        header_layout.addStretch()
        
        has_presence = field.has_presence
        is_set = True
        if has_presence:
            try:
                is_set = msg.HasField(field.name)
            except ValueError:
                is_set = True
                
        if has_presence:
            if not is_set:
                btn_add = QPushButton("Adicionar")
                btn_add.setStyleSheet("background-color: #2b579a; color: white; border-radius: 4px; padding: 4px 8px;")
                def make_on_add(m=msg, f=field):
                    def on_add():
                        if f.type == FieldDescriptor.TYPE_MESSAGE:
                            msg_class = GetMessageClass(f.message_type)
                            val = msg_class()
                            self.inicializar_oneofs(val)
                        else:
                            val = f.default_value
                        
                        self.controller.alterar_oneof(m, None, None, None, f.name, val)
                        
                        self._mark_dirty()
                        self._notify_tree_changed()
                        self._render_field_inner(m, f, layout, container)
                    return on_add
                btn_add.clicked.connect(make_on_add())
                header_layout.addWidget(btn_add)
            else:
                btn_remove = QPushButton("Remover")
                btn_remove.setStyleSheet("background-color: #d9534f; color: white; border-radius: 4px; padding: 4px 8px;")
                def make_on_remove(m=msg, f=field):
                    def on_remove():
                        val_antigo = getattr(m, f.name)
                        
                        self.controller.alterar_oneof(m, None, f.name, val_antigo, None, None)
                        
                        self._mark_dirty()
                        self._notify_tree_changed()
                        self._render_field_inner(m, f, layout, container)
                    return on_remove
                btn_remove.clicked.connect(make_on_remove())
                header_layout.addWidget(btn_remove)
                
        card_layout.addLayout(header_layout)
        if desc_label:
            card_layout.addWidget(desc_label)
            
        layout.addWidget(card)
            
        if is_set:
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                sub_msg = getattr(msg, field.name)
                frame = QFrame()
                frame.setObjectName("SubMessageFrame")
                frame.setStyleSheet("""
                    QFrame#SubMessageFrame {
                        border: 1.5px solid #2b579a;
                        border-radius: 6px;
                        background-color: #fdfdfd;
                    }
                """)
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(10, 10, 10, 10)
                frame_layout.setSpacing(6)
                
                self._render_message_fields(sub_msg, frame_layout, extra_path)
                card_layout.addWidget(frame)
            else:
                opts = field.GetOptions()
                is_markdown = False
                if opts.HasExtension(croqui_pb2.mime_type):
                    is_markdown = opts.Extensions[croqui_pb2.mime_type] == "text/markdown"
                if opts.HasExtension(croqui_pb2.conteudo_markdown) and opts.Extensions[croqui_pb2.conteudo_markdown]:
                    is_markdown = True
                    
                if is_markdown:
                    widget = WidgetEditorMarkdown(msg, field, self, parent=self)
                    card_layout.addWidget(widget)
                else:
                    widget = ProtobufWidgetFactory.create_widget(field)
                    self._aplicar_largura_maxima(widget)
                    self._setup_primitive_widget(widget, msg, field)
                    card_layout.addWidget(widget)
                
        layout.addWidget(card)

    def _aplicar_largura_maxima(self, widget):
        """Aplica largura máxima a widgets primitivos para não ocupar a tela inteira."""
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setMaximumWidth(150)
        elif isinstance(widget, QComboBox):
            widget.setMaximumWidth(200)
        elif isinstance(widget, QCheckBox):
            widget.setMaximumWidth(200)
        elif isinstance(widget, QLineEdit):
            widget.installEventFilter(GlobalUndoRedoFilter(widget))
            widget.setMaximumWidth(450)


    def _render_repeated_field(self, msg, field, parent_layout):
        container_widget = ContainerRepeatedWidget(msg, field, self)
        parent_layout.addWidget(container_widget)

    def _setup_primitive_widget(self, widget, msg, field):
        widget.setProperty("protobuf_field", field.name)
        widget.setProperty("protobuf_msg_id", _get_id(msg))
        val = getattr(msg, field.name)
        if isinstance(widget, QLineEdit):
            widget.installEventFilter(GlobalUndoRedoFilter(widget))
            widget.setText(val)
            def make_on_changed(w=widget, m=msg, f=field):
                def on_changed():
                    val_antigo = getattr(m, f.name)
                    val_novo = w.text()
                    if val_antigo != val_novo:
                        self.controller.alterar_primitivo(m, f.name, val_antigo, val_novo)
                        self._mark_dirty()
                        self._notify_tree_changed()
                return on_changed
            widget.textChanged.connect(make_on_changed())
            
        elif isinstance(widget, QSpinBox):
            widget.setValue(val)
            def make_on_changed(w=widget, m=msg, f=field):
                def on_changed(new_val):
                    val_antigo = getattr(m, f.name)
                    if val_antigo != new_val:
                        self.controller.alterar_primitivo(m, f.name, val_antigo, new_val)
                        self._mark_dirty()
                        self._notify_tree_changed()
                return on_changed
            widget.valueChanged.connect(make_on_changed())
            
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(val)
            def make_on_changed(w=widget, m=msg, f=field):
                def on_changed(new_val):
                    val_antigo = getattr(m, f.name)
                    if val_antigo != new_val:
                        self.controller.alterar_primitivo(m, f.name, val_antigo, new_val)
                        self._mark_dirty()
                        self._notify_tree_changed()
                return on_changed
            widget.valueChanged.connect(make_on_changed())
            
        elif isinstance(widget, QCheckBox):
            widget.setChecked(val)
            def make_on_changed(w=widget, m=msg, f=field):
                def on_changed(checked):
                    val_antigo = getattr(m, f.name)
                    if val_antigo != checked:
                        self.controller.alterar_primitivo(m, f.name, val_antigo, checked)
                        self._mark_dirty()
                        self._notify_tree_changed()
                return on_changed
            widget.toggled.connect(make_on_changed())
            
        elif isinstance(widget, QComboBox):
            idx = widget.findData(val)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            def make_on_changed(w=widget, m=msg, f=field):
                def on_changed():
                    new_val = w.currentData()
                    if new_val is not None:
                        val_antigo = getattr(m, f.name)
                        if val_antigo != new_val:
                            self.controller.alterar_primitivo(m, f.name, val_antigo, new_val)
                            self._mark_dirty()
                            self._notify_tree_changed()
                return on_changed
            widget.currentIndexChanged.connect(make_on_changed())

    def _mark_dirty(self):
        window = self.window()


    def _notify_tree_changed(self):
        pass


class WidgetEditorDados(QWidget):
    def __init__(self, model, controller, caminhos_originais=None, referencias_mensagens=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.controller = controller
        self.croqui = model.obter_croqui_readonly()
        self.caminhos_originais = caminhos_originais if caminhos_originais is not None else {}
        self.referencias_mensagens = referencias_mensagens if referencias_mensagens is not None else {}
        self.layout = QHBoxLayout(self)
        
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setIndentation(12)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._exibir_menu_contexto)
        self.tree_model = ProtobufTreeViewAdapter(self.croqui)
        self.tree_view.setModel(self.tree_model)
        
        self.stacked_widget = QStackedWidget()
        
        self.form_padrao = WidgetFormularioPadrao(self.model, self.controller)
        self.form_padrao.widget_editor = self
        
        self.stacked_widget.addWidget(self.form_padrao)
        
        self.layout.addWidget(self.tree_view, 1)
        self.layout.addWidget(self.stacked_widget, 2)
        
        self.tree_view.selectionModel().selectionChanged.connect(self._on_tree_selection_changed)
        
        self.expandir_arvore_ate_alvos()
        
        self._bloquear_reconstrucao = False
        self._conectar_sinais_model()
        
        # Seleciona o nó raiz (Croqui) por padrão
        root_idx = self.tree_model.index(0, 0, QModelIndex())
        if root_idx.isValid():
            self.tree_view.selectionModel().select(root_idx, self.tree_view.selectionModel().SelectionFlag.ClearAndSelect)
            self._on_tree_selection_changed(None, None)
        
    def _on_tree_selection_changed(self, selected, deselected):
        indexes = self.tree_view.selectionModel().selectedIndexes()
        if not indexes:
            self.stacked_widget.setCurrentIndex(0)
            return
            
        index = indexes[0]
        node = index.internalPointer()
        
        # Evita recursão
        if getattr(self, "_adicionando_item", False):
            return
            
        # Trata seleção do nó virtual de adição
        if node and node.eh_no_adicao:
            if getattr(self, '_removendo_item', False):
                self.tree_view.selectionModel().clearSelection()
                return
                
            self._adicionando_item = True
            try:
                self._executar_adicionar_item(index)
            finally:
                self._adicionando_item = False
            return
        
        if not node or not node.descriptor:
            self.stacked_widget.setCurrentIndex(0)
            return
            
        self.stacked_widget.setCurrentIndex(0)
        self.form_padrao.load_node(node)
            
        if hasattr(self.controller, 'set_contexto'):
            self.controller.set_contexto("page:dados/" + get_node_path(node))

    def _on_foco_requisitado(self, path):
        from editor.core.contexto import ContextoUIPath
        ctx = ContextoUIPath(path)
        if ctx.pagina is not None and ctx.pagina != "dados":
            return
            
        path_local = ctx.caminho_local_arvore
        print(f"FOCO REQUISITADO PARA: {path_local}")
        if not path_local: return
        
        # Verifica se já estamos no nó para evitar loop/flicker
        indexes = self.tree_view.selectionModel().selectedIndexes()
        if indexes:
            current_node = indexes[0].internalPointer()
            curr_path = get_node_path(current_node) if current_node else None
            print(f"CURRENT PATH: {curr_path}")
            if curr_path == path_local:
                print("JA ESTAMOS NO NO, RETORNANDO")
                return
                
        idx = self.tree_model.find_index_for_path(path_local)
        if idx and idx.isValid():
            self.tree_view.selectionModel().select(idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            self.tree_view.scrollTo(idx)

    def _salvar_estado_expansao(self):
        """Salva o estado de expansão de todos os nós da árvore."""
        estado = {}
        def _percorrer(parent_index):
            total = self.tree_model.rowCount(parent_index)
            for r in range(total):
                idx = self.tree_model.index(r, 0, parent_index)
                node = idx.internalPointer()
                if node:
                    estado[id(node)] = self.tree_view.isExpanded(idx)
                _percorrer(idx)
        _percorrer(QModelIndex())
        return estado

    def _restaurar_estado_expansao(self, estado):
        """Restaura o estado de expansão após reconstruir a árvore."""
        def _percorrer(parent_index):
            total = self.tree_model.rowCount(parent_index)
            for r in range(total):
                idx = self.tree_model.index(r, 0, parent_index)
                node = idx.internalPointer()
                if node and id(node) in estado and estado[id(node)]:
                    self.tree_view.setExpanded(idx, True)
                _percorrer(idx)
        _percorrer(QModelIndex())

    def _reconstruir_arvore_e_expandir(self, selecionar_index_fn=None):
        """Reconstrói a árvore e opcionalmente seleciona um índice."""
        self.tree_model.inicializar_arvore()
        self.expandir_arvore_ate_alvos()
        if selecionar_index_fn:
            novo_idx = selecionar_index_fn()
            if novo_idx and novo_idx.isValid():
                self.tree_view.selectionModel().select(
                    novo_idx,
                    self.tree_view.selectionModel().SelectionFlag.ClearAndSelect
                )
                self.tree_view.scrollTo(novo_idx)
                self._on_tree_selection_changed(None, None)

    def _encontrar_parent_expando_e_campo(self, index):
        """Retorna (parent_expando_node, campo_field, repeated_container, indice_no_pai) para um índice."""
        node = index.internalPointer()
        if node is None:
            return None, None, None, None

        parent_node = node.parent_node
        if parent_node is None or not parent_node.is_expando:
            return None, None, None, None

        campo = parent_node.descriptor
        if campo is None:
            return None, None, None, None

        # Sobe mais um nível para achar a mensagem dona da coleção
        avo_node = parent_node.parent_node
        if avo_node is None or avo_node.message is None:
            return None, None, None, None

        repeated_container = getattr(avo_node.message, campo.name, None)
        if repeated_container is None:
            return None, None, None, None

        idx_no_pai = node.index_in_repeated
        return parent_node, campo, repeated_container, idx_no_pai

    def _executar_adicionar_item(self, index):
        """Adiciona novo item na coleção referenciada pelo nó expando ou nó virtual."""
        node = index.internalPointer()
        if node is None:
            return

        # O nó pode ser o expando ou um nó virtual de adição (filho do expando)
        if node.eh_no_adicao:
            expando_node = node.parent_node
        elif node.is_expando:
            expando_node = node
        else:
            return

        campo = expando_node.descriptor
        if campo is None:
            return

        avo_node = expando_node.parent_node
        if avo_node is None or avo_node.message is None:
            return

        msg_pai = avo_node.message
        repeated_container = getattr(msg_pai, campo.name, None)
        if repeated_container is None:
            return

        if campo.type == FieldDescriptor.TYPE_MESSAGE:
            msg_class = GetMessageClass(campo.message_type)
            val = msg_class()
            self.form_padrao.inicializar_oneofs(val)
        else:
            if campo.type == FieldDescriptor.TYPE_BOOL:
                val = False
            elif campo.type in (FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_INT64,
                                FieldDescriptor.TYPE_UINT32, FieldDescriptor.TYPE_UINT64,
                                FieldDescriptor.TYPE_SINT32, FieldDescriptor.TYPE_SINT64):
                val = 0
            elif campo.type in (FieldDescriptor.TYPE_FLOAT, FieldDescriptor.TYPE_DOUBLE):
                val = 0.0
            else:
                val = ""

        idx = len(repeated_container)
        self.controller.adicionar_repeated(msg_pai, campo.name, idx, val)

        janela = self.window()


        novo_indice = len(repeated_container) - 1
        
        def _localizar_novo_idx():
            croqui_idx = self.tree_model.index(0, 0)
            return self._localizar_no_por_indice(croqui_idx, expando_node.name, novo_indice)
            
        novo_model_idx = _localizar_novo_idx()
        if novo_model_idx and novo_model_idx.isValid():
            self.tree_view.selectionModel().select(
                novo_model_idx,
                self.tree_view.selectionModel().SelectionFlag.ClearAndSelect
            )
            self.tree_view.scrollTo(novo_model_idx)
            novo_node = novo_model_idx.internalPointer()
            print(f"DEBUG: novo_model_idx isValid={novo_model_idx.isValid()}, node_name={novo_node.name if novo_node else None}, eh_no_adicao={getattr(novo_node, 'eh_no_adicao', False)}")
            if novo_node:
                self.stacked_widget.setCurrentIndex(0)
                self.form_padrao.load_node(novo_node)



    def _localizar_no_por_indice(self, parent_idx, expando_name, item_index):
        """Localiza o QModelIndex de um item em um expando pelo nome do expando e índice do item."""
        total = self.tree_model.rowCount(parent_idx)
        for r in range(total):
            idx = self.tree_model.index(r, 0, parent_idx)
            node = idx.internalPointer()
            if node and node.is_expando and node.name == expando_name:
                self.tree_view.expand(idx)
                item_idx = self.tree_model.index(item_index, 0, idx)
                if item_idx.isValid():
                    return item_idx
            # Busca recursiva
            resultado = self._localizar_no_por_indice(idx, expando_name, item_index)
            if resultado and resultado.isValid():
                return resultado
        return QModelIndex()

    def _executar_remover_item(self, index):
        """Remove o item referenciado pelo índice da coleção Protobuf."""
        expando_node, campo, repeated_container, idx_no_pai = self._encontrar_parent_expando_e_campo(index)
        if repeated_container is None or idx_no_pai is None:
            return

        # Limpa a selecao e foco antes de remover para que o QTreeView nao 
        # tente mover o foco automaticamente para o proximo no (que seria '+ Adicionar')
        self.tree_view.selectionModel().clearSelection()
        from PyQt6.QtCore import QModelIndex
        self.tree_view.setCurrentIndex(QModelIndex())
        
        msg_pai = expando_node.parent_node.message
        
        self._removendo_item = True
        try:
            self.controller.remover_repeated(msg_pai, campo.name, idx_no_pai, getattr(msg_pai, campo.name)[idx_no_pai])
        finally:
            self._removendo_item = False

        janela = self.window()


        self.stacked_widget.setCurrentIndex(0)
        self.form_padrao.load_node(None)

    def _atualizar_mapeamentos_apos_troca(self, msg_a, msg_b):
        """Atualiza recursivamente os mapeamentos de caminhos originais
        e referências de mensagens quando os conteúdos de duas mensagens protobuf de mesmo tipo
        foram trocados em memória por CopyFrom.
        """
        def _trocar_recursivo(m_a, m_b):
            id_a = _get_id(m_a)
            id_b = _get_id(m_b)

            # Troca no dicionário caminhos_originais
            val_a = self.caminhos_originais.pop(id_a, None) if id_a in self.caminhos_originais else None
            val_b = self.caminhos_originais.pop(id_b, None) if id_b in self.caminhos_originais else None
            if val_a is not None:
                self.caminhos_originais[id_b] = val_a
            if val_b is not None:
                self.caminhos_originais[id_a] = val_b

            # Troca no dicionário referencias_mensagens
            tem_a_ref = id_a in self.referencias_mensagens
            tem_b_ref = id_b in self.referencias_mensagens
            if tem_a_ref:
                self.referencias_mensagens[id_a] = m_a
            if tem_b_ref:
                self.referencias_mensagens[id_b] = m_b

            # Percorre recursivamente os subcampos de tipo mensagem
            for campo in m_a.DESCRIPTOR.fields:
                if campo.type == campo.TYPE_MESSAGE:
                    try:
                        if campo.is_repeated:
                            lista_a, lista_b = getattr(m_a, campo.name), getattr(m_b, campo.name)
                            for i in range(min(len(lista_a), len(lista_b))):
                                _trocar_recursivo(lista_a[i], lista_b[i])
                        elif campo.containing_oneof:
                            if m_a.WhichOneof(campo.containing_oneof.name) == campo.name or m_b.WhichOneof(campo.containing_oneof.name) == campo.name:
                                _trocar_recursivo(getattr(m_a, campo.name), getattr(m_b, campo.name))
                        elif m_a.HasField(campo.name) or m_b.HasField(campo.name):
                            _trocar_recursivo(getattr(m_a, campo.name), getattr(m_b, campo.name))
                    except (ValueError, AttributeError):
                        pass
        _trocar_recursivo(msg_a, msg_b)

    def _executar_mover_para_cima(self, index):
        """Move o item selecionado uma posição para cima na coleção."""
        expando_node, campo, repeated_container, idx_no_pai = self._encontrar_parent_expando_e_campo(index)
        if repeated_container is None or idx_no_pai is None or idx_no_pai == 0:
            return

        msg_pai = expando_node.parent_node.message
        
        # Salva o QModelIndex do pai antes da mutação, pois o 'index' atual será invalidado (removido)
        parent_idx = index.parent()
        
        # O controller vai despachar uma Macro de remover e adicionar, e a UI responderá via eventos do model.
        self.controller.mover_repeated_para_cima(msg_pai, campo.name, idx_no_pai)

        janela = self.window()


        # Re-seleciona o item na nova posição (idx_no_pai - 1) no mesmo expando node
        novo_idx = self.tree_model.index(idx_no_pai - 1, 0, parent_idx)
        if novo_idx and novo_idx.isValid():
            self.tree_view.selectionModel().select(
                novo_idx, self.tree_view.selectionModel().SelectionFlag.ClearAndSelect
            )
            self.tree_view.scrollTo(novo_idx)
            novo_node = novo_idx.internalPointer()
            if novo_node:
                self.stacked_widget.setCurrentIndex(0)
                self.form_padrao.load_node(novo_node)

    def _executar_mover_para_baixo(self, index):
        """Move o item selecionado uma posição para baixo na coleção."""
        expando_node, campo, repeated_container, idx_no_pai = self._encontrar_parent_expando_e_campo(index)
        if repeated_container is None or idx_no_pai is None:
            return
        if idx_no_pai >= len(repeated_container) - 1:
            return

        msg_pai = expando_node.parent_node.message
        
        # Salva o QModelIndex do pai antes da mutação, pois o 'index' atual será invalidado (removido)
        parent_idx = index.parent()
        
        # O controller vai despachar uma Macro de remover e adicionar, e a UI responderá via eventos do model.
        self.controller.mover_repeated_para_baixo(msg_pai, campo.name, idx_no_pai)

        janela = self.window()


        # Re-seleciona o item na nova posição (idx_no_pai + 1) no mesmo expando node
        novo_idx = self.tree_model.index(idx_no_pai + 1, 0, parent_idx)
        if novo_idx and novo_idx.isValid():
            self.tree_view.selectionModel().select(
                novo_idx, self.tree_view.selectionModel().SelectionFlag.ClearAndSelect
            )
            self.tree_view.scrollTo(novo_idx)
            novo_node = novo_idx.internalPointer()
            if novo_node:
                self.stacked_widget.setCurrentIndex(0)
                self.form_padrao.load_node(novo_node)

    def _exibir_menu_contexto(self, posicao):
        """Exibe o menu de contexto ao clicar com botão direito na árvore."""
        index = self.tree_view.indexAt(posicao)
        if not index.isValid():
            return

        node = index.internalPointer()
        if node is None:
            return

        menu = QMenu(self)

        if node.is_expando:
            # Nó expando: acao de adicionar
            acao_add = menu.addAction("Adicionar item")
            acao_add.triggered.connect(lambda: self._executar_adicionar_item(index))
        elif not node.eh_no_adicao and node.parent_node and node.parent_node.is_expando:
            # Nó filho de um expando: ações de remover e mover
            _, campo, repeated_container, idx_no_pai = self._encontrar_parent_expando_e_campo(index)
            if repeated_container is not None:
                acao_add = menu.addAction("Adicionar item")
                acao_add.triggered.connect(lambda: self._executar_adicionar_item(
                    self.tree_model.index(index.parent().row(), 0, index.parent().parent())
                    if False else self.tree_model.index(index.row(), 0, index.parent()).parent()))
                # Simplificado: usa o índice do pai (expando) para adicionar
                acao_add2 = menu.addAction("Adicionar item")
                menu.removeAction(acao_add)
                menu.removeAction(acao_add2)
                acao_add_real = menu.addAction("Adicionar item")
                pai_expando_idx = index.parent()
                acao_add_real.triggered.connect(lambda checked=False, p=pai_expando_idx: self._executar_adicionar_item(p))

                acao_remover = menu.addAction("Excluir item")
                acao_remover.triggered.connect(lambda: self._executar_remover_item(index))

                if idx_no_pai is not None and idx_no_pai > 0:
                    acao_cima = menu.addAction("Mover para Cima")
                    acao_cima.triggered.connect(lambda: self._executar_mover_para_cima(index))

                if idx_no_pai is not None and idx_no_pai < len(repeated_container) - 1:
                    acao_baixo = menu.addAction("Mover para Baixo")
                    acao_baixo.triggered.connect(lambda: self._executar_mover_para_baixo(index))

        if not menu.isEmpty():
            menu.exec(self.tree_view.viewport().mapToGlobal(posicao))

    def expandir_arvore_ate_alvos(self):
        def _recursivo(parent_index):
            total_linhas = self.tree_model.rowCount(parent_index)
            for r in range(total_linhas):
                idx = self.tree_model.index(r, 0, parent_index)
                node = idx.internalPointer()
                if not node:
                    continue
                
                deve_expandir = False
                
                # Nós de mensagem estruturais
                if node.message is not None:
                    nome_msg = node.message.DESCRIPTOR.name
                    if nome_msg in ("Croqui", "Pico", "Grupo"):
                        deve_expandir = True
                
                # Nós expandores (coleções repetidas)
                elif node.is_expando:
                    if node.name in ("Botões", "Picos", "Setores ou grupos", "Setores"):
                        deve_expandir = True
                        
                if deve_expandir:
                    self.tree_view.expand(idx)
                    _recursivo(idx)
                    
        _recursivo(QModelIndex())

    def _conectar_sinais_model(self):
        if self.model:
            self.model.dado_alterado.connect(self._on_dado_alterado)
            self.model.repeated_adicionado.connect(self._on_repeated_adicionado)
            self.model.repeated_removido.connect(self._on_repeated_removido)
            self.model.repeated_movido.connect(self._on_repeated_movido)
            self.model.oneof_alterado.connect(self._on_oneof_alterado)
            self.model.repeated_item_alterado.connect(self._on_dado_alterado)
        self.model.foco_requisitado.connect(self._on_foco_requisitado)

    def _on_dado_alterado(self, msg, campo_nome, *args):
        novo_valor = getattr(msg, campo_nome) if hasattr(msg, campo_nome) else None
        self.form_padrao._on_campo_alterado(_get_id(msg), campo_nome, novo_valor)
        self.tree_model._on_campo_alterado(_get_id(msg), campo_nome, novo_valor)

    def _on_oneof_alterado(self, msg, campo_afetado):
        if hasattr(msg, campo_afetado):
            novo_valor = getattr(msg, campo_afetado)
            self.tree_model._on_campo_alterado(_get_id(msg), campo_afetado, novo_valor)
        self.form_padrao._on_estrutura_campo_alterada(_get_id(msg), campo_afetado)

    def _on_repeated_adicionado(self, msg, campo_nome, index):
        self.tree_model._on_item_adicionado(_get_id(msg), campo_nome, index)

    def _on_repeated_removido(self, msg, campo_nome, index):
        self.tree_model._on_item_removido(_get_id(msg), campo_nome, index)

    def _on_repeated_movido(self, msg, campo_nome, index_from, index_to):
        self.tree_model._on_item_movido(_get_id(msg), campo_nome, index_from, index_to)


    def find_node_index(self, target_node, parent_idx=QModelIndex()):
        if not target_node:
            return QModelIndex()

        if target_node == self.tree_model.croqui_node:
            return self.tree_model.index(0, 0)

        model = self.tree_model
        rows = model.rowCount(parent_idx)
        for r in range(rows):
            idx = model.index(r, 0, parent_idx)
            node = idx.internalPointer()
            if node:
                match = False
                if target_node.eh_no_adicao and node.eh_no_adicao:
                    match = (target_node.descriptor == node.descriptor)
                elif target_node.is_expando and node.is_expando:
                    match = (target_node.descriptor == node.descriptor)
                elif target_node.message is not None and node.message is not None:
                    match = (id(target_node.message) == _get_id(node.message))
                elif target_node.index_in_repeated is not None and node.index_in_repeated is not None:
                    match = (target_node.descriptor == node.descriptor and target_node.index_in_repeated == node.index_in_repeated)

                if match:
                    return idx

                child_match = self.find_node_index(target_node, idx)
                if child_match.isValid():
                    return child_match

        return QModelIndex()

