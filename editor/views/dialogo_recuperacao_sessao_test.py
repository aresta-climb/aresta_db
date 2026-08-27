# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QDialog
from editor.views.dialogo_recuperacao_sessao import DialogoRecuperacaoSessao


def test_dialogo_recuperacao_sessao_renderizacao(qtbot):
    dialogo = DialogoRecuperacaoSessao(total_acoes=5)
    qtbot.addWidget(dialogo)
    dialogo.show()
    
    assert "Sessão Anterior" in dialogo.windowTitle()
    assert "5" in dialogo.label_mensagem.text()
    assert dialogo.botao_recuperar.isVisible()
    assert dialogo.botao_descartar.isVisible()


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
