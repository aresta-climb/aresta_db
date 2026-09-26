# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import uuid
import subprocess
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from editor.core.instancia_unica import (
    verificar_se_ja_em_execucao,
    iniciar_servidor_instancia_unica,
)


def test_verificar_se_ja_em_execucao_quando_nenhum_servidor_ativo(qtbot):
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    assert verificar_se_ja_em_execucao(nome_servidor, timeout_ms=50) is False


def test_verificar_se_ja_em_execucao_com_servidor_real_ativo(qtbot):
    """Testa que uma instância ativa real responde ao PING com PONG."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    
    server_code = f'''
from PySide6.QtCore import QCoreApplication
from editor.core.instancia_unica import iniciar_servidor_instancia_unica
import sys

app = QCoreApplication(sys.argv)
srv = iniciar_servidor_instancia_unica("{nome_servidor}")
print("SERVER_READY", flush=True)
sys.exit(app.exec())
'''
    proc = subprocess.Popen([sys.executable, "-c", server_code], stdout=subprocess.PIPE, text=True)
    try:
        linha = proc.stdout.readline()
        assert "SERVER_READY" in linha

        ja_executando = verificar_se_ja_em_execucao(nome_servidor, timeout_ms=1000)
        assert ja_executando is True
    finally:
        proc.terminate()
        proc.wait()
        QLocalServer.removeServer(nome_servidor)


def test_verificar_se_ja_em_execucao_recupera_de_servidor_zumbi(qtbot):
    """Testa que um servidor mudo/zumbi é detectado como não responsivo e a trava é limpa."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"

    server_code = f'''
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer
import sys

app = QCoreApplication(sys.argv)
srv = QLocalServer()
QLocalServer.removeServer("{nome_servidor}")
srv.listen("{nome_servidor}")
print("ZOMBIE_READY", flush=True)
sys.exit(app.exec())
'''
    proc = subprocess.Popen([sys.executable, "-c", server_code], stdout=subprocess.PIPE, text=True)
    try:
        linha = proc.stdout.readline()
        assert "ZOMBIE_READY" in linha

        # Não deve travar o editor; deve detectar como zumbi e retornar False
        ja_executando = verificar_se_ja_em_execucao(nome_servidor, timeout_ms=300)
        assert ja_executando is False
    finally:
        proc.terminate()
        proc.wait()
        QLocalServer.removeServer(nome_servidor)


def test_ativar_janela_existente_sem_janelas():
    """Verifica que ativar_janela_existente retorna False quando não há janelas visíveis."""
    from editor.core.instancia_unica import ativar_janela_existente
    from PySide6.QtWidgets import QApplication

    with patch.object(QApplication, "activeWindow", return_value=None):
        with patch.object(QApplication, "topLevelWidgets", return_value=[]):
            assert ativar_janela_existente() is False


def test_ativar_janela_existente_com_janela_visivel(qtbot):
    """Verifica que ativa janela visível encontrada em topLevelWidgets."""
    from editor.core.instancia_unica import ativar_janela_existente
    from PySide6.QtWidgets import QMainWindow, QApplication

    janela = QMainWindow()
    qtbot.addWidget(janela)
    janela.show()

    with patch.object(QApplication, "activeWindow", return_value=None):
        with patch("editor.core.integracao_windows.trazer_janela_para_frente", return_value=True) as mock_win32:
            resultado = ativar_janela_existente()
            assert resultado is True
            mock_win32.assert_called_once_with(int(janela.winId()))


def test_ativar_janela_existente_com_janela_minimizada(qtbot):
    """Verifica que restaura janela se estiver minimizada."""
    from editor.core.instancia_unica import ativar_janela_existente
    from PySide6.QtWidgets import QMainWindow, QApplication

    janela = QMainWindow()
    qtbot.addWidget(janela)
    janela.showMinimized()

    with patch.object(QApplication, "activeWindow", return_value=None):
        with patch("editor.core.integracao_windows.trazer_janela_para_frente", return_value=True):
            resultado = ativar_janela_existente()
            assert resultado is True
            assert not janela.isMinimized()


def test_ativar_janela_existente_com_active_window():
    """Verifica que prioriza QApplication.activeWindow() quando presente."""
    from editor.core.instancia_unica import ativar_janela_existente
    from PySide6.QtWidgets import QApplication

    mock_janela = MagicMock()
    mock_janela.isMinimized.return_value = False
    mock_janela.winId.return_value = 12345

    with patch.object(QApplication, "activeWindow", return_value=mock_janela):
        with patch("editor.core.integracao_windows.trazer_janela_para_frente", return_value=True) as mock_win32:
            assert ativar_janela_existente() is True
            mock_janela.raise_.assert_called_once()
            mock_janela.activateWindow.assert_called_once()
            mock_win32.assert_called_once_with(12345)


def test_ativar_janela_existente_ignora_excecao_win32():
    """Garante resiliência caso a integração Win32 lance exceção."""
    from editor.core.instancia_unica import ativar_janela_existente
    from PySide6.QtWidgets import QApplication

    mock_janela = MagicMock()
    mock_janela.isMinimized.return_value = False
    mock_janela.winId.return_value = 12345

    with patch.object(QApplication, "activeWindow", return_value=mock_janela):
        with patch("editor.core.integracao_windows.trazer_janela_para_frente", side_effect=RuntimeError("Erro win32")):
            assert ativar_janela_existente() is True


def test_servidor_responde_pong_e_chama_callback(qtbot):
    """Testa que servidor responde PONG e executa o callback de ativação ao receber PING."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    chamou_callback = False

    def callback():
        nonlocal chamou_callback
        chamou_callback = True

    srv = iniciar_servidor_instancia_unica(nome_servidor, callback_ativacao=callback)
    assert srv is not None
    try:
        cliente = QLocalSocket()
        cliente.connectToServer(nome_servidor)
        assert cliente.waitForConnected(500)

        cliente.write(b"PING\n")
        cliente.flush()
        qtbot.waitUntil(lambda: chamou_callback, timeout=1000)
        qtbot.waitUntil(lambda: cliente.bytesAvailable() > 0, timeout=1000)
        resposta = bytes(cliente.readAll().data())
        assert b"PONG" in resposta
        assert chamou_callback is True
        cliente.disconnectFromServer()
    finally:
        srv.close()
        QLocalServer.removeServer(nome_servidor)


def test_servidor_desconexao_de_cliente_limpa_lista(qtbot):
    """Testa que a lista de clientes ativos do servidor remove sockets desconectados."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    srv = iniciar_servidor_instancia_unica(nome_servidor)
    assert srv is not None
    try:
        cliente = QLocalSocket()
        cliente.connectToServer(nome_servidor)
        assert cliente.waitForConnected(500)
        qtbot.wait(50)
        clientes = getattr(srv, "_clientes_ativos")
        assert len(clientes) == 1

        cliente.disconnectFromServer()
        qtbot.wait(100)
        assert len(clientes) == 0
    finally:
        srv.close()
        QLocalServer.removeServer(nome_servidor)


def test_servidor_falha_ao_escutar():
    """Garante retorno None quando QLocalServer.listen falhar."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    with patch.object(QLocalServer, "listen", return_value=False):
        srv = iniciar_servidor_instancia_unica(nome_servidor)
        assert srv is None


def test_servidor_ao_conectar_sem_conexao_pendente():
    """Garante tratamento gracioso caso nextPendingConnection retorne None."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    srv = iniciar_servidor_instancia_unica(nome_servidor)
    assert srv is not None
    try:
        with patch.object(srv, "nextPendingConnection", return_value=None):
            srv.newConnection.emit()
    finally:
        srv.close()
        QLocalServer.removeServer(nome_servidor)


def test_servidor_recusa_pong_quando_sem_janela_e_fora_tolerancia():
    """
    Testa que servidor sem janela visível e após tempo de tolerância esgotado
    responde SEM_JANELA, fecha a si próprio e permite que verificar_se_ja_em_execucao retorne False.
    """
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"

    server_code = f'''
from PySide6.QtCore import QCoreApplication
from editor.core.instancia_unica import iniciar_servidor_instancia_unica
import sys

app = QCoreApplication(sys.argv)
srv = iniciar_servidor_instancia_unica("{nome_servidor}", tempo_tolerancia_inicializacao_s=0.0)
print("SERVER_READY", flush=True)
sys.exit(app.exec())
'''
    proc = subprocess.Popen([sys.executable, "-c", server_code], stdout=subprocess.PIPE, text=True)
    try:
        linha = proc.stdout.readline()
        assert "SERVER_READY" in linha

        ja_executando = verificar_se_ja_em_execucao(nome_servidor, timeout_ms=1000)
        assert ja_executando is False
    finally:
        proc.terminate()
        proc.wait()
        QLocalServer.removeServer(nome_servidor)


def test_servidor_responde_pong_com_ativar_janela_existente(qtbot):
    """Testa que servidor sem callback customizado invoca ativar_janela_existente e responde PONG."""
    from editor.core.instancia_unica import iniciar_servidor_instancia_unica

    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    with patch("editor.core.instancia_unica.ativar_janela_existente", return_value=True) as mock_ativar:
        srv = iniciar_servidor_instancia_unica(nome_servidor, callback_ativacao=None)
        assert srv is not None
        try:
            cliente = QLocalSocket()
            cliente.connectToServer(nome_servidor)
            assert cliente.waitForConnected(500)

            cliente.write(b"PING\n")
            cliente.flush()
            qtbot.waitUntil(lambda: mock_ativar.called, timeout=1000)
            qtbot.waitUntil(lambda: cliente.bytesAvailable() > 0, timeout=1000)
            resposta = bytes(cliente.readAll().data())
            assert b"PONG" in resposta
            cliente.disconnectFromServer()
        finally:
            srv.close()
            QLocalServer.removeServer(nome_servidor)


def test_servidor_rejeita_pong_em_processo_quando_sem_janela(qtbot):
    """Testa que servidor sem janela e fora de tolerância responde SEM_JANELA e fecha servidor."""
    from editor.core.instancia_unica import iniciar_servidor_instancia_unica
    from PySide6.QtWidgets import QApplication

    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    with patch("editor.core.instancia_unica.ativar_janela_existente", return_value=False):
        srv = iniciar_servidor_instancia_unica(
            nome_servidor,
            callback_ativacao=None,
            tempo_tolerancia_inicializacao_s=0.0
        )
        assert srv is not None
        try:
            cliente = QLocalSocket()
            cliente.connectToServer(nome_servidor)
            assert cliente.waitForConnected(500)

            cliente.write(b"PING\n")
            cliente.flush()
            qtbot.waitUntil(lambda: cliente.bytesAvailable() > 0, timeout=1000)
            resposta = bytes(cliente.readAll().data())
            assert b"SEM_JANELA" in resposta
            assert not srv.isListening()
            cliente.disconnectFromServer()
        finally:
            srv.close()
            QLocalServer.removeServer(nome_servidor)


def test_servidor_ao_conectar_com_bytes_ja_disponiveis():
    """Garante que bytes imediatamente disponíveis no momento da conexão sejam processados."""
    from editor.core.instancia_unica import iniciar_servidor_instancia_unica

    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    srv = iniciar_servidor_instancia_unica(nome_servidor)
    assert srv is not None
    try:
        mock_socket = MagicMock()
        mock_socket.bytesAvailable.return_value = 5
        mock_socket.readAll.return_value.data.return_value = b"PING\n"
        with patch.object(srv, "nextPendingConnection", return_value=mock_socket):
            srv.newConnection.emit()
            mock_socket.write.assert_called_with(b"PONG\n")
    finally:
        srv.close()
        QLocalServer.removeServer(nome_servidor)



