# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from editor.views.dialogo_erro_salvamento import (
    criar_dialogo_erro_salvamento,
    exibir_dialogo_erro_salvamento,
    copiar_para_area_transferencia,
)


def test_criar_dialogo_erro_salvamento_propriedades_basicas(qtbot):
    pai = QWidget()
    qtbot.addWidget(pai)

    erro = "Erro durante a compilação: falha interna"
    traceback_falso = "Traceback (most recent call last):\n  File 'test.py', line 10, in <module>\n    raise ValueError('Falha')"

    dialogo = criar_dialogo_erro_salvamento(pai, erro, traceback_detalhado=traceback_falso)

    assert isinstance(dialogo, QMessageBox)
    assert dialogo.icon() == QMessageBox.Icon.Critical
    assert "Não foi possível salvar" in dialogo.windowTitle()
    assert "Não foi possível salvar o croqui" in dialogo.text()

    # Mensagem informativa amigável que tranquiliza o usuário
    info_text = dialogo.informativeText()
    assert "dados em tela permanecem seguros" in info_text or "dados permanecem seguros" in info_text

    # Garante que não culpa estruturas vazias
    assert "vazio" not in info_text.lower()
    assert "incompleto" not in info_text.lower()

    # Detalhes técnicos expansíveis
    detalhes = dialogo.detailedText()
    assert "falha interna" in detalhes
    assert "Traceback" in detalhes


def test_criar_dialogo_com_objeto_exception(qtbot):
    pai = QWidget()
    qtbot.addWidget(pai)

    ex = RuntimeError("Falha de I/O em disco")
    dialogo = criar_dialogo_erro_salvamento(pai, ex)

    assert "Falha de I/O em disco" in dialogo.detailedText()


def test_dialogo_erro_salvamento_sanitiza_caminhos(qtbot):
    pai = QWidget()
    qtbot.addWidget(pai)

    from pathlib import Path
    home_dir = str(Path.home())
    traceback_com_usuario = f"Traceback:\n  File '{home_dir}\\arquivo.py', line 5"

    dialogo = criar_dialogo_erro_salvamento(pai, "Erro teste", traceback_detalhado=traceback_com_usuario)
    detalhes = dialogo.detailedText()

    assert home_dir not in detalhes
    assert "%userprofile%" in detalhes


def test_copiar_para_area_transferencia(qapp):
    texto_teste = "Log de erro para suporte técnico"
    copiar_para_area_transferencia(texto_teste)

    clipboard = QApplication.clipboard()
    assert clipboard.text() == texto_teste


def test_botao_copiar_detalhes_clicado(qtbot):
    dialogo = criar_dialogo_erro_salvamento(None, "Erro de teste para copiar", "Linha 1 do traceback")
    qtbot.addWidget(dialogo)

    # Localizar o botão de copiar detalhes
    botao_copiar = None
    for botao in dialogo.buttons():
        if "copiar" in botao.text().lower():
            botao_copiar = botao
            break

    assert botao_copiar is not None, "Botão 'Copiar Detalhes' deve estar presente no diálogo"

    qtbot.mouseClick(botao_copiar, Qt.MouseButton.LeftButton)
    clipboard = QApplication.clipboard()
    assert "Erro de teste para copiar" in clipboard.text()
    assert "Linha 1 do traceback" in clipboard.text()


def test_exibir_dialogo_erro_salvamento_chama_exec(monkeypatch):
    chamou_exec = False

    def fake_exec(self):
        nonlocal chamou_exec
        chamou_exec = True
        return 1

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)

    res = exibir_dialogo_erro_salvamento(None, "Erro teste")
    assert chamou_exec is True
    assert res == 1
