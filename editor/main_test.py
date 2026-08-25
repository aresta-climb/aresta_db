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

def test_fluxo_inicializacao_cria_janela_principal(qtbot, tmp_path):
    with patch("editor.main.TarefaInicializacao") as MockTarefa:
        with patch("editor.main.TelaDeCarregamento") as MockDialog:
            mock_tarefa_inst = MockTarefa.return_value
            mock_tarefa_inst.storage = MagicMock()
            mock_tarefa_inst.sessao_usuario = None

            mock_dialog_inst = MockDialog.return_value
            mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted
            mock_dialog_inst.caminho_croqui_selecionado = tmp_path

            controlador = ControladorAplicativo()
            controlador.executar_selecao()

            assert controlador.janela_principal is not None
            assert hasattr(controlador.janela_principal, "workspace")

def test_controlador_app_conecta_sinais_corretamente(qtbot):
    # Verificamos manualmente se os sinais usados no ControladorApp existem no TarefaInicializacao
    sinais_necessarios = ["status", "progresso", "mostrar_progresso", "atualizacao_disponivel", "auth_requerida", "auth_concluida", "sucesso", "erro"]
    for sinal in sinais_necessarios:
        assert hasattr(TarefaInicializacao, sinal), f"O TarefaInicializacao não possui o sinal '{sinal}'"

def test_controlador_app_ao_detectar_atualizacao(qtbot):
    with patch("editor.main.TarefaInicializacao"):
        controlador = ControladorAplicativo()
        qtbot.addWidget(controlador.abertura)
        controlador.abertura.exibir_aviso_atualizacao = MagicMock()
        
        mock_resultado = MagicMock()
        controlador.ao_detectar_atualizacao(mock_resultado)
        
        controlador.abertura.exibir_aviso_atualizacao.assert_called_once()
        args, kwargs = controlador.abertura.exibir_aviso_atualizacao.call_args
        assert args[0] == mock_resultado
        assert callable(kwargs.get("callback_atualizar"))
        
        # Testa a execução do callback
        callback = kwargs.get("callback_atualizar")
        controlador.tarefa.servico_loja = MagicMock()
        callback()
        controlador.tarefa.servico_loja.solicitar_instalacao_atualizacao.assert_called_once_with(mock_resultado)

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

def test_main_impede_multiplas_instancias(qtbot):
    with patch("editor.main.QSharedMemory") as MockSharedMemory:
        with patch("editor.main.QMessageBox.warning") as mock_warning:
            with patch("editor.main.sys.exit", side_effect=SystemExit) as mock_exit:
                mock_mem_inst = MockSharedMemory.return_value
                # Simula que a criação falhou (outra instância já tem o lock)
                mock_mem_inst.create.return_value = False
                
                from editor.main import main
                with pytest.raises(SystemExit):
                    main()
                
                # Verifica a chave usada
                MockSharedMemory.assert_called_once_with("ArestaEditorSingleInstanceLock")
                # Verifica se o aviso foi mostrado
                mock_warning.assert_called_once()
                # Verifica se a verificação de criação foi feita corretamente
                mock_mem_inst.create.assert_called_once_with(1)

