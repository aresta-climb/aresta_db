# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente reutilizável de busca e listagem de entidades do croqui.
Suporta filtragem por tipo de entidade, mapas, busca sem acentos e criação inline.
Princípios I, II e VI de AGENTS.md.
"""

import unicodedata
from typing import Optional, List, Dict, Any, Set, Tuple
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel


class WidgetBuscaEntidades(QWidget):
    """
    Widget visual reutilizável para busca unificada de entidades do Croqui
    (Grupos, Setores, Escaladas) com filtragem textual, suporte a mapas e criação rápida.
    """

    entidade_selecionada = Signal(dict)
    entidade_ativada = Signal(dict)

    def __init__(
        self,
        model: Optional[CroquiModel] = None,
        croqui: Optional[croqui_pb2.Croqui] = None,
        setor: Optional[Any] = None,
        mapa_filtro: Optional[Any] = None,
        tipos_permitidos: Optional[Set[str]] = None,
        permitir_criacao_nova: bool = False,
        placeholder_busca: str = "Ex: Bloco Romano, Via Láctea, etc...",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self.model = model
        self.croqui = croqui
        self.setor = setor
        self.mapa_filtro = mapa_filtro
        self.tipos_permitidos = tipos_permitidos
        self.permitir_criacao_nova = permitir_criacao_nova
        self.placeholder_busca = placeholder_busca

        self.todas_entidades: List[Dict[str, Any]] = []

        self._setup_ui()
        self.recarregar_entidades()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 1. Campo de busca
        layout_busca = QHBoxLayout()
        lbl_busca = QLabel("Buscar:", self)
        layout_busca.addWidget(lbl_busca)

        self.input_busca = QLineEdit(self)
        self.input_busca.setPlaceholderText(self.placeholder_busca)
        self.input_busca.textChanged.connect(self._ao_alterar_busca)
        layout_busca.addWidget(self.input_busca)

        layout.addLayout(layout_busca)

        # 2. Lista de resultados
        self.lista_resultados = QListWidget(self)
        self.lista_resultados.itemSelectionChanged.connect(self._ao_mudar_selecao)
        self.lista_resultados.itemDoubleClicked.connect(self._ao_item_duplo_clicado)
        layout.addWidget(self.lista_resultados)

    def _remover_acentos(self, texto: str) -> str:
        """Remove marcas diacríticas e acentos para comparação normalizada."""
        return "".join(
            c for c in unicodedata.normalize("NFD", texto)
            if unicodedata.category(c) != "Mn"
        )

    def _extrair_conteudo(self, obj: Any) -> Any:
        if hasattr(obj, "conteudo"):
            return obj.conteudo
        return obj

    def _obter_info_escalada(self, escalada: croqui_pb2.Escalada) -> Tuple[str, str, str]:
        """Retorna (nome, tipo_campo, grau_formatado) de uma mensagem Escalada."""
        tipo_campo = escalada.WhichOneof("tipo")
        if not tipo_campo:
            return ("", "", "")

        conteudo = getattr(escalada, tipo_campo)
        nome = str(getattr(conteudo, "nome", ""))

        grau = ""
        if hasattr(conteudo, "dificuldade"):
            dificuldade = conteudo.dificuldade
            if hasattr(dificuldade, "name"):
                grau = str(dificuldade.name)
            elif dificuldade:
                grau = str(dificuldade)

        return (nome, tipo_campo, grau)

    def _formatar_rotulo_escalada(self, tipo_campo: str, nome: str, grau: str, caminho_hierarquia: str) -> str:
        """Formata o texto de apresentação na lista com ícone semântico."""
        rotulo_tipo = "Boulder" if tipo_campo == "boulder" else "Via"
        sufixo_grau = f" ({grau})" if grau else ""
        if caminho_hierarquia:
            return f"🧗 {rotulo_tipo}: {caminho_hierarquia} > {nome}{sufixo_grau}"
        return f"🧗 {rotulo_tipo}: {nome}{sufixo_grau}"

    def _obter_nomes_mapeados(self) -> Set[str]:
        """Retorna o conjunto de nomes de escaladas já associadas ao mapa ativo."""
        nomes = set()
        if self.mapa_filtro and hasattr(self.mapa_filtro, "referencias"):
            for ref in self.mapa_filtro.referencias:
                if ref.escalada:
                    nomes.add(ref.escalada)
        return nomes

    def _carregar_entidades(self) -> None:
        """Extrai todas as entidades do modelo ou setor aplicando filtros de tipos e mapa."""
        self.todas_entidades.clear()
        nomes_mapeados = self._obter_nomes_mapeados()

        croqui_msg = None
        if self.model and hasattr(self.model, "obter_croqui_readonly"):
            croqui_msg = self.model.obter_croqui_readonly()
        elif self.croqui:
            croqui_msg = self.croqui

        if croqui_msg and hasattr(croqui_msg, "picos"):
            for pico in croqui_msg.picos:
                for sg in pico.setores_ou_grupos:
                    if sg.HasField("grupo"):
                        grupo = self._extrair_conteudo(sg.grupo)
                        self.todas_entidades.append({
                            "tipo": "Grupo",
                            "display": f"🎯 Grupo: {pico.nome} > {grupo.nome}",
                            "grupo": grupo.nome,
                            "grupo_obj": grupo,
                            "setor": "",
                            "setor_obj": None,
                            "escalada": "",
                            "escalada_obj": None,
                            "tipo_escalada": "",
                            "grau": "",
                            "nova": False,
                        })
                        for setor_msg in grupo.setores:
                            setor = self._extrair_conteudo(setor_msg)
                            self.todas_entidades.append({
                                "tipo": "Setor",
                                "display": f"🎯 Setor: {grupo.nome} > {setor.nome}",
                                "grupo": grupo.nome,
                                "grupo_obj": grupo,
                                "setor": setor.nome,
                                "setor_obj": setor,
                                "escalada": "",
                                "escalada_obj": None,
                                "tipo_escalada": "",
                                "grau": "",
                                "nova": False,
                            })
                            for esc in setor.escaladas:
                                nome_esc, tipo_campo, grau = self._obter_info_escalada(esc)
                                if not nome_esc:
                                    continue
                                ja_mapeada = nome_esc in nomes_mapeados
                                caminho = f"{grupo.nome} > {setor.nome}"
                                rotulo = self._formatar_rotulo_escalada(tipo_campo, nome_esc, grau, caminho)
                                self.todas_entidades.append({
                                    "tipo": "Escalada",
                                    "display": rotulo,
                                    "grupo": grupo.nome,
                                    "grupo_obj": grupo,
                                    "setor": setor.nome,
                                    "setor_obj": setor,
                                    "escalada": nome_esc,
                                    "escalada_obj": esc,
                                    "tipo_escalada": tipo_campo,
                                    "grau": grau,
                                    "nova": False,
                                    "ja_mapeada": ja_mapeada,
                                })
                    elif sg.HasField("setor"):
                        setor = self._extrair_conteudo(sg.setor)
                        self.todas_entidades.append({
                            "tipo": "Setor",
                            "display": f"🎯 Setor: {pico.nome} > {setor.nome}",
                            "grupo": "",
                            "grupo_obj": None,
                            "setor": setor.nome,
                            "setor_obj": setor,
                            "escalada": "",
                            "escalada_obj": None,
                            "tipo_escalada": "",
                            "grau": "",
                            "nova": False,
                            "ja_mapeada": False,
                        })
                        for esc in setor.escaladas:
                            nome_esc, tipo_campo, grau = self._obter_info_escalada(esc)
                            if not nome_esc:
                                continue
                            ja_mapeada = nome_esc in nomes_mapeados
                            caminho = setor.nome
                            rotulo = self._formatar_rotulo_escalada(tipo_campo, nome_esc, grau, caminho)
                            self.todas_entidades.append({
                                "tipo": "Escalada",
                                "display": rotulo,
                                "grupo": "",
                                "grupo_obj": None,
                                "setor": setor.nome,
                                "setor_obj": setor,
                                "escalada": nome_esc,
                                "escalada_obj": esc,
                                "tipo_escalada": tipo_campo,
                                "grau": grau,
                                "nova": False,
                                "ja_mapeada": ja_mapeada,
                            })

        elif self.setor and hasattr(self.setor, "escaladas"):
            setor = self._extrair_conteudo(self.setor)
            for esc in setor.escaladas:
                nome_esc, tipo_campo, grau = self._obter_info_escalada(esc)
                if not nome_esc:
                    continue
                ja_mapeada = nome_esc in nomes_mapeados
                caminho = getattr(setor, "nome", "")
                rotulo = self._formatar_rotulo_escalada(tipo_campo, nome_esc, grau, caminho)
                self.todas_entidades.append({
                    "tipo": "Escalada",
                    "display": rotulo,
                    "grupo": "",
                    "grupo_obj": None,
                    "setor": getattr(setor, "nome", ""),
                    "setor_obj": setor,
                    "escalada": nome_esc,
                    "escalada_obj": esc,
                    "tipo_escalada": tipo_campo,
                    "grau": grau,
                    "nova": False,
                    "ja_mapeada": ja_mapeada,
                })

        # Filtro de tipos permitidos
        if self.tipos_permitidos is not None:
            self.todas_entidades = [
                e for e in self.todas_entidades
                if e["tipo"] in self.tipos_permitidos
            ]

    def _popular_lista(self, filtro: str = "") -> None:
        """Preenche a lista filtrando por texto e adicionando opção de criação se habilitada."""
        self.lista_resultados.clear()
        filtro_norm = self._remover_acentos(filtro.strip().lower())

        for entidade in self.todas_entidades:
            display_norm = self._remover_acentos(entidade["display"].lower())
            if not filtro_norm or filtro_norm in display_norm:
                rotulo = entidade["display"]
                ja_mapeada = bool(entidade.get("ja_mapeada", False))
                if ja_mapeada:
                    rotulo = f"{rotulo} [já no mapa]"
                item = QListWidgetItem(rotulo)
                item.setData(Qt.ItemDataRole.UserRole, dict(entidade))
                if ja_mapeada:
                    item.setForeground(QColor("#888888"))
                    item.setToolTip("Esta escalada já possui traçado neste mapa. Para ajustar, selecione a linha na imagem ou no painel lateral.")
                self.lista_resultados.addItem(item)

        termo_digitado = filtro.strip()
        if self.permitir_criacao_nova and termo_digitado:
            item_novo = QListWidgetItem(f"➕ Criar Nova Escalada: \"{termo_digitado}\"")
            item_novo.setData(Qt.ItemDataRole.UserRole, {
                "nova": True,
                "nome": termo_digitado,
                "tipo": "boulder",
                "grau": "V4",
                "tipo_entidade": "Escalada",
                "setor_obj": self.setor,
                "ja_mapeada": False,
            })
            self.lista_resultados.addItem(item_novo)

        if self.lista_resultados.count() > 0:
            self.lista_resultados.setCurrentRow(0)
        else:
            self._ao_mudar_selecao()

    def _ao_alterar_busca(self, texto: str) -> None:
        self._popular_lista(texto)

    def _ao_mudar_selecao(self) -> None:
        dados = self.obter_entidade_selecionada() or {}
        self.entidade_selecionada.emit(dados)

    def _ao_item_duplo_clicado(self, _item: Any) -> None:
        dados = self.obter_entidade_selecionada() or {}
        if dados:
            self.entidade_ativada.emit(dados)

    def obter_entidade_selecionada(self) -> Optional[Dict[str, Any]]:
        """Retorna os dados da entidade atualmente selecionada na lista, ou None."""
        itens = self.lista_resultados.selectedItems()
        if not itens:
            return None
        dados = itens[0].data(Qt.ItemDataRole.UserRole)
        return dict(dados) if dados else None

    def definir_filtro(self, texto: str) -> None:
        """Altera o texto do campo de busca e atualiza os resultados."""
        self.input_busca.setText(texto)

    def recarregar_entidades(self) -> None:
        """Recarrega os dados do modelo/setor e atualiza a exibição da lista."""
        self._carregar_entidades()
        self._popular_lista(self.input_busca.text())
