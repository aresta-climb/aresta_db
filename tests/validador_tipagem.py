# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import ast
import os
from typing import Sequence
from mypy import api


def executar_verificacao_mypy(
    caminhos: Sequence[str],
    config_path: str | None = None,
) -> tuple[int, str, str]:
    """
    Executa o MyPy programaticamente sobre os caminhos fornecidos.

    Retorna uma tupla contendo (codigo_saida, stdout, stderr).
    """
    argumentos: list[str] = list(caminhos)
    if config_path and os.path.exists(config_path):
        argumentos.insert(0, f"--config-file={config_path}")

    stdout, stderr, codigo_saida = api.run(argumentos)
    return codigo_saida, stdout, stderr


def verificar_anotacoes_ast(codigo_fonte: str) -> list[str]:
    """
    Inspeciona o código-fonte via AST para assegurar que todas as funções
    e métodos possuem anotações de tipos nos parâmetros e tipo de retorno.

    Retorna uma lista de strings descrevendo quaisquer ausências de anotações.
    """
    arvore = ast.parse(codigo_fonte)
    erros: list[str] = []

    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nome_funcao = no.name

            # Verifica parâmetros posicionais e nomeados
            todos_args = (
                no.args.posonlyargs
                + no.args.args
                + no.args.kwonlyargs
            )

            for arg in todos_args:
                # Ignora o primeiro argumento convencional de métodos de classe e instância
                if arg.arg in ("self", "cls"):
                    continue
                if arg.annotation is None:
                    erros.append(
                        f"Função/método '{nome_funcao}' (linha {no.lineno}): "
                        f"parâmetro '{arg.arg}' não possui anotação de tipo."
                    )

            if no.args.vararg and no.args.vararg.annotation is None:
                erros.append(
                    f"Função/método '{nome_funcao}' (linha {no.lineno}): "
                    f"parâmetro *{no.args.vararg.arg} não possui anotação de tipo."
                )

            if no.args.kwarg and no.args.kwarg.annotation is None:
                erros.append(
                    f"Função/método '{nome_funcao}' (linha {no.lineno}): "
                    f"parâmetro **{no.args.kwarg.arg} não possui anotação de tipo."
                )

            # Verifica retorno
            if no.returns is None:
                erros.append(
                    f"Função/método '{nome_funcao}' (linha {no.lineno}): "
                    f"não possui anotação de tipo de retorno (ex: -> None ou -> Tipo)."
                )

    return erros


def verificar_arquivo_ast(caminho_arquivo: str) -> list[str]:
    """Lê um arquivo Python do disco e valida suas anotações via AST."""
    with open(caminho_arquivo, "r", encoding="utf-8-sig") as f:
        conteudo = f.read()
    return verificar_anotacoes_ast(conteudo)
