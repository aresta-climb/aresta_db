# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual de alça de arraste (drag handle) para itens de coleções repetidas.
"""

from typing import Optional
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QWidget, QApplication


class AlcaArrasteItem(QLabel):
    """
    Rótulo atuando como alça de arraste (⠿) para disparar reordenação por Drag and Drop.
    Emite o sinal `solicitar_arraste` com a posição inicial quando a distância mínima
    de arraste for atingida com o botão esquerdo do mouse pressionado.
    """

    solicitar_arraste: Signal = Signal(QPoint)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText("⠿")
        self.setToolTip("Arrastar para reordenar")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet(
            "QLabel {"
            "  color: #777777;"
            "  font-size: 11pt;"
            "  font-weight: bold;"
            "  padding: 2px 4px;"
            "  border-radius: 3px;"
            "}"
            "QLabel:hover {"
            "  color: #2b579a;"
            "  background-color: #e0e8f5;"
            "}"
        )
        self._pos_inicial: Optional[QPoint] = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pos_inicial = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (event.buttons() & Qt.MouseButton.LeftButton) and self._pos_inicial is not None:
            distancia = (event.position().toPoint() - self._pos_inicial).manhattanLength()
            if distancia >= QApplication.startDragDistance():
                ponto_disparo = self._pos_inicial
                self._pos_inicial = None
                self.solicitar_arraste.emit(ponto_disparo)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._pos_inicial = None
        super().mouseReleaseEvent(event)
