import pytest
from PyQt6.QtWidgets import QMainWindow, QToolBar, QStackedWidget, QWidget, QDialog
from PyQt6.QtCore import Qt
from editor.legacy_views.area_principal import JanelaPrincipal, PaginaDados, PaginaImagens, PaginaMapas, PaginaHistorico
from PyQt6.QtGui import QIcon
from unittest.mock import MagicMock, patch

def test_janela_principal_usa_icones_qtawesome(qtbot):
    with patch("editor.views.estilo.Icones.obter") as mock_obter:
        mock_obter.return_value = QIcon()
        janela = JanelaPrincipal()
        qtbot.addWidget(janela)
        
        # Coleta os nomes de ícones solicitados ao helper
        nomes_solicitados = [chamada.args[0] for chamada in mock_obter.call_args_list]
        
        # Verifica se as principais ações solicitaram ícones ao helper
        acoes_obrigatorias = ["novo", "salvar", "publicar", "dados", "imagens", "mapas"]
        for acao in acoes_obrigatorias:
            assert acao in nomes_solicitados, f"Ícone para '{acao}' não foi solicitado ao helper Icones"

def test_janela_principal_e_uma_main_window(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    assert isinstance(janela, QMainWindow)

def test_janela_principal_tem_areas_obrigatorias(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Verifica Toolbar Superior
    toolbar_superior = janela.findChild(QToolBar, "toolbar_superior")
    assert toolbar_superior is not None
    assert janela.toolBarArea(toolbar_superior) == Qt.ToolBarArea.TopToolBarArea
    
    # Verifica Toolbar Lateral
    toolbar_lateral = janela.findChild(QToolBar, "toolbar_lateral")
    assert toolbar_lateral is not None
    assert janela.toolBarArea(toolbar_lateral) == Qt.ToolBarArea.LeftToolBarArea
    
    # Verifica Widget Central (Stacked)
    widget_central = janela.findChild(QStackedWidget)
    assert widget_central is not None

def test_janela_principal_exibe_pagina_dados_inicialmente(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    stack = janela.findChild(QStackedWidget)
    assert isinstance(stack.currentWidget(), PaginaDados)

def test_toolbar_superior_tem_acoes_globais(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    toolbar = janela.findChild(QToolBar, "toolbar_superior")
    acoes = toolbar.actions()
    textos_acoes = [a.toolTip() for a in acoes] # Usando tooltip para identificar ações com ícone
    
    assert "Abrir Novo" in textos_acoes
    assert "Salvar" in textos_acoes
    assert "Desfazer" in textos_acoes
    assert "Refazer" in textos_acoes
    assert "Exportar .croqui" in textos_acoes
    assert "Conectar com celular..." in textos_acoes
    assert "Publicar para produção" in textos_acoes

def test_toolbar_lateral_tem_navegacao_entre_visoes(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    toolbar = janela.findChild(QToolBar, "toolbar_lateral")
    acoes = toolbar.actions()
    textos_acoes = [a.toolTip() for a in acoes]
    
    assert "Dados" in textos_acoes
    assert "Imagens" in textos_acoes
    assert "Mapas" in textos_acoes
    assert "Histórico" in textos_acoes

def test_navegacao_lateral_troca_paginas(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    stack = janela.findChild(QStackedWidget)
    
    toolbar = janela.findChild(QToolBar, "toolbar_lateral")
    acoes = toolbar.actions()
    
    # Encontra ação de Imagens
    acao_imagens = next(a for a in acoes if a.toolTip() == "Imagens")
    acao_imagens.trigger()
    assert isinstance(stack.currentWidget(), PaginaImagens)
    
    # Encontra ação de Mapas
    acao_mapas = next(a for a in acoes if a.toolTip() == "Mapas")
    acao_mapas.trigger()
    assert isinstance(stack.currentWidget(), PaginaMapas)
    
    # Encontra ação de Histórico
    acao_historico = next(a for a in acoes if a.toolTip() == "Histórico")
    acao_historico.trigger()
    assert isinstance(stack.currentWidget(), PaginaHistorico)
    
    # Volta para Dados
    acao_dados = next(a for a in acoes if a.toolTip() == "Dados")
    acao_dados.trigger()
    assert isinstance(stack.currentWidget(), PaginaDados)

def test_clique_publicar_inicia_worker(qtbot):
    # Mock do Diálogo para não abrir janela real no teste
    with patch("editor.legacy_views.area_principal.DialogoPublicar") as MockDialog:
        MockDialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
        MockDialog.return_value.obter_dados.return_value = {"titulo": "Test", "descricao": "Test"}
        
        # Mock do Worker para não iniciar thread real
        with patch("editor.core.worker.TarefaPublicacao") as MockWorker:
            mock_workspace = MagicMock()
            mock_workspace.obter_caminho_database.return_value = Path("temp_croqui_db")
            janela = JanelaPrincipal(auth=MagicMock(), workspace=mock_workspace)
            qtbot.addWidget(janela)
            
            toolbar = janela.findChild(QToolBar, "toolbar_superior")
            acoes = toolbar.actions()
            acao_publicar = next(a for a in acoes if a.toolTip() == "Publicar para produção")
            
            acao_publicar.trigger()
            
            assert MockWorker.called

def test_janela_principal_nao_gera_avisos_de_fonte_qt(qtbot):
    """Verifica se a inicialização da janela não dispara avisos de QFont no terminal."""
    avisos = []
    
    def message_handler(mode, context, message):
        # Captura avisos específicos de fonte
        if ("QFont" in message or "PointSize" in message) and "Cannot find font directory" not in message:
            avisos.append(message)
            
    from PyQt6.QtCore import qInstallMessageHandler
    
    # Instala o interceptor
    original_handler = qInstallMessageHandler(message_handler)
    
    try:
        janela = JanelaPrincipal()
        qtbot.addWidget(janela)
        
        # Simula hover sobre os botões da barra lateral para disparar repaints
        for acao in janela.grupo_nav:
            botao = janela.toolbar_lateral.widgetForAction(acao)
            if botao:
                qtbot.mouseMove(botao)
                qtbot.wait(50) # Pequena pausa para processar eventos de pintura
    finally:
        # Restaura o handler original
        qInstallMessageHandler(original_handler)
        
    assert len(avisos) == 0, f"Avisos de fonte detectados: {avisos}"

from editor.core.croqui_experimental import GerenciadorCroquiExperimental

def test_salvar_croqui_exibe_notificacao(qtbot):
    # Mock do Gerenciador para não salvar arquivos reais
    with patch.object(GerenciadorCroquiExperimental, "compilar_croqui"), \
         patch("editor.legacy_views.area_principal.QMessageBox.information") as mock_info:
        
        mock_workspace = MagicMock()
        mock_workspace.obter_caminho_database.return_value = Path("temp_croqui")
        mock_workspace.caminho_raiz.name = "temp_croqui"
        mock_workspace.processar_renomeacao_e_compilacao.return_value = (Path("temp_croqui"), [])
        janela = JanelaPrincipal(workspace=mock_workspace)
        qtbot.addWidget(janela)
        janela.croqui_data = {"id": "teste"} # Simula croqui carregado
        janela.croqui_model = MagicMock()
        
        janela.pagina_dados = MagicMock()
        janela.pagina_mapas = MagicMock()
        janela.pagina_imagens = MagicMock()
        
        # Mock do open para não tentar escrever no disco
        with patch("builtins.open", MagicMock()), \
             patch("editor.legacy_views.area_principal.yaml.dump"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit, \
             patch.object(janela, "exibir_notificacao") as mock_notif:
            
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            janela.salvamento_finalizado.connect(loop.quit)
            janela.salvar_croqui()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            
            # Verifica que QMessageBox NÃO foi chamado
            mock_info.assert_not_called()
            if mock_crit.called:
                print("ERRO NO SALVAR:", mock_crit.call_args)
            assert not mock_crit.called
            # Verifica que a notificação FOI chamada
            mock_notif.assert_called_once_with("Croqui salvo e compilado com sucesso!")

def test_salvar_croqui_assincrono_nao_trava_ui(qtbot, tmp_path):
    """[TDD] Verifica se o salvamento ocorre de forma assíncrona, não bloqueando a UI."""
    with patch.object(GerenciadorCroquiExperimental, "compilar_croqui"):
        db_path = tmp_path / "temp_croqui"
        db_path.mkdir()
        mock_workspace = MagicMock()
        mock_workspace.obter_caminho_database.return_value = db_path
        mock_workspace.caminho_raiz.name = "temp_croqui"
        mock_workspace.processar_renomeacao_e_compilacao.return_value = (db_path, [])
        janela = JanelaPrincipal(workspace=mock_workspace)
        qtbot.addWidget(janela)
        janela.croqui_data = {"id": "teste"}
        janela.croqui_model = MagicMock()
        janela.croqui_model.extrair_arquivos_e_serializar.return_value = {"id": "teste_serializado"}
        janela.pagina_dados = MagicMock()
        janela.pagina_mapas = MagicMock()
        janela.pagina_imagens = MagicMock()
        janela.pagina_imagens.editor.salvar_alteracoes = MagicMock()
        
        with patch.object(janela, "exibir_notificacao"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit:
             
            event_loop_ran = False
            def process_events_check():
                nonlocal event_loop_ran
                event_loop_ran = True
            
            from PyQt6.QtCore import QTimer
            timer = QTimer()
            timer.timeout.connect(process_events_check)
            timer.start(10)
            
            original_processar = mock_workspace.processar_renomeacao_e_compilacao
            def mock_salvar_lento(*args, **kwargs):
                import time
                time.sleep(0.1)
                return (Path("temp_croqui"), [])
                
            mock_workspace.processar_renomeacao_e_compilacao.side_effect = mock_salvar_lento
    
            janela.show()
            janela.salvar_croqui()
    
            assert hasattr(janela, 'label_status_salvamento') and not janela.label_status_salvamento.isHidden(), "Aviso de salvamento não está visível na UI"
            
            if hasattr(janela, 'salvamento_finalizado'):
                with qtbot.waitSignal(janela.salvamento_finalizado, timeout=1000):
                    pass
                timer.stop()
                if mock_crit.called:
                    print("ERRO CAPTURADO:", mock_crit.call_args)
                assert event_loop_ran, "O Event Loop travou e o QTimer não rodou!"
                qtbot.waitUntil(lambda: janela.label_status_salvamento.isHidden(), timeout=1000)

def test_janela_principal_tem_icone_configurado(qtbot):
    """Garante que a Janela Principal carrega o ícone de montanha."""
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    assert not janela.windowIcon().isNull()

def test_atalhos_teclado_desfazer_refazer(qtbot):
    from PyQt6.QtGui import QKeySequence
    from PyQt6.QtCore import Qt
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Verifica desfazer
    shortcuts_undo = janela.acao_desfazer.shortcuts()
    assert QKeySequence.StandardKey.Undo in shortcuts_undo, "Atalho padrão de Undo (Ctrl+Z) ausente"
    assert janela.acao_desfazer.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut, "Contexto do atalho deve ser global (ApplicationShortcut)"
    
    # Verifica refazer
    shortcuts_redo = janela.acao_refazer.shortcuts()
    assert QKeySequence.StandardKey.Redo in shortcuts_redo, "Atalho padrão de Redo (Ctrl+Y/Ctrl+Shift+Z) ausente"
    assert janela.acao_refazer.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut, "Contexto do atalho deve ser global (ApplicationShortcut)"

def test_salvar_croqui_remove_foco_do_widget_ativo(qtbot):
    from PyQt6.QtWidgets import QLineEdit
    from PyQt6.QtWidgets import QApplication
    
    with patch.object(GerenciadorCroquiExperimental, "compilar_croqui"):
        mock_workspace = MagicMock()
        mock_workspace.obter_caminho_database.return_value = Path("temp_croqui_db")
        janela = JanelaPrincipal(auth=MagicMock(), workspace=mock_workspace)
        qtbot.addWidget(janela)
        janela.croqui_data = {"id": "teste"}
        
        edit = QLineEdit(janela)
        
        with patch.object(QApplication, "focusWidget", return_value=edit), \
             patch.object(edit, "clearFocus") as mock_clear, \
             patch("builtins.open", MagicMock()), \
             patch("editor.legacy_views.area_principal.yaml.dump"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit, \
             patch.object(janela.pagina_imagens.editor, "salvar_alteracoes"):
             
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            janela.salvamento_finalizado.connect(loop.quit)
            janela.salvar_croqui()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            
        mock_clear.assert_called_once()

from pathlib import Path

def test_salvar_croqui_renomeia_pasta_se_id_alterado(qtbot, tmp_path):
    # Setup de diretório simulando um croqui
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    pasta_croqui = croquis_dir / "20260501_old_id"
    pasta_croqui.mkdir()
    (pasta_croqui / "database").mkdir()
    
    with open(pasta_croqui / "database" / "croqui.yaml", "w", encoding="utf-8") as f:
        f.write("id: old_id\n")

    # Mocks para não chamar métodos pesados/reais do UI e Worker
    with patch("editor.legacy_views.area_principal.QMessageBox.information"), \
         patch("editor.legacy_views.area_principal.NotificacaoToast"):
         
        nova_pasta = croquis_dir / "20260501_new_id"
        mock_workspace = MagicMock()
        mock_workspace.caminho_raiz = pasta_croqui
        mock_workspace.obter_caminho_database.return_value = pasta_croqui / "database"
        mock_workspace.processar_renomeacao_e_compilacao.return_value = (nova_pasta, [])
        
        # Instanciar a janela
        janela = JanelaPrincipal(workspace=mock_workspace)
        qtbot.addWidget(janela)
        
        # Simular a extração que retornaria o novo ID alterado na UI
        janela.croqui_model = MagicMock()
        janela.croqui_model.extrair_arquivos_e_serializar.return_value = {"id": "new_id"}
        
        # Simular editores de imagem e mapa
        janela.pagina_mapas.editor = MagicMock()
        janela.pagina_imagens.editor = MagicMock()
        janela.pagina_mapas.carregar_mapas = MagicMock()
        janela.pagina_imagens.carregar_imagens = MagicMock()
        janela.croqui_model.carregar_arquivos_externos = MagicMock()

        with patch("builtins.open", MagicMock()), \
             patch("editor.legacy_views.area_principal.yaml.dump"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit:
            
            # Executar a ação alvo
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            janela.salvamento_finalizado.connect(loop.quit)
            janela.salvar_croqui()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            
            # Se chamou error dialog, printar o erro
            if mock_crit.called:
                print("ERRO:", mock_crit.call_args)
            assert not mock_crit.called

        # Verificações
        mock_workspace.processar_renomeacao_e_compilacao.assert_called_once_with("new_id", "old_id", janela.storage)
        
        # Garantir que salvou as edições (para a pasta antes do reload)
        janela.pagina_imagens.editor.salvar_alteracoes.assert_called_once()
        
        # Garantir que os subeditores receberam a recarga do path com o novo diretório
        janela.pagina_mapas.carregar_mapas.assert_called_once_with(janela.croqui_model, janela.historico.obter_pilha(), pasta_croqui / "database")
        janela.pagina_imagens.carregar_imagens.assert_called_once_with(pasta_croqui / "database")


def test_pagina_mapas_recebe_model_e_controller(qtbot):
    from editor.legacy_views.area_principal import PaginaMapas
    from unittest.mock import MagicMock
    
    pagina = PaginaMapas()
    qtbot.addWidget(pagina)
    
    # Mocks
    model_mock = MagicMock()
    controller_mock = MagicMock()
    
    # Mock do editor interno para verificar se recebe os argumentos corretos
    pagina.editor = MagicMock()
    
    # Executa o metodo
    # Como carregar_mapas instancia um MapasController internamente, 
    # devemos mockar a classe MapasController do module editor.controllers.mapas_controller
    with patch("editor.controllers.mapas_controller.MapasController") as MockControllerClass:
        pagina.carregar_mapas(model_mock, controller_mock)
        
        # Verifica se o MapasController foi instanciado
        MockControllerClass.assert_called_once_with(model_mock, controller_mock)
        
        # E se o editor recebeu o controller criado
        assert pagina.editor.mapas_controller == MockControllerClass.return_value
        pagina.editor.configurar_lista_mapas.assert_called_once()


def test_salvar_croqui_repassa_erros_ao_controller(qtbot):
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import MagicMock, patch
    from pathlib import Path
    
    mock_workspace = MagicMock()
    mock_workspace.obter_caminho_database.return_value = Path("temp_croqui_db")
    mock_workspace.processar_renomeacao_e_compilacao.return_value = (Path("temp_croqui"), ["Erro no mapa"])
    
    janela = JanelaPrincipal(auth=MagicMock(), workspace=mock_workspace)
    qtbot.addWidget(janela)
    
    janela.croqui_data = {"id": "teste"}
    janela.croqui_model = MagicMock()
    janela.pagina_dados = MagicMock()
    janela.pagina_mapas = MagicMock()
    janela.pagina_imagens = MagicMock()
    
    with patch("builtins.open", MagicMock()), \
         patch("editor.legacy_views.area_principal.yaml.dump"), \
         patch.object(janela, "exibir_notificacao") as mock_notif, \
         patch.object(janela.compilacao_controller, "processar_resultado") as mock_processar:
         
        from PyQt6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        janela.salvamento_finalizado.connect(loop.quit)
        janela.salvar_croqui()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        
        # Verifica se os erros foram passados pro controlador
def test_salvar_croqui_exibe_notificacao(qtbot):
    # Mock do Gerenciador para não salvar arquivos reais
    with patch.object(GerenciadorCroquiExperimental, "compilar_croqui"), \
         patch("editor.legacy_views.area_principal.QMessageBox.information") as mock_info:
        
        mock_workspace = MagicMock()
        mock_workspace.obter_caminho_database.return_value = Path("temp_croqui")
        mock_workspace.caminho_raiz.name = "temp_croqui"
        mock_workspace.processar_renomeacao_e_compilacao.return_value = (Path("temp_croqui"), [])
        janela = JanelaPrincipal(workspace=mock_workspace)
        qtbot.addWidget(janela)
        janela.croqui_data = {"id": "teste"} # Simula croqui carregado
        janela.croqui_model = MagicMock()
        
        janela.pagina_dados = MagicMock()
        janela.pagina_mapas = MagicMock()
        janela.pagina_imagens = MagicMock()
        
        # Mock do open para não tentar escrever no disco
        with patch("builtins.open", MagicMock()), \
             patch("editor.legacy_views.area_principal.yaml.dump"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit, \
             patch.object(janela, "exibir_notificacao") as mock_notif:
            
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            janela.salvamento_finalizado.connect(loop.quit)
            janela.salvar_croqui()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            
            # Verifica que QMessageBox NÃO foi chamado
            mock_info.assert_not_called()
            if mock_crit.called:
                print("ERRO NO SALVAR:", mock_crit.call_args)
            assert not mock_crit.called
            # Verifica que a notificação FOI chamada
            mock_notif.assert_called_once_with("Croqui salvo e compilado com sucesso!")

def test_janela_principal_tem_icone_configurado(qtbot):
    """Garante que a Janela Principal carrega o ícone de montanha."""
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    assert not janela.windowIcon().isNull()

def test_atalhos_teclado_desfazer_refazer(qtbot):
    from PyQt6.QtGui import QKeySequence
    from PyQt6.QtCore import Qt
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Verifica desfazer
    shortcuts_undo = janela.acao_desfazer.shortcuts()
    assert QKeySequence.StandardKey.Undo in shortcuts_undo, "Atalho padrão de Undo (Ctrl+Z) ausente"
    assert janela.acao_desfazer.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut, "Contexto do atalho deve ser global (ApplicationShortcut)"
    
    # Verifica refazer
    shortcuts_redo = janela.acao_refazer.shortcuts()
    assert QKeySequence.StandardKey.Redo in shortcuts_redo, "Atalho padrão de Redo (Ctrl+Y/Ctrl+Shift+Z) ausente"
    assert janela.acao_refazer.shortcutContext() == Qt.ShortcutContext.ApplicationShortcut, "Contexto do atalho deve ser global (ApplicationShortcut)"

def test_salvar_croqui_remove_foco_do_widget_ativo(qtbot):
    from PyQt6.QtWidgets import QLineEdit
    from PyQt6.QtWidgets import QApplication
    
    with patch.object(GerenciadorCroquiExperimental, "compilar_croqui"):
        mock_workspace = MagicMock()
        mock_workspace.obter_caminho_database.return_value = Path("temp_croqui_db")
        janela = JanelaPrincipal(auth=MagicMock(), workspace=mock_workspace)
        qtbot.addWidget(janela)
        janela.croqui_data = {"id": "teste"}
        
        edit = QLineEdit(janela)
        
        with patch.object(QApplication, "focusWidget", return_value=edit), \
             patch.object(edit, "clearFocus") as mock_clear, \
             patch("builtins.open", MagicMock()), \
             patch("editor.legacy_views.area_principal.yaml.dump"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit, \
             patch.object(janela.pagina_imagens.editor, "salvar_alteracoes"):
             
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            janela.salvamento_finalizado.connect(loop.quit)
            janela.salvar_croqui()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            
        mock_clear.assert_called_once()

from pathlib import Path

def test_salvar_croqui_renomeia_pasta_se_id_alterado(qtbot, tmp_path):
    # Setup de diretório simulando um croqui
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    pasta_croqui = croquis_dir / "20260501_old_id"
    pasta_croqui.mkdir()
    (pasta_croqui / "database").mkdir()
    
    with open(pasta_croqui / "database" / "croqui.yaml", "w", encoding="utf-8") as f:
        f.write("id: old_id\n")

    # Mocks para não chamar métodos pesados/reais do UI e Worker
    with patch("editor.legacy_views.area_principal.QMessageBox.information"), \
         patch("editor.legacy_views.area_principal.NotificacaoToast"):
         
        nova_pasta = croquis_dir / "20260501_new_id"
        mock_workspace = MagicMock()
        mock_workspace.caminho_raiz = pasta_croqui
        mock_workspace.obter_caminho_database.return_value = pasta_croqui / "database"
        mock_workspace.processar_renomeacao_e_compilacao.return_value = (nova_pasta, [])
        
        # Instanciar a janela
        janela = JanelaPrincipal(workspace=mock_workspace)
        qtbot.addWidget(janela)
        
        # Simular a extração que retornaria o novo ID alterado na UI
        janela.croqui_model = MagicMock()
        janela.croqui_model.extrair_arquivos_e_serializar.return_value = {"id": "new_id"}
        
        # Simular editores de imagem e mapa
        janela.pagina_mapas.editor = MagicMock()
        janela.pagina_imagens.editor = MagicMock()
        janela.pagina_mapas.carregar_mapas = MagicMock()
        janela.pagina_imagens.carregar_imagens = MagicMock()
        janela.croqui_model.carregar_arquivos_externos = MagicMock()

        with patch("builtins.open", MagicMock()), \
             patch("editor.legacy_views.area_principal.yaml.dump"), \
             patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit:
            
            # Executar a ação alvo
            from PyQt6.QtCore import QEventLoop, QTimer
            loop = QEventLoop()
            janela.salvamento_finalizado.connect(loop.quit)
            janela.salvar_croqui()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
            
            # Se chamou error dialog, printar o erro
            if mock_crit.called:
                print("ERRO:", mock_crit.call_args)
            assert not mock_crit.called

        # Verificações
        mock_workspace.processar_renomeacao_e_compilacao.assert_called_once_with("new_id", "old_id", janela.storage)
        
        # Garantir que salvou as edições (para a pasta antes do reload)
        janela.pagina_imagens.editor.salvar_alteracoes.assert_called_once()
        
        # Garantir que os subeditores receberam a recarga do path com o novo diretório
        janela.pagina_mapas.carregar_mapas.assert_called_once_with(janela.croqui_model, janela.historico.obter_pilha(), pasta_croqui / "database")
        janela.pagina_imagens.carregar_imagens.assert_called_once_with(pasta_croqui / "database")


def test_pagina_mapas_recebe_model_e_controller(qtbot):
    from editor.legacy_views.area_principal import PaginaMapas
    from unittest.mock import MagicMock
    
    pagina = PaginaMapas()
    qtbot.addWidget(pagina)
    
    # Mocks
    model_mock = MagicMock()
    controller_mock = MagicMock()
    
    # Mock do editor interno para verificar se recebe os argumentos corretos
    pagina.editor = MagicMock()
    
    # Executa o metodo
    # Como carregar_mapas instancia um MapasController internamente, 
    # devemos mockar a classe MapasController do module editor.controllers.mapas_controller
    with patch("editor.controllers.mapas_controller.MapasController") as MockControllerClass:
        pagina.carregar_mapas(model_mock, controller_mock)
        
        # Verifica se o MapasController foi instanciado
        MockControllerClass.assert_called_once_with(model_mock, controller_mock)
        
        # E se o editor recebeu o controller criado
        assert pagina.editor.mapas_controller == MockControllerClass.return_value
        pagina.editor.configurar_lista_mapas.assert_called_once()


def test_salvar_croqui_repassa_erros_ao_controller(qtbot):
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import MagicMock, patch
    from pathlib import Path
    
    mock_workspace = MagicMock()
    mock_workspace.obter_caminho_database.return_value = Path("temp_croqui_db")
    mock_workspace.processar_renomeacao_e_compilacao.return_value = (Path("temp_croqui"), ["Erro no mapa"])
    
    janela = JanelaPrincipal(auth=MagicMock(), workspace=mock_workspace)
    qtbot.addWidget(janela)
    
    janela.croqui_data = {"id": "teste"}
    janela.croqui_model = MagicMock()
    janela.pagina_dados = MagicMock()
    janela.pagina_mapas = MagicMock()
    janela.pagina_imagens = MagicMock()
    
    with patch("builtins.open", MagicMock()), \
         patch("editor.legacy_views.area_principal.yaml.dump"), \
         patch.object(janela, "exibir_notificacao") as mock_notif, \
         patch.object(janela.compilacao_controller, "processar_resultado") as mock_processar:
         
        from PyQt6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        janela.salvamento_finalizado.connect(loop.quit)
        janela.salvar_croqui()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        
        # Verifica se os erros foram passados pro controlador
        mock_processar.assert_called_once_with(["Erro no mapa"])
        
        # Verifica que a notificação toast NÃO foi chamada
        mock_notif.assert_not_called()

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_botao_abrir_habilitado_em_modo_normal(mock_carregar, qtbot):
    workspace_mock = MagicMock()
    workspace_mock.can_publish_pr.return_value = True
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    assert janela.acao_abrir.isEnabled()

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_botao_abrir_desabilitado_em_modo_local(mock_carregar, qtbot):
    workspace_mock = MagicMock()
    workspace_mock.can_publish_pr.return_value = False
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    assert not janela.acao_abrir.isEnabled()

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_atualizar_titulo_mantem_workspace_tag(mock_carregar, qtbot):
    workspace_mock = MagicMock()
    workspace_mock.obter_tag_titulo.return_value = "[Local Mode]"
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    janela.croqui_data = {"nome": "Croqui Teste"}
    janela.historico.obter_pilha().isClean = MagicMock(return_value=True)
    
    janela.atualizar_titulo()
    assert janela.windowTitle() == "Aresta Editor - [Local Mode] - Croqui Teste"
    janela.close()

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_atualizar_titulo_dirty_state(mock_carregar, qtbot):
    workspace_mock = MagicMock()
    workspace_mock.obter_tag_titulo.return_value = "[Local Mode]"
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    janela.croqui_data = {"nome": "Croqui Teste"}
    janela.historico.obter_pilha().isClean = MagicMock(return_value=False)
    
    janela.atualizar_titulo()
    assert janela.windowTitle() == "Aresta Editor - [Local Mode] - Croqui Teste *"
    
    # Restaura para limpo para não abrir prompt de confirmação ao fechar
    janela.historico.obter_pilha().isClean.return_value = True
    janela.close()

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_cancelar_fechamento_nao_deleta_undo_stack(mock_carregar, qtbot):
    from PyQt6.QtGui import QUndoCommand, QCloseEvent
    from PyQt6.QtWidgets import QMessageBox
    from unittest.mock import MagicMock
    
    workspace_mock = MagicMock()
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    # Suja o histórico para forçar a verificação no closeEvent
    cmd = QUndoCommand()
    janela.historico.obter_pilha().push(cmd)
    
    # Chama o closeEvent simulando o usuário clicando em "Cancel" no alerta
    with patch("editor.legacy_views.area_principal.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel):
        event = MagicMock(spec=QCloseEvent)
        janela.closeEvent(event)
        
        event.ignore.assert_called_once()
        
    # Agora testa se o QUndoStack ainda está vivo e não explode com RuntimeError
    try:
        janela.historico.obter_pilha().isClean()
    except RuntimeError:
        import pytest
        pytest.fail("O QUndoStack foi indevidamente deletado após cancelar o fechamento!")
        
    # Limpa o estado e fecha a janela corretamente
    janela.historico.limpar()
    janela.close()
from unittest.mock import patch

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_area_principal_regex_mapas_gerais(mock_carregar, qtbot):
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import MagicMock
    
    workspace_mock = MagicMock()
    workspace_mock.can_publish_pr.return_value = True
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    janela.pagina_mapas = MagicMock()
    janela.pagina_mapas.editor = MagicMock()
    
    janela._on_foco_requisitado("page:mapas/expando:picos/item:0/mapas_gerais/conteudo/mapas/expando:mapas/item:0")
    
    # It should call: self.pagina_mapas.editor.selecionar_mapa_por_indices(p_idx, sg_idx, m_idx, s_idx)
    # But since it's mapas gerais, p_idx=0, m_idx=0, what about sg_idx and s_idx?
    # Wait, the code sets sg_idx=-1 and s_idx=-1.
    janela.pagina_mapas.editor.selecionar_mapa_por_indices.assert_called_with(0, -1, 0, -1)
    
    janela.close()

def test_close_event_enquanto_salva_marca_para_fechar(qtbot):
    """[TDD] Verifica se tentar fechar a janela durante o salvamento marca _fechar_apos_salvar."""
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import patch
    from PyQt6.QtGui import QCloseEvent

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Simula salvamento em andamento
    janela._salvando = True
    
    with patch.object(janela, "_mostrar_modal_fechamento") as mock_modal:
        event = QCloseEvent()
        janela.closeEvent(event)
        
        assert not event.isAccepted(), "O evento de fechamento deveria ser ignorado (adiado)."
        assert getattr(janela, "_fechar_apos_salvar", False) is True, "A janela não foi marcada para fechar após o término do salvamento."
        assert mock_modal.called, "O modal de 'Finalizando salvamento...' deveria ter sido exibido."
