# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Diálogo de busca para selecionar uma entidade alvo (Grupo, Setor ou Escalada)
e gerar uma nova mensagem croqui_pb2.Mapa.Referencia a partir dela.
Princípios I, II e VI de AGENTS.md.
"""

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.widget_busca_entidades import WidgetBuscaEntidades


class DialogoBuscaReferencia(QDialog):
    """
    Modal de busca para selecionar uma entidade alvo (Grupo, Setor ou Escalada)
    e gerar uma nova mensagem croqui_pb2.Mapa.Referencia a partir dela.
    Reutiliza internamente WidgetBuscaEntidades.
    """

    def __init__(self, model: CroquiModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buscar Referência")
        self.resize(600, 400)

        self.croqui_model: CroquiModel = model
        self.referencia_selecionada: croqui_pb2.Mapa.Referencia | None = None

        self.layout_principal = QVBoxLayout(self)

        # 1. Widget reutilizável de busca de entidades
        self.widget_busca = WidgetBuscaEntidades(
            model=self.croqui_model,
            tipos_permitidos={"Grupo", "Setor", "Escalada"},
            permitir_criacao_nova=False,
            parent=self,
        )
        self.layout_principal.addWidget(self.widget_busca)

        # Atalhos para retrocompatibilidade
        self.input_busca = self.widget_busca.input_busca
        self.lista_resultados = self.widget_busca.lista_resultados

        # 2. Botões OK / Cancelar
        self.bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_ok: QPushButton | None = self.bbox.button(QDialogButtonBox.StandardButton.Ok)
        if self.btn_ok:
            self.btn_ok.setEnabled(self.widget_busca.obter_entidade_selecionada() is not None)

        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        self.layout_principal.addWidget(self.bbox)

        # Conexões do widget de busca
        self.widget_busca.entidade_selecionada.connect(self._on_entidade_selecionada)
        self.widget_busca.entidade_ativada.connect(self._on_entidade_ativada)

    @property
    def todas_entidades(self) -> list[dict[str, Any]]:
        return self.widget_busca.todas_entidades

    @todas_entidades.setter
    def todas_entidades(self, valor: list[dict[str, Any]]) -> None:
        self.widget_busca.todas_entidades = valor

    def _on_entidade_selecionada(self, dados: dict[str, Any]) -> None:
        if self.btn_ok:
            self.btn_ok.setEnabled(bool(dados))

    def _on_entidade_ativada(self, _dados: dict[str, Any]) -> None:
        self.accept()

    def accept(self) -> None:
        dados = self.widget_busca.obter_entidade_selecionada()
        if not dados:
            return

        self.referencia_selecionada = croqui_pb2.Mapa.Referencia()
        alvo_uid = dados.get("uid") or ""
        if not alvo_uid:
            obj = dados.get("escalada_obj") or dados.get("setor_obj") or dados.get("grupo_obj")
            if obj and hasattr(obj, "uid"):
                alvo_uid = str(obj.uid)

        if alvo_uid:
            self.referencia_selecionada.alvo_uid = str(alvo_uid)

        super().accept()

    def obter_referencia(self) -> croqui_pb2.Mapa.Referencia | None:
        return self.referencia_selecionada
