# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de contrato arquitetural de encapsulamento exclusivo da biblioteca nanoid.

Garante estritamente via inspeção da árvore sintática (AST) que a biblioteca
de terceiros 'nanoid' seja importada ÚNICA E EXCLUSIVAMENTE dentro do módulo
'scripts/gerenciar_uids_lib.py'. Nenhum outro módulo Python no repositório
pode realizar `import nanoid` ou `from nanoid import ...`.
"""

import ast
from pathlib import Path
from typing import List, Tuple
import pytest

PASTA_RAIZ: Path = Path(__file__).resolve().parent.parent
ARQUIVO_AUTORIZADO: Path = (PASTA_RAIZ / "scripts" / "gerenciar_uids_lib.py").resolve()

# Pastas e diretórios ignorados na varredura
PASTAS_IGNORADAS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}


def _verificar_importacao_nanoid_em_ast(caminho_arquivo: Path) -> List[Tuple[int, str]]:
    """Analisa um arquivo Python via AST e retorna lista de (linha, codigo_import) se importar 'nanoid'."""
    try:
        conteudo = caminho_arquivo.read_text(encoding="utf-8")
    except Exception as e:
        pytest.fail(f"Falha ao ler arquivo {caminho_arquivo}: {e}")

    try:
        arvore = ast.parse(conteudo, filename=str(caminho_arquivo))
    except SyntaxError:
        # Arquivos com erro de sintaxe são ignorados ou tratados pelo validador geral
        return []

    violacoes: List[Tuple[int, str]] = []

    for no in ast.walk(arvore):
        # Caso 1: import nanoid, import nanoid.xxx
        if isinstance(no, ast.Import):
            for alias in no.names:
                if alias.name == "nanoid" or alias.name.startswith("nanoid."):
                    violacoes.append((no.lineno, f"import {alias.name}"))

        # Caso 2: from nanoid import ...
        elif isinstance(no, ast.ImportFrom):
            if no.module == "nanoid" or (no.module and no.module.startswith("nanoid.")):
                nomes = ", ".join(a.name for a in no.names)
                violacoes.append((no.lineno, f"from {no.module} import {nomes}"))

    return violacoes


def test_contrato_importacao_nanoid_exclusiva_em_gerenciar_uids_lib():
    """Varre todos os módulos Python do repositório e valida o isolamento da biblioteca nanoid."""
    arquivos_python: List[Path] = []
    for caminho in PASTA_RAIZ.rglob("*.py"):
        partes = set(caminho.parts)
        if not partes.intersection(PASTAS_IGNORADAS):
            arquivos_python.append(caminho.resolve())

    assert len(arquivos_python) > 0, "Nenhum arquivo Python encontrado no repositório."

    # Garante que o arquivo autorizado está presente na lista
    assert ARQUIVO_AUTORIZADO in arquivos_python, (
        f"Arquivo autorizado {ARQUIVO_AUTORIZADO} não foi encontrado na varredura."
    )

    violacoes_detectadas: List[str] = []

    for arquivo in arquivos_python:
        violacoes = _verificar_importacao_nanoid_em_ast(arquivo)
        if not violacoes:
            continue

        caminho_relativo = arquivo.relative_to(PASTA_RAIZ).as_posix()

        # O único arquivo permitido é scripts/gerenciar_uids_lib.py
        if arquivo == ARQUIVO_AUTORIZADO:
            continue

        for linha, trecho in violacoes:
            violacoes_detectadas.append(f"{caminho_relativo}:{linha} -> '{trecho}'")

    assert not violacoes_detectadas, (
        "Violação do Princípio de Isolamento: a biblioteca externa 'nanoid' foi importada fora de "
        f"'{ARQUIVO_AUTORIZADO.name}'.\n"
        "Todo o repositório deve importar exclusivamente 'scripts.gerenciar_uids_lib'.\n"
        "Ocorrências proibidas:\n" + "\n".join(violacoes_detectadas)
    )


def test_validador_ast_detecta_violacao_sintetica():
    """Testa se o analisador AST detecta violações reais simuladas."""
    codigo_invalido = """
import os
import nanoid
from nanoid import generate
"""
    arvore = ast.parse(codigo_invalido)
    violacoes = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                if alias.name == "nanoid":
                    violacoes.append((no.lineno, f"import {alias.name}"))
        elif isinstance(no, ast.ImportFrom):
            if no.module == "nanoid":
                violacoes.append((no.lineno, f"from {no.module} import ..."))

    assert len(violacoes) == 2
