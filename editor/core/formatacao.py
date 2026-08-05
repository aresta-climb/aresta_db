# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import unicodedata
import re

def remover_acentos(texto):
    """Remove acentos de uma string."""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def para_snake_case(texto):
    """Converte texto para snake_case (minúsculas, espaços e sublinhados por sublinhados)."""
    texto = remover_acentos(texto).lower()
    # Remove caracteres especiais exceto espaços, sublinhados e alfanuméricos
    texto = re.sub(r'[^a-z0-9\s_]', '', texto)
    # Substitui espaços ou hífens por sublinhados
    texto = re.sub(r'[\s\-]+', '_', texto.strip())
    # Garante que não temos múltiplos sublinhados seguidos
    texto = re.sub(r'_+', '_', texto)
    return texto


def para_camel_case(texto):
    """Converte texto para CamelCase (iniciais maiúsculas, sem espaços)."""
    texto = remover_acentos(texto)
    # Remove caracteres especiais exceto espaços e alfanuméricos
    texto = re.sub(r'[^a-zA-Z0-9\s]', '', texto)
    palavras = texto.strip().split()
    return "".join(p.capitalize() for p in palavras)

def para_id_croqui(texto):
    """Normalização genérica para partes do ID (snake_case)."""
    return para_snake_case(texto)
