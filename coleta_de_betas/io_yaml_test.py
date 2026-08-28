# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from pathlib import Path
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.io_yaml import (
    salvar_vias_extraidas_yaml,
    carregar_vias_extraidas_yaml,
    salvar_candidatos_brutos_yaml,
    carregar_candidatos_brutos_yaml,
)


def test_vias_extraidas_yaml_roundtrip(tmp_path: Path):
    """
    Testa a serialização e desserialização de ViasExtraidasCroqui para YAML.
    """
    arquivo_yaml = tmp_path / "vias_extraidas.yaml"

    vias_orig = beta_pb2.ViasExtraidasCroqui()
    vias_orig.id_croqui = "br_mg_ouro_preto_ouroboulder"
    vias_orig.nome_croqui = "Ouroboulder"
    vias_orig.cidade = "Ouro Preto"
    vias_orig.estado = "MG"
    vias_orig.pais = "Brasil"

    esc = vias_orig.escaladas.add()
    esc.id_escalada = "1"
    esc.nome = "Fusca Azul"
    esc.grau = "V4"
    esc.tipo = "boulder"
    esc.nome_setor = "Geriatria"
    esc.nome_grupo = "Setor Principal"
    esc.nome_pico = "São Sebastião"
    esc.cidade = "Ouro Preto"
    esc.estado = "MG"
    esc.arquivo_origem = "grupo_1_setor_1.md"

    salvar_vias_extraidas_yaml(vias_orig, arquivo_yaml)
    assert arquivo_yaml.exists()

    # Valida conteúdo em texto do YAML gerado
    conteudo = arquivo_yaml.read_text(encoding="utf-8")
    assert "Fusca Azul" in conteudo
    assert "Ouro Preto" in conteudo

    vias_lidas = carregar_vias_extraidas_yaml(arquivo_yaml)
    assert vias_lidas.id_croqui == "br_mg_ouro_preto_ouroboulder"
    assert len(vias_lidas.escaladas) == 1
    assert vias_lidas.escaladas[0].nome == "Fusca Azul"
    assert vias_lidas.escaladas[0].grau == "V4"
    assert vias_lidas.escaladas[0].nome_setor == "Geriatria"
    assert vias_lidas.escaladas[0].nome_grupo == "Setor Principal"


def test_candidatos_brutos_yaml_roundtrip(tmp_path: Path):
    """
    Testa a serialização e desserialização de BetasPendentes para YAML.
    """
    arquivo_yaml = tmp_path / "candidatos_brutos.yaml"

    pendentes_orig = beta_pb2.BetasPendentes()
    pendentes_orig.id_croqui = "br_mg_ouro_preto_ouroboulder"

    cand_esc = pendentes_orig.candidatos_por_escalada.add()
    cand_esc.nome_escalada = "Fusca Azul"
    cand_esc.grau = "V4"
    cand_esc.nome_setor = "Geriatria"
    cand_esc.nome_grupo = "Setor Principal"
    cand_esc.cidade = "Ouro Preto"
    cand_esc.estado = "MG"

    m = cand_esc.candidatos.add()
    m.url = "https://youtube.com/watch?v=123"
    m.titulo = "Mandando Fusca Azul V4"
    m.thumbnail_url = "https://img.youtube.com/vi/123/hqdefault.jpg"
    m.fonte = beta_pb2.FonteMidia.YOUTUBE
    m.match_multiplas_fontes = True
    m.match_nome_no_snippet = True
    m.snippets.append("Vídeo no setor Geriatria")

    salvar_candidatos_brutos_yaml(pendentes_orig, arquivo_yaml)
    assert arquivo_yaml.exists()

    pendentes_lidos = carregar_candidatos_brutos_yaml(arquivo_yaml)
    assert pendentes_lidos.id_croqui == "br_mg_ouro_preto_ouroboulder"
    assert len(pendentes_lidos.candidatos_por_escalada) == 1
    assert pendentes_lidos.candidatos_por_escalada[0].nome_escalada == "Fusca Azul"
    assert pendentes_lidos.candidatos_por_escalada[0].grau == "V4"
    assert len(pendentes_lidos.candidatos_por_escalada[0].candidatos) == 1

    cand = pendentes_lidos.candidatos_por_escalada[0].candidatos[0]
    assert cand.url == "https://youtube.com/watch?v=123"
    assert cand.fonte == beta_pb2.FonteMidia.YOUTUBE
    assert cand.match_multiplas_fontes is True
    assert cand.snippets[0] == "Vídeo no setor Geriatria"
