# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from editor.core.monitor_inatividade import MonitorInatividade


def test_deve_emitir_sinal_apos_tempo_de_inatividade(qtbot):
    monitor = MonitorInatividade(timeout_ms=200)
    monitor.iniciar()

    with qtbot.waitSignal(monitor.inatividade_detectada, timeout=500):
        pass  # Aguarda o sinal

    monitor.parar()


def test_deve_resetar_timer_ao_pressionar_tecla(qtbot):
    monitor = MonitorInatividade(timeout_ms=300)
    monitor.iniciar()

    class Rastreador:
        def __init__(self):
            self.chamado = False

        def marcar(self):
            self.chamado = True

    rastreador = Rastreador()
    monitor.inatividade_detectada.connect(rastreador.marcar)

    qtbot.wait(200)

    app = QApplication.instance()
    app.installEventFilter(monitor)
    try:
        evento = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        app.postEvent(app, evento)

        qtbot.wait(200)
        assert not rastreador.chamado, (
            "O sinal não deveria ter sido emitido pois o timer foi resetado"
        )

        qtbot.wait(200)
        assert rastreador.chamado, "O sinal deveria ter sido emitido após o tempo do reset"
    finally:
        app.removeEventFilter(monitor)
        monitor.parar()


def test_deve_resetar_timer_ao_clicar_mouse(qtbot):
    monitor = MonitorInatividade(timeout_ms=300)
    monitor.iniciar()

    class Rastreador:
        def __init__(self):
            self.chamado = False

        def marcar(self):
            self.chamado = True

    rastreador = Rastreador()
    monitor.inatividade_detectada.connect(rastreador.marcar)

    qtbot.wait(200)

    app = QApplication.instance()
    app.installEventFilter(monitor)
    try:
        evento = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.postEvent(app, evento)

        qtbot.wait(200)
        assert not rastreador.chamado

        qtbot.wait(200)
        assert rastreador.chamado
    finally:
        app.removeEventFilter(monitor)
        monitor.parar()


def test_nao_deve_resetar_timer_ao_apenas_mover_mouse(qtbot):
    monitor = MonitorInatividade(timeout_ms=300)
    monitor.iniciar()

    class Rastreador:
        def __init__(self):
            self.chamado = False

        def marcar(self):
            self.chamado = True

    rastreador = Rastreador()
    monitor.inatividade_detectada.connect(rastreador.marcar)

    qtbot.wait(200)

    app = QApplication.instance()
    app.installEventFilter(monitor)
    try:
        evento = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.postEvent(app, evento)

        qtbot.wait(200)
        assert rastreador.chamado, "O sinal deveria ter sido emitido mesmo com movimento de mouse"
    finally:
        app.removeEventFilter(monitor)
        monitor.parar()
