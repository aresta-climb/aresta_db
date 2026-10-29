# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

"""Biblioteca pura para validação, formatação e construção de URLs de códigos de sessão em Base36."""

import re

CARACTERES_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
DOMINIO_PREVIA_CANONICO = "https://previa.arestaclimb.com"
PREFIXO_PULL_REQUEST = "pr"
_REGEX_CODIGO_PR = re.compile(r"^pr0*([1-9]\d*)$")


def formatar_codigo(codigo: str) -> str:
    """Formata um código de 8 ou mais caracteres adicionando um hífen após o quarto caractere (ex: k9x2-p83a)."""
    if not isinstance(codigo, str) or len(codigo) < 8:
        raise ValueError("O código deve ter pelo menos 8 caracteres.")
    return f"{codigo[:4]}-{codigo[4:]}"


def normalizar_codigo(codigo: str) -> str:
    """Normaliza o código removendo espaços e hifens e convertendo para minúsculas."""
    if not isinstance(codigo, str):
        raise ValueError("Código inválido: deve ser uma string.")

    limpo = re.sub(r"[\s\-]+", "", codigo).lower()
    if len(limpo) < 8 or not all(c in CARACTERES_BASE36 for c in limpo):
        raise ValueError(f"Código inválido: '{codigo}'.")
    return limpo


def validar_codigo(codigo: str | None) -> bool:
    """Verifica se uma string representa um código de sessão válido (8 ou mais caracteres Base36)."""
    if not isinstance(codigo, str):
        return False
    try:
        normalizar_codigo(codigo)
        return True
    except ValueError:
        return False


def validar_codigo_sessao_editor(codigo: str | None) -> bool:
    """Verifica se o código é válido para uma sessão do Editor Desktop (não iniciada pelo prefixo reservado 'pr')."""
    if not isinstance(codigo, str):
        return False
    try:
        normalizado = normalizar_codigo(codigo)
        return not normalizado.startswith(PREFIXO_PULL_REQUEST)
    except ValueError:
        return False


def gerar_codigo_pull_request(numero_pr: int, formatado: bool = True) -> str:
    """Gera o código para uma Pull Request com zero-padding até 6 dígitos (8 chars) e unbounded acima disso."""
    if isinstance(numero_pr, bool) or not isinstance(numero_pr, int) or numero_pr <= 0:
        raise ValueError("O número da Pull Request deve ser um inteiro positivo.")
    bruto = f"{PREFIXO_PULL_REQUEST}{numero_pr:06d}"
    return formatar_codigo(bruto) if formatado else bruto


def extrair_numero_pull_request(codigo: str | None) -> int | None:
    """Extrai o número inteiro positivo da Pull Request caso o código seja um código de PR válido."""
    if not isinstance(codigo, str):
        return None
    try:
        normalizado = normalizar_codigo(codigo)
    except ValueError:
        return None
    match = _REGEX_CODIGO_PR.match(normalizado)
    if not match:
        return None
    return int(match.group(1))


def eh_codigo_pull_request(codigo: str | None) -> bool:
    """Retorna True se o código pertencer a uma instância de Pull Request."""
    return extrair_numero_pull_request(codigo) is not None


def obter_url_previa(
    codigo: str, base_url: str = DOMINIO_PREVIA_CANONICO, com_hifen: bool = True
) -> str:
    """Retorna a URL canônica de prévia para um determinado código de sessão (com hífen por padrão para legibilidade)."""
    codigo_normalizado = normalizar_codigo(codigo)
    segmento = formatar_codigo(codigo_normalizado) if com_hifen else codigo_normalizado
    return f"{base_url.rstrip('/')}/{segmento}"


def obter_url_resumo_previa(
    codigo: str, base_url: str = DOMINIO_PREVIA_CANONICO, com_hifen: bool = True
) -> str:
    """Retorna a URL do relatório visual de resumo (resumo.html) para uma Pull Request."""
    codigo_normalizado = normalizar_codigo(codigo)
    segmento = formatar_codigo(codigo_normalizado) if com_hifen else codigo_normalizado
    return f"{base_url.rstrip('/')}/resumo/{segmento}"
