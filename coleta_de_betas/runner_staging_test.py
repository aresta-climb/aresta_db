# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from pathlib import Path
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.io_yaml import salvar_candidatos_brutos_yaml
from coleta_de_betas.runner_staging import converter_yaml_para_staging, executar_cli_salvar_staging
from coleta_de_betas.inteligencia.avaliador import carregar_betas_pendentes


def test_converter_yaml_para_staging(tmp_path: Path):
    """
    Testa a conversão de arquivo YAML avaliado em betas_pendentes.binarypb.
    """
    pico_dir = tmp_path / "br_mg_croqui"
    pico_dir.mkdir()

    yaml_avaliado = pico_dir / "candidatos_avaliados.yaml"
    staging_pb = pico_dir / "betas_pendentes.binarypb"

    pendentes = beta_pb2.BetasPendentes()
    pendentes.id_croqui = "br_mg_croqui"

    cand_esc = pendentes.candidatos_por_escalada.add()
    cand_esc.nome_escalada = "Fusca Azul"
    cand_esc.grau = "V4"
    cand_esc.nome_setor = "Geriatria"

    m = cand_esc.candidatos.add()
    m.url = "https://youtube.com/watch?v=123"
    m.titulo = "Beta Fusca Azul"
    m.fonte = beta_pb2.FonteMidia.YOUTUBE
    m.resultado_llm.llm_confidence_score = 90
    m.resultado_llm.llm_reasoning = "Perfeita correspondência"

    salvar_candidatos_brutos_yaml(pendentes, yaml_avaliado)

    caminho_gerado = converter_yaml_para_staging(yaml_avaliado, staging_pb)
    assert caminho_gerado.exists()

    lido_pb = carregar_betas_pendentes(caminho_gerado)
    assert lido_pb.id_croqui == "br_mg_croqui"
    assert len(lido_pb.candidatos_por_escalada) == 1
    assert lido_pb.candidatos_por_escalada[0].nome_escalada == "Fusca Azul"
    assert lido_pb.candidatos_por_escalada[0].candidatos[0].resultado_llm.llm_confidence_score == 90


def test_executar_cli_salvar_staging(tmp_path: Path):
    """
    Testa o comando CLI de staging salvando betas_pendentes.binarypb.
    """
    pico_dir = tmp_path / "br_mg_croqui"
    pico_dir.mkdir()

    yaml_entrada = pico_dir / "candidatos_brutos.yaml"
    staging_pb = pico_dir / "betas_pendentes.binarypb"

    pendentes = beta_pb2.BetasPendentes()
    pendentes.id_croqui = "br_mg_croqui"
    salvar_candidatos_brutos_yaml(pendentes, yaml_entrada)

    retorno = executar_cli_salvar_staging([str(pico_dir)])
    assert retorno == 0
    assert staging_pb.exists()
