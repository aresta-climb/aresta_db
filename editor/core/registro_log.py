# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from editor.core.telemetria import sanitizar_texto_caminhos


class SanitizingFormatter(logging.Formatter):
    """Formatador de log que sanitiza caminhos absolutos locais para privacidade."""
    def format(self, record: logging.LogRecord) -> str:
        mensagem_original = super().format(record)
        return sanitizar_texto_caminhos(mensagem_original)


def _obter_pasta_padrao_logs() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "ArestaEditor" / "logs"
    return Path.home() / ".aresta_editor" / "logs"


def configurar_logging(
    pasta_logs: Path | str | None = None,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    nivel: int = logging.INFO
) -> logging.Logger:
    """
    Configura o sistema de logging do editor com rotação de arquivos e saída em console.
    """
    diretorio = Path(pasta_logs) if pasta_logs else _obter_pasta_padrao_logs()
    diretorio.mkdir(parents=True, exist_ok=True)
    
    arquivo_log = diretorio / "editor.log"
    
    logger_raiz = logging.getLogger("aresta_editor")
    logger_raiz.setLevel(nivel)
    
    # Remove handlers antigos para evitar duplicação em reconfigurações
    for handler in list(logger_raiz.handlers):
        logger_raiz.removeHandler(handler)
        
    formato = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    formatter = SanitizingFormatter(formato, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Handler em arquivo com rotação
    file_handler = RotatingFileHandler(
        arquivo_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger_raiz.addHandler(file_handler)
    
    # Handler de console (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
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
