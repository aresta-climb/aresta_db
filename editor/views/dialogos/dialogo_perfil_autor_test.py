# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QDialog
from unittest.mock import patch

from editor.views.dialogos.dialogo_perfil_autor import DialogoPerfilAutor


class TesteDialogoPerfilAutor:
    """Testes unitários para o diálogo de perfil do autor."""

    def teste_inicializacao_sem_nome_pre_preenchido(self, qtbot):
        dialogo = DialogoPerfilAutor()
        qtbot.addWidget(dialogo)

        assert dialogo.edit_nome.text() == ""
        assert dialogo.edit_nome.placeholderText() == "Ex: João da Silva"
        assert dialogo.windowTitle() == "Identificação do Autor"

    def teste_pre_preenchimento_com_nome_sugerido(self, qtbot):
        dialogo = DialogoPerfilAutor(nome_sugerido="Renato Utsch")
        qtbot.addWidget(dialogo)

        assert dialogo.edit_nome.text() == "Renato Utsch"

    def teste_validacao_rejeita_nome_incompleto(self, qtbot):
        dialogo = DialogoPerfilAutor()
        qtbot.addWidget(dialogo)

        dialogo.edit_nome.setText("Renato")
        with patch("PyQt6.QtWidgets.QMessageBox.warning") as mock_aviso:
            dialogo.confirmar_e_fechar()
            mock_aviso.assert_called_once()
            assert dialogo.result() != QDialog.DialogCode.Accepted

    def teste_validacao_aceita_nome_completo(self, qtbot):
        dialogo = DialogoPerfilAutor()
        qtbot.addWidget(dialogo)

        dialogo.edit_nome.setText("Renato Utsch")
        dialogo.confirmar_e_fechar()

        assert dialogo.result() == QDialog.DialogCode.Accepted
        assert dialogo.obter_nome_completo() == "Renato Utsch"
