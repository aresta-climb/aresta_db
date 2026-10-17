# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para leitura e escrita de arquivos Markdown com cabeçalho YAML Frontmatter.
"""

import re
from pathlib import Path
from typing import Any

import yaml


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

    match = re.match(r"^---\s*\r?\n(?:(.*?)\r?\n)?---\s*(?:\r?\n(.*))?$", conteudo, re.DOTALL)
    if match:
        bloco_frontmatter = match.group(1)
        if bloco_frontmatter and bloco_frontmatter.strip():
            try:
                frontmatter: dict[str, Any] | None = yaml.safe_load(bloco_frontmatter)
            except yaml.YAMLError as e:
                if lancar_erro_yaml:
                    raise ValueError(f"Erro de YAML no frontmatter de {caminho_arquivo}:\n{e}")
                frontmatter = {}
        else:
            frontmatter = None
        corpo = (match.group(2) or "").strip()
        return frontmatter, corpo
    return None, conteudo.strip()


def salvar_md_com_frontmatter(
    md_path: str | Path, frontmatter: dict[str, Any] | None, corpo: str
) -> None:
    """
    Salva o YAML Frontmatter e o corpo de volta no arquivo markdown especificado.

    Inclui automaticamente os identificadores de licença ODbL-1.0 e copyright
    da comunidade no topo do cabeçalho YAML.
    """
    from editor.core.serializacao_util import (
        configurar_yaml_representer,
        escrever_texto_se_modificado,
    )

    configurar_yaml_representer()
    partes: list[str] = []
    if frontmatter:
        bloco_yaml = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
        partes.append(
            "---\n"
            "# SPDX-License-Identifier: ODbL-1.0\n"
            "# Copyright (C) 2026 Aresta Climb Contributors\n" + bloco_yaml + "---\n\n"
        )
    partes.append(corpo)
    escrever_texto_se_modificado(md_path, "".join(partes))

