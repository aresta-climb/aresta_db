# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from editor.views.dialogos.dialogo_conflito_sincronizacao import (
    DialogoConflitoSincronizacao,
    DecisaoConflito,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestDialogoConflitoSincronizacao:
    """Testes unitários para o diálogo de resolução de conflitos de sincronização."""

    def test_inicializacao_exibe_arquivos_em_conflito(self, qapp):
        arquivos = ["database/bau/croqui.yaml", "database/bau/foto.png"]
        dialogo = DialogoConflitoSincronizacao(
            id_croqui="bau",
            nome_branch="edicao-bau-1234",
            arquivos_conflito=arquivos,
        )

        assert "bau" in dialogo.windowTitle().lower() or "conflito" in dialogo.windowTitle().lower()
        assert len(dialogo.arquivos_conflito) == 2
        # Verifica se os arquivos estão listados no widget
        texto_lista = dialogo.obter_texto_arquivos()
        assert "croqui.yaml" in texto_lista
        assert "foto.png" in texto_lista

    def test_clicar_manter_local(self, qapp):
        dialogo = DialogoConflitoSincronizacao(
            id_croqui="bau",
            nome_branch="edicao-bau-1234",
            arquivos_conflito=["database/bau/croqui.yaml"],
        )
        dialogo.botao_manter_local.click()
        assert dialogo.obter_decisao() == DecisaoConflito.MANTER_LOCAL

    def test_clicar_usar_remoto(self, qapp):
        dialogo = DialogoConflitoSincronizacao(
            id_croqui="bau",
            nome_branch="edicao-bau-1234",
            arquivos_conflito=["database/bau/croqui.yaml"],
        )
        dialogo.botao_usar_remoto.click()
        assert dialogo.obter_decisao() == DecisaoConflito.USAR_REMOTO

    def test_clicar_cancelar(self, qapp):
        dialogo = DialogoConflitoSincronizacao(
            id_croqui="bau",
            nome_branch="edicao-bau-1234",
            arquivos_conflito=["database/bau/croqui.yaml"],
        )
        dialogo.botao_cancelar.click()
        assert dialogo.obter_decisao() == DecisaoConflito.CANCELAR
