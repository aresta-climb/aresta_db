# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from editor.core.registro_log import (
    obter_logger,
    configurar_logging,
    SanitizingFormatter
)


def test_sanitizing_formatter():
    user_dir = str(Path.home())
    formatter = SanitizingFormatter("%(levelname)s - %(message)s")
    record = logging.LogRecord(
        name="teste",
        level=logging.INFO,
        pathname="teste.py",
        lineno=10,
        msg=f"Acessando arquivo {user_dir}\\croqui.yaml",
        args=(),
        exc_info=None
    )
    formatado = formatter.format(record)
    assert user_dir not in formatado
    assert "%userprofile%" in formatado or "%appdata%" in formatado


def test_configurar_logging_cria_arquivo_e_rotacao(tmp_path):
    pasta_logs = tmp_path / "logs"
    logger = configurar_logging(pasta_logs=pasta_logs, max_bytes=1024, backup_count=2)
    
    assert logger is not None
    arquivo_log = pasta_logs / "editor.log"
    assert arquivo_log.exists()
    
    # Escreve mensagens no logger
    logger.info("Mensagem de teste de log")
    
    conteudo = arquivo_log.read_text(encoding="utf-8")
    assert "Mensagem de teste de log" in conteudo


def test_obter_logger():
    logger1 = obter_logger("modulo_a")
    logger2 = obter_logger("modulo_a")
    assert logger1 is logger2
    assert logger1.name == "aresta_editor.modulo_a"
