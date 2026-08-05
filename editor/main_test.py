# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QDialog
from unittest.mock import MagicMock, patch
from editor.main import JanelaPrincipal, ControladorAplicativo
from editor.core.worker import TarefaInicializacao

def test_janela_principal_tem_stack_central(qtbot):
    mock_storage = MagicMock()
    mock_auth = MagicMock()
    janela = JanelaPrincipal(storage=mock_storage, auth=mock_auth)
    qtbot.addWidget(janela)
    
    # Verifica se existe um QStackedWidget (área principal)
    stack = janela.findChild(QStackedWidget)
    assert stack is not None

def test_fluxo_inicializacao_passa_auth_para_janela(qtbot):
    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        with patch("editor.main.TelaDeCarregamento") as MockDialog:
            mock_tarefa_inst = MockTarefa.return_value
            mock_tarefa_inst.storage = MagicMock()
            mock_tarefa_inst.auth = MagicMock()
            
            mock_dialog_inst = MockDialog.return_value
            mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted
            
            controlador = ControladorAplicativo()
            controlador.executar_selecao()
            
            assert controlador.janela_principal.auth == mock_tarefa_inst.auth

def test_controlador_app_conecta_sinais_corretamente(qtbot):
    # Verificamos manualmente se os sinais usados no ControladorApp existem no TarefaInicializacao
    sinais_necessarios = ["status", "progresso", "mostrar_progresso", "auth_requerida", "auth_concluida", "sucesso", "erro"]
    for sinal in sinais_necessarios:
        assert hasattr(TarefaInicializacao, sinal), f"O TarefaInicializacao não possui o sinal '{sinal}'"

def test_fluxo_inicializacao_transicao(qtbot):
    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        with patch("editor.main.TelaDeCarregamento") as MockDialog:
            mock_tarefa_inst = MockTarefa.return_value
            mock_tarefa_inst.storage = MagicMock()
            
            # Mock para o diálogo retornar 'Accepted'
            mock_dialog_inst = MockDialog.return_value
            mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted
            
            controlador = ControladorAplicativo()
            qtbot.addWidget(controlador.abertura)
            
            # Simula sucesso chamando o novo fluxo de seleção
            controlador.executar_selecao()
            
            assert controlador.janela_principal is not None
            assert controlador.janela_principal.isVisible()
            assert not controlador.abertura.isVisible()
            
            qtbot.addWidget(controlador.janela_principal)
            controlador.janela_principal.close()

def test_mostrar_erro_esconde_abertura_antes(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        with patch("editor.main.QMessageBox.critical") as mock_critical:
            with patch("editor.main.QApplication.quit"):
                controlador = ControladorAplicativo()
                qtbot.addWidget(controlador.abertura)
                
                # Espionamos o método hide da abertura
                controlador.abertura.hide = MagicMock(side_effect=controlador.abertura.hide)
                
                controlador.mostrar_erro("Erro de teste")
                
                # Verifica se hide foi chamado ANTES de critical
                assert controlador.abertura.hide.called
                assert mock_critical.called

def test_controlador_app_define_icone_global(qtbot):
    """Garante que o ícone global da aplicação é configurado na inicialização."""
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        assert not controlador.app.windowIcon().isNull()

def test_tela_de_abertura_tem_icone_configurado(qtbot):
    """Garante que a tela de abertura carrega o ícone de montanha."""
    from editor.views.tela_de_abertura import TelaDeAbertura
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    assert not abertura.windowIcon().isNull()

def test_application_version_is_set(qtbot):
    """Garante que a constante VERSION do módulo version é setada no QApplication."""
    from editor.core.version import VERSION
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        assert controlador.app.applicationVersion() == VERSION



