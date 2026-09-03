# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Guardião nativo para bloquear conexões externas com a internet durante a execução de testes.
Permite estritamente o tráfego de loopback local (127.0.0.1, localhost, ::1, 0.0.0.0).
"""

import socket
from typing import Any, Callable, Set

ENDERECOS_LOCAIS_PERMITIDOS: Set[str] = {
    "127.0.0.1",
    "localhost",
    "::1",
    "0.0.0.0",
}

_getaddrinfo_original: Callable[..., Any] | None = None
_connect_original: Callable[..., Any] | None = None
_bloqueio_ativo: bool = False


class AcessoInternetBloqueadoErro(RuntimeError):
    """Exceção lançada quando um teste tenta acessar a internet ou resolver DNS externo."""
    pass


def eh_endereco_local(host: str) -> bool:
    """
    Verifica se o host fornecido corresponde a um endereço de loopback ou local.
    """
    if not host or not isinstance(host, str):
        return True

    host_limpo = host.strip().lower()
    if host_limpo in ENDERECOS_LOCAIS_PERMITIDOS:
        return True

    if host_limpo.startswith("127."):
        return True

    return False


def bloquear_acesso_externo() -> None:
    """
    Ativa o bloqueio de rede interceptando socket.getaddrinfo e socket.socket.connect.
    É idempotente e preserva as funções originais para restauração posterior.
    """
    global _getaddrinfo_original, _connect_original, _bloqueio_ativo

    if _bloqueio_ativo:
        return

    _getaddrinfo_original = socket.getaddrinfo
    _connect_original = socket.socket.connect

    def getaddrinfo_interceptado(
        host: Any,
        port: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if host and isinstance(host, str) and not eh_endereco_local(host):
            raise AcessoInternetBloqueadoErro(
                f"Acesso externo à internet bloqueado durante execução de testes: "
                f"tentativa de resolução DNS para '{host}'."
            )
        assert _getaddrinfo_original is not None
        return _getaddrinfo_original(host, port, *args, **kwargs)

    def connect_interceptado(self: socket.socket, address: Any) -> Any:
        host: Any = address
        if isinstance(address, tuple) and len(address) > 0:
            host = address[0]

        if host and isinstance(host, str) and not eh_endereco_local(host):
            raise AcessoInternetBloqueadoErro(
                f"Acesso externo à internet bloqueado durante execução de testes: "
                f"tentativa de conexão para {address}."
            )
        assert _connect_original is not None
        return _connect_original(self, address)

    socket.getaddrinfo = getaddrinfo_interceptado
    socket.socket.connect = connect_interceptado
    _bloqueio_ativo = True


def restaurar_acesso_rede() -> None:
    """
    Restaura as funções originais de socket e resolução de DNS.
    """
    global _getaddrinfo_original, _connect_original, _bloqueio_ativo

    if not _bloqueio_ativo:
        return

    if _getaddrinfo_original is not None:
        socket.getaddrinfo = _getaddrinfo_original
        _getaddrinfo_original = None

    if _connect_original is not None:
        socket.socket.connect = _connect_original
        _connect_original = None

    _bloqueio_ativo = False
