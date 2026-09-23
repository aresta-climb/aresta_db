# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o componente AlcaArrasteItem.
"""

from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from editor.views.componentes.alca_arraste_item import AlcaArrasteItem


def test_alca_arraste_item_inicializacao(qtbot):
    alca = AlcaArrasteItem()
    qtbot.addWidget(alca)
    alca.show()

    assert alca.text() == "⠿"
    assert alca.cursor().shape() == Qt.CursorShape.OpenHandCursor
    assert "reordenar" in alca.toolTip().lower()


def test_alca_arraste_item_emite_sinal_ao_arrastar(qtbot):
    alca = AlcaArrasteItem()
    qtbot.addWidget(alca)
    alca.show()

    sinais = []
    alca.solicitar_arraste.connect(sinais.append)

    pos_inicial = QPointF(5.0, 5.0)
    evento_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos_inicial,
        pos_inicial,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    alca.mousePressEvent(evento_press)

    assert len(sinais) == 0

    dist_min = QApplication.startDragDistance() + 5
    pos_move = QPointF(5.0, 5.0 + dist_min)
    evento_move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        pos_move,
        pos_move,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    alca.mouseMoveEvent(evento_move)

    assert len(sinais) == 1
    assert isinstance(sinais[0], QPoint)


def test_alca_arraste_item_ignora_movimento_curto(qtbot):
    alca = AlcaArrasteItem()
    qtbot.addWidget(alca)
    alca.show()

    sinais = []
    alca.solicitar_arraste.connect(sinais.append)

    pos_inicial = QPointF(5.0, 5.0)
    evento_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos_inicial,
        pos_inicial,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    alca.mousePressEvent(evento_press)

    # Movimento de apenas 1 pixel (abaixo de startDragDistance)
    pos_move = QPointF(5.0, 6.0)
    evento_move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        pos_move,
        pos_move,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    alca.mouseMoveEvent(evento_move)

    assert len(sinais) == 0


def test_alca_arraste_item_libera_posicao_no_release(qtbot):
    alca = AlcaArrasteItem()
    qtbot.addWidget(alca)
    alca.show()

    pos_inicial = QPointF(5.0, 5.0)
    evento_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos_inicial,
        pos_inicial,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    alca.mousePressEvent(evento_press)

    evento_release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        pos_inicial,
        pos_inicial,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    alca.mouseReleaseEvent(evento_release)

    assert alca._pos_inicial is None
