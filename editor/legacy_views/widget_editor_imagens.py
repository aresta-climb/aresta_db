# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

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
from pathlib import Path
from typing import Optional, Union, Tuple, List, Dict, Any, Callable
from PIL import Image, ImageDraw
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QVBoxLayout, QWidget,
    QPushButton, QMessageBox, QLabel,
    QSplitter, QListWidget, QListWidgetItem, QHBoxLayout,
    QGraphicsPixmapItem, QFileDialog
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPen, QColor, QFont, QBrush, QCursor, QImage, QUndoCommand

class CmdMoverImagem(QUndoCommand):
    """
    Comando para desfazer/refazer modificações (movimento ou redimensionamento) na caixa de corte (CropBoxItem).
    """
    def __init__(self, caminho_imagem: str, estado_antigo: Tuple[QRectF, QPointF], estado_novo: Tuple[QRectF, QPointF], widget_editor: Any, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.caminho_imagem: str = caminho_imagem
        self.estado_antigo: Tuple[QRectF, QPointF] = estado_antigo  # (rect, pos)
        self.estado_novo: Tuple[QRectF, QPointF] = estado_novo      # (rect, pos)
        self.widget_editor: Any = widget_editor
        import os
        nome_arquivo = os.path.basename(caminho_imagem)
        self.contexto_ui: str = f"page:imagens/file:{nome_arquivo}"

    def undo(self) -> None:
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

    def redo(self) -> None:
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
    NONE: int = 0
    LEFT: int = 1
    RIGHT: int = 2
    TOP: int = 4
    BOTTOM: int = 8
    
    HANDLE_MARGIN: int = 12 # Margem de detecção dos handles
    MIN_SIZE: int = 20 # Tamanho mínimo do box

    def __init__(self, rect: QRectF, parent: Optional[Any] = None) -> None:
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
        
        self.active_handle: int = self.NONE
        self.is_resizing: bool = False
        self._estado_inicial: Optional[Tuple[QRectF, QPointF]] = None
        self.resize_start_pos: QPointF = QPointF()
        self.resize_start_rect: QRectF = QRectF()
        self.resize_start_item_pos: QPointF = QPointF()

    def get_handle_at(self, pos: QPointF) -> int:
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

    def set_cursor_for_handle(self, handle: int) -> None:
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

    def hoverMoveEvent(self, event: Any) -> None:
        handle = self.get_handle_at(event.pos())
        self.set_cursor_for_handle(handle)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: Any) -> None:
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

    def mouseMoveEvent(self, event: Any) -> None:
        if self.is_resizing:
            delta = event.scenePos() - self.resize_start_pos
            rect = QRectF(self.resize_start_rect)
            item_pos = QPointF(self.resize_start_item_pos)
            
            # Limites da cena (imagem) para clamping
            sc = self.scene()
            if not sc:
                return
            scene_rect = sc.sceneRect()
            
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

    def itemChange(self, change: Any, value: Any) -> Any:
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Clamping da posição para manter o box dentro da imagem
            new_pos = value
            rect = self.rect()
            sc = self.scene()
            if sc:
                scene_rect = sc.sceneRect()
                
                # Limites calculados
                min_x = scene_rect.left() - rect.left()
                max_x = scene_rect.right() - rect.right()
                min_y = scene_rect.top() - rect.top()
                max_y = scene_rect.bottom() - rect.bottom()
                
                new_pos.setX(max(min_x, min(max_x, new_pos.x())))
                new_pos.setY(max(min_y, min(max_y, new_pos.y())))
            return new_pos
            
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event: Any) -> None:
        self.is_resizing = False
        super().mouseReleaseEvent(event)
        
        estado_final = (self.rect(), self.pos())
        if getattr(self, '_estado_inicial', None) and self._estado_inicial != estado_final:
            widget_editor: Optional[Any] = None
            # Tenta encontrar o WidgetEditorImagens subindo na hierarquia de pais
            sc = self.scene()
            p = sc.views()[0].parent() if sc and sc.views() else None
            while p:
                if p.__class__.__name__ == "WidgetEditorImagens":
                    widget_editor = p
                    break
                p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None
                
            if widget_editor and hasattr(widget_editor, "window"):
                historico = None
                window = widget_editor.window()
                if window and hasattr(window, "historico"):
                    historico = getattr(window, "historico", None)
                    
                if historico and self._estado_inicial is not None:
                    historico.executar(CmdMoverImagem(getattr(widget_editor, "current_file", ""), self._estado_inicial, estado_final, widget_editor))
                elif hasattr(widget_editor, "mark_modified"):
                    widget_editor.mark_modified()


    def get_absolute_rect(self) -> QRectF:
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
    def __init__(self, rect: QRectF, color: QColor, parent: Optional[Any] = None) -> None:
        super().__init__(rect, parent)
        self.fill_color: QColor = color
        # Estilo visual da máscara: cor sólida sem transparência (ou opcional)
        pen = QPen(QColor(color.red(), color.green(), color.blue()))
        pen.setWidth(1)
        self.setPen(pen)
        self.setBrush(QBrush(color))

    def get_color_tuple(self) -> Tuple[int, int, int]:
        """Retorna a cor em formato (R, G, B) para o Pillow"""
        return (self.fill_color.red(), self.fill_color.green(), self.fill_color.blue())

    def hoverEnterEvent(self, event: Any) -> None:
        # Destaca as bordas ao passar o mouse (Magenta sólido para contraste)
        pen = QPen(Qt.GlobalColor.magenta)
        pen.setWidth(3)
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: Any) -> None:
        # Restaura a borda original
        pen = QPen(QColor(self.fill_color.red(), self.fill_color.green(), self.fill_color.blue()))
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)
        super().hoverLeaveEvent(event)

class PageState:
    def __init__(self, image: Image.Image, file_path: str) -> None:
        self.working_image: Image.Image = image # PIL Image
        self.file_path: str = file_path
        self.mask_data: List[Tuple[QPointF, QRectF, QColor]] = [] # List of (pos, rect, color)
        self.crop_data: Optional[Tuple[QRectF, QPointF]] = None # (rect, pos)
        self.is_modified: bool = False

    def burn_masks(self) -> None:
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
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ImageViewer")
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(45, 45, 45)))
        self.picking_callback: Optional[Callable[[QPointF], None]] = None

    def mousePressEvent(self, event: Any) -> None:
        if self.picking_callback and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.picking_callback(scene_pos)
            return
        super().mousePressEvent(event)

    def wheelEvent(self, event: Any) -> None:
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1/1.15, 1/1.15)


class WidgetEditorImagens(QWidget):
    def __init__(
        self,
        folder_path: Optional[str] = None,
        modo_integrado: bool = False,
        parent: Optional[QWidget] = None,
        model: Optional[Any] = None,
        controller: Optional[Any] = None,
        croqui_model: Optional[Any] = None,
        croqui_controller: Optional[Any] = None,
        imagens_path: Optional[Union[str, Path]] = None,
    ) -> None:
        super().__init__(parent)
        self.folder_path: Optional[str] = folder_path
        if imagens_path:
            self.imagens_path: str = str(imagens_path)
        elif folder_path:
            self.imagens_path = os.path.join(folder_path, "imagens")
        else:
            self.imagens_path = "imagens"
        self.modo_integrado: bool = modo_integrado
        self.croqui_model: Optional[Any] = croqui_model or model
        self.croqui_controller: Optional[Any] = croqui_controller or controller
        
        self.current_file: Optional[str] = None
        self.scene: Optional[QGraphicsScene] = None
        self.crop_item: Optional[CropBoxItem] = None
        self.mask_items: List[MaskBoxItem] = []
        
        self.states: Dict[str, PageState] = {} # Dict: file_path -> PageState
        
        self.setup_ui()
        if self.croqui_model and hasattr(self.croqui_model, "imagem_alterada"):
            self.croqui_model.imagem_alterada.connect(self._on_imagem_alterada)
            self._model_conectado: Optional[Any] = self.croqui_model
        else:
            self._model_conectado = None
        self.load_images_list()

    def setup_ui(self) -> None:
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

        self.btn_substituir_imagem = QPushButton("Substituir Imagem...")
        self.btn_substituir_imagem.clicked.connect(self.substituir_imagem_selecionada)
        left_layout.addWidget(self.btn_substituir_imagem)

        self.btn_abrir_no_editor_mapas = QPushButton("Abrir no Editor de Mapas")
        self.btn_abrir_no_editor_mapas.clicked.connect(self.abrir_no_editor_mapas)
        self.btn_abrir_no_editor_mapas.setEnabled(False)
        left_layout.addWidget(self.btn_abrir_no_editor_mapas)
        
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

    def load_images_list(self) -> None:
        caminho_selecionado = self.current_file
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        arquivos = set()
        if self.imagens_path and os.path.exists(self.imagens_path):
            extensions = ['*.webp', '*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff', '*.tif']
            for ext in extensions:
                arquivos.update(glob.glob(os.path.join(self.imagens_path, ext)))

        if self.croqui_model and hasattr(self.croqui_model, "obter_imagens_em_memoria"):
            for rel in self.croqui_model.obter_imagens_em_memoria().keys():
                nome = Path(rel).name
                if self.imagens_path:
                    arquivos.add(os.path.join(self.imagens_path, nome))
                else:
                    arquivos.add(rel)

        image_files = sorted(list(arquivos))
        if not image_files:
            self.current_file = None
            self.list_widget.blockSignals(False)
            self._atualizar_estado_botao_mapa()
            return

        linha_para_selecionar = 0
        for idx, path in enumerate(image_files):
            nome = os.path.basename(path)
            item = QListWidgetItem(nome)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.list_widget.addItem(item)
            if caminho_selecionado and (path == caminho_selecionado or nome == Path(caminho_selecionado).name):
                linha_para_selecionar = idx

        self.list_widget.blockSignals(False)
        if self.list_widget.count() > 0:
            if self.list_widget.currentRow() == linha_para_selecionar:
                self.on_image_selected(linha_para_selecionar)
            else:
                self.list_widget.setCurrentRow(linha_para_selecionar)

    def select_image_by_name(self, filename_or_path: str) -> None:
        """Seleciona uma imagem na lista pelo nome do arquivo."""
        if not filename_or_path:
            return
        clean_name = filename_or_path
        if clean_name.startswith("file:"):
            clean_name = clean_name[5:]
        target_name = Path(clean_name).name
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and (item.text() == target_name or item.text() == "* " + target_name):
                if self.list_widget.currentRow() != row:
                    self.list_widget.setCurrentRow(row)
                else:
                    self.on_image_selected(row)
                return

    def on_image_selected(self, index: int) -> None:
        if index < 0:
            return
        item = self.list_widget.item(index)
        if not item:
            return
        file_path = item.data(Qt.ItemDataRole.UserRole)
        self.load_image(str(file_path))

    def save_current_state(self) -> None:
        """Captura o estado atual da UI e guarda no PageState correspondente."""
        if self.current_file and self.current_file in self.states:
            state = self.states[self.current_file]
            if self.crop_item:
                state.crop_data = (self.crop_item.rect(), self.crop_item.pos())
            
            state.mask_data = []
            for mask in self.mask_items:
                state.mask_data.append((mask.pos(), mask.rect(), mask.fill_color))

    def load_image(self, file_path: str) -> None:
        self.save_current_state()
        
        rel_path = f"imagens/{Path(file_path).name}" if not str(file_path).startswith("imagens/") else file_path
        bytes_ram = None
        if self.croqui_model and hasattr(self.croqui_model, "obter_bytes_imagem"):
            bytes_ram = self.croqui_model.obter_bytes_imagem(rel_path) or self.croqui_model.obter_bytes_imagem(file_path)

        if bytes_ram and isinstance(bytes_ram, (bytes, bytearray, memoryview)):
            try:
                import io
                with Image.open(io.BytesIO(bytes_ram)) as img:
                    working_image = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()
                self.states[file_path] = PageState(working_image, file_path)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao carregar imagem {file_path}: {e}")
                return
        elif file_path not in self.states:
            try:
                with Image.open(file_path) as img:
                    working_image = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()
                self.states[file_path] = PageState(working_image, file_path)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao carregar imagem {file_path}: {e}")
                return

        self.current_file = file_path
        self.refresh_ui()
        self._atualizar_estado_botao_mapa()

    def imagem_pertence_a_mapa(self, nome_arquivo_ou_caminho: str) -> bool:
        """Verifica se a imagem especificada pertence a algum mapa no croqui_model."""
        if not self.croqui_model or not nome_arquivo_ou_caminho:
            return False
        from pathlib import Path
        nome_alvo = Path(nome_arquivo_ou_caminho).name
        
        croqui_ro = self.croqui_model.obter_croqui_readonly() if hasattr(self.croqui_model, "obter_croqui_readonly") else getattr(self.croqui_model, "croqui", None)
        if not croqui_ro:
            return False
            
        for pico in getattr(croqui_ro, "picos", []):
            if hasattr(pico, "HasField") and pico.HasField('mapas_gerais'):
                for mapa in pico.mapas_gerais.conteudo.mapas:
                    if mapa.caminho_imagem_mapa and Path(mapa.caminho_imagem_mapa).name == nome_alvo:
                        return True
            for sg in getattr(pico, "setores_ou_grupos", []):
                if getattr(sg, 'setor', None) and (not hasattr(sg, "HasField") or sg.HasField('setor')):
                    for mapa in sg.setor.conteudo.mapas:
                        if mapa.caminho_imagem_mapa and Path(mapa.caminho_imagem_mapa).name == nome_alvo:
                            return True
                if getattr(sg, 'grupo', None) and (not hasattr(sg, "HasField") or sg.HasField('grupo')):
                    for mapa in sg.grupo.conteudo.mapas:
                        if mapa.caminho_imagem_mapa and Path(mapa.caminho_imagem_mapa).name == nome_alvo:
                            return True
                    for subsetor in getattr(sg.grupo.conteudo, "setores", []):
                        for mapa in subsetor.conteudo.mapas:
                            if mapa.caminho_imagem_mapa and Path(mapa.caminho_imagem_mapa).name == nome_alvo:
                                return True
        return False

    def _atualizar_estado_botao_mapa(self) -> None:
        """Atualiza o estado habilitado/desabilitado do botão de abrir no editor de mapas."""
        if hasattr(self, "btn_abrir_no_editor_mapas"):
            pertence = self.imagem_pertence_a_mapa(self.current_file) if self.current_file else False
            self.btn_abrir_no_editor_mapas.setEnabled(pertence)
            if pertence:
                self.btn_abrir_no_editor_mapas.setToolTip("Abre esta imagem diretamente na aba do Editor de Mapas")
            else:
                self.btn_abrir_no_editor_mapas.setToolTip("Esta imagem não está vinculada a nenhum mapa no croqui")

    def abrir_no_editor_mapas(self) -> None:
        """Abre e foca a imagem selecionada no Editor de Mapas."""
        if not self.current_file:
            return
        from pathlib import Path
        nome_arquivo = Path(self.current_file).name
        contexto_uri = f"page:mapas/file:{nome_arquivo}"

        if self.croqui_controller:
            self.croqui_controller.set_contexto(contexto_uri)
        if self.croqui_model and hasattr(self.croqui_model, "notificar_foco_requisitado"):
            self.croqui_model.notificar_foco_requisitado(contexto_uri)
        elif self.croqui_model and hasattr(self.croqui_model, "foco_requisitado"):
            self.croqui_model.foco_requisitado.emit(contexto_uri)

    def substituir_imagem_selecionada(self) -> None:
        """Abre diálogo para substituir a imagem selecionada com compressão WebP em RAM."""
        if not self.current_file:
            return

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Substituir Imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif)",
        )
        if not arquivo:
            return

        from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp
        try:
            bytes_originais = Path(arquivo).read_bytes()
            bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(bytes_originais, quality=90)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao processar nova imagem: {e}")
            return

        nome_arquivo = Path(self.current_file).name
        caminho_rel = f"imagens/{nome_arquivo}"
        contexto_img = f"page:imagens/file:{nome_arquivo}"

        if self.croqui_controller:
            self.croqui_controller.set_contexto(contexto_img)
            self.croqui_controller.substituir_imagem(caminho_rel, bytes_webp, context_path=contexto_img)
        elif self.croqui_model:
            self.croqui_model.definir_imagem_memoria(caminho_rel, bytes_webp)

        self.states.pop(self.current_file, None)
        self.load_image(self.current_file)

    def _on_imagem_alterada(self, caminho_relativo: str) -> None:
        """Atualiza a lista e visualizador quando uma imagem for alterada externamente."""
        self.load_images_list()
        if self.current_file:
            nome_atual = Path(self.current_file).name
            nome_alt = Path(caminho_relativo).name
            if nome_atual == nome_alt or self.current_file == caminho_relativo:
                self.states.pop(self.current_file, None)
                self.load_image(self.current_file)

    def mark_modified(self) -> None:
        if self.current_file in self.states:
            state = self.states[self.current_file]
            if not state.is_modified:
                state.is_modified = True
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == self.current_file:
                        if not item.text().startswith("* "):
                            item.setText("* " + item.text())
                        break

    def pil_to_pixmap(self, pil_image: Image.Image) -> QPixmap:
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)

    def refresh_ui(self) -> None:
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

    def reset_crop(self) -> None:
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
                    if item and item.data(Qt.ItemDataRole.UserRole) == self.current_file:
                        if item.text().startswith("* "):
                            item.setText(item.text()[2:])
                        break
                
                self.refresh_ui()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao resetar imagem: {e}")

    def start_picking_color(self) -> None:
        if not self.current_file:
            return
        self.viewer.picking_callback = self.on_color_picked
        self.viewer.setCursor(Qt.CursorShape.CrossCursor)
        self.info_label.setText("MODO CONTA-GOTAS: Clique na imagem para escolher a cor da máscara.")
        self.info_label.setStyleSheet("background-color: #0078d7; color: white; padding: 5px; font-weight: bold;")

    def on_color_picked(self, scene_pos: QPointF) -> None:
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
                elif isinstance(color_tuple, tuple) and len(color_tuple) >= 3:
                    color = QColor(color_tuple[0], color_tuple[1], color_tuple[2])
                else:
                    return
                self.add_mask_at(scene_pos, color)

    def add_mask_at(self, pos: QPointF, color: QColor) -> None:
        if not self.scene:
            return
        size = 100
        rect = QRectF(-size/2, -size/2, size, size)
        mask = MaskBoxItem(rect, color)
        mask.setPos(pos)
        self.scene.addItem(mask)
        self.mask_items.append(mask)
        self.mark_modified()

    def clear_masks(self) -> None:
        if not self.scene:
            return
        for item in self.mask_items:
            self.scene.removeItem(item)
        self.mask_items = []
        self.mark_modified()

    def rotate_image(self, angle: int) -> None:
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

    def apply_crop(self) -> None:
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

    def salvar_alteracoes(self, mostrar_mensagem: bool = True) -> bool:
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
            if item and item.text().startswith("* "):
                item.setText(item.text()[2:])
        
        if mostrar_mensagem:
            QMessageBox.information(self, "Sucesso", f"{success_count} imagem(ns) salva(s) com sucesso!")
        return True

