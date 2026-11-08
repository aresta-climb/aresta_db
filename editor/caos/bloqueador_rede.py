# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket
from types import TracebackType
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

_HOSTS_LOOPBACK_PERMITIDOS = frozenset({"127.0.0.1", "::1", "localhost", ""})


class ErroAcessoRedeProibidoEmTeste(RuntimeError):
    """Exceção lançada quando código em teste tenta abrir conexão para fora de loopback."""


def _validar_endereco_loopback(endereco: Any, registro_bloqueios: list[str]) -> None:
    if isinstance(endereco, tuple) and len(endereco) >= 1:
        host = str(endereco[0]).strip().lower()
        porta = endereco[1] if len(endereco) >= 2 else ""
        if host not in _HOSTS_LOOPBACK_PERMITIDOS:
            alvo = f"{host}:{porta}"
            registro_bloqueios.append(alvo)
            raise ErroAcessoRedeProibidoEmTeste(
                f"Conexão de rede externa bloqueada pelo Robô Caótico: {alvo}"
            )


class BloqueadorRedeCaos:
    """
    Guardião de rede para o Robô Caótico.
    Bloqueia conexões TCP/UDP externas (8.8.8.8, github.com, supabase.co, previa.arestaclimb.com)
    preservando conexões locais de loopback (127.0.0.1, ::1, localhost) e interceptando QDesktopServices.openUrl.
    """

    def __init__(self) -> None:
        self.tentativas_bloqueadas: list[str] = []
        self.urls_abertas_interceptadas: list[str] = []
        self._connect_original: Any = socket.socket.connect
        self._connect_ex_original: Any = socket.socket.connect_ex
        self._create_connection_original: Any = socket.create_connection
        self._open_url_original: Any = QDesktopServices.openUrl

    def ativar(self) -> "BloqueadorRedeCaos":
        """Instala os ganchos de bloqueio de socket externo e interceptação de navegador."""
        connect_orig = self._connect_original
        connect_ex_orig = self._connect_ex_original
        create_conn_orig = self._create_connection_original
        bloqueios = self.tentativas_bloqueadas
        urls_interceptadas = self.urls_abertas_interceptadas

        def _connect_seguro(sock_self: socket.socket, endereco: Any) -> Any:
            _validar_endereco_loopback(endereco, bloqueios)
            return connect_orig(sock_self, endereco)

        def _connect_ex_seguro(sock_self: socket.socket, endereco: Any) -> int:
            _validar_endereco_loopback(endereco, bloqueios)
            return int(connect_ex_orig(sock_self, endereco))

        def _create_connection_seguro(endereco: Any, *args: Any, **kwargs: Any) -> socket.socket:
            _validar_endereco_loopback(endereco, bloqueios)
            sock: socket.socket = create_conn_orig(endereco, *args, **kwargs)
            return sock

        def _open_url_seguro(url: QUrl) -> bool:
            urls_interceptadas.append(url.toString())
            return True

        socket.socket.connect = _connect_seguro  # type: ignore[method-assign,assignment]
        socket.socket.connect_ex = _connect_ex_seguro  # type: ignore[method-assign,assignment]
        socket.create_connection = _create_connection_seguro  # type: ignore[assignment]
        QDesktopServices.openUrl = staticmethod(_open_url_seguro)  # type: ignore[assignment]
        return self

    def desativar(self) -> None:
        """Restaura as funções originais de socket e QDesktopServices."""
        socket.socket.connect = self._connect_original  # type: ignore[method-assign]
        socket.socket.connect_ex = self._connect_ex_original  # type: ignore[method-assign]
        socket.create_connection = self._create_connection_original
        QDesktopServices.openUrl = self._open_url_original  # type: ignore[method-assign]

    def __enter__(self) -> "BloqueadorRedeCaos":
        return self.ativar()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        _ = (exc_type, exc_val, exc_tb)
        self.desativar()
