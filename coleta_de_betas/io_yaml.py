# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from pathlib import Path
from typing import Union
import yaml
from google.protobuf.json_format import MessageToDict, ParseDict
from aresta_api.proto.generated import beta_pb2


def salvar_vias_extraidas_yaml(vias: beta_pb2.ViasExtraidasCroqui, caminho: Union[Path, str]) -> None:
    """
    Serializa uma mensagem ViasExtraidasCroqui para um arquivo YAML formatado.
    """
    caminho_obj = Path(caminho)
    caminho_obj.parent.mkdir(parents=True, exist_ok=True)

    dados_dict = MessageToDict(
        vias,
        always_print_fields_with_no_presence=False,
        preserving_proto_field_name=True
    )

    with open(caminho_obj, "w", encoding="utf-8") as f:
        yaml.dump(dados_dict, f, allow_unicode=True, sort_keys=False)


def carregar_vias_extraidas_yaml(caminho: Union[Path, str]) -> beta_pb2.ViasExtraidasCroqui:
    """
    Lê e desserializa um arquivo YAML no formato ViasExtraidasCroqui com validação estática.
    """
    caminho_obj = Path(caminho)
    with open(caminho_obj, "r", encoding="utf-8") as f:
        dados_dict = yaml.safe_load(f) or {}

    vias = beta_pb2.ViasExtraidasCroqui()
    ParseDict(dados_dict, vias, ignore_unknown_fields=True)
    return vias


def salvar_candidatos_brutos_yaml(candidatos: beta_pb2.BetasPendentes, caminho: Union[Path, str]) -> None:
    """
    Serializa uma mensagem BetasPendentes para um arquivo YAML formatado.
    """
    caminho_obj = Path(caminho)
    caminho_obj.parent.mkdir(parents=True, exist_ok=True)

    dados_dict = MessageToDict(
        candidatos,
        always_print_fields_with_no_presence=False,
        preserving_proto_field_name=True
    )

    with open(caminho_obj, "w", encoding="utf-8") as f:
        yaml.dump(dados_dict, f, allow_unicode=True, sort_keys=False)


def carregar_candidatos_brutos_yaml(caminho: Union[Path, str]) -> beta_pb2.BetasPendentes:
    """
    Lê e desserializa um arquivo YAML no formato BetasPendentes com validação estática.
    """
    caminho_obj = Path(caminho)
    with open(caminho_obj, "r", encoding="utf-8") as f:
        dados_dict = yaml.safe_load(f) or {}

    candidatos = beta_pb2.BetasPendentes()
    ParseDict(dados_dict, candidatos, ignore_unknown_fields=True)
    return candidatos
