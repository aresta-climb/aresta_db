# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import BuscadorWebFake
from coleta_de_betas.extratores.duckduckgo import ExtratorDuckDuckGo


def test_extrator_duckduckgo_monta_query() -> None:
    extrator = ExtratorDuckDuckGo(buscador=BuscadorWebFake())
    query = extrator.montar_query("Fusca Azul", "Geriatria", "Ouro Preto")
    assert "Fusca Azul" in query
    assert "Geriatria" in query
    assert "Ouro Preto" in query
    assert "site:instagram.com" in query


def test_extrator_duckduckgo_busca_com_sucesso() -> None:
    buscador = BuscadorWebFake()
    buscador.registrar_resultados(
        "Fusca Azul",
        [
            {"href": "", "title": "Ignorado sem href", "body": ""},
            {
                "href": "https://www.instagram.com/p/Cxyz123/",
                "title": "Post do Instagram: Fusca Azul",
                "body": "Mandando a via Fusca Azul no setor Geriatria em Ouro Preto.",
            },
            {
                "href": "https://www.instagram.com/p/Cxyz789/",
                "title": "Dia de escalada",
                "body": "",
            },
        ],
    )

    extrator = ExtratorDuckDuckGo(buscador=buscador)
    resultados = extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    assert len(resultados) == 2

    item1 = resultados[0]
    assert isinstance(item1, beta_pb2.CandidatoMidiaBeta)
    assert item1.midia.url == "https://www.instagram.com/p/Cxyz123/"
    assert item1.midia.titulo == "Post do Instagram: Fusca Azul"
    assert item1.midia.fonte == beta_pb2.FonteMidia.INSTAGRAM
    assert item1.match_nome_no_snippet is True
    assert list(item1.snippets) == [
        "Mandando a via Fusca Azul no setor Geriatria em Ouro Preto."
    ]

    item2 = resultados[1]
    assert item2.midia.url == "https://www.instagram.com/p/Cxyz789/"
    assert item2.match_nome_no_snippet is False
    assert list(item2.snippets) == []


def test_extrator_duckduckgo_trata_erro_scraping() -> None:
    buscador = BuscadorWebFake()
    buscador.registrar_erro("Rate limit / Blocked")

    extrator = ExtratorDuckDuckGo(buscador=buscador)
    with pytest.raises(RuntimeError, match="Erro na busca via DuckDuckGo"):
        extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")
