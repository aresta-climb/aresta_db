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
