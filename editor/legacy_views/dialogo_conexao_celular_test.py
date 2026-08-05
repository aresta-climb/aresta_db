# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import pytest
from PyQt6.QtWidgets import QApplication
from editor.legacy_views.dialogo_conexao_celular import DialogoConexaoCelular
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QGuiApplication
from unittest.mock import MagicMock

class ServidorMock(QObject):
    dispositivo_conectado = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.porta = 8080
        self.obter_ip_local = MagicMock(return_value="192.168.1.5")
        self.gerar_qr_code = MagicMock(return_value=b"fake_png_data")

@pytest.fixture
def dialogo(qtbot):
    servidor = ServidorMock()
    # Usamos o QTimer para dar tempo  tarefa de background rodar no teste
    dialogo = DialogoConexaoCelular(servidor)
    qtbot.addWidget(dialogo)
    return dialogo

def test_deve_exibir_endereco_e_qr_code_carregados(qtbot, dialogo):
    # Aguarda a tarefa de background emitir o sinal de concluído
    qtbot.wait_until(lambda: dialogo.label_endereco.text() == "http://192.168.1.5:8080", timeout=2000)
    assert dialogo.label_qr.pixmap() is not None

def test_deve_mudar_status_quando_conectado(qtbot, dialogo):
    # Aguarda carga inicial
    qtbot.wait_until(lambda: dialogo.label_endereco.text() != "Aguardando IP...", timeout=2000)
    
    # Simula o sinal de conectado vindo do servidor
    dialogo.servidor.dispositivo_conectado.emit()
    
    # Verifica se a UI mudou para Conectado!
    assert dialogo.label_status.text() == "Conectado!"

def test_deve_copiar_url_para_clipboard(qtbot, dialogo):
    # Aguarda carga inicial
    qtbot.wait_until(lambda: dialogo.label_endereco.text() != "Aguardando IP...", timeout=2000)
    url = dialogo.label_endereco.text()
    
    # Clica no botão copiar
    qtbot.mouseClick(dialogo.btn_copiar, Qt.MouseButton.LeftButton)
    
    # Verifica clipboard
    cb = QGuiApplication.clipboard()
    assert cb.text() == url

def test_deve_emitir_sinal_ao_clicar_encerrar(qtbot, dialogo):
    with qtbot.wait_signal(dialogo.solicitar_encerrar):
        qtbot.mouseClick(dialogo.btn_encerrar, Qt.MouseButton.LeftButton)
