# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Aresta Contributors

import pytest
from unittest.mock import patch, MagicMock
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.vertex import ExtratorVertexSearch

def test_extrator_vertex_monta_query():
    extrator = ExtratorVertexSearch(project_id="test-proj", data_store_id="test-store")
    query = extrator.montar_query("Fusca Azul", "Geriatria", "Ouro Preto")
    assert "Fusca Azul" in query
    assert "Geriatria" in query
    assert "Ouro Preto" in query


@patch("requests.post")
def test_extrator_vertex_busca_com_sucesso(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "document": {
                    "derivedStructData": {
                        "link": "https://www.instagram.com/p/Cxyz123/",
                        "title": "Mandando a via Fusca Azul no setor Geriatria",
                        "snippets": [
                            {"snippet": "Baita cadena na clássica Fusca Azul em Ouro Preto!"}
                        ],
                        "pagemap": {
                            "cse_image": [{"src": "https://instagram.com/thumb123.jpg"}]
                        }
                    }
                }
            },
            {
                "document": {
                    "derivedStructData": {
                        "link": "https://www.instagram.com/p/Cxyz456/",
                        "title": "Dia de escalada com a galera",
                        "snippets": [
                            {"snippet": "Passeio em Ouro Preto no fim de semana."}
                        ]
                    }
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    extrator = ExtratorVertexSearch(project_id="test-proj", data_store_id="test-store", api_key="KEY")
    resultados = extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    assert len(resultados) == 2
    
    item1 = resultados[0]
    assert isinstance(item1, beta_pb2.MidiaBeta)
    assert item1.url == "https://www.instagram.com/p/Cxyz123/"
    assert item1.titulo == "Mandando a via Fusca Azul no setor Geriatria"
    assert item1.thumbnail_url == "https://instagram.com/thumb123.jpg"
    assert item1.fonte == beta_pb2.FonteMidia.INSTAGRAM
    assert item1.match_nome_no_snippet is True

    item2 = resultados[1]
    assert item2.url == "https://www.instagram.com/p/Cxyz456/"
    assert item2.match_nome_no_snippet is False


@patch("requests.post")
def test_extrator_vertex_trata_erro_api(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_post.return_value = mock_response

    extrator = ExtratorVertexSearch(project_id="test-proj", data_store_id="test-store")
    with pytest.raises(RuntimeError, match="Erro na API do Vertex AI Search"):
        extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")
