# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Callable, Optional
from PySide6.QtCore import QObject, QTimer


class TemporizadorCoalescencia(QObject):
    """Gerencia a coalescência (debounce) de eventos frequentes, como digitação.
    
    Adia a execução de uma função de retorno (callback) até que transcorra um
    intervalo sem novos agendamentos, com suporte à descarga forçada imediata.
    """

    def __init__(self, atraso_padrao_ms: int = 250, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.atraso_padrao_ms: int = atraso_padrao_ms
        self._callback: Optional[Callable[[], None]] = None

        self._timer: QTimer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._ao_expirar_tempo)

    def agendar(self, callback: Callable[[], None], atraso_ms: Optional[int] = None) -> None:
        """Agenda ou reinicia o temporizador para executar o callback após o atraso."""
        self._callback = callback
        intervalo = self.atraso_padrao_ms if atraso_ms is None else atraso_ms
        self._timer.start(intervalo)

    def descartar(self) -> None:
        """Cancela qualquer agendamento pendente sem disparar o callback."""
        self._timer.stop()
        self._callback = None

    def forcar_descarga(self) -> None:
        """Executa imediatamente a ação pendente caso haja um agendamento ativo."""
        if self._callback is not None:
            callback = self._callback
            self.descartar()
            callback()

    def esta_ativo(self) -> bool:
        """Verifica se há uma ação agendada aguardando expiração."""
        return self._timer.isActive() or self._callback is not None

    def _ao_expirar_tempo(self) -> None:
        """Dispara o callback quando o temporizador atinge o tempo limite."""
        if self._callback is not None:
            callback = self._callback
            self._callback = None
            callback()
