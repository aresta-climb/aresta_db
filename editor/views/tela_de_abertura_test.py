import pytest
from PyQt6.QtWidgets import QApplication, QLineEdit, QPushButton
from PyQt6.QtCore import Qt
from unittest.mock import MagicMock, patch
from editor.views.tela_de_abertura import TelaDeAbertura

def test_tela_abertura_componentes_iniciais(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    
    assert abertura.label_status.text() == "Iniciando..."
    assert not abertura.progress_bar.isVisible()
    assert not abertura.auth_container.isVisible()

def test_tela_abertura_exibir_barra_progresso(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)
    
    abertura.exibir_barra_progresso(True)
    assert abertura.progress_bar.isVisible()
    
    abertura.exibir_barra_progresso(False)
    assert not abertura.progress_bar.isVisible()

def test_tela_abertura_exibe_codigo_auth(qtbot):
    abertura = TelaDeAbertura()
    abertura.show() # Necessário para isVisible() funcionar corretamente
    qtbot.addWidget(abertura)
    
    codigo = "1234-5678"
    abertura.exibir_codigo_auth(codigo)
    
    assert abertura.auth_container.isVisible()
    assert abertura.edit_auth_code.text() == codigo
    assert abertura.edit_auth_code.isReadOnly()
    
    abertura.esconder_auth()
    assert not abertura.auth_container.isVisible()

def test_tela_abertura_botao_copiar(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    
    codigo = "ABCD-EFGH"
    abertura.exibir_codigo_auth(codigo)
    
    # Mock do clipboard
    clipboard = QApplication.clipboard()
    
    qtbot.mouseClick(abertura.btn_copy, Qt.MouseButton.LeftButton)
    
    assert clipboard.text() == codigo
    assert abertura.btn_copy.text() == "Copiado!"

def test_tela_abertura_botao_abrir_navegador(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    abertura.exibir_codigo_auth("CODE")
    
    with patch("editor.views.tela_de_abertura.QDesktopServices.openUrl") as mock_open:
        qtbot.mouseClick(abertura.btn_abrir_github, Qt.MouseButton.LeftButton)
        mock_open.assert_called_once()
        args, _ = mock_open.call_args
        assert args[0].toString() == "https://github.com/login/device"

def test_tela_abertura_botao_fechar(qtbot):
    with patch("editor.views.tela_de_abertura.QApplication.quit") as mock_quit:
        abertura = TelaDeAbertura()
        qtbot.addWidget(abertura)
        qtbot.mouseClick(abertura.btn_close, Qt.MouseButton.LeftButton)
        mock_quit.assert_called_once()

def test_tela_abertura_nao_fica_no_topo(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    
    # Verifica que a flag WindowStaysOnTopHint não está presente
    flags = abertura.windowFlags()
    assert not (flags & Qt.WindowType.WindowStaysOnTopHint)
    # Verifica que FramelessWindowHint continua presente
    assert flags & Qt.WindowType.FramelessWindowHint

def test_tela_abertura_logo_oficial(qtbot):
    abertura = TelaDeAbertura()
    qtbot.addWidget(abertura)
    
    pixmap = abertura.label_logo.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()

def test_tela_abertura_drag_and_drop(qtbot):
    abertura = TelaDeAbertura()
    abertura.show()
    qtbot.addWidget(abertura)
    
    pos_inicial = abertura.pos()
    
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtCore import QPointF, QEvent
    
    # Simula o clique inicial
    pos_local = QPointF(10.0, 10.0)
    pos_global = abertura.mapToGlobal(pos_local.toPoint())
    
    evento_press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        pos_local,
        QPointF(pos_global.x(), pos_global.y()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    abertura.mousePressEvent(evento_press)
    
    # Simula o movimento
    pos_global_movida = QPointF(pos_global.x() + 50, pos_global.y() + 50)
    pos_local_movida = QPointF(60.0, 60.0)
    
    evento_move = QMouseEvent(
        QEvent.Type.MouseMove,
        pos_local_movida,
        pos_global_movida,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    abertura.mouseMoveEvent(evento_move)
    
    nova_pos = abertura.pos()
    assert nova_pos.x() == pos_inicial.x() + 50
    assert nova_pos.y() == pos_inicial.y() + 50
