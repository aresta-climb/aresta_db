# Copyright (C) 2026 ARESTA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import glob
from PIL import Image, ImageDraw
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QVBoxLayout, QWidget,
    QPushButton, QMessageBox, QLabel,
    QSplitter, QListWidget, QListWidgetItem, QHBoxLayout,
    QGraphicsPixmapItem
)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QPen, QColor, QFont, QBrush, QCursor, QImage, QUndoCommand

class CmdMoverImagem(QUndoCommand):
    """
    Comando para desfazer/refazer modificações (movimento ou redimensionamento) na caixa de corte (CropBoxItem).
    """
    def __init__(self, caminho_imagem, estado_antigo, estado_novo, widget_editor, parent=None):
        super().__init__(parent)
        self.caminho_imagem = caminho_imagem
        self.estado_antigo = estado_antigo  # (rect, pos)
        self.estado_novo = estado_novo      # (rect, pos)
        self.widget_editor = widget_editor
        import os
        nome_arquivo = os.path.basename(caminho_imagem)
        self.contexto_ui = f"page:imagens/file:{nome_arquivo}"

    def undo(self):
        state = self.widget_editor.states.get(self.caminho_imagem)
        if state:
            state.crop_data = self.estado_antigo
            self.widget_editor.mark_modified()
            if self.widget_editor.current_file == self.caminho_imagem and self.widget_editor.crop_item:
                try:
                    rect, pos = self.estado_antigo
                    self.widget_editor.crop_item.setRect(rect)
                    self.widget_editor.crop_item.setPos(pos)
                except RuntimeError:
                    self.widget_editor.refresh_ui()

    def redo(self):
        state = self.widget_editor.states.get(self.caminho_imagem)
        if state:
            state.crop_data = self.estado_novo
            self.widget_editor.mark_modified()
            if self.widget_editor.current_file == self.caminho_imagem and self.widget_editor.crop_item:
                try:
                    rect, pos = self.estado_novo
                    self.widget_editor.crop_item.setRect(rect)
                    self.widget_editor.crop_item.setPos(pos)
                except RuntimeError:
                    self.widget_editor.refresh_ui()

class CropBoxItem(QGraphicsRectItem):
    # Enum-like flags for handles
    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8
    
    HANDLE_MARGIN = 12 # Margem de detecção dos handles
    MIN_SIZE = 20 # Tamanho mínimo do box

    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        # Estilo visual da caixa de crop
        pen = QPen(QColor(255, 50, 50)) # Vermelho
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(255, 50, 50, 40)))
        
        self.active_handle = self.NONE
        self.is_resizing = False

    def get_handle_at(self, pos):
        """Retorna o handle (quina ou lateral) sob a posição fornecida."""
        rect = self.rect()
        h = self.NONE
        
        x, y = pos.x(), pos.y()
        
        # Detecção de laterais (com margem)
        if abs(x - rect.left()) < self.HANDLE_MARGIN:
            h |= self.LEFT
        elif abs(x - rect.right()) < self.HANDLE_MARGIN:
            h |= self.RIGHT
            
        if abs(y - rect.top()) < self.HANDLE_MARGIN:
            h |= self.TOP
        elif abs(y - rect.bottom()) < self.HANDLE_MARGIN:
            h |= self.BOTTOM
            
        return h

    def set_cursor_for_handle(self, handle):
        if handle == (self.LEFT | self.TOP) or handle == (self.RIGHT | self.BOTTOM):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle == (self.RIGHT | self.TOP) or handle == (self.LEFT | self.BOTTOM):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle & (self.LEFT | self.RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif handle & (self.TOP | self.BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    def hoverMoveEvent(self, event):
        handle = self.get_handle_at(event.pos())
        self.set_cursor_for_handle(handle)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self._estado_inicial = (self.rect(), self.pos())
        self.active_handle = self.get_handle_at(event.pos())
        if self.active_handle != self.NONE:
            self.is_resizing = True
            self.resize_start_pos = event.scenePos()
            self.resize_start_rect = self.rect()
            self.resize_start_item_pos = self.pos()
            event.accept()
        else:
            self.is_resizing = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resizing:
            delta = event.scenePos() - self.resize_start_pos
            rect = QRectF(self.resize_start_rect)
            item_pos = QPointF(self.resize_start_item_pos)
            
            # Limites da cena (imagem) para clamping
            scene_rect = self.scene().sceneRect()
            
            # Coordenadas absolutas atuais do box
            abs_left = item_pos.x() + rect.left()
            abs_right = item_pos.x() + rect.right()
            abs_top = item_pos.y() + rect.top()
            abs_bottom = item_pos.y() + rect.bottom()
            
            if self.active_handle & self.LEFT:
                new_abs_left = max(scene_rect.left(), min(abs_right - self.MIN_SIZE, abs_left + delta.x()))
                rect.setLeft(rect.left() + (new_abs_left - abs_left))
            elif self.active_handle & self.RIGHT:
                new_abs_right = min(scene_rect.right(), max(abs_left + self.MIN_SIZE, abs_right + delta.x()))
                rect.setRight(rect.right() + (new_abs_right - abs_right))
                
            if self.active_handle & self.TOP:
                new_abs_top = max(scene_rect.top(), min(abs_bottom - self.MIN_SIZE, abs_top + delta.y()))
                rect.setTop(rect.top() + (new_abs_top - abs_top))
            elif self.active_handle & self.BOTTOM:
                new_abs_bottom = min(scene_rect.bottom(), max(abs_top + self.MIN_SIZE, abs_bottom + delta.y()))
                rect.setBottom(rect.bottom() + (new_abs_bottom - abs_bottom))
            
            self.setRect(rect.normalized())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Clamping da posição para manter o box dentro da imagem
            new_pos = value
            rect = self.rect()
            scene_rect = self.scene().sceneRect()
            
            # Limites calculados
            min_x = scene_rect.left() - rect.left()
            max_x = scene_rect.right() - rect.right()
            min_y = scene_rect.top() - rect.top()
            max_y = scene_rect.bottom() - rect.bottom()
            
            new_pos.setX(max(min_x, min(max_x, new_pos.x())))
            new_pos.setY(max(min_y, min(max_y, new_pos.y())))
            return new_pos
            
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        self.is_resizing = False
        super().mouseReleaseEvent(event)
        
        estado_final = (self.rect(), self.pos())
        if getattr(self, '_estado_inicial', None) and self._estado_inicial != estado_final:
            widget_editor = None
            # Tenta encontrar o WidgetEditorImagens subindo na hierarquia de pais
            p = self.scene().views()[0].parent() if self.scene() and self.scene().views() else None
            while p:
                if p.__class__.__name__ == "WidgetEditorImagens":
                    widget_editor = p
                    break
                p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None
                
            if widget_editor:
                historico = None
                window = widget_editor.window()
                if window and hasattr(window, "historico"):
                    historico = window.historico
                    
                if historico:
                    historico.executar(CmdMoverImagem(widget_editor.current_file, self._estado_inicial, estado_final, widget_editor))
                else:
                    widget_editor.mark_modified()

    def get_absolute_rect(self):
        """Retorna o retângulo final em coordenadas da cena (pixels da imagem)"""
        pos_delta = self.pos()
        rect = self.rect()
        return QRectF(
            rect.x() + pos_delta.x(),
            rect.y() + pos_delta.y(),
            rect.width(),
            rect.height()
        )

class MaskBoxItem(CropBoxItem):
    def __init__(self, rect, color, parent=None):
        super().__init__(rect, parent)
        self.fill_color = color
        # Estilo visual da máscara: cor sólida sem transparência (ou opcional)
        pen = QPen(QColor(color.red(), color.green(), color.blue()))
        pen.setWidth(1)
        self.setPen(pen)
        self.setBrush(QBrush(color))

    def get_color_tuple(self):
        """Retorna a cor em formato (R, G, B) para o Pillow"""
        return (self.fill_color.red(), self.fill_color.green(), self.fill_color.blue())

    def hoverEnterEvent(self, event):
        # Destaca as bordas ao passar o mouse (Magenta sólido para contraste)
        pen = QPen(Qt.GlobalColor.magenta)
        pen.setWidth(3)
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        # Restaura a borda original
        pen = QPen(QColor(self.fill_color.red(), self.fill_color.green(), self.fill_color.blue()))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)
        super().hoverLeaveEvent(event)

class PageState:
    def __init__(self, image, file_path):
        self.working_image = image # PIL Image
        self.file_path = file_path
        self.mask_data = [] # List of (pos, rect, color)
        self.crop_data = None # (rect, pos)
        self.is_modified = False

    def burn_masks(self):
        if not self.mask_data or not self.working_image:
            return
        draw = ImageDraw.Draw(self.working_image)
        for pos, rect, color in self.mask_data:
            # Reconstituímos o retângulo absoluto
            m_left = pos.x() + rect.left()
            m_top = pos.y() + rect.top()
            m_right = pos.x() + rect.right()
            m_bottom = pos.y() + rect.bottom()
            
            color_tuple = (color.red(), color.green(), color.blue())
            draw.rectangle(
                [m_left, m_top, m_right, m_bottom],
                fill=color_tuple, outline=color_tuple
            )
        self.mask_data = []

class ImageViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setObjectName("ImageViewer")
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(45, 45, 45)))
        self.picking_callback = None

    def mousePressEvent(self, event):
        if self.picking_callback and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.picking_callback(scene_pos)
            return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1/1.15, 1/1.15)

class WidgetEditorImagens(QWidget):
    def __init__(self, folder_path, modo_integrado=False, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.imagens_path = os.path.join(folder_path, "imagens")
        self.modo_integrado = modo_integrado
        
        self.current_file = None
        self.scene = None
        self.crop_item = None
        self.mask_items = []
        
        self.states = {} # Dict: file_path -> PageState
        
        self.setup_ui()
        self.load_images_list()

    def setup_ui(self):
        self.setObjectName("WidgetEditorImagens")
        # Estilo Premium
        self.setStyleSheet("""
            #WidgetEditorImagens {
                background-color: #f5f6f7;
            }
            #painel_esquerdo {
                background-color: #ffffff;
                border-right: 1px solid #ddd;
            }
            #painel_direito {
                background-color: #f5f6f7;
            }
            QLabel#label_titulo_sidebar {
                font-weight: bold;
                color: #444;
                font-size: 12px;
                padding: 5px;
            }
            QListWidget {
                border: 1px solid #eee;
                border-radius: 5px;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f9f9f9;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
                font-weight: bold;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                background-color: #ffffff;
                border: 1px solid #ccc;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton#btn_crop {
                background-color: #1976d2;
                color: white;
                border: none;
            }
            QPushButton#btn_crop:hover {
                background-color: #1565c0;
            }
            QPushButton#btn_save {
                background-color: #2e7d32;
                color: white;
                border: none;
            }
            QPushButton#btn_save:hover {
                background-color: #1b5e20;
            }
            QLabel#info_label {
                background-color: #333;
                color: #eee;
                padding: 8px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        
        # --- Painel Esquerdo ---
        left_widget = QWidget()
        left_widget.setObjectName("painel_esquerdo")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        lbl_titulo = QLabel("Imagens do Croqui")
        lbl_titulo.setObjectName("label_titulo_sidebar")
        left_layout.addWidget(lbl_titulo)
        
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_image_selected)
        left_layout.addWidget(self.list_widget)
        
        # --- Painel Direito ---
        right_widget = QWidget()
        right_widget.setObjectName("painel_direito")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(15, 10, 15, 15)
        
        self.info_label = QLabel("Dica: Use as bordas ou quinas da caixa vermelha para redimensionar. Arraste o centro para mover.")
        self.info_label.setObjectName("info_label")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.info_label)
        
        self.viewer = ImageViewer()
        self.viewer.setStyleSheet("border: 1px solid #ddd; border-radius: 4px;")
        right_layout.addWidget(self.viewer, 1) # Stretch 1
        
        # Controles
        controles_layout = QVBoxLayout()
        controles_layout.setSpacing(10)
        controles_layout.setContentsMargins(0, 10, 0, 0)

        # Linha 1: Máscaras
        masks_layout = QHBoxLayout()
        self.add_mask_btn = QPushButton("+ Adicionar Máscara (Conta-gotas)")
        self.add_mask_btn.clicked.connect(self.start_picking_color)
        
        self.clear_masks_btn = QPushButton("X Limpar Máscaras")
        self.clear_masks_btn.clicked.connect(self.clear_masks)
        
        masks_layout.addWidget(self.add_mask_btn)
        masks_layout.addWidget(self.clear_masks_btn)
        controles_layout.addLayout(masks_layout)

        # Linha 2: Ações
        btns_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Resetar")
        self.reset_btn.clicked.connect(self.reset_crop)
        btns_layout.addWidget(self.reset_btn)

        self.rotate_ccw_btn = QPushButton("⟲ 90°")
        self.rotate_ccw_btn.clicked.connect(lambda: self.rotate_image(-90))
        btns_layout.addWidget(self.rotate_ccw_btn)

        self.rotate_cw_btn = QPushButton("⟳ 90°")
        self.rotate_cw_btn.clicked.connect(lambda: self.rotate_image(90))
        btns_layout.addWidget(self.rotate_cw_btn)
        
        self.crop_btn = QPushButton("✂ Cortar (Preview)")
        self.crop_btn.setObjectName("btn_crop")
        self.crop_btn.clicked.connect(self.apply_crop)
        btns_layout.addWidget(self.crop_btn)

        self.save_btn = QPushButton("💾 Salvar TUDO")
        self.save_btn.setObjectName("btn_save")
        self.save_btn.clicked.connect(self.salvar_alteracoes)
        btns_layout.addWidget(self.save_btn)
        
        if self.modo_integrado:
            self.save_btn.hide()

        controles_layout.addLayout(btns_layout)
        right_layout.addLayout(controles_layout)
        
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([220, 980])
        
        main_layout.addWidget(self.splitter)

    def load_images_list(self):
        if not os.path.exists(self.imagens_path):
            return
            
        extensions = ['*.webp', '*.png', '*.jpg', '*.jpeg']
        image_files = []
        for ext in extensions:
            image_files.extend(glob.glob(os.path.join(self.imagens_path, ext)))
            
        image_files = sorted(image_files)
        if not image_files:
            return
            
        for path in image_files:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.list_widget.addItem(item)
            
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def on_image_selected(self, index):
        if index < 0:
            return
        item = self.list_widget.item(index)
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self.load_image(file_path)

    def save_current_state(self):
        """Captura o estado atual da UI e guarda no PageState correspondente."""
        if self.current_file and self.current_file in self.states:
            state = self.states[self.current_file]
            if self.crop_item:
                state.crop_data = (self.crop_item.rect(), self.crop_item.pos())
            
            state.mask_data = []
            for mask in self.mask_items:
                state.mask_data.append((mask.pos(), mask.rect(), mask.fill_color))

    def load_image(self, file_path):
        self.save_current_state()
        
        if file_path not in self.states:
            try:
                with Image.open(file_path) as img:
                    working_image = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()
                self.states[file_path] = PageState(working_image, file_path)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao carregar imagem {file_path}: {e}")
                return

        self.current_file = file_path
        self.refresh_ui()

    def mark_modified(self):
        if self.current_file in self.states:
            state = self.states[self.current_file]
            if not state.is_modified:
                state.is_modified = True
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.current_file:
                        if not item.text().startswith("* "):
                            item.setText("* " + item.text())
                        break

    def pil_to_pixmap(self, pil_image):
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def refresh_ui(self):
        if not self.current_file or self.current_file not in self.states:
            return
            
        state = self.states[self.current_file]
        pixmap = self.pil_to_pixmap(state.working_image)
        self.scene = QGraphicsScene()
        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        
        if state.crop_data:
            rect, pos = state.crop_data
            self.crop_item = CropBoxItem(rect)
            self.crop_item.setPos(pos)
        else:
            w, h = pixmap.width(), pixmap.height()
            margin_w, margin_h = w * 0.05, h * 0.05
            crop_rect = QRectF(margin_w, margin_h, w - 2*margin_w, h - 2*margin_h)
            self.crop_item = CropBoxItem(crop_rect)
            
        self.scene.addItem(self.crop_item)
        
        self.mask_items = []
        for pos, rect, color in state.mask_data:
            mask = MaskBoxItem(rect, color)
            mask.setPos(pos)
            self.scene.addItem(mask)
            self.mask_items.append(mask)
            
        self.viewer.setScene(self.scene)
        self.viewer.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def reset_crop(self):
        if not self.current_file or self.current_file not in self.states:
            return
            
        reply = QMessageBox.question(self, "Confirmar Reset", 
                                   "Deseja descartar TODAS as alterações desta imagem e voltar ao original?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with Image.open(self.current_file) as img:
                    working_image = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()
                
                state = self.states[self.current_file]
                state.working_image = working_image
                state.mask_data = []
                state.crop_data = None
                state.is_modified = False
                
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == self.current_file:
                        if item.text().startswith("* "):
                            item.setText(item.text()[2:])
                        break
                
                self.refresh_ui()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao resetar imagem: {e}")

    def start_picking_color(self):
        if not self.current_file:
            return
        self.viewer.picking_callback = self.on_color_picked
        self.viewer.setCursor(Qt.CursorShape.CrossCursor)
        self.info_label.setText("MODO CONTA-GOTAS: Clique na imagem para escolher a cor da máscara.")
        self.info_label.setStyleSheet("background-color: #0078d7; color: white; padding: 5px; font-weight: bold;")

    def on_color_picked(self, scene_pos):
        self.viewer.picking_callback = None
        self.viewer.unsetCursor()
        self.info_label.setText("Dica: Passe o mouse nas bordas ou quinas da caixa vermelha para redimensionar. Arraste o centro para mover.")
        self.info_label.setStyleSheet("background-color: #444; color: white; padding: 5px; font-weight: bold;")
        
        if self.current_file and self.current_file in self.states:
            state = self.states[self.current_file]
            img = state.working_image
            x, y = int(scene_pos.x()), int(scene_pos.y())
            if 0 <= x < img.width and 0 <= y < img.height:
                color_tuple = img.getpixel((x, y))
                if isinstance(color_tuple, int):
                    color = QColor(color_tuple, color_tuple, color_tuple)
                elif len(color_tuple) >= 3:
                    color = QColor(color_tuple[0], color_tuple[1], color_tuple[2])
                else:
                    return
                self.add_mask_at(scene_pos, color)

    def add_mask_at(self, pos, color):
        size = 100
        rect = QRectF(-size/2, -size/2, size, size)
        mask = MaskBoxItem(rect, color)
        mask.setPos(pos)
        self.scene.addItem(mask)
        self.mask_items.append(mask)
        self.mark_modified()

    def clear_masks(self):
        for item in self.mask_items:
            self.scene.removeItem(item)
        self.mask_items = []
        self.mark_modified()

    def rotate_image(self, angle):
        if not self.current_file or self.current_file not in self.states:
            return
        
        state = self.states[self.current_file]
        try:
            if angle == 90:
                state.working_image = state.working_image.transpose(Image.Transpose.ROTATE_270)
            else:
                state.working_image = state.working_image.transpose(Image.Transpose.ROTATE_90)
            
            state.crop_data = None
            self.mark_modified()
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao rotacionar: {e}")

    def apply_crop(self):
        if not self.current_file or self.current_file not in self.states:
            return
        
        state = self.states[self.current_file]
        if not self.crop_item:
            return
            
        final_rect = self.crop_item.get_absolute_rect()
        
        if final_rect.width() < 1 or final_rect.height() < 1:
            QMessageBox.warning(self, "Aviso", "Área de corte inválida.")
            return

        self.save_current_state()
        state.burn_masks()
        
        left = int(max(0, final_rect.left()))
        top = int(max(0, final_rect.top()))
        right = int(min(state.working_image.width, final_rect.right()))
        bottom = int(min(state.working_image.height, final_rect.bottom()))
        
        if right <= left or bottom <= top:
            QMessageBox.warning(self, "Erro", "Corte resultaria em imagem vazia.")
            return
            
        state.working_image = state.working_image.crop((left, top, right, bottom))
        state.crop_data = None
        self.mark_modified()
        self.refresh_ui()

    def salvar_alteracoes(self, mostrar_mensagem=True):
        self.save_current_state()
        
        modified_states = [s for s in self.states.values() if s.is_modified]
        if not modified_states:
            if mostrar_mensagem:
                QMessageBox.information(self, "Aviso", "Nenhuma imagem foi modificada.")
            return True

        if mostrar_mensagem:
            reply = QMessageBox.question(self, "Confirmar Salvar Tudo", 
                                       f"Deseja salvar as alterações em {len(modified_states)} imagem(ns)?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return False

        success_count = 0
        for state in modified_states:
            try:
                state.burn_masks()
                ext = os.path.splitext(state.file_path)[1].lower()
                if ext == '.webp':
                    state.working_image.save(state.file_path, "WEBP", quality=90)
                else:
                    state.working_image.save(state.file_path)
                state.is_modified = False
                success_count += 1
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar {os.path.basename(state.file_path)}: {e}")
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text().startswith("* "):
                item.setText(item.text()[2:])
        
        if mostrar_mensagem:
            QMessageBox.information(self, "Sucesso", f"{success_count} imagem(ns) salva(s) com sucesso!")
        return True
