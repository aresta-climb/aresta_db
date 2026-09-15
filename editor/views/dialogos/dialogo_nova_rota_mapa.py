# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Paleta rápida para seleção de escalada não mapeada no setor ou criação inline de nova rota.
Atende à Jornada de Anotação de Rotas em Mapas (AGENTS.md).
Reutiliza o componente unificado WidgetBuscaEntidades.
"""

from typing import Optional, List, Dict, Any, Tuple
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QWidget,
    QFormLayout,
)
from PySide6.QtCore import Qt
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.widget_busca_entidades import WidgetBuscaEntidades


class DialogoNovaRotaMapa(QDialog):
    """
    Diálogo modal de busca ágil para associar uma rota a uma escalada existente no croqui/setor
    ou criar uma nova escalada inline sem sair do Editor de Mapas.
    """

    OPCOES_TIPO: List[Tuple[str, str]] = [
        ("Boulder", "boulder"),
        ("Via Esportiva", "via_esportiva"),
        ("Via Móvel", "via_movel"),
        ("Via Múltiplas Enfiadas", "via_multiplas_enfiadas"),
        ("Highline", "highline"),
    ]

    def __init__(
        self,
        setor: Optional[Any] = None,
        mapa: Optional[Any] = None,
        model: Optional[CroquiModel] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nova Rota no Mapa")
        self.resize(520, 440)

        self.setor = setor
        self.mapa = mapa
        self.model = model

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 1. Título descritivo
        lbl_busca = QLabel("Buscar escalada existente ou digitar nome da nova:", self)
        lbl_busca.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_busca)

        # 2. Componente unificado de busca de entidades
        self.widget_busca = WidgetBuscaEntidades(
            model=self.model,
            setor=self.setor,
            mapa_filtro=self.mapa,
            tipos_permitidos={"Escalada"},
            permitir_criacao_nova=True,
            placeholder_busca="Ex: Fissura dos Sonhos, Boulder Central...",
            parent=self,
        )
        layout.addWidget(self.widget_busca)

        # Atalhos para retrocompatibilidade
        self.input_busca = self.widget_busca.input_busca
        self.lista_resultados = self.widget_busca.lista_resultados

        # 3. Painel inline de criação para nova rota
        self.painel_nova_rota = QWidget(self)
        layout_form = QFormLayout(self.painel_nova_rota)
        layout_form.setContentsMargins(0, 5, 0, 5)

        self.combo_tipo = QComboBox(self)
        for rotulo, chave in self.OPCOES_TIPO:
            self.combo_tipo.addItem(rotulo, chave)
        layout_form.addRow("Tipo:", self.combo_tipo)

        self.edit_grau = QLineEdit(self)
        self.edit_grau.setPlaceholderText("Ex: V4, 6sup, 7a...")
        self.edit_grau.setText("V4")
        layout_form.addRow("Grau:", self.edit_grau)

        self.painel_nova_rota.setVisible(False)
        layout.addWidget(self.painel_nova_rota)

        # 4. Botões de ação
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()

        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_cancelar.clicked.connect(self.reject)
        layout_botoes.addWidget(self.btn_cancelar)

        self.btn_confirmar = QPushButton("Confirmar", self)
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.setEnabled(
            self.widget_busca.obter_entidade_selecionada() is not None
        )
        self.btn_confirmar.setStyleSheet("""
            QPushButton {
                background-color: #2b579a;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1e3f6f; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        self.btn_confirmar.clicked.connect(self.accept)
        layout_botoes.addWidget(self.btn_confirmar)

        layout.addLayout(layout_botoes)

        # Conexões do widget de busca
        self.widget_busca.entidade_selecionada.connect(self._ao_selecionar_entidade)
        self.widget_busca.entidade_ativada.connect(self._ao_entidade_ativada)

        # Inicializa visibilidade do painel conforme o item inicial selecionado
        self._ao_selecionar_entidade(
            self.widget_busca.obter_entidade_selecionada() or {}
        )

    @property
    def escaladas_disponiveis(self) -> List[Dict[str, Any]]:
        """Propriedade para compatibilidade com leitores de escaladas disponíveis."""
        return [
            {
                "nome": e["escalada"],
                "tipo": e["tipo_escalada"],
                "grau": e["grau"],
                "obj": e.get("escalada_obj"),
            }
            for e in self.widget_busca.todas_entidades
            if e.get("tipo") == "Escalada"
        ]

    def _ao_selecionar_entidade(self, dados: Dict[str, Any]) -> None:
        """Atualiza a visibilidade do painel de tipo/grau e o botão confirmar."""
        if dados:
            if dados.get("ja_mapeada", False):
                self.painel_nova_rota.setVisible(False)
                self.btn_confirmar.setEnabled(False)
                return

            eh_nova = bool(dados.get("nova", False))
            self.painel_nova_rota.setVisible(eh_nova)
            self.btn_confirmar.setEnabled(True)
        else:
            self.painel_nova_rota.setVisible(False)
            self.btn_confirmar.setEnabled(False)

    def _ao_entidade_ativada(self, dados: Dict[str, Any]) -> None:
        """Aceita o diálogo em caso de ativação/duplo-clique se a rota não estiver mapeada."""
        if dados and dados.get("ja_mapeada"):
            return
        if self.btn_confirmar.isEnabled():
            self.accept()

    def _on_item_duplo_clicado(self, _item: Any) -> None:
        """Método de retrocompatibilidade para testes."""
        dados = self.widget_busca.obter_entidade_selecionada() or {}
        if dados and dados.get("ja_mapeada"):
            return
        if self.btn_confirmar.isEnabled():
            self.accept()

    def _ao_selecionar_item(self) -> None:
        """Método de retrocompatibilidade para testes."""
        dados = self.widget_busca.obter_entidade_selecionada() or {}
        self._ao_selecionar_entidade(dados)

    def obter_dados_rota(self) -> Dict[str, Any]:
        """Retorna os dados completos da rota selecionada ou criada para traçado."""
        dados_entidade = self.widget_busca.obter_entidade_selecionada()
        if not dados_entidade:
            return {}

        dados = dict(dados_entidade)
        eh_nova = bool(dados.get("nova", False))

        if eh_nova:
            dados["tipo"] = str(self.combo_tipo.currentData() or "boulder")
            dados["grau"] = str(self.edit_grau.text().strip())
            dados["setor_obj"] = self.setor
        else:
            dados["nome"] = dados.get("escalada") or dados.get("nome", "")
            dados["tipo"] = dados.get("tipo_escalada") or dados.get("tipo", "")
            dados["grau"] = dados.get("grau", "")
            dados["obj"] = dados.get("escalada_obj")
            dados["setor_obj"] = dados.get("setor_obj") or self.setor
            dados["setor_nome"] = dados.get("setor", "")
            dados["grupo_nome"] = dados.get("grupo", "")

        return dados
