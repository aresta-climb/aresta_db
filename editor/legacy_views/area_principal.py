from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QStyle, QMessageBox, QDialog, QLineEdit, QTextEdit, QPushButton, QFormLayout,
    QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QKeySequence
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

class DialogoPublicar(QDialog):
    """Diálogo para coletar informações para o Pull Request."""
    def __init__(self, titulo_padrao="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publicar no GitHub")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.edit_titulo = QLineEdit(f"Croqui: {titulo_padrao}")
        self.edit_descricao = QTextEdit()
        self.edit_descricao.setPlaceholderText("Descreva as alterações feitas...")
        
        form.addRow("Título da PR:", self.edit_titulo)
        form.addRow("Descrição:", self.edit_descricao)
        layout.addLayout(form)
        
        botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_publicar = QPushButton("Publicar Agora")
        self.btn_publicar.setDefault(True)
        self.btn_publicar.clicked.connect(self.accept)
        
        botoes.addStretch()
        botoes.addWidget(self.btn_cancelar)
        botoes.addWidget(self.btn_publicar)
        layout.addLayout(botoes)

    def obter_dados(self):
        return {
            "titulo": self.edit_titulo.text(),
            "descricao": self.edit_descricao.toPlainText()
        }

class PaginaBase(QWidget):
    """Classe base para as páginas do editor."""
    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.titulo = titulo
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Página: {titulo}\n(A Implementar)", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 24px; color: #666; font-weight: bold;")
        layout.addWidget(self.label)
        self.setStyleSheet(".PaginaBase { background-color: #ffffff; border-radius: 10px; }")

    def obter_acoes_contextuais(self):
        """Retorna uma lista de QActions específicas desta página."""
        return []

class PaginaDados(PaginaBase):
    def __init__(self, parent=None):
        super().__init__("Dados", parent)
        self.layout().removeWidget(self.label)
        self.label.deleteLater()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.editor_dados = None
        
    def carregar_dados(self, model, controller):
        if self.editor_dados:
            self.layout().removeWidget(self.editor_dados)
            self.editor_dados.deleteLater()
            
        from editor.views.widget_editor_dados import WidgetEditorDados
        self.editor_dados = WidgetEditorDados(model, controller, parent=self)
        self.layout().addWidget(self.editor_dados)

class PaginaImagens(PaginaBase):
    def __init__(self, parent=None):
        super().__init__("Imagens", parent)
        # Remove o label de placeholder
        self.layout().removeWidget(self.label)
        self.label.deleteLater()
        
        # Remove as margens da página base
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        # O folder_path inicial é vazio, será carregado em carregar_imagens
        self.editor = WidgetEditorImagens("", modo_integrado=True, parent=self)
        self.layout().addWidget(self.editor)
        
    def carregar_imagens(self, caminho_db):
        if caminho_db:
            self.editor.folder_path = str(caminho_db)
            self.editor.imagens_path = str(Path(caminho_db) / "imagens")
            self.editor.load_images_list()
class PaginaMapas(PaginaBase):
    def __init__(self, parent=None):
        super().__init__("Mapas", parent)
        # Remove o label de placeholder
        self.layout().removeWidget(self.label)
        self.label.deleteLater()
        
        # Remove as margens da página base para o editor de mapas ocupar tudo
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.editor = WidgetEditorMapas(parent=self)
        self.layout().addWidget(self.editor)
        
    def carregar_mapas(self, model, undo_stack, caminho_db=None):
        if model:
            from editor.controllers.mapas_controller import MapasController
            mapas_controller = MapasController(model, undo_stack)
            if caminho_db:
                mapas_controller.set_caminho_db(caminho_db)
            self.editor.mapas_controller = mapas_controller
            self.editor.configurar_lista_mapas()

class PaginaHistorico(PaginaBase):
    def __init__(self, parent=None):
        super().__init__("Histórico", parent)

class JanelaPrincipal(QMainWindow):
    # Sinal emitido quando o usuário deseja voltar para a tela de carregamento
    solicitar_abrir_novo = pyqtSignal()
    
    def __init__(self, storage=None, auth=None, workspace=None, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 9))
        self.storage = storage
        self.auth = auth
        self.workspace = workspace
        self.croqui_data = None
        self._acoes_contextuais = []
        self._worker_pr = None
        
        self.servidor_celular = None
        self.monitor_inatividade = None
        self.dialogo_celular = None
        self.historico = GerenciadorHistorico()
        self.historico.obter_pilha().cleanChanged.connect(self._on_clean_changed)
        
        self.setWindowTitle("Aresta Editor")
        self.resize(1200, 800)
        
        # Componentes do Painel de Saída de Compilação
        self.compilacao_log = CompilacaoLog()
        self.widget_saida_compilacao = WidgetSaidaCompilacao(self)
        self.compilacao_controller = CompilacaoController(self.compilacao_log, self.widget_saida_compilacao)
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
        
    def _setup_ui(self):
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
        
        
    def _setup_toolbars(self):
        self.toolbar_superior = QToolBar("Barra Superior")
        self.toolbar_superior.setObjectName("toolbar_superior")
        self.toolbar_superior.setMovable(False)
        self.toolbar_superior.setIconSize(QSize(24, 24))
        
        # Logo do aplicativo (montanha verde musgo)
        self.espacador_superior = QLabel()
        self.espacador_superior.setFixedWidth(63)
        self.espacador_superior.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from PyQt6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QColor
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

    def _on_clean_changed(self, is_clean: bool):
        """Atualiza o título da janela baseado no estado limpo da pilha de histórico."""
        if not is_clean:
            self.setWindowTitle("Aresta Editor *")
        else:
            self.setWindowTitle("Aresta Editor")
        
    def _setup_acoes_globais(self):
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
        
        self.acao_publicar = QAction(Icones.obter("publicar"), "Publicar", self)
        self.acao_publicar.setToolTip("Publicar para produção")
        self.acao_publicar.triggered.connect(self.publicar_croqui)
        
        if self.workspace and not self.workspace.can_publish_pr():
            self.acao_publicar.setEnabled(False)
            self.acao_publicar.setToolTip("Publicar pelo Editor não suportado no Local Mode.")
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
        
    def _setup_navegacao_lateral(self):
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
        
        self.acao_nav_historico = QAction(Icones.obter("historico"), "Histórico", self)
        self.acao_nav_historico.setToolTip("Histórico")
        self.acao_nav_historico.setCheckable(True)
        self.acao_nav_historico.triggered.connect(lambda: self._trocar_pagina(3))
        
        self.grupo_nav = [self.acao_nav_dados, self.acao_nav_imagens, self.acao_nav_mapas, self.acao_nav_historico]
        
        # Adiciona ações na toolbar lateral (setSpacing(4) cuidará do gap)
        self.toolbar_lateral.addActions(self.grupo_nav)
        
        # Força o tamanho do botão para garantir simetria
        for acao in self.grupo_nav:
            botao = self.toolbar_lateral.widgetForAction(acao)
            if botao:
                botao.setFixedSize(70, 62)
        
        # Garante o estilo de texto sob o ícone após adicionar as ações
        self.toolbar_lateral.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        
    def _setup_paginas(self):
        self.pagina_dados = PaginaDados(self)
        self.pagina_imagens = PaginaImagens(self)
        self.pagina_mapas = PaginaMapas(self)
        self.pagina_historico = PaginaHistorico(self)
        
        self.stack.addWidget(self.pagina_dados)
        self.stack.addWidget(self.pagina_imagens)
        self.stack.addWidget(self.pagina_mapas)
        self.stack.addWidget(self.pagina_historico)
        
        self.stack.setCurrentWidget(self.pagina_dados)
        
    def _trocar_pagina(self, indice):
        for i, acao in enumerate(self.grupo_nav):
            acao.setChecked(i == indice)
        
        self.stack.setCurrentIndex(indice)
        self._atualizar_acoes_contextuais()
        
    def _atualizar_acoes_contextuais(self):
        """Limpa as ações contextuais anteriores e adiciona as da nova página."""
        # Limpa anteriores
        for acao in self._acoes_contextuais:
            self.toolbar_superior.removeAction(acao)
        self._acoes_contextuais = []
        
        # Adiciona novas
        pagina_ativa = self.stack.currentWidget()
        if hasattr(pagina_ativa, 'obter_acoes_contextuais'):
            acoes = pagina_ativa.obter_acoes_contextuais()
            self._acoes_contextuais = acoes
            for acao in acoes:
                self.toolbar_superior.addAction(acao)

    def _on_foco_requisitado(self, uri: str):
        if not uri: return
        from editor.core.contexto import ContextoUIPath
        ctx = ContextoUIPath(uri)
        
        if ctx.pagina == "dados":
            if self.stack.currentIndex() != 0:
                self._trocar_pagina(0)
        elif ctx.pagina == "imagens":
            if self.stack.currentIndex() != 1:
                self._trocar_pagina(1)
        elif ctx.pagina == "mapas":
            if self.stack.currentIndex() != 2:
                self._trocar_pagina(2)
            if ctx.arquivo_mapa and hasattr(self.pagina_mapas, 'editor'):
                # Busca o mapa na hierarquia pelo filename original (legacy)
                encontrou = False
                for p_idx, pico in enumerate(self.croqui_model.croqui_msg.picos):
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
                    match = re.search(r'expando:picos/item:(\d+)/expando:setores_ou_grupos/item:(\d+).*?expando:mapas/item:(\d+)', ctx.caminho_local_arvore)
                    if match:
                        p_idx, sg_idx, m_idx = int(match.group(1)), int(match.group(2)), int(match.group(3))
                
                if p_idx >= 0 and hasattr(self.pagina_mapas.editor, 'selecionar_mapa_por_indices'):
                    self.pagina_mapas.editor.selecionar_mapa_por_indices(p_idx, sg_idx, m_idx, s_idx)
        elif ctx.pagina == "historico":
            if self.stack.currentIndex() != 3:
                self._trocar_pagina(3)
        
    def carregar_croqui(self):
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
                
                # Configura o título com tag de workspace
                nome_croqui = self.croqui_data.get('nome', 'Sem Nome')
                tag = self.workspace.obter_tag_titulo()
                titulo = f"Aresta Editor - {tag} - {nome_croqui}" if tag else f"Aresta Editor - {nome_croqui}"
                self.setWindowTitle(titulo)
                
                from google.protobuf.json_format import ParseDict
                from aresta_api.proto.generated.croqui_pb2 import Croqui
                
                croqui_msg = ParseDict(self.croqui_data, Croqui(), ignore_unknown_fields=True)
                import json
                croqui_msg.Extensions[Croqui.ext_metadados_arquivo].dados_json_originais = json.dumps(self.croqui_data, ensure_ascii=False)
                
                from editor.models.croqui_model import CroquiModel
                self.croqui_model = CroquiModel(croqui_msg)
                if hasattr(self.croqui_model, "foco_requisitado"):
                    self.croqui_model.foco_requisitado.connect(self._on_foco_requisitado)
                
                from editor.controllers.croqui_controller import CroquiController
                self.croqui_controller = CroquiController(self.croqui_model, self.historico.obter_pilha())
                
                # Inicializa/limpa rastreadores
                self.croqui_model.carregar_arquivos_externos(caminho_db)
                
                # Configura a UI
                self.pagina_dados.carregar_dados(self.croqui_model, self.croqui_controller)
                self.pagina_mapas.carregar_mapas(self.croqui_model, self.historico.obter_pilha(), caminho_db)
                self.pagina_imagens.carregar_imagens(caminho_db)
                
    def salvar_croqui(self):
        """Salva as alterações, compila e faz commit no git local se aplicável."""
        if not self.workspace or not self.croqui_data:
            return
            
        foco_atual = QApplication.focusWidget()
        if foco_atual:
            foco_atual.clearFocus()
            
        caminho_db = self.workspace.obter_caminho_database()
            
        try:
            if hasattr(self.pagina_dados, 'editor_dados') and self.pagina_dados.editor_dados:
                # Usar a assinatura atualizada que não recebe dicionários de tracking
                self.croqui_data = self.croqui_model.extrair_arquivos_e_serializar(caminho_db)
                
            # 1. Salva croqui.yaml na pasta ATUAL do db
            yaml_path = caminho_db / "croqui.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(self.croqui_data, f, allow_unicode=True, sort_keys=False)
                
            # 2. Salva Mapas na pasta ATUAL
            if hasattr(self.pagina_mapas.editor, 'salvar_todas_mudancas'):
                self.pagina_mapas.editor.salvar_todas_mudancas(mostrar_mensagem=False)
            
            # 3. Salva Imagens na pasta ATUAL
            self.pagina_imagens.editor.salvar_alteracoes(mostrar_mensagem=False)
            
            # Verifica se precisa renomear a pasta (mudou o ID)
            novo_id = self.croqui_data.get("id") if self.croqui_data else None
            
            nome_raiz = self.workspace.caminho_raiz.name
            partes = nome_raiz.split("_", 1)
            id_atual = partes[1] if len(partes) > 1 and partes[0].isdigit() else nome_raiz

            houve_renomeacao = False
            if novo_id and id_atual and novo_id != id_atual:
                houve_renomeacao = True
                
            # 4. Processa renomeação (se houver) e Compila
            caminho_retornado, erros = self.workspace.processar_renomeacao_e_compilacao(novo_id, id_atual, self.storage)
            
            self.historico.obter_pilha().setClean()
            
            if erros:
                self.compilacao_controller.processar_resultado(erros)
            else:
                self.compilacao_controller.processar_resultado([])
                self.exibir_notificacao("Croqui salvo e compilado com sucesso!")
            
            if houve_renomeacao:
                # Recarrega para atualizar os caminhos absolutos que os editores seguram em memória
                novo_db = self.workspace.obter_caminho_database()
                if hasattr(self, 'croqui_model') and self.croqui_model:
                    # Força a atualização do widget de mapas se estiver ativo e houver modelo
                    if getattr(self, "croqui_model", None) is not None:
                        self.pagina_mapas.carregar_mapas(self.croqui_model, self.historico.obter_pilha(), novo_db)
                self.pagina_imagens.carregar_imagens(novo_db)
                
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o croqui:\n{str(e)}")

    def exportar_croqui(self):
        """Gera o arquivo .croqui (ZIP)."""
        if not self.workspace:
            return
            
        from PyQt6.QtWidgets import QFileDialog
        
        id_croqui = self.croqui_data.get("id", "croqui") if self.croqui_data else "croqui"
        sugestao_nome = f"{id_croqui}.croqui"
        
        destino, _ = QFileDialog.getSaveFileName(
            self, "Exportar Croqui", sugestao_nome, "Arquivos de Croqui (*.croqui)"
        )
        
        if destino:
            try:
                from editor.core.worker import TarefaExportacao
                from PyQt6.QtWidgets import QProgressDialog
                
                self.progresso_export = QProgressDialog("Compactando e ofuscando...", None, 0, 0, self)
                self.progresso_export.setWindowTitle("Exportando Croqui")
                self.progresso_export.setWindowModality(Qt.WindowModality.WindowModal)
                self.progresso_export.show()
                
                self._worker_export = TarefaExportacao(self.workspace.caminho_raiz, Path(destino))
                self._worker_export.sucesso.connect(lambda: self.exibir_notificacao("Croqui exportado com sucesso!"))
                self._worker_export.sucesso.connect(self.progresso_export.close)
                self._worker_export.erro.connect(lambda e: QMessageBox.critical(self, "Erro ao Exportar", f"Falha na exportação:\n{e}"))
                self._worker_export.erro.connect(self.progresso_export.close)
                
                self._worker_export.start()
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Exportar", f"Não foi possível iniciar a exportação:\n{str(e)}")

    def publicar_croqui(self):
        """Cria um Pull Request no GitHub com as alterações do croqui."""
        if not self.workspace or not self.auth:
            return
            
        if not self.historico.obter_pilha().isClean():
            resposta = QMessageBox.question(
                self, "Salvar Necessário",
                "Você precisa salvar suas alterações antes de publicar. Deseja salvar agora?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel
            )
            if resposta == QMessageBox.StandardButton.Save:
                self.salvar_croqui()
            else:
                return

        # Coleta dados da PR
        titulo_sugerido = self.croqui_data.get("nome", self.workspace.caminho_raiz.name) if self.croqui_data else self.workspace.caminho_raiz.name
        dialogo = DialogoPublicar(titulo_padrao=titulo_sugerido, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
            
        dados_pr = dialogo.obter_dados()
        
        # Inicia Worker
        from editor.core.worker import TarefaPublicacao
        from PyQt6.QtWidgets import QProgressDialog
        
        self.progresso_pr = QProgressDialog("Iniciando publicação...", "Cancelar", 0, 100, self)
        self.progresso_pr.setWindowTitle("Publicando no GitHub")
        self.progresso_pr.setWindowModality(Qt.WindowModality.WindowModal)
        self.progresso_pr.setAutoClose(True)
        self.progresso_pr.show()

        self._worker_pr = TarefaPublicacao(
            token=self.auth.recuperar_token(),
            storage=self.storage,
            caminho_database_croqui=self.workspace.obter_caminho_database(),
            id_croqui=self.croqui_data.get("id") if self.croqui_data else self.workspace.caminho_raiz.name,
            dados_pr=dados_pr
        )
        
        self._worker_pr.status.connect(self.progresso_pr.setLabelText)
        self._worker_pr.progresso.connect(self.progresso_pr.setValue)
        self._worker_pr.sucesso.connect(self._on_publicacao_sucesso)
        self._worker_pr.erro.connect(self._on_publicacao_erro)
        
        self._worker_pr.start()

    def _on_publicacao_sucesso(self, url_pr):
        QMessageBox.information(self, "Sucesso", f"Pull Request criada com sucesso!\n\nLink: {url_pr}")
        # Opcional: abrir no browser
        import webbrowser
        webbrowser.open(url_pr)

    def _on_publicacao_erro(self, erro):
        QMessageBox.critical(self, "Erro na Publicação", f"Falha ao criar Pull Request:\n{erro}")

    def _on_abrir_novo_clicado(self):
        """Trata o clique no botão de voltar para a tela de carregamento."""
        if not self.historico.obter_pilha().isClean():
            resposta = QMessageBox.question(
                self, "Modificações Pendentes",
                "Existem modificações não salvas. Deseja salvar antes de sair?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if resposta == QMessageBox.StandardButton.Save:
                self.salvar_croqui()
                self.solicitar_abrir_novo.emit()
            elif resposta == QMessageBox.StandardButton.Discard:
                self.solicitar_abrir_novo.emit()
        else:
            self.solicitar_abrir_novo.emit()

    def closeEvent(self, event):
        """Intercepta o fechamento da janela para verificar modificações."""
        if not self.historico.obter_pilha().isClean():
            resposta = QMessageBox.question(
                self, "Sair do Editor",
                "Existem modificações não salvas. Deseja salvar antes de sair?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            
            if resposta == QMessageBox.StandardButton.Save:
                self.salvar_croqui()
                event.accept()
            elif resposta == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
    def _exibir_conexao_celular(self):
        """Inicia o servidor e exibe o diálogo de conexão com o celular."""
        if not self.workspace:
            QMessageBox.warning(self, "Aviso", "Abra um croqui antes de conectar ao celular.")
            return
            
        # Inicia o servidor se não estiver rodando
        if not self.servidor_celular:
            pasta_compilado = self.workspace.obter_caminho_compilado()
            if not pasta_compilado.exists():
                pasta_compilado.mkdir(parents=True, exist_ok=True)
            
            self.servidor_celular = ServidorCelular(pasta_compilado, self)
            self.servidor_celular.dispositivo_conectado.connect(self._ao_celular_conectado)
            self.servidor_celular.iniciar()

        # Inicia o monitor de inatividade (10 segundos)
        if not self.monitor_inatividade:
            self.monitor_inatividade = MonitorInatividade(timeout_ms=10000, parent=self)
            self.monitor_inatividade.inatividade_detectada.connect(self.salvar_croqui)
            QApplication.instance().installEventFilter(self.monitor_inatividade)
            self.monitor_inatividade.iniciar()

        # Reusamos a instância para manter o estado visual (ex: "Conectado!")
        if not self.dialogo_celular:
            self.dialogo_celular = DialogoConexaoCelular(self.servidor_celular, self)
            self.dialogo_celular.solicitar_encerrar.connect(self._encerrar_servidor_celular)
        
        # Sincroniza o estado visual com o estado real do servidor antes de mostrar
        if self.servidor_celular.conectado:
            self.dialogo_celular._ao_dispositivo_conectado()

        self.dialogo_celular.exec()

    def _ao_celular_conectado(self):
        """Atualiza o ícone da toolbar quando o celular conecta."""
        self.acao_celular.setIcon(Icones.obter_celular(conectado=True))

    def _encerrar_servidor_celular(self):
        """Para o servidor e limpa os recursos de conexão."""
        if self.servidor_celular:
            self.servidor_celular.parar()
            self.servidor_celular = None
            
        if self.monitor_inatividade:
            self.monitor_inatividade.parar()
            QApplication.instance().removeEventFilter(self.monitor_inatividade)
            self.monitor_inatividade = None
            
        self.dialogo_celular = None
        self.acao_celular.setIcon(Icones.obter_celular(conectado=False))

    def exibir_notificacao(self, mensagem):
        """Exibe uma notificação temporária no canto inferior direito."""
        toast = NotificacaoToast(mensagem, parent=self)
        toast.show()
        toast.posicionar_no_canto(self)
