# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

"""Biblioteca pura para validação, formatação e construção de URLs de códigos de sessão em Base36."""

import re
from typing import Optional

CARACTERES_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
DOMINIO_PREVIA_CANONICO = "https://previa.arestaclimb.com"


def formatar_codigo(codigo: str) -> str:
    """Formata um código de 8 caracteres adicionando um hífen no meio (ex: k9x2-p83a)."""
    if not isinstance(codigo, str) or len(codigo) != 8:
        raise ValueError("O código deve ter exatamente 8 caracteres.")
    return f"{codigo[:4]}-{codigo[4:]}"


def normalizar_codigo(codigo: str) -> str:
    """Normaliza o código removendo espaços e hifens e convertendo para minúsculas."""
    if not isinstance(codigo, str):
        raise ValueError("Código inválido: deve ser uma string.")
    
    limpo = re.sub(r"[\s\-]+", "", codigo).lower()
    if len(limpo) != 8 or not all(c in CARACTERES_BASE36 for c in limpo):
        raise ValueError(f"Código inválido: '{codigo}'.")
    return limpo


def validar_codigo(codigo: Optional[str]) -> bool:
    """Verifica se uma string representa um código de sessão válido (com ou sem hifens/espaços)."""
    if not isinstance(codigo, str):
        return False
    try:
        normalizar_codigo(codigo)
        return True
    except ValueError:
        return False


def obter_url_previa(codigo: str, base_url: str = DOMINIO_PREVIA_CANONICO, com_hifen: bool = True) -> str:
    """Retorna a URL canônica de prévia para um determinado código de sessão (com hífen por padrão para legibilidade)."""
    codigo_normalizado = normalizar_codigo(codigo)
    segmento = formatar_codigo(codigo_normalizado) if com_hifen else codigo_normalizado
    return f"{base_url.rstrip('/')}/{segmento}"
