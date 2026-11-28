# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import threading
from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FuturoTimeoutError
from typing import Any, TypeVar

from PySide6.QtCore import QObject, Qt, Signal, Slot

T = TypeVar("T")


class DespachanteQt(QObject):
    """
    Despachante thread-safe que garante a execução de funções de leitura e mutação
    do modelo e da interface gráfica exclusivamente na thread principal do Qt.
    """

    _sinal_executar = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        timeout_execucao_padrao: float = 60.0,
    ) -> None:
        super().__init__(parent)
        self._id_thread_principal = threading.get_ident()
        self._timeout_execucao_padrao = float(timeout_execucao_padrao)
        self._sinal_executar.connect(self._processar_pacote, Qt.ConnectionType.QueuedConnection)

    @Slot(object)
    def _processar_pacote(
        self, pacote: tuple[Future[Any], Callable[..., Any], tuple[Any, ...], dict[str, Any]]
    ) -> None:
        futuro, fn, args, kwargs = pacote
        if not futuro.set_running_or_notify_cancel():
            return
        try:
            resultado = fn(*args, **kwargs)
            futuro.set_result(resultado)
        except Exception as exc:
            futuro.set_exception(exc)

    def executar(
        self,
        fn: Callable[..., T],
        *args: Any,
        timeout: float = 10.0,
        timeout_execucao: float | None = None,
        **kwargs: Any,
    ) -> T:
        """
        Executa `fn(*args, **kwargs)` na thread principal associada a este QObject
        e retorna o seu resultado ou relança qualquer exceção ocorrida.
        Separa o tempo limite de espera na fila (`timeout`) do tempo limite máximo
        de conclusão (`timeout_execucao`) caso a função já tenha iniciado na thread Qt.
        """
        if threading.get_ident() == self._id_thread_principal:
            return fn(*args, **kwargs)

        futuro: Future[T] = Future()
        self._sinal_executar.emit((futuro, fn, args, kwargs))
        try:
            return futuro.result(timeout=timeout)
        except FuturoTimeoutError as exc:
            if futuro.cancel():
                raise TimeoutError(
                    "Tempo limite excedido ao aguardar execução na thread principal do Qt."
                ) from exc

            limite_execucao = (
                self._timeout_execucao_padrao
                if timeout_execucao is None
                else float(timeout_execucao)
            )
            try:
                return futuro.result(timeout=max(0.01, limite_execucao))
            except FuturoTimeoutError as exc_exec:
                raise TimeoutError(
                    "A execução já iniciada na thread principal do Qt excedeu o tempo limite "
                    "máximo de conclusão."
                ) from exc_exec
