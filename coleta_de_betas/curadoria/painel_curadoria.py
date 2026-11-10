# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Painel de curadoria e revisão de mídias de beta (YouTube, Instagram, Blogs, TikTok, Facebook)
integrado ao CroquiModel e ao CroquiController (Undo/Redo).
"""

from collections.abc import Callable, Sequence
from functools import partial
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
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
    "💡 Passo 1: Conecte seu agente de IA (Cursor, Claude, Antigravity) ao Editor Aresta clicando em "
    '"🔌 Conectar Agente (MCP)...".\n'
    "Passo 2: Copie e envie o comando ao agente:\n"
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


class SecaoExpansivelCuradoria(QFrame):
    """
    Seção de curadoria com cabeçalho clicável estilo Expando (▼ / ▶) que oculta ou exibe
    seu container de conteúdo sem exibir checkboxes enganosos de seleção.
    """

    expansao_alterada = Signal(bool)

    def __init__(
        self,
        titulo: str = "",
        expandida: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._titulo: str = titulo
        self._expandida: bool = expandida

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            SecaoExpansivelCuradoria {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
            }
        """)

        layout_externo = QVBoxLayout(self)
        layout_externo.setContentsMargins(8, 8, 8, 8)
        layout_externo.setSpacing(8)

        self.botao_cabecalho = QPushButton()
        self.botao_cabecalho.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_cabecalho.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.botao_cabecalho.setStyleSheet("""
            QPushButton {
                text-align: left;
                font-weight: bold;
                font-size: 13px;
                color: #0f172a;
                background-color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
            }
        """)
        self.botao_cabecalho.clicked.connect(self.alternar_expansao)
        layout_externo.addWidget(self.botao_cabecalho)

        self.container_conteudo = QWidget()
        self.layout_conteudo = QVBoxLayout(self.container_conteudo)
        self.layout_conteudo.setContentsMargins(4, 4, 4, 4)
        self.layout_conteudo.setSpacing(8)
        layout_externo.addWidget(self.container_conteudo)

        self._atualizar_estado_visual()

    def _atualizar_estado_visual(self) -> None:
        seta = "▼" if self._expandida else "▶"
        self.botao_cabecalho.setText(f"{seta}  {self._titulo}")
        self.container_conteudo.setVisible(self._expandida)

    def esta_expandida(self) -> bool:
        """Retorna True se o conteúdo da seção está expandido."""
        return self._expandida

    def definir_expandida(self, expandida: bool) -> None:
        """Expande ou recolhe a seção e emite `expansao_alterada` quando o estado muda."""
        expandida_bool = bool(expandida)
        if self._expandida == expandida_bool:
            return
        self._expandida = expandida_bool
        self._atualizar_estado_visual()
        self.expansao_alterada.emit(self._expandida)

    def alternar_expansao(self) -> None:
        """Inverte o estado de expansão da seção ao clicar no cabeçalho."""
        self.definir_expandida(not self._expandida)

    def setTitle(self, titulo: str) -> None:
        """Atualiza o título exibido no botão de cabeçalho preservando o ícone ▼/▶."""
        self._titulo = titulo
        self._atualizar_estado_visual()

    def title(self) -> str:
        """Retorna o texto atual do cabeçalho (incluindo o indicador ▼/▶)."""
        return str(self.botao_cabecalho.text())


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
        usar_apenas_fallback: bool = False,
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
        if usar_apenas_fallback or not self.midia.url:
            self.label_thumbnail.setPixmap(obter_pixmap_fallback(self.midia.fonte))
        elif carregar_assincrono:
            pixmap_imediato = self._provedor.obter_pixmap_imediato(self.midia.url, self.midia.fonte)
            if pixmap_imediato is not None:
                self.label_thumbnail.setPixmap(pixmap_imediato)
            else:
                self.label_thumbnail.setPixmap(obter_pixmap_fallback(self.midia.fonte))
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

        # Coluna de ações individuais (1 a 1)
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
        """Desconecta sem bloquear a UI thread a QThread de thumbnail, se ativa."""
        if self._worker_imagem is not None:
            try:
                self._worker_imagem.imagem_carregada.disconnect(self._ao_carregar_thumbnail)
            except Exception:
                pass
            self._worker_imagem.setParent(None)
            self._worker_imagem.finished.connect(self._worker_imagem.deleteLater)
            self._worker_imagem = None


class PainelCuradoria(QWidget):
    """
    Aba de revisão e curadoria de betas com 4 seções expansíveis na ordem do pipeline:
    1. Betas Não Scorados (coletados, aguardando avaliação LLM via MCP)
    2. Betas Não Revisados (avaliados pelo LLM, ordenados por score decrescente, com ações em lote)
    3. Betas Aprovados (publicados em Escalada.betas)
    4. Betas Rejeitados (mantidos em curadoria_betas.md para bloquear re-scraping; inicia recolhida)
    """

    def __init__(
        self,
        provedor_imagem: ProvedorImagemAresta | None = None,
        carregar_assincrono: bool = True,
        ao_solicitar_conexao_mcp: Callable[[], Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any | None = None
        self.controller: Any | None = None
        self.provedor_imagem = provedor_imagem or ProvedorImagemAresta()
        self.carregar_assincrono = carregar_assincrono
        self.ao_solicitar_conexao_mcp = ao_solicitar_conexao_mcp
        self.filtro_escalada_uid: str = ""

        self.cards_nao_scorados: list[CardBetaCuradoria] = []
        self.cards_nao_revisados: list[CardBetaCuradoria] = []
        self.cards_aprovados: list[CardBetaCuradoria] = []
        self.cards_rejeitados: list[CardBetaCuradoria] = []
        self._scores_nao_revisados_atuais: list[int] = []
        self._itens_rejeitados_atuais: list[tuple[str, int, Any, InfoEscaladaColeta]] = []
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

        # 1. Seção Betas Não Scorados (Aguardando Avaliação LLM via MCP) — 1ª na pipeline
        self.secao_nao_scorados = SecaoExpansivelCuradoria(
            "1. Betas Não Scorados - Aguardando Avaliação LLM",
            expandida=True,
        )
        banner_mcp = QFrame()
        banner_mcp.setObjectName("BannerMcpCuradoria")
        banner_mcp.setStyleSheet(
            "#BannerMcpCuradoria { background-color: #fff8c5; border: 1px solid #d4a72c; border-radius: 6px; padding: 6px; }"
        )
        layout_banner = QHBoxLayout(banner_mcp)
        self.label_instrucoes_mcp = QLabel(INSTRUCOES_MCP_AVALIACAO)
        self.label_instrucoes_mcp.setWordWrap(True)
        layout_banner.addWidget(self.label_instrucoes_mcp, stretch=1)

        layout_botoes_mcp = QVBoxLayout()
        self.btn_conectar_mcp = QPushButton("🔌 Conectar Agente (MCP)...")
        self.btn_conectar_mcp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_conectar_mcp.clicked.connect(self.abrir_conexao_mcp)
        layout_botoes_mcp.addWidget(self.btn_conectar_mcp)

        self.btn_copiar_prompt_mcp = QPushButton("📋 Copiar Prompt MCP")
        self.btn_copiar_prompt_mcp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copiar_prompt_mcp.clicked.connect(self._copiar_prompt_mcp)
        layout_botoes_mcp.addWidget(self.btn_copiar_prompt_mcp)
        layout_banner.addLayout(layout_botoes_mcp)

        self.secao_nao_scorados.layout_conteudo.addWidget(banner_mcp)
        self.layout_nao_scorados = QVBoxLayout()
        self.secao_nao_scorados.layout_conteudo.addLayout(self.layout_nao_scorados)
        self.layout_secoes.addWidget(self.secao_nao_scorados)

        # 2. Seção Betas Não Revisados (Avaliados pelo LLM) — 2ª na pipeline, com ações em lote por score
        self.secao_nao_revisados = SecaoExpansivelCuradoria(
            "2. Betas Não Revisados - Avaliados pelo LLM",
            expandida=True,
        )
        barra_lote = QFrame()
        barra_lote.setObjectName("BarraLoteCuradoria")
        barra_lote.setStyleSheet(
            "#BarraLoteCuradoria { background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; }"
        )
        layout_lote = QHBoxLayout(barra_lote)
        layout_lote.addWidget(QLabel("Limiar de confiança LLM:"))

        self.spin_limiar_score = QSpinBox()
        self.spin_limiar_score.setMinimumWidth(85)
        self.spin_limiar_score.setRange(0, 100)
        self.spin_limiar_score.setSuffix("%")
        self.spin_limiar_score.setValue(80)
        self.spin_limiar_score.valueChanged.connect(self._atualizar_botoes_lote_score)
        layout_lote.addWidget(self.spin_limiar_score)

        self.btn_aprovar_lote_score = QPushButton("✅ Aprovar >= 80% (0)")
        self.btn_aprovar_lote_score.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_aprovar_lote_score.setStyleSheet(
            "background-color: #28a745; color: white; font-weight: bold; "
            "padding: 5px 10px; border-radius: 4px;"
        )
        self.btn_aprovar_lote_score.clicked.connect(self._aprovar_lote_por_score)
        layout_lote.addWidget(self.btn_aprovar_lote_score)

        self.btn_rejeitar_lote_score = QPushButton("❌ Rejeitar < 80% (0)")
        self.btn_rejeitar_lote_score.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rejeitar_lote_score.setStyleSheet(
            "background-color: #dc3545; color: white; font-weight: bold; "
            "padding: 5px 10px; border-radius: 4px;"
        )
        self.btn_rejeitar_lote_score.clicked.connect(self._rejeitar_lote_por_score)
        layout_lote.addWidget(self.btn_rejeitar_lote_score)
        layout_lote.addStretch(1)

        self.secao_nao_revisados.layout_conteudo.addWidget(barra_lote)
        self.layout_nao_revisados = QVBoxLayout()
        self.secao_nao_revisados.layout_conteudo.addLayout(self.layout_nao_revisados)
        self.layout_secoes.addWidget(self.secao_nao_revisados)

        # 3. Seção Betas Aprovados (Publicados na Escalada)
        self.secao_aprovados = SecaoExpansivelCuradoria(
            "3. Betas Aprovados - Publicados na Escalada",
            expandida=True,
        )
        self.layout_aprovados = self.secao_aprovados.layout_conteudo
        self.layout_secoes.addWidget(self.secao_aprovados)

        # 4. Seção Betas Rejeitados (Bloqueados contra Re-Scraping) — inicia recolhida e lazy
        self.secao_rejeitados = SecaoExpansivelCuradoria(
            "4. Betas Rejeitados - Ignorados em Futuras Coletas",
            expandida=False,
        )
        self.layout_rejeitados = self.secao_rejeitados.layout_conteudo
        self.secao_rejeitados.expansao_alterada.connect(self._ao_alternar_expansao_rejeitados)
        self.layout_secoes.addWidget(self.secao_rejeitados)

    def abrir_conexao_mcp(self) -> None:
        """Abre o diálogo/assistente de conexão MCP da janela principal ou callback configurado."""
        if self.ao_solicitar_conexao_mcp is not None:
            self.ao_solicitar_conexao_mcp()
            return
        janela = self.window()
        exibir_mcp = getattr(janela, "_exibir_conexao_mcp", None)
        if callable(exibir_mcp):
            exibir_mcp()

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

    def _atualizar_botoes_lote_score(self) -> None:
        limiar = int(self.spin_limiar_score.value())
        qtd_aprovar = sum(1 for s in self._scores_nao_revisados_atuais if s >= limiar)
        qtd_rejeitar = sum(1 for s in self._scores_nao_revisados_atuais if s < limiar)
        self.btn_aprovar_lote_score.setText(f"✅ Aprovar >= {limiar}% ({qtd_aprovar})")
        self.btn_aprovar_lote_score.setEnabled(qtd_aprovar > 0)
        self.btn_rejeitar_lote_score.setText(f"❌ Rejeitar < {limiar}% ({qtd_rejeitar})")
        self.btn_rejeitar_lote_score.setEnabled(qtd_rejeitar > 0)

    def _aprovar_lote_por_score(self) -> None:
        if self.controller is None:
            return
        limiar = int(self.spin_limiar_score.value())
        self.controller.aprovar_betas_nao_revisados_por_score(
            score_minimo=limiar,
            escalada_uid=self.filtro_escalada_uid,
        )

    def _rejeitar_lote_por_score(self) -> None:
        if self.controller is None:
            return
        limiar = int(self.spin_limiar_score.value())
        self.controller.rejeitar_betas_nao_revisados_por_score(
            score_maximo_exclusivo=limiar,
            escalada_uid=self.filtro_escalada_uid,
        )

    def _ao_alternar_expansao_rejeitados(self, expandida: bool) -> None:
        if expandida and not self.cards_rejeitados and self._itens_rejeitados_atuais:
            self._renderizar_cards_rejeitados()

    def _renderizar_cards_rejeitados(self) -> None:
        if self.controller is None:
            return
        ctrl = self.controller
        for uid, idx_rej, midia_rej, info in self._itens_rejeitados_atuais:
            card = CardBetaCuradoria(
                midia=midia_rej,
                nome_escalada=info.nome_escalada,
                nome_setor=info.nome_setor,
                ao_restaurar=partial(ctrl.restaurar_beta_rejeitado, uid, idx_rej),
                provedor_imagem=self.provedor_imagem,
                carregar_assincrono=False,
                usar_apenas_fallback=True,
                parent=self.secao_rejeitados,
            )
            self.cards_rejeitados.append(card)
            self.layout_rejeitados.addWidget(card)

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
        """Reconstrói os cards das 4 seções refletindo o estado atual do CroquiModel sem perder o scroll."""
        self._atualizacao_pendente = False
        self.total_atualizacoes_visualizacao += 1

        vbar = self.scroll_area.verticalScrollBar()
        pos_scroll = vbar.value() if vbar is not None else 0

        foco_atual = QApplication.focusWidget()
        if foco_atual is not None and self.container_secoes.isAncestorOf(foco_atual):
            foco_atual.clearFocus()

        self.container_secoes.setUpdatesEnabled(False)
        try:
            self._limpar_layout(self.layout_nao_scorados, self.cards_nao_scorados)
            self._limpar_layout(self.layout_nao_revisados, self.cards_nao_revisados)
            self._limpar_layout(self.layout_aprovados, self.cards_aprovados)
            self._limpar_layout(self.layout_rejeitados, self.cards_rejeitados)
            self._scores_nao_revisados_atuais.clear()
            self._itens_rejeitados_atuais.clear()

            if self.model is None or self.controller is None:
                self._atualizar_botoes_lote_score()
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

            # 1. Betas Não Scorados
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

            # 2. Betas Não Revisados (ordenados globalmente por score decrescente)
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
                self._scores_nao_revisados_atuais.append(score)
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

            self._atualizar_botoes_lote_score()

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

            # 4. Betas Rejeitados (instanciados apenas se a seção estiver expandida)
            for uid in uids_alvo:
                cur = mapa_curadoria.get(uid)
                if cur is None:
                    continue
                info = mapa_info[uid]
                for idx_rej, midia_rej in enumerate(cur.betas_rejeitados):
                    self._itens_rejeitados_atuais.append((uid, idx_rej, midia_rej, info))

            if self.secao_rejeitados.esta_expandida():
                self._renderizar_cards_rejeitados()

            total_rejeitados = len(self._itens_rejeitados_atuais)
            self.secao_nao_scorados.setTitle(
                f"1. Betas Não Scorados - Aguardando Avaliação LLM ({len(self.cards_nao_scorados)})"
            )
            self.secao_nao_revisados.setTitle(
                f"2. Betas Não Revisados - Avaliados pelo LLM ({len(self.cards_nao_revisados)})"
            )
            self.secao_aprovados.setTitle(
                f"3. Betas Aprovados - Publicados na Escalada ({len(self.cards_aprovados)})"
            )
            self.secao_rejeitados.setTitle(
                f"4. Betas Rejeitados - Ignorados em Futuras Coletas ({total_rejeitados})"
            )

            self.label_status.setText(
                f"{len(self.cards_aprovados)} aprovado(s) • "
                f"{len(self.cards_nao_revisados)} não revisado(s) • "
                f"{len(self.cards_nao_scorados)} não scorado(s) • "
                f"{total_rejeitados} rejeitado(s)"
            )
        finally:
            self.container_secoes.setUpdatesEnabled(True)
            if vbar is not None:
                vbar.setValue(pos_scroll)

    def abrir_wizard_coleta(self) -> DialogoColetarBetas | None:
        """Abre o Wizard para coletar betas para escaladas selecionadas do croqui."""
        if self.model is None or self.controller is None:
            return None
        dialogo = DialogoColetarBetas(model=self.model, controller=self.controller, parent=self)
        dialogo.exec()
        return dialogo
