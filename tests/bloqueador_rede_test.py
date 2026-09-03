# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket
import pytest

from tests.bloqueador_rede import (
    AcessoInternetBloqueadoErro,
    eh_endereco_local,
    bloquear_acesso_externo,
    restaurar_acesso_rede,
)


def test_eh_endereco_local_identifica_loopback():
    assert eh_endereco_local("127.0.0.1") is True
    assert eh_endereco_local("127.0.0.2") is True
    assert eh_endereco_local("127.1.2.3") is True
    assert eh_endereco_local("localhost") is True
    assert eh_endereco_local("::1") is True
    assert eh_endereco_local("0.0.0.0") is True

    assert eh_endereco_local("google.com") is False
    assert eh_endereco_local("api.github.com") is False
    assert eh_endereco_local("8.8.8.8") is False
    assert eh_endereco_local("192.168.1.1") is False


def test_bloquear_acesso_externo_bloqueia_dns():
    bloquear_acesso_externo()
    try:
        with pytest.raises(AcessoInternetBloqueadoErro) as exc_info:
            socket.getaddrinfo("api.github.com", 443)
        assert "Acesso externo à internet bloqueado" in str(exc_info.value)
        assert "api.github.com" in str(exc_info.value)
    finally:
        restaurar_acesso_rede()


def test_bloquear_acesso_externo_permite_dns_local():
    bloquear_acesso_externo()
    try:
        # Loopback não deve disparar AcessoInternetBloqueadoErro
        info = socket.getaddrinfo("127.0.0.1", 80)
        assert len(info) > 0
    finally:
        restaurar_acesso_rede()


def test_bloquear_acesso_externo_bloqueia_socket_connect():
    bloquear_acesso_externo()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(AcessoInternetBloqueadoErro) as exc_info:
            sock.connect(("8.8.8.8", 80))
        assert "Acesso externo à internet bloqueado" in str(exc_info.value)
        assert "8.8.8.8" in str(exc_info.value)
        sock.close()
    finally:
        restaurar_acesso_rede()


def test_restaurar_acesso_rede_restaura_funcoes_originais():
    func_orig_dns = socket.getaddrinfo
    func_orig_conn = socket.socket.connect

    bloquear_acesso_externo()
    assert socket.getaddrinfo != func_orig_dns
    assert socket.socket.connect != func_orig_conn

    restaurar_acesso_rede()
    assert socket.getaddrinfo == func_orig_dns
    assert socket.socket.connect == func_orig_conn


def test_bloquear_acesso_externo_idempotente():
    func_orig_dns = socket.getaddrinfo
    func_orig_conn = socket.socket.connect

    bloquear_acesso_externo()
    bloquear_acesso_externo()  # Segunda chamada não deve encadear ou perder originais

    restaurar_acesso_rede()
    assert socket.getaddrinfo == func_orig_dns
    assert socket.socket.connect == func_orig_conn
