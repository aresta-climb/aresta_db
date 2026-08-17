# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from unittest.mock import patch, MagicMock
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.youtube import ExtratorYouTube

def test_extrator_youtube_monta_query_correta():
    extrator = ExtratorYouTube(chave_api="TEST_KEY")
    query = extrator.montar_query("Fusca Azul", "Geriatria", "Ouro Preto")
    assert "Fusca Azul" in query
    assert "Geriatria" in query
    assert "Ouro Preto" in query
    assert "escalada" in query.lower() or "boulder" in query.lower()


@patch("requests.get")
def test_extrator_youtube_busca_com_sucesso(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": {"videoId": "vid123"},
                "snippet": {
                    "title": "Mandando o crux da Fusca Azul V4",
                    "description": "Vídeo mostrando a beta da via Fusca Azul no setor Geriatria.",
                    "thumbnails": {
                        "high": {"url": "https://img.youtube.com/vi/vid123/hqdefault.jpg"}
                    }
                }
            },
            {
                "id": {"videoId": "vid456"},
                "snippet": {
                    "title": "Outra escalada qualquer",
                    "description": "Escalando em Ouro Preto",
                    "thumbnails": {
                        "default": {"url": "https://img.youtube.com/vi/vid456/default.jpg"}
                    }
                }
            }
        ]
    }
    mock_get.return_value = mock_response

    extrator = ExtratorYouTube(chave_api="TEST_KEY")
    resultados = extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    assert len(resultados) == 2
    
    item1 = resultados[0]
    assert isinstance(item1, beta_pb2.MidiaBeta)
    assert item1.url == "https://www.youtube.com/watch?v=vid123"
    assert item1.titulo == "Mandando o crux da Fusca Azul V4"
    assert item1.thumbnail_url == "https://img.youtube.com/vi/vid123/hqdefault.jpg"
    assert item1.fonte == beta_pb2.FonteMidia.YOUTUBE
    assert item1.match_nome_no_snippet is True

    item2 = resultados[1]
    assert item2.url == "https://www.youtube.com/watch?v=vid456"
    assert item2.match_nome_no_snippet is False


@patch("requests.get")
def test_extrator_youtube_trata_erro_api(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Quota exceeded"
    mock_get.return_value = mock_response

    extrator = ExtratorYouTube(chave_api="TEST_KEY")
    with pytest.raises(RuntimeError, match="Erro na API do YouTube"):
        extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")
