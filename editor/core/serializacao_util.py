# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitários de sanitização, serialização YAML e escrita condicional em LF.
"""

from pathlib import Path
from typing import Any

import yaml


def representar_string_yaml(
    dumper: yaml.representer.SafeRepresenter, dados: str
) -> yaml.ScalarNode:
    """
    Representa strings no PyYAML usando bloco literal ('|') para multilinhas
    e aspas simples ("'") para strings puramente numéricas (positivas ou negativas).
    """
    if "\n" in dados:
        return dumper.represent_scalar("tag:yaml.org,2002:str", dados, style="|")
    if dados.isdigit() or (dados.startswith("-") and dados[1:].isdigit()):
        return dumper.represent_scalar("tag:yaml.org,2002:str", dados, style="'")
    return dumper.represent_scalar("tag:yaml.org,2002:str", dados)


def configurar_yaml_representer() -> None:
    """
    Registra o representer unificado de strings tanto no yaml.Dumper quanto no yaml.SafeDumper.
    """
    yaml.add_representer(str, representar_string_yaml, Dumper=yaml.Dumper)
    yaml.add_representer(str, representar_string_yaml, Dumper=yaml.SafeDumper)


def escrever_texto_se_modificado(
    caminho: Path | str,
    conteudo: str,
    *,
    forcar_lf_no_disco: bool = False,
) -> bool:
    """
    Escreve conteúdo textual em UTF-8 com quebras de linha LF ('\\n') apenas se
    o conteúdo normalizado tiver mudado em relação ao arquivo existente no disco.

    Args:
        caminho: Caminho do arquivo de destino.
        conteudo: Conteúdo textual a ser gravado.
        forcar_lf_no_disco: Se True, também regrava caso o arquivo no disco possua '\\r\\n'.

    Returns:
        True se o arquivo foi escrito/atualizado no disco, False se foi mantido intacto.
    """
    alvo = Path(caminho)
    conteudo_lf = conteudo.replace("\r\n", "\n")

    if alvo.exists():
        try:
            bytes_atuais = alvo.read_bytes()
            texto_atual = bytes_atuais.decode("utf-8")
            if texto_atual.replace("\r\n", "\n") == conteudo_lf:
                if not forcar_lf_no_disco or b"\r\n" not in bytes_atuais:
                    return False
        except UnicodeDecodeError:
            pass

    alvo.parent.mkdir(parents=True, exist_ok=True)
    with open(alvo, "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo_lf)
    return True


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

