# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QApplication
from editor.views.dialogos.dialogo_criar_botao import DialogoCriarBotao

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialogo_criar_botao_inicializacao(qapp):
    """Verifica a inicialização padrão do diálogo com botão Criar desabilitado."""
    dialogo = DialogoCriarBotao()
    dialogo.show()

    assert dialogo.edit_texto.text() == ""
    assert dialogo.edit_arquivo.text() == ""
    assert dialogo.btn_criar.isEnabled() is False


def test_dialogo_criar_botao_auto_proposicao_arquivo(qapp):
    """Verifica se digitar o texto do botão auto-propõe o nome do arquivo .md em snake_case."""
    dialogo = DialogoCriarBotao()
    dialogo.show()

    dialogo.edit_texto.setText("Como Chegar ao Pico")
    assert dialogo.edit_arquivo.text() == "como_chegar_ao_pico.md"
    assert dialogo.btn_criar.isEnabled() is True

    # Edição manual do arquivo preserva o valor customizado
    dialogo.edit_arquivo.setText("meu_arquivo_custom.md")
    dialogo.edit_texto.setText("Como Chegar ao Pico Editado")
    assert dialogo.edit_arquivo.text() == "meu_arquivo_custom.md"

    # Confirmação garante extensão .md
    dialogo.edit_arquivo.setText("meu_arquivo_sem_ext")
    texto, arquivo, ok = dialogo.obter_dados_confirmados()
    assert texto == "Como Chegar ao Pico Editado"
    assert arquivo == "meu_arquivo_sem_ext.md"


def test_dialogo_criar_botao_validacao_duplicidade(qapp):
    """Verifica se duplicidade de texto ou de arquivo é detectada e bloqueia a criação."""
    dialogo = DialogoCriarBotao(
        textos_existentes=["Apresentação", "História"],
        arquivos_existentes=["apresentacao.md", "historia.md"]
    )
    dialogo.show()

    # Texto duplicado
    dialogo.edit_texto.setText("Apresentação")
    assert dialogo.btn_criar.isEnabled() is False
    assert "já existe" in dialogo.lbl_aviso.text().lower()

    # Texto novo mas arquivo duplicado
    dialogo.edit_texto.setText("Novo Botão")
    dialogo.edit_arquivo.setText("historia.md")
    assert dialogo.btn_criar.isEnabled() is False
    assert "já existe" in dialogo.lbl_aviso.text().lower()

    # Texto e arquivo inéditos
    dialogo.edit_arquivo.setText("novo_botao.md")
    assert dialogo.btn_criar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""


def test_dialogo_criar_botao_metodo_estatico_obter_dados(qapp, monkeypatch):
    """Verifica a chamada do método estático obter_dados com confirmação e rejeição."""
    from PyQt6.QtWidgets import QDialog
    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Accepted))

    texto, arquivo, ok = DialogoCriarBotao.obter_dados(texto_sugerido="Apoio")
    assert ok is True

    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Rejected))
    texto, arquivo, ok = DialogoCriarBotao.obter_dados()
    assert ok is False


def test_dialogo_criar_botao_texto_vazio_e_caracteres_especiais(qapp):
    """Verifica comportamento ao limpar o campo texto ou usar caracteres sem slug."""
    dialogo = DialogoCriarBotao()
    dialogo.show()

    dialogo.edit_texto.setText("Info")
    assert dialogo.edit_arquivo.text() == "info.md"

    dialogo.edit_texto.setText("")
    assert dialogo.edit_arquivo.text() == ""
    assert dialogo.btn_criar.isEnabled() is False

    dialogo.edit_texto.setText("!!!")
    assert dialogo.edit_arquivo.text() == "botao.md"

