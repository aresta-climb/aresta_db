# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.runner_busca import buscar_candidatos_para_croqui, executar_cli_buscar
from coleta_de_betas.io_yaml import salvar_vias_extraidas_yaml


def test_buscar_candidatos_para_croqui():
    """
    Testa o processamento de busca a partir de ViasExtraidasCroqui com extratores mockados.
    """
    vias = beta_pb2.ViasExtraidasCroqui()
    vias.id_croqui = "br_mg_croqui"
    vias.cidade = "Ouro Preto"
    vias.estado = "MG"

    via1 = vias.escaladas.add()
    via1.nome = "Fusca Azul"
    via1.grau = "V4"
    via1.nome_setor = "Geriatria"
    via1.nome_grupo = "Principal"
    via1.nome_pico = "Pico A"
    via1.cidade = "Ouro Preto"
    via1.estado = "MG"

    # Mock de extrator 1 (YouTube)
    m1 = beta_pb2.MidiaBeta()
    m1.url = "https://youtube.com/watch?v=123"
    m1.titulo = "Mandando Fusca Azul"
    m1.fonte = beta_pb2.FonteMidia.YOUTUBE
    m1.snippets.append("Vídeo de beta")

    mock_yt = MagicMock()
    mock_yt.buscar.return_value = [m1]

    # Mock de extrator 2 (DuckDuckGo)
    m2 = beta_pb2.MidiaBeta()
    m2.url = "https://instagram.com/p/abc"
    m2.titulo = "Post Fusca Azul"
    m2.fonte = beta_pb2.FonteMidia.INSTAGRAM
    m2.snippets.append("Post no insta")

    mock_ddg = MagicMock()
    mock_ddg.buscar.return_value = [m2]

    resultado_pendentes = buscar_candidatos_para_croqui(vias, extratores=[mock_yt, mock_ddg])

    assert resultado_pendentes.id_croqui == "br_mg_croqui"
    assert len(resultado_pendentes.candidatos_por_escalada) == 1
    
    cand_esc = resultado_pendentes.candidatos_por_escalada[0]
    assert cand_esc.nome_escalada == "Fusca Azul"
    assert cand_esc.grau == "V4"
    assert cand_esc.nome_setor == "Geriatria"
    assert cand_esc.nome_grupo == "Principal"
    assert len(cand_esc.candidatos) == 2


def test_executar_cli_buscar(tmp_path: Path):
    """
    Testa a execução do comando CLI de busca consumindo vias_extraidas.yaml
    e gerando candidatos_brutos.yaml.
    """
    pico_dir = tmp_path / "br_mg_croqui"
    pico_dir.mkdir()

    vias_yaml = pico_dir / "vias_extraidas.yaml"
    candidatos_yaml = pico_dir / "candidatos_brutos.yaml"

    vias = beta_pb2.ViasExtraidasCroqui()
    vias.id_croqui = "br_mg_croqui"
    via = vias.escaladas.add()
    via.nome = "Via Teste"

    salvar_vias_extraidas_yaml(vias, vias_yaml)

    mock_ext = MagicMock()
    m = beta_pb2.MidiaBeta()
    m.url = "https://youtube.com/watch?v=999"
    m.titulo = "Vídeo Teste"
    mock_ext.buscar.return_value = [m]

    retorno = executar_cli_buscar(
        [str(pico_dir)],
        extratores=[mock_ext]
    )
    assert retorno == 0
    assert candidatos_yaml.exists()

    conteudo = candidatos_yaml.read_text(encoding="utf-8")
    assert "https://youtube.com/watch?v=999" in conteudo
