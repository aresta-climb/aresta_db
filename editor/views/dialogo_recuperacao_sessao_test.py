# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import editor.plataforma as mod_plataforma
from editor.plataforma.adaptador_plataforma_fake import AdaptadorPlataformaFake
from editor.views.dialogo_recuperacao_sessao import DialogoRecuperacaoSessao


def test_dialogo_recuperacao_sessao_renderizacao_e_icone_proprio(qtbot, tmp_path: Path):
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    icone_anterior = app.windowIcon()
    app.setWindowIcon(QIcon())

    fake = AdaptadorPlataformaFake(diretorio_dados=tmp_path)
    chave_plat = (
        "win32"
        if sys.platform.startswith("win")
        else ("linux" if sys.platform.startswith("linux") else "darwin")
    )
    cache_orig = dict(mod_plataforma._ADAPTADORES_POR_PLATAFORMA)
    try:
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA[chave_plat] = fake
        dialogo = DialogoRecuperacaoSessao(total_acoes=5)
        qtbot.addWidget(dialogo)
        dialogo.show()

        assert not dialogo.windowIcon().isNull()
        assert len(fake.icones_aplicados) >= 1
        assert "Sessão Anterior" in dialogo.windowTitle()
        assert "<b>5 ações não salvas</b>" in dialogo.label_mensagem.text()
        assert "Foram encontradas" in dialogo.label_mensagem.text()
        assert dialogo.botao_recuperar.isVisible()
        assert dialogo.botao_descartar.isVisible()
    finally:
        app.setWindowIcon(icone_anterior)
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.clear()
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.update(cache_orig)


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
