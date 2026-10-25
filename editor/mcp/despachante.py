# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FuturoTimeoutError
from typing import Any, TypeVar

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

T = TypeVar("T")


class DespachanteQt(QObject):
    """
    Despachante thread-safe que garante a execução de funções de leitura e mutação
    do modelo e da interface gráfica exclusivamente na thread principal do Qt.
    """

    _sinal_executar = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
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

    def executar(self, fn: Callable[..., T], *args: Any, timeout: float = 10.0, **kwargs: Any) -> T:
        """
        Executa `fn(*args, **kwargs)` na thread principal associada a este QObject
        e retorna o seu resultado ou relança qualquer exceção ocorrida.
        """
        if QThread.currentThread() == self.thread():
            return fn(*args, **kwargs)

        futuro: Future[T] = Future()
        self._sinal_executar.emit((futuro, fn, args, kwargs))
        try:
            return futuro.result(timeout=timeout)
        except FuturoTimeoutError as exc:
            futuro.cancel()
            raise TimeoutError(
                "Tempo limite excedido ao aguardar execução na thread principal do Qt."
            ) from exc
