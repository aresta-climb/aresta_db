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
from ..core.mapas_lib import converter_box_para_circulo, GerenciadorArquivosMapa
import copy

class CmdMoverPonto(QUndoCommand):
    """
    Comando para desfazer/refazer modificações (posição, tamanho, rotação, nome) em um POI.
    """
    def __init__(self, chave_mapa, idx_poi, estado_antigo, estado_novo, widget_editor, parent=None):
        super().__init__(parent)
        self.chave_mapa = chave_mapa
        self.idx_poi = idx_poi
        self.estado_antigo = estado_antigo
        self.estado_novo = estado_novo
        self.widget_editor = widget_editor
        import os
        nome_arquivo = os.path.basename(str(chave_mapa[0]))
        self.contexto_ui = f"page:mapas/file:{nome_arquivo}"

    def undo(self):
        dados = self.widget_editor.dados_arquivos.get(self.chave_mapa)
        if dados and 0 <= self.idx_poi < len(dados['itens_bb']):
            item = dados['itens_bb'][self.idx_poi]
            item.carregar_de_dict(self.estado_antigo)
            dados['dados_yaml']['mapas'][dados['indice_mapa']]['pontos_de_interesse'][self.idx_poi] = self.estado_antigo
            self.widget_editor.marcar_modificado()

    def redo(self):
        dados = self.widget_editor.dados_arquivos.get(self.chave_mapa)
        if dados and 0 <= self.idx_poi < len(dados['itens_bb']):
            item = dados['itens_bb'][self.idx_poi]
            item.carregar_de_dict(self.estado_novo)
            dados['dados_yaml']['mapas'][dados['indice_mapa']]['pontos_de_interesse'][self.idx_poi] = self.estado_novo
            self.widget_editor.marcar_modificado()


def registrar_movimento_final(item, estado_inicial):
    estado_final = copy.deepcopy(item.obter_dict_atualizado())
    if estado_inicial and estado_inicial != estado_final:
        widget_editor = item.scene().widget_editor
        chave_mapa = None
        idx_poi = -1
        for k, d in widget_editor.dados_arquivos.items():
            if item in d.get('itens_bb', []):
                chave_mapa = k
                idx_poi = d['itens_bb'].index(item)
                break
        
        if chave_mapa is not None and idx_poi != -1:
            dados = widget_editor.dados_arquivos[chave_mapa]
            if hasattr(widget_editor, 'controller') and widget_editor.controller:
                from google.protobuf.json_format import ParseDict
                from aresta_api.proto.generated import croqui_pb2
                poi_antigo = croqui_pb2.Mapa.PontoDeInteresse()
                ParseDict(estado_inicial, poi_antigo)
                poi_novo = croqui_pb2.Mapa.PontoDeInteresse()
                ParseDict(estado_final, poi_novo)
                if hasattr(widget_editor.controller, 'set_contexto'):
                    p_idx, sg_idx, m_idx = dados['pico_idx'], dados['sg_idx'], dados['mapa_idx']
                    path_str = f'node:root/node:Croqui/node:picos/item:{p_idx}/node:setores_ou_grupos/item:{sg_idx}/node:setor/node:mapas/item:{m_idx}'
                    widget_editor.controller.set_contexto('page:mapas/' + path_str)
                widget_editor.controller.alterar_repeated_item(dados['mapa_msg'], 'pontos_de_interesse', idx_poi, poi_antigo, poi_novo)
                return
            
            historico = None
            window = widget_editor.window()
            if window and hasattr(window, "historico"):
                historico = window.historico
            if historico:
                historico.executar(CmdMoverPonto(chave_mapa, idx_poi, estado_inicial, estado_final, widget_editor))
                return
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
                if novo_id or novo_label:
                    estado_inicial = copy.deepcopy(self.obter_dict_atualizado())
                    
                    # Cria o estado final desejado
                    estado_final = copy.deepcopy(estado_inicial)
                    estado_final['id'] = novo_id
                    estado_final['label'] = novo_label
                    
                    widget_editor = self.scene().widget_editor
                    chave_mapa = None
                    idx_poi = -1
                    for k, d in widget_editor.dados_arquivos.items():
                        if self in d['itens_bb']:
                            chave_mapa = k
                            idx_poi = d['itens_bb'].index(self)
                            break
                    
                    if chave_mapa is not None and idx_poi != -1:
                        historico = None
                        window = widget_editor.window()
                        if window and hasattr(window, "historico"):
                            historico = window.historico
                        if historico:
                            historico.executar(CmdMoverPonto(chave_mapa, idx_poi, estado_inicial, estado_final, widget_editor))
                            return
                            
                    self.pt_dict['id'] = novo_id
                    self.pt_dict['label'] = novo_label
                    texto_exibicao = novo_id if novo_id else novo_label
                    self.item_texto.setPlainText(texto_exibicao)
                    self.setToolTip(f"ID: {novo_id} | Label: {novo_label}")
                    self.marcar_alterado()

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
            
            novo_w = max(5, self.rect_inicio_redim.width() + 2 * diff_x)
            novo_h = max(5, self.rect_inicio_redim.height() + 2 * diff_y)
            
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
        if mudanca == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self):
        rect = self.rect()
        dados_box = {
            'x': int(round(self.x() + rect.width() / 2)),
            'y': int(round(self.y() + rect.height() / 2)),
            'comprimento': int(rect.width()),
            'largura': int(rect.height())
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
            r = max(5, self.rect_inicio_redim.width() / 2 + delta.x())
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
        if mudanca == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionHasChanged:
            self.marcar_alterado()
        return super().itemChange(mudanca, valor)

    def obter_dict_atualizado(self):
        r = int(self.rect().width() / 2)
        self.pt_dict['circular'] = {
            'x': int(self.x()),
            'y': int(self.y()),
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
            coords.append(int(p.x() + pos.x()))
            coords.append(int(p.y() + pos.y()))
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
    
    def __init__(self, caminho_pasta=None, parent=None, standalone=False):
        super().__init__(parent)
        self.standalone = standalone
        self.caminho_pasta = caminho_pasta
        self.dados_arquivos = {}
        self.esta_modificado = False
        self.gerenciador_arquivos = GerenciadorArquivosMapa()
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

        if self.caminho_pasta:
            self.carregar_pasta(self.caminho_pasta)

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
        
        label_titulo = QLabel("Arquivos de Mapa")
        label_titulo.setStyleSheet("font-weight: bold; color: #444; font-size: 13px;")
        layout_esquerdo.addWidget(label_titulo)

        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.ao_selecionar_arquivo)
        layout_esquerdo.addWidget(self.list_widget)
        
        layout_botoes = QVBoxLayout()
        layout_botoes.setSpacing(4)
        
        from editor.views.estilo import Icones
        
        self.btn_add_circ = QPushButton(" Novo Círculo")
        self.btn_add_circ.setIcon(Icones.obter("dados")) # Temporário, ou usar qta diretamente
        self.btn_add_circ.clicked.connect(lambda: self.adicionar_poi('circular'))
        layout_botoes.addWidget(self.btn_add_circ)

        self.btn_add_box = QPushButton(" Nova Box")
        self.btn_add_box.setIcon(Icones.obter("imagens"))
        self.btn_add_box.clicked.connect(lambda: self.adicionar_poi('box'))
        layout_botoes.addWidget(self.btn_add_box)

        self.btn_add_area = QPushButton(" Nova Área Livre")
        self.btn_add_area.setIcon(Icones.obter("mapas"))
        self.btn_add_area.clicked.connect(lambda: self.adicionar_poi('area_livre'))
        layout_botoes.addWidget(self.btn_add_area)
        
        layout_esquerdo.addLayout(layout_botoes)
        layout_esquerdo.addSpacing(10)

        self.btn_converter = QPushButton(" Box -> Círculo")
        self.btn_converter.setToolTip("Converte Boxes em Círculos. Se já estiver no modo, clique novamente para converter TODAS as boxes.")
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

        layout_bulk.addWidget(QLabel("Boxes:"))
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

        self.label_info = QLabel("Dicas: Ctrl+Arrastar (Resize) | Shift+Arrastar (Girar Box)")
        self.label_info.setStyleSheet("color: #6c757d; font-style: italic; font-size: 11px;")
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout_direito.addWidget(self.label_info)
        
        # Placeholder quando não há mapa
        self.label_placeholder = QLabel("Selecione um arquivo de mapa na lista à esquerda para começar a editar.")
        self.label_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_placeholder.setStyleSheet("color: #999; font-size: 16px; font-style: italic;")
        layout_direito.addWidget(self.label_placeholder)
        
        layout_direito.addWidget(self.visualizador)
        
        self.splitter.addWidget(widget_direito)
        self.splitter.setSizes([250, 750])
        layout_principal.addWidget(self.splitter)

    def carregar_de_modelo(self, modelo, caminho_db=None):
        self.modelo = modelo
        self.caminho_db = caminho_db
        self.list_widget.clear()
        self.dados_arquivos = {}
        if hasattr(self, '_on_repeated_item_alterado'):
            try:
                self.modelo.repeated_item_alterado.disconnect(self._on_repeated_item_alterado)
                self.modelo.repeated_adicionado.disconnect(self._on_repeated_adicionado)
                self.modelo.repeated_removido.disconnect(self._on_repeated_removido)
            except Exception: pass
        self.modelo.repeated_item_alterado.connect(self._on_repeated_item_alterado)
        self.modelo.repeated_adicionado.connect(self._on_repeated_adicionado)
        self.modelo.repeated_removido.connect(self._on_repeated_removido)
        
        croqui_msg = modelo.obter_croqui_readonly()
        
        for p_idx, pico in enumerate(croqui_msg.picos):
            for sg_idx, sg in enumerate(pico.setores_ou_grupos):
                if sg.HasField("setor"):
                    setor = sg.setor.conteudo
                    for m_idx, mapa in enumerate(setor.mapas):
                        disp = mapa.caminho_imagem_mapa if mapa.caminho_imagem_mapa else f"Mapa {m_idx+1}"
                        ui_item = QListWidgetItem(f"{setor.nome} - {disp}")
                        chave = (pico.nome, setor.nome, m_idx)
                        self.dados_arquivos[chave] = {
                            'mapa_msg': mapa,
                            'pico_idx': p_idx,
                            'sg_idx': sg_idx,
                            'mapa_idx': m_idx
                        }
                        ui_item.setData(Qt.ItemDataRole.UserRole, chave)
                        self.list_widget.addItem(ui_item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            self.label_placeholder.setVisible(False)
        else:
            self.label_placeholder.setVisible(True)

    def carregar_markdown(self, caminho_arquivo):
        try:
            dados_yaml, corpo_md = self.gerenciador_arquivos.ler_arquivo(caminho_arquivo)
            if not dados_yaml or 'mapas' not in dados_yaml:
                return
            
            for indice_mapa, mapa in enumerate(dados_yaml['mapas']):
                img_rel = mapa.get('caminho_imagem_mapa')
                if not img_rel: continue
                img_path = os.path.normpath(os.path.join(os.path.dirname(caminho_arquivo), img_rel))
                if not os.path.exists(img_path): continue
                
                cena = CenaDesenho(self)
                cena.addPixmap(QPixmap(img_path))
                itens_bb = []
                for pt in mapa.get('pontos_de_interesse', []):
                    item = None
                    if 'circular' in pt:
                        item = ItemBoundingCircular(pt, self.deletar_item_poi, self.marcar_modificado)
                    elif 'box' in pt:
                        item = ItemBoundingBox(pt, self.deletar_item_poi, self.marcar_modificado)
                    elif 'area_livre' in pt:
                        item = ItemBoundingAreaLivre(pt, self.deletar_item_poi, self.marcar_modificado)
                    
                    if item:
                        cena.addItem(item)
                        itens_bb.append(item)
                
                chave = (caminho_arquivo, indice_mapa)
                self.dados_arquivos[chave] = {
                    'caminho_arquivo': caminho_arquivo, 'indice_mapa': indice_mapa,
                    'dados_yaml': dados_yaml, 'corpo_markdown': corpo_md,
                    'cena': cena, 'itens_bb': itens_bb
                }
                disp = os.path.basename(caminho_arquivo)
                if len(dados_yaml['mapas']) > 1: disp += f" (M{indice_mapa+1})"
                ui_item = QListWidgetItem(disp)
                ui_item.setData(Qt.ItemDataRole.UserRole, chave)
                self.list_widget.addItem(ui_item)
        except Exception as e:
            print(f"Erro ao carregar {caminho_arquivo}: {e}")

    def ao_selecionar_arquivo(self, indice):
        if indice < 0: 
            self.label_placeholder.setVisible(True)
            self.visualizador.setVisible(False)
            return
        
        chave = self.list_widget.item(indice).data(Qt.ItemDataRole.UserRole)
        dados = self.dados_arquivos.get(chave)
        if dados:
            if 'cena' not in dados:
                cena = CenaDesenho(self)
                itens_bb = []
                mapa_msg = dados.get('mapa_msg')
                
                if mapa_msg:
                    import os
                    from pathlib import Path
                    from google.protobuf.json_format import MessageToDict
                    
                    if mapa_msg.caminho_imagem_mapa and hasattr(self, 'caminho_db') and self.caminho_db:
                        img_path = str(Path(self.caminho_db) / mapa_msg.caminho_imagem_mapa)
                        if os.path.exists(img_path):
                            cena.addPixmap(QPixmap(img_path))
                    
                    for pt_msg in mapa_msg.pontos_de_interesse:
                        pt = MessageToDict(pt_msg, preserving_proto_field_name=True)
                        item = None
                        if 'circular' in pt:
                            item = ItemBoundingCircular(pt, self.deletar_item_poi, self.marcar_modificado)
                        elif 'box' in pt:
                            item = ItemBoundingBox(pt, self.deletar_item_poi, self.marcar_modificado)
                        elif 'area_livre' in pt:
                            item = ItemBoundingAreaLivre(pt, self.deletar_item_poi, self.marcar_modificado)
                        
                        if item:
                            cena.addItem(item)
                            itens_bb.append(item)
                
                dados['cena'] = cena
                dados['itens_bb'] = itens_bb

            self.label_placeholder.setVisible(False)
            self.visualizador.setVisible(True)
            self.dados_atuais = dados
            self.visualizador.setScene(dados['cena'])
            self.visualizador.fitInView(dados['cena'].sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            if self.modo_desenho: self.cancelar_modo_desenho()
            if self.modo_conversao: self.parar_modo_conversao()

    def selecionar_arquivo(self, nome_arquivo: str):
        """Seleciona um arquivo na lista pelo nome do arquivo."""
        import os
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            chave = item.data(Qt.ItemDataRole.UserRole)
            if chave and isinstance(chave, tuple) and len(chave) > 0:
                caminho = str(chave[0])
                if os.path.basename(caminho) == nome_arquivo:
                    self.list_widget.setCurrentRow(i)
                    return

    def adicionar_poi(self, tipo):
        if not self.dados_atuais: return
        
        if tipo == 'area_livre':
            self.iniciar_modo_desenho(self.dados_atuais)
            return

        dialogo = DialogoEdicaoPOI("", "")
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            novo_id, novo_label = dialogo.obter_valores()
            if not novo_id and not novo_label: return
            
            rect_visao = self.visualizador.mapToScene(self.visualizador.viewport().rect()).boundingRect()
            cx, cy = rect_visao.center().x(), rect_visao.center().y()
            
            pt_dict = {'id': novo_id, 'label': novo_label}
            item_gui = None
            if tipo == 'circular':
                pt_dict['circular'] = {'x': int(cx), 'y': int(cy), 'raio': 40}
                item_gui = ItemBoundingCircular(pt_dict, self.deletar_item_poi, self.marcar_modificado)
            elif tipo == 'box':
                pt_dict['box'] = {'x': int(cx-40), 'y': int(cy-40), 'comprimento': 80, 'largura': 80}
                item_gui = ItemBoundingBox(pt_dict, self.deletar_item_poi, self.marcar_modificado)
            
            if item_gui:
                if hasattr(self, 'controller') and self.controller:
                    from aresta_api.proto.generated import croqui_pb2
                    from google.protobuf.json_format import ParseDict
                    novo_poi = croqui_pb2.Mapa.PontoDeInteresse()
                    ParseDict(pt_dict, novo_poi)
                    indice_insercao = len(self.dados_atuais['itens_bb'])
                    if hasattr(self.controller, 'set_contexto'):
                        d = self.dados_atuais
                        path_str = f'node:root/node:Croqui/node:picos/item:{d['pico_idx']}/node:setores_ou_grupos/item:{d['sg_idx']}/node:setor/node:mapas/item:{d['mapa_idx']}'
                        self.controller.set_contexto('page:mapas/' + path_str)
                    self.controller.adicionar_repeated(self.dados_atuais['mapa_msg'], 'pontos_de_interesse', indice_insercao, novo_poi)
                    return
                self.dados_atuais['cena'].addItem(item_gui)
                self.dados_atuais['itens_bb'].append(item_gui)
                if 'dados_yaml' in self.dados_atuais:
                    self.dados_atuais['dados_yaml']['mapas'][self.dados_atuais['indice_mapa']].setdefault('pontos_de_interesse', []).append(pt_dict)
                self.marcar_modificado()

    def deletar_item_poi(self, item):
        chave_unica = None
        for k, d in self.dados_arquivos.items():
            if item in d.get('itens_bb', []):
                chave_unica = k
                break
        if not chave_unica: return
        
        dados = self.dados_arquivos[chave_unica]
        idx = dados['itens_bb'].index(item)
        
        if hasattr(self, 'controller') and self.controller:
            from aresta_api.proto.generated import croqui_pb2
            from google.protobuf.json_format import ParseDict
            poi_removido = croqui_pb2.Mapa.PontoDeInteresse()
            estado_atual = item.obter_dict_atualizado()
            ParseDict(estado_atual, poi_removido)
            if hasattr(self.controller, 'set_contexto'):
                d = dados
                path_str = f'node:root/node:Croqui/node:picos/item:{d['pico_idx']}/node:setores_ou_grupos/item:{d['sg_idx']}/node:setor/node:mapas/item:{d['mapa_idx']}'
                self.controller.set_contexto('page:mapas/' + path_str)
            self.controller.remover_repeated(dados['mapa_msg'], 'pontos_de_interesse', idx, poi_removido)
            return
            
        dados['cena'].removeItem(item)
        dados['itens_bb'].pop(idx)
        if 'dados_yaml' in dados:
            dados['dados_yaml']['mapas'][dados['indice_mapa']]['pontos_de_interesse'].pop(idx)
        self.marcar_modificado()

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
                coords = []
                for p in self.pontos_desenho:
                    coords.append(int(p.x()))
                    coords.append(int(p.y()))
                
                pt_dict = {
                    'id': novo_id, 'label': novo_label,
                    'area_livre': {'coordenadas': coords}
                }
                item_gui = ItemBoundingAreaLivre(pt_dict, self.deletar_item_poi, self.marcar_modificado)
                self.dados_atuais['cena'].addItem(item_gui)
                self.dados_atuais['itens_bb'].append(item_gui)
                self.dados_atuais['dados_yaml']['mapas'][self.dados_atuais['indice_mapa']].setdefault('pontos_de_interesse', []).append(pt_dict)
                self.marcar_modificado()
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
            if self.dados_atuais:
                boxes = [it for it in self.dados_atuais['itens_bb'] if isinstance(it, ItemBoundingBox)]
                for box in boxes:
                    self.converter_box_para_circulo(box)
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
        if not self.dados_atuais: return
        a_converter = []
        for it in self.dados_atuais['itens_bb']:
            if isinstance(it, ItemBoundingBox):
                if rect.contains(it.mapToScene(it.rect().center())):
                    a_converter.append(it)
        if a_converter:
            for it in a_converter:
                self.converter_box_para_circulo(it)
        self.parar_modo_conversao()

    def converter_box_para_circulo(self, item):
        pt_dict = item.pt_dict
        novo_pt_dict = converter_box_para_circulo(pt_dict)
        if not novo_pt_dict: return
        
        idx = self.dados_atuais['itens_bb'].index(item)
        self.dados_atuais['cena'].removeItem(item)
        
        novo_item = ItemBoundingCircular(novo_pt_dict, self.deletar_item_poi, self.marcar_modificado)
        self.dados_atuais['cena'].addItem(novo_item)
        self.dados_atuais['itens_bb'][idx] = novo_item
        self.dados_atuais['dados_yaml']['mapas'][self.dados_atuais['indice_mapa']]['pontos_de_interesse'][idx] = novo_pt_dict
        self.marcar_modificado()

    # Bulk Sliders logic
    def ao_pressionar_slider_bulk(self, tipo):
        if not self.dados_atuais: return
        self.bulk_base_dims = {}
        for it in self.dados_atuais['itens_bb']:
            if tipo == 'circular' and isinstance(it, ItemBoundingCircular):
                self.bulk_base_dims[id(it)] = it.rect().width() / 2
            elif tipo == 'box' and isinstance(it, ItemBoundingBox):
                self.bulk_base_dims[id(it)] = (it.rect().width(), it.rect().height())

    def ao_mover_slider_bulk(self, valor, tipo):
        if not self.bulk_base_dims: return
        fator = 1.0 + valor / 100.0
        mudou = False
        if tipo == 'circular':
            self.label_circ.setText(f"{valor:+}%")
            for it in self.dados_atuais['itens_bb']:
                if isinstance(it, ItemBoundingCircular) and id(it) in self.bulk_base_dims:
                    base_r = self.bulk_base_dims[id(it)]
                    novo_r = max(2, base_r * fator)
                    it.setRect(-novo_r, -novo_r, 2 * novo_r, 2 * novo_r)
                    it.atualizar_pos_texto(-novo_r, -novo_r)
                    mudou = True
        elif tipo == 'box':
            self.label_box.setText(f"{valor:+}%")
            for it in self.dados_atuais['itens_bb']:
                if isinstance(it, ItemBoundingBox) and id(it) in self.bulk_base_dims:
                    base_w, base_h = self.bulk_base_dims[id(it)]
                    novo_w = max(4, base_w * fator)
                    novo_h = max(4, base_h * fator)
                    centro_cena_antigo = it.mapToScene(it.rect().center())
                    it.setRect(0, 0, novo_w, novo_h)
                    it.setTransformOriginPoint(it.rect().center())
                    it.setPos(centro_cena_antigo - it.rect().center())
                    mudou = True
        if mudou: self.marcar_modificado()

    def ao_soltar_slider_bulk(self, tipo):
        self.bulk_base_dims = {}
        if tipo == 'circular':
            self.slider_circ.blockSignals(True); self.slider_circ.setValue(0); self.slider_circ.blockSignals(False)
            self.label_circ.setText("0%")
        elif tipo == 'box':
            self.slider_box.blockSignals(True); self.slider_box.setValue(0); self.slider_box.blockSignals(False)
            self.label_box.setText("0%")

    def _recarregar_pois_cena_atual(self):
        if not self.dados_atuais or 'cena' not in self.dados_atuais: return
        cena = self.dados_atuais['cena']
        mapa_msg = self.dados_atuais['mapa_msg']
        
        for item in self.dados_atuais.get('itens_bb', []):
            cena.removeItem(item)
        self.dados_atuais['itens_bb'] = []
        
        from google.protobuf.json_format import MessageToDict
        for pt_msg in mapa_msg.pontos_de_interesse:
            pt = MessageToDict(pt_msg, preserving_proto_field_name=True)
            item = None
            if 'circular' in pt:
                item = ItemBoundingCircular(pt, self.deletar_item_poi, self.marcar_modificado)
            elif 'box' in pt:
                item = ItemBoundingBox(pt, self.deletar_item_poi, self.marcar_modificado)
            elif 'area_livre' in pt:
                item = ItemBoundingAreaLivre(pt, self.deletar_item_poi, self.marcar_modificado)
            
            if item:
                cena.addItem(item)
                self.dados_atuais['itens_bb'].append(item)

    def _on_repeated_item_alterado(self, msg, campo_nome, index):
        if hasattr(self, 'dados_atuais') and self.dados_atuais and self.dados_atuais.get('mapa_msg') == msg and campo_nome == 'pontos_de_interesse':
            self._recarregar_pois_cena_atual()

    def _on_repeated_adicionado(self, msg, campo_nome, index):
        if hasattr(self, 'dados_atuais') and self.dados_atuais and self.dados_atuais.get('mapa_msg') == msg and campo_nome == 'pontos_de_interesse':
            self._recarregar_pois_cena_atual()

    def _on_repeated_removido(self, msg, campo_nome, index):
        if hasattr(self, 'dados_atuais') and self.dados_atuais and self.dados_atuais.get('mapa_msg') == msg and campo_nome == 'pontos_de_interesse':
            self._recarregar_pois_cena_atual()
