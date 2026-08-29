# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any
import logging
import sys

from editor.core.telemetria import sanitizar_texto_caminhos


class SanitizingFormatter(logging.Formatter):
    """Formatador de log que sanitiza caminhos absolutos locais para privacidade."""
    def format(self, record: logging.LogRecord) -> str:
        mensagem_original = super().format(record)
        return sanitizar_texto_caminhos(mensagem_original)


class SafeStreamHandler(logging.StreamHandler[Any]):

    """StreamHandler seguro que evita falhas se o stream for fechado durante shutdown ou testes."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except (ValueError, OSError):
            pass

    def handleError(self, record: logging.LogRecord) -> None:
        # Silencia erros de stream fechado
        pass


def configurar_logging(nivel: int = logging.INFO) -> logging.Logger:
    """
    Configura o sistema de logging do editor com saída sanitizada em console.
    O Sentry SDK captura os breadcrumbs automaticamente da hierarquia de log em memória.
    """
    logger_raiz = logging.getLogger("aresta_editor")
    logger_raiz.setLevel(nivel)
    
    # Remove handlers antigos para evitar duplicação em reconfigurações
    for handler in list(logger_raiz.handlers):
        logger_raiz.removeHandler(handler)
        
    formato = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    formatter = SanitizingFormatter(formato, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Handler de console (stdout) com sanitização de privacidade
    stream_handler = SafeStreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger_raiz.addHandler(stream_handler)
    
    return logger_raiz



# Inicialização padrão do logger global
logger = configurar_logging()


def obter_logger(nome: str = "") -> logging.Logger:
    """Retorna um logger filho hierárquico sob o namespace aresta_editor."""
    if not nome or nome == "aresta_editor":
        return logging.getLogger("aresta_editor")
    return logging.getLogger(f"aresta_editor.{nome}")
