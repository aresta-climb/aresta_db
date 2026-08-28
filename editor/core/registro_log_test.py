# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
import logging
from pathlib import Path
import pytest

from editor.core.registro_log import (
    obter_logger,
    configurar_logging,
    SanitizingFormatter,
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


def test_configurar_logging_usa_stream_handler():
    logger = configurar_logging()
    assert logger is not None
    assert len(logger.handlers) >= 1
    # Verifica que usa StreamHandler
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)


def test_obter_logger():
    logger1 = obter_logger("modulo_a")
    logger2 = obter_logger("modulo_a")
    assert logger1 is logger2
    assert logger1.name == "aresta_editor.modulo_a"
