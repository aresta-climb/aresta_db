# Copyright (C) 2026 ARESTA
#
# Este arquivo faz parte do Aresta Editor.
# Componentes visuais para edição de mapas.

import math
import os
import glob
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem,
    QGraphicsPathItem, QGraphicsTextItem, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QMenu, QSlider, QMessageBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPixmap, QPen, QColor, QFont, QBrush, QPolygonF, QTransform, QPainterPath,
    QUndoCommand
)
import copy
from google.protobuf.json_format import ParseDict
from aresta_api.proto.generated import croqui_pb2

def registrar_movimento_final(item, estado_inicial):
    estado_final = copy.deepcopy(item.obter_dict_atualizado())
    if estado_inicial and estado_inicial != estado_final:
        widget_editor = item.scene().widget_editor
        if hasattr(widget_editor, 'mapas_controller') and widget_editor.mapas_controller:
            idx_poi = -1
            for idx, gui_item in widget_editor.itens_poi.items():
                if gui_item == item:
                    idx_poi = idx
                    break
            
            if idx_poi != -1 and widget_editor.msg_mapa_proxy:
                try:
                    poi_antigo = croqui_pb2.Mapa.PontoDeInteresse()
                    ParseDict(estado_inicial, poi_antigo)
                    poi_novo = croqui_pb2.Mapa.PontoDeInteresse()
                    ParseDict(estado_final, poi_novo)
                    
                    widget_editor.mapas_controller.mover_poi(widget_editor.msg_mapa_proxy, idx_poi, poi_antigo, poi_novo)
                    return
                except Exception as e:
                    print(f"Erro ao registrar movimento do POI: {e}")
    item.marcar_alterado()


class DialogoEdicaoPOI(QDialog):
    def __init__(self, id_atual="", label_atual="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Ponto de Interesse")
        layout = QFormLayout(self)
        
        self.input_id = QLineEdit(self)
        self.input_id.setText(str(id_atual))
        layout.addRow("ID (Referência):", self.input_id)
        
        self.input_label = QLineEdit(self)
        self.input_label.setText(str(label_atual))
        layout.addRow("Label (Texto no Mapa):", self.input_label)
        
        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)
        
    def obter_valores(self):
        return self.input_id.text().strip(), self.input_label.text().strip()


class BaseItemPOI:
    """Mixin base para itens de POI para compartilhar lógica comum."""
    def configurar_comum(self, pt_dict, callback_mudanca):
        self.inicializando = True
        self.pt_dict = pt_dict
        self.callback_mudanca = callback_mudanca
        
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        id_atual = pt_dict.get('id', '')
        label_atual = pt_dict.get('label', '')
        texto_exibicao = str(id_atual if id_atual else label_atual)
        self.setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        
        # Estilo visual
        self.pen = QPen(QColor(100, 255, 100))
        self.pen.setWidth(2)
        self.brush = QBrush(QColor(100, 255, 100, 60))
        
        # Texto
        self.item_texto = QGraphicsTextItem(texto_exibicao, self)
        self.item_texto.setDefaultTextColor(QColor(0, 0, 0))
        fonte = QFont("Arial", 14, QFont.Weight.Bold)
        self.item_texto.setFont(fonte)
        self.item_texto.setZValue(100)

    def atualizar_pos_texto(self, x, y):
        self.item_texto.setPos(x, y - 25)

    def marcar_alterado(self):
        if getattr(self, 'inicializando', False):
            return
        if self.callback_mudanca:
            self.callback_mudanca()

    def tratar_menu_contexto(self, evento, callback_deletar):
        menu = QMenu()
        acao_renomear = menu.addAction("Renomear Ponto de Interesse")
        acao_deletar = menu.addAction("Deletar Ponto de Interesse")
        acao = menu.exec(evento.screenPos())
        
        if acao == acao_renomear:
            id_atual = str(self.pt_dict.get('id', ''))
            label_atual = str(self.pt_dict.get('label', ''))
            dialogo = DialogoEdicaoPOI(id_atual, label_atual)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                novo_id, novo_label = dialogo.obter_valores()
                if novo_id != id_atual or novo_label != label_atual:
                    estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
                    
                    self.pt_dict['id'] = novo_id
                    self.pt_dict['label'] = novo_label
                    texto_exibicao = novo_id if novo_id else novo_label
                    self.item_texto.setPlainText(texto_exibicao)
                    self.setToolTip(f"ID: {novo_id} | Label: {novo_label}")
                    
                    registrar_movimento_final(self, estado_inicial)

        elif acao == acao_deletar:
            if callback_deletar:
                callback_deletar(self)


class ItemBoundingBox(QGraphicsRectItem, BaseItemPOI):
    def __init__(self, pt_dict, callback_deletar, callback_mudanca=None):
        super().__init__()
        self.callback_deletar = callback_deletar
        self.configurar_comum(pt_dict, callback_mudanca)
        
        box = pt_dict['box']
        w, h = box['comprimento'], box['largura']
        self.setRect(0, 0, w, h)
        self.setPos(box['x'] - w / 2, box['y'] - h / 2)
        self.setRotation(box.get('angulo_graus_x100', 0) / 100.0)
        
        self.setPen(self.pen)
        self.setBrush(self.brush)
        self.setTransformOriginPoint(self.rect().center())
        self.atualizar_pos_texto(0, 0)
        self.inicializando = False

    def carregar_de_dict(self, pt_dict):
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        box = self.pt_dict['box']
        w, h = box['comprimento'], box['largura']
        self.setRect(0, 0, w, h)
        self.setPos(box['x'] - w / 2, box['y'] - h / 2)
        self.setRotation(box.get('angulo_graus_x100', 0) / 100.0)
        self.setTransformOriginPoint(self.rect().center())
        self.atualizar_pos_texto(0, 0)
        id_atual = self.pt_dict.get('id', '')
        label_atual = self.pt_dict.get('label', '')
        self.item_texto.setPlainText(str(id_atual if id_atual else label_atual))
        self.setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def contextMenuEvent(self, evento):
        self.tratar_menu_contexto(evento, self.callback_deletar)

    def mousePressEvent(self, evento):
        self._estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
        if evento.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redimensionando = True
            self.rect_inicio_redim = self.rect()
            self.setTransformOriginPoint(self.rect_inicio_redim.center())
            self.centro_cena_inicio_redim = self.mapToScene(self.rect_inicio_redim.center())
            self.rotacao_inicio_redim = self.rotation()
            
            delta_inicio_cena = evento.scenePos() - self.centro_cena_inicio_redim
            transf_inv = QTransform().rotate(-self.rotacao_inicio_redim)
            delta_inicio_local = transf_inv.map(delta_inicio_cena)
            self.dist_inicio_redim_abs = QPointF(abs(delta_inicio_local.x()), abs(delta_inicio_local.y()))
            
            evento.accept()
        elif evento.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.rotacionando = True
            centro = self.mapToScene(self.rect().center())
            diff = evento.scenePos() - centro
            self.offset_angulo_inicio_rot = math.degrees(math.atan2(diff.y(), diff.x())) - self.rotation()
            evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if hasattr(self, 'redimensionando') and self.redimensionando:
            mouse_cena = evento.scenePos()
            delta_cena = mouse_cena - self.centro_cena_inicio_redim
            transf_inv = QTransform().rotate(-self.rotacao_inicio_redim)
            delta_local = transf_inv.map(delta_cena)
            
            diff_x = abs(delta_local.x()) - self.dist_inicio_redim_abs.x()
            diff_y = abs(delta_local.y()) - self.dist_inicio_redim_abs.y()
            
            novo_w = max(5, round(self.rect_inicio_redim.width() + 2 * diff_x))
            novo_h = max(5, round(self.rect_inicio_redim.height() + 2 * diff_y))
            
            self.setRect(0, 0, novo_w, novo_h)
            novo_centro = self.rect().center()
            self.setTransformOriginPoint(novo_centro)
            self.setPos(self.centro_cena_inicio_redim - novo_centro)
            evento.accept()
        elif hasattr(self, 'rotacionando') and self.rotacionando:
            centro = self.mapToScene(self.rect().center())
            diff = evento.scenePos() - centro
            angulo_atual = math.degrees(math.atan2(diff.y(), diff.x()))
            self.setRotation(angulo_atual - self.offset_angulo_inicio_rot)
            evento.accept()
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        self.redimensionando = False
        self.rotacionando = False
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def itemChange(self, mudanca, valor):
        if mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self):
        rect = self.rect()
        dados_box = {
            'x': int(round(self.x() + rect.width() / 2)),
            'y': int(round(self.y() + rect.height() / 2)),
            'comprimento': int(round(rect.width())),
            'largura': int(round(rect.height()))
        }
        angulo = self.rotation()
        while angulo > 360: angulo -= 360
        while angulo < -360: angulo += 360
        
        angulo_escalonado = int(round(angulo * 100))
        if angulo_escalonado != 0:
            dados_box['angulo_graus_x100'] = angulo_escalonado
            
        self.pt_dict['box'] = dados_box
        return self.pt_dict


class ItemBoundingCircular(QGraphicsEllipseItem, BaseItemPOI):
    def __init__(self, pt_dict, callback_deletar, callback_mudanca=None):
        super().__init__()
        self.callback_deletar = callback_deletar
        self.configurar_comum(pt_dict, callback_mudanca)
        
        circ = pt_dict['circular']
        r = circ['raio']
        self.setRect(-r, -r, 2 * r, 2 * r)
        self.setPos(circ['x'], circ['y'])
        
        self.setPen(self.pen)
        self.setBrush(self.brush)
        self.atualizar_pos_texto(-r, -r)
        self.inicializando = False

    def carregar_de_dict(self, pt_dict):
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        circ = self.pt_dict['circular']
        r = circ['raio']
        self.setRect(-r, -r, 2 * r, 2 * r)
        self.setPos(circ['x'], circ['y'])
        self.atualizar_pos_texto(-r, -r)
        id_atual = self.pt_dict.get('id', '')
        label_atual = self.pt_dict.get('label', '')
        self.item_texto.setPlainText(str(id_atual if id_atual else label_atual))
        self.setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def contextMenuEvent(self, evento):
        self.tratar_menu_contexto(evento, self.callback_deletar)

    def mousePressEvent(self, evento):
        self._estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
        if evento.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redimensionando = True
            self.pos_inicio_redim = evento.pos()
            self.rect_inicio_redim = self.rect()
            evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if hasattr(self, 'redimensionando') and self.redimensionando:
            delta = evento.pos() - self.pos_inicio_redim
            r = max(5, round(self.rect_inicio_redim.width() / 2 + delta.x()))
            self.setRect(-r, -r, 2 * r, 2 * r)
            self.atualizar_pos_texto(-r, -r)
            evento.accept()
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        self.redimensionando = False
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def itemChange(self, mudanca, valor):
        if mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self):
        r = int(round(self.rect().width() / 2))
        self.pt_dict['circular'] = {
            'x': int(round(self.x())),
            'y': int(round(self.y())),
            'raio': r
        }
        return self.pt_dict


class AlcaVertice(QGraphicsEllipseItem):
    def __init__(self, indice, pai):
        super().__init__(-7, -7, 14, 14, pai)
        self.indice = indice
        self.item_pai = pai
        cor = QColor(100, 100, 255) if isinstance(pai, ItemBoundingAreaLivre) else QColor(100, 255, 100)
        self.setBrush(QBrush(cor))
        self.setPen(QPen(QColor(0, 0, 0), 1))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def itemChange(self, mudanca, valor):
        if mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                novo_valor = QPointF(round(valor.x()), round(valor.y()))
                self.item_pai.atualizar_ponto(self.indice, novo_valor)
                return novo_valor
            else:
                self.item_pai.atualizar_ponto(self.indice, valor)
        return super().itemChange(mudanca, valor)

    def mousePressEvent(self, evento):
        self.item_pai._estado_inicial = copy.deepcopy(self.item_pai.obter_dict_atualizado())
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento):
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self.item_pai, getattr(self.item_pai, '_estado_inicial', None))


class ItemBoundingAreaLivre(QGraphicsPolygonItem, BaseItemPOI):
    def __init__(self, pt_dict, callback_deletar, callback_mudanca=None):
        super().__init__()
        self.callback_deletar = callback_deletar
        self.configurar_comum(pt_dict, callback_mudanca)
        
        coords = pt_dict['area_livre']['coordenadas']
        self.pontos = [QPointF(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
        
        self.setPolygon(QPolygonF(self.pontos))
        # Estilo azul para Área Livre
        self.pen = QPen(QColor(100, 100, 255))
        self.pen.setWidth(2)
        self.brush = QBrush(QColor(100, 100, 255, 60))
        
        self.setPen(self.pen)
        self.setBrush(self.brush)
        
        self.redimensionando = False
        self.rotacionando = False
        
        self.alcas = []
        for i, p in enumerate(self.pontos):
            alca = AlcaVertice(i, self)
            alca.setPos(p)
            self.alcas.append(alca)
            
        self.atualizar_posicao_texto()
        self.inicializando = False

    def carregar_de_dict(self, pt_dict):
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        coords = self.pt_dict['area_livre']['coordenadas']
        self.pontos = [QPointF(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
        self.setPos(0, 0)
        self.setPolygon(QPolygonF(self.pontos))
        
        # Reconstrói as alças
        if self.scene():
            for alca in self.alcas:
                self.scene().removeItem(alca)
        self.alcas.clear()
        for i, p in enumerate(self.pontos):
            alca = AlcaVertice(i, self)
            alca.setPos(p)
            self.alcas.append(alca)
        self.atualizar_posicao_texto()
        id_atual = self.pt_dict.get('id', '')
        label_atual = self.pt_dict.get('label', '')
        self.item_texto.setPlainText(str(id_atual if id_atual else label_atual))
        self.setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def atualizar_ponto(self, indice, pos):
        self.pontos[indice] = pos
        self.setPolygon(QPolygonF(self.pontos))
        self.atualizar_posicao_texto()
        self.marcar_alterado()

    def mousePressEvent(self, evento):
        self._estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento):
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def atualizar_posicao_texto(self):
        if not self.pontos: return
        min_x = min(p.x() for p in self.pontos)
        min_y = min(p.y() for p in self.pontos)
        self.atualizar_pos_texto(min_x, min_y)

    def itemChange(self, mudanca, valor):
        if mudanca == QGraphicsPolygonItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsPolygonItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def contextMenuEvent(self, evento):
        menu = QMenu()
        acao_renomear = menu.addAction("Renomear Ponto de Interesse")
        acao_deletar = menu.addAction("Deletar Ponto de Interesse")
        acao_add_ponto = menu.addAction("Adicionar Ponto")
        acao = menu.exec(evento.screenPos())
        
        if acao == acao_renomear:
            id_atual = str(self.pt_dict.get('id', ''))
            label_atual = str(self.pt_dict.get('label', ''))
            dialogo = DialogoEdicaoPOI(id_atual, label_atual)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                novo_id, novo_label = dialogo.obter_valores()
                if novo_id or novo_label:
                    self.pt_dict['id'] = novo_id
                    self.pt_dict['label'] = novo_label
                    self.item_texto.setPlainText(novo_id if novo_id else novo_label)
                    self.marcar_alterado()
        elif acao == acao_deletar:
            self.callback_deletar(self)
        elif acao == acao_add_ponto:
            p = self.mapFromScene(evento.pos())
            self.pontos.append(p)
            self.setPolygon(QPolygonF(self.pontos))
            alca = AlcaVertice(len(self.pontos)-1, self)
            alca.setPos(p)
            self.alcas.append(alca)
            self.atualizar_posicao_texto()
            self.marcar_alterado()

    def obter_dict_atualizado(self):
        pos = self.pos()
        coords = []
        for p in self.pontos:
            coords.append(int(round(p.x() + pos.x())))
            coords.append(int(round(p.y() + pos.y())))
        self.pt_dict['area_livre'] = {'coordenadas': coords}
        return self.pt_dict


class VisualizadorMapa(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, evento):
        if evento.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1/1.15, 1/1.15)


class CenaDesenho(QGraphicsScene):
    def __init__(self, widget_editor):
        super().__init__()
        self.widget_editor = widget_editor
        self.item_selecao = None
        # Alias para compatibilidade com testes antigos
        self.selection_item = None

    def mousePressEvent(self, evento):
        if self.widget_editor.drawing_mode:
            pos = evento.scenePos()
            if evento.button() == Qt.MouseButton.LeftButton:
                self.widget_editor.add_drawing_point(pos)
            elif evento.button() == Qt.MouseButton.RightButton:
                self.widget_editor.desfazer_ponto_desenho()
            evento.accept()
        elif self.widget_editor.convert_mode:
            if evento.button() == Qt.MouseButton.LeftButton:
                self.widget_editor.selection_origin = evento.scenePos()
                self.item_selecao = QGraphicsRectItem()
                self.selection_item = self.item_selecao # Alias
                self.item_selecao.setPen(QPen(QColor(255, 165, 0), 2, Qt.PenStyle.DashLine))
                self.item_selecao.setBrush(QBrush(QColor(255, 165, 0, 40)))
                self.addItem(self.item_selecao)
                evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        if self.widget_editor.convert_mode and self.item_selecao:
            rect = QRectF(self.widget_editor.selection_origin, evento.scenePos()).normalized()
            self.item_selecao.setRect(rect)
            evento.accept()
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        if self.widget_editor.convert_mode and self.item_selecao:
            rect = self.item_selecao.rect()
            self.removeItem(self.item_selecao)
            self.item_selecao = None
            self.selection_item = None # Alias
            self.widget_editor.selection_origin = None
            self.widget_editor.finish_conversion_area(rect)
            evento.accept()
        else:
            super().mouseReleaseEvent(evento)


class WidgetEditorMapas(QWidget):
    alterado = pyqtSignal(bool)
    
    def __init__(self, mapas_controller=None, parent=None, standalone=False):
        super().__init__(parent)
        self.standalone = standalone
        self.mapas_controller = mapas_controller
        self.msg_mapa_proxy = None
        self.itens_poi = {} # idx_poi -> QGraphicsItem
        
        self.dados_arquivos = {}
        self.esta_modificado = False
        self.bulk_base_dims = {}
        
        self.modo_desenho = False
        self.pontos_desenho = []
        self.item_desenho_temp = None
        self.alcas_desenho_temp = []
        
        self.modo_conversao = False
        self.origem_selecao = None
        self.dados_atuais = None

        self._setup_ui()
        
        # Estilo geral para combinar com o editor
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', sans-serif; }
            QPushButton { 
                padding: 8px; 
                border-radius: 4px; 
                background-color: #f0f0f0;
                border: 1px solid #ccc;
            }
            QPushButton:hover { background-color: #e0e0e0; }
            QPushButton#btn_salvar { 
                background-color: #2b579a; 
                color: white; 
                font-weight: bold; 
                border: none;
                font-size: 13px;
            }
            QPushButton#btn_salvar:hover { background-color: #244b85; }
            QListWidget { 
                border: 1px solid #dee2e6; 
                background-color: white;
                border-radius: 4px;
            }
        """)
        
        # Removido o carregamento automatico de pasta legada

    @property
    def convert_mode(self): return self.modo_conversao
    @convert_mode.setter
    def convert_mode(self, v): self.modo_conversao = v
    
    @property
    def drawing_mode(self): return self.modo_desenho
    @drawing_mode.setter
    def drawing_mode(self, v): self.modo_desenho = v
    
    @property
    def selection_origin(self): return self.origem_selecao
    @selection_origin.setter
    def selection_origin(self, v): self.origem_selecao = v

    # Aliases de compatibilidade para suporte a scripts/editar_mapas_test.py
    def add_drawing_point(self, pos): 
        return self.adicionar_ponto_desenho(pos)
    
    def finish_conversion_area(self, rect):
        return self.finalizar_area_conversao(rect)

    def _setup_ui(self):
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Painel Esquerdo (Sidebar de Mapas)
        self.widget_esquerdo = QWidget()
        self.widget_esquerdo.setMinimumWidth(220)
        self.widget_esquerdo.setStyleSheet("background-color: #f8f9fa; border-right: 1px solid #dee2e6;")
        layout_esquerdo = QVBoxLayout(self.widget_esquerdo)
        layout_esquerdo.setContentsMargins(10, 10, 10, 10)
        layout_esquerdo.setSpacing(8)
        
        self.label_titulo_arquivos = QLabel("Arquivos de Mapa")
        self.label_titulo_arquivos.setStyleSheet("font-weight: bold; color: #444; font-size: 13px;")
        layout_esquerdo.addWidget(self.label_titulo_arquivos)

        self.list_widget = QListWidget()
        layout_esquerdo.addWidget(self.list_widget)
        
        layout_botoes = QVBoxLayout()
        layout_botoes.setSpacing(4)
        
        from editor.views.estilo import Icones
        
        self.btn_add_circ = QPushButton(" Novo Círculo")
        self.btn_add_circ.setIcon(Icones.obter("dados")) # Temporário, ou usar qta diretamente
        self.btn_add_circ.clicked.connect(lambda: self.adicionar_poi('circular'))
        layout_botoes.addWidget(self.btn_add_circ)

        self.btn_add_box = QPushButton(" Novo Retângulo")
        self.btn_add_box.setIcon(Icones.obter("imagens"))
        self.btn_add_box.clicked.connect(lambda: self.adicionar_poi('box'))
        layout_botoes.addWidget(self.btn_add_box)

        self.btn_add_area = QPushButton(" Nova Área Livre")
        self.btn_add_area.setIcon(Icones.obter("mapas"))
        self.btn_add_area.clicked.connect(lambda: self.adicionar_poi('area_livre'))
        layout_botoes.addWidget(self.btn_add_area)
        
        layout_esquerdo.addLayout(layout_botoes)
        layout_esquerdo.addSpacing(10)

        self.btn_converter = QPushButton(" Retângulo -> Círculo")
        self.btn_converter.setToolTip("Converte Retângulos em Círculos. Se já estiver no modo, clique novamente para converter TODOS os retângulos.")
        self.btn_converter.clicked.connect(self.alternar_modo_conversao)
        layout_esquerdo.addWidget(self.btn_converter)

        layout_esquerdo.addStretch()

        layout_bulk = QVBoxLayout()
        label_bulk = QLabel("Redimensionamento:")
        label_bulk.setStyleSheet("font-weight: bold; color: #666;")
        layout_bulk.addWidget(label_bulk)
        
        # Sliders de redimensionamento em massa
        layout_bulk.addWidget(QLabel("Círculos:"))
        self.slider_circ = QSlider(Qt.Orientation.Horizontal)
        self.slider_circ.setRange(-50, 50)
        self.slider_circ.setValue(0)
        self.slider_circ.sliderPressed.connect(lambda: self.ao_pressionar_slider_bulk('circular'))
        self.slider_circ.valueChanged.connect(lambda v: self.ao_mover_slider_bulk(v, 'circular'))
        self.slider_circ.sliderReleased.connect(lambda: self.ao_soltar_slider_bulk('circular'))
        self.label_circ = QLabel("0%")
        self.label_circ.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_bulk.addWidget(self.slider_circ)
        layout_bulk.addWidget(self.label_circ)

        layout_bulk.addWidget(QLabel("Retângulos:"))
        self.slider_box = QSlider(Qt.Orientation.Horizontal)
        self.slider_box.setRange(-50, 50)
        self.slider_box.setValue(0)
        self.slider_box.sliderPressed.connect(lambda: self.ao_pressionar_slider_bulk('box'))
        self.slider_box.valueChanged.connect(lambda v: self.ao_mover_slider_bulk(v, 'box'))
        self.slider_box.sliderReleased.connect(lambda: self.ao_soltar_slider_bulk('box'))
        self.label_box = QLabel("0%")
        self.label_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_bulk.addWidget(self.slider_box)
        layout_bulk.addWidget(self.label_box)
        
        layout_esquerdo.addLayout(layout_bulk)
        layout_esquerdo.addSpacing(10)


        self.splitter.addWidget(self.widget_esquerdo)
        
        # Painel Direito (Visualizador)
        widget_direito = QWidget()
        layout_direito = QVBoxLayout(widget_direito)
        layout_direito.setContentsMargins(5, 5, 5, 5)

        self.visualizador = VisualizadorMapa()
        self.visualizador.setStyleSheet("background-color: #e9ecef; border: 1px solid #dee2e6; border-radius: 4px;")
        
        self.label_desenho = QLabel("MODO DESENHO - Clique para pontos, feche no primeiro. Dir: desfazer.")
        self.label_desenho.setStyleSheet("color: white; background-color: #dc3545; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.label_desenho.setVisible(False)
        self.label_desenho.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_direito.addWidget(self.label_desenho)

        self.label_conversao = QLabel("MODO CONVERSÃO - Selecione uma área no mapa ou CLIQUE NO BOTÃO NOVAMENTE para converter TODAS as boxes.")
        self.label_conversao.setStyleSheet("color: white; background-color: #fd7e14; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.label_conversao.setVisible(False)
        self.label_conversao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_direito.addWidget(self.label_conversao)

        self.label_info = QLabel("Dicas: Ctrl+Arrastar (Redimensionar) | Shift+Arrastar (Girar Retângulo)")
        self.label_info.setStyleSheet("color: #6c757d; font-style: italic; font-size: 11px;")
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout_direito.addWidget(self.label_info)
        
        self.label_placeholder = QLabel(
            "Selecione um mapa na árvore de Dados para começar a editar." if not self.standalone else "Selecione um arquivo de mapa na lista à esquerda para começar a editar."
        )
        self.label_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_placeholder.setStyleSheet("color: #999; font-size: 16px; font-style: italic;")
        layout_direito.addWidget(self.label_placeholder)
        
        layout_direito.addWidget(self.visualizador)
        
        # Conecta o clique no item
        self.list_widget.itemSelectionChanged.connect(self._on_mapa_selecionado)
        
        # O painel esquerdo agora é sempre adicionado. A visibilidade do widget_esquerdo
        # é mantida globalmente, mas para standalone tem comportamentos customizados em outros cantos.
        self.splitter.addWidget(self.widget_esquerdo)
        self.splitter.addWidget(widget_direito)
        
        self.splitter.setSizes([200, 800])
        
        layout_principal.addWidget(self.splitter)

    def configurar_lista_mapas(self):
        """Conecta o modelo reativo e preenche a lista."""
        if not self.mapas_controller or not self.mapas_controller.model:
            return
            
        model = self.mapas_controller.model
        model.dado_alterado.connect(self._atualizar_lista_mapas)
        model.repeated_adicionado.connect(self._atualizar_lista_mapas)
        model.repeated_removido.connect(self._atualizar_lista_mapas)
        
        self._atualizar_lista_mapas()
        
    def _atualizar_lista_mapas(self, *args):
        """Reconstrói a lista lendo do CroquiModel."""
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import Qt
        from pathlib import Path
        
        # Salva seleção atual
        current_item = self.list_widget.currentItem()
        selected_data = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None

        self.list_widget.clear()
        if not self.mapas_controller or not self.mapas_controller.model: return
        
        croqui_msg = self.mapas_controller.model.obter_croqui_readonly()
        
        for p_idx, pico in enumerate(croqui_msg.picos):
            for sg_idx, sg in enumerate(pico.setores_ou_grupos):
                # Mapas do Setor
                if getattr(sg, 'setor', None):
                    for m_idx, mapa in enumerate(sg.setor.conteudo.mapas):
                        if not mapa.caminho_imagem_mapa: continue
                        nome = Path(mapa.caminho_imagem_mapa).name
                        item = QListWidgetItem(nome)
                        item.setData(Qt.ItemDataRole.UserRole, ('setor', p_idx, sg_idx, m_idx))
                        self.list_widget.addItem(item)
                
                # Mapas do Grupo e seus Sub-setores
                if getattr(sg, 'grupo', None):
                    for m_idx, mapa in enumerate(sg.grupo.conteudo.mapas):
                        if not mapa.caminho_imagem_mapa: continue
                        nome = Path(mapa.caminho_imagem_mapa).name
                        item = QListWidgetItem(nome)
                        item.setData(Qt.ItemDataRole.UserRole, ('grupo', p_idx, sg_idx, m_idx))
                        self.list_widget.addItem(item)
                    
                    for s_idx, subsetor in enumerate(sg.grupo.conteudo.setores):
                        for m_idx, mapa in enumerate(subsetor.conteudo.mapas):
                            if not mapa.caminho_imagem_mapa: continue
                            nome = Path(mapa.caminho_imagem_mapa).name
                            item = QListWidgetItem(nome)
                            item.setData(Qt.ItemDataRole.UserRole, ('subsetor', p_idx, sg_idx, s_idx, m_idx))
                            self.list_widget.addItem(item)

        # Restaura a seleção da lista
        if selected_data:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == selected_data:
                    self.list_widget.blockSignals(True)
                    self.list_widget.setCurrentItem(item)
                    self.list_widget.blockSignals(False)
                    break
        elif hasattr(self, 'pico_idx') and self.pico_idx >= 0 and self.sg_idx >= 0 and self.mapa_idx >= 0:
            self.list_widget.blockSignals(True)
            s_idx = getattr(self, 's_idx', -1)
            self.selecionar_mapa_por_indices(self.pico_idx, self.sg_idx, self.mapa_idx, s_idx)
            self.list_widget.blockSignals(False)
                    
    def _on_mapa_selecionado(self):
        item = self.list_widget.currentItem()
        if not item: return
        
        indices = item.data(Qt.ItemDataRole.UserRole)
        if not indices: return
        
        if len(indices) == 3:
            # Compatibilidade com índices antigos por segurança, assumindo setor
            p_idx, sg_idx, m_idx = indices
            tipo = 'setor'
            s_idx = -1
        elif len(indices) == 5:
            tipo, p_idx, sg_idx, s_idx, m_idx = indices
        else:
            tipo, p_idx, sg_idx, m_idx = indices
            s_idx = -1
            
        if not self.mapas_controller or not self.mapas_controller.model: return
        
        croqui_msg = self.mapas_controller.model.obter_croqui_readonly()
        try:
            if tipo == 'grupo':
                mapa = croqui_msg.picos[p_idx].setores_ou_grupos[sg_idx].grupo.conteudo.mapas[m_idx]
            elif tipo == 'subsetor':
                mapa = croqui_msg.picos[p_idx].setores_ou_grupos[sg_idx].grupo.conteudo.setores[s_idx].conteudo.mapas[m_idx]
            else: # setor
                mapa = croqui_msg.picos[p_idx].setores_ou_grupos[sg_idx].setor.conteudo.mapas[m_idx]
                
            # O set_mapa_atual interno ainda não precisa do tipo pois ele emite sinais usando MapasController
            # que depois vai salvar_mapa. Precisamos ver se o MapasController também requer ajuste.
            self.set_mapa_atual(mapa, p_idx, sg_idx, m_idx, s_idx=s_idx, tipo=tipo)
        except IndexError:
            pass # Prevenção de falhas de sincronia na deleção

    def selecionar_mapa_por_indices(self, pico_idx, grupo_idx, mapa_idx, s_idx=-1):
        """Seleciona visualmente o mapa na lista dado os seus índices, disparando a atualização da tela."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            indices = item.data(Qt.ItemDataRole.UserRole)
            if indices:
                if len(indices) == 3 and indices == (pico_idx, grupo_idx, mapa_idx):
                    self.list_widget.setCurrentItem(item)
                    return True
                elif len(indices) == 4 and indices[1:] == (pico_idx, grupo_idx, mapa_idx) and s_idx == -1:
                    self.list_widget.setCurrentItem(item)
                    return True
                elif len(indices) == 5 and indices[1:] == (pico_idx, grupo_idx, s_idx, mapa_idx):
                    self.list_widget.setCurrentItem(item)
                    return True
        return False

    def set_mapa_atual(self, msg_mapa_proxy, pico_idx=-1, grupo_idx=-1, mapa_idx=-1, s_idx=-1, tipo='setor'):
        """Define o mapa atual para exibição na view, limpando a cena."""
        self.msg_mapa_proxy = msg_mapa_proxy
        self.pico_idx = pico_idx
        self.sg_idx = grupo_idx
        self.mapa_idx = mapa_idx
        self.s_idx = s_idx
        self.dados_atuais = {
            'cena': CenaDesenho(self),
            'itens_bb': [],
            'mapa_msg': msg_mapa_proxy,
            'pico_idx': pico_idx,
            'sg_idx': grupo_idx,
            'mapa_idx': mapa_idx,
            's_idx': s_idx
        }
        self.itens_poi.clear()
        
        # Conectar sinais do Model caso haja um MapasController com o Model (necessário para reatividade)
        if self.mapas_controller and self.mapas_controller.model:
            if hasattr(self.mapas_controller, 'set_contexto') and pico_idx >= 0 and mapa_idx >= 0:
                if tipo == 'grupo':
                    path = f"page:mapas/node:Croqui/expando:picos/item:{pico_idx}/expando:setores_ou_grupos/item:{grupo_idx}/expando:grupo/expando:mapas/item:{mapa_idx}"
                elif tipo == 'subsetor':
                    path = f"page:mapas/node:Croqui/expando:picos/item:{pico_idx}/expando:setores_ou_grupos/item:{grupo_idx}/expando:grupo/expando:setores/item:{s_idx}/expando:setor/expando:mapas/item:{mapa_idx}"
                else:
                    path = f"page:mapas/node:Croqui/expando:picos/item:{pico_idx}/expando:setores_ou_grupos/item:{grupo_idx}/expando:setor/expando:mapas/item:{mapa_idx}"
                self.mapas_controller.set_contexto(path)
                
            model = self.mapas_controller.model
            try:
                model.repeated_item_alterado.disconnect(self._on_repeated_item_alterado)
                model.repeated_adicionado.disconnect(self._on_repeated_adicionado)
                model.repeated_removido.disconnect(self._on_repeated_removido)
            except Exception: pass
            model.repeated_item_alterado.connect(self._on_repeated_item_alterado)
            model.repeated_adicionado.connect(self._on_repeated_adicionado)
            model.repeated_removido.connect(self._on_repeated_removido)
            
        self._renderizar_mapa(reset_zoom=True)
        
    def _renderizar_mapa(self, reset_zoom=True):
        """Lê a mensagem Protobuf e renderiza a cena inteira."""
        if not self.msg_mapa_proxy:
            self.visualizador.setScene(None)
            self.label_placeholder.show()
            return
            
        old_transform = self.visualizador.transform()
        old_h_scroll = self.visualizador.horizontalScrollBar().value()
        old_v_scroll = self.visualizador.verticalScrollBar().value()
        
        self.label_placeholder.hide()
        dados = self.dados_atuais
        cena = dados['cena']
        cena.clear()
        self.itens_poi.clear()
        dados['itens_bb'] = []
        
        img_path = None
        if self.mapas_controller:
            img_path = self.mapas_controller.obter_caminho_imagem_mapa(self.msg_mapa_proxy)
            
        if img_path and str(img_path) and os.path.exists(str(img_path)):
            pixmap = QPixmap(str(img_path))
            item_img = cena.addPixmap(pixmap)
            item_img.setZValue(-100)
            
        for i, poi in enumerate(self.msg_mapa_proxy.pontos_de_interesse):
            self._adicionar_item_cena(poi, i, cena)
            
        self.visualizador.setScene(cena)
        
        if reset_zoom:
            self.visualizador.fitInView(cena.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.visualizador.setTransform(old_transform)
            self.visualizador.horizontalScrollBar().setValue(old_h_scroll)
            self.visualizador.verticalScrollBar().setValue(old_v_scroll)

        # Sincroniza a seleção na lista se os índices foram passados
        if getattr(self, 'pico_idx', -1) >= 0 and getattr(self, 'sg_idx', -1) >= 0 and getattr(self, 'mapa_idx', -1) >= 0:
            self.list_widget.blockSignals(True)
            s_idx = getattr(self, 's_idx', -1)
            self.selecionar_mapa_por_indices(self.pico_idx, self.sg_idx, self.mapa_idx, s_idx)
            self.list_widget.blockSignals(False)
    def _adicionar_item_cena(self, poi, index, cena):
        # Transforma mensagem protobuf em dicionário genérico para os itens gráficos legacy
        from google.protobuf.json_format import MessageToDict
        pt_dict = MessageToDict(poi, preserving_proto_field_name=True)
        
        def cb_deletar(item):
            self.deletar_item_poi(item)
            
        item_visual = None
        if poi.HasField('box'):
            item_visual = ItemBoundingBox(pt_dict, cb_deletar)
        elif poi.HasField('circular'):
            item_visual = ItemBoundingCircular(pt_dict, cb_deletar)
        elif poi.HasField('area_livre'):
            item_visual = ItemBoundingAreaLivre(pt_dict, cb_deletar)
            
        if item_visual:
            cena.addItem(item_visual)
            self.itens_poi[index] = item_visual
            self.dados_atuais['itens_bb'].append(item_visual)

    def adicionar_poi(self, tipo):
        if not self.dados_atuais or not self.mapas_controller: return
        
        if tipo == 'area_livre':
            self.iniciar_modo_desenho(self.dados_atuais)
            return

        dialogo = DialogoEdicaoPOI("", "")
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            novo_id, novo_label = dialogo.obter_valores()
            if not novo_id and not novo_label: return
            
            rect_visao = self.visualizador.mapToScene(self.visualizador.viewport().rect()).boundingRect()
            cx, cy = rect_visao.center().x(), rect_visao.center().y()
            
            from aresta_api.proto.generated import croqui_pb2
            novo_poi = croqui_pb2.Mapa.PontoDeInteresse(id=novo_id, label=novo_label)
            
            if tipo == 'circular':
                novo_poi.circular.x = int(cx)
                novo_poi.circular.y = int(cy)
                novo_poi.circular.raio = 40
            elif tipo == 'box':
                novo_poi.box.x = int(cx-40)
                novo_poi.box.y = int(cy-40)
                novo_poi.box.comprimento = 80
                novo_poi.box.largura = 80
            
            self.mapas_controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)

    def deletar_item_poi(self, item):
        if not self.mapas_controller: return
        
        idx_poi = -1
        for idx, gui_item in self.itens_poi.items():
            if gui_item == item:
                idx_poi = idx
                break
                
        if idx_poi != -1:
            self.mapas_controller.deletar_poi(self.msg_mapa_proxy, idx_poi)

    def marcar_modificado(self):
        if not self.esta_modificado:
            self.esta_modificado = True
            self.alterado.emit(True)

    # Lógica de Desenho e Conversão
    def iniciar_modo_desenho(self, dados):
        self.modo_desenho = True
        self.pontos_desenho = []
        self.dados_atuais = dados
        self.label_desenho.setVisible(True)
        self.visualizador.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.visualizador.setCursor(Qt.CursorShape.CrossCursor)
        self.item_desenho_temp = QGraphicsPathItem()
        self.item_desenho_temp.setPen(QPen(QColor(255, 100, 100), 2))
        self.item_desenho_temp.setBrush(QBrush(QColor(255, 100, 100, 50)))
        dados['cena'].addItem(self.item_desenho_temp)
        self.alcas_desenho_temp = []

    def adicionar_ponto_desenho(self, pos):
        if self.pontos_desenho:
            p_inicio = self.pontos_desenho[0]
            dist = math.sqrt((pos.x() - p_inicio.x())**2 + (pos.y() - p_inicio.y())**2)
            if dist < 15 and len(self.pontos_desenho) >= 3:
                self.finalizar_modo_desenho()
                return
        
        self.pontos_desenho.append(pos)
        path = QPainterPath()
        path.moveTo(self.pontos_desenho[0])
        for p in self.pontos_desenho[1:]:
            path.lineTo(p)
        self.item_desenho_temp.setPath(path)
        
        alca = QGraphicsEllipseItem(-4, -4, 8, 8)
        alca.setPos(pos)
        alca.setPen(QPen(QColor(255, 100, 100)))
        alca.setBrush(QBrush(QColor(255, 255, 255)))
        alca.setZValue(1000)
        self.dados_atuais['cena'].addItem(alca)
        self.alcas_desenho_temp.append(alca)

    def desfazer_ponto_desenho(self):
        if self.pontos_desenho:
            self.pontos_desenho.pop()
            alca = self.alcas_desenho_temp.pop()
            self.dados_atuais['cena'].removeItem(alca)
            if not self.pontos_desenho:
                self.cancelar_modo_desenho()
            else:
                path = QPainterPath()
                path.moveTo(self.pontos_desenho[0])
                for p in self.pontos_desenho[1:]:
                    path.lineTo(p)
                self.item_desenho_temp.setPath(path)

    def finalizar_modo_desenho(self):
        if len(self.pontos_desenho) < 3:
            self.cancelar_modo_desenho()
            return
            
        dialogo = DialogoEdicaoPOI("", "")
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            novo_id, novo_label = dialogo.obter_valores()
            if novo_id or novo_label:
                from aresta_api.proto.generated import croqui_pb2
                novo_poi = croqui_pb2.Mapa.PontoDeInteresse(id=novo_id, label=novo_label)
                for p in self.pontos_desenho:
                    novo_poi.area_livre.coordenadas.append(int(p.x()))
                    novo_poi.area_livre.coordenadas.append(int(p.y()))
                
                if self.mapas_controller:
                    self.mapas_controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)

        self.cancelar_modo_desenho()

    def cancelar_modo_desenho(self):
        self.modo_desenho = False
        self.label_desenho.setVisible(False)
        self.visualizador.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.visualizador.unsetCursor()
        if self.item_desenho_temp:
            self.dados_atuais['cena'].removeItem(self.item_desenho_temp)
            self.item_desenho_temp = None
        for alca in self.alcas_desenho_temp:
            self.dados_atuais['cena'].removeItem(alca)
        self.alcas_desenho_temp = []
        self.pontos_desenho = []

    def alternar_modo_conversao(self):
        if self.modo_desenho: return
        if self.modo_conversao:
            if self.dados_atuais and self.mapas_controller:
                indices = []
                for idx_poi, gui_item in list(self.itens_poi.items()):
                    if isinstance(gui_item, ItemBoundingBox):
                        indices.append(idx_poi)
                if indices:
                    self.mapas_controller.converter_boxes_para_circulos(self.msg_mapa_proxy, indices)
            self.parar_modo_conversao()
        else:
            self.iniciar_modo_conversao()

    def iniciar_modo_conversao(self):
        self.modo_conversao = True
        self.label_conversao.setVisible(True)
        self.btn_converter.setStyleSheet("background-color: orange; font-weight: bold;")
        self.visualizador.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.visualizador.setCursor(Qt.CursorShape.CrossCursor)

    def parar_modo_conversao(self):
        self.modo_conversao = False
        self.label_conversao.setVisible(False)
        self.btn_converter.setStyleSheet("")
        self.visualizador.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.visualizador.unsetCursor()
        self.origem_selecao = None

    def finalizar_area_conversao(self, rect):
        if not self.dados_atuais or not self.mapas_controller: return
        a_converter = []
        for idx_poi, gui_item in list(self.itens_poi.items()):
            if isinstance(gui_item, ItemBoundingBox):
                if rect.contains(gui_item.mapToScene(gui_item.rect().center())):
                    a_converter.append(idx_poi)
        if a_converter:
            self.mapas_controller.converter_boxes_para_circulos(self.msg_mapa_proxy, a_converter)
        self.parar_modo_conversao()

    # Bulk Sliders logic
    def ao_pressionar_slider_bulk(self, tipo):
        if not self.dados_atuais: return
        self.bulk_base_dims = {}
        from copy import deepcopy
        for idx, gui_item in self.itens_poi.items():
            if tipo == 'circular' and isinstance(gui_item, ItemBoundingCircular):
                self.bulk_base_dims[id(gui_item)] = {
                    'r': gui_item.rect().width() / 2,
                    'estado_inicial': deepcopy(gui_item.obter_dict_atualizado()),
                    'idx': idx
                }
            elif tipo == 'box' and isinstance(gui_item, ItemBoundingBox):
                self.bulk_base_dims[id(gui_item)] = {
                    'w': gui_item.rect().width(),
                    'h': gui_item.rect().height(),
                    'estado_inicial': deepcopy(gui_item.obter_dict_atualizado()),
                    'idx': idx
                }

    def ao_mover_slider_bulk(self, valor, tipo):
        if not self.bulk_base_dims: return
        fator = 1.0 + valor / 100.0
        mudou = False
        if tipo == 'circular':
            self.label_circ.setText(f"{valor:+}%")
            for gui_item in self.itens_poi.values():
                if isinstance(gui_item, ItemBoundingCircular) and id(gui_item) in self.bulk_base_dims:
                    base_r = self.bulk_base_dims[id(gui_item)]['r']
                    novo_r = max(2, base_r * fator)
                    gui_item.setRect(-novo_r, -novo_r, 2 * novo_r, 2 * novo_r)
                    gui_item.atualizar_pos_texto(-novo_r, -novo_r)
                    mudou = True
        elif tipo == 'box':
            self.label_box.setText(f"{valor:+}%")
            for gui_item in self.itens_poi.values():
                if isinstance(gui_item, ItemBoundingBox) and id(gui_item) in self.bulk_base_dims:
                    base_w = self.bulk_base_dims[id(gui_item)]['w']
                    base_h = self.bulk_base_dims[id(gui_item)]['h']
                    novo_w = max(4, base_w * fator)
                    novo_h = max(4, base_h * fator)
                    centro_cena_antigo = gui_item.mapToScene(gui_item.rect().center())
                    gui_item.setRect(0, 0, novo_w, novo_h)
                    gui_item.setTransformOriginPoint(gui_item.rect().center())
                    gui_item.setPos(centro_cena_antigo - gui_item.rect().center())
                    mudou = True

    def ao_soltar_slider_bulk(self, tipo):
        if self.bulk_base_dims and self.mapas_controller:
            # Dispatch changes to controller
            from aresta_api.proto.generated import croqui_pb2
            from google.protobuf.json_format import ParseDict
            
            # Cria nome da ação
            nome_acao = "Redimensionar Círculos" if tipo == 'circular' else "Redimensionar Retângulos"
            self.mapas_controller.iniciar_grupo_undo(nome_acao)
            
            # Simples iterar e aplicar modificações
            for uid, state in self.bulk_base_dims.items():
                idx = state['idx']
                gui_item = self.itens_poi.get(idx)
                if gui_item:
                    estado_inicial = state['estado_inicial']
                    estado_final = gui_item.obter_dict_atualizado()
                    
                    if estado_inicial != estado_final:
                        poi_antigo = croqui_pb2.Mapa.PontoDeInteresse()
                        ParseDict(estado_inicial, poi_antigo)
                        poi_novo = croqui_pb2.Mapa.PontoDeInteresse()
                        ParseDict(estado_final, poi_novo)
                        self.mapas_controller.mover_poi(self.msg_mapa_proxy, idx, poi_antigo, poi_novo)
                        
            self.mapas_controller.finalizar_grupo_undo()
            
        self.bulk_base_dims = {}
        if tipo == 'circular':
            self.slider_circ.blockSignals(True); self.slider_circ.setValue(0); self.slider_circ.blockSignals(False)
            self.label_circ.setText("0%")
        elif tipo == 'box':
            self.slider_box.blockSignals(True); self.slider_box.setValue(0); self.slider_box.blockSignals(False)
            self.label_box.setText("0%")

    def _on_repeated_item_alterado(self, msg, campo_nome, index):
        if self.msg_mapa_proxy == msg and campo_nome == 'pontos_de_interesse':
            poi = msg.pontos_de_interesse[index]
            item_existente = self.itens_poi.get(index)
            if item_existente:
                from google.protobuf.json_format import MessageToDict
                pt_dict = MessageToDict(poi, preserving_proto_field_name=True)
                # Verifica se o tipo da Box foi convertido (ex: box -> circular)
                mesmo_tipo = False
                if poi.HasField('box') and isinstance(item_existente, ItemBoundingBox):
                    mesmo_tipo = True
                elif poi.HasField('circular') and isinstance(item_existente, ItemBoundingCircular):
                    mesmo_tipo = True
                elif poi.HasField('area_livre') and isinstance(item_existente, ItemBoundingAreaLivre):
                    mesmo_tipo = True
                    
                if mesmo_tipo:
                    item_existente.carregar_de_dict(pt_dict)
                else:
                    self._renderizar_mapa()

    def _on_repeated_adicionado(self, msg, campo_nome, index):
        if self.msg_mapa_proxy == msg and campo_nome == 'pontos_de_interesse':
            self._renderizar_mapa()

    def _on_repeated_removido(self, msg, campo_nome, index):
        if self.msg_mapa_proxy == msg and campo_nome == 'pontos_de_interesse':
            self._renderizar_mapa()
