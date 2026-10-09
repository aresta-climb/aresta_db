# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitários de sanitização e manipulação de dicionários para serialização do editor.
"""

from typing import Any


def sanitizar_dicionario_sem_extensoes(dados: Any) -> Any:
    """
    Remove recursivamente chaves de extensões Protobuf ou shadow state de dicionários e listas.

    Garante que chaves de extensões serializadas pelo Protobuf (ex: '[aresta.ArquivoMapas.ext_metadados_arquivo]')
    ou que contenham referências a 'ext_metadados' sejam completamente removidas antes
    da persistência em arquivos YAML ou Markdown com frontmatter.

    Args:
        dados: Objeto a ser sanitizado (dicionário, lista ou tipo primitivo).

    Returns:
        Nova estrutura de dados sem as chaves de extensão de shadow state.
    """
    if isinstance(dados, dict):
        novo_dict = {}
        for chave, valor in dados.items():
            if isinstance(chave, str):
                if chave.startswith("[") or "ext_metadados" in chave:
                    continue
            novo_dict[chave] = sanitizar_dicionario_sem_extensoes(valor)
        return novo_dict
    elif isinstance(dados, list):
        return [sanitizar_dicionario_sem_extensoes(item) for item in dados]
    return dados
