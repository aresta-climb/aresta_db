from typing import cast, Optional, Any, Callable, List, Dict, Set, Tuple, Union
# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

# Copyright (C) 2026 ARESTA
#
# Este arquivo faz parte do Editor Aresta.
# Componentes visuais para edição de mapas.

import math
import os
import glob
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPolygonItem,
    QGraphicsPathItem, QGraphicsTextItem, QGraphicsPixmapItem, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QMenu, QSlider, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPixmap, QPen, QColor, QFont, QBrush, QPolygonF, QTransform, QPainterPath,
    QUndoCommand
)
import copy
from google.protobuf.json_format import ParseDict
from aresta_api.proto.generated import croqui_pb2

def registrar_movimento_final(item: Any, estado_inicial: Optional[Dict[str, Any]]) -> None:
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
    def __init__(self, id_atual: str = "", label_atual: str = "", parent: Optional[QWidget] = None) -> None:
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
        
    def obter_valores(self) -> Tuple[str, str]:
        return self.input_id.text().strip(), self.input_label.text().strip()


class BaseItemPOI:
    """Mixin base para itens de POI para compartilhar lógica comum."""
    inicializando: bool
    pt_dict: Dict[str, Any]
    callback_mudanca: Any
    item_texto: QGraphicsTextItem
    pen_poi: QPen
    brush_poi: QBrush
    clique_handler: Optional[Callable[[str], bool]]
    
    def obter_dict_atualizado(self) -> Dict[str, Any]:
        raise NotImplementedError
        
    def setToolTip(self, text: str) -> None:
        pass
    def configurar_comum(self, pt_dict: Dict[str, Any], callback_mudanca: Any) -> None:
        self.inicializando = True
        self.pt_dict = pt_dict
        self.callback_mudanca = callback_mudanca
        
        cast_self = cast(Any, self)
        cast_self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        cast_self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        cast_self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        id_atual = pt_dict.get('id', '')
        label_atual = pt_dict.get('label', '')
        texto_exibicao = str(id_atual if id_atual else label_atual)
        cast(Any, self).setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        
        # Estilo visual
        self.pen_poi = QPen(QColor(100, 255, 100))
        self.pen_poi.setWidth(2)
        self.brush_poi = QBrush(QColor(100, 255, 100, 60))
        
        # Texto
        self.item_texto = QGraphicsTextItem(texto_exibicao, cast(Any, self))
        self.item_texto.setDefaultTextColor(QColor(0, 0, 0))
        fonte = QFont("Arial", 14, QFont.Weight.Bold)
        self.item_texto.setFont(fonte)
        self.item_texto.setZValue(100)

    def atualizar_pos_texto(self, x: float, y: float) -> None:
        self.item_texto.setPos(x, y - 25)

    def marcar_alterado(self) -> None:
        if getattr(self, 'inicializando', False):
            return
        if self.callback_mudanca:
            self.callback_mudanca()

    def set_clique_handler(self, handler: Any) -> None:
        self.clique_handler = handler

    def tratar_menu_contexto(self, evento: Any, callback_deletar: Any, acoes_extras: Optional[List[Tuple[str, Callable[[], None]]]] = None) -> None:
        menu = QMenu()
        acao_renomear = menu.addAction("Renomear Ponto de Interesse")
        acao_deletar = menu.addAction("Deletar Ponto de Interesse")
        
        acoes_map = {}
        if acoes_extras:
            menu.addSeparator()
            for texto, cb in acoes_extras:
                acao = menu.addAction(texto)
                acoes_map[acao] = cb
                
        pos = evento.screenPos() if hasattr(evento, 'screenPos') else None
        if pos is not None:
            acao = menu.exec(pos)
        else:
            acao = menu.exec()
        
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
                
        elif acao in acoes_map:
            acoes_map[acao]()


class ItemBoundingRetangulo(QGraphicsRectItem, BaseItemPOI):
    """Representa visualmente uma área de interesse retangular no editor de mapas. Permite redimensionamento pelos cantos e rotação."""
    def __init__(self, pt_dict: Dict[str, Any], callback_deletar: Any, callback_mudanca: Optional[Any] = None, callback_converter: Optional[Any] = None) -> None:
        super().__init__()
        self.callback_deletar = callback_deletar
        self.callback_converter = callback_converter
        self.configurar_comum(pt_dict, callback_mudanca)
        
        box = pt_dict.get('retangulo', pt_dict.get('retangulo', {}))
        w, h = box['comprimento'], box['largura']
        self.setRect(0, 0, w, h)
        self.setPos(box['x'] - w / 2, box['y'] - h / 2)
        self.setRotation(box.get('angulo_graus_x100', 0) / 100.0)
        
        self.setPen(self.pen_poi)
        self.setBrush(self.brush_poi)
        self.setTransformOriginPoint(self.rect().center())
        self.atualizar_pos_texto(0, 0)
        self.inicializando = False

    def carregar_de_dict(self, pt_dict: Dict[str, Any]) -> None:
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        box = self.pt_dict['retangulo']
        w, h = box['comprimento'], box['largura']
        self.setRect(0, 0, w, h)
        self.setPos(box['x'] - w / 2, box['y'] - h / 2)
        self.setRotation(box.get('angulo_graus_x100', 0) / 100.0)
        self.setTransformOriginPoint(self.rect().center())
        self.atualizar_pos_texto(0, 0)
        id_atual = self.pt_dict.get('id', '')
        label_atual = self.pt_dict.get('label', '')
        self.item_texto.setPlainText(str(id_atual if id_atual else label_atual))
        cast(Any, self).setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def contextMenuEvent(self, evento: Any) -> None:
        acoes_extras = []
        if getattr(self, 'callback_converter', None):
            acoes_extras.append(("Converter para Círculo", lambda: self.callback_converter(self) if self.callback_converter else None if self.callback_converter else None))
        self.tratar_menu_contexto(evento, self.callback_deletar, acoes_extras)

    def mousePressEvent(self, evento: Any) -> None:
        if hasattr(self, 'clique_handler') and getattr(self, 'clique_handler') and hasattr(self, 'pt_dict'):
            if getattr(self, 'clique_handler')(getattr(self, 'pt_dict', {}).get('id')):
                evento.accept()
                return
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

    def mouseMoveEvent(self, evento: Any) -> None:
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

    def mouseReleaseEvent(self, evento: Any) -> None:
        self.redimensionando = False
        self.rotacionando = False
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def itemChange(self, mudanca: Any, valor: Any) -> Any:
        if mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self) -> Dict[str, Any]:
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
            
        self.pt_dict['retangulo'] = dados_box
        return self.pt_dict



class ItemBoundingQuadrado(QGraphicsRectItem, BaseItemPOI):
    """Representa visualmente uma área de interesse quadrada no editor de mapas. Mantém proporção 1:1 e permite redimensionamento preservando os eixos centrais."""
    def __init__(self, pt_dict: Dict[str, Any], callback_deletar: Any, callback_mudanca: Optional[Any] = None, callback_converter: Optional[Any] = None) -> None:
        super().__init__()
        self.callback_deletar = callback_deletar
        self.callback_converter = callback_converter
        self.configurar_comum(pt_dict, callback_mudanca)
        
        box = pt_dict.get('quadrado', {})
        lado = box['lado']
        self.setRect(0, 0, lado, lado)
        self.setPos(box['x'] - lado / 2, box['y'] - lado / 2)
        
        self.setPen(self.pen_poi)
        self.setBrush(self.brush_poi)
        self.setTransformOriginPoint(self.rect().center())
        self.atualizar_pos_texto(0, 0)
        self.inicializando = False

    def carregar_de_dict(self, pt_dict: Dict[str, Any]) -> None:
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        box = self.pt_dict['quadrado']
        lado = box['lado']
        self.setRect(0, 0, lado, lado)
        self.setPos(box['x'] - lado / 2, box['y'] - lado / 2)
        self.setTransformOriginPoint(self.rect().center())
        self.atualizar_pos_texto(0, 0)
        id_atual = self.pt_dict.get('id', '')
        label_atual = self.pt_dict.get('label', '')
        self.item_texto.setPlainText(str(id_atual if id_atual else label_atual))
        cast(Any, self).setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def contextMenuEvent(self, evento: Any) -> None:
        acoes_extras = []
        if getattr(self, 'callback_converter', None):
            acoes_extras.append(("Converter para Círculo", lambda: self.callback_converter(self) if self.callback_converter else None if self.callback_converter else None))
        self.tratar_menu_contexto(evento, self.callback_deletar, acoes_extras)

    def mousePressEvent(self, evento: Any) -> None:
        if hasattr(self, 'clique_handler') and getattr(self, 'clique_handler') and hasattr(self, 'pt_dict'):
            if getattr(self, 'clique_handler')(getattr(self, 'pt_dict', {}).get('id')):
                evento.accept()
                return
        self._estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
        if evento.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redimensionando = True
            self.rect_inicio_redim = self.rect()
            self.setTransformOriginPoint(self.rect_inicio_redim.center())
            self.centro_cena_inicio_redim = self.mapToScene(self.rect_inicio_redim.center())
            
            delta_inicio_cena = evento.scenePos() - self.centro_cena_inicio_redim
            self.dist_inicio_redim_abs = QPointF(abs(delta_inicio_cena.x()), abs(delta_inicio_cena.y()))
            
            evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento: Any) -> None:
        if hasattr(self, 'redimensionando') and self.redimensionando:
            mouse_cena = evento.scenePos()
            delta_cena = mouse_cena - self.centro_cena_inicio_redim
            
            diff_x = abs(delta_cena.x()) - self.dist_inicio_redim_abs.x()
            diff_y = abs(delta_cena.y()) - self.dist_inicio_redim_abs.y()
            
            diff = max(diff_x, diff_y)
            novo_lado = max(5, round(self.rect_inicio_redim.width() + 2 * diff))
            
            self.setRect(0, 0, novo_lado, novo_lado)
            novo_centro = self.rect().center()
            self.setTransformOriginPoint(novo_centro)
            self.setPos(self.centro_cena_inicio_redim - novo_centro)
            evento.accept()
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento: Any) -> None:
        self.redimensionando = False
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def itemChange(self, mudanca: Any, valor: Any) -> Any:
        if mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self) -> Dict[str, Any]:
        rect = self.rect()
        dados_box = {
            'x': int(round(self.x() + rect.width() / 2)),
            'y': int(round(self.y() + rect.height() / 2)),
            'lado': int(round(rect.width()))
        }
        self.pt_dict['quadrado'] = dados_box
        return self.pt_dict


class ItemBoundingCirculo(QGraphicsEllipseItem, BaseItemPOI):
    """Representa visualmente uma área de interesse circular no editor de mapas. Trata redimensionamento radial a partir do centro."""
    def __init__(self, pt_dict: Dict[str, Any], callback_deletar: Any, callback_mudanca: Optional[Any] = None, callback_converter: Optional[Any] = None) -> None:
        super().__init__()
        self.callback_deletar = callback_deletar
        self.callback_converter = callback_converter
        self.configurar_comum(pt_dict, callback_mudanca)
        
        circ = pt_dict.get('circulo', pt_dict.get('circulo', {}))
        r = circ['raio']
        self.setRect(-r, -r, 2 * r, 2 * r)
        self.setPos(circ['x'], circ['y'])
        
        self.setPen(self.pen_poi)
        self.setBrush(self.brush_poi)
        self.atualizar_pos_texto(-r, -r)
        self.inicializando = False

    def carregar_de_dict(self, pt_dict: Dict[str, Any]) -> None:
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        circ = self.pt_dict['circulo']
        r = circ['raio']
        self.setRect(-r, -r, 2 * r, 2 * r)
        self.setPos(circ['x'], circ['y'])
        self.atualizar_pos_texto(-r, -r)
        id_atual = self.pt_dict.get('id', '')
        label_atual = self.pt_dict.get('label', '')
        self.item_texto.setPlainText(str(id_atual if id_atual else label_atual))
        cast(Any, self).setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def contextMenuEvent(self, evento: Any) -> None:
        acoes_extras = []
        if getattr(self, 'callback_converter', None):
            acoes_extras.append(("Converter para Retângulo", lambda: self.callback_converter(self) if self.callback_converter else None if self.callback_converter else None))
        self.tratar_menu_contexto(evento, self.callback_deletar, acoes_extras)

    def mousePressEvent(self, evento: Any) -> None:
        if hasattr(self, 'clique_handler') and getattr(self, 'clique_handler') and hasattr(self, 'pt_dict'):
            if getattr(self, 'clique_handler')(getattr(self, 'pt_dict', {}).get('id')):
                evento.accept()
                return
        self._estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
        if evento.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.redimensionando = True
            self.pos_inicio_redim = evento.pos()
            self.rect_inicio_redim = self.rect()
            evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento: Any) -> None:
        if hasattr(self, 'redimensionando') and self.redimensionando:
            delta = evento.pos() - self.pos_inicio_redim
            r = max(5, round(self.rect_inicio_redim.width() / 2 + delta.x()))
            self.setRect(-r, -r, 2 * r, 2 * r)
            self.atualizar_pos_texto(-r, -r)
            evento.accept()
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento: Any) -> None:
        self.redimensionando = False
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def itemChange(self, mudanca: Any, valor: Any) -> Any:
        if mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self) -> Dict[str, Any]:
        r = int(round(self.rect().width() / 2))
        self.pt_dict['circulo'] = {
            'x': int(round(self.x())),
            'y': int(round(self.y())),
            'raio': r
        }
        return self.pt_dict


class AlcaVertice(QGraphicsEllipseItem):
    def __init__(self, indice: int, pai: Any) -> None:
        super().__init__(-7, -7, 14, 14, pai)
        self.indice = indice
        self.item_pai = pai
        cor = QColor(100, 100, 255) if isinstance(pai, ItemBoundingPoligono) else QColor(100, 255, 100)
        self.setBrush(QBrush(cor))
        self.setPen(QPen(QColor(0, 0, 0), 1))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def itemChange(self, mudanca: Any, valor: Any) -> Any:
        if mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                novo_valor = QPointF(round(valor.x()), round(valor.y()))
                self.item_pai.atualizar_ponto(self.indice, novo_valor)
                return novo_valor
            else:
                self.item_pai.atualizar_ponto(self.indice, valor)
        return super().itemChange(mudanca, valor)

    def mousePressEvent(self, evento: Any) -> None:
        if hasattr(self, 'clique_handler') and getattr(self, 'clique_handler') and hasattr(self, 'pt_dict'):
            if getattr(self, 'clique_handler')(getattr(self, 'pt_dict', {}).get('id')):
                evento.accept()
                return
        self.item_pai._estado_inicial = copy.deepcopy(self.item_pai.obter_dict_atualizado())
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento: Any) -> None:
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self.item_pai, getattr(self.item_pai, '_estado_inicial', None))


class ItemBoundingPoligono(QGraphicsPolygonItem, BaseItemPOI):
    """Representa visualmente uma área de interesse de polígono livre no editor de mapas. Permite adicionar e mover vértices (alças) individualmente."""
    def __init__(self, pt_dict: Dict[str, Any], callback_deletar: Any, callback_mudanca: Optional[Any] = None) -> None:
        super().__init__()
        self.callback_deletar = callback_deletar
        self.configurar_comum(pt_dict, callback_mudanca)
        
        coords = pt_dict.get('poligono', pt_dict.get('poligono', {}))['coordenadas']
        self.pontos = [QPointF(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
        
        self.setPolygon(QPolygonF(self.pontos))
        # Estilo azul para Área Livre
        self.pen_poi = QPen(QColor(100, 100, 255))
        self.pen_poi.setWidth(2)
        self.brush_poi = QBrush(QColor(100, 100, 255, 60))
        
        self.setPen(self.pen_poi)
        self.setBrush(self.brush_poi)
        
        self.redimensionando = False
        self.rotacionando = False
        
        self.alcas = []
        for i, p in enumerate(self.pontos):
            alca = AlcaVertice(i, self)
            alca.setPos(p)
            self.alcas.append(alca)
            
        self.atualizar_posicao_texto()
        self.inicializando = False

    def carregar_de_dict(self, pt_dict: Dict[str, Any]) -> None:
        self.inicializando = True
        self.pt_dict.update(pt_dict)
        coords = self.pt_dict['poligono']['coordenadas']
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
        cast(Any, self).setToolTip(f"ID: {id_atual} | Label: {label_atual}")
        self.inicializando = False

    def atualizar_ponto(self, indice: int, pos: QPointF) -> None:
        self.pontos[indice] = pos
        self.setPolygon(QPolygonF(self.pontos))
        self.atualizar_posicao_texto()
        self.marcar_alterado()

    def mousePressEvent(self, evento: Any) -> None:
        if hasattr(self, 'clique_handler') and getattr(self, 'clique_handler') and hasattr(self, 'pt_dict'):
            if getattr(self, 'clique_handler')(getattr(self, 'pt_dict', {}).get('id')):
                evento.accept()
                return
        self._estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
        super().mousePressEvent(evento)

    def mouseReleaseEvent(self, evento: Any) -> None:
        super().mouseReleaseEvent(evento)
        registrar_movimento_final(self, getattr(self, '_estado_inicial', None))

    def atualizar_posicao_texto(self) -> None:
        if not self.pontos: return
        min_x = min(p.x() for p in self.pontos)
        min_y = min(p.y() for p in self.pontos)
        self.atualizar_pos_texto(min_x, min_y)

    def itemChange(self, mudanca: Any, valor: Any) -> Any:
        if mudanca == QGraphicsPolygonItem.GraphicsItemChange.ItemPositionChange:
            if self.scene():
                return QPointF(round(valor.x()), round(valor.y()))
        elif mudanca == QGraphicsPolygonItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def contextMenuEvent(self, evento: Any) -> None:
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

    def obter_dict_atualizado(self) -> Dict[str, Any]:
        pos = self.pos()
        coords = []
        for p in self.pontos:
            coords.append(int(round(p.x() + pos.x())))
            coords.append(int(round(p.y() + pos.y())))
        self.pt_dict['poligono'] = {'coordenadas': coords}
        return self.pt_dict


class VisualizadorMapa(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        # Desabilita o drag nativo para implementarmos o customizado que não conflita com os POIs
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        
        self._arrastando_mapa: bool = False
        self._posicao_inicial_mouse: Optional[Any] = None
        self._posicao_inicial_scroll: Optional[Any] = None
        
        # Ativa o tracking de mouse para o cursor de mão aberta (hover)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def wheelEvent(self, evento: Any) -> None:
        if evento.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1/1.15, 1/1.15)

    def keyPressEvent(self, evento: Any) -> None:
        if evento.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            cena = self.scene()
            if cena:
                deletado = False
                for item in cena.selectedItems():
                    if isinstance(item, BaseItemPOI) and hasattr(item, 'callback_deletar') and item.callback_deletar:
                        item.callback_deletar(item)
                        deletado = True
                if deletado:
                    evento.accept()
                    return
        super().keyPressEvent(evento)

    def mousePressEvent(self, evento: Any) -> None:
        # Apenas arrasta se não houver item e for botão esquerdo, 
        # E se não estivermos no modo de desenho/conversão (que usam cross cursor)
        cursor_atual = self.cursor().shape()
        item = self.itemAt(evento.pos())
        
        if (not item or isinstance(item, QGraphicsPixmapItem)) and evento.button() == Qt.MouseButton.LeftButton and cursor_atual != Qt.CursorShape.CrossCursor:
            self._arrastando_mapa = True
            from PySide6.QtCore import QPoint
            self._posicao_inicial_mouse = evento.pos()
            self._posicao_inicial_scroll = QPoint(
                self.horizontalScrollBar().value(),
                self.verticalScrollBar().value()
            )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            evento.accept()
            return
            
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento: Any) -> None:
        cursor_atual = self.cursor().shape()
        
        if self._arrastando_mapa:
            if self._posicao_inicial_mouse is not None and self._posicao_inicial_scroll is not None:
                delta = evento.pos() - self._posicao_inicial_mouse
                self.horizontalScrollBar().setValue(self._posicao_inicial_scroll.x() - delta.x())
                self.verticalScrollBar().setValue(self._posicao_inicial_scroll.y() - delta.y())
            evento.accept()
            return
            
        super().mouseMoveEvent(evento)
        
        # Atualiza cursor de hover
        if cursor_atual != Qt.CursorShape.CrossCursor:
            item = self.itemAt(evento.pos())
            if not item or isinstance(item, QGraphicsPixmapItem):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, evento: Any) -> None:
        if self._arrastando_mapa and evento.button() == Qt.MouseButton.LeftButton:
            self._arrastando_mapa = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            evento.accept()
            return
            
        super().mouseReleaseEvent(evento)

    def leaveEvent(self, evento: Any) -> None:
        cursor_atual = self.cursor().shape()
        if cursor_atual != Qt.CursorShape.CrossCursor:
            self.unsetCursor()
        super().leaveEvent(evento)

class CenaDesenho(QGraphicsScene):
    def __init__(self, widget_editor: Any) -> None:
        super().__init__()
        self.widget_editor = widget_editor
        self.item_selecao: Optional[QGraphicsRectItem] = None
        # Alias para compatibilidade com testes antigos
        self.selection_item: Optional[QGraphicsRectItem] = None

    def mousePressEvent(self, evento: Any) -> None:
        if hasattr(self, 'clique_handler') and getattr(self, 'clique_handler') and hasattr(self, 'pt_dict'):
            if getattr(self, 'clique_handler')(getattr(self, 'pt_dict', {}).get('id')):
                evento.accept()
                return
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
                item_sel = QGraphicsRectItem()
                self.item_selecao = item_sel
                self.selection_item = item_sel # Alias
                item_sel.setPen(QPen(QColor(255, 165, 0), 2, Qt.PenStyle.DashLine))
                item_sel.setBrush(QBrush(QColor(255, 165, 0, 40)))
                self.addItem(item_sel)
                evento.accept()
        else:
            super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento: Any) -> None:
        if self.widget_editor.convert_mode and self.item_selecao:
            rect = QRectF(self.widget_editor.selection_origin, evento.scenePos()).normalized()
            self.item_selecao.setRect(rect)
            evento.accept()
        else:
            super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento: Any) -> None:
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
    alterado = Signal(bool)
    
    def __init__(self, mapas_controller: Optional[Any] = None, parent: Optional[QWidget] = None, standalone: bool = False, croqui_model: Optional[Any] = None, croqui_controller: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.standalone = standalone
        self.mapas_controller = mapas_controller
        self.croqui_model = croqui_model or (getattr(mapas_controller, "model", None))
        self.croqui_controller = croqui_controller or (getattr(mapas_controller, "croqui_controller", None))
        self.msg_mapa_proxy: Optional[Any] = None
        self.itens_poi: Dict[Any, Any] = {}
        self.dados_arquivos: Dict[Any, Any] = {}
        self.esta_modificado: bool = False
        self.bulk_base_dims: Dict[Any, Any] = {}
        self.bulk_tipo_ativo: Optional[str] = None
        self.modo_desenho: bool = False
        self.pontos_desenho: List[QPointF] = []
        self.item_desenho_temp: Optional[Any] = None
        self.alcas_desenho_temp: List[Any] = []
        self.path_desenho_temp: Optional[QGraphicsPathItem] = None
        self.modo_conversao: bool = False
        self.origem_selecao: Optional[QPointF] = None
        self.item_selecao_conversao: Optional[QGraphicsRectItem] = None
        self.dados_atuais: Optional[Dict[str, Any]] = None
        self.pico_idx: Optional[int] = -1
        self.sg_idx: Optional[int] = -1
        self.mapa_idx: Optional[int] = -1
        self.s_idx: Optional[int] = -1
        self.item_hover_camera_overlay: Optional[Any] = None
        self.item_camera_overlay: Optional[Any] = None
        self.referencia_linkagem_ativa: Optional[Any] = None
        self.idx_referencia_linkagem: int = -1

        self._setup_ui()
        
        if self.croqui_model and hasattr(self.croqui_model, "imagem_alterada"):
            self.croqui_model.imagem_alterada.connect(self._on_imagem_alterada)
            self._model_imagem_conectado = self.croqui_model
        else:
            self._model_imagem_conectado = None
        self._model_repeated_conectado = None
        
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
    def convert_mode(self) -> bool: return self.modo_conversao
    @convert_mode.setter
    def convert_mode(self, v: bool) -> None: self.modo_conversao = v
    
    @property
    def drawing_mode(self) -> bool: return self.modo_desenho
    @drawing_mode.setter
    def drawing_mode(self, v: bool) -> None: self.modo_desenho = v
    
    @property
    def selection_origin(self) -> Optional[QPointF]: return self.origem_selecao
    @selection_origin.setter
    def selection_origin(self, v: Optional[QPointF]) -> None: self.origem_selecao = v

    # Aliases de compatibilidade para suporte a scripts/editar_mapas_test.py
    def add_drawing_point(self, pos: QPointF) -> None: 
        return self.adicionar_ponto_desenho(pos)
    
    def finish_conversion_area(self, rect: QRectF) -> None:
        return self.finalizar_area_conversao(rect)

    def _setup_ui(self) -> None:
        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background: transparent;
            }
        """)
        
        # Painel Esquerdo (Sidebar de Mapas)
        self.widget_esquerdo = QWidget()
        self.widget_esquerdo.setMinimumWidth(260)
        self.widget_esquerdo.setStyleSheet("background-color: #f8f9fa; border-right: 1px solid #dee2e6;")
        layout_esquerdo = QVBoxLayout(self.widget_esquerdo)
        layout_esquerdo.setContentsMargins(8, 8, 8, 8)
        layout_esquerdo.setSpacing(4)
        
        self.label_titulo_arquivos = QLabel("Arquivos de Mapa")
        self.label_titulo_arquivos.setStyleSheet("font-weight: bold; color: #444; font-size: 13px;")
        layout_esquerdo.addWidget(self.label_titulo_arquivos)

        self.list_widget = QListWidget()
        from PySide6.QtWidgets import QSizePolicy
        self.list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout_esquerdo.addWidget(self.list_widget, stretch=1)
        
        from editor.views.estilo import Icones

        # Linha de criação rápida: Círculo e Retângulo lado a lado (cabem confortavelmente em 2 colunas)
        layout_pois_dupla = QHBoxLayout()
        layout_pois_dupla.setSpacing(4)
        
        self.btn_add_circ = QPushButton(" Círculo")
        self.btn_add_circ.setIcon(Icones.obter("dados"))
        self.btn_add_circ.clicked.connect(lambda: self.adicionar_poi('circulo'))
        layout_pois_dupla.addWidget(self.btn_add_circ)

        self.btn_add_box = QPushButton(" Retângulo")
        self.btn_add_box.setIcon(Icones.obter("imagens"))
        self.btn_add_box.clicked.connect(lambda: self.adicionar_poi('retangulo'))
        layout_pois_dupla.addWidget(self.btn_add_box)
        layout_esquerdo.addLayout(layout_pois_dupla)

        # Polígono em largura total
        self.btn_add_poligono = QPushButton(" Novo Polígono")
        self.btn_add_poligono.setIcon(Icones.obter("mapas"))
        self.btn_add_poligono.clicked.connect(lambda: self.adicionar_poi('poligono'))
        layout_esquerdo.addWidget(self.btn_add_poligono)

        self.btn_converter = QPushButton(" Retângulo -> Círculo")
        self.btn_converter.setToolTip("Converte Retângulos em Círculos. Se já estiver no modo, clique novamente para converter TODOS os retângulos.")
        self.btn_converter.clicked.connect(self.alternar_modo_conversao)
        layout_esquerdo.addWidget(self.btn_converter)

        self.btn_substituir_imagem = QPushButton(" Substituir Imagem...")
        self.btn_substituir_imagem.setIcon(Icones.obter("imagens"))
        self.btn_substituir_imagem.clicked.connect(self.substituir_imagem_mapa)
        layout_esquerdo.addWidget(self.btn_substituir_imagem)

        self.btn_abrir_editor_imagens = QPushButton(" Abrir no Editor de Imagens")
        self.btn_abrir_editor_imagens.setIcon(Icones.obter("imagens"))
        self.btn_abrir_editor_imagens.clicked.connect(self.abrir_no_editor_imagens)
        layout_esquerdo.addWidget(self.btn_abrir_editor_imagens)

        layout_bulk = QVBoxLayout()
        layout_bulk.setSpacing(3)
        label_bulk = QLabel("Redimensionamento:")
        label_bulk.setStyleSheet("font-weight: bold; color: #555; font-size: 11px;")
        layout_bulk.addWidget(label_bulk)
        
        # Sliders de redimensionamento em massa em linhas horizontais compactas
        linha_circ = QHBoxLayout()
        lbl_circ = QLabel("Círculos:")
        lbl_circ.setFixedWidth(65)
        self.slider_circ = QSlider(Qt.Orientation.Horizontal)
        self.slider_circ.setRange(-50, 50)
        self.slider_circ.setValue(0)
        self.slider_circ.sliderPressed.connect(lambda: self.ao_pressionar_slider_bulk('circulo'))
        self.slider_circ.valueChanged.connect(lambda v: self.ao_mover_slider_bulk(v, 'circulo'))
        self.slider_circ.sliderReleased.connect(lambda: self.ao_soltar_slider_bulk('circulo'))
        self.label_circ = QLabel("0%")
        self.label_circ.setFixedWidth(32)
        self.label_circ.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        linha_circ.addWidget(lbl_circ)
        linha_circ.addWidget(self.slider_circ)
        linha_circ.addWidget(self.label_circ)
        layout_bulk.addLayout(linha_circ)

        linha_box = QHBoxLayout()
        lbl_box = QLabel("Retângulos:")
        lbl_box.setFixedWidth(65)
        self.slider_box = QSlider(Qt.Orientation.Horizontal)
        self.slider_box.setRange(-50, 50)
        self.slider_box.setValue(0)
        self.slider_box.sliderPressed.connect(lambda: self.ao_pressionar_slider_bulk('retangulo'))
        self.slider_box.valueChanged.connect(lambda v: self.ao_mover_slider_bulk(v, 'retangulo'))
        self.slider_box.sliderReleased.connect(lambda: self.ao_soltar_slider_bulk('retangulo'))
        self.label_box = QLabel("0%")
        self.label_box.setFixedWidth(32)
        self.label_box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        linha_box.addWidget(lbl_box)
        linha_box.addWidget(self.slider_box)
        linha_box.addWidget(self.label_box)
        layout_bulk.addLayout(linha_box)
        
        linha_quad = QHBoxLayout()
        lbl_quad = QLabel("Quadrados:")
        lbl_quad.setFixedWidth(65)
        self.slider_quad = QSlider(Qt.Orientation.Horizontal)
        self.slider_quad.setRange(-50, 50)
        self.slider_quad.setValue(0)
        self.slider_quad.sliderPressed.connect(lambda: self.ao_pressionar_slider_bulk('quadrado'))
        self.slider_quad.valueChanged.connect(lambda v: self.ao_mover_slider_bulk(v, 'quadrado'))
        self.slider_quad.sliderReleased.connect(lambda: self.ao_soltar_slider_bulk('quadrado'))
        self.label_quad = QLabel("0%")
        self.label_quad.setFixedWidth(32)
        self.label_quad.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        linha_quad.addWidget(lbl_quad)
        linha_quad.addWidget(self.slider_quad)
        linha_quad.addWidget(self.label_quad)
        layout_bulk.addLayout(linha_quad)
        
        layout_esquerdo.addLayout(layout_bulk)

        # Painel Direito (Visualizador)
        widget_direito = QWidget()
        layout_direito = QVBoxLayout(widget_direito)
        layout_direito.setContentsMargins(5, 5, 5, 5)

        self.visualizador = VisualizadorMapa()
        self.visualizador.setStyleSheet("background-color: #e9ecef; border: 1px solid #dee2e6; border-radius: 4px;")
        
        self.label_modo = QLabel("MODO DESENHO - Clique para pontos, feche no primeiro. Dir: desfazer.")
        self.label_modo.setStyleSheet("color: white; background-color: #dc3545; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.label_modo.setVisible(False)
        self.label_modo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_direito.addWidget(self.label_modo)

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
        
        self.splitter.addWidget(self.widget_esquerdo)
        self.splitter.addWidget(widget_direito)
        
        layout_principal.addWidget(self.splitter)
        from editor.views.widget_painel_referencias import PainelReferencias
        self.painel_referencias = PainelReferencias(self.mapas_controller)
        self.splitter.addWidget(self.painel_referencias)
        self.splitter.setSizes([260, 680, 260])
        self.painel_referencias.destacar_pois.connect(self.destacar_pois_temporariamente)
        self.painel_referencias.remover_destaque_pois.connect(self.remover_destaque_pois)
        self.painel_referencias.iniciar_modo_linkagem.connect(self.iniciar_modo_linkagem)
        self.painel_referencias.parar_modo_linkagem.connect(self.parar_modo_linkagem)
        self.painel_referencias.iniciar_modo_camera.connect(self.iniciar_modo_camera)
        self.painel_referencias.parar_modo_camera.connect(self.parar_modo_camera)
        self.painel_referencias.salvar_modo_camera.connect(self.salvar_ajuste_camera)
        self.painel_referencias.remover_ajuste_camera.connect(self.remover_ajuste_camera)

    def configurar_lista_mapas(self) -> None:
        """Conecta o modelo reativo e preenche a lista."""
        if not self.mapas_controller or not self.mapas_controller.model:
            return
            
        model = self.mapas_controller.model
        model.dado_alterado.connect(self._atualizar_lista_mapas)
        model.repeated_adicionado.connect(self._atualizar_lista_mapas)
        model.repeated_removido.connect(self._atualizar_lista_mapas)
        
        self._atualizar_lista_mapas()
        
    def _atualizar_lista_mapas(self, *args: Any) -> None:
        """Reconstrói a lista lendo do CroquiModel."""
        if len(args) >= 2 and args[1] in ('referencias', 'pontos_de_interesse'):
            return
            
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        from pathlib import Path
        
        # Salva seleção atual
        current_item = self.list_widget.currentItem()
        selected_data = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None

        self.list_widget.clear()
        if not self.mapas_controller or not self.mapas_controller.model: return
        
        croqui_msg = self.mapas_controller.model.obter_croqui_readonly()
        
        for p_idx, pico in enumerate(croqui_msg.picos):
            # Mapas Gerais do Pico
            if pico.HasField('mapas_gerais'):
                for m_idx, mapa in enumerate(pico.mapas_gerais.conteudo.mapas):
                    if not mapa.caminho_imagem_mapa: continue
                    nome = Path(mapa.caminho_imagem_mapa).name
                    item = QListWidgetItem(nome)
                    item.setData(Qt.ItemDataRole.UserRole, ('mapa_geral', p_idx, -1, m_idx))
                    self.list_widget.addItem(item)
                    
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
        elif hasattr(self, 'pico_idx') and self.pico_idx is not None and self.pico_idx >= 0 and self.sg_idx is not None and self.sg_idx >= 0 and self.mapa_idx is not None and self.mapa_idx >= 0 and getattr(self, 's_idx', -1) is not None:
            self.list_widget.blockSignals(True)
            s_idx = getattr(self, 's_idx', -1)
            self.selecionar_mapa_por_indices(self.pico_idx, self.sg_idx, self.mapa_idx, s_idx if s_idx is not None else -1)
            self.list_widget.blockSignals(False)
                    
    def _on_mapa_selecionado(self) -> None:
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
            if tipo == 'mapa_geral':
                mapa = croqui_msg.picos[p_idx].mapas_gerais.conteudo.mapas[m_idx]
            elif tipo == 'grupo':
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

    def selecionar_mapa_por_indices(self, pico_idx: Optional[int] = None, grupo_idx: Optional[int] = None, mapa_idx: Optional[int] = None, s_idx: Optional[int] = -1) -> bool:
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

    def set_mapa_atual(self, msg_mapa_proxy: Any, pico_idx: Optional[int] = -1, grupo_idx: Optional[int] = -1, mapa_idx: Optional[int] = -1, s_idx: Optional[int] = -1, tipo: str = 'setor') -> None:
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
            if hasattr(self.mapas_controller, 'set_contexto') and pico_idx is not None and pico_idx >= 0 and mapa_idx is not None and mapa_idx >= 0:
                if tipo == 'grupo':
                    path = f"page:mapas/node:Croqui/expando:picos/item:{pico_idx}/expando:setores_ou_grupos/item:{grupo_idx}/expando:grupo/expando:mapas/item:{mapa_idx}"
                elif tipo == 'subsetor':
                    path = f"page:mapas/node:Croqui/expando:picos/item:{pico_idx}/expando:setores_ou_grupos/item:{grupo_idx}/expando:grupo/expando:setores/item:{s_idx}/expando:setor/expando:mapas/item:{mapa_idx}"
                else:
                    path = f"page:mapas/node:Croqui/expando:picos/item:{pico_idx}/expando:setores_ou_grupos/item:{grupo_idx}/expando:setor/expando:mapas/item:{mapa_idx}"
                self.mapas_controller.set_contexto(path)
                
            model = self.mapas_controller.model
            if model and getattr(self, "_model_repeated_conectado", None) is not model:
                if getattr(self, "_model_repeated_conectado", None) is not None:
                    try:
                        cast(Any, self._model_repeated_conectado).repeated_item_alterado.disconnect(self._on_repeated_item_alterado)
                        cast(Any, self._model_repeated_conectado).repeated_adicionado.disconnect(self._on_repeated_adicionado)
                        cast(Any, self._model_repeated_conectado).repeated_removido.disconnect(self._on_repeated_removido)
                    except Exception:
                        pass
                if hasattr(model, "repeated_item_alterado"):
                    cast(Any, model).repeated_item_alterado.connect(self._on_repeated_item_alterado)
                if hasattr(model, "repeated_adicionado"):
                    cast(Any, model).repeated_adicionado.connect(self._on_repeated_adicionado)
                if hasattr(model, "repeated_removido"):
                    cast(Any, model).repeated_removido.connect(self._on_repeated_removido)
                self._model_repeated_conectado = model
            
        self.painel_referencias.carregar_mapa(msg_mapa_proxy)
        self._renderizar_mapa(reset_zoom=True)

    def carregar_mapa(self, msg_mapa_proxy: Any, reset_zoom: bool = True) -> None:
        """Carrega e renderiza o mapa a partir do objeto ou proxy de mapa."""
        self.msg_mapa_proxy = msg_mapa_proxy
        if not self.dados_atuais:
            self.dados_atuais = {
                'cena': QGraphicsScene(self),
                'itens_bb': []
            }
        self.painel_referencias.carregar_mapa(msg_mapa_proxy)
        self._renderizar_mapa(reset_zoom=reset_zoom)
        
    def _renderizar_mapa(self, reset_zoom: bool = True) -> None:
        """Lê a mensagem Protobuf e renderiza a cena inteira."""
        if not self.msg_mapa_proxy:
            self.visualizador.setScene(None)
            self.label_placeholder.show()
            return
            
        old_transform = self.visualizador.transform()
        old_h_scroll = self.visualizador.horizontalScrollBar().value()
        old_v_scroll = self.visualizador.verticalScrollBar().value()
        
        self.label_placeholder.hide()
        if not self.dados_atuais:
            return
        dados = self.dados_atuais
        cena = dados['cena']
        cena.clear()
        self.itens_poi.clear()
        dados['itens_bb'] = []
        
        if hasattr(self, 'modo_linkagem') and self.modo_linkagem:
            self._aplicar_highlight_linkagem()
        if hasattr(self, 'modo_camera') and self.modo_camera:
            self.destacar_pois_temporariamente(self.referencia_camera_ativa)
        
        img_bytes = None
        caminho_rel = getattr(self.msg_mapa_proxy, "caminho_imagem_mapa", None)
        if self.croqui_model and caminho_rel:
            img_bytes = self.croqui_model.obter_bytes_imagem(caminho_rel)

        if img_bytes and isinstance(img_bytes, (bytes, bytearray, memoryview)):
            pixmap = QPixmap()
            if pixmap.loadFromData(img_bytes):
                item_img = cena.addPixmap(pixmap)
                item_img.setZValue(-100)
        else:
            img_path = None
            if self.mapas_controller:
                img_path = self.mapas_controller.obter_caminho_imagem_mapa(self.msg_mapa_proxy)
            elif self.croqui_model and hasattr(self.croqui_model, "_caminho_db_atual") and self.croqui_model._caminho_db_atual and caminho_rel:
                img_path = self.croqui_model._caminho_db_atual / caminho_rel
                
            if img_path and str(img_path) and os.path.exists(str(img_path)):
                pixmap = QPixmap(str(img_path))
                item_img = cena.addPixmap(pixmap)
                item_img.setZValue(-100)
            
        for i, poi in enumerate(self.msg_mapa_proxy.pontos_de_interesse):
            self._adicionar_item_cena(poi, i, cena)
            
        # Define um sceneRect enorme para permitir navegação livre (panning) mesmo
        # se o mapa/cena for menor que o viewport. O QtGraphicsView só habilita
        # scrollbars se o sceneRect exceder o viewport.
        cena.setSceneRect(-50000, -50000, 100000, 100000)
        self.visualizador.setScene(cena)
        
        if reset_zoom:
            # Em vez de cena.sceneRect() (que agora é enorme), ajustamos
            # o zoom baseado na área ocupada pelos itens (a imagem do mapa e POIs).
            rect_itens = cena.itemsBoundingRect()
            if rect_itens.isNull():
                rect_itens = QRectF(0, 0, 800, 600)
            self.visualizador.fitInView(rect_itens, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.visualizador.setTransform(old_transform)
            self.visualizador.horizontalScrollBar().setValue(old_h_scroll)
            self.visualizador.verticalScrollBar().setValue(old_v_scroll)

        # Sincroniza a seleção na lista se os índices foram passados
        if getattr(self, 'pico_idx', -1) >= 0 and getattr(self, 'sg_idx', -1) >= 0 and getattr(self, 'mapa_idx', -1) >= 0:
            self.list_widget.blockSignals(True)
            s_idx = getattr(self, 's_idx', -1)
            self.selecionar_mapa_por_indices(self.pico_idx, self.sg_idx, self.mapa_idx, s_idx if s_idx is not None else -1)
            self.list_widget.blockSignals(False)
    def _adicionar_item_cena(self, poi: Any, index: int, cena: Any) -> None:
        # Transforma mensagem protobuf em dicionário genérico para os itens gráficos legacy
        from google.protobuf.json_format import MessageToDict
        pt_dict = MessageToDict(poi, preserving_proto_field_name=True)
        
        def cb_deletar(item: Any) -> None:
            self.deletar_item_poi(item)
            
        def cb_converter(item: Any) -> None:
            self.converter_item_para_circulo(item)
            
        def cb_converter_retangulo(item: Any) -> None:
            self.converter_item_para_retangulo(item)
            
        item_visual: Optional[Any] = None
        if poi.HasField('retangulo'):
            item_visual = ItemBoundingRetangulo(pt_dict, cb_deletar, callback_converter=cb_converter)
        elif poi.HasField('circulo'):
            item_visual = ItemBoundingCirculo(pt_dict, cb_deletar, callback_converter=cb_converter_retangulo)
        elif poi.HasField('poligono'):
            item_visual = ItemBoundingPoligono(pt_dict, cb_deletar)
            
        if item_visual:
            item_visual.set_clique_handler(self.tratar_clique_poi_linkagem)
            cena.addItem(item_visual)
            self.itens_poi[index] = item_visual
            if self.dados_atuais:
                self.dados_atuais['itens_bb'].append(item_visual)

    def substituir_imagem_mapa(self) -> None:
        """Abre diálogo para substituir a imagem de fundo do mapa atual com pré-processamento WebP."""
        if not self.msg_mapa_proxy:
            return
        caminho_rel = getattr(self.msg_mapa_proxy, "caminho_imagem_mapa", "")
        if not caminho_rel:
            return

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Substituir Imagem do Mapa",
            "",
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif)",
        )
        if not arquivo:
            return

        from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp
        from pathlib import Path
        try:
            bytes_originais = Path(arquivo).read_bytes()
            bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(bytes_originais, quality=90)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao processar nova imagem: {e}")
            return

        nome_mapa = Path(caminho_rel).name
        contexto_mapa = f"page:mapas/file:{nome_mapa}"
        if self.croqui_controller:
            self.croqui_controller.set_contexto(contexto_mapa)
            self.croqui_controller.substituir_imagem(caminho_rel, bytes_webp, context_path=contexto_mapa)
        elif self.mapas_controller:
            self.mapas_controller.set_contexto(contexto_mapa)
            self.mapas_controller.substituir_imagem(caminho_rel, bytes_webp, context_path=contexto_mapa)
        elif self.croqui_model:
            self.croqui_model.definir_imagem_memoria(caminho_rel, bytes_webp)

        self.carregar_mapa(self.msg_mapa_proxy, reset_zoom=False)

    def abrir_no_editor_imagens(self) -> None:
        """Abre e foca a imagem do mapa atual no Editor de Imagens."""
        if not self.msg_mapa_proxy:
            return
        caminho_rel = getattr(self.msg_mapa_proxy, "caminho_imagem_mapa", "")
        if not caminho_rel:
            return

        from pathlib import Path
        nome_arquivo = Path(caminho_rel).name
        contexto_uri = f"page:imagens/file:{nome_arquivo}"

        if self.croqui_controller:
            self.croqui_controller.set_contexto(contexto_uri)
        if self.croqui_model and hasattr(self.croqui_model, "notificar_foco_requisitado"):
            self.croqui_model.notificar_foco_requisitado(contexto_uri)
        elif self.croqui_model and hasattr(self.croqui_model, "foco_requisitado"):
            self.croqui_model.foco_requisitado.emit(contexto_uri)

    def _on_imagem_alterada(self, caminho_relativo: str) -> None:
        """Recarrega a cena do mapa quando a imagem correspondente for alterada em outra área."""
        if self.msg_mapa_proxy and hasattr(self.msg_mapa_proxy, "caminho_imagem_mapa"):
            from pathlib import Path
            caminho_atual = str(self.msg_mapa_proxy.caminho_imagem_mapa).replace("\\", "/")
            caminho_alt = str(caminho_relativo).replace("\\", "/")
            if caminho_atual == caminho_alt or Path(caminho_atual).name == Path(caminho_alt).name:
                self.carregar_mapa(self.msg_mapa_proxy, reset_zoom=False)

    def adicionar_poi(self, tipo: str) -> None:
        if not self.dados_atuais or not self.mapas_controller: return
        
        if tipo == 'poligono':
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
            
            if tipo == 'circulo':
                novo_poi.circulo.x = int(cx)
                novo_poi.circulo.y = int(cy)
                novo_poi.circulo.raio = 40
            elif tipo == 'retangulo':
                novo_poi.retangulo.x = int(cx-40)
                novo_poi.retangulo.y = int(cy-40)
                novo_poi.retangulo.comprimento = 80
                novo_poi.retangulo.largura = 80
            
            self.mapas_controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)

    def deletar_item_poi(self, item: Any) -> None:
        if not self.mapas_controller: return
        
        idx_poi = -1
        for idx, gui_item in self.itens_poi.items():
            if gui_item == item:
                idx_poi = idx
                break
                
        if idx_poi != -1:
            self.mapas_controller.deletar_poi(self.msg_mapa_proxy, idx_poi)

    def converter_item_para_circulo(self, item: Any) -> None:
        if not self.mapas_controller: return
        idx_poi = -1
        for idx, gui_item in self.itens_poi.items():
            if gui_item == item:
                idx_poi = idx
                break
        if idx_poi != -1:
            self.mapas_controller.converter_boxes_para_circulos(self.msg_mapa_proxy, [idx_poi])

    def converter_item_para_retangulo(self, item: Any) -> None:
        if not self.mapas_controller: return
        idx_poi = -1
        for idx, gui_item in self.itens_poi.items():
            if gui_item == item:
                idx_poi = idx
                break
        if idx_poi != -1:
            self.mapas_controller.converter_circulos_para_boxes(self.msg_mapa_proxy, [idx_poi])

    def marcar_modificado(self) -> None:
        if not self.esta_modificado:
            self.esta_modificado = True
            self.alterado.emit(True)

    # Lógica de Desenho e Conversão
    def iniciar_modo_desenho(self, dados: Any) -> None:
        self.modo_desenho = True
        self.pontos_desenho = []
        self.dados_atuais = dados
        self.label_modo.setText("MODO DESENHO - Clique para pontos, feche no primeiro. Dir: desfazer.")
        self.label_modo.setStyleSheet("color: white; background-color: #dc3545; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.label_modo.setVisible(True)
        # self.visualizador.setDragMode(QGraphicsView.DragMode.NoDrag) # Substituído por controle customizado
        self.visualizador.setCursor(Qt.CursorShape.CrossCursor)
        self.item_desenho_temp = QGraphicsPathItem()
        self.item_desenho_temp.setPen(QPen(QColor(255, 100, 100), 2))
        self.item_desenho_temp.setBrush(QBrush(QColor(255, 100, 100, 50)))
        dados['cena'].addItem(self.item_desenho_temp)
        self.alcas_desenho_temp = []

    def adicionar_ponto_desenho(self, pos: QPointF) -> None:
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
        if self.item_desenho_temp is not None: self.item_desenho_temp.setPath(path)
        
        alca = QGraphicsEllipseItem(-4, -4, 8, 8)
        alca.setPos(pos)
        alca.setPen(QPen(QColor(255, 100, 100)))
        alca.setBrush(QBrush(QColor(255, 255, 255)))
        alca.setZValue(1000)
        if self.dados_atuais: self.dados_atuais['cena'].addItem(alca)
        self.alcas_desenho_temp.append(alca)

    def desfazer_ponto_desenho(self) -> None:
        if self.pontos_desenho:
            self.pontos_desenho.pop()
            alca = self.alcas_desenho_temp.pop()
            if self.dados_atuais: self.dados_atuais['cena'].removeItem(alca)
            if not self.pontos_desenho:
                self.cancelar_modo_desenho()
            else:
                path = QPainterPath()
                path.moveTo(self.pontos_desenho[0])
                for p in self.pontos_desenho[1:]:
                    path.lineTo(p)
                if self.item_desenho_temp is not None: self.item_desenho_temp.setPath(path)

    def finalizar_modo_desenho(self) -> None:
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
                    novo_poi.poligono.coordenadas.append(int(p.x()))
                    novo_poi.poligono.coordenadas.append(int(p.y()))
                
                if self.mapas_controller:
                    self.mapas_controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)

        self.cancelar_modo_desenho()

    def cancelar_modo_desenho(self) -> None:
        self.modo_desenho = False
        self.label_modo.setVisible(False)
        # self.visualizador.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Substituído por controle customizado
        self.visualizador.unsetCursor()
        if self.item_desenho_temp and self.dados_atuais:
            self.dados_atuais['cena'].removeItem(self.item_desenho_temp)
            self.item_desenho_temp = None
        for alca in self.alcas_desenho_temp:
            if self.dados_atuais: self.dados_atuais['cena'].removeItem(alca)
        self.alcas_desenho_temp = []
        self.pontos_desenho = []


    def alternar_modo_conversao(self) -> None:
        if self.modo_desenho: return
        if self.modo_conversao:
            if self.dados_atuais and self.mapas_controller:
                indices = []
                for idx_poi, gui_item in list(self.itens_poi.items()):
                    if isinstance(gui_item, ItemBoundingRetangulo):
                        indices.append(idx_poi)
                if indices:
                    self.mapas_controller.converter_boxes_para_circulos(self.msg_mapa_proxy, indices)
            self.parar_modo_conversao()
        else:
            self.iniciar_modo_conversao()

    def iniciar_modo_conversao(self) -> None:
        self.modo_conversao = True
        self.label_conversao.setVisible(True)
        self.btn_converter.setStyleSheet("background-color: orange; font-weight: bold;")
        # self.visualizador.setDragMode(QGraphicsView.DragMode.NoDrag) # Substituído por controle customizado
        self.visualizador.setCursor(Qt.CursorShape.CrossCursor)

    def parar_modo_conversao(self) -> None:
        self.modo_conversao = False
        self.label_conversao.setVisible(False)
        self.btn_converter.setStyleSheet("")
        # self.visualizador.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Substituído por controle customizado
        self.visualizador.unsetCursor()
        self.origem_selecao = None

    def finalizar_area_conversao(self, rect: QRectF) -> None:
        if not self.dados_atuais or not self.mapas_controller: return
        a_converter = []
        for idx_poi, gui_item in list(self.itens_poi.items()):
            if isinstance(gui_item, ItemBoundingRetangulo):
                if rect.contains(gui_item.mapToScene(gui_item.rect().center())):
                    a_converter.append(idx_poi)
        if a_converter:
            self.mapas_controller.converter_boxes_para_circulos(self.msg_mapa_proxy, a_converter)
        self.parar_modo_conversao()

    # Bulk Sliders logic
    def ao_pressionar_slider_bulk(self, tipo: str) -> None:
        if not self.dados_atuais: return
        self.bulk_base_dims = {}
        from copy import deepcopy
        for idx, gui_item in self.itens_poi.items():
            if tipo == 'circulo' and isinstance(gui_item, ItemBoundingCirculo):
                self.bulk_base_dims[id(gui_item)] = {
                    'r': gui_item.rect().width() / 2,
                    'estado_inicial': deepcopy(gui_item.obter_dict_atualizado()),
                    'idx': idx
                }
            elif tipo == 'quadrado' and isinstance(gui_item, ItemBoundingQuadrado):
                self.bulk_base_dims[id(gui_item)] = {
                    'lado': gui_item.rect().width(),
                    'estado_inicial': deepcopy(gui_item.obter_dict_atualizado()),
                    'idx': idx
                }
            elif tipo == 'retangulo' and isinstance(gui_item, ItemBoundingRetangulo):
                self.bulk_base_dims[id(gui_item)] = {
                    'w': gui_item.rect().width(),
                    'h': gui_item.rect().height(),
                    'estado_inicial': deepcopy(gui_item.obter_dict_atualizado()),
                    'idx': idx
                }

    def ao_mover_slider_bulk(self, valor: int, tipo: str) -> None:
        if not self.bulk_base_dims: return
        fator = 1.0 + valor / 100.0
        mudou = False
        if tipo == 'circulo':
            self.label_circ.setText(f"{valor:+}%")
            for gui_item in self.itens_poi.values():
                if isinstance(gui_item, ItemBoundingCirculo) and id(gui_item) in self.bulk_base_dims:
                    base_r = self.bulk_base_dims[id(gui_item)]['r']
                    novo_r = max(2, base_r * fator)
                    gui_item.setRect(-novo_r, -novo_r, 2 * novo_r, 2 * novo_r)
                    gui_item.atualizar_pos_texto(-novo_r, -novo_r)
                    mudou = True
        elif tipo == 'quadrado':
            self.label_quad.setText(f"{valor:+}%")
            for gui_item in self.itens_poi.values():
                if isinstance(gui_item, ItemBoundingQuadrado) and id(gui_item) in self.bulk_base_dims:
                    base_lado = self.bulk_base_dims[id(gui_item)]['lado']
                    novo_lado = max(4, base_lado * fator)
                    centro_cena_antigo = gui_item.mapToScene(gui_item.rect().center())
                    gui_item.setRect(0, 0, novo_lado, novo_lado)
                    gui_item.setTransformOriginPoint(gui_item.rect().center())
                    gui_item.setPos(centro_cena_antigo - gui_item.rect().center())
                    mudou = True
        elif tipo == 'retangulo':
            self.label_box.setText(f"{valor:+}%")
            for gui_item in self.itens_poi.values():
                if isinstance(gui_item, ItemBoundingRetangulo) and id(gui_item) in self.bulk_base_dims:
                    base_w = self.bulk_base_dims[id(gui_item)]['w']
                    base_h = self.bulk_base_dims[id(gui_item)]['h']
                    novo_w = max(4, base_w * fator)
                    novo_h = max(4, base_h * fator)
                    centro_cena_antigo = gui_item.mapToScene(gui_item.rect().center())
                    gui_item.setRect(0, 0, novo_w, novo_h)
                    gui_item.setTransformOriginPoint(gui_item.rect().center())
                    gui_item.setPos(centro_cena_antigo - gui_item.rect().center())
                    mudou = True

    def ao_soltar_slider_bulk(self, tipo: str) -> None:
        if self.bulk_base_dims and self.mapas_controller:
            # Dispatch changes to controller
            from aresta_api.proto.generated import croqui_pb2
            from google.protobuf.json_format import ParseDict
            
            # Cria nome da ação
            nome_acao = "Redimensionar Círculos" if tipo == 'circulo' else ("Redimensionar Quadrados" if tipo == 'quadrado' else "Redimensionar Retângulos")
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
        if tipo == 'circulo':
            self.slider_circ.blockSignals(True); self.slider_circ.setValue(0); self.slider_circ.blockSignals(False)
            self.label_circ.setText("0%")
        elif tipo == 'retangulo':
            self.slider_box.blockSignals(True); self.slider_box.setValue(0); self.slider_box.blockSignals(False)
            self.slider_quad.blockSignals(True); self.slider_quad.setValue(0); self.slider_quad.blockSignals(False)
            self.label_box.setText("0%")

    def _on_repeated_item_alterado(self, msg: Any, campo_nome: str, index: int) -> None:
        if self.msg_mapa_proxy == msg and campo_nome == 'referencias':
            self.painel_referencias.carregar_mapa(msg)
        if self.msg_mapa_proxy == msg and campo_nome == 'pontos_de_interesse':
            poi = msg.pontos_de_interesse[index]
            item_existente = self.itens_poi.get(index)
            if item_existente:
                from google.protobuf.json_format import MessageToDict
                pt_dict = MessageToDict(poi, preserving_proto_field_name=True)
                # Verifica se o tipo da Box foi convertido (ex: box -> circular)
                mesmo_tipo = False
                if poi.HasField('retangulo') and isinstance(item_existente, ItemBoundingRetangulo):
                    mesmo_tipo = True
                elif poi.HasField('quadrado') and isinstance(item_existente, ItemBoundingQuadrado):
                    item_existente.carregar_de_dict(pt_dict)
                elif poi.HasField('circulo') and isinstance(item_existente, ItemBoundingCirculo):
                    mesmo_tipo = True
                elif poi.HasField('poligono') and isinstance(item_existente, ItemBoundingPoligono):
                    mesmo_tipo = True
                    
                if mesmo_tipo:
                    item_existente.carregar_de_dict(pt_dict)
                else:
                    cena = self.visualizador.scene()
                    if cena:
                        cena.removeItem(item_existente)
                        if self.dados_atuais and 'itens_bb' in self.dados_atuais:
                            if item_existente in self.dados_atuais['itens_bb']:
                                self.dados_atuais['itens_bb'].remove(item_existente)
                        self._adicionar_item_cena(poi, index, cena)

    def _on_repeated_adicionado(self, msg: Any, campo_nome: str, index: int) -> None:
        if self.msg_mapa_proxy == msg and campo_nome == 'referencias':
            self.painel_referencias.carregar_mapa(msg)
        if self.msg_mapa_proxy == msg and campo_nome == 'pontos_de_interesse':
            poi = msg.pontos_de_interesse[index]
            cena = self.visualizador.scene()
            if cena:
                nova_dict = {}
                for k, v in self.itens_poi.items():
                    if k >= index:
                        nova_dict[k + 1] = v
                    else:
                        nova_dict[k] = v
                self.itens_poi = nova_dict
                
                self._adicionar_item_cena(poi, index, cena)

    def _on_repeated_removido(self, msg: Any, campo_nome: str, index: int) -> None:
        if self.msg_mapa_proxy == msg and campo_nome == 'referencias':
            self.painel_referencias.carregar_mapa(msg)
        if self.msg_mapa_proxy == msg and campo_nome == 'pontos_de_interesse':
            item = self.itens_poi.get(index)
            if item:
                cena = self.visualizador.scene()
                if cena:
                    cena.removeItem(item)
                if self.dados_atuais and 'itens_bb' in self.dados_atuais:
                    if item in self.dados_atuais['itens_bb']:
                        self.dados_atuais['itens_bb'].remove(item)
                del self.itens_poi[index]
                
            nova_dict = {}
            for k, v in self.itens_poi.items():
                if k > index:
                    nova_dict[k - 1] = v
                else:
                    nova_dict[k] = v
            self.itens_poi = nova_dict


    def destacar_pois_temporariamente(self, referencia: Any) -> None:
        ids_list = list(referencia.ids) if hasattr(referencia, 'ids') else []
        is_camera = getattr(self, 'modo_camera', False)
        
        for idx_poi, gui_item in self.itens_poi.items():
            poi_dict = gui_item.pt_dict
            if poi_dict.get('id') in ids_list:
                from PySide6.QtGui import QBrush, QColor, QPen
                gui_item.brush = QBrush(QColor(0, 255, 255, 150))
                gui_item.setBrush(gui_item.brush)
                gui_item.setPen(QPen(QColor(0, 255, 255), 2))
                
        # Draw static camera if exists
        if not is_camera and hasattr(referencia, 'ajuste_de_camera') and referencia.HasField('ajuste_de_camera') and referencia.ajuste_de_camera.zoom > 0:
            if not hasattr(self, 'item_hover_camera_overlay') or not self.item_hover_camera_overlay:
                self.item_hover_camera_overlay = ItemCameraOverlay()
                if self.visualizador.scene():
                    self.visualizador.scene().addItem(self.item_hover_camera_overlay)
            self.item_hover_camera_overlay.setVisible(True)
            from PySide6.QtGui import QPen, QColor
            from PySide6.QtCore import Qt
            self.item_hover_camera_overlay.setPen(QPen(QColor("#6f42c1"), 3, Qt.PenStyle.DashLine))
            
            scene_rect = self.visualizador.sceneRect()
            if scene_rect.isEmpty():
                scene_rect = self.visualizador.mapToScene(self.visualizador.viewport().rect()).boundingRect()
            
            w_scene = scene_rect.width()
            h_scene = scene_rect.height()
            
            zoom = referencia.ajuste_de_camera.zoom
            pos_h = referencia.ajuste_de_camera.posicao_horizontal / 100.0
            pos_v = referencia.ajuste_de_camera.posicao_vertical / 100.0
            
            w = w_scene / zoom
            h = w * (16.0 / 9.0)
            
            center_x = pos_h * w_scene
            center_y = pos_v * h_scene
            
            x = scene_rect.x() + center_x - w/2
            y = scene_rect.y() + center_y - h/2
            
            self.item_hover_camera_overlay.setRect(0, 0, w, h)
            self.item_hover_camera_overlay.setPos(x, y)
        else:
            if hasattr(self, 'item_hover_camera_overlay') and self.item_hover_camera_overlay:
                self.item_hover_camera_overlay.setVisible(False)

    def remover_destaque_pois(self, force: bool = False) -> None:
        for idx_poi, gui_item in self.itens_poi.items():
            from PySide6.QtGui import QBrush, QColor, QPen
            if getattr(gui_item, 'is_hovered', False):
                gui_item.brush = QBrush(QColor(255, 165, 0, 100)) # Laranja hover
                gui_item.setBrush(gui_item.brush)
                gui_item.setPen(QPen(QColor(255, 140, 0), 2))
            else:
                gui_item.brush = QBrush(QColor(0, 255, 0, 50)) # Verde padrao
                gui_item.setBrush(gui_item.brush)
                gui_item.setPen(QPen(QColor(0, 255, 0), 2))
            
        if hasattr(self, 'item_hover_camera_overlay') and self.item_hover_camera_overlay:
            if self.visualizador.scene():
                self.visualizador.scene().removeItem(self.item_hover_camera_overlay)
            self.item_hover_camera_overlay = None
            
        if not force:
            if getattr(self, 'referencia_camera_ativa', None):
                self.destacar_pois_temporariamente(self.referencia_camera_ativa)
            elif getattr(self, 'referencia_linkagem_ativa', None):
                self.destacar_pois_temporariamente(self.referencia_linkagem_ativa)

    def _aplicar_highlight_linkagem(self) -> None:
        self.remover_destaque_pois(force=True)
        self.destacar_pois_temporariamente(self.referencia_linkagem_ativa)

    def iniciar_modo_camera(self, index: int, referencia: Any) -> None:
        self.referencia_camera_ativa = referencia
        self.camera_ref_idx = index
        self.modo_camera = True
        
        self.label_modo.setText("MODO CÂMERA - Posicione e redimensione a janela 9:16. Ao final, clique em Salvar Ajuste no painel lateral.")
        self.label_modo.setStyleSheet("color: white; background-color: #6f42c1; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.label_modo.setVisible(True)
        
        if not hasattr(self, 'item_camera_overlay') or not self.item_camera_overlay:
            self.item_camera_overlay = ItemCameraOverlay()
            if self.visualizador.scene():
                self.visualizador.scene().addItem(self.item_camera_overlay)
        else:
            self.item_camera_overlay.setVisible(True)

        self.destacar_pois_temporariamente(referencia)
        
        scene_rect = self.visualizador.sceneRect()
        if scene_rect.isEmpty():
            scene_rect = self.visualizador.mapToScene(self.visualizador.viewport().rect()).boundingRect()
            
        w_scene = scene_rect.width()
        h_scene = scene_rect.height()
        
        # Fallback de segurança caso cena seja nula
        if w_scene <= 0 or h_scene <= 0:
            w_scene = 800
            h_scene = 600
        
        if referencia.HasField('ajuste_de_camera') and referencia.ajuste_de_camera.zoom > 0:
            zoom = referencia.ajuste_de_camera.zoom
            pos_h = referencia.ajuste_de_camera.posicao_horizontal / 100.0
            pos_v = referencia.ajuste_de_camera.posicao_vertical / 100.0
            
            w = w_scene / zoom
            h = w * (16.0 / 9.0)
            
            center_x = pos_h * w_scene
            center_y = pos_v * h_scene
            
            x = scene_rect.x() + center_x - w/2
            y = scene_rect.y() + center_y - h/2
            
            self.item_camera_overlay.setRect(0, 0, w, h)
            self.item_camera_overlay.setPos(x, y)
        else:
            w = min(w_scene * 0.8, h_scene * 0.8 * (9.0 / 16.0))
            h = w * (16.0 / 9.0)
            x = scene_rect.x() + (w_scene - w) / 2
            y = scene_rect.y() + (h_scene - h) / 2
            
        self.item_camera_overlay.setRect(0, 0, w, h)
        self.item_camera_overlay.setPos(x, y)
        
    def parar_modo_camera(self) -> None:
        self.referencia_camera_ativa = None
        self.modo_camera = False
        if hasattr(self, 'item_camera_overlay') and self.item_camera_overlay:
            if self.visualizador.scene():
                self.visualizador.scene().removeItem(self.item_camera_overlay)
            self.item_camera_overlay = None
        self.remover_destaque_pois()
        self.label_modo.setVisible(False)

    def salvar_ajuste_camera(self) -> None:
        if not hasattr(self, 'referencia_camera_ativa') or not self.referencia_camera_ativa:
            return
            
        ref = self.referencia_camera_ativa
        idx = -1
        for i, r in enumerate(cast(Any, self.msg_mapa_proxy).referencias):
            if r == ref:
                idx = i
                break
        
        if idx == -1: return
        
        if not hasattr(self, 'item_camera_overlay') or not self.item_camera_overlay:
            return
            
        scene_rect = self.visualizador.sceneRect()
        if scene_rect.isEmpty():
            scene_rect = self.visualizador.mapToScene(self.visualizador.viewport().rect()).boundingRect()
            
        w_scene = scene_rect.width()
        h_scene = scene_rect.height()
        
        r = self.item_camera_overlay.sceneBoundingRect()
        
        zoom = w_scene / r.width()
        center_x = r.center().x() - scene_rect.x()
        center_y = r.center().y() - scene_rect.y()
        
        pos_h = (center_x / w_scene) * 100.0
        pos_v = (center_y / h_scene) * 100.0
        
        from aresta_api.proto.generated import croqui_pb2
        import copy
        
        ref_antiga = copy.deepcopy(self.referencia_camera_ativa)
        ref_nova = copy.deepcopy(self.referencia_camera_ativa)
        ref_nova.ajuste_de_camera.posicao_horizontal = int(pos_h)
        ref_nova.ajuste_de_camera.posicao_vertical = int(pos_v)
        ref_nova.ajuste_de_camera.zoom = zoom
        
        if self.mapas_controller and self.msg_mapa_proxy:
            self.mapas_controller.alterar_referencia(
                self.msg_mapa_proxy,
                self.camera_ref_idx,
                ref_antiga,
                ref_nova
            )
        if hasattr(self, 'painel_referencias'):
            self.painel_referencias.forcar_parada_camera()
        self.parar_modo_camera()

    def remover_ajuste_camera(self, idx: int) -> None:
        if idx < 0 or idx >= len(cast(Any, self.msg_mapa_proxy).referencias): return
        
        ref = cast(Any, self.msg_mapa_proxy).referencias[idx]
        import copy
        ref_antiga = copy.deepcopy(ref)
        ref_nova = copy.deepcopy(ref)
        ref_nova.ClearField('ajuste_de_camera')
        
        if self.mapas_controller and self.msg_mapa_proxy:
            self.mapas_controller.alterar_referencia(
                self.msg_mapa_proxy,
                idx,
                ref_antiga,
                ref_nova
            )
        self.parar_modo_camera()


    def iniciar_modo_linkagem(self, idx_ref: int, ref: Any) -> None:
        from PySide6.QtCore import Qt
        self.modo_linkagem = True
        self.linkagem_ref_idx = idx_ref
        self.linkagem_ref = ref
        self.referencia_linkagem_ativa = ref
        self.visualizador.setCursor(Qt.CursorShape.CrossCursor)
        self.label_modo.setText("MODO LINKAGEM - Clique nos POIs para linkar ou deslinkar à referência. Selecionados ficam em Ciano.")
        self.label_modo.setStyleSheet("color: white; background-color: #007bff; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.label_modo.setVisible(True)
        self._aplicar_highlight_linkagem()
        
        # TDD: Impedir POIs de se moverem durante a linkagem
        from PySide6.QtWidgets import QGraphicsItem
        for poi in self.itens_poi.values():
            poi.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def parar_modo_linkagem(self) -> None:
        from PySide6.QtCore import Qt
        self.modo_linkagem = False
        self.linkagem_ref_idx = -1
        self.linkagem_ref = None
        self.referencia_linkagem_ativa = None
        self.visualizador.setCursor(Qt.CursorShape.ArrowCursor)
        self.remover_destaque_pois()
        self.label_modo.setVisible(False)
        
        # TDD: Restaurar movimento dos POIs
        from PySide6.QtWidgets import QGraphicsItem
        for poi in self.itens_poi.values():
            poi.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def tratar_clique_poi_linkagem(self, poi_id: str) -> bool:
        if not hasattr(self, 'modo_linkagem') or not self.modo_linkagem:
            return False
            
        import copy
        ref_antiga = copy.deepcopy(self.linkagem_ref)
        ref_nova = copy.deepcopy(self.linkagem_ref)
        
        if poi_id in ref_nova.ids:
            ref_nova.ids.remove(poi_id)
        else:
            ref_nova.ids.append(poi_id)
            
        if self.mapas_controller and self.msg_mapa_proxy:
            self.mapas_controller.alterar_referencia(
                self.msg_mapa_proxy, self.linkagem_ref_idx, ref_antiga, ref_nova
            )
        self.linkagem_ref = ref_nova
        self.referencia_linkagem_ativa = ref_nova
        self._aplicar_highlight_linkagem()
        return True
class ItemCameraOverlay(QGraphicsRectItem):
    def __init__(self, rect: Optional[QRectF] = None) -> None:
        from PySide6.QtGui import QPen, QColor, QBrush
        from PySide6.QtCore import Qt
        super().__init__(rect)
        self.setPen(QPen(QColor(111, 66, 193), 4, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(Qt.GlobalColor.transparent))
        
        # Permitir arrastar
        cast_self = cast(Any, self)
        cast_self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        cast_self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        cast_self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        self.setAcceptHoverEvents(True)
        self.setZValue(100)
    
    def hoverMoveEvent(self, event: Any) -> None:
        from PySide6.QtCore import Qt
        rect = self.rect()
        if (event.pos() - rect.bottomRight()).manhattanLength() < 40:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)
        
    def mousePressEvent(self, event: Any) -> None:
        from PySide6.QtCore import Qt
        rect = self.rect()
        dist = (event.pos() - rect.bottomRight()).manhattanLength()
        if dist < 40:
            self.resizing_corner = True
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            event.accept()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.resizing_center = True
            self.rect_inicio = self.rect()
            self.centro_cena = self.mapToScene(self.rect_inicio.center())
            delta_inicio = event.scenePos() - self.centro_cena
            self.dist_inicio_abs = max(1.0, abs(delta_inicio.x()))
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            event.accept()
        else:
            self.resizing_corner = False
            self.resizing_center = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: Any) -> None:
        from PySide6.QtCore import Qt
        if getattr(self, 'resizing_center', False):
            delta = event.scenePos() - self.centro_cena
            diff_x = abs(delta.x()) - self.dist_inicio_abs
            
            novo_w = max(50.0, self.rect_inicio.width() + 2 * diff_x)
            novo_h = novo_w * (16.0 / 9.0)
            
            self.setRect(0, 0, novo_w, novo_h)
            novo_centro = self.rect().center()
            self.setTransformOriginPoint(novo_centro)
            self.setPos(self.centro_cena - novo_centro)
            event.accept()
        elif getattr(self, 'resizing_corner', False):
            new_width = max(50.0, event.pos().x() - self.rect().x())
            new_height = new_width * (16.0 / 9.0)
            self.setRect(self.rect().x(), self.rect().y(), new_width, new_height)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:
        from PySide6.QtCore import Qt
        if getattr(self, 'resizing_corner', False) or getattr(self, 'resizing_center', False):
            self.resizing_corner = False
            self.resizing_center = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def paint(self, painter: Any, option: Any, widget: Optional[QWidget] = None) -> None:
        from PySide6.QtGui import QPainter, QBrush, QColor
        from PySide6.QtCore import Qt, QRectF
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        safe_margin = rect.height() * 0.2
        
        top_rect = QRectF(rect.x(), rect.y(), rect.width(), safe_margin)
        bottom_rect = QRectF(rect.x(), rect.y() + rect.height() - safe_margin, rect.width(), safe_margin)
        
        painter.setBrush(QBrush(QColor(111, 66, 193, 50)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(top_rect)
        painter.drawRect(bottom_rect)
        
        pen = self.pen()
        pen.setCosmetic(True) # keeps 4px width even when zooming
        painter.setPen(pen)
        painter.setBrush(self.brush())
        painter.drawRect(rect)
