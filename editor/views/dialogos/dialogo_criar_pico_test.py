# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtWidgets import QApplication, QDialog
from editor.views.dialogos.dialogo_criar_pico import DialogoCriarPico

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialogo_criar_pico_inicializacao(qapp):
    """Verifica a inicialização padrão do diálogo com botão Criar desabilitado."""
    dialogo = DialogoCriarPico()
    dialogo.show()

    assert dialogo.edit_nome.text() == ""
    assert dialogo.btn_criar.isEnabled() is False


def test_dialogo_criar_pico_preenchimento_nome(qapp):
    """Verifica se ao preencher o nome, o botão Criar é habilitado."""
    dialogo = DialogoCriarPico()
    dialogo.show()

    dialogo.edit_nome.setText("Pedra do Baú")
    assert dialogo.btn_criar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""

    dialogo.btn_criar.click()
    nome, ok = dialogo.obter_dados_confirmados()
    assert nome == "Pedra do Baú"
    assert ok is True


def test_dialogo_criar_pico_validacao_duplicidade(qapp):
    """Verifica se o diálogo detecta duplicidade de nome e bloqueia a criação."""
    nomes_existentes = ["Pedra do Baú", "Cuscuzeiro"]
    dialogo = DialogoCriarPico(nomes_existentes=nomes_existentes)
    dialogo.show()

    # Nome duplicado
    dialogo.edit_nome.setText("Pedra do Baú")
    assert dialogo.btn_criar.isEnabled() is False
    assert "já existe" in dialogo.lbl_aviso.text().lower()

    # Nome inédito
    dialogo.edit_nome.setText("Visual das Águas")
    assert dialogo.btn_criar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""

    # Limpa o texto
    dialogo.edit_nome.setText("")
    assert dialogo.btn_criar.isEnabled() is False
    assert dialogo.lbl_aviso.text() == ""


def test_dialogo_criar_pico_metodo_estatico_obter_dados(qapp, monkeypatch):
    """Verifica a chamada do método estático obter_dados."""
    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Accepted))
    nome, ok = DialogoCriarPico.obter_dados(nome_sugerido="Falésia")
    assert nome == "Falésia"
    assert ok is True

    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Rejected))
    nome, ok = DialogoCriarPico.obter_dados()
    assert ok is False
