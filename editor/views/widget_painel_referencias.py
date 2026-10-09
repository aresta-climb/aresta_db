# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from aresta_api.proto.generated import croqui_pb2
from editor.views.dialogos.dialogo_busca_referencia import DialogoBuscaReferencia
from editor.views.estilo import Icones
from editor.core.rotulos_referencia import extrair_rotulo_referencia
from editor.models.referencias_util import resolver_caminho_referencia

ESTILO_CARD_PADRAO = """
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
    QToolTip {
        color: #212529;
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 4px 6px;
        font-size: 11px;
    }
"""

ESTILO_CARD_SELECIONADO = """
    CardReferencia {
        background-color: #f0f7ff;
        border: 2px solid #007bff;
        border-radius: 6px;
        margin-bottom: 8px;
    }
    CardReferencia:hover {
        border: 2px solid #0056b3;
        background-color: #e2f0fd;
    }
    QToolTip {
        color: #212529;
        background-color: #ffffff;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 4px 6px;
        font-size: 11px;
    }
"""

class CardReferencia(QFrame):
    """Card visual que representa uma Referência individual."""
    
    hover_in = Signal(object)
    hover_out = Signal()
    clicado = Signal(int)
    
    def __init__(
        self,
        referencia: croqui_pb2.Mapa.Referencia,
        index: int,
        parent: Optional[QWidget] = None,
        mapa: Optional[Any] = None,
        root_croqui: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self.referencia: croqui_pb2.Mapa.Referencia = referencia
        self.index: int = index
        self.mapa: Optional[Any] = mapa
        self.root_croqui: Optional[Any] = root_croqui
        self.selecionado: bool = False
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(ESTILO_CARD_PADRAO)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título (Caminho da entidade resolvido por UID)
        titulo = resolver_caminho_referencia(root_croqui, referencia) if root_croqui else ""
        if not titulo:
            titulo = "Referência Inválida"
        
        # Cabeçalho: Título
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
        self.btn_editar_alvo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_editar_alvo.setToolTip("Editar Referência")
        self.btn_editar_alvo.setFixedSize(24, 24)
        h_title.addWidget(self.btn_editar_alvo)
        h_title.addStretch()
        
        v_titles.addLayout(h_title)
        
        h_ids = QHBoxLayout()
        h_ids.setContentsMargins(0, 0, 0, 0)
        h_ids.setSpacing(6)

        self.lbl_ids = QLabel()
        self.lbl_ids.setStyleSheet("color: #6c757d; font-size: 11px;")
        h_ids.addWidget(self.lbl_ids)

        self.btn_inverter = QPushButton("Inverter Ordem")
        self.btn_inverter.setIcon(Icones.obter("inverter"))
        self.btn_inverter.setToolTip("Inverter ordem dos nós/linhas linkados")
        self.btn_inverter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inverter.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f5;
                color: #495057;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 1px 5px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:disabled {
                color: #adb5bd;
                background-color: #f8f9fa;
                border-color: #e9ecef;
            }
        """)
        h_ids.addWidget(self.btn_inverter)
        h_ids.addStretch()

        v_titles.addLayout(h_ids)

        # Preview do codenome da referência
        self.lbl_preview = QLabel()
        v_titles.addWidget(self.lbl_preview)

        self.atualizar_preview(self.mapa)
        
        header_layout.addLayout(v_titles)
        header_layout.addStretch()
        
        self.btn_remover = QPushButton()
        self.btn_remover.setIcon(Icones.obter("lixeira"))
        self.btn_remover.setStyleSheet("background-color: transparent; border: none; color: #dc3545;")
        self.btn_remover.setToolTip("Excluir Referência")
        self.btn_remover.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remover.setFixedSize(24, 24)
        
        header_layout.addWidget(self.btn_remover, 0, Qt.AlignmentFlag.AlignTop)
        
        layout.addLayout(header_layout)
        
        # Linha 1: Vincular Elementos
        layout_linha1 = QHBoxLayout()
        layout_linha1.setContentsMargins(0, 0, 0, 0)
        
        self.btn_vincular = QPushButton(" Vincular Elementos")
        self.btn_vincular.setCheckable(True)
        self.btn_vincular.setIcon(Icones.obter("mapas"))
        self.btn_vincular.setToolTip("Vincular ou desvincular elementos (pontos e trajetos) do mapa a esta referência")
        self.btn_linkar = self.btn_vincular  # Alias de compatibilidade
        
        layout_linha1.addWidget(self.btn_vincular)
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

    def atualizar_preview(self, mapa: Optional[Any] = None, root_croqui: Optional[Any] = None) -> None:
        """Atualiza a exibição do codenome e a contagem de nós linkados na referência."""
        if mapa is not None:
            self.mapa = mapa
            if hasattr(self.mapa, 'referencias') and 0 <= self.index < len(self.mapa.referencias):
                self.referencia = self.mapa.referencias[self.index]
        if root_croqui is not None:
            self.root_croqui = root_croqui
        elif not self.root_croqui:
            p = self.parent()
            while p:
                if hasattr(p, "_obter_root_croqui"):
                    self.root_croqui = p._obter_root_croqui()
                    break
                p = p.parent()

        if self.root_croqui:
            titulo = resolver_caminho_referencia(self.root_croqui, self.referencia)
            if titulo:
                self.label_titulo.setText(f"<b>{titulo}</b>")

        total_links = len(self.referencia.pontos_uids)
        self.lbl_ids.setText(f"IDs linkados: {total_links}")
        self.btn_inverter.setEnabled(total_links > 1)

        codenome = extrair_rotulo_referencia(self.mapa, self.referencia) if self.mapa else ""
        if codenome:
            self.lbl_preview.setText(f"Codenome: <b>[ {codenome} ]</b>")
            self.lbl_preview.setStyleSheet("""
                QLabel {
                    color: #155724;
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
            """)
            self.lbl_preview.setToolTip(f"Codenome exibido no aplicativo: {codenome}")
        else:
            self.lbl_preview.setText("⚠️ Sem rótulo")
            self.lbl_preview.setStyleSheet("""
                QLabel {
                    color: #856404;
                    background-color: #fff3cd;
                    border: 1px solid #ffeeba;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
            """)
            self.lbl_preview.setToolTip(
                "Esta referência não possui label ou nós de círculo identificador e não exibirá identificador no aplicativo."
            )

    def definir_selecionado(self, selecionado: bool) -> None:
        """Define o estado de seleção visual do card."""
        self.selecionado = selecionado
        self.setStyleSheet(ESTILO_CARD_SELECIONADO if selecionado else ESTILO_CARD_PADRAO)

    def mousePressEvent(self, event: Any) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicado.emit(self.index)
            event.accept()
            return
        super().mousePressEvent(event)

    def enterEvent(self, event: Any) -> None:

        self.hover_in.emit(self.referencia)
        super().enterEvent(event)
        
    def leaveEvent(self, event: Any) -> None:
        self.hover_out.emit()
        super().leaveEvent(event)

class PainelReferencias(QWidget):
    """Painel lateral direito contendo a lista de referências do mapa."""
    
    # Sinais para interagir com o WidgetEditorMapas
    referencia_removida = Signal(int)
    referencia_selecionada = Signal(int, object)
    referencia_desmarcada = Signal()
    iniciar_modo_linkagem = Signal(int, object)
    parar_modo_linkagem = Signal()
    
    iniciar_modo_camera = Signal(int, object)
    parar_modo_camera = Signal()
    salvar_modo_camera = Signal()
    remover_ajuste_camera = Signal(int)
    
    destacar_pois = Signal(object)
    remover_destaque_pois = Signal()

    def __init__(self, mapas_controller: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._mapas_controller: Optional[Any] = mapas_controller
        self._croqui_model: Optional[Any] = getattr(mapas_controller, "model", None) if mapas_controller else None
        self.msg_mapa_proxy: Optional[Any] = None
        
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
        self.btn_ativo_link: Optional[QPushButton] = None
        self.btn_ativo_camera: Optional[QPushButton] = None
        self.card_camera_ativo: Optional[CardReferencia] = None
        self.idx_card_selecionado: Optional[int] = None

    @property
    def mapas_controller(self) -> Optional[Any]:
        return self._mapas_controller

    @mapas_controller.setter
    def mapas_controller(self, valor: Optional[Any]) -> None:
        self._mapas_controller = valor
        if valor and getattr(valor, "model", None):
            self.croqui_model = valor.model
        elif self.msg_mapa_proxy:
            self.atualizar_cards()

    @property
    def croqui_model(self) -> Optional[Any]:
        return self._croqui_model

    @croqui_model.setter
    def croqui_model(self, valor: Optional[Any]) -> None:
        self._croqui_model = valor
        if valor and hasattr(valor, "indice_uids") and valor.indice_uids:
            try:
                valor.indice_uids.indice_alterado.connect(self.atualizar_previews)
            except Exception:
                pass
        if self.msg_mapa_proxy:
            self.atualizar_cards()

    def _obter_root_croqui(self) -> Optional[Any]:
        model = self._croqui_model
        if not model and self._mapas_controller and getattr(self._mapas_controller, "model", None):
            model = self._mapas_controller.model
        if not model:
            parent = self.parent()
            while parent:
                parent_model = getattr(parent, "croqui_model", None)
                if parent_model:
                    model = parent_model
                    break
                parent_ctrl = getattr(parent, "mapas_controller", None)
                if parent_ctrl and getattr(parent_ctrl, "model", None):
                    model = parent_ctrl.model
                    break
                parent = parent.parent()
        if model:
            indice = getattr(model, "indice_uids", None)
            if indice is not None:
                return indice
            if hasattr(model, "obter_croqui_readonly"):
                return model.obter_croqui_readonly()
            return getattr(model, "croqui", getattr(model, "_croqui", None))
        return None

    def carregar_mapa(self, msg_mapa_proxy: Any) -> None:
        self.msg_mapa_proxy = msg_mapa_proxy
        self.atualizar_cards()

    def atualizar_previews(self) -> None:
        """Atualiza os badges de codenome e contagem de nós de todos os cards de referência."""
        root_croqui = self._obter_root_croqui()
        for i in range(self.layout_cards.count()):
            item = self.layout_cards.itemAt(i)
            if item:
                card = item.widget()
                if card and isinstance(card, CardReferencia):
                    card.atualizar_preview(self.msg_mapa_proxy, root_croqui)

    def atualizar_cards(self) -> None:
        modo_link_index = None
        modo_camera_index = None
        modo_selecionado_index = self.idx_card_selecionado
        
        for i in range(self.layout_cards.count()):
            item = self.layout_cards.itemAt(i)
            if item:
                card = item.widget()
                if card and isinstance(card, CardReferencia):
                    if card.btn_linkar.isChecked():
                        modo_link_index = i
                    if card.btn_camera.isChecked():
                        modo_camera_index = i

        # Limpa layout
        while self.layout_cards.count():
            item = self.layout_cards.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                
        self.btn_ativo_link = None
        self.btn_ativo_camera = None
                
        if not self.msg_mapa_proxy:
            self.idx_card_selecionado = None
            return
            
        root_croqui = self._obter_root_croqui()
        for i, ref in enumerate(self.msg_mapa_proxy.referencias):
            card = CardReferencia(
                ref,
                i,
                parent=self.container_cards,
                mapa=self.msg_mapa_proxy,
                root_croqui=root_croqui,
            )
            
            # Conecta hover e clique
            card.hover_in.connect(self.destacar_pois.emit)
            card.hover_out.connect(self.remover_destaque_pois.emit)
            card.clicado.connect(self._ao_clicar_card)
            
            # Conecta botões
            card.btn_remover.clicked.connect(lambda checked=False, idx=i: self._confirmar_remover(idx))
            card.btn_editar_alvo.clicked.connect(lambda checked=False, idx=i, r=ref: self._ao_clicar_editar_alvo(idx, r))
            card.btn_inverter.clicked.connect(lambda checked=False, idx=i, r=ref: self._ao_clicar_inverter_ids(idx, r))
            if hasattr(card, 'btn_remover_camera'):
                card.btn_remover_camera.clicked.connect(lambda checked=False, idx=i: self.remover_ajuste_camera.emit(idx))
            
            card.btn_linkar.toggled.connect(lambda checked, c=card: self._on_linkar_toggled(checked, c))
            card.btn_camera.toggled.connect(lambda checked, c=card: self._on_camera_toggled(checked, c))
            card.btn_salvar_camera.clicked.connect(self.salvar_modo_camera.emit)
            
            self.layout_cards.addWidget(card)
            
            if modo_selecionado_index == i:
                card.definir_selecionado(True)
                self.idx_card_selecionado = i
            
            if modo_link_index == i:
                card.btn_vincular.blockSignals(True)
                card.btn_vincular.setChecked(True)
                card.btn_vincular.setText(" Vinculando...")
                card.btn_vincular.setStyleSheet("background-color: #007bff; color: white;")
                self.btn_ativo_link = card.btn_vincular
                card.btn_vincular.blockSignals(False)
            
            if modo_camera_index == i:
                card.btn_camera.blockSignals(True)
                card.btn_camera.setChecked(True)
                card.btn_camera.setStyleSheet("background-color: #6f42c1; color: white;")
                card.btn_salvar_camera.setVisible(True)
                self.btn_ativo_camera = card.btn_camera
                self.card_camera_ativo = card
                card.btn_camera.blockSignals(False)

        if modo_selecionado_index is not None and modo_selecionado_index >= len(self.msg_mapa_proxy.referencias):
            self.idx_card_selecionado = None

    def _ao_clicar_card(self, index: int) -> None:
        if self.idx_card_selecionado == index:
            self.desmarcar_selecao()
        else:
            self.selecionar_referencia(index)

    def desmarcar_selecao(self) -> None:
        """Desmarca o card de referência atualmente selecionado."""
        if self.idx_card_selecionado is not None:
            if 0 <= self.idx_card_selecionado < self.layout_cards.count():
                item = self.layout_cards.itemAt(self.idx_card_selecionado)
                if item:
                    card = item.widget()
                    if isinstance(card, CardReferencia):
                        card.definir_selecionado(False)
            self.idx_card_selecionado = None
            self.referencia_desmarcada.emit()

    def selecionar_referencia(self, index: int) -> None:
        """Seleciona programaticamente a referência pelo índice do card."""
        if self.idx_card_selecionado is not None and self.idx_card_selecionado != index:
            if 0 <= self.idx_card_selecionado < self.layout_cards.count():
                item = self.layout_cards.itemAt(self.idx_card_selecionado)
                if item:
                    card = item.widget()
                    if isinstance(card, CardReferencia):
                        card.definir_selecionado(False)
                        if card.btn_vincular.isChecked() and self.btn_ativo_link == card.btn_vincular:
                            card.btn_vincular.setChecked(False)
        if 0 <= index < self.layout_cards.count():
            item = self.layout_cards.itemAt(index)
            if item:
                card = item.widget()
                if isinstance(card, CardReferencia):
                    card.definir_selecionado(True)
                    self.idx_card_selecionado = index
                    self.scroll_area.ensureWidgetVisible(card)
                    self.referencia_selecionada.emit(index, card.referencia)

    def _referencias_iguais(self, ref1: Any, ref2: Any) -> bool:
        alvo1 = getattr(ref1, "alvo_uid", "")
        alvo2 = getattr(ref2, "alvo_uid", "")
        if alvo1 and alvo2:
            return bool(alvo1 == alvo2)
        return False

    def _referencia_ja_existe(self, ref_nova: Any) -> bool:
        if not self.msg_mapa_proxy: return False
        for ref in self.msg_mapa_proxy.referencias:
            if self._referencias_iguais(ref, ref_nova):
                return True
        return False

    def _ao_clicar_adicionar(self) -> None:
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

    def _ao_clicar_editar_alvo(self, index: int, ref_antiga: Any) -> None:
        if not self.mapas_controller or not self.mapas_controller.model:
            return
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
                
                if getattr(ref_nova, "alvo_uid", ""):
                    ref_editada.alvo_uid = ref_nova.alvo_uid
                    
                self.mapas_controller.alterar_referencia(
                    self.msg_mapa_proxy, index, ref_antiga, ref_editada
                )

    def _ao_clicar_inverter_ids(self, index: int, ref_antiga: Any) -> None:
        """Inverte a ordem dos nós linkados na referência e registra a alteração no histórico."""
        if not self.mapas_controller or not self.msg_mapa_proxy:
            return
        from editor.models.readonly_proxy import _copia_segura

        ref_nova = _copia_segura(ref_antiga)
        if ref_antiga.pontos_uids:
            pontos_invertidos = list(reversed(ref_antiga.pontos_uids))
            del ref_nova.pontos_uids[:]
            ref_nova.pontos_uids.extend(pontos_invertidos)

        self.mapas_controller.alterar_referencia(
            self.msg_mapa_proxy, index, ref_antiga, ref_nova
        )

    def _confirmar_remover(self, index: int) -> None:
        self._limpar_modos_ativos()
        if self.idx_card_selecionado == index:
            self.desmarcar_selecao()
        elif self.idx_card_selecionado is not None and self.idx_card_selecionado > index:
            self.idx_card_selecionado -= 1
        if self.mapas_controller:
            self.mapas_controller.deletar_referencia(self.msg_mapa_proxy, index)

    def _on_linkar_toggled(self, checked: bool, card: CardReferencia) -> None:
        if checked:
            # Desmarca qualquer outro botão de ação
            self._limpar_modos_ativos()
            self.btn_ativo_link = card.btn_vincular
            card.btn_vincular.setText(" Vinculando...")
            card.btn_vincular.setStyleSheet("background-color: #007bff; color: white;")
            self.selecionar_referencia(card.index)
            self.iniciar_modo_linkagem.emit(card.index, card.referencia)
        else:
            if self.btn_ativo_link == card.btn_vincular:
                self.btn_ativo_link = None
                self.parar_modo_linkagem.emit()
            card.btn_vincular.setText(" Vincular Elementos")
            card.btn_vincular.setStyleSheet("")

    def _on_camera_toggled(self, checked: bool, card: CardReferencia) -> None:
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

    def forcar_parada_camera(self) -> None:
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

    def _limpar_modos_ativos(self) -> None:
        if self.btn_ativo_link:
            btn = self.btn_ativo_link
            self.btn_ativo_link = None
            btn.setChecked(False)
        if self.btn_ativo_camera:
            btn_cam = self.btn_ativo_camera
            self.btn_ativo_camera = None
            btn_cam.setChecked(False)

