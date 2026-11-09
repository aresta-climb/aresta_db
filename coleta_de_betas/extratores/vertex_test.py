# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpFake
from coleta_de_betas.extratores.vertex import ExtratorVertexSearch

URL_VERTEX_TESTE = (
    "https://discoveryengine.googleapis.com/v1alpha/projects/test-proj/"
    "locations/global/collections/default_collection/dataStores/test-store/"
    "servingConfigs/default_search:search"
)


def test_extrator_vertex_monta_query() -> None:
    extrator = ExtratorVertexSearch(project_id="test-proj", data_store_id="test-store")
    query = extrator.montar_query("Fusca Azul", "Geriatria", "Ouro Preto")
    assert "Fusca Azul" in query
    assert "Geriatria" in query
    assert "Ouro Preto" in query


def test_extrator_vertex_busca_com_sucesso() -> None:
    http = ClienteHttpFake()
    http.registrar_json(
        URL_VERTEX_TESTE,
        {
            "results": [
                {"document": {"derivedStructData": {}}},
                {
                    "document": {
                        "derivedStructData": {
                            "link": "https://www.instagram.com/p/Cxyz123/",
                            "title": "Mandando a via Fusca Azul no setor Geriatria",
                            "snippets": [
                                {"snippet": "Baita cadena na clássica Fusca Azul em Ouro Preto!"}
                            ],
                        }
                    }
                },
                {
                    "document": {
                        "derivedStructData": {
                            "link": "https://www.instagram.com/p/Cxyz456/",
                            "title": "Dia de escalada com a galera",
                            "snippets": [],
                        }
                    }
                },
            ]
        },
        status_code=200,
    )

    extrator = ExtratorVertexSearch(
        project_id="test-proj",
        data_store_id="test-store",
        api_key="KEY",
        cliente_http=http,
    )
    resultados = extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    assert len(resultados) == 2

    item1 = resultados[0]
    assert isinstance(item1, beta_pb2.CandidatoMidiaBeta)
    assert item1.midia.url == "https://www.instagram.com/p/Cxyz123/"
    assert item1.midia.titulo == "Mandando a via Fusca Azul no setor Geriatria"
    assert item1.midia.fonte == beta_pb2.FonteMidia.INSTAGRAM
    assert item1.match_nome_no_snippet is True
    assert list(item1.snippets) == ["Baita cadena na clássica Fusca Azul em Ouro Preto!"]

    item2 = resultados[1]
    assert item2.midia.url == "https://www.instagram.com/p/Cxyz456/"
    assert item2.match_nome_no_snippet is False
    assert list(item2.snippets) == []


def test_extrator_vertex_trata_erro_api_e_conexao() -> None:
    http_401 = ClienteHttpFake()
    http_401.registrar_texto(URL_VERTEX_TESTE, "Unauthorized", status_code=401)
    extrator_401 = ExtratorVertexSearch(
        project_id="test-proj",
        data_store_id="test-store",
        cliente_http=http_401,
    )
    with pytest.raises(RuntimeError, match="Erro na API do Vertex AI Search"):
        extrator_401.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    http_rede = ClienteHttpFake()
    http_rede.registrar_erro(URL_VERTEX_TESTE, "Falha DNS")
    extrator_rede = ExtratorVertexSearch(
        project_id="test-proj",
        data_store_id="test-store",
        cliente_http=http_rede,
    )
    with pytest.raises(RuntimeError, match="Erro na conexão com a API do Vertex AI Search"):
        extrator_rede.buscar("Fusca Azul", "Geriatria", "Ouro Preto")
