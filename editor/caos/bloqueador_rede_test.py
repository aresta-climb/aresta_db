# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from editor.caos.bloqueador_rede import (
    BloqueadorRedeCaos,
    ErroAcessoRedeProibidoEmTeste,
)


def test_bloqueia_conexoes_externas_connect_connect_ex_e_create_connection() -> None:
    with BloqueadorRedeCaos() as bloqueador:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s_udp:
            with pytest.raises(ErroAcessoRedeProibidoEmTeste, match="8.8.8.8"):
                s_udp.connect(("8.8.8.8", 80))

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_tcp:
            with pytest.raises(ErroAcessoRedeProibidoEmTeste, match="github.com"):
                s_tcp.connect_ex(("github.com", 443))

        with pytest.raises(ErroAcessoRedeProibidoEmTeste, match="previa.arestaclimb.com"):
            socket.create_connection(("previa.arestaclimb.com", 443), timeout=1.0)

        assert len(bloqueador.tentativas_bloqueadas) == 3


def test_permite_comunicacao_loopback_local_e_intercepta_open_url() -> None:
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]

    try:
        with BloqueadorRedeCaos() as bloqueador:
            with socket.create_connection(("127.0.0.1", porta), timeout=2.0) as cliente:
                conn, _ = servidor.accept()
                with conn:
                    cliente.sendall(b"ping")
                    assert conn.recv(4) == b"ping"

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cliente2:
                assert cliente2.connect_ex(("localhost", porta)) == 0
                conn2, _ = servidor.accept()
                conn2.close()

            assert (
                QDesktopServices.openUrl(QUrl("https://github.com/aresta-climb/aresta_db/pull/1"))
                is True
            )
            assert bloqueador.urls_abertas_interceptadas == [
                "https://github.com/aresta-climb/aresta_db/pull/1"
            ]
            assert bloqueador.tentativas_bloqueadas == []
    finally:
        servidor.close()
