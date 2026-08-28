# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QEvent, QPointF, QPoint
from PyQt6.QtGui import QKeyEvent, QMouseEvent
from editor.core.monitor_inatividade import MonitorInatividade
import time

def test_deve_emitir_sinal_apos_tempo_de_inatividade(qtbot):
    monitor = MonitorInatividade(timeout_ms=200)
    monitor.iniciar()
    
    with qtbot.waitSignal(monitor.inatividade_detectada, timeout=500):
        pass # Aguarda o sinal
        
    monitor.parar()

def test_deve_resetar_timer_ao_pressionar_tecla(qtbot):
    monitor = MonitorInatividade(timeout_ms=300)
    monitor.iniciar()
    
    # Usamos uma classe rastreadora para capturar a emissão do sinal
    class Rastreador:
        def __init__(self): self.chamado = False
        def marcar(self): self.chamado = True
    
    rastreador = Rastreador()
    monitor.inatividade_detectada.connect(rastreador.marcar)
    
    qtbot.wait(200)
    
    # Simula evento de tecla
    evento = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
    QApplication.instance().installEventFilter(monitor)
    QApplication.instance().postEvent(QApplication.instance(), evento)
    
    # Se resetou, ele no deve disparar nos prximos 200ms (total 400ms desde o incio)
    qtbot.wait(200)
    assert not rastreador.chamado, "O sinal não deveria ter sido emitido pois o timer foi resetado"
    
    # Agora aguarda mais 200ms para ver se dispara (total 400ms desde o reset)
    qtbot.wait(200)
    assert rastreador.chamado, "O sinal deveria ter sido emitido após o tempo do reset"
    
    monitor.parar()

def test_deve_resetar_timer_ao_clicar_mouse(qtbot):
    monitor = MonitorInatividade(timeout_ms=300)
    monitor.iniciar()
    
    class Rastreador:
        def __init__(self): self.chamado = False
        def marcar(self): self.chamado = True
    
    rastreador = Rastreador()
    monitor.inatividade_detectada.connect(rastreador.marcar)
    
    qtbot.wait(200)
    
    # Simula evento de clique
    evento = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(0,0), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.instance().installEventFilter(monitor)
    QApplication.instance().postEvent(QApplication.instance(), evento)
    
    qtbot.wait(200)
    assert not rastreador.chamado
    
    qtbot.wait(200)
    assert rastreador.chamado
    
    monitor.parar()

def test_nao_deve_resetar_timer_ao_apenas_mover_mouse(qtbot):
    monitor = MonitorInatividade(timeout_ms=300)
    monitor.iniciar()
    
    class Rastreador:
        def __init__(self): self.chamado = False
        def marcar(self): self.chamado = True
    
    rastreador = Rastreador()
    monitor.inatividade_detectada.connect(rastreador.marcar)
    
    qtbot.wait(200)
    
    # Simula movimento de mouse (no deve resetar)
    evento = QMouseEvent(QEvent.Type.MouseMove, QPointF(10,10), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    QApplication.instance().installEventFilter(monitor)
    QApplication.instance().postEvent(QApplication.instance(), evento)
    
    # Deve disparar em breve (total 300ms)
    qtbot.wait(200)
    assert rastreador.chamado, "O sinal deveria ter sido emitido mesmo com movimento de mouse"
        
    monitor.parar()
