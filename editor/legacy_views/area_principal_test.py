# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QMainWindow, QToolBar, QStackedWidget, QWidget, QDialog
from PySide6.QtCore import Qt
from editor.legacy_views.area_principal import JanelaPrincipal, PaginaDados, PaginaImagens, PaginaMapas, PaginaHistorico
from PySide6.QtGui import QIcon
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
    assert "Enviar proposta de mudança no croqui" in textos_acoes

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



def test_janela_principal_nao_gera_avisos_de_fonte_qt(qtbot):
    """Verifica se a inicialização da janela não dispara avisos de QFont no terminal."""
    avisos = []
    
    def message_handler(mode, context, message):
        # Captura avisos específicos de fonte
        if ("QFont" in message or "PointSize" in message) and "Cannot find font directory" not in message:
            avisos.append(message)
            
    from PySide6.QtCore import qInstallMessageHandler
    
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
            
            from PySide6.QtCore import QEventLoop, QTimer
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
            
            from PySide6.QtCore import QTimer
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
    from PySide6.QtGui import QKeySequence
    from PySide6.QtCore import Qt
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
    from PySide6.QtWidgets import QLineEdit
    from PySide6.QtWidgets import QApplication
    
    with patch.object(GerenciadorCroquiExperimental, "compilar_croqui"):
        mock_workspace = MagicMock()
        mock_workspace.obter_caminho_database.return_value = Path("temp_croqui_db")
        mock_workspace.processar_renomeacao_e_compilacao.return_value = (Path("temp_croqui_db"), [])
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
             
            from PySide6.QtCore import QEventLoop, QTimer
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
            from PySide6.QtCore import QEventLoop, QTimer
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
         
        from PySide6.QtCore import QEventLoop, QTimer
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
            
            from PySide6.QtCore import QEventLoop, QTimer
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
    from PySide6.QtGui import QKeySequence
    from PySide6.QtCore import Qt
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
    from PySide6.QtWidgets import QLineEdit
    from PySide6.QtWidgets import QApplication
    
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
             
            from PySide6.QtCore import QEventLoop, QTimer
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
            from PySide6.QtCore import QEventLoop, QTimer
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
        janela.pagina_mapas.carregar_mapas.assert_called_once_with(janela.croqui_model, janela.historico, pasta_croqui / "database")
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
         
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        janela.salvamento_finalizado.connect(loop.quit)
        janela.salvar_croqui()
        QTimer.singleShot(5000, loop.quit)
        loop.exec()
        
        # Verifica se os erros foram passados pro controlador
        mock_processar.assert_called_once_with(["Erro no mapa"])
        
        # Verifica que a notificação toast foi chamada informando avisos
        mock_notif.assert_called_once_with("Croqui salvo com avisos de compilação.")

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
    assert "Editor Aresta" in janela.windowTitle()
    assert "[Local Mode]" in janela.windowTitle()
    assert "Croqui Teste" in janela.windowTitle()
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
    assert "Editor Aresta" in janela.windowTitle()
    assert "[Local Mode]" in janela.windowTitle()
    assert "Croqui Teste *" in janela.windowTitle()
    
    # Restaura para limpo para não abrir prompt de confirmação ao fechar
    janela.historico.obter_pilha().isClean.return_value = True
    janela.close()

@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_cancelar_fechamento_nao_deleta_undo_stack(mock_carregar, qtbot):
    from PySide6.QtGui import QUndoCommand, QCloseEvent
    from PySide6.QtWidgets import QMessageBox
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
    from PySide6.QtGui import QCloseEvent

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Simula salvamento em andamento
    janela._salvando = True
    
    with patch.object(janela, "_mostrar_modal_espera") as mock_modal:
        event = QCloseEvent()
        janela.closeEvent(event)
        
        assert not event.isAccepted(), "O evento de fechamento deveria ser ignorado (adiado)."
        assert getattr(janela, "_fechar_apos_salvar", False) is True, "A janela não foi marcada para fechar após o término do salvamento."
        assert mock_modal.called, "O modal de 'Finalizando salvamento...' deveria ter sido exibido."
        
@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_publicar_croqui_instancia_publish_controller_corretamente(mock_carregar, qtbot):
    """Garante que o PublishController é instanciado corretamente evitando TypeErrors."""
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import patch, MagicMock

    workspace_mock = MagicMock()
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    janela.auth = MagicMock()
    janela.storage = MagicMock()

    with patch("editor.controllers.publish_controller.PublishController") as mock_publish_controller_class:
        # Execução
        janela.publicar_croqui()
        
        # Validação
        mock_publish_controller_class.assert_called_once_with(
            workspace=workspace_mock,
            auth=janela.auth,
            historico=janela.historico,
            storage=janela.storage,
            parent=janela
        )
        
        mock_publish_controller_class.return_value.iniciar_publicacao.assert_called_once()
        
    # Limpa estado e fecha
    janela.historico.limpar()
    janela.close()

@patch("editor.legacy_views.area_principal.QCoreApplication.applicationVersion", return_value="1.2.3-test")
@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_atualizar_titulo_mostra_versao_do_app_seguro(mock_carregar, mock_version, qtbot):
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import MagicMock
    
    workspace_mock = MagicMock()
    workspace_mock.obter_tag_titulo.return_value = None
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    janela.croqui_data = {"nome": "Meu Croqui"}
    janela.historico.obter_pilha().isClean = MagicMock(return_value=True)
    
    janela.atualizar_titulo()
    assert janela.windowTitle() == "Editor Aresta v1.2.3-test - Meu Croqui"
    janela.close()
@patch("editor.legacy_views.area_principal.QCoreApplication.applicationVersion", return_value="1.2.3-test")
@patch("editor.legacy_views.area_principal.JanelaPrincipal.carregar_croqui")
def test_atualizar_titulo_mostra_versao_do_app(mock_carregar, mock_version, qtbot):
    from editor.legacy_views.area_principal import JanelaPrincipal
    from unittest.mock import MagicMock
    
    workspace_mock = MagicMock()
    workspace_mock.obter_tag_titulo.return_value = None
    
    janela = JanelaPrincipal(workspace=workspace_mock)
    qtbot.addWidget(janela)
    
    janela.croqui_data = {"nome": "Meu Croqui"}
    janela.historico.obter_pilha().isClean = MagicMock(return_value=True)
    
    janela.atualizar_titulo()
    assert janela.windowTitle() == "Editor Aresta v1.2.3-test - Meu Croqui"


def test_ao_clicar_abrir_novo_sem_modificacoes_fecha_janela_e_emite_sinal(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    janela.solicitar_abrir_novo = MagicMock()
    with patch.object(janela, "close", wraps=janela.close) as mock_close:
        janela._on_abrir_novo_clicado()
        janela.solicitar_abrir_novo.emit.assert_called_once()
        mock_close.assert_called_once()


def test_ao_clicar_abrir_novo_com_modificacoes_salva_fecha_janela_e_emite_sinal(qtbot):
    from PySide6.QtWidgets import QMessageBox
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    janela.historico.obter_pilha().isClean = MagicMock(return_value=False)
    janela.solicitar_abrir_novo = MagicMock()
    
    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Save):
        with patch.object(janela, "salvar_croqui") as mock_salvar:
            with patch.object(janela, "close", wraps=janela.close) as mock_close:
                janela._on_abrir_novo_clicado()
                mock_salvar.assert_called_once()
                # Simula o callback de sucesso de salvamento
                assert callable(janela._callback_sucesso_salvar)
                janela._callback_sucesso_salvar()
                janela.solicitar_abrir_novo.emit.assert_called_once()
                mock_close.assert_called_once()


def test_ao_clicar_abrir_novo_com_modificacoes_descarta_fecha_janela_e_emite_sinal(qtbot):
    from PySide6.QtWidgets import QMessageBox
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    janela.historico.obter_pilha().isClean = MagicMock(return_value=False)
    janela.solicitar_abrir_novo = MagicMock()
    
    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Discard):
        with patch.object(janela, "close", wraps=janela.close) as mock_close:
            janela._on_abrir_novo_clicado()
            janela.solicitar_abrir_novo.emit.assert_called_once()
            mock_close.assert_called_once()


def test_ao_clicar_abrir_novo_com_modificacoes_cancela_nao_fecha_janela(qtbot):
    from PySide6.QtWidgets import QMessageBox
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    janela.historico.obter_pilha().isClean = MagicMock(return_value=False)
    janela.solicitar_abrir_novo = MagicMock()
    
    with patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Cancel):
        with patch.object(janela, "close", wraps=janela.close) as mock_close:
            janela._on_abrir_novo_clicado()
            janela.solicitar_abrir_novo.emit.assert_not_called()
            mock_close.assert_not_called()
            
    janela._forcar_fechamento = True
    janela.close()


def test_edicao_na_janela_principal_grava_diario_e_salva_consolida(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    pasta_croqui = tmp_path / "croqui_teste"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    (pasta_db / "croqui.yaml").write_text("id: teste\nnome: Croqui Original\n", encoding="utf-8")

    ws = ExperimentalWorkspace(pasta_croqui)
    janela = JanelaPrincipal(workspace=ws)
    qtbot.addWidget(janela)

    diario = ws.obter_diario()
    assert diario is not None
    assert not diario.tem_alteracoes_pendentes()

    # Faz uma alteração usando o controller da janela
    proxy = janela.croqui_model.obter_croqui_readonly()
    janela.croqui_controller.alterar_primitivo(proxy, "nome", "Croqui Original", "Croqui Alterado")

    # Verifica que gravou no disco em diario_pendente.bin
    assert diario.tem_alteracoes_pendentes()
    pendentes = diario.ler_diario_pendente()
    assert len(pendentes) == 1
    assert pendentes[0]["valor_novo"] == "Croqui Alterado"

    # Simula salvamento
    with patch("editor.core.croqui_experimental.GerenciadorCroquiExperimental") as mock_cls, \
         patch("editor.legacy_views.area_principal.QMessageBox.critical") as mock_crit, \
         patch("editor.legacy_views.area_principal.NotificacaoToast"):
        mock_gerenciador = mock_cls.return_value
        mock_gerenciador.compilar_croqui.return_value = None

        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        janela.salvamento_finalizado.connect(loop.quit)
        janela.salvar_croqui()
        QTimer.singleShot(3000, loop.quit)
        loop.exec()

        assert not mock_crit.called

    # Após salvar, pendente deve estar limpo e consolidado no salvo
    assert not diario.tem_alteracoes_pendentes()
    salvos = diario.ler_diario_salvo()
    assert len(salvos) == 1
    assert salvos[0]["valor_novo"] == "Croqui Alterado"

    janela._forcar_fechamento = True
    janela.close()


def test_recuperacao_de_crash_ao_reabrir_croqui_com_pendencias(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    from editor.core.diario import GerenciadorDiario
    pasta_croqui = tmp_path / "croqui_crash"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    (pasta_db / "croqui.yaml").write_text("id: teste_crash\nnome: Nome Original\n", encoding="utf-8")

    # Simula gravação prévia no diário pendente (como se tivesse crashado)
    diario = GerenciadorDiario(pasta_croqui)
    diario.gravar_comando_pendente({
        "classe": "CmdAlterarPrimitivo",
        "caminho_msg": "node:root",
        "campo_nome": "nome",
        "valor_antigo": "Nome Original",
        "valor_novo": "Nome Recuperado do Crash",
        "context_path": None
    })
    assert diario.tem_alteracoes_pendentes()

    ws = ExperimentalWorkspace(pasta_croqui)

    # Ao abrir, usuário aceita recuperar
    with patch.object(JanelaPrincipal, "_perguntar_recuperacao_sessao", return_value=True):
        janela = JanelaPrincipal(workspace=ws)
        qtbot.addWidget(janela)

        # Verifica se o modelo foi recuperado
        proxy = janela.croqui_model.obter_croqui_readonly()
        assert proxy.nome == "Nome Recuperado do Crash"

        # Verifica se a pilha de Undo funciona
        assert janela.historico.obter_pilha().count() == 1
        janela.historico.desfazer()
        assert proxy.nome == "Nome Original"

        janela._forcar_fechamento = True
        janela.close()


def test_reabrir_croqui_com_diario_salvo_habilita_undo_e_preserva_historico(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    from editor.core.diario import GerenciadorDiario
    pasta_croqui = tmp_path / "croqui_salvo"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    # O YAML salvo reflete o estado pós-edição
    (pasta_db / "croqui.yaml").write_text("id: teste_salvo\nnome: Nome Pos Salvamento\n", encoding="utf-8")

    # diario_salvo.bin contém o comando que gerou essa modificação
    diario = GerenciadorDiario(pasta_croqui)
    diario.gravar_comando_pendente({
        "classe": "CmdAlterarPrimitivo",
        "caminho_msg": "",
        "campo_nome": "nome",
        "valor_antigo": "Nome Base Original",
        "valor_novo": "Nome Pos Salvamento",
        "context_path": None
    })
    diario.consolidar_salvamento()
    assert not diario.tem_alteracoes_pendentes()
    assert len(diario.ler_diario_salvo()) == 1

    ws = ExperimentalWorkspace(pasta_croqui)
    janela = JanelaPrincipal(workspace=ws)
    qtbot.addWidget(janela)

    # Ao abrir, o modelo deve estar com o valor salvo
    proxy = janela.croqui_model.obter_croqui_readonly()
    assert proxy.nome == "Nome Pos Salvamento"

    # A pilha de Undo DEVE estar populada e permitir desfazer!
    assert janela.historico.obter_pilha().count() == 1
    assert janela.historico.obter_pilha().canUndo()
    assert janela.historico.obter_pilha().isClean()

    # Executa Desfazer
    janela.historico.desfazer()
    assert proxy.nome == "Nome Base Original"
    assert not janela.historico.obter_pilha().isClean()

    # Executa Refazer
    janela.historico.refazer()
    assert proxy.nome == "Nome Pos Salvamento"
    assert janela.historico.obter_pilha().isClean()

    janela._forcar_fechamento = True
    janela.close()


def test_recuperacao_de_crash_com_diario_salvo_e_pendente_permite_undo_imediato_de_ambos(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    from editor.core.diario import GerenciadorDiario
    pasta_croqui = tmp_path / "croqui_misto"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    # O YAML salvo reflete o estado pós-salvamento anterior
    (pasta_db / "croqui.yaml").write_text("id: teste_misto\nnome: Nome Salvo\n", encoding="utf-8")

    diario = GerenciadorDiario(pasta_croqui)
    # 1. Comando que foi consolidado no passado
    diario.gravar_comando_pendente({
        "classe": "CmdAlterarPrimitivo",
        "caminho_msg": "",
        "campo_nome": "nome",
        "valor_antigo": "Nome Base Original",
        "valor_novo": "Nome Salvo",
        "context_path": None
    })
    diario.consolidar_salvamento()

    # 2. Comando que estava pendente quando ocorreu o crash
    diario.gravar_comando_pendente({
        "classe": "CmdAlterarPrimitivo",
        "caminho_msg": "",
        "campo_nome": "nome",
        "valor_antigo": "Nome Salvo",
        "valor_novo": "Nome Pendente Final",
        "context_path": None
    })

    assert diario.tem_alteracoes_pendentes()
    assert len(diario.ler_diario_salvo()) == 1
    assert len(diario.ler_diario_pendente()) == 1

    ws = ExperimentalWorkspace(pasta_croqui)

    # Ao abrir, o usuário aceita recuperar a sessão do crash
    with patch.object(JanelaPrincipal, "_perguntar_recuperacao_sessao", return_value=True):
        janela = JanelaPrincipal(workspace=ws)
        qtbot.addWidget(janela)

        # O modelo deve refletir a mudança pendente recuperada
        proxy = janela.croqui_model.obter_croqui_readonly()
        assert proxy.nome == "Nome Pendente Final"

        # A pilha contém ambos os passos (salvo e pendente)
        assert janela.historico.obter_pilha().count() == 2
        assert janela.historico.obter_pilha().canUndo()

        # 1º Undo: Desfaz imediatamente a alteração pendente de volta para o estado salvo
        janela.historico.desfazer()
        assert proxy.nome == "Nome Salvo"

        # 2º Undo: Desfaz o histórico salvo anterior de volta para a base original
        janela.historico.desfazer()
        assert proxy.nome == "Nome Base Original"

        # 1º Redo: Refaz para o estado salvo
        janela.historico.refazer()
        assert proxy.nome == "Nome Salvo"

        # 2º Redo: Refaz para a alteração pendente
        janela.historico.refazer()
        assert proxy.nome == "Nome Pendente Final"

        janela._forcar_fechamento = True
        janela.close()


def test_fechar_croqui_sem_salvar_descarta_diario_pendente(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    from editor.core.diario import GerenciadorDiario
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtGui import QCloseEvent

    pasta_croqui = tmp_path / "croqui_fechar_descarte"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    (pasta_db / "croqui.yaml").write_text("id: teste_fechar\nnome: Original\n", encoding="utf-8")

    ws = ExperimentalWorkspace(pasta_croqui)
    janela = JanelaPrincipal(workspace=ws)
    qtbot.addWidget(janela)

    # Realiza uma alteração pendente
    janela.croqui_controller.alterar_primitivo(
        janela.croqui_model.obter_croqui_readonly(), "nome", "Original", "Modificado", pode_mesclar=True
    )
    diario = ws.obter_diario()
    assert diario.tem_alteracoes_pendentes()

    # Simula o usuário fechando a janela e clicando em "Descartar" no diálogo
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
        close_event = QCloseEvent()
        janela.closeEvent(close_event)
        assert close_event.isAccepted()

    # O diário pendente deve ter sido limpo!
    assert not diario.tem_alteracoes_pendentes()
    janela._forcar_fechamento = True
    janela.close()


def test_abrir_novo_sem_salvar_descarta_diario_pendente(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    from editor.core.diario import GerenciadorDiario
    from PySide6.QtWidgets import QMessageBox

    pasta_croqui = tmp_path / "croqui_voltar_descarte"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    (pasta_db / "croqui.yaml").write_text("id: teste_voltar\nnome: Original\n", encoding="utf-8")

    ws = ExperimentalWorkspace(pasta_croqui)
    janela = JanelaPrincipal(workspace=ws)
    qtbot.addWidget(janela)

    # Realiza uma alteração pendente
    janela.croqui_controller.alterar_primitivo(
        janela.croqui_model.obter_croqui_readonly(), "nome", "Original", "Modificado", pode_mesclar=True
    )
    diario = ws.obter_diario()
    assert diario.tem_alteracoes_pendentes()

    # Simula o usuário clicando em "Voltar / Abrir Novo" e escolhendo "Descartar"
    with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
        janela._on_abrir_novo_clicado()

    # O diário pendente deve ter sido limpo!
    assert not diario.tem_alteracoes_pendentes()
    janela._forcar_fechamento = True
    janela.close()


def test_recuperacao_crash_exatas_3_acoes_com_undos_perfeitos(qtbot, tmp_path):
    from editor.core.workspace import ExperimentalWorkspace
    from editor.core.diario import GerenciadorDiario
    from aresta_api.proto.generated import croqui_pb2

    pasta_croqui = tmp_path / "croqui_3_acoes"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    (pasta_db / "croqui.yaml").write_text("id: teste_3_acoes\nnome: Croqui Original\n", encoding="utf-8")

    ws1 = ExperimentalWorkspace(pasta_croqui)
    janela1 = JanelaPrincipal(workspace=ws1)
    qtbot.addWidget(janela1)

    # 1. Ação 1: Adiciona um Pico
    pico = croqui_pb2.Pico(nome="Pico 1")
    janela1.croqui_controller.adicionar_repeated(janela1.croqui_model.obter_croqui_readonly(), "picos", 0, pico)

    # 2. Ação 2: Adiciona um Setor
    sg = croqui_pb2.SetorOuGrupo()
    sg.setor.conteudo.nome = "Setor 1"
    janela1.croqui_controller.adicionar_repeated(janela1.croqui_model.obter_croqui_readonly().picos[0], "setores_ou_grupos", 0, sg)

    # 3. Ação 3: Digita interativamente 7 caracteres no nome do setor
    for texto in ["S", "Se", "Set", "Seto", "Setor", "Setor ", "Setor Final"]:
        janela1.croqui_controller.alterar_primitivo(
            janela1.croqui_model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo,
            "nome",
            "Setor 1" if texto == "S" else "S",
            texto,
            pode_mesclar=True
        )

    # Verifica que a sessão ativa possui exatamente 3 comandos consolidados
    assert janela1.historico.obter_pilha().count() == 3
    diario1 = ws1.obter_diario()
    comandos_pendentes = diario1.ler_diario_pendente()
    assert len(comandos_pendentes) == 3

    # Simula crash abrupto (fechamento sem salvar, preservando o diário)
    janela1._forcar_fechamento = True
    janela1.close()

    # Reabre a aplicação
    ws2 = ExperimentalWorkspace(pasta_croqui)
    perguntas_acoes = []
    def mock_perguntar(total):
        perguntas_acoes.append(total)
        return True

    with patch.object(JanelaPrincipal, "_perguntar_recuperacao_sessao", side_effect=mock_perguntar):
        janela2 = JanelaPrincipal(workspace=ws2)
        qtbot.addWidget(janela2)

        # O diálogo de recuperação deve reportar EXATAMENTE 3 ações não salvas!
        assert perguntas_acoes == [3]

        # O modelo restaurado possui os 3 passos aplicados
        croqui_rec = janela2.croqui_model.obter_croqui_readonly()
        assert len(croqui_rec.picos) == 1
        assert len(croqui_rec.picos[0].setores_ou_grupos) == 1
        assert croqui_rec.picos[0].setores_ou_grupos[0].setor.conteudo.nome == "Setor Final"
        assert janela2.historico.obter_pilha().count() == 3

        # 1º Undo: Desfaz a Ação 3 (Setor volta a ter o nome 'Setor 1')
        janela2.historico.desfazer()
        croqui_rec = janela2.croqui_model.obter_croqui_readonly()
        assert croqui_rec.picos[0].setores_ou_grupos[0].setor.conteudo.nome == "Setor 1"

        # 2º Undo: Desfaz a Ação 2 (Remove o Setor adicionado)
        janela2.historico.desfazer()
        croqui_rec = janela2.croqui_model.obter_croqui_readonly()
        assert len(croqui_rec.picos[0].setores_ou_grupos) == 0

        # 3º Undo: Desfaz a Ação 1 (Remove o Pico adicionado)
        janela2.historico.desfazer()
        croqui_rec = janela2.croqui_model.obter_croqui_readonly()
        assert len(croqui_rec.picos) == 0
        assert not janela2.historico.obter_pilha().canUndo()

        janela2._forcar_fechamento = True
        janela2.close()


def test_recuperacao_crash_edicao_repeated_creditos_com_undo_visual_imediato(qtbot, tmp_path):
    from PySide6.QtWidgets import QLineEdit
    from PySide6.QtTest import QTest
    from editor.core.workspace import ExperimentalWorkspace

    pasta_croqui = tmp_path / "croqui_creditos"
    pasta_db = pasta_croqui / "database"
    pasta_db.mkdir(parents=True)
    (pasta_db / "croqui.yaml").write_text("id: teste_cred\nnome: Meu Croqui\ncreditos:\n  - Autor Original\n", encoding="utf-8")

    ws1 = ExperimentalWorkspace(pasta_croqui)
    janela1 = JanelaPrincipal(workspace=ws1)
    qtbot.addWidget(janela1)

    form1 = janela1.pagina_dados.editor_dados.form_padrao

    # Ação 1: Digita em 'nome'
    nome_le = [w for w in form1.findChildren(QLineEdit) if w.property("protobuf_field") == "nome"][0]
    QTest.keyClicks(nome_le, " Oficial")

    # Ação 2: Digita em 'descricao'
    desc_le = [w for w in form1.findChildren(QLineEdit) if w.property("protobuf_field") == "descricao"][0]
    QTest.keyClicks(desc_le, "Minha Descricao")

    # Ação 3: Digita no primeiro item de 'creditos'
    cred_le = [w for w in form1.findChildren(QLineEdit) if w.property("protobuf_field") == "creditos[0]"][0]
    QTest.keyClicks(cred_le, " Extra")

    assert nome_le.text() == "Meu Croqui Oficial"
    assert desc_le.text() == "Minha Descricao"
    assert cred_le.text() == "Autor Original Extra"
    assert janela1.historico.obter_pilha().count() == 3

    # Simula crash abrupto
    janela1._forcar_fechamento = True
    janela1.close()

    # Reabre com recuperação
    ws2 = ExperimentalWorkspace(pasta_croqui)
    with patch.object(JanelaPrincipal, "_perguntar_recuperacao_sessao", return_value=True):
        janela2 = JanelaPrincipal(workspace=ws2)
        qtbot.addWidget(janela2)

        form2 = janela2.pagina_dados.editor_dados.form_padrao
        nome_le2 = [w for w in form2.findChildren(QLineEdit) if w.property("protobuf_field") == "nome"][0]
        desc_le2 = [w for w in form2.findChildren(QLineEdit) if w.property("protobuf_field") == "descricao"][0]
        cred_le2 = [w for w in form2.findChildren(QLineEdit) if w.property("protobuf_field") == "creditos[0]"][0]

        assert nome_le2.text() == "Meu Croqui Oficial"
        assert desc_le2.text() == "Minha Descricao"
        assert cred_le2.text() == "Autor Original Extra"
        assert janela2.historico.obter_pilha().count() == 3

        # 1º Undo: Desfaz a Ação 3 (Crédito volta visualmente para 'Autor Original')
        janela2.historico.desfazer()
        assert cred_le2.text() == "Autor Original"
        assert desc_le2.text() == "Minha Descricao"
        assert nome_le2.text() == "Meu Croqui Oficial"

        # 2º Undo: Desfaz a Ação 2 (Descrição volta para vazia)
        janela2.historico.desfazer()
        assert desc_le2.text() == ""
        assert cred_le2.text() == "Autor Original"
        assert nome_le2.text() == "Meu Croqui Oficial"

        # 3º Undo: Desfaz a Ação 1 (Nome volta para 'Meu Croqui')
        janela2.historico.desfazer()
        assert nome_le2.text() == "Meu Croqui"
        assert desc_le2.text() == ""
        assert cred_le2.text() == "Autor Original"
        assert not janela2.historico.obter_pilha().canUndo()

        janela2._forcar_fechamento = True
        janela2.close()



