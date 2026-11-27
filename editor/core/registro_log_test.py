# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import logging
from pathlib import Path

from editor.core.registro_log import (
    SanitizingFormatter,
    configurar_logging,
    obter_logger,
    obter_logger_raiz_python,
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
        exc_info=None,
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
    assert obter_logger().name == "aresta_editor"


def test_obter_logger_raiz_python():
    raiz = obter_logger_raiz_python()
    assert raiz is logging.getLogger()


def test_safe_stream_handler_ignora_stream_fechado():
    import io

    from editor.core.registro_log import SafeStreamHandler

    stream_fechado = io.StringIO()
    stream_fechado.close()
    handler = SafeStreamHandler(stream_fechado)
    record = logging.LogRecord(
        name="aresta_editor.teste",
        level=logging.INFO,
        pathname="teste.py",
        lineno=1,
        msg="mensagem",
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    handler.handleError(record)
