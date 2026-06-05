import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from editor.views.notificacao import NotificacaoToast

def test_notificacao_exibe_texto_corretamente(qtbot):
    mensagem = "Teste de Notificação"
    toast = NotificacaoToast(mensagem)
    qtbot.addWidget(toast)
    toast.show()
    
    assert toast.label_texto.text() == mensagem

def test_notificacao_possui_estilo_correto(qtbot):
    toast = NotificacaoToast("Sucesso")
    qtbot.addWidget(toast)
    
    # Verifica se tem transparência e sem bordas de janela
    assert toast.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert toast.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

def test_notificacao_auto_destruicao(qtbot):
    # Diminuímos o timeout para o teste ser mais rápido se possível, 
    # ou apenas verificamos se o timer está rodando
    toast = NotificacaoToast("Auto-close", timeout_ms=100)
    qtbot.addWidget(toast)
    toast.show()
    
    # Aguarda o timeout (100ms) + animação (500ms) + margem
    qtbot.wait(1000)
    
    # Como WA_DeleteOnClose está ativo, o objeto C++ deve ter sido deletado.
    # Tentar acessar qualquer método dele deve gerar um RuntimeError.
    with pytest.raises(RuntimeError):
        toast.isVisible()
