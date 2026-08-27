# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import MagicMock
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.inteligencia.avaliador import (
    gerar_prompt_avaliacao,
    parsear_resposta_llm,
    avaliar_candidatos,
    salvar_betas_pendentes,
    carregar_betas_pendentes
)

def test_gerar_prompt_avaliacao():
    candidatos = [
        {
            "url": "https://youtube.com/v1",
            "titulo": "Mandando Fusca Azul V4",
            "thumbnail_url": "https://img.youtube.com/vi/v1/hqdefault.jpg",
            "snippet": "Escalada em Ouro Preto"
        }
    ]
    prompt = gerar_prompt_avaliacao("Fusca Azul", "V4", "Geriatria", "Ouro Preto", candidatos)
    assert "Fusca Azul" in prompt
    assert "V4" in prompt
    assert "Geriatria" in prompt
    assert "Mandando Fusca Azul V4" in prompt
    assert "thumbnail_url" in prompt
    assert "JSON" in prompt


def test_parsear_resposta_llm_json_valido():
    json_str = """
    ```json
    [
        {
            "url": "https://youtube.com/v1",
            "score": 95,
            "justificativa": "Vídeo demonstra a via com o nome e grau exatos."
        }
    ]
    ```
    """
    dados = parsear_resposta_llm(json_str)
    assert len(dados) == 1
    assert dados[0]["url"] == "https://youtube.com/v1"
    assert dados[0]["score"] == 95
    assert "exatos" in dados[0]["justificativa"]


def test_parsear_resposta_llm_json_direto():
    json_str = '[{"url": "https://instagram.com/p/123", "score": 40, "justificativa": "Dúvida no setor"}]'
    dados = parsear_resposta_llm(json_str)
    assert len(dados) == 1
    assert dados[0]["score"] == 40


def test_avaliar_candidatos_atualiza_proto():
    m1 = beta_pb2.MidiaBeta()
    m1.url = "https://youtube.com/v1"
    m1.titulo = "Mandando Fusca Azul"
    m1.thumbnail_url = "https://img.youtube.com/vi/v1/hqdefault.jpg"

    mock_llm = MagicMock()
    mock_llm.gerar_texto.return_value = """
    [
        {
            "url": "https://youtube.com/v1",
            "score": 90,
            "justificativa": "Bate 100% com a via."
        }
    ]
    """

    avaliados = avaliar_candidatos("Fusca Azul", "V4", "Geriatria", "Ouro Preto", [m1], client_llm=mock_llm)
    
    assert len(avaliados) == 1
    item = avaliados[0]
    assert item.resultado_llm.llm_confidence_score == 90
    assert item.resultado_llm.llm_reasoning == "Bate 100% com a via."


def test_salvar_e_carregar_betas_pendentes(tmp_path):
    arquivo_pb = tmp_path / "betas_pendentes.binarypb"

    candidato = beta_pb2.CandidatosBetaPorEscalada()
    candidato.nome_escalada = "Fusca Azul"
    candidato.nome_setor = "Geriatria"
    candidato.nome_grupo = "Setor Principal"

    m = candidato.candidatos.add()
    m.url = "https://youtube.com/v1"
    m.titulo = "Vídeo Teste"
    m.snippets.append("Crux na reglete")
    m.resultado_llm.llm_confidence_score = 90

    salvar_betas_pendentes("br_mg_ouro_preto_ouroboulder", [candidato], arquivo_pb)

    assert arquivo_pb.exists()

    lido = carregar_betas_pendentes(arquivo_pb)
    assert lido.id_croqui == "br_mg_ouro_preto_ouroboulder"
    assert len(lido.candidatos_por_escalada) == 1
    assert lido.candidatos_por_escalada[0].nome_escalada == "Fusca Azul"
    assert lido.candidatos_por_escalada[0].nome_setor == "Geriatria"
    assert lido.candidatos_por_escalada[0].nome_grupo == "Setor Principal"
    assert lido.candidatos_por_escalada[0].candidatos[0].snippets[0] == "Crux na reglete"
    assert lido.candidatos_por_escalada[0].candidatos[0].resultado_llm.llm_confidence_score == 90
