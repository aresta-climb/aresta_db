# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from google.protobuf.json_format import MessageToDict, ParseDict

from aresta_api.proto.generated import beta_pb2
from editor.core.serializacao_util import (
    carregar_yaml,
    escrever_texto_se_modificado,
    serializar_yaml,
)


def salvar_vias_extraidas_yaml(vias: beta_pb2.ViasExtraidasCroqui, caminho: Path | str) -> None:
    """
    Serializa uma mensagem ViasExtraidasCroqui para um arquivo YAML formatado.
    """
    caminho_obj = Path(caminho)
    dados_dict = MessageToDict(
        vias, always_print_fields_with_no_presence=False, preserving_proto_field_name=True
    )
    escrever_texto_se_modificado(
        caminho_obj,
        serializar_yaml(dados_dict, incluir_cabecalho_spdx=False),
    )


def carregar_vias_extraidas_yaml(caminho: Path | str) -> beta_pb2.ViasExtraidasCroqui:
    """
    Lê e desserializa um arquivo YAML no formato ViasExtraidasCroqui com validação estática.
    """
    caminho_obj = Path(caminho)
    dados_dict = carregar_yaml(caminho_obj.read_text(encoding="utf-8")) or {}

    vias = beta_pb2.ViasExtraidasCroqui()
    ParseDict(dados_dict, vias, ignore_unknown_fields=True)
    return vias


def salvar_candidatos_brutos_yaml(candidatos: beta_pb2.BetasPendentes, caminho: Path | str) -> None:
    """
    Serializa uma mensagem BetasPendentes para um arquivo YAML formatado.
    """
    caminho_obj = Path(caminho)
    dados_dict = MessageToDict(
        candidatos, always_print_fields_with_no_presence=False, preserving_proto_field_name=True
    )
    escrever_texto_se_modificado(
        caminho_obj,
        serializar_yaml(dados_dict, incluir_cabecalho_spdx=False),
    )


def carregar_candidatos_brutos_yaml(caminho: Path | str) -> beta_pb2.BetasPendentes:
    """
    Lê e desserializa um arquivo YAML no formato BetasPendentes com validação estática.
    """
    caminho_obj = Path(caminho)
    dados_dict = carregar_yaml(caminho_obj.read_text(encoding="utf-8")) or {}

    candidatos = beta_pb2.BetasPendentes()
    ParseDict(dados_dict, candidatos, ignore_unknown_fields=True)
    return candidatos
