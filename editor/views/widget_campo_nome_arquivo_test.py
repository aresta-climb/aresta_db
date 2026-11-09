# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from editor.views.dialogos.dialogo_renomear_arquivo import DialogoRenomearArquivo
from editor.views.widget_campo_nome_arquivo import WidgetCampoNomeArquivo


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_widget_campo_nome_arquivo_somente_leitura_e_propriedade_protobuf(qapp):
    """Verifica que o QLineEdit interno é somente-leitura e possui a propriedade '__filename__'."""
    widget = WidgetCampoNomeArquivo(nome_inicial="setor_inicial.md")
    widget.show()

    assert widget.edit_nome.isReadOnly() is True
    assert widget.edit_nome.property("protobuf_field") == "__filename__"
    assert widget.obter_nome_arquivo() == "setor_inicial.md"
    assert widget.btn_modificar.text() == "Modificar..."

    widget.definir_nome_arquivo("setor_atualizado.md")
    assert widget.obter_nome_arquivo() == "setor_atualizado.md"


def test_widget_campo_nome_arquivo_modificar_emite_sinal_ao_confirmar_novo_nome(qapp):
    """Verifica que clicar em 'Modificar...' e confirmar um novo nome válido atualiza o campo e emite sinal."""
    recebidos: list[str] = []
    widget = WidgetCampoNomeArquivo(nome_inicial="setor_antigo.md")
    widget.definir_provedor_arquivos_existentes(lambda: ["setor_antigo.md", "setor_outro.md"])
    widget.nome_alterado.connect(recebidos.append)
    widget.show()

    def _confirmar_novo_nome():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoRenomearArquivo)
        # Tenta primeiro o duplicado para garantir que o provedor de arquivos existentes foi repassado
        modal.edit_arquivo.setText("setor_outro.md")
        assert modal.btn_confirmar.isEnabled() is False
        # Agora define um novo nome válido com espaço
        modal.edit_arquivo.setText("setor novo valido")
        assert modal.btn_confirmar.isEnabled() is True
        modal.btn_confirmar.click()

    QTimer.singleShot(0, _confirmar_novo_nome)
    widget.btn_modificar.click()

    assert widget.obter_nome_arquivo() == "setor_novo_valido.md"
    assert recebidos == ["setor_novo_valido.md"]


def test_widget_campo_nome_arquivo_nao_emite_sinal_se_cancelar_ou_mantiver_mesmo_nome(qapp):
    """Verifica que cancelar o modal ou confirmar o mesmo nome não emite nome_alterado."""
    recebidos: list[str] = []
    widget = WidgetCampoNomeArquivo(nome_inicial="setor_ fixo.md".replace(" ", ""))
    widget.nome_alterado.connect(recebidos.append)
    widget.show()

    # 1. Cancelar
    def _cancelar():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoRenomearArquivo)
        modal.edit_arquivo.setText("setor_ignorado.md")
        modal.btn_cancelar.click()

    QTimer.singleShot(0, _cancelar)
    widget.btn_modificar.click()
    assert widget.obter_nome_arquivo() == "setor_fixo.md"
    assert recebidos == []

    # 2. Confirmar o mesmo nome
    def _confirmar_igual():
        modal = QApplication.activeModalWidget()
        assert isinstance(modal, DialogoRenomearArquivo)
        modal.btn_confirmar.click()

    QTimer.singleShot(0, _confirmar_igual)
    widget.btn_modificar.click()
    assert widget.obter_nome_arquivo() == "setor_fixo.md"
    assert recebidos == []
