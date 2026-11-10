# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Painel de Qualidade e Prontidão do Croqui (estilo Google Play Console).

Exibe a `nota_qualidade` total em escala aberta aditiva, o status de publicação
(`Rascunho` / `Publicado`), o controle de `publicar_croqui` via histórico de Undo/Redo
e as 3 etapas de tarefas colapsáveis (expandos) em cascata automática com botões de
ação rápida (`ContextoUIPath`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from editor.controllers.croqui_controller import CroquiController
from editor.core.avaliador_nota_qualidade import (
    ResumoEtapaQualidade,
    TarefaQualidade,
    avaliar_nota_qualidade_croqui,
)
from editor.models.croqui_model import CroquiModel


class CardTarefaQualidade(QFrame):
    """Card visual que apresenta o progresso e os botões de ação rápida de uma `TarefaQualidade`."""

    def __init__(
        self,
        tarefa: TarefaQualidade,
        ao_clicar_acao: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CardTarefaQualidade")
        self._ao_clicar_acao = ao_clicar_acao
        self._pool_botoes: list[QPushButton] = []
        self._uris_botoes: list[str] = ["", "", "", ""]
        self.botoes_acao: list[QPushButton] = []

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(14, 12, 14, 12)
        layout_principal.setSpacing(6)

        linha_topo = QHBoxLayout()
        linha_topo.setSpacing(8)

        self.label_titulo = QLabel(self)
        self.label_titulo.setStyleSheet("font-weight: 600; font-size: 10.5pt; color: #212529;")
        linha_topo.addWidget(self.label_titulo, stretch=1)

        self.label_pontos = QLabel(self)
        linha_topo.addWidget(self.label_pontos)
        layout_principal.addLayout(linha_topo)

        self.label_descricao = QLabel(self)
        self.label_descricao.setWordWrap(True)
        self.label_descricao.setStyleSheet("color: #495057; font-size: 9.5pt;")
        layout_principal.addWidget(self.label_descricao)

        linha_progresso = QHBoxLayout()
        linha_progresso.setSpacing(10)

        self.barra_progresso = QProgressBar(self)
        self.barra_progresso.setFixedHeight(10)
        self.barra_progresso.setTextVisible(False)
        linha_progresso.addWidget(self.barra_progresso, stretch=1)

        self.label_detalhe_progresso = QLabel(self)
        self.label_detalhe_progresso.setStyleSheet("color: #6c757d; font-size: 9pt;")
        linha_progresso.addWidget(self.label_detalhe_progresso)
        layout_principal.addLayout(linha_progresso)

        self.container_acoes = QWidget(self)
        self.layout_acoes = QHBoxLayout(self.container_acoes)
        self.layout_acoes.setContentsMargins(0, 4, 0, 0)
        self.layout_acoes.setSpacing(8)
        for indice in range(4):
            btn = QPushButton(self.container_acoes)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { background-color: #f6f8fa; color: #2b579a; "
                "border: 1px solid #d0d7de; border-radius: 4px; padding: 4px 10px; "
                "font-size: 8.5pt; font-weight: 600; } "
                "QPushButton:hover { background-color: #e7f1ff; border-color: #2b579a; }"
            )
            btn.clicked.connect(lambda _checked=False, idx=indice: self._disparar_acao_indice(idx))
            self.layout_acoes.addWidget(btn)
            self._pool_botoes.append(btn)
        self.layout_acoes.addStretch(1)
        layout_principal.addWidget(self.container_acoes)

        self.atualizar_tarefa(tarefa)

    def _disparar_acao_indice(self, indice: int) -> None:
        self._ao_clicar_acao(self._uris_botoes[indice])

    def atualizar_tarefa(self, tarefa: TarefaQualidade) -> None:
        """Atualiza textos, barra de progresso e botões de ação rápida do card."""
        icone = "✅" if tarefa.concluida else ("⏳" if tarefa.pontos_obtidos > 0 else "⭕")
        self.label_titulo.setText(f"{icone} {tarefa.titulo}")
        self.label_pontos.setText(f"+{tarefa.pontos_obtidos} / {tarefa.pontos_maximos} pts")

        cor_badge = "#198754" if tarefa.concluida else "#2b579a"
        fundo_badge = "#d1e7dd" if tarefa.concluida else "#e7f1ff"
        self.label_pontos.setStyleSheet(
            f"background-color: {fundo_badge}; color: {cor_badge}; "
            "border-radius: 10px; padding: 2px 10px; font-weight: bold; font-size: 9pt;"
        )

        borda = "#badbcc" if tarefa.concluida else "#dee2e6"
        fundo_card = "#f8fffb" if tarefa.concluida else "#ffffff"
        self.setStyleSheet(
            f"QFrame#CardTarefaQualidade {{ background-color: {fundo_card}; "
            f"border: 1px solid {borda}; border-radius: 6px; }}"
        )

        self.label_descricao.setText(tarefa.descricao)
        self.barra_progresso.setMaximum(max(1, tarefa.progresso_total))
        self.barra_progresso.setValue(min(tarefa.progresso_atual, max(1, tarefa.progresso_total)))
        self.label_detalhe_progresso.setText(f"{tarefa.progresso_atual}/{tarefa.progresso_total}")

        acoes_visiveis = tarefa.acoes[:4]
        self.botoes_acao = []
        for idx, btn in enumerate(self._pool_botoes):
            if idx < len(acoes_visiveis):
                acao = acoes_visiveis[idx]
                btn.setText(acao.rotulo)
                self._uris_botoes[idx] = acao.uri_contexto
                btn.setVisible(True)
                self.botoes_acao.append(btn)
            else:
                self._uris_botoes[idx] = ""
                btn.setVisible(False)

        self.container_acoes.setVisible(bool(self.botoes_acao))


class SecaoEtapaExpansivel(QFrame):
    """Seção colapsável (expando) que agrupa os cards de tarefas de uma Etapa."""

    def __init__(
        self,
        resumo_etapa: ResumoEtapaQualidade,
        ao_clicar_acao: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SecaoEtapaExpansivel")
        self.numero_etapa = resumo_etapa.numero_etapa
        self._ao_clicar_acao = ao_clicar_acao
        self._expandida = True
        self.alterado_manualmente = False
        self.cards_por_id: dict[str, CardTarefaQualidade] = {}

        self.setStyleSheet(
            "QFrame#SecaoEtapaExpansivel { background-color: #f8f9fa; "
            "border: 1px solid #ced4da; border-radius: 8px; }"
        )

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(12, 10, 12, 10)
        layout_raiz.setSpacing(8)

        linha_cabecalho = QHBoxLayout()
        linha_cabecalho.setSpacing(10)

        self.botao_cabecalho = QPushButton(self)
        self.botao_cabecalho.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_cabecalho.setStyleSheet(
            "QPushButton { border: none; background: transparent; text-align: left; "
            "font-size: 11pt; font-weight: bold; color: #212529; padding: 4px; }"
        )
        self.botao_cabecalho.clicked.connect(self._alternar_manual)
        linha_cabecalho.addWidget(self.botao_cabecalho, stretch=1)

        self.label_progresso_etapa = QLabel(self)
        self.label_progresso_etapa.setStyleSheet(
            "font-size: 9.5pt; font-weight: 600; color: #495057;"
        )
        linha_cabecalho.addWidget(self.label_progresso_etapa)
        layout_raiz.addLayout(linha_cabecalho)

        self.container_tarefas = QWidget(self)
        self.layout_tarefas = QVBoxLayout(self.container_tarefas)
        self.layout_tarefas.setContentsMargins(0, 4, 0, 0)
        self.layout_tarefas.setSpacing(8)
        layout_raiz.addWidget(self.container_tarefas)

        self.atualizar_etapa(resumo_etapa)

    def esta_expandida(self) -> bool:
        """Retorna True se o corpo de tarefas da etapa estiver expandido."""
        return self._expandida

    def definir_expandida(self, expandida: bool, *, manual: bool = False) -> None:
        """Define o estado de expansão da seção e atualiza o ícone de seta do cabeçalho."""
        self._expandida = expandida
        if manual:
            self.alterado_manualmente = True
        self.container_tarefas.setVisible(expandida)
        self._atualizar_texto_cabecalho()

    def _alternar_manual(self) -> None:
        self.definir_expandida(not self._expandida, manual=True)

    def _atualizar_texto_cabecalho(self) -> None:
        seta = "▼" if self._expandida else "▶"
        status_icone = "✅" if getattr(self, "_concluida", False) else "📋"
        titulo = getattr(self, "_titulo_etapa", f"Etapa {self.numero_etapa}")
        self.botao_cabecalho.setText(f"{seta}  {status_icone}  {titulo}")

    def atualizar_etapa(self, resumo_etapa: ResumoEtapaQualidade) -> None:
        """Sincroniza o cabeçalho e os cards de tarefas com o `ResumoEtapaQualidade`."""
        self._titulo_etapa = resumo_etapa.titulo
        self._concluida = resumo_etapa.concluida
        self.label_progresso_etapa.setText(
            f"{resumo_etapa.tarefas_concluidas}/{resumo_etapa.total_tarefas} concluídas  •  "
            f"+{resumo_etapa.pontos_obtidos} / {resumo_etapa.pontos_maximos} pts"
        )
        self._atualizar_texto_cabecalho()

        for tarefa in resumo_etapa.tarefas:
            card = self.cards_por_id.get(tarefa.id_tarefa)
            if card is None:
                card = CardTarefaQualidade(
                    tarefa,
                    ao_clicar_acao=self._ao_clicar_acao,
                    parent=self.container_tarefas,
                )
                self.cards_por_id[tarefa.id_tarefa] = card
                self.layout_tarefas.addWidget(card)
            else:
                card.atualizar_tarefa(tarefa)


class WidgetPainelQualidade(QWidget):
    """
    Painel principal de Nota de Qualidade e Prontidão de Publicação do Croqui.
    Opera de forma reativa sobre `CroquiModel` e despacha mutações via `CroquiController`.
    """

    def __init__(
        self,
        model: CroquiModel | None = None,
        controller: CroquiController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model: CroquiModel | None = None
        self._controller: CroquiController | None = None
        self._estado_conclusao_anterior: tuple[bool, bool, bool] | None = None

        self.secoes_etapas: dict[int, SecaoEtapaExpansivel] = {}
        self.cards_tarefas: dict[str, CardTarefaQualidade] = {}

        self._construir_interface()
        if model is not None:
            self.set_model_e_controller(model, controller)

    def _construir_interface(self) -> None:
        layout_externo = QVBoxLayout(self)
        layout_externo.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout_externo.addWidget(scroll)

        conteudo = QWidget(scroll)
        self._layout_conteudo = QVBoxLayout(conteudo)
        self._layout_conteudo.setContentsMargins(24, 20, 24, 24)
        self._layout_conteudo.setSpacing(16)
        scroll.setWidget(conteudo)

        # Card de cabeçalho (Placar + Status + Botão de Publicação)
        card_topo = QFrame(conteudo)
        card_topo.setObjectName("CardTopoPainelQualidade")
        card_topo.setStyleSheet(
            "QFrame#CardTopoPainelQualidade { background-color: #ffffff; "
            "border: 1px solid #d0d7de; border-radius: 10px; }"
        )
        layout_topo = QVBoxLayout(card_topo)
        layout_topo.setContentsMargins(20, 16, 20, 16)
        layout_topo.setSpacing(10)

        linha_placar = QHBoxLayout()
        linha_placar.setSpacing(16)

        coluna_nota = QVBoxLayout()
        titulo_painel = QLabel("Painel de Qualidade do Croqui", card_topo)
        titulo_painel.setStyleSheet("font-size: 13pt; font-weight: bold; color: #212529;")
        coluna_nota.addWidget(titulo_painel)

        subtitulo_painel = QLabel(
            "Complete as tarefas abaixo para elevar a nota de qualidade e destacar este croqui no aplicativo.",
            card_topo,
        )
        subtitulo_painel.setWordWrap(True)
        subtitulo_painel.setStyleSheet("color: #6c757d; font-size: 9.5pt;")
        coluna_nota.addWidget(subtitulo_painel)
        linha_placar.addLayout(coluna_nota, stretch=1)

        self.label_nota_qualidade = QLabel("0 pts", card_topo)
        self.label_nota_qualidade.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_nota_qualidade.setStyleSheet(
            "background-color: #e7f1ff; color: #2b579a; border: 1px solid #b6d4fe; "
            "border-radius: 10px; padding: 8px 18px; font-size: 16pt; font-weight: bold;"
        )
        linha_placar.addWidget(self.label_nota_qualidade)
        layout_topo.addLayout(linha_placar)

        linha_publicacao = QHBoxLayout()
        linha_publicacao.setSpacing(12)

        self.label_status_publicacao = QLabel("Status: Rascunho", card_topo)
        self.label_status_publicacao.setStyleSheet("font-size: 10pt; font-weight: 600;")
        linha_publicacao.addWidget(self.label_status_publicacao)

        self.label_requisito_publicacao = QLabel(card_topo)
        self.label_requisito_publicacao.setStyleSheet("color: #6c757d; font-size: 9.5pt;")
        linha_publicacao.addWidget(self.label_requisito_publicacao, stretch=1)

        self.botao_publicar = QPushButton("Publicar Croqui", card_topo)
        self.botao_publicar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_publicar.clicked.connect(self._ao_clicar_publicar)
        linha_publicacao.addWidget(self.botao_publicar)
        layout_topo.addLayout(linha_publicacao)

        self.label_aviso_legado = QLabel(
            "⚠️ Este croqui já está marcado como Publicado, mas possui pendências na Etapa 1 "
            "(Requisitos Básicos). Recomendamos concluir os itens abaixo.",
            card_topo,
        )
        self.label_aviso_legado.setWordWrap(True)
        self.label_aviso_legado.setStyleSheet(
            "background-color: #fff3cd; color: #664d03; border: 1px solid #ffecb5; "
            "border-radius: 6px; padding: 8px 12px; font-size: 9.5pt;"
        )
        self.label_aviso_legado.setVisible(False)
        layout_topo.addWidget(self.label_aviso_legado)

        self._layout_conteudo.addWidget(card_topo)

        self._container_secoes = QWidget(conteudo)
        self._layout_secoes = QVBoxLayout(self._container_secoes)
        self._layout_secoes.setContentsMargins(0, 0, 0, 0)
        self._layout_secoes.setSpacing(14)
        self._layout_conteudo.addWidget(self._container_secoes)
        self._layout_conteudo.addStretch(1)

    def set_model_e_controller(
        self,
        model: CroquiModel,
        controller: CroquiController | None = None,
    ) -> None:
        """Vincula o painel a um `CroquiModel` e `CroquiController` e atualiza o diagnóstico."""
        self._model = model
        self._controller = controller
        self._estado_conclusao_anterior = None

        model.dado_alterado.connect(self._ao_mutar_modelo)
        model.repeated_adicionado.connect(self._ao_mutar_modelo)
        model.repeated_removido.connect(self._ao_mutar_modelo)
        model.repeated_item_alterado.connect(self._ao_mutar_modelo)
        model.repeated_movido.connect(self._ao_mutar_modelo)
        model.oneof_alterado.connect(self._ao_mutar_modelo)

        self.atualizar_painel()

    def _ao_mutar_modelo(self, *_args: Any) -> None:
        self.atualizar_painel()

    def _emitir_foco_acao(self, uri_foco: str) -> None:
        if self._model is not None:
            self._model.foco_requisitado.emit(uri_foco)

    def _ao_clicar_publicar(self) -> None:
        if self._model is not None and self._controller is not None:
            croqui_ro = self._model.obter_croqui_readonly()
            publicado_atual = bool(croqui_ro.publicar_croqui)
            self._controller.set_contexto("page:painel")
            self._controller.alterar_primitivo(
                croqui_ro,
                "publicar_croqui",
                publicado_atual,
                not publicado_atual,
            )

    def atualizar_painel(self) -> None:
        """Recalcula o `ResultadoNotaQualidade` e sincroniza o cabeçalho e as 3 etapas."""
        if self._model is None:
            return

        croqui_ro = self._model.obter_croqui_readonly()
        resultado = avaliar_nota_qualidade_croqui(croqui_ro)
        publicado = bool(croqui_ro.publicar_croqui)

        self.label_nota_qualidade.setText(f"{resultado.nota_qualidade} pts")

        if publicado:
            self.label_status_publicacao.setText("Status: ✅ Publicado")
            self.label_status_publicacao.setStyleSheet(
                "font-size: 10pt; font-weight: bold; color: #198754;"
            )
            self.label_requisito_publicacao.setText(
                "Este croqui está marcado para ser incluído no índice público."
            )
            self.botao_publicar.setText("Voltar para Rascunho")
            self.botao_publicar.setEnabled(True)
            self.botao_publicar.setStyleSheet(
                "QPushButton { background-color: #f8f9fa; color: #495057; "
                "border: 1px solid #ced4da; border-radius: 6px; padding: 6px 14px; font-weight: 600; }"
            )
            self.label_aviso_legado.setVisible(not resultado.pronto_para_publicar)
        else:
            self.label_status_publicacao.setText("Status: 📝 Rascunho")
            self.label_status_publicacao.setStyleSheet(
                "font-size: 10pt; font-weight: bold; color: #6c757d;"
            )
            self.label_aviso_legado.setVisible(False)
            self.botao_publicar.setText("Publicar Croqui")
            if resultado.pronto_para_publicar:
                self.label_requisito_publicacao.setText(
                    "Etapa 1 concluída! O croqui já cumpre os requisitos para publicação."
                )
                self.botao_publicar.setEnabled(True)
                self.botao_publicar.setStyleSheet(
                    "QPushButton { background-color: #198754; color: #ffffff; "
                    "border: 1px solid #198754; border-radius: 6px; padding: 6px 14px; font-weight: bold; }"
                )
            else:
                self.label_requisito_publicacao.setText(
                    "Conclua 100% da Etapa 1 para liberar a publicação deste croqui."
                )
                self.botao_publicar.setEnabled(False)
                self.botao_publicar.setStyleSheet(
                    "QPushButton { background-color: #e9ecef; color: #adb5bd; "
                    "border: 1px solid #dee2e6; border-radius: 6px; padding: 6px 14px; font-weight: 600; }"
                )

        for resumo_etapa in resultado.etapas:
            secao = self.secoes_etapas.get(resumo_etapa.numero_etapa)
            if secao is None:
                secao = SecaoEtapaExpansivel(
                    resumo_etapa,
                    ao_clicar_acao=self._emitir_foco_acao,
                    parent=self._container_secoes,
                )
                self.secoes_etapas[resumo_etapa.numero_etapa] = secao
                self._layout_secoes.addWidget(secao)
            else:
                secao.atualizar_etapa(resumo_etapa)
            self.cards_tarefas.update(secao.cards_por_id)

        estado_atual = (
            resultado.etapas[0].concluida,
            resultado.etapas[1].concluida,
            resultado.etapas[2].concluida,
        )
        if estado_atual != self._estado_conclusao_anterior:
            self._estado_conclusao_anterior = estado_atual
            e1_ok, e2_ok, _e3_ok = estado_atual
            if not e1_ok:
                alvos_expansao = {1: True, 2: False, 3: False}
            elif not e2_ok:
                alvos_expansao = {1: False, 2: True, 3: False}
            else:
                alvos_expansao = {1: False, 2: False, 3: True}

            for num_etapa, deve_expandir in alvos_expansao.items():
                secao_alvo = self.secoes_etapas[num_etapa]
                secao_alvo.alterado_manualmente = False
                secao_alvo.definir_expandida(deve_expandir, manual=False)


PaginaPainel = WidgetPainelQualidade
