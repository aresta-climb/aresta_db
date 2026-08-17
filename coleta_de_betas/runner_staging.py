# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import sys
import argparse
from pathlib import Path
from typing import List, Union, Optional
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.io_yaml import carregar_candidatos_brutos_yaml


def converter_yaml_para_staging(
    caminho_yaml: Union[Path, str],
    caminho_binarypb: Optional[Union[Path, str]] = None
) -> Path:
    """
    Lê o arquivo YAML de candidatos e grava no formato Protobuf binário (betas_pendentes.binarypb).
    """
    caminho_yaml_obj = Path(caminho_yaml)
    if not caminho_yaml_obj.exists():
        raise FileNotFoundError(f"Arquivo YAML não encontrado: {caminho_yaml}")

    pendentes = carregar_candidatos_brutos_yaml(caminho_yaml_obj)

    if caminho_binarypb is None:
        caminho_destino = caminho_yaml_obj.parent / "betas_pendentes.binarypb"
    else:
        caminho_destino = Path(caminho_binarypb)

    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_destino, "wb") as f:
        f.write(pendentes.SerializeToString())

    return caminho_destino


def executar_cli_salvar_staging(argv: List[str] = None) -> int:
    """Ponto de entrada CLI para conversão de YAML para staging binário."""
    parser = argparse.ArgumentParser(
        description="Converte candidatos_brutos.yaml (ou arquivo avaliado) no arquivo binário betas_pendentes.binarypb."
    )
    parser.add_argument(
        "croqui_dir",
        type=str,
        help="Caminho para o diretório do croqui (ex: database/br_mg_ouro_preto_ouroboulder)"
    )
    parser.add_argument(
        "-i", "--entrada",
        type=str,
        default="",
        help="Caminho opcional do arquivo YAML de entrada (padrão: <croqui_dir>/candidatos_brutos.yaml)"
    )
    parser.add_argument(
        "-o", "--saida",
        type=str,
        default="",
        help="Caminho opcional de saída do binarypb (padrão: <croqui_dir>/betas_pendentes.binarypb)"
    )

    args = parser.parse_args(argv)
    pico_dir = Path(args.croqui_dir)
    if not pico_dir.exists() or not pico_dir.is_dir():
        print(f"Erro: Diretório de croqui inválido ou não encontrado: {args.croqui_dir}", file=sys.stderr)
        return 1

    caminho_entrada = Path(args.entrada) if args.entrada else pico_dir / "candidatos_brutos.yaml"
    caminho_saida = Path(args.saida) if args.saida else pico_dir / "betas_pendentes.binarypb"

    try:
        gerado = converter_yaml_para_staging(caminho_entrada, caminho_saida)
        print(f"Sucesso: Arquivo de staging salvo em {gerado}")
        return 0
    except Exception as e:
        print(f"Erro ao salvar staging: {e}", file=sys.stderr)
        return 1
