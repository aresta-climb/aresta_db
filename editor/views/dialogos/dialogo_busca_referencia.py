# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QDialogButtonBox, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel

class DialogoBuscaReferencia(QDialog):
    """
    Modal de busca para selecionar uma entidade alvo (Grupo, Setor ou Escalada)
    e gerar uma nova mensagem croqui_pb2.Mapa.Referencia a partir dela.
    """
    def __init__(self, model: CroquiModel, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buscar Referência")
        self.resize(600, 400)
        
        self.croqui_model: CroquiModel = model
        self.referencia_selecionada: Optional[croqui_pb2.Mapa.Referencia] = None
        
        self.layout_principal: QVBoxLayout = QVBoxLayout(self)
        
        # Campo de busca
        self.layout_busca: QHBoxLayout = QHBoxLayout()
        self.layout_busca.addWidget(QLabel("Buscar:"))
        self.input_busca: QLineEdit = QLineEdit()
        self.input_busca.setPlaceholderText("Ex: Bloco Romano, Via Láctea, etc...")
        self.layout_busca.addWidget(self.input_busca)
        self.layout_principal.addLayout(self.layout_busca)
        
        # Lista de resultados
        self.lista_resultados: QListWidget = QListWidget()
        self.layout_principal.addWidget(self.lista_resultados)
        
        # Botões
        self.bbox: QDialogButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_ok: Optional[QPushButton] = self.bbox.button(QDialogButtonBox.StandardButton.Ok)
        if self.btn_ok:
            self.btn_ok.setEnabled(False)
        
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        self.layout_principal.addWidget(self.bbox)
        
        # Conexões
        self.input_busca.textChanged.connect(self._filtrar_resultados)
        self.lista_resultados.itemSelectionChanged.connect(self._on_item_selecionado)
        self.lista_resultados.itemDoubleClicked.connect(self.accept)
        
        self.todas_entidades: List[Dict[str, str]] = []
        self._carregar_entidades()
        self._popular_lista()

    def _obter_nome_escalada(self, escalada: croqui_pb2.Escalada) -> str:
        tipo = escalada.WhichOneof('tipo')
        if not tipo:
            return "Desconhecida"
        return str(getattr(escalada, tipo).nome)

    def _carregar_entidades(self) -> None:
        croqui = self.croqui_model.obter_croqui_readonly()
        
        for pico in croqui.picos:
            for sg in pico.setores_ou_grupos:
                if sg.HasField('grupo'):
                    grupo = sg.grupo.conteudo
                    self.todas_entidades.append({
                        "tipo": "Grupo",
                        "display": f"🎯 Grupo: {pico.nome} > {grupo.nome}",
                        "grupo": grupo.nome,
                        "setor": "",
                        "escalada": ""
                    })
                    for setor_msg in grupo.setores:
                        setor = setor_msg.conteudo
                        self.todas_entidades.append({
                            "tipo": "Setor",
                            "display": f"🎯 Setor: {grupo.nome} > {setor.nome}",
                            "grupo": grupo.nome,
                            "setor": setor.nome,
                            "escalada": ""
                        })
                        for escalada in setor.escaladas:
                            nome_esc = self._obter_nome_escalada(escalada)
                            self.todas_entidades.append({
                                "tipo": "Escalada",
                                "display": f"🧗 Via: {grupo.nome} > {setor.nome} > {nome_esc}",
                                "grupo": grupo.nome,
                                "setor": setor.nome,
                                "escalada": nome_esc
                            })
                elif sg.HasField('setor'):
                    setor = sg.setor.conteudo
                    self.todas_entidades.append({
                        "tipo": "Setor",
                        "display": f"🎯 Setor: {pico.nome} > {setor.nome}",
                        "grupo": "",
                        "setor": setor.nome,
                        "escalada": ""
                    })
                    for escalada in setor.escaladas:
                        nome_esc = self._obter_nome_escalada(escalada)
                        self.todas_entidades.append({
                            "tipo": "Escalada",
                            "display": f"🧗 Via: {setor.nome} > {nome_esc}",
                            "grupo": "",
                            "setor": setor.nome,
                            "escalada": nome_esc
                        })

    def _remover_acentos(self, texto: str) -> str:
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

    def _popular_lista(self, filtro: str = "") -> None:
        self.lista_resultados.clear()
        filtro_lower = self._remover_acentos(filtro.lower())
        
        for entidade in self.todas_entidades:
            display_lower = self._remover_acentos(entidade["display"].lower())
            if filtro_lower in display_lower:
                item = QListWidgetItem(entidade["display"])
                item.setData(Qt.ItemDataRole.UserRole, entidade)
                self.lista_resultados.addItem(item)
                
        if self.lista_resultados.count() > 0:
            self.lista_resultados.setCurrentRow(0)
                
    def _filtrar_resultados(self, texto: str) -> None:
        self._popular_lista(texto)
        
    def _on_item_selecionado(self) -> None:
        items = self.lista_resultados.selectedItems()
        if self.btn_ok:
            self.btn_ok.setEnabled(len(items) > 0)
        
    def accept(self) -> None:
        items = self.lista_resultados.selectedItems()
        if not items:
            return
            
        dados = items[0].data(Qt.ItemDataRole.UserRole)
        
        self.referencia_selecionada = croqui_pb2.Mapa.Referencia()
        if dados["grupo"]:
            self.referencia_selecionada.grupo = dados["grupo"]
        if dados["setor"]:
            self.referencia_selecionada.setor = dados["setor"]
        if dados["escalada"]:
            self.referencia_selecionada.escalada = dados["escalada"]
            
        super().accept()

    def obter_referencia(self) -> Optional[croqui_pb2.Mapa.Referencia]:
        return self.referencia_selecionada

