# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional
from PySide6.QtCore import QObject, QTimer, Signal, QEvent

class MonitorInatividade(QObject):
    """Monitora a inatividade do usuário através de eventos de input do Qt."""
    inatividade_detectada: Signal = Signal()
    
    def __init__(self, timeout_ms: int = 10000, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.timeout_ms: int = timeout_ms
        self.timer: QTimer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._ao_estourar_tempo)
        
    def iniciar(self) -> None:
        """Inicia o monitoramento."""
        self.timer.start(self.timeout_ms)
        
    def parar(self) -> None:
        """Para o monitoramento."""
        self.timer.stop()
        
    def resetar(self) -> None:
        """Reinicia a contagem do timer."""
        if self.timer.isActive():
            self.timer.start(self.timeout_ms)
            
    def _ao_estourar_tempo(self) -> None:
        """Emite o sinal quando o tempo de inatividade é atingido."""
        self.inatividade_detectada.emit()
        
    def eventFilter(self, objeto: QObject, evento: QEvent) -> bool:
        """Filtra eventos da aplicação para detectar atividade do usuário."""
        # Consideramos apenas cliques de mouse ou teclas pressionadas como interação
        # Mover o mouse (MouseMove) NÃO reseta o timer conforme requisitos
        if evento.type() in [QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress]:
            self.resetar()
            
        res = super().eventFilter(objeto, evento)
        return bool(res)

