# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import patch, MagicMock
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.duckduckgo import ExtratorDuckDuckGo

def test_extrator_duckduckgo_monta_query():
    extrator = ExtratorDuckDuckGo()
    query = extrator.montar_query("Fusca Azul", "Geriatria", "Ouro Preto")
    assert "Fusca Azul" in query
    assert "Geriatria" in query
    assert "Ouro Preto" in query
    assert "site:instagram.com" in query


@patch("duckduckgo_search.DDGS")
def test_extrator_duckduckgo_busca_com_sucesso(mock_ddgs_cls):
    mock_ddgs_instance = MagicMock()
    mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs_instance

    mock_ddgs_instance.text.return_value = [
        {
            "href": "https://www.instagram.com/p/Cxyz123/",
            "title": "Post do Instagram: Fusca Azul",
            "body": "Mandando a via Fusca Azul no setor Geriatria em Ouro Preto."
        },
        {
            "href": "https://www.instagram.com/p/Cxyz789/",
            "title": "Dia de escalada",
            "body": "Belas fotos da rocha e da paisagem."
        }
    ]

    extrator = ExtratorDuckDuckGo()
    resultados = extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    assert len(resultados) == 2
    
    item1 = resultados[0]
    assert isinstance(item1, beta_pb2.MidiaBeta)
    assert item1.url == "https://www.instagram.com/p/Cxyz123/"
    assert item1.titulo == "Post do Instagram: Fusca Azul"
    assert item1.fonte == beta_pb2.FonteMidia.INSTAGRAM
    assert item1.match_nome_no_snippet is True

    item2 = resultados[1]
    assert item2.url == "https://www.instagram.com/p/Cxyz789/"
    assert item2.match_nome_no_snippet is False


@patch("duckduckgo_search.DDGS")
def test_extrator_duckduckgo_trata_erro_scraping(mock_ddgs_cls):
    mock_ddgs_instance = MagicMock()
    mock_ddgs_cls.return_value.__enter__.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.side_effect = Exception("Rate limit / Blocked")

    extrator = ExtratorDuckDuckGo()
    with pytest.raises(RuntimeError, match="Erro na busca via DuckDuckGo"):
        extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")
