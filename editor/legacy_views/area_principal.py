# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, List, Dict, Any, Callable, Union
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QStyle, QMessageBox, QDialog, QLineEdit, QTextEdit, QPushButton, QFormLayout,
    QApplication, QDockWidget, QProgressDialog
)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QCoreApplication
from PySide6.QtGui import QAction, QIcon, QFont, QKeySequence, QCloseEvent
from pathlib import Path
import yaml
import os
from editor.views.estilo import Icones
from ..core.servidor_celular import ServidorCelular
from ..core.monitor_inatividade import MonitorInatividade
from .dialogo_conexao_celular import DialogoConexaoCelular
from editor.views.widget_editor_mapas import WidgetEditorMapas
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens
from editor.views.notificacao import NotificacaoToast
from ..core.historico import GerenciadorHistorico
from editor.models.compilacao_log import CompilacaoLog
from editor.controllers.compilacao_controller import CompilacaoController
from editor.views.widget_saida_compilacao import WidgetSaidaCompilacao
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController

class DialogoPublicar(QDialog):
    """Diálogo para coletar informações para o Pull Request."""
    def __init__(self, titulo_padrao: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Publicar no GitHub")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.edit_titulo: QLineEdit = QLineEdit(f"Croqui: {titulo_padrao}")
        self.edit_descricao: QTextEdit = QTextEdit()
        self.edit_descricao.setPlaceholderText("Descreva as alterações feitas...")
        
        form.addRow("Título da PR:", self.edit_titulo)
        form.addRow("Descrição:", self.edit_descricao)
        layout.addLayout(form)
        
        botoes = QHBoxLayout()
        self.btn_cancelar: QPushButton = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_publicar: QPushButton = QPushButton("Publicar Agora")
        self.btn_publicar.setDefault(True)
        self.btn_publicar.clicked.connect(self.accept)
        
        botoes.addStretch()
        botoes.addWidget(self.btn_cancelar)
        botoes.addWidget(self.btn_publicar)
        layout.addLayout(botoes)

    def obter_dados(self) -> Dict[str, str]:
        return {
            "titulo": self.edit_titulo.text(),
            "descricao": self.edit_descricao.toPlainText()
        }

class PaginaBase(QWidget):
    """Classe base para as páginas do editor."""
    def __init__(self, titulo: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.titulo: str = titulo
        layout = QVBoxLayout(self)
        self.label: QLabel = QLabel(f"Página: {titulo}\n(A Implementar)", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 24px; color: #666; font-weight: bold;")
        layout.addWidget(self.label)
        self.setStyleSheet(".PaginaBase { background-color: #ffffff; border-radius: 10px; }")

    def obter_acoes_contextuais(self) -> List[QAction]:
        """Retorna uma lista de QActions específicas desta página."""
        return []

class PaginaDados(PaginaBase):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Dados", parent)
        layout = self.layout()
        if layout:
            layout.removeWidget(self.label)
            layout.setContentsMargins(0, 0, 0, 0)
        self.label.deleteLater()
        self.editor_dados: Optional[Any] = None
        
    def carregar_dados(self, model: CroquiModel, controller: CroquiController) -> None:
        layout = self.layout()
        if self.editor_dados and layout:
            layout.removeWidget(self.editor_dados)
            self.editor_dados.deleteLater()
            
        from editor.views.widget_editor_dados import WidgetEditorDados
        self.editor_dados = WidgetEditorDados(model, controller, parent=self)
        if layout:
            layout.addWidget(self.editor_dados)

class PaginaImagens(PaginaBase):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Imagens", parent)
        # Remove o label de placeholder
        layout = self.layout()
        if layout:
            layout.removeWidget(self.label)
            layout.setContentsMargins(0, 0, 0, 0)
        self.label.deleteLater()
        
        # O folder_path inicial é vazio, será carregado em carregar_imagens
        self.editor: WidgetEditorImagens = WidgetEditorImagens("", modo_integrado=True, parent=self)
        if layout:
            layout.addWidget(self.editor)
        
    def carregar_imagens(self, caminho_db: Optional[Union[str, Path]], model: Optional[Any] = None, controller: Optional[Any] = None) -> None:
        if model:
            if getattr(self.editor, "_model_conectado", None) is not model:
                conectado = getattr(self.editor, "_model_conectado", None)
                if conectado is not None and hasattr(conectado, "imagem_alterada"):
                    try:
                        conectado.imagem_alterada.disconnect(self.editor._on_imagem_alterada)
                    except Exception:
                        pass
                self.editor.croqui_model = model
                if hasattr(model, "imagem_alterada"):
                    model.imagem_alterada.connect(self.editor._on_imagem_alterada)
                    self.editor._model_conectado = model
        if controller:
            self.editor.croqui_controller = controller

        if caminho_db:
            self.editor.folder_path = str(caminho_db)
            self.editor.imagens_path = str(Path(caminho_db) / "imagens")
        self.editor.load_images_list()

class PaginaMapas(PaginaBase):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Mapas", parent)
        # Remove o label de placeholder
        layout = self.layout()
        if layout:
            layout.removeWidget(self.label)
            layout.setContentsMargins(0, 0, 0, 0)
        self.label.deleteLater()
        
        self.editor: WidgetEditorMapas = WidgetEditorMapas(parent=self)
        if layout:
            layout.addWidget(self.editor)
        
    def carregar_mapas(self, model: Optional[Any], undo_stack: Optional[Any], caminho_db: Optional[Union[str, Path]] = None, controller: Optional[Any] = None) -> None:
        if model:
            from editor.controllers.mapas_controller import MapasController
            mapas_controller = MapasController(model, undo_stack)
            if caminho_db:
                mapas_controller.set_caminho_db(Path(caminho_db))
            self.editor.mapas_controller = mapas_controller
            self.editor.croqui_model = model
            self.editor.croqui_controller = controller or getattr(mapas_controller, "croqui_controller", None)
            if getattr(self.editor, "_model_imagem_conectado", None) is not model:
                conectado_img = getattr(self.editor, "_model_imagem_conectado", None)
                if conectado_img is not None and hasattr(conectado_img, "imagem_alterada"):
                    try:
                        conectado_img.imagem_alterada.disconnect(self.editor._on_imagem_alterada)
                    except Exception:
                        pass
                if hasattr(model, "imagem_alterada"):
                    model.imagem_alterada.connect(self.editor._on_imagem_alterada)
                    self.editor._model_imagem_conectado = model
            if hasattr(self.editor, 'painel_referencias') and self.editor.painel_referencias:
                self.editor.painel_referencias.mapas_controller = mapas_controller
            self.editor.configurar_lista_mapas()


class PaginaBetas(PaginaBase):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Betas", parent)
        layout = self.layout()
        if layout:
            layout.removeWidget(self.label)
            layout.setContentsMargins(0, 0, 0, 0)
        self.label.deleteLater()
        from coleta_de_betas.curadoria.painel_curadoria import PainelCuradoria
        self.painel: Any = PainelCuradoria(parent=self)
        if layout:

            layout.addWidget(self.painel)


    def carregar_betas(self, caminho_db: Optional[Union[str, Path]]) -> None:
        if caminho_db:
            caminho_staging = Path(caminho_db) / "betas_pendentes.binarypb"
            if caminho_staging.exists():
                self.painel.carregar_staging(caminho_staging)

class PaginaHistorico(PaginaBase):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Histórico", parent)


class JanelaPrincipal(QMainWindow):
    # Sinal emitido quando o usuário deseja voltar para a tela de carregamento
    solicitar_abrir_novo = Signal()
    salvamento_finalizado = Signal()
    
    def __init__(self, storage: Optional[Any] = None, auth: Optional[Any] = None, workspace: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.storage: Optional[Any] = storage
        if auth is None:
            from editor.core.gerenciador_sessao import GerenciadorSessao
            auth = GerenciadorSessao()
        self.auth: Optional[Any] = auth
        self.workspace: Optional[Any] = workspace
        self.croqui_data: Optional[Dict[str, Any]] = None
        self.croqui_model: Optional[CroquiModel] = None
        self.croqui_controller: Optional[CroquiController] = None
        self._acoes_contextuais: List[QAction] = []
        self._worker_pr: Optional[Any] = None
        
        self.servidor_celular: Optional[ServidorCelular] = None
        self.monitor_inatividade: Optional[MonitorInatividade] = None
        self.dialogo_celular: Optional[DialogoConexaoCelular] = None
        self.historico: GerenciadorHistorico = GerenciadorHistorico(self)
        self.historico.obter_pilha().cleanChanged.connect(self._on_clean_changed)
        
        self._salvando: bool = False
        self._fechar_apos_salvar: bool = False
        self._forcar_fechamento: bool = False
        self._callback_sucesso_salvar: Optional[Callable[[], None]] = None
        self.label_status_salvamento: Optional[QLabel] = None
        self.dlg_espera: Optional[QProgressDialog] = None
        
        self.atualizar_titulo()
        self.resize(1200, 800)

        
        # Componentes do Painel de Saída de Compilação
        self.compilacao_log: CompilacaoLog = CompilacaoLog()
        self.widget_saida_compilacao: WidgetSaidaCompilacao = WidgetSaidaCompilacao(self)
        self.compilacao_controller: CompilacaoController = CompilacaoController(self.compilacao_log, self.widget_saida_compilacao)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.widget_saida_compilacao)
        self.widget_saida_compilacao.hide()
        
        # Estilo Global
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6f7;
            }
            QToolBar {
                background-color: #ffffff;
                border: none;
                padding: 5px;
            }
            #toolbar_superior {
                border-bottom: 1px solid #ddd;
            }
            #toolbar_lateral {
                border-right: 1px solid #ddd;
                spacing: 10px;
            }
            QToolButton {
                border-radius: 5px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #f0f0f0;
            }
            QToolButton:checked {
                background-color: #e0e0e0;
            }
            
            /* Barras de Rolagem Modernas */
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #c1c1c1;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #a8a8a8;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        self._setup_ui()
        
        if self.workspace:
            self.carregar_croqui()
        
    def _setup_ui(self) -> None:
        # 1. Configura as Toolbars (Superior e Lateral)
        self._setup_toolbars()
        
        # 2. Configura as Ações (Globais e de Navegação)
        self._setup_acoes_globais()
        self._setup_navegacao_lateral()
        
        # 3. Área Central (Stacked Widget)
        self.container_central = QWidget(self)
        self.layout_central = QVBoxLayout(self.container_central)
        self.layout_central.setContentsMargins(10, 10, 10, 10)
        
        self.stack = QStackedWidget(self)
        self.layout_central.addWidget(self.stack)
        
        self.setCentralWidget(self.container_central)
        
        self._setup_paginas()
        self.historico.sinal_foco_requisitado.connect(self._on_foco_requisitado)
        
        
    def _setup_toolbars(self) -> None:
        self.toolbar_superior = QToolBar("Barra Superior")
        self.toolbar_superior.setObjectName("toolbar_superior")
        self.toolbar_superior.setMovable(False)
        self.toolbar_superior.setIconSize(QSize(24, 24))
        
        # Logo do aplicativo (montanha verde musgo)
        self.espacador_superior = QLabel()
        self.espacador_superior.setFixedWidth(63)
        self.espacador_superior.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QColor
        from editor.core.storage import GerenciadorCaminhos
        storage_atual = self.storage or GerenciadorCaminhos()
        caminho_logo_app = storage_atual.obter_caminho_recurso_interno("recursos/logo_app.png")
        pixmap = QPixmap(str(caminho_logo_app))
        
        if not pixmap.isNull():
            pixmap = pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            # Aplica bordas arredondadas ao pixmap
            rounded = QPixmap(pixmap.size())
            rounded.fill(QColor("transparent"))
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            path = QPainterPath()
            path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 4, 4)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            pixmap = rounded

        self.espacador_superior.setPixmap(pixmap)
        
        # Define o ícone da janela
        self.setWindowIcon(QIcon(str(caminho_logo_app)))
        
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar_superior)
        
        self.toolbar_lateral = QToolBar("Barra Lateral")
        self.toolbar_lateral.setObjectName("toolbar_lateral")
        self.toolbar_lateral.setMovable(False)
        self.toolbar_lateral.setIconSize(QSize(28, 28))
        self.toolbar_lateral.setMinimumWidth(82)
        self.toolbar_lateral.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.toolbar_lateral.setStyleSheet(Icones.QSS_BARRA_LATERAL)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar_lateral)

    def atualizar_titulo(self) -> None:
        """Atualiza o título da janela baseado no workspace, nome do croqui e estado de modificação."""
        versao = QCoreApplication.applicationVersion()
        titulo_base = f"Editor Aresta v{versao}" if versao else "Editor Aresta"
        
        if self.workspace:
            tag = self.workspace.obter_tag_titulo()
            if tag:
                titulo_base += f" - {tag}"
                
        if self.croqui_data:
            nome_croqui = self.croqui_data.get('nome', 'Sem Nome')
            titulo_base += f" - {nome_croqui}"
            
        if not self.historico.obter_pilha().isClean():
            titulo_base += " *"
            
        self.setWindowTitle(titulo_base)

    def _on_clean_changed(self, is_clean: bool) -> None:
        """Atualiza o título da janela baseado no estado limpo da pilha de histórico."""
        self.atualizar_titulo()
        
    def _setup_acoes_globais(self) -> None:
        self.acao_abrir = QAction(Icones.obter("novo"), "Abrir Novo", self)
        self.acao_abrir.setToolTip("Abrir Novo")
        self.acao_abrir.triggered.connect(self._on_abrir_novo_clicado)
        
        self.acao_salvar = QAction(Icones.obter("salvar"), "Salvar", self)
        self.acao_salvar.setToolTip("Salvar")
        self.acao_salvar.triggered.connect(self.salvar_croqui)
        
        self.acao_desfazer = QAction(Icones.obter("desfazer"), "Desfazer", self)
        self.acao_desfazer.setToolTip("Desfazer")
        self.acao_desfazer.setShortcuts(QKeySequence.StandardKey.Undo)
        self.acao_desfazer.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.acao_desfazer.setEnabled(False)
        self.acao_desfazer.triggered.connect(self.historico.desfazer)
        
        self.acao_refazer = QAction(Icones.obter("refazer"), "Refazer", self)
        self.acao_refazer.setToolTip("Refazer")
        self.acao_refazer.setShortcuts(QKeySequence.StandardKey.Redo)
        self.acao_refazer.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.acao_refazer.setEnabled(False)
        self.acao_refazer.triggered.connect(self.historico.refazer)
        
        # Sincroniza a pilha global do QUndoStack com a disponibilidade das ações
        self.historico.obter_pilha().canUndoChanged.connect(self.acao_desfazer.setEnabled)
        self.historico.obter_pilha().canRedoChanged.connect(self.acao_refazer.setEnabled)
        
        self.acao_exportar = QAction(Icones.obter("exportar"), "Exportar", self)
        self.acao_exportar.setToolTip("Exportar .croqui")
        self.acao_exportar.triggered.connect(self.exportar_croqui)
        
        self.acao_celular = QAction(Icones.obter_celular(conectado=False), "Celular", self)
        self.acao_celular.setToolTip("Conectar com celular...")
        self.acao_celular.triggered.connect(self._exibir_conexao_celular)
        
        self.acao_publicar = QAction(Icones.obter("publicar"), "Propor Mudança", self)
        self.acao_publicar.setToolTip("Enviar proposta de mudança no croqui")
        self.acao_publicar.triggered.connect(self.publicar_croqui)
        
        if self.workspace and not self.workspace.can_publish_pr():
            self.acao_publicar.setEnabled(False)
            self.acao_publicar.setToolTip("Envio de proposta de mudança não suportado no Local Mode.")
            self.acao_abrir.setEnabled(False)
            self.acao_abrir.setToolTip("Abrir outro croqui não suportado no Local Mode.")
        
        # Adiciona o espaçador primeiro para alinhar com a área de conteúdo
        self.toolbar_superior.addWidget(self.espacador_superior)
        self.toolbar_superior.addSeparator()
        
        self.toolbar_superior.addAction(self.acao_abrir)
        self.toolbar_superior.addAction(self.acao_salvar)
        self.toolbar_superior.addSeparator()
        self.toolbar_superior.addAction(self.acao_desfazer)
        self.addAction(self.acao_desfazer)
        self.toolbar_superior.addAction(self.acao_refazer)
        self.addAction(self.acao_refazer)
        self.toolbar_superior.addSeparator()
        self.toolbar_superior.addAction(self.acao_exportar)
        self.toolbar_superior.addAction(self.acao_celular)
        self.toolbar_superior.addSeparator()
        self.toolbar_superior.addAction(self.acao_publicar)
        
    def _setup_navegacao_lateral(self) -> None:
        self.acao_nav_dados = QAction(Icones.obter("dados"), "Dados", self)
        self.acao_nav_dados.setToolTip("Dados")
        self.acao_nav_dados.setCheckable(True)
        self.acao_nav_dados.setChecked(True)
        self.acao_nav_dados.triggered.connect(lambda: self._trocar_pagina(0))
        
        self.acao_nav_imagens = QAction(Icones.obter("imagens"), "Imagens", self)
        self.acao_nav_imagens.setToolTip("Imagens")
        self.acao_nav_imagens.setCheckable(True)
        self.acao_nav_imagens.triggered.connect(lambda: self._trocar_pagina(1))
        
        self.acao_nav_mapas = QAction(Icones.obter("mapas"), "Mapas", self)
        self.acao_nav_mapas.setToolTip("Mapas")
        self.acao_nav_mapas.setCheckable(True)
        self.acao_nav_mapas.triggered.connect(lambda: self._trocar_pagina(2))
        
        self.acao_nav_betas = QAction(Icones.obter("betas"), "Betas", self)
        self.acao_nav_betas.setToolTip("Betas")
        self.acao_nav_betas.setCheckable(True)
        self.acao_nav_betas.setVisible(False)
        self.acao_nav_betas.triggered.connect(lambda: self._trocar_pagina(3))

        self.acao_nav_historico = QAction(Icones.obter("historico"), "Histórico", self)
        self.acao_nav_historico.setToolTip("Histórico")
        self.acao_nav_historico.setCheckable(True)
        self.acao_nav_historico.setVisible(False) # TODO: Habilitar quando for implementado
        self.acao_nav_historico.triggered.connect(lambda: self._trocar_pagina(4))
        
        self.grupo_nav: List[QAction] = [self.acao_nav_dados, self.acao_nav_imagens, self.acao_nav_mapas, self.acao_nav_betas, self.acao_nav_historico]
        
        # Adiciona ações na toolbar lateral (setSpacing(4) cuidará do gap)
        self.toolbar_lateral.addActions(self.grupo_nav)
        
        # Força o tamanho do botão para garantir simetria
        for acao in self.grupo_nav:
            botao = self.toolbar_lateral.widgetForAction(acao)
            if botao:
                botao.setFixedSize(70, 62)
        
        # Garante o estilo de texto sob o ícone após adicionar as ações
        self.toolbar_lateral.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        
    def _setup_paginas(self) -> None:
        self.pagina_dados: PaginaDados = PaginaDados(self)
        self.pagina_imagens: PaginaImagens = PaginaImagens(self)
        self.pagina_mapas: PaginaMapas = PaginaMapas(self)
        self.pagina_betas: PaginaBetas = PaginaBetas(self)
        self.pagina_historico: PaginaHistorico = PaginaHistorico(self)
        
        self.stack.addWidget(self.pagina_dados)
        self.stack.addWidget(self.pagina_imagens)
        self.stack.addWidget(self.pagina_mapas)
        self.stack.addWidget(self.pagina_betas)
        self.stack.addWidget(self.pagina_historico)
        
        self.stack.setCurrentWidget(self.pagina_dados)
        
    def _trocar_pagina(self, indice: int) -> None:
        for i, acao in enumerate(self.grupo_nav):
            acao.setChecked(i == indice)
        
        self.stack.setCurrentIndex(indice)
        self._atualizar_acoes_contextuais()
        
        if getattr(self, "croqui_controller", None) and self.croqui_controller:
            mapa_paginas = {0: "page:dados", 1: "page:imagens", 2: "page:mapas", 3: "page:betas", 4: "page:historico"}
            self.croqui_controller.set_contexto(mapa_paginas.get(indice, "page:dados"))
        
    def _atualizar_acoes_contextuais(self) -> None:
        """Limpa as ações contextuais anteriores e adiciona as da nova página."""
        # Limpa anteriores
        for acao in self._acoes_contextuais:
            self.toolbar_superior.removeAction(acao)
        self._acoes_contextuais = []
        
        # Adiciona novas
        pagina_ativa = self.stack.currentWidget()
        if pagina_ativa and hasattr(pagina_ativa, 'obter_acoes_contextuais'):
            acoes = pagina_ativa.obter_acoes_contextuais()
            self._acoes_contextuais = acoes
            for acao in acoes:
                self.toolbar_superior.addAction(acao)

    def _on_foco_requisitado(self, uri: str) -> None:
        if not uri: return
        from editor.core.contexto import ContextoUIPath
        ctx = ContextoUIPath(uri)
        
        if ctx.pagina == "dados":
            if self.stack.currentIndex() != 0:
                self._trocar_pagina(0)
        elif ctx.pagina == "imagens":
            if self.stack.currentIndex() != 1:
                self._trocar_pagina(1)
            if hasattr(self.pagina_imagens, 'editor') and hasattr(self.pagina_imagens.editor, 'select_image_by_name'):
                nome_imagem = ctx.arquivo_mapa or ctx.caminho_local_arvore or uri.split("page:imagens/")[-1]
                if nome_imagem.startswith("file:"):
                    nome_imagem = nome_imagem[5:]
                self.pagina_imagens.editor.select_image_by_name(nome_imagem)
        elif ctx.pagina == "mapas":
            if self.stack.currentIndex() != 2:
                self._trocar_pagina(2)
            if ctx.arquivo_mapa and hasattr(self.pagina_mapas, 'editor') and self.croqui_model:
                croqui_ro = self.croqui_model.obter_croqui_readonly() if hasattr(self.croqui_model, "obter_croqui_readonly") else getattr(self.croqui_model, "croqui", None)
                if croqui_ro:
                    encontrou = False
                    for p_idx, pico in enumerate(croqui_ro.picos):
                        if encontrou: break
                        if pico.HasField('mapas_gerais'):
                            for m_idx, mapa in enumerate(pico.mapas_gerais.conteudo.mapas):
                                from pathlib import Path
                                if mapa.caminho_imagem_mapa and Path(mapa.caminho_imagem_mapa).name == ctx.arquivo_mapa:
                                    if hasattr(self.pagina_mapas.editor, 'selecionar_mapa_por_indices'):
                                        self.pagina_mapas.editor.selecionar_mapa_por_indices(p_idx, -1, m_idx)
                                    else:
                                        self.pagina_mapas.editor.set_mapa_atual(mapa, p_idx, -1, m_idx)
                                    encontrou = True
                                    break
                        if encontrou: break
                        for sg_idx, sg in enumerate(pico.setores_ou_grupos):
                            if encontrou: break
                            if not sg.HasField('setor'): continue
                            for m_idx, mapa in enumerate(sg.setor.conteudo.mapas):
                                from pathlib import Path
                                if mapa.caminho_imagem_mapa and Path(mapa.caminho_imagem_mapa).name == ctx.arquivo_mapa:
                                    if hasattr(self.pagina_mapas.editor, 'selecionar_mapa_por_indices'):
                                        self.pagina_mapas.editor.selecionar_mapa_por_indices(p_idx, sg_idx, m_idx)
                                    else:
                                        self.pagina_mapas.editor.set_mapa_atual(mapa, p_idx, sg_idx, m_idx)
                                    encontrou = True
                                    break
            elif ctx.caminho_local_arvore and hasattr(self.pagina_mapas, 'editor'):
                # Busca via node path
                import re
                p_idx, sg_idx, s_idx, m_idx = -1, -1, -1, -1
                match_s = re.search(r'expando:picos/item:(\d+)/expando:setores_ou_grupos/item:(\d+).*?expando:setores/item:(\d+).*?expando:mapas/item:(\d+)', ctx.caminho_local_arvore)
                if match_s:
                    p_idx, sg_idx, s_idx, m_idx = int(match_s.group(1)), int(match_s.group(2)), int(match_s.group(3)), int(match_s.group(4))
                else:
                    match_mg = re.search(r'expando:picos/item:(\d+).*?mapas_gerais.*?item:(\d+)', ctx.caminho_local_arvore)
                    if match_mg:
                        p_idx, m_idx = int(match_mg.group(1)), int(match_mg.group(2))
                    else:
                        match = re.search(r'expando:picos/item:(\d+)/expando:setores_ou_grupos/item:(\d+).*?expando:mapas/item:(\d+)', ctx.caminho_local_arvore)
                        if match:
                            p_idx, sg_idx, m_idx = int(match.group(1)), int(match.group(2)), int(match.group(3))
                
                if p_idx >= 0 and hasattr(self.pagina_mapas.editor, 'selecionar_mapa_por_indices'):
                    self.pagina_mapas.editor.selecionar_mapa_por_indices(p_idx, sg_idx, m_idx, s_idx)
        elif ctx.pagina == "historico":
            if self.stack.currentIndex() != 3:
                self._trocar_pagina(3)
        
    def _perguntar_recuperacao_sessao(self, total_acoes: int) -> bool:
        from editor.views.dialogo_recuperacao_sessao import DialogoRecuperacaoSessao
        from PySide6.QtWidgets import QDialog
        dialogo = DialogoRecuperacaoSessao(total_acoes=total_acoes, parent=self)
        return bool(dialogo.exec() == QDialog.DialogCode.Accepted)

    def carregar_croqui(self) -> None:
        """Carrega os dados do croqui a partir do sistema de arquivos."""
        if not self.workspace:
            return
            
        caminho_db = self.workspace.obter_caminho_database()
        
        # Roda as migrações no banco de dados antes de carregar
        from scripts.migrador import aplicar_migracoes
        aplicar_migracoes(caminho_db)
            
        yaml_path = caminho_db / "croqui.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r", encoding="utf-8") as f:
                self.croqui_data = yaml.safe_load(f)
                
                from google.protobuf.json_format import ParseDict
                from aresta_api.proto.generated.croqui_pb2 import Croqui
                
                croqui_msg = ParseDict(self.croqui_data, Croqui(), ignore_unknown_fields=True)
                import json
                croqui_msg.Extensions[Croqui.ext_metadados_arquivo].dados_json_originais = json.dumps(self.croqui_data, ensure_ascii=False)
                
                self.croqui_model = CroquiModel(croqui_msg)
                self.croqui_model.definir_caminho_db(caminho_db)
                if hasattr(self.croqui_model, "foco_requisitado"):
                    self.croqui_model.foco_requisitado.connect(self._on_foco_requisitado)
                self.croqui_controller = CroquiController(self.croqui_model, self.historico)
                
                # Inicializa/limpa rastreadores
                self.croqui_model.carregar_arquivos_externos(caminho_db)

                # Verifica recuperação de sessão e histórico no diário
                diario = self.workspace.obter_diario() if hasattr(self.workspace, "obter_diario") else None
                from editor.core.diario import GerenciadorDiario
                if isinstance(diario, GerenciadorDiario):
                    # 1. Carrega comandos salvos na pilha de Undo (permitindo Ctrl+Z entre sessões)
                    self.historico.carregar_diario_salvo(self.croqui_model, diario)

                    # 2. Verifica se há alterações pendentes de crash
                    if diario.tem_alteracoes_pendentes():
                        comandos_pendentes = diario.ler_diario_pendente()
                        if comandos_pendentes:
                            if self._perguntar_recuperacao_sessao(len(comandos_pendentes)):
                                self.historico.restaurar_do_diario(self.croqui_model, diario)
                            else:
                                diario.descartar_pendente()

                    self.historico.definir_gerenciador_diario(diario)
                
                # Atualiza os componentes com os dados carregados
                self.pagina_dados.carregar_dados(self.croqui_model, self.croqui_controller)
                self.pagina_imagens.carregar_imagens(caminho_db, model=self.croqui_model, controller=self.croqui_controller)
                self.pagina_mapas.carregar_mapas(self.croqui_model, self.historico, caminho_db, controller=self.croqui_controller)
                self.pagina_betas.carregar_betas(caminho_db)

                # Registra contexto no escopo de telemetria
                from editor.core.telemetria import registrar_contexto_croqui, anexar_diario_escopo
                id_croqui = self.croqui_data.get("id", "") if self.croqui_data else ""
                commit_base_sha = self.workspace.obter_commit_base_sha() if hasattr(self.workspace, "obter_commit_base_sha") else ""
                registrar_contexto_croqui(id_croqui=id_croqui, commit_base_sha=commit_base_sha)
                if isinstance(diario, GerenciadorDiario):
                    anexar_diario_escopo(diario)
                
                self.atualizar_titulo()
                
    def salvar_croqui(self, callback_sucesso: Optional[Callable[[], None]] = None) -> None:
        """Salva as alterações, compila e faz commit no git local se aplicável."""
        if not self.workspace or not self.croqui_data:
            return
            
        if self._salvando:
            return
            
        foco_atual = QApplication.focusWidget()
        if foco_atual:
            foco_atual.clearFocus()
            
        caminho_db = self.workspace.obter_caminho_database()
            
        try:
            if hasattr(self.pagina_dados, 'editor_dados') and self.pagina_dados.editor_dados and self.croqui_model:
                self.croqui_data = self.croqui_model.extrair_arquivos_e_serializar(caminho_db)

                
            if hasattr(self.pagina_mapas.editor, 'salvar_todas_mudancas'):
                self.pagina_mapas.editor.salvar_todas_mudancas(mostrar_mensagem=False)
            
            self.pagina_imagens.editor.salvar_alteracoes(mostrar_mensagem=False)
            
            novo_id = str(self.croqui_data.get("id", "")) if self.croqui_data else ""
            nome_raiz = self.workspace.caminho_raiz.name
            partes = nome_raiz.split("_", 1)
            id_atual = partes[1] if len(partes) > 1 and partes[0].isdigit() else nome_raiz
            
            undo_index = self.historico.obter_pilha().index()
            
            import copy
            from editor.core.worker import TarefaSalvamento
            self._worker_salvar = TarefaSalvamento(
                self.workspace, self.storage, caminho_db, copy.deepcopy(self.croqui_data), novo_id, id_atual, undo_index
            )
            self._worker_salvar.sucesso.connect(self._on_salvar_sucesso)
            self._worker_salvar.erro.connect(self._on_salvar_erro)
            
            self._salvando = True
            self._callback_sucesso_salvar = callback_sucesso
            
            if not self.label_status_salvamento:
                from PySide6.QtWidgets import QLabel
                from PySide6.QtCore import Qt
                self.label_status_salvamento = QLabel("Salvando...", self)
                self.label_status_salvamento.setStyleSheet("background-color: #28a745; color: white; padding: 5px; border-radius: 4px; font-weight: bold;")
                self.label_status_salvamento.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.label_status_salvamento.move(self.width() - 150, 20)
            self.label_status_salvamento.resize(120, 30)
            self.label_status_salvamento.show()
            self.label_status_salvamento.raise_()
            
            self._worker_salvar.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível iniciar o salvamento:\n{str(e)}")

    def _on_salvar_sucesso(self, caminho_retornado: Any, erros: List[str], houve_renomeacao: bool, undo_index: int) -> None:
        self._salvando = False
        if self.label_status_salvamento:
            self.label_status_salvamento.hide()
            
        if self.historico.obter_pilha().index() == undo_index:
            self.historico.obter_pilha().setClean()
            
        if erros:
            self.compilacao_controller.processar_resultado(erros)
        else:
            self.compilacao_controller.processar_resultado([])
            self.exibir_notificacao("Croqui salvo e compilado com sucesso!")
        
        if self.workspace:
            caminho_db = self.workspace.obter_caminho_database()
            if getattr(self, 'croqui_model', None):
                self.pagina_mapas.carregar_mapas(self.croqui_model, self.historico, caminho_db)
            self.pagina_imagens.carregar_imagens(caminho_db)
            
        if hasattr(self, 'salvamento_finalizado'):
            self.salvamento_finalizado.emit()
            
        if self._callback_sucesso_salvar:
            cb = self._callback_sucesso_salvar
            self._callback_sucesso_salvar = None
            cb()
            
        if self._fechar_apos_salvar:
            if self.dlg_espera:
                self.dlg_espera.accept()
            self.close()

    def _on_salvar_erro(self, e: Exception) -> None:
        self._salvando = False
        if self.label_status_salvamento:
            self.label_status_salvamento.hide()
        QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o croqui:\n{str(e)}")
        
        if hasattr(self, 'salvamento_finalizado'):
            self.salvamento_finalizado.emit()
            
        if self._fechar_apos_salvar:
            self._fechar_apos_salvar = False
            if hasattr(self, 'dlg_fechamento') and self.dlg_fechamento:
                self.dlg_fechamento.reject()

    def exportar_croqui(self) -> None:
        """Gera o arquivo .croqui (ZIP)."""
        if not self.workspace:
            return
            
        from PySide6.QtWidgets import QFileDialog
        
        id_croqui = self.croqui_data.get("id", "croqui") if self.croqui_data else "croqui"
        sugestao_nome = f"{id_croqui}.croqui"
        
        destino, _ = QFileDialog.getSaveFileName(
            self, "Exportar Croqui", sugestao_nome, "Arquivos de Croqui (*.croqui)"
        )
        
        if destino:
            try:
                from editor.core.worker import TarefaExportacao
                from PySide6.QtWidgets import QProgressDialog
                
                self.progresso_export: QProgressDialog = QProgressDialog("Compactando e ofuscando...", "", 0, 0, self)
                self.progresso_export.setWindowTitle("Exportando Croqui")
                self.progresso_export.setWindowModality(Qt.WindowModality.WindowModal)
                self.progresso_export.show()
                
                self._worker_export: TarefaExportacao = TarefaExportacao(self.workspace.caminho_raiz, Path(destino))
                self._worker_export.sucesso.connect(lambda: self.exibir_notificacao("Croqui exportado com sucesso!"))
                self._worker_export.sucesso.connect(self.progresso_export.close)
                self._worker_export.erro.connect(lambda e: QMessageBox.critical(self, "Erro ao Exportar", f"Falha na exportação:\n{e}"))
                self._worker_export.erro.connect(self.progresso_export.close)
                
                self._worker_export.start()
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Exportar", f"Não foi possível iniciar a exportação:\n{str(e)}")

    def publicar_croqui(self) -> None:
        """Inicia o fluxo de publicação do croqui."""
        if not self.workspace:
            return
            
        from editor.controllers.publish_controller import PublishController
        self._publish_controller: PublishController = PublishController(
            workspace=self.workspace,
            auth=self.auth,
            historico=self.historico,
            storage=self.storage,
            parent=self
        )
        self._publish_controller.iniciar_publicacao()

    def _descartar_diario_pendente(self) -> None:
        """Limpa o diário pendente caso o usuário feche sem salvar ou descarte as alterações."""
        if self.workspace and hasattr(self.workspace, "obter_diario"):
            diario = self.workspace.obter_diario()
            if diario and hasattr(diario, "descartar_pendente"):
                diario.descartar_pendente()

    def _on_abrir_novo_clicado(self) -> None:
        """Trata o clique no botão de voltar para a tela de carregamento."""
        if not self.historico.obter_pilha().isClean():
            resposta = QMessageBox.question(
                self, "Modificações Pendentes",
                "Existem modificações não salvas. Deseja salvar antes de sair?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if resposta == QMessageBox.StandardButton.Save:
                self._callback_sucesso_salvar = self._concluir_abrir_novo
                self.salvar_croqui()
            elif resposta == QMessageBox.StandardButton.Discard:
                self._descartar_diario_pendente()
                self._concluir_abrir_novo()
        else:
            self._descartar_diario_pendente()
            self._concluir_abrir_novo()

    def _concluir_abrir_novo(self) -> None:
        self._forcar_fechamento = True
        self.solicitar_abrir_novo.emit()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Intercepta o fechamento da janela para verificar modificações."""
        if self._forcar_fechamento:
            event.accept()
            return

        if self._salvando:
            self._fechar_apos_salvar = True
            self._mostrar_modal_espera("Finalizando salvamento...")
            event.ignore()
            return
            
        if not self.historico.obter_pilha().isClean():
            resposta = QMessageBox.question(
                self, "Sair do Editor",
                "Existem modificações não salvas. Deseja salvar antes de sair?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if resposta == QMessageBox.StandardButton.Save:
                self._fechar_apos_salvar = True
                self.salvar_croqui()
                self._mostrar_modal_espera("Finalizando salvamento...")
                event.ignore()
            elif resposta == QMessageBox.StandardButton.Discard:
                self._descartar_diario_pendente()
                event.accept()
            else:
                event.ignore()
        else:
            self._descartar_diario_pendente()
            event.accept()
            
    def _mostrar_modal_espera(self, mensagem: str = "Aguarde...") -> None:
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt
        if not self.dlg_espera:
            self.dlg_espera = QProgressDialog(mensagem, "", 0, 0, self)
            self.dlg_espera.setWindowTitle("Aguarde")
            self.dlg_espera.setWindowModality(Qt.WindowModality.WindowModal)
            self.dlg_espera.setCancelButton(None)
        else:
            self.dlg_espera.setLabelText(mensagem)
        self.dlg_espera.show()


    def _exibir_conexao_celular(self) -> None:
        """Inicia o servidor e exibe o diálogo de conexão com o celular."""
        if not self.workspace:
            QMessageBox.warning(self, "Aviso", "Abra um croqui antes de conectar ao celular.")
            return
            
        # Inicia o servidor se não estiver rodando
        if not self.servidor_celular:
            pasta_compilado = self.workspace.obter_pasta_servidor_celular()
            if not pasta_compilado.exists():
                pasta_compilado.mkdir(parents=True, exist_ok=True)
            
            jwt_supabase = None
            if self.auth and hasattr(self.auth, "carregar_sessao"):
                sessao_usr = self.auth.carregar_sessao()
                if sessao_usr and hasattr(sessao_usr, "jwt_supabase"):
                    jwt_supabase = sessao_usr.jwt_supabase

            self.servidor_celular = ServidorCelular(
                pasta_compilado,
                jwt_token=jwt_supabase,
                parent=self,
            )
            self.servidor_celular.dispositivo_conectado.connect(self._ao_celular_conectado)
            self.servidor_celular.iniciar()

        # Inicia o monitor de inatividade (10 segundos)
        if not self.monitor_inatividade:
            self.monitor_inatividade = MonitorInatividade(timeout_ms=10000, parent=self)
            self.monitor_inatividade.inatividade_detectada.connect(self.salvar_croqui)
            inst = QApplication.instance()
            if inst:
                inst.installEventFilter(self.monitor_inatividade)
            self.monitor_inatividade.iniciar()

        # Reusamos a instância para manter o estado visual (ex: "Conectado!")
        if not self.dialogo_celular:
            self.dialogo_celular = DialogoConexaoCelular(self.servidor_celular, self)
            self.dialogo_celular.solicitar_encerrar.connect(self._encerrar_servidor_celular)
        
        # Sincroniza o estado visual com o estado real do servidor antes de mostrar
        if self.servidor_celular.conectado:
            self.dialogo_celular._ao_dispositivo_conectado()

        self.dialogo_celular.exec()

    def _ao_celular_conectado(self) -> None:
        """Atualiza o ícone da toolbar quando o celular conecta."""
        self.acao_celular.setIcon(Icones.obter_celular(conectado=True))

    def _encerrar_servidor_celular(self) -> None:
        """Para o servidor e limpa os recursos de conexão."""
        if self.servidor_celular:
            self.servidor_celular.parar()
            self.servidor_celular = None
            
        if self.monitor_inatividade:
            self.monitor_inatividade.parar()
            inst = QApplication.instance()
            if inst:
                inst.removeEventFilter(self.monitor_inatividade)
            self.monitor_inatividade = None
            
        self.dialogo_celular = None
        self.acao_celular.setIcon(Icones.obter_celular(conectado=False))

    def exibir_notificacao(self, mensagem: str) -> None:
        """Exibe uma notificação temporária no canto inferior direito."""
        toast = NotificacaoToast(mensagem, parent=self)
        toast.show()
        toast.posicionar_no_canto(self)

