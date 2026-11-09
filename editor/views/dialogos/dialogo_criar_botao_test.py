# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QApplication

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
        arquivos_existentes=["apresentacao.md", "historia.md"],
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


def test_dialogo_criar_botao_metodo_estatico_obter_dados(qapp):
    """Verifica a chamada do método estático obter_dados com confirmação e rejeição."""
    from PySide6.QtCore import QTimer

    def _confirmar():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoCriarBotao)
        modal.btn_criar.click()

    QTimer.singleShot(0, _confirmar)
    texto, arquivo, ok = DialogoCriarBotao.obter_dados(texto_sugerido="Apoio")
    assert ok is True
    assert texto == "Apoio"
    assert arquivo == "apoio.md"

    def _cancelar():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoCriarBotao)
        modal.btn_cancelar.click()

    QTimer.singleShot(0, _cancelar)
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


def test_dialogo_criar_botao_valida_nome_arquivo_contra_vazio_invalidos_e_limite_100(qapp):
    """Verifica que o diálogo recusa arquivo vazio, caracteres inválidos ou > 100 chars e converte espaços."""
    dialogo = DialogoCriarBotao()
    dialogo.show()

    dialogo.edit_texto.setText("Sobre o Local")
    assert dialogo.btn_criar.isEnabled() is True

    # Limpar manualmente o arquivo deve bloquear o botão Criar
    dialogo.edit_arquivo.setText("")
    assert dialogo.btn_criar.isEnabled() is False
    assert dialogo.lbl_aviso.text() != ""

    # Digitar espaços no arquivo converte em '_' e permite criar
    dialogo.edit_arquivo.setText("secao sobre local")
    assert dialogo.edit_arquivo.text() == "secao_sobre_local"
    assert dialogo.btn_criar.isEnabled() is True

    # Caracteres inválidos ou acentos bloqueiam
    for invalido in ("secao:invalida.md", "<script>.md", "seção_acento.md", "Secao_Maiuscula.md"):
        dialogo.edit_arquivo.setText(invalido)
        assert dialogo.btn_criar.isEnabled() is False
        assert dialogo.lbl_aviso.text() != ""

    # Acima de 100 caracteres bloqueia
    dialogo.edit_arquivo.setText("a" * 99 + ".md")
    assert dialogo.btn_criar.isEnabled() is False
    assert "100" in dialogo.lbl_aviso.text()

