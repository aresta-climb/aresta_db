# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Painel de curadoria e revisão 1 a 1 de mídias de beta (YouTube, Instagram, Blogs)
integrado ao CroquiModel e ao CroquiController (Undo/Redo).
"""

from collections.abc import Callable, Sequence
from functools import partial
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.dialogo_coletar_betas import (
    DialogoColetarBetas,
    InfoEscaladaColeta,
    extrair_escaladas_do_croqui,
)
from coleta_de_betas.curadoria.provedor_imagem_aresta import (
    ProvedorImagemAresta,
    WorkerProvedorImagem,
    obter_pixmap_fallback,
)

INSTRUCOES_MCP_AVALIACAO = (
    "💡 Para avaliar e pontuar automaticamente estes candidatos com IA, peça ao agente conectado via MCP:\n"
    '"Execute a skill avaliar_betas_croqui para avaliar e pontuar os betas_nao_scorados deste croqui."'
)


_ROTULOS_POR_FONTE: dict[int, str] = {
    beta_pb2.FonteMidia.YOUTUBE: "YouTube",
    beta_pb2.FonteMidia.INSTAGRAM: "Instagram",
    beta_pb2.FonteMidia.BLOG: "Blog",
    beta_pb2.FonteMidia.TIKTOK: "TikTok",
    beta_pb2.FonteMidia.FACEBOOK: "Facebook",
    beta_pb2.FonteMidia.TWITTER: "Twitter",
    beta_pb2.FonteMidia.REDDIT: "Reddit",
    beta_pb2.FonteMidia.OUTRO_UGC: "Outro UGC",
}


def _rotulo_fonte(fonte: int) -> str:
    return _ROTULOS_POR_FONTE.get(fonte, "Mídia")


class CardBetaCuradoria(QFrame):
    """
    Card individual de revisão 1 a 1 de uma mídia ou candidato a beta, exibindo
    thumbnail estilo preview do WhatsApp (com cache offline), metadados e botões de ação.
    """

    def __init__(
        self,
        midia: beta_pb2.MidiaBeta,
        nome_escalada: str,
        nome_setor: str = "",
        score_llm: int | None = None,
        justificativa_llm: str = "",
        snippets: Sequence[str] = (),
        ao_aprovar: Callable[[], Any] | None = None,
        ao_rejeitar: Callable[[], Any] | None = None,
        ao_restaurar: Callable[[], Any] | None = None,
        provedor_imagem: ProvedorImagemAresta | None = None,
        carregar_assincrono: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.midia = midia
        self.nome_escalada = nome_escalada
        self.nome_setor = nome_setor
        self._worker_imagem: WorkerProvedorImagem | None = None
        self._provedor = provedor_imagem or ProvedorImagemAresta()

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CardBetaCuradoria {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-bottom: 6px;
                padding: 6px;
            }
            CardBetaCuradoria:hover {
                border: 1px solid #0066cc;
            }
        """)

        layout_principal = QHBoxLayout(self)
        layout_principal.setContentsMargins(8, 8, 8, 8)
        layout_principal.setSpacing(12)

        self.label_thumbnail = QLabel()
        self.label_thumbnail.setFixedSize(120, 90)
        self.label_thumbnail.setScaledContents(True)
        if carregar_assincrono:
            self.label_thumbnail.setPixmap(obter_pixmap_fallback(self.midia.fonte))
            if self.midia.url:
                self._worker_imagem = WorkerProvedorImagem(
                    self.midia.url,
                    self.midia.fonte,
                    provedor=self._provedor,
                    parent=self,
                )
                self._worker_imagem.imagem_carregada.connect(self._ao_carregar_thumbnail)
                self._worker_imagem.start()
        else:
            self.label_thumbnail.setPixmap(
                self._provedor.obter_pixmap(self.midia.url, self.midia.fonte)
            )
        layout_principal.addWidget(self.label_thumbnail, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout_textos = QVBoxLayout()
        layout_textos.setSpacing(4)

        texto_via_setor = (
            f"🧗 Via: {nome_escalada}  •  📍 {nome_setor}"
            if nome_setor
            else f"🧗 Via: {nome_escalada}"
        )
        self.label_via_setor = QLabel(texto_via_setor)
        self.label_via_setor.setStyleSheet(
            "background-color: #f0fdf4; color: #166534; font-weight: bold; "
            "border: 1px solid #bbf7d0; border-radius: 4px; padding: 2px 8px; font-size: 11px;"
        )
        self.label_via_setor.setWordWrap(True)
        layout_textos.addWidget(self.label_via_setor)

        layout_cabecalho = QHBoxLayout()
        titulo_exibido = self.midia.titulo or self.midia.url
        self.label_titulo = QLabel(titulo_exibido)
        self.label_titulo.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.label_titulo.setWordWrap(True)
        layout_cabecalho.addWidget(self.label_titulo, stretch=1)

        self.label_fonte = QLabel(_rotulo_fonte(self.midia.fonte))
        self.label_fonte.setStyleSheet(
            "background-color: #eef2ff; color: #1e40af; font-weight: bold; "
            "border-radius: 4px; padding: 2px 6px; font-size: 10px;"
        )
        layout_cabecalho.addWidget(self.label_fonte)

        self.label_score: QLabel | None = None
        if score_llm is not None:
            cor_score = (
                "#28a745" if score_llm >= 80 else ("#ffc107" if score_llm >= 50 else "#dc3545")
            )
            self.label_score = QLabel(f"Confiança: {score_llm}%")
            self.label_score.setStyleSheet(
                f"background-color: {cor_score}; color: #ffffff; font-weight: bold; "
                "border-radius: 4px; padding: 3px 6px;"
            )
            layout_cabecalho.addWidget(self.label_score)

        layout_textos.addLayout(layout_cabecalho)

        self.label_url = QLabel(f'<a href="{self.midia.url}">{self.midia.url}</a>')
        self.label_url.setOpenExternalLinks(True)
        self.label_url.setStyleSheet("color: #0066cc; font-size: 11px;")
        layout_textos.addWidget(self.label_url)

        self.label_reasoning: QLabel | None = None
        if justificativa_llm:
            self.label_reasoning = QLabel(justificativa_llm)
            self.label_reasoning.setStyleSheet(
                "color: #444444; font-size: 11px; font-style: italic;"
            )
            self.label_reasoning.setWordWrap(True)
            layout_textos.addWidget(self.label_reasoning)

        self.label_snippets: QLabel | None = None
        if snippets:
            texto_snippets = " | ".join(snippets)
            self.label_snippets = QLabel(f"Trechos: {texto_snippets}")
            self.label_snippets.setStyleSheet("color: #666666; font-size: 11px;")
            self.label_snippets.setWordWrap(True)
            layout_textos.addWidget(self.label_snippets)

        layout_principal.addLayout(layout_textos, stretch=1)

        # Coluna de ações individuais (estritamente 1 a 1)
        layout_botoes = QVBoxLayout()
        layout_botoes.setSpacing(6)

        self.btn_aprovar: QPushButton | None = None
        if ao_aprovar is not None:
            self.btn_aprovar = QPushButton("✅ Aprovar")
            self.btn_aprovar.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_aprovar.setStyleSheet(
                "background-color: #28a745; color: white; font-weight: bold; "
                "padding: 5px 10px; border-radius: 4px;"
            )
            self.btn_aprovar.clicked.connect(lambda _checked=False: ao_aprovar())
            layout_botoes.addWidget(self.btn_aprovar)

        self.btn_rejeitar: QPushButton | None = None
        if ao_rejeitar is not None:
            self.btn_rejeitar = QPushButton("❌ Rejeitar")
            self.btn_rejeitar.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_rejeitar.setStyleSheet(
                "background-color: #dc3545; color: white; font-weight: bold; "
                "padding: 5px 10px; border-radius: 4px;"
            )
            self.btn_rejeitar.clicked.connect(lambda _checked=False: ao_rejeitar())
            layout_botoes.addWidget(self.btn_rejeitar)

        self.btn_restaurar: QPushButton | None = None
        if ao_restaurar is not None:
            self.btn_restaurar = QPushButton("↩️ Restaurar")
            self.btn_restaurar.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_restaurar.setStyleSheet(
                "background-color: #0969da; color: white; font-weight: bold; "
                "padding: 5px 10px; border-radius: 4px;"
            )
            self.btn_restaurar.clicked.connect(lambda _checked=False: ao_restaurar())
            layout_botoes.addWidget(self.btn_restaurar)

        layout_botoes.addStretch()
        layout_principal.addLayout(layout_botoes)

    def _ao_carregar_thumbnail(self, pixmap: QPixmap | None) -> None:
        if pixmap and not pixmap.isNull():
            self.label_thumbnail.setPixmap(pixmap)

    def encerrar_worker(self) -> None:
        """Desconecta e aguarda com segurança a finalização da QThread de thumbnail, se ativa."""
        if self._worker_imagem is not None:
            try:
                self._worker_imagem.imagem_carregada.disconnect(self._ao_carregar_thumbnail)
            except Exception:
                pass
            if self._worker_imagem.isRunning():
                self._worker_imagem.wait(500)
            self._worker_imagem = None


class PainelCuradoria(QWidget):
    """
    Aba de revisão e curadoria 1 a 1 de betas com 4 seções expansíveis:
    1. Betas Não Revisados (avaliados pelo LLM, ordenados por score decrescente)
    2. Betas Não Scorados (coletados, aguardando avaliação LLM via MCP)
    3. Betas Aprovados (publicados em Escalada.betas)
    4. Betas Rejeitados (mantidos em curadoria_betas.md para bloquear re-scraping)
    """

    def __init__(
        self,
        provedor_imagem: ProvedorImagemAresta | None = None,
        carregar_assincrono: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any | None = None
        self.controller: Any | None = None
        self.provedor_imagem = provedor_imagem or ProvedorImagemAresta()
        self.carregar_assincrono = carregar_assincrono
        self.filtro_escalada_uid: str = ""

        self.cards_nao_revisados: list[CardBetaCuradoria] = []
        self.cards_nao_scorados: list[CardBetaCuradoria] = []
        self.cards_aprovados: list[CardBetaCuradoria] = []
        self.cards_rejeitados: list[CardBetaCuradoria] = []
        self._atualizacao_pendente: bool = False
        self._agendado_timer: bool = False
        self.total_atualizacoes_visualizacao: int = 0

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(12, 12, 12, 12)
        layout_principal.setSpacing(10)

        # Barra superior: Filtro por escalada + Resumo + Botão Coletar Betas
        barra_superior = QHBoxLayout()
        barra_superior.addWidget(QLabel("Escalada:"))

        self.combo_escalada = QComboBox()
        self.combo_escalada.setMinimumWidth(240)
        self.combo_escalada.currentIndexChanged.connect(self._ao_trocar_filtro_escalada)
        barra_superior.addWidget(self.combo_escalada)

        self.label_status = QLabel("Nenhum croqui carregado.")
        self.label_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        barra_superior.addWidget(self.label_status, stretch=1)

        self.btn_coletar_betas = QPushButton("🌐 Coletar Betas...")
        self.btn_coletar_betas.setObjectName("BtnColetarBetas")
        self.btn_coletar_betas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_coletar_betas.setStyleSheet(
            "background-color: #0969da; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px;"
        )
        self.btn_coletar_betas.clicked.connect(self.abrir_wizard_coleta)
        barra_superior.addWidget(self.btn_coletar_betas)

        layout_principal.addLayout(barra_superior)

        # Scroll principal com as 4 seções expansíveis
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.container_secoes = QWidget()
        self.layout_secoes = QVBoxLayout(self.container_secoes)
        self.layout_secoes.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout_secoes.setSpacing(12)
        self.scroll_area.setWidget(self.container_secoes)
        layout_principal.addWidget(self.scroll_area, stretch=1)

        # 1. Seção Betas Não Revisados (Avaliados pelo LLM)
        self.secao_nao_revisados = QGroupBox("1. Betas Não Revisados (Avaliados pelo LLM)")
        self.secao_nao_revisados.setCheckable(True)
        self.secao_nao_revisados.setChecked(True)
        self.layout_nao_revisados = QVBoxLayout(self.secao_nao_revisados)
        self.layout_secoes.addWidget(self.secao_nao_revisados)

        # 2. Seção Betas Não Scorados (Aguardando Avaliação LLM via MCP)
        self.secao_nao_scorados = QGroupBox("2. Betas Não Scorados (Aguardando Avaliação LLM)")
        self.secao_nao_scorados.setCheckable(True)
        self.secao_nao_scorados.setChecked(True)
        self.layout_nao_scorados_externo = QVBoxLayout(self.secao_nao_scorados)

        banner_mcp = QFrame()
        banner_mcp.setStyleSheet(
            "background-color: #fff8c5; border: 1px solid #d4a72c; border-radius: 6px; padding: 6px;"
        )
        layout_banner = QHBoxLayout(banner_mcp)
        self.label_instrucoes_mcp = QLabel(INSTRUCOES_MCP_AVALIACAO)
        self.label_instrucoes_mcp.setWordWrap(True)
        layout_banner.addWidget(self.label_instrucoes_mcp, stretch=1)

        self.btn_copiar_prompt_mcp = QPushButton("📋 Copiar Prompt MCP")
        self.btn_copiar_prompt_mcp.clicked.connect(self._copiar_prompt_mcp)
        layout_banner.addWidget(self.btn_copiar_prompt_mcp)

        self.layout_nao_scorados_externo.addWidget(banner_mcp)
        self.layout_nao_scorados = QVBoxLayout()
        self.layout_nao_scorados_externo.addLayout(self.layout_nao_scorados)
        self.layout_secoes.addWidget(self.secao_nao_scorados)

        # 3. Seção Betas Aprovados (Publicados na Escalada)
        self.secao_aprovados = QGroupBox("3. Betas Aprovados (Publicados na Escalada)")
        self.secao_aprovados.setCheckable(True)
        self.secao_aprovados.setChecked(True)
        self.layout_aprovados = QVBoxLayout(self.secao_aprovados)
        self.layout_secoes.addWidget(self.secao_aprovados)

        # 4. Seção Betas Rejeitados (Bloqueados contra Re-Scraping)
        self.secao_rejeitados = QGroupBox("4. Betas Rejeitados (Ignorados em Futuras Coletas)")
        self.secao_rejeitados.setCheckable(True)
        self.secao_rejeitados.setChecked(True)
        self.layout_rejeitados = QVBoxLayout(self.secao_rejeitados)
        self.layout_secoes.addWidget(self.secao_rejeitados)

    def _copiar_prompt_mcp(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(
                "Execute a skill avaliar_betas_croqui para avaliar e pontuar os betas_nao_scorados deste croqui."
            )
        self.btn_copiar_prompt_mcp.setText("✅ Copiado para a área de transferência!")
        QTimer.singleShot(2000, self._restaurar_botao_copiar_prompt_mcp)

    def _restaurar_botao_copiar_prompt_mcp(self) -> None:
        self.btn_copiar_prompt_mcp.setText("📋 Copiar Prompt MCP")

    @staticmethod
    def _obter_pilha_undo(controller: Any) -> Any | None:
        pilha = getattr(controller, "undo_stack", None)
        if pilha is not None and hasattr(pilha, "obter_pilha"):
            return pilha.obter_pilha()
        return pilha

    def carregar_dados(self, model: Any, controller: Any) -> None:
        """Conecta o painel ao CroquiModel e ao CroquiController ativos e renderiza as 4 seções."""
        if self.model is not None and self.model is not model:
            for sig_name in ("repeated_adicionado", "repeated_removido", "dado_alterado"):
                sig = getattr(self.model, sig_name, None)
                if sig is not None:
                    try:
                        sig.disconnect(self._ao_mutar_modelo)
                    except Exception:
                        pass

        pilha_antiga = self._obter_pilha_undo(self.controller)
        if pilha_antiga is not None:
            sig_idx_ant = getattr(pilha_antiga, "indexChanged", None)
            if sig_idx_ant is not None:
                try:
                    sig_idx_ant.disconnect(self._ao_alterar_indice_undo)
                except Exception:
                    pass

        self.model = model
        self.controller = controller

        if self.model is not None:
            for sig_name in ("repeated_adicionado", "repeated_removido", "dado_alterado"):
                sig = getattr(self.model, sig_name, None)
                if sig is not None:
                    sig.connect(self._ao_mutar_modelo)

        pilha_nova = self._obter_pilha_undo(self.controller)
        if pilha_nova is not None:
            sig_idx_nova = getattr(pilha_nova, "indexChanged", None)
            if sig_idx_nova is not None:
                sig_idx_nova.connect(self._ao_alterar_indice_undo)

        self._popular_combo_escaladas()
        self.atualizar_visualizacao()

    def _ao_mutar_modelo(self, *_args: Any) -> None:
        self._atualizacao_pendente = True
        if not self._agendado_timer:
            self._agendado_timer = True
            QTimer.singleShot(0, self._processar_atualizacao_pendente)

    def _ao_alterar_indice_undo(self, *_args: Any) -> None:
        self._processar_atualizacao_pendente()

    def _processar_atualizacao_pendente(self) -> None:
        self._agendado_timer = False
        if not self._atualizacao_pendente:
            return
        self._atualizacao_pendente = False
        self._popular_combo_escaladas()
        self.atualizar_visualizacao()

    def _popular_combo_escaladas(self) -> None:
        self.combo_escalada.blockSignals(True)
        try:
            self.combo_escalada.clear()
            self.combo_escalada.addItem("Todas as Escaladas", "")
            if self.model is not None:
                croqui_ro = self.model.obter_croqui_readonly()
                for info in extrair_escaladas_do_croqui(croqui_ro):
                    self.combo_escalada.addItem(
                        f"{info.nome_escalada} ({info.nome_setor})",
                        info.escalada_uid,
                    )
            idx = self.combo_escalada.findData(self.filtro_escalada_uid)
            self.combo_escalada.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self.combo_escalada.blockSignals(False)

    def _ao_trocar_filtro_escalada(self) -> None:
        self.filtro_escalada_uid = str(self.combo_escalada.currentData() or "")
        self.atualizar_visualizacao()

    def selecionar_escalada_por_uid(self, escalada_uid: str) -> None:
        """Filtra e foca o painel de curadoria em uma escalada específica pelo seu UID."""
        self.filtro_escalada_uid = escalada_uid.strip()
        idx = self.combo_escalada.findData(self.filtro_escalada_uid)
        if idx >= 0:
            self.combo_escalada.setCurrentIndex(idx)
        else:
            self.atualizar_visualizacao()

    @staticmethod
    def _limpar_layout(layout: QVBoxLayout, lista_cards: list[CardBetaCuradoria]) -> None:
        for card in lista_cards:
            card.encerrar_worker()
        lista_cards.clear()
        while layout.count():
            item = layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    if isinstance(w, CardBetaCuradoria):
                        w.encerrar_worker()
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()

    def atualizar_visualizacao(self) -> None:
        """Reconstrói os cards das 4 seções refletindo o estado atual do CroquiModel."""
        self._atualizacao_pendente = False
        self.total_atualizacoes_visualizacao += 1
        self._limpar_layout(self.layout_nao_revisados, self.cards_nao_revisados)
        self._limpar_layout(self.layout_nao_scorados, self.cards_nao_scorados)
        self._limpar_layout(self.layout_aprovados, self.cards_aprovados)
        self._limpar_layout(self.layout_rejeitados, self.cards_rejeitados)

        if self.model is None or self.controller is None:
            self.label_status.setText("Nenhum croqui carregado.")
            return

        ctrl = self.controller
        croqui_ro = self.model.obter_croqui_readonly()
        mapa_info: dict[str, InfoEscaladaColeta] = {
            info.escalada_uid: info for info in extrair_escaladas_do_croqui(croqui_ro)
        }
        mapa_curadoria: dict[str, Any] = {
            cur.escalada_uid: cur for cur in croqui_ro.curadoria_betas.conteudo.escaladas
        }

        uids_alvo = (
            [self.filtro_escalada_uid]
            if self.filtro_escalada_uid and self.filtro_escalada_uid in mapa_info
            else list(mapa_info.keys())
        )

        # 1. Coleta e ordena globalmente por score decrescente os itens de betas_nao_revisados
        itens_nr: list[tuple[int, str, int, Any]] = []
        for uid in uids_alvo:
            cur = mapa_curadoria.get(uid)
            if cur is not None:
                for idx_orig, cand in enumerate(cur.betas_nao_revisados):
                    score = int(cand.resultado_llm.llm_confidence_score)
                    itens_nr.append((score, uid, idx_orig, cand))
        itens_nr.sort(key=lambda t: t[0], reverse=True)

        for score, uid, idx_orig, cand in itens_nr:
            info = mapa_info[uid]
            card = CardBetaCuradoria(
                midia=cand.midia,
                nome_escalada=info.nome_escalada,
                nome_setor=info.nome_setor,
                score_llm=score,
                justificativa_llm=str(cand.resultado_llm.llm_reasoning or ""),
                snippets=list(cand.snippets),
                ao_aprovar=partial(
                    ctrl.aprovar_beta_curadoria, uid, "betas_nao_revisados", idx_orig
                ),
                ao_rejeitar=partial(
                    ctrl.rejeitar_beta_curadoria, uid, "betas_nao_revisados", idx_orig
                ),
                provedor_imagem=self.provedor_imagem,
                carregar_assincrono=self.carregar_assincrono,
                parent=self.secao_nao_revisados,
            )
            self.cards_nao_revisados.append(card)
            self.layout_nao_revisados.addWidget(card)

        # 2. Betas Não Scorados
        for uid in uids_alvo:
            cur = mapa_curadoria.get(uid)
            if cur is None:
                continue
            info = mapa_info[uid]
            for idx_ns, cand in enumerate(cur.betas_nao_scorados):
                card = CardBetaCuradoria(
                    midia=cand.midia,
                    nome_escalada=info.nome_escalada,
                    nome_setor=info.nome_setor,
                    snippets=list(cand.snippets),
                    ao_aprovar=partial(
                        ctrl.aprovar_beta_curadoria, uid, "betas_nao_scorados", idx_ns
                    ),
                    ao_rejeitar=partial(
                        ctrl.rejeitar_beta_curadoria, uid, "betas_nao_scorados", idx_ns
                    ),
                    provedor_imagem=self.provedor_imagem,
                    carregar_assincrono=self.carregar_assincrono,
                    parent=self.secao_nao_scorados,
                )
                self.cards_nao_scorados.append(card)
                self.layout_nao_scorados.addWidget(card)

        # 3. Betas Aprovados (em escalada.betas)
        for uid in uids_alvo:
            esc_obj = self.model.obter_objeto_por_uid(uid)
            if esc_obj is None:
                continue
            info = mapa_info[uid]
            for idx_ap, midia in enumerate(esc_obj.betas):
                card = CardBetaCuradoria(
                    midia=midia,
                    nome_escalada=info.nome_escalada,
                    nome_setor=info.nome_setor,
                    ao_rejeitar=partial(ctrl.rejeitar_beta_curadoria, uid, "betas", idx_ap),
                    provedor_imagem=self.provedor_imagem,
                    carregar_assincrono=self.carregar_assincrono,
                    parent=self.secao_aprovados,
                )
                self.cards_aprovados.append(card)
                self.layout_aprovados.addWidget(card)

        # 4. Betas Rejeitados
        for uid in uids_alvo:
            cur = mapa_curadoria.get(uid)
            if cur is None:
                continue
            info = mapa_info[uid]
            for idx_rej, midia_rej in enumerate(cur.betas_rejeitados):
                card = CardBetaCuradoria(
                    midia=midia_rej,
                    nome_escalada=info.nome_escalada,
                    nome_setor=info.nome_setor,
                    ao_restaurar=partial(ctrl.restaurar_beta_rejeitado, uid, idx_rej),
                    provedor_imagem=self.provedor_imagem,
                    carregar_assincrono=self.carregar_assincrono,
                    parent=self.secao_rejeitados,
                )
                self.cards_rejeitados.append(card)
                self.layout_rejeitados.addWidget(card)

        self.secao_nao_revisados.setTitle(
            f"1. Betas Não Revisados - Avaliados pelo LLM ({len(self.cards_nao_revisados)})"
        )
        self.secao_nao_scorados.setTitle(
            f"2. Betas Não Scorados - Aguardando Avaliação LLM ({len(self.cards_nao_scorados)})"
        )
        self.secao_aprovados.setTitle(
            f"3. Betas Aprovados - Publicados na Escalada ({len(self.cards_aprovados)})"
        )
        self.secao_rejeitados.setTitle(
            f"4. Betas Rejeitados - Ignorados em Futuras Coletas ({len(self.cards_rejeitados)})"
        )

        self.label_status.setText(
            f"{len(self.cards_aprovados)} aprovado(s) • "
            f"{len(self.cards_nao_revisados)} não revisado(s) • "
            f"{len(self.cards_nao_scorados)} não scorado(s) • "
            f"{len(self.cards_rejeitados)} rejeitado(s)"
        )

    def abrir_wizard_coleta(self) -> DialogoColetarBetas | None:
        """Abre o Wizard para coletar betas para escaladas selecionadas do croqui."""
        if self.model is None or self.controller is None:
            return None
        dialogo = DialogoColetarBetas(model=self.model, controller=self.controller, parent=self)
        dialogo.exec()
        return dialogo
