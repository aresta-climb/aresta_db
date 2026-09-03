# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para cálculo do tamanho total em bytes dos artefatos de download de um croqui.

Calcula a soma dos tamanhos do arquivo compilado binário (compilado.binarypb)
e das imagens exportadas para uso offline, ignorando pastas intermediárias de
processamento (como raw_mapas).
"""

from pathlib import Path
from typing import Optional, Set, Union


def calcular_tamanho_croqui_bytes(
    caminho_compilado: Union[Path, str],
    pasta_imagens: Optional[Union[Path, str]] = None,
    pastas_excluidas: Optional[Set[str]] = None,
) -> int:
    """
    Calcula o tamanho total em bytes para download offline de um croqui.

    Soma o tamanho do arquivo compilado.binarypb com todas as mídias da
    pasta de imagens, ignorando subdiretórios presentes em pastas_excluidas.

    Argumentos:
        caminho_compilado: Caminho para o arquivo compilado.binarypb.
        pasta_imagens: Caminho para o diretório de imagens do croqui.
        pastas_excluidas: Conjunto de nomes de subdiretórios a serem ignorados (ex: {'raw_mapas'}).

    Retorna:
        Tamanho total em bytes como inteiro.
    """
    tamanho_total = 0

    caminho_pb = Path(caminho_compilado)
    if caminho_pb.is_file():
        tamanho_total += caminho_pb.stat().st_size

    if pasta_imagens is not None:
        caminho_imagens = Path(pasta_imagens)
        if caminho_imagens.is_dir():
            excluidas = pastas_excluidas or set()
            for arquivo in caminho_imagens.rglob("*"):
                if not arquivo.is_file():
                    continue

                # Verifica se algum diretório pai relativo à pasta de imagens está na lista de exclusão
                partes_relativas = arquivo.relative_to(caminho_imagens).parts[:-1]
                if any(parte in excluidas for parte in partes_relativas):
                    continue

                tamanho_total += arquivo.stat().st_size

    return tamanho_total