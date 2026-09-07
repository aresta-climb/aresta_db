# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from typing import Any
import conftest


class TestConftestTeardown(unittest.TestCase):
    def test_pytest_sessionfinish_executa_limpeza_qapplication_quando_existir(self) -> None:
        """
        Valida que o teardown do pytest encerra janelas ativas e processa eventos pendentes
        da QApplication antes da finalização do CPython, prevenindo falhas de Access Violation no Windows.
        """
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QThreadPool
        mock_app = MagicMock(spec=QApplication)
        mock_pool = MagicMock(spec=QThreadPool)
        mock_session = MagicMock()
        mock_config = MagicMock()
        mock_session.config = mock_config

        with patch("PySide6.QtWidgets.QApplication.instance", return_value=mock_app), \
             patch("PySide6.QtCore.QThreadPool.globalInstance", return_value=mock_pool), \
             patch("shiboken6.delete") as mock_shiboken_delete:
            conftest.pytest_sessionfinish(mock_session, 0)
            mock_app.closeAllWindows.assert_called_once()
            mock_app.processEvents.assert_called_once()
            mock_pool.waitForDone.assert_called_once_with(1000)
            mock_shiboken_delete.assert_called_once_with(mock_app)
            self.assertEqual(getattr(mock_config, "_aresta_exitstatus", None), 0)

    def test_pytest_sessionfinish_ignora_quando_sem_qapplication(self) -> None:
        """Valida que o teardown conclui sem erros quando nenhuma QApplication estiver instanciada."""
        mock_session = MagicMock()
        with patch("PySide6.QtWidgets.QApplication.instance", return_value=None), \
             patch("PySide6.QtCore.QThreadPool.globalInstance", return_value=None):
            conftest.pytest_sessionfinish(mock_session, 0)

    def test_pytest_sessionfinish_trata_excecoes_graciosamente(self) -> None:
        """Valida que falhas inesperadas no teardown não quebram o encerramento do teste."""
        with patch("PySide6.QtWidgets.QApplication.instance", side_effect=RuntimeError("Erro simulado")):
            conftest.pytest_sessionfinish(None, 0)

    def test_pytest_unconfigure_executa_fast_exit_em_ambiente_ci(self) -> None:
        """Valida que no CI o processo encerra via os._exit para contornar crash de teardown de DLLs."""
        mock_config = MagicMock()
        mock_config._aresta_exitstatus = 0

        with patch.dict(os.environ, {"CI": "true"}), \
             patch("faulthandler.disable") as mock_fh_disable, \
             patch("sys.stdout.flush") as mock_stdout_flush, \
             patch("sys.stderr.flush") as mock_stderr_flush, \
             patch("os._exit") as mock_exit:
            conftest.pytest_unconfigure(mock_config)
            mock_fh_disable.assert_called_once()
            mock_stdout_flush.assert_called_once()
            mock_stderr_flush.assert_called_once()
            mock_exit.assert_called_once_with(0)

    def test_pytest_unconfigure_preserva_status_de_falha_no_fast_exit(self) -> None:
        """Valida que status de falha do pytest (ex: 1) é repassado ao os._exit."""
        mock_config = MagicMock()
        mock_config._aresta_exitstatus = 1

        with patch.dict(os.environ, {"ARESTA_FAST_EXIT": "1"}, clear=False), \
             patch("faulthandler.disable"), \
             patch("sys.stdout.flush"), \
             patch("sys.stderr.flush"), \
             patch("os._exit") as mock_exit:
            conftest.pytest_unconfigure(mock_config)
            mock_exit.assert_called_once_with(1)

    def test_pytest_unconfigure_nao_executa_exit_fora_do_ci(self) -> None:
        """Valida que fora do CI/ARESTA_FAST_EXIT o os._exit não é invocado."""
        mock_config = MagicMock()
        with patch.dict(os.environ, {"CI": "", "ARESTA_FAST_EXIT": ""}, clear=False), \
             patch("os._exit") as mock_exit:
            conftest.pytest_unconfigure(mock_config)
            mock_exit.assert_not_called()
