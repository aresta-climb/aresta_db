# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from editor.core.nomes_arquivos import LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD
from editor.views.dialogos.dialogo_renomear_arquivo import DialogoRenomearArquivo


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialogo_renomear_arquivo_inicializacao_com_nome_valido(qapp):
    """Verifica que o diálogo inicializa com o nome atual válido e botão Confirmar habilitado."""
    dialogo = DialogoRenomearArquivo(arquivo_atual="setor_principal.md")
    dialogo.show()

    assert dialogo.edit_arquivo.text() == "setor_principal.md"
    assert dialogo.btn_confirmar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""


def test_dialogo_renomear_arquivo_converte_espacos_para_underscore_e_garante_md(qapp):
    """Verifica que espaços digitados são convertidos em '_' e o retorno garante '.md'."""
    dialogo = DialogoRenomearArquivo(arquivo_atual="setor_antigo.md")
    dialogo.show()

    dialogo.edit_arquivo.setText("setor fornos novos")
    assert dialogo.edit_arquivo.text() == "setor_fornos_novos"
    assert dialogo.btn_confirmar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""

    dialogo.btn_confirmar.click()
    nome, confirmado = dialogo.obter_dados_confirmados()
    assert confirmado is True
    assert nome == "setor_fornos_novos.md"


def test_dialogo_renomear_arquivo_recusa_vazio_caracteres_invalidos_e_acima_de_100_chars(qapp):
    """Verifica que entradas vazias, com caracteres inválidos ou > 100 caracteres bloqueiam confirmação."""
    dialogo = DialogoRenomearArquivo(arquivo_atual="setor_antigo.md")
    dialogo.show()

    # Vazio
    dialogo.edit_arquivo.setText("")
    assert dialogo.btn_confirmar.isEnabled() is False
    assert dialogo.lbl_aviso.text() != ""

    # Caracteres inválidos (Issue #86 e #87)
    for invalido in (
        "YAML: 'aspas' \"duplas\".md",
        "<script>alert('caos')</script>.md",
        "setor_forno_da_onça.md",
        "Setor_Maiusculo.md",
    ):
        dialogo.edit_arquivo.setText(invalido)
        assert dialogo.btn_confirmar.isEnabled() is False
        assert dialogo.lbl_aviso.text() != ""

    # Acima de 100 caracteres
    nome_longo = "a" * (LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD - 2) + ".md"
    dialogo.edit_arquivo.setText(nome_longo)
    assert dialogo.btn_confirmar.isEnabled() is False
    assert "100" in dialogo.lbl_aviso.text()


def test_dialogo_renomear_arquivo_recusa_duplicata_mas_permite_proprio_nome(qapp):
    """Verifica que o diálogo recusa colisão com outro arquivo do croqui mas aceita o próprio nome atual."""
    existentes = ["setor_norte.md", "setor_sul.md"]
    dialogo = DialogoRenomearArquivo(
        arquivo_atual="setor_norte.md",
        arquivos_existentes=existentes,
    )
    dialogo.show()

    # Próprio nome é válido
    assert dialogo.btn_confirmar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""

    # Nome de outro arquivo existente é bloqueado
    dialogo.edit_arquivo.setText("setor_sul.md")
    assert dialogo.btn_confirmar.isEnabled() is False
    assert "uso" in dialogo.lbl_aviso.text().lower()


def test_dialogo_renomear_arquivo_obter_dados_confirmando_e_cancelando(qapp):
    """Verifica o ciclo completo de obter_dados via loop modal real do Qt (confirmar e cancelar)."""

    def _confirmar_modal():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoRenomearArquivo)
        modal.edit_arquivo.setText("setor_confirmado.md")
        modal.btn_confirmar.click()

    QTimer.singleShot(0, _confirmar_modal)
    nome, ok = DialogoRenomearArquivo.obter_dados(arquivo_atual="setor_inicial.md")
    assert ok is True
    assert nome == "setor_confirmado.md"

    def _cancelar_modal():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoRenomearArquivo)
        modal.btn_cancelar.click()

    QTimer.singleShot(0, _cancelar_modal)
    _, ok_cancelado = DialogoRenomearArquivo.obter_dados(arquivo_atual="setor_inicial.md")
    assert ok_cancelado is False
