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
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ImageViewer")
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(45, 45, 45)))
        self.picking_callback: Optional[Callable[[QPointF], None]] = None
        self.selecao_callback: Optional[Callable[[QRectF], None]] = None
        self._em_selecao: bool = False
        self._ponto_inicio_selecao: Optional[QPointF] = None
        self._item_retangulo_selecao: Optional[QGraphicsRectItem] = None
        self._cor_selecao: QColor = QColor(25, 118, 210)
        self._precisa_ajustar_zoom: bool = True

    def iniciar_modo_selecao(self, callback: Callable[[QRectF], None], cor_borda: QColor = QColor(25, 118, 210)) -> None:
        self.selecao_callback = callback
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._em_selecao = False
        self._ponto_inicio_selecao = None
        self._cor_selecao = cor_borda

    def cancelar_modo_selecao(self) -> None:
        self.selecao_callback = None
        self.picking_callback = None
        self._em_selecao = False
        self._ponto_inicio_selecao = None
        if self._item_retangulo_selecao and self.scene():
            self.scene().removeItem(self._item_retangulo_selecao)
        self._item_retangulo_selecao = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.unsetCursor()

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.picking_callback:
                scene_pos = self.mapToScene(event.pos())
                self.picking_callback(scene_pos)
                return
            if self.selecao_callback:
                self._em_selecao = True
                self._ponto_inicio_selecao = self.mapToScene(event.pos())
                if self._item_retangulo_selecao and self.scene():
                    self.scene().removeItem(self._item_retangulo_selecao)
                self._item_retangulo_selecao = QGraphicsRectItem()
                pen = QPen(self._cor_selecao, 2, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(self._cor_selecao.red(), self._cor_selecao.green(), self._cor_selecao.blue(), 40))
                self._item_retangulo_selecao.setPen(pen)
                self._item_retangulo_selecao.setBrush(brush)
                if self.scene():
                    self.scene().addItem(self._item_retangulo_selecao)
                self._item_retangulo_selecao.setRect(QRectF(self._ponto_inicio_selecao, self._ponto_inicio_selecao))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        if self._em_selecao and self._ponto_inicio_selecao and self._item_retangulo_selecao:
            pos_atual = self.mapToScene(event.pos())
            rect = QRectF(self._ponto_inicio_selecao, pos_atual).normalized()
            if self.scene():
                rect = rect.intersected(self.scene().sceneRect())
            self._item_retangulo_selecao.setRect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        if self._em_selecao and self._ponto_inicio_selecao and self.selecao_callback:
            self._em_selecao = False
            pos_final = self.mapToScene(event.pos())
            rect = QRectF(self._ponto_inicio_selecao, pos_final).normalized()
            if self.scene():
                rect = rect.intersected(self.scene().sceneRect())
            if self._item_retangulo_selecao and self.scene():
                self.scene().removeItem(self._item_retangulo_selecao)
            self._item_retangulo_selecao = None
            cb = self.selecao_callback
            cb(rect)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: Any) -> None:
        if event.key() == Qt.Key.Key_Escape:
            p: Optional[Any] = self.parent()
            while p:
                if hasattr(p, "cancelar_selecao"):
                    p.cancelar_selecao()
                    event.accept()
                    return
                p = p.parent() if hasattr(p, "parent") and callable(p.parent) else None
        super().keyPressEvent(event)

    def wheelEvent(self, event: Any) -> None:
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1/1.15, 1/1.15)

    def ajustar_ao_visualizador(self) -> None:
        """Ajusta a cena inteira para preencher a área visível do viewport mantendo a proporção."""
        if not self.scene() or self.scene().sceneRect().isEmpty():
            return
        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        if vp_w > 50 and vp_h > 50:
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._precisa_ajustar_zoom = False
        else:
            self._precisa_ajustar_zoom = True

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        if getattr(self, "_precisa_ajustar_zoom", True):
            self.ajustar_ao_visualizador()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if getattr(self, "_precisa_ajustar_zoom", True):
            self.ajustar_ao_visualizador()




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
        self._croqui_model: Optional[Any] = None
        self.croqui_model = croqui_model or model
        self.croqui_controller: Optional[Any] = croqui_controller or controller
        
        self.current_file: Optional[str] = None
        self.scene: Optional[QGraphicsScene] = None
        self.crop_item: Optional[CropBoxItem] = None
        self.mask_items: List[MaskBoxItem] = []
        self.modo_corte: bool = False
        self.modo_mascara: bool = False
        self.cor_mascara_atual: Optional[Tuple[int, int, int]] = None
        self._despachando_transformacao: bool = False
        
        self.states: Dict[str, PageState] = {} # Dict: file_path -> PageState
        
        self.setup_ui()
        self.load_images_list()

    @property
    def croqui_model(self) -> Optional[Any]:
        return getattr(self, "_croqui_model", None)

    @croqui_model.setter
    def croqui_model(self, model: Optional[Any]) -> None:
        antigo = getattr(self, "_croqui_model", None)
        if antigo is not model:
            if antigo is not None and hasattr(antigo, "imagem_alterada"):
                try:
                    antigo.imagem_alterada.disconnect(self._on_imagem_alterada)
                except Exception:
                    pass
            self._croqui_model = model
            if self._croqui_model and hasattr(self._croqui_model, "imagem_alterada"):
                self._croqui_model.imagem_alterada.connect(self._on_imagem_alterada)

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
        
        self.info_label = QLabel("Dica: Selecione Cortar ou Máscara abaixo para editar a imagem. Use a roda do mouse para zoom e arraste para navegar.")
        self.info_label.setObjectName("info_label")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.info_label)
        
        self.viewer = ImageViewer(self)
        self.viewer.setStyleSheet("border: 1px solid #ddd; border-radius: 4px;")
        right_layout.addWidget(self.viewer, 1) # Stretch 1
        
        # Controles
        # Controles
        controles_layout = QHBoxLayout()
        controles_layout.setSpacing(10)
        controles_layout.setContentsMargins(0, 10, 0, 0)

        self.crop_btn = QPushButton("✂ Cortar")
        self.crop_btn.setObjectName("btn_crop")
        self.crop_btn.clicked.connect(self.alternar_modo_corte)
        controles_layout.addWidget(self.crop_btn)

        self.add_mask_btn = QPushButton("🎨 Máscara")
        self.add_mask_btn.setObjectName("btn_mask")
        self.add_mask_btn.clicked.connect(self.alternar_modo_mascara)
        controles_layout.addWidget(self.add_mask_btn)

        self.rotate_ccw_btn = QPushButton("⟲ 90°")
        self.rotate_ccw_btn.clicked.connect(lambda: self.rotate_image(-90))
        controles_layout.addWidget(self.rotate_ccw_btn)

        self.rotate_cw_btn = QPushButton("⟳ 90°")
        self.rotate_cw_btn.clicked.connect(lambda: self.rotate_image(90))
        controles_layout.addWidget(self.rotate_cw_btn)

        self.save_btn = QPushButton("💾 Salvar TUDO")
        self.save_btn.setObjectName("btn_save")
        self.save_btn.clicked.connect(self.salvar_alteracoes)
        controles_layout.addWidget(self.save_btn)
        
        if self.modo_integrado:
            self.save_btn.hide()

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
                elif not self.current_file:
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
        if hasattr(self, "viewer"):
            self.viewer._precisa_ajustar_zoom = True
        self.refresh_ui()
        self._atualizar_estado_botao_mapa()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if hasattr(self, "viewer") and getattr(self.viewer, "_precisa_ajustar_zoom", True):
            self.viewer.ajustar_ao_visualizador()


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
        """Atualiza a lista e visualizador quando uma imagem for alterada externamente ou por histórico."""
        if getattr(self, "_despachando_transformacao", False):
            return

        nome_alt = Path(caminho_relativo).name
        
        # Só executa varredura de disco se for um arquivo novo não presente na lista
        esta_na_lista = False
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and Path(item.data(Qt.ItemDataRole.UserRole) or "").name == nome_alt:
                esta_na_lista = True
                break
        if not esta_na_lista:
            self.load_images_list()

        if self.current_file:
            nome_atual = Path(self.current_file).name
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
        
        self.viewer.setScene(self.scene)
        self.viewer.ajustar_ao_visualizador()

    def alternar_modo_corte(self) -> None:
        """Alterna entre ativar e desativar o modo de corte interativo."""
        if self.modo_corte:
            self.desativar_modo_corte()
        else:
            self.ativar_modo_corte()

    def ativar_modo_corte(self) -> None:
        """Ativa o modo de corte com cursor de mira e seleção por arrasto."""
        if not self.current_file:
            return
        self.cancelar_selecao()
        self.modo_corte = True
        self.crop_btn.setStyleSheet("background-color: #0d47a1; color: white; font-weight: bold;")
        self.info_label.setText("MODO CORTAR: Arraste para selecionar a área de corte. Esc para cancelar.")
        self.info_label.setStyleSheet("background-color: #1976d2; color: white; padding: 5px; font-weight: bold;")
        self.viewer.iniciar_modo_selecao(self._ao_finalizar_selecao_corte, cor_borda=QColor(25, 118, 210))

    def desativar_modo_corte(self) -> None:
        """Desativa o modo de corte e restaura o visualizador."""
        self.modo_corte = False
        self.crop_btn.setStyleSheet("")
        self.viewer.cancelar_modo_selecao()
        self.info_label.setText("Dica: Use as ferramentas acima para cortar, rotacionar ou mascarar a imagem.")
        self.info_label.setStyleSheet("background-color: #333; color: #eee; padding: 8px; border-radius: 4px; font-size: 11px;")

    def cancelar_selecao(self) -> None:
        """Cancela qualquer modo interativo ativo (corte ou máscara)."""
        if self.modo_corte:
            self.desativar_modo_corte()
        if getattr(self, "modo_mascara", False):
            self.desativar_modo_mascara()

    def _ao_finalizar_selecao_corte(self, rect: QRectF) -> None:
        """Callback executado ao soltar o mouse no visualizador durante o modo de corte."""
        x1, y1 = int(rect.left()), int(rect.top())
        x2, y2 = int(rect.right()), int(rect.bottom())
        self.executar_corte_selecao(x1, y1, x2, y2)

    def executar_corte_selecao(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Executa o corte da área delimitada e despacha a transformação via histórico."""
        largura = abs(x2 - x1)
        altura = abs(y2 - y1)
        if largura < 10 or altura < 10:
            # Ignora seleções acidentais ou muito pequenas
            self.desativar_modo_corte()
            return

        bytes_atuais = self._obter_bytes_imagem_atual()
        if not bytes_atuais:
            self.desativar_modo_corte()
            return

        try:
            from editor.core.transformacoes_imagem import cortar_imagem_bytes
            bytes_cortados = cortar_imagem_bytes(bytes_atuais, (x1, y1, x2, y2))
            self._despachar_transformacao_imagem(bytes_cortados)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao cortar imagem: {e}")
        finally:
            self.desativar_modo_corte()

    def alternar_modo_mascara(self) -> None:
        """Alterna entre ativar e desativar o modo de máscara interativo."""
        if self.modo_mascara:
            self.desativar_modo_mascara()
        else:
            self.ativar_modo_mascara()

    def ativar_modo_mascara(self) -> None:
        """Ativa o modo de máscara iniciando pelo conta-gotas para captura da cor de fundo."""
        if not self.current_file:
            return
        self.cancelar_selecao()
        self.modo_mascara = True
        self.cor_mascara_atual = None
        self.add_mask_btn.setStyleSheet("background-color: #0d47a1; color: white; font-weight: bold;")
        self.info_label.setText("MODO MÁSCARA: Passo 1 - Clique na imagem para capturar a cor (conta-gotas). Esc para cancelar.")
        self.info_label.setStyleSheet("background-color: #0078d7; color: white; padding: 5px; font-weight: bold;")
        self.viewer.picking_callback = self._ao_clicar_conta_gotas
        self.viewer.setCursor(Qt.CursorShape.CrossCursor)

    def desativar_modo_mascara(self) -> None:
        """Desativa o modo de máscara e restaura o visualizador."""
        self.modo_mascara = False
        self.cor_mascara_atual = None
        self.add_mask_btn.setStyleSheet("")
        self.viewer.picking_callback = None
        self.viewer.cancelar_modo_selecao()
        self.info_label.setText("Dica: Use as ferramentas acima para cortar, rotacionar ou mascarar a imagem.")
        self.info_label.setStyleSheet("background-color: #333; color: #eee; padding: 8px; border-radius: 4px; font-size: 11px;")

    def start_picking_color(self) -> None:
        """Método de conveniência/legado para iniciar o fluxo de máscara."""
        self.ativar_modo_mascara()

    def _ao_clicar_conta_gotas(self, scene_pos: QPointF) -> None:
        """Chamado quando o usuário clica na imagem para capturar a cor."""
        self.capturar_cor_ponto(int(scene_pos.x()), int(scene_pos.y()))

    def capturar_cor_ponto(self, x: int, y: int) -> None:
        """Captura a cor do pixel na coordenada (x, y) e avança para a seleção do retângulo."""
        bytes_atuais = self._obter_bytes_imagem_atual()
        if not bytes_atuais:
            self.desativar_modo_mascara()
            return

        try:
            from editor.core.transformacoes_imagem import obter_cor_pixel
            self.cor_mascara_atual = obter_cor_pixel(bytes_atuais, x, y)
            r, g, b = self.cor_mascara_atual
            self.viewer.picking_callback = None
            self.info_label.setText(f"MODO MÁSCARA: Passo 2 - Cor RGB({r}, {g}, {b}) capturada. Arraste um retângulo sobre a área a cobrir. Esc para cancelar.")
            self.info_label.setStyleSheet("background-color: #2e7d32; color: white; padding: 5px; font-weight: bold;")
            self.viewer.iniciar_modo_selecao(self._ao_finalizar_selecao_mascara, cor_borda=QColor(r, g, b))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao capturar cor: {e}")
            self.desativar_modo_mascara()

    def _ao_finalizar_selecao_mascara(self, rect: QRectF) -> None:
        """Callback executado ao soltar o mouse após desenhar a área da máscara."""
        x1, y1 = int(rect.left()), int(rect.top())
        x2, y2 = int(rect.right()), int(rect.bottom())
        self.aplicar_mascara_selecao(x1, y1, x2, y2)

    def aplicar_mascara_selecao(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Aplica a máscara sólida retangular com a cor atual e despacha a transformação via histórico."""
        if not self.cor_mascara_atual:
            return

        largura = abs(x2 - x1)
        altura = abs(y2 - y1)
        if largura < 2 or altura < 2:
            return

        bytes_atuais = self._obter_bytes_imagem_atual()
        if not bytes_atuais:
            return

        try:
            from editor.core.transformacoes_imagem import aplicar_mascara_bytes
            bytes_mascarados = aplicar_mascara_bytes(bytes_atuais, (x1, y1, x2, y2), self.cor_mascara_atual)
            self._despachar_transformacao_imagem(bytes_mascarados)
            # Reativa o modo de seleção com a mesma cor para permitir múltiplas aplicações sequenciais
            if self.modo_mascara and self.cor_mascara_atual:
                r, g, b = self.cor_mascara_atual
                self.viewer.iniciar_modo_selecao(self._ao_finalizar_selecao_mascara, cor_borda=QColor(r, g, b))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao aplicar máscara: {e}")
            self.desativar_modo_mascara()

    def clear_masks(self) -> None:
        """Método de compatibilidade legado."""
        self.cancelar_selecao()

    def _obter_bytes_imagem_atual(self) -> Optional[bytes]:
        """Obtém os bytes mais recentes da imagem atual em memória RAM ou do disco."""
        if not self.current_file:
            return None
        nome_arquivo = Path(self.current_file).name
        caminho_rel = f"imagens/{nome_arquivo}"
        bytes_img = None
        if self.croqui_model and hasattr(self.croqui_model, "obter_bytes_imagem"):
            bytes_img = self.croqui_model.obter_bytes_imagem(caminho_rel) or self.croqui_model.obter_bytes_imagem(self.current_file)
        if bytes_img is None and os.path.exists(self.current_file):
            try:
                bytes_img = Path(self.current_file).read_bytes()
            except Exception:
                bytes_img = None
        if bytes_img is None and self.current_file in self.states:
            import io
            buf = io.BytesIO()
            self.states[self.current_file].working_image.save(buf, format="WEBP", quality=90)
            bytes_img = buf.getvalue()
        return bytes_img

    def _despachar_transformacao_imagem(self, bytes_novos: bytes) -> None:
        """Despacha uma transformação de imagem para o controlador/modelo com registro de histórico."""
        if not self.current_file:
            return
        nome_arquivo = Path(self.current_file).name
        caminho_rel = f"imagens/{nome_arquivo}"
        contexto_img = f"page:imagens/file:{nome_arquivo}"

        self._despachando_transformacao = True
        try:
            if self.croqui_controller and hasattr(self.croqui_controller, "substituir_imagem"):
                self.croqui_controller.set_contexto(contexto_img)
                self.croqui_controller.substituir_imagem(caminho_rel, bytes_novos, context_path=contexto_img)
            elif self.croqui_model and hasattr(self.croqui_model, "definir_imagem_memoria"):
                self.croqui_model.definir_imagem_memoria(caminho_rel, bytes_novos)
            else:
                # Modo autônomo sem modelo compartilhado
                import io
                with Image.open(io.BytesIO(bytes_novos)) as im:
                    working = im.convert("RGB") if im.mode not in ("RGB", "RGBA") else im.copy()
                if self.current_file in self.states:
                    self.states[self.current_file].working_image = working
                else:
                    self.states[self.current_file] = PageState(working, self.current_file)
                self.mark_modified()
                self.refresh_ui()
                return
        finally:
            self._despachando_transformacao = False

        self.states.pop(self.current_file, None)
        self.load_image(self.current_file)

    def rotate_image(self, angle: int) -> None:
        """Rotaciona a imagem atual pelo ângulo especificado (+90° horária, -90° anti-horária)."""
        if not self.current_file:
            return

        bytes_atuais = self._obter_bytes_imagem_atual()
        if not bytes_atuais:
            return

        try:
            from editor.core.transformacoes_imagem import rotacionar_imagem_bytes
            bytes_rotacionados = rotacionar_imagem_bytes(bytes_atuais, angle)
            self._despachar_transformacao_imagem(bytes_rotacionados)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao rotacionar: {e}")


    def apply_crop(self) -> None:
        """Legado: ativa o modo de corte interativo."""
        self.ativar_modo_corte()

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

