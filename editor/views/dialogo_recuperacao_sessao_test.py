# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QDialog
from editor.views.dialogo_recuperacao_sessao import DialogoRecuperacaoSessao


def test_dialogo_recuperacao_sessao_renderizacao(qtbot):
    dialogo = DialogoRecuperacaoSessao(total_acoes=5)
    qtbot.addWidget(dialogo)
    dialogo.show()
    
    assert "Sessão Anterior" in dialogo.windowTitle()
    assert "<b>5 ações não salvas</b>" in dialogo.label_mensagem.text()
    assert "Foram encontradas" in dialogo.label_mensagem.text()
    assert dialogo.botao_recuperar.isVisible()
    assert dialogo.botao_descartar.isVisible()


def test_dialogo_recuperacao_sessao_singular(qtbot):
    dialogo = DialogoRecuperacaoSessao(total_acoes=1)
    qtbot.addWidget(dialogo)
    dialogo.show()
    
    assert "<b>1 ação não salva</b>" in dialogo.label_mensagem.text()
    assert "Foi encontrada" in dialogo.label_mensagem.text()


def test_dialogo_recuperacao_sessao_aceitar(qtbot):
    dialogo = DialogoRecuperacaoSessao(total_acoes=3)
    qtbot.addWidget(dialogo)
    
    with qtbot.waitSignal(dialogo.accepted, timeout=1000):
        dialogo.botao_recuperar.click()


def test_dialogo_recuperacao_sessao_descartar(qtbot):
    dialogo = DialogoRecuperacaoSessao(total_acoes=3)
    qtbot.addWidget(dialogo)
    
    with qtbot.waitSignal(dialogo.rejected, timeout=1000):
        dialogo.botao_descartar.click()
