# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtWidgets import QApplication
from editor.legacy_views.area_principal import JanelaPrincipal
from PyQt6.QtCore import QObject, pyqtSignal
from unittest.mock import MagicMock, patch
from pathlib import Path

# Classes fake que herdam de QObject para o Qt aceitar
class ServidorFake(QObject):
    dispositivo_conectado = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.iniciar = MagicMock()
        self.parar = MagicMock()
        self.obter_ip_local = MagicMock(return_value="192.168.1.5")
        self.gerar_qr_code = MagicMock(return_value=b"fake_png_data")
        self.porta = 8080
        self.conectado = False

class MonitorFake(QObject):
    inatividade_detectada = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.iniciar = MagicMock()
        self.parar = MagicMock()

class DialogoFake(QObject):
    solicitar_encerrar = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.exec = MagicMock(return_value=0)

@pytest.fixture
def janela(qtbot):
    janela = JanelaPrincipal()
    janela.workspace = MagicMock()
    janela.workspace.obter_pasta_servidor_celular.return_value = Path("fake_path")
    qtbot.addWidget(janela)
    return janela

def test_deve_iniciar_servidor_e_abrir_dialogo_ao_clicar_celular(qtbot, janela):
    with patch("editor.legacy_views.area_principal.ServidorCelular", side_effect=ServidorFake) as MockServidor, \
         patch("editor.legacy_views.area_principal.MonitorInatividade", side_effect=MonitorFake), \
         patch("editor.legacy_views.area_principal.DialogoConexaoCelular", side_effect=DialogoFake) as MockDialogo:
        
        janela.acao_celular.trigger()
        
        MockServidor.assert_called_once()
        janela.servidor_celular.iniciar.assert_called_once()
        
        MockDialogo.assert_called_once()
        janela.dialogo_celular.exec.assert_called_once()

def test_deve_parar_servidor_ao_encerrar_dialogo(qtbot, janela):
    with patch("editor.legacy_views.area_principal.ServidorCelular", side_effect=ServidorFake), \
         patch("editor.legacy_views.area_principal.MonitorInatividade", side_effect=MonitorFake), \
         patch("editor.legacy_views.area_principal.DialogoConexaoCelular", side_effect=DialogoFake):
        
        janela.acao_celular.trigger()
        
        servidor_antes = janela.servidor_celular
        janela.dialogo_celular.solicitar_encerrar.emit()
        
        servidor_antes.parar.assert_called_once()
        assert janela.servidor_celular is None

def test_deve_ativar_autosave_quando_celular_conectado(qtbot, janela):
    with patch("editor.legacy_views.area_principal.ServidorCelular", side_effect=ServidorFake), \
         patch("editor.legacy_views.area_principal.MonitorInatividade", side_effect=MonitorFake), \
         patch("editor.legacy_views.area_principal.DialogoConexaoCelular", side_effect=DialogoFake):
        
        # Mock do salvar_croqui ANTES da conexão do sinal
        with patch.object(janela, "salvar_croqui") as mock_salvar:
            janela.acao_celular.trigger()
            
            janela.monitor_inatividade.iniciar.assert_called_once()
            
            janela.monitor_inatividade.inatividade_detectada.emit()
            mock_salvar.assert_called_once()
