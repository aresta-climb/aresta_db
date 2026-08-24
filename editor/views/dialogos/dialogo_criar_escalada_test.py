# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QApplication
from editor.views.dialogos.dialogo_criar_escalada import DialogoCriarEscalada

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialogo_criar_escalada_inicializacao(qapp):
    """Verifica se o diálogo inicializa com Via Esportiva selecionada por padrão e botão Criar desabilitado."""
    dialogo = DialogoCriarEscalada()
    dialogo.show()

    assert dialogo.obter_tipo_selecionado() == "via_esportiva"
    assert dialogo.edit_nome.text() == ""
    assert dialogo.btn_criar.isEnabled() is False


def test_dialogo_criar_escalada_preenchimento_nome_habilita_criar(qapp):
    """Verifica se preencher o nome habilita o botão Criar e a confirmação retorna os dados."""
    dialogo = DialogoCriarEscalada()
    dialogo.show()

    dialogo.edit_nome.setText("Sombra e Água Fresca")
    assert dialogo.btn_criar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""

    tipo, nome, ok = dialogo.obter_dados_confirmados()
    assert tipo == "via_esportiva"
    assert nome == "Sombra e Água Fresca"


def test_dialogo_criar_escalada_selecao_tipo(qapp):
    """Verifica a seleção de diferentes tipos de escalada."""
    dialogo = DialogoCriarEscalada()
    dialogo.show()

    dialogo.combo_tipo.setCurrentText("Boulder")
    assert dialogo.obter_tipo_selecionado() == "boulder"

    dialogo.combo_tipo.setCurrentText("Via Móvel")
    assert dialogo.obter_tipo_selecionado() == "via_movel"


def test_dialogo_criar_escalada_validacao_duplicidade(qapp):
    """Verifica se o diálogo bloqueia a criação e exibe aviso caso o nome já exista no setor."""
    nomes_existentes = ["Sombra e Água Fresca", "Fissura do Meio"]
    dialogo = DialogoCriarEscalada(nomes_existentes=nomes_existentes)
    dialogo.show()

    dialogo.edit_nome.setText("Sombra e Água Fresca")
    assert dialogo.btn_criar.isEnabled() is False
    assert "já existe" in dialogo.lbl_aviso.text().lower()

    # Digita nome não existente
    dialogo.edit_nome.setText("Nova Via Inédita")
    assert dialogo.btn_criar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""

    # Limpa o texto
    dialogo.edit_nome.setText("")
    assert dialogo.btn_criar.isEnabled() is False
    assert dialogo.lbl_aviso.text() == ""


def test_dialogo_criar_escalada_metodo_estatico_obter_dados(qapp, monkeypatch):
    """Verifica a chamada do método estático obter_dados."""
    from PyQt6.QtWidgets import QDialog
    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Accepted))

    tipo, nome, ok = DialogoCriarEscalada.obter_dados(nomes_existentes=[])
    assert ok is True

    # Teste de cancelamento
    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Rejected))
    tipo, nome, ok = DialogoCriarEscalada.obter_dados(nomes_existentes=[])
    assert ok is False
