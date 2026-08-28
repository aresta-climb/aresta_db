# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from aresta_api.proto.generated import croqui_pb2
from editor.views.dialogos.dialogo_busca_referencia import DialogoBuscaReferencia
from editor.views.estilo import Icones

class CardReferencia(QFrame):
    """Card visual que representa uma Referência individual."""
    
    hover_in = Signal(object)
    hover_out = Signal()
    
    def __init__(self, referencia: croqui_pb2.Mapa.Referencia, index: int, parent=None):
        super().__init__(parent)
        self.referencia = referencia
        self.index = index
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CardReferencia {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-bottom: 8px;
            }
            CardReferencia:hover {
                border: 1px solid #adb5bd;
                background-color: #f8f9fa;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título (Caminho da entidade)
        caminho = []
        if referencia.grupo: caminho.append(referencia.grupo)
        if referencia.setor: caminho.append(referencia.setor)
        if referencia.escalada: caminho.append(referencia.escalada)
        
        titulo = " > ".join(caminho) if caminho else "Referência Inválida"
        
        # Cabeçalho: Título e Grupo
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        v_titles = QVBoxLayout()
        v_titles.setContentsMargins(0, 0, 0, 0)
        
        h_title = QHBoxLayout()
        h_title.setContentsMargins(0, 0, 0, 0)
        
        self.label_titulo = QLabel(f"<b>{titulo}</b>")
        self.label_titulo.setWordWrap(True)
        h_title.addWidget(self.label_titulo)
        
        self.btn_editar_alvo = QPushButton()
        self.btn_editar_alvo.setIcon(Icones.obter("lapis"))
        self.btn_editar_alvo.setStyleSheet("background-color: transparent; border: none; color: #007bff;")
        from PySide6.QtCore import Qt
        self.btn_editar_alvo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_editar_alvo.setToolTip("Editar Referência")
        self.btn_editar_alvo.setFixedSize(24, 24)
        h_title.addWidget(self.btn_editar_alvo)
        h_title.addStretch()
        
        v_titles.addLayout(h_title)
        
        if referencia.grupo:
            lbl_grupo = QLabel(referencia.grupo)
            lbl_grupo.setStyleSheet("font-weight: bold; font-size: 13px;")
            v_titles.addWidget(lbl_grupo)
        
        lbl_ids = QLabel(f"IDs linkados: {len(referencia.ids)}")
        lbl_ids.setStyleSheet("color: #6c757d; font-size: 11px;")
        v_titles.addWidget(lbl_ids)
        
        header_layout.addLayout(v_titles)
        header_layout.addStretch()
        
        self.btn_remover = QPushButton()
        self.btn_remover.setIcon(Icones.obter("lixeira"))
        self.btn_remover.setStyleSheet("background-color: transparent; border: none; color: #dc3545;")
        self.btn_remover.setToolTip("Excluir Referência")
        from PySide6.QtCore import Qt
        self.btn_remover.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remover.setFixedSize(24, 24)
        
        header_layout.addWidget(self.btn_remover, 0, Qt.AlignmentFlag.AlignTop)
        
        layout.addLayout(header_layout)
        
        # Linha 1: Linkar POIs
        layout_linha1 = QHBoxLayout()
        layout_linha1.setContentsMargins(0, 0, 0, 0)
        
        self.btn_linkar = QPushButton(" Linkar POIs")
        self.btn_linkar.setCheckable(True)
        self.btn_linkar.setIcon(Icones.obter("mapas"))
        
        layout_linha1.addWidget(self.btn_linkar)
        layout_linha1.addStretch()
        layout.addLayout(layout_linha1)
        
        # Linha 2: Câmera
        layout_linha2 = QHBoxLayout()
        layout_linha2.setContentsMargins(0, 0, 0, 0)
        
        tem_camera = referencia.HasField('ajuste_de_camera') and referencia.ajuste_de_camera.zoom > 0
        texto_camera = " Modificar Ajuste Câmera" if tem_camera else " Adicionar Ajuste Câmera"
        
        self.btn_camera = QPushButton(texto_camera)
        self.btn_camera.setCheckable(True)
        
        self.btn_remover_camera = QPushButton("X")
        self.btn_remover_camera.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; max-width: 30px;")
        self.btn_remover_camera.setToolTip("Remover Ajuste Câmera")
        self.btn_remover_camera.setVisible(tem_camera)
        
        layout_linha2.addWidget(self.btn_camera)
        layout_linha2.addWidget(self.btn_remover_camera)
        layout_linha2.addStretch()
        layout.addLayout(layout_linha2)
        
        self.btn_salvar_camera = QPushButton(" Salvar Ajuste")
        self.btn_salvar_camera.setIcon(Icones.obter("check"))
        self.btn_salvar_camera.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_salvar_camera.setVisible(False)
        layout.addWidget(self.btn_salvar_camera)

    def enterEvent(self, event):
        self.hover_in.emit(self.referencia)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.hover_out.emit()
        super().leaveEvent(event)

class PainelReferencias(QWidget):
    """Painel lateral direito contendo a lista de referências do mapa."""
    
    # Sinais para interagir com o WidgetEditorMapas
    referencia_removida = Signal(int)
    iniciar_modo_linkagem = Signal(int, object)
    parar_modo_linkagem = Signal()
    
    iniciar_modo_camera = Signal(int, object)
    parar_modo_camera = Signal()
    salvar_modo_camera = Signal()
    remover_ajuste_camera = Signal(int)
    
    destacar_pois = Signal(object)
    remover_destaque_pois = Signal()

    def __init__(self, mapas_controller, parent=None):
        super().__init__(parent)
        self.mapas_controller = mapas_controller
        self.msg_mapa_proxy = None
        
        self.setMinimumWidth(280)
        self.setStyleSheet("background-color: #f8f9fa; border-left: 1px solid #dee2e6;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Cabeçalho
        lbl_header = QLabel("Referências do Mapa")
        lbl_header.setStyleSheet("font-weight: bold; color: #444; font-size: 13px;")
        layout.addWidget(lbl_header)
        
        # Área de rolagem para os cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.container_cards = QWidget()
        self.container_cards.setStyleSheet("background: transparent;")
        self.layout_cards = QVBoxLayout(self.container_cards)
        self.layout_cards.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_cards.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area.setWidget(self.container_cards)
        layout.addWidget(self.scroll_area)
        
        # Botão Adicionar
        self.btn_add = QPushButton("+ Adicionar Referência")
        self.btn_add.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; border: none; padding: 8px; border-radius: 4px;")
        self.btn_add.clicked.connect(self._ao_clicar_adicionar)
        layout.addWidget(self.btn_add)
        
        # Estado atual
        self.btn_ativo_link = None
        self.btn_ativo_camera = None

    def carregar_mapa(self, msg_mapa_proxy):
        self.msg_mapa_proxy = msg_mapa_proxy
        self.atualizar_cards()

    def atualizar_cards(self):
        modo_link_index = None
        modo_camera_index = None
        
        for i in range(self.layout_cards.count()):
            item = self.layout_cards.itemAt(i)
            if item:
                card = item.widget()
                if card:
                    if hasattr(card, 'btn_linkar') and card.btn_linkar.isChecked():
                        modo_link_index = i
                    if hasattr(card, 'btn_camera') and card.btn_camera.isChecked():
                        modo_camera_index = i

        # Limpa layout
        while self.layout_cards.count():
            item = self.layout_cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        self.btn_ativo_link = None
        self.btn_ativo_camera = None
                
        if not self.msg_mapa_proxy:
            return
            
        for i, ref in enumerate(self.msg_mapa_proxy.referencias):
            card = CardReferencia(ref, i)
            
            # Conecta hover
            card.hover_in.connect(self.destacar_pois.emit)
            card.hover_out.connect(self.remover_destaque_pois.emit)
            
            # Conecta botões
            card.btn_remover.clicked.connect(lambda checked=False, idx=i: self._confirmar_remover(idx))
            card.btn_editar_alvo.clicked.connect(lambda checked=False, idx=i, r=ref: self._ao_clicar_editar_alvo(idx, r))
            if hasattr(card, 'btn_remover_camera'):
                card.btn_remover_camera.clicked.connect(lambda checked=False, idx=i: self.remover_ajuste_camera.emit(idx))
            
            card.btn_linkar.toggled.connect(lambda checked, c=card: self._on_linkar_toggled(checked, c))
            card.btn_camera.toggled.connect(lambda checked, c=card: self._on_camera_toggled(checked, c))
            card.btn_salvar_camera.clicked.connect(self.salvar_modo_camera.emit)
            
            self.layout_cards.addWidget(card)
            
            if modo_link_index == i:
                card.btn_linkar.blockSignals(True)
                card.btn_linkar.setChecked(True)
                card.btn_linkar.setStyleSheet("background-color: #007bff; color: white;")
                self.btn_ativo_link = card.btn_linkar
                card.btn_linkar.blockSignals(False)
            
            if modo_camera_index == i:
                card.btn_camera.blockSignals(True)
                card.btn_camera.setChecked(True)
                card.btn_camera.setStyleSheet("background-color: #6f42c1; color: white;")
                card.btn_salvar_camera.setVisible(True)
                self.btn_ativo_camera = card.btn_camera
                self.card_camera_ativo = card
                card.btn_camera.blockSignals(False)

    def _referencias_iguais(self, ref1, ref2):
        if ref1.HasField('grupo') != ref2.HasField('grupo') or (ref1.HasField('grupo') and ref1.grupo != ref2.grupo):
            return False
        if ref1.HasField('setor') != ref2.HasField('setor') or (ref1.HasField('setor') and ref1.setor != ref2.setor):
            return False
        if ref1.HasField('escalada') != ref2.HasField('escalada') or (ref1.HasField('escalada') and ref1.escalada != ref2.escalada):
            return False
        if ref1.HasField('indice_mapa_alvo') != ref2.HasField('indice_mapa_alvo') or (ref1.HasField('indice_mapa_alvo') and ref1.indice_mapa_alvo != ref2.indice_mapa_alvo):
            return False
        return True

    def _referencia_ja_existe(self, ref_nova):
        if not self.msg_mapa_proxy: return False
        for ref in self.msg_mapa_proxy.referencias:
            if self._referencias_iguais(ref, ref_nova):
                return True
        return False

    def _ao_clicar_adicionar(self):
        if not self.msg_mapa_proxy or not self.mapas_controller or not self.mapas_controller.model:
            return
            
        dialogo = DialogoBuscaReferencia(self.mapas_controller.model, self)
        if dialogo.exec():
            ref = dialogo.obter_referencia()
            if ref:
                if self._referencia_ja_existe(ref):
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Aviso", "Esta referência já existe neste mapa!")
                    return
                self.mapas_controller.adicionar_referencia(self.msg_mapa_proxy, ref)

    def _ao_clicar_editar_alvo(self, index, ref_antiga):
        dialogo = DialogoBuscaReferencia(self.mapas_controller.model, self)
        if dialogo.exec():
            ref_nova = dialogo.obter_referencia()
            if ref_nova:
                if not self._referencias_iguais(ref_nova, ref_antiga) and self._referencia_ja_existe(ref_nova):
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Aviso", "Esta referência já existe neste mapa!")
                    return
                
                from aresta_api.proto.generated import croqui_pb2
                ref_editada = croqui_pb2.Mapa.Referencia()
                # Se for um ReadOnlyProxy, copiar o conteúdo original
                obj_original = ref_antiga._obj if hasattr(ref_antiga, '_obj') else ref_antiga
                ref_editada.CopyFrom(obj_original)
                
                if ref_nova.HasField('grupo'):
                    ref_editada.grupo = ref_nova.grupo
                else:
                    ref_editada.ClearField('grupo')
                    
                if ref_nova.HasField('setor'):
                    ref_editada.setor = ref_nova.setor
                else:
                    ref_editada.ClearField('setor')
                    
                if ref_nova.HasField('escalada'):
                    ref_editada.escalada = ref_nova.escalada
                else:
                    ref_editada.ClearField('escalada')
                    
                if ref_nova.HasField('indice_mapa_alvo'):
                    ref_editada.indice_mapa_alvo = ref_nova.indice_mapa_alvo
                else:
                    ref_editada.ClearField('indice_mapa_alvo')
                    
                self.mapas_controller.alterar_referencia(
                    self.msg_mapa_proxy, index, ref_antiga, ref_editada
                )

    def _confirmar_remover(self, index):
        self._limpar_modos_ativos()
        if self.mapas_controller:
            self.mapas_controller.deletar_referencia(self.msg_mapa_proxy, index)

    def _on_linkar_toggled(self, checked, card):
        if checked:
            # Desmarca qualquer outro botão de ação
            self._limpar_modos_ativos()
            self.btn_ativo_link = card.btn_linkar
            card.btn_linkar.setStyleSheet("background-color: #007bff; color: white;")
            self.iniciar_modo_linkagem.emit(card.index, card.referencia)
        else:
            if self.btn_ativo_link == card.btn_linkar:
                self.btn_ativo_link = None
                self.parar_modo_linkagem.emit()
            card.btn_linkar.setStyleSheet("")

    def _on_camera_toggled(self, checked, card):
        if checked:
            self._limpar_modos_ativos()
            self.btn_ativo_camera = card.btn_camera
            self.card_camera_ativo = card
            card.btn_camera.setStyleSheet("background-color: #6f42c1; color: white;")
            card.btn_salvar_camera.setVisible(True)
            self.iniciar_modo_camera.emit(card.index, card.referencia)
        else:
            if self.btn_ativo_camera == card.btn_camera:
                self.btn_ativo_camera = None
                self.card_camera_ativo = None
                self.parar_modo_camera.emit()
            card.btn_camera.setStyleSheet("")
            card.btn_salvar_camera.setVisible(False)

    def forcar_parada_camera(self):
        """Método para forçar o desmarque do botão de câmera ativo."""
        if self.btn_ativo_camera:
            self.btn_ativo_camera.blockSignals(True)
            self.btn_ativo_camera.setChecked(False)
            self.btn_ativo_camera.setStyleSheet("")
            self.btn_ativo_camera.blockSignals(False)
            
        if hasattr(self, 'card_camera_ativo') and self.card_camera_ativo:
            self.card_camera_ativo.btn_salvar_camera.setVisible(False)
            self.card_camera_ativo = None
            
        self.btn_ativo_camera = None

    def _limpar_modos_ativos(self):
        if self.btn_ativo_link:
            self.btn_ativo_link.setChecked(False)
        if self.btn_ativo_camera:
            self.btn_ativo_camera.setChecked(False)
