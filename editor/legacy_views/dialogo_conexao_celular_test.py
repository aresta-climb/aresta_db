# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QApplication
from editor.legacy_views.dialogo_conexao_celular import DialogoConexaoCelular
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtGui import QGuiApplication
from unittest.mock import MagicMock
from editor.legacy_views.dialogo_conexao_celular import DialogoConexaoCelular


class ServidorMock(QObject):
    dispositivo_conectado = Signal()

    def __init__(self):
        super().__init__()
        self.porta = 8080
        self.codigo_sessao = "k9x2p83a"
        self.obter_ip_local = MagicMock(return_value="192.168.1.5")
        self.obter_url_previa_canonica = MagicMock(return_value="https://previa.arestaclimb.com/k9x2p83a")
        self.gerar_qr_code = MagicMock(return_value=b"fake_png_data")


@pytest.fixture
def dialogo(qtbot):
    servidor = ServidorMock()
    dialogo = DialogoConexaoCelular(servidor)
    qtbot.addWidget(dialogo)
    return dialogo


def test_deve_exibir_endereco_codigo_e_qr_code_carregados(qtbot, dialogo):
    """Aguarda a tarefa de background emitir a URL canônica, código formatado e QR Code."""
    qtbot.wait_until(
        lambda: dialogo.label_endereco.text() == "https://previa.arestaclimb.com/k9x2p83a",
        timeout=2000,
    )
    assert dialogo.label_codigo.text() == "k9x2-p83a"
    assert dialogo.label_qr.pixmap() is not None


def test_deve_mudar_status_quando_conectado(qtbot, dialogo):
    """Muda o rótulo de status quando o sinal de conexão for disparado."""
    qtbot.wait_until(lambda: not dialogo.label_endereco.text().startswith("Aguardando"), timeout=2000)
    
    dialogo.servidor.dispositivo_conectado.emit()
    assert dialogo.label_status.text() == "Celular Conectado!"


def test_deve_copiar_url_para_clipboard(qtbot, dialogo):
    """Copia a URL canônica para o clipboard do sistema."""
    qtbot.wait_until(lambda: not dialogo.label_endereco.text().startswith("Aguardando"), timeout=2000)
    url = dialogo.label_endereco.text()
    
    qtbot.mouseClick(dialogo.btn_copiar, Qt.MouseButton.LeftButton)
    
    cb = QGuiApplication.clipboard()
    assert cb.text() == url


def test_deve_emitir_sinal_ao_clicar_encerrar(qtbot, dialogo):
    """Emite solicitar_encerrar ao clicar no botão encerrar."""
    with qtbot.wait_signal(dialogo.solicitar_encerrar):
        qtbot.mouseClick(dialogo.btn_encerrar, Qt.MouseButton.LeftButton)
