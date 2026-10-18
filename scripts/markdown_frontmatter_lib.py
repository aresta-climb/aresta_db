# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para leitura e escrita de arquivos Markdown com cabeçalho YAML Frontmatter.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from editor.core.serializacao_util import (
    carregar_yaml,
    escrever_texto_se_modificado,
    serializar_yaml,
)


def parse_texto_md_com_frontmatter(
    conteudo: str,
    caminho_origem: str | Path = "<memoria>",
    lancar_erro_yaml: bool = False,
) -> tuple[dict[str, Any] | None, str]:
    """
    Separa o YAML Frontmatter do conteúdo textual a partir de uma string já carregada em memória.
    """
    match = re.match(r"^---\s*\r?\n(?:(.*?)\r?\n)?---\s*(?:\r?\n(.*))?$", conteudo, re.DOTALL)
    if match:
        bloco_frontmatter = match.group(1)
        if bloco_frontmatter and bloco_frontmatter.strip():
            try:
                frontmatter: dict[str, Any] | None = carregar_yaml(bloco_frontmatter)
            except yaml.YAMLError as e:
                if lancar_erro_yaml:
                    raise ValueError(f"Erro de YAML no frontmatter de {caminho_origem}:\n{e}")
                frontmatter = {}
        else:
            frontmatter = None
        corpo = (match.group(2) or "").strip()
        return frontmatter, corpo
    return None, conteudo.strip()


def parse_md_com_frontmatter(
    caminho_arquivo: str | Path,
    lancar_erro_yaml: bool = False,
) -> tuple[dict[str, Any] | None, str]:
    """
    Lê um arquivo Markdown e separa o YAML Frontmatter do conteúdo textual.

    Retorna uma tupla (frontmatter, corpo). Se não houver bloco de frontmatter,
    retorna (None, corpo). Em caso de erro de sintaxe YAML, se lancar_erro_yaml for True,
    levanta ValueError; caso contrário, retorna ({}, corpo).
    """
    try:
        with open(caminho_arquivo, encoding="utf-8") as f:
            conteudo = f.read()
    except Exception as e:
        raise RuntimeError(f"Erro ao ler arquivo: {caminho_arquivo}. Erro: {e}")

    return parse_texto_md_com_frontmatter(
        conteudo,
        caminho_origem=caminho_arquivo,
        lancar_erro_yaml=lancar_erro_yaml,
    )


def salvar_md_com_frontmatter(
    md_path: str | Path, frontmatter: dict[str, Any] | None, corpo: str
) -> bool:
    """
    Salva o YAML Frontmatter e o corpo de volta no arquivo markdown especificado.

    Inclui automaticamente os identificadores de licença ODbL-1.0 e copyright
    da comunidade no topo do cabeçalho YAML. Retorna True se o arquivo foi
    efetivamente gravado/modificado no disco, False se já estava idêntico.
    """
    partes: list[str] = []
    if frontmatter:
        bloco_yaml = serializar_yaml(frontmatter, incluir_cabecalho_spdx=True)
        partes.append(f"---\n{bloco_yaml}---\n\n")
    partes.append(corpo)
    return escrever_texto_se_modificado(md_path, "".join(partes))
