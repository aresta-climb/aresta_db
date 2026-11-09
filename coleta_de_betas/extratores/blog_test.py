# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import ExtratorBlog, _BuscadorDuckDuckGoPadrao
from coleta_de_betas.extratores.cliente_http_fake import (
    BuscadorWebFake,
    ClienteHttpFake,
)


def test_extrator_blog_extrai_janelas_de_contexto_e_usa_cache_por_url() -> None:
    buscador = BuscadorWebFake()
    http = ClienteHttpFake()

    url_post = "https://blogmontanha.com.br/escaladas-serra-do-cipo"
    buscador.registrar_resultados(
        "Via do Sol",
        [
            {
                "href": url_post,
                "title": "Guia de Escaladas na Serra do Cipó",
                "body": "Relato de várias vias esportivas clássicas.",
            }
        ],
    )
    buscador.registrar_resultados(
        "Aresta Oeste",
        [
            {
                "href": url_post,
                "title": "Guia de Escaladas na Serra do Cipó",
                "body": "Relato de várias vias esportivas clássicas.",
            }
        ],
    )

    html_post = """
    <html>
      <head><title>Escaladas na Serra do Cipó - Blog Montanha</title></head>
      <body>
        <script>console.log("Via do Sol ignorada no script");</script>
        <p>Chegamos cedo ao setor principal para aquecer nas chaminés.</p>
        <p>A clássica Via do Sol (7a) tem um crux técnico na terceira chapeleta com regletes pequenos e exige ótimo posicionamento de pés.</p>
        <p>Mais tarde entramos na Aresta Oeste, uma linha tradicional de 3 enfiadas com proteção móvel em fenda perfeita.</p>
      </body>
    </html>
    """
    http.registrar_texto(url_post, html_post, status_code=200)

    extrator = ExtratorBlog(buscador=buscador, cliente_http=http)

    candidatos_sol = extrator.buscar(
        nome_escalada="Via do Sol",
        nome_setor="Setor Principal",
        nome_pico="Serra do Cipó",
    )
    assert len(candidatos_sol) == 1
    cand = candidatos_sol[0]
    assert cand.midia.url == url_post
    assert cand.midia.titulo == "Escaladas na Serra do Cipó - Blog Montanha"
    assert cand.midia.fonte == beta_pb2.FonteMidia.BLOG
    assert cand.match_nome_no_snippet is True
    assert len(cand.snippets) >= 1
    assert "crux técnico na terceira chapeleta" in cand.snippets[0]
    assert "console.log" not in cand.snippets[0]

    # Segunda busca para outra escalada citada no mesmo post deve reaproveitar o cache HTTP
    candidatos_aresta = extrator.buscar(
        nome_escalada="Aresta Oeste",
        nome_setor="Setor Principal",
        nome_pico="Serra do Cipó",
    )
    assert len(candidatos_aresta) == 1
    assert "3 enfiadas com proteção móvel" in candidatos_aresta[0].snippets[0]
    assert len(http.chamadas_get) == 1


def test_extrator_blog_descarta_redes_sociais_paginas_sem_vocabulario_ou_sem_nome_da_via() -> None:
    buscador = BuscadorWebFake()
    http = ClienteHttpFake()

    buscador.registrar_resultados(
        "Sonho de Ícaro",
        [
            {"href": "", "title": "Sem Link", "body": ""},
            {
                "href": "https://www.instagram.com/p/abc/",
                "title": "Post Instagram",
                "body": "Sonho de Ícaro",
            },
            {
                "href": "https://blogculinaria.com/receita",
                "title": "Receita Sonho de Ícaro",
                "body": "Doce de padaria",
            },
            {
                "href": "https://blogescalada.com/outro-setor",
                "title": "Escalada em Outro Setor",
                "body": "Vias e boulders",
            },
            {
                "href": "https://blogescalada.com/erro-404",
                "title": "Página Quebrada",
                "body": "Sonho de Ícaro",
            },
            {
                "href": "https://blogescalada.com/timeout",
                "title": "Página Timeout",
                "body": "Sonho de Ícaro",
            },
        ],
    )

    # Página com nome "Sonho de Ícaro", mas sem vocabulário de escalada
    http.registrar_texto(
        "https://blogculinaria.com/receita",
        "<html><body>O doce Sonho de Ícaro leva açúcar e canela.</body></html>",
        status_code=200,
    )
    # Página com vocabulário de escalada, mas sem mencionar a via "Sonho de Ícaro"
    http.registrar_texto(
        "https://blogescalada.com/outro-setor",
        "<html><body>Fizemos vários boulders e vias com chapeletas novas.</body></html>",
        status_code=200,
    )
    # Página HTTP 404
    http.registrar_texto("https://blogescalada.com/erro-404", "Not Found", status_code=404)
    # Página com erro de conexão
    http.registrar_erro("https://blogescalada.com/timeout", "Falha de rede")

    extrator = ExtratorBlog(buscador=buscador, cliente_http=http)
    candidatos = extrator.buscar("Sonho de Ícaro")
    assert candidatos == []


def test_extrator_blog_propaga_erro_quando_buscador_falha() -> None:
    buscador = BuscadorWebFake()
    buscador.registrar_erro("Serviço indisponível")
    extrator = ExtratorBlog(buscador=buscador, cliente_http=ClienteHttpFake())

    with pytest.raises(RuntimeError, match="Erro na busca de blogs"):
        extrator.buscar("Via Teste")


def test_buscador_duckduckgo_padrao_usa_ddgs_sem_runtime_warning() -> None:
    class _SessaoDdgsFake:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def text(self, query: str, max_results: int = 10) -> list[dict[str, str]]:
            return [{"href": "https://blog.com/post", "title": query, "body": str(max_results)}]

    buscador_padrao = _BuscadorDuckDuckGoPadrao(fabrica_ddgs=_SessaoDdgsFake)
    res = buscador_padrao.buscar_texto("Via Teste", max_resultados=5)
    assert res == [{"href": "https://blog.com/post", "title": "Via Teste", "body": "5"}]
    assert _BuscadorDuckDuckGoPadrao()._fabrica_ddgs.__module__.startswith("ddgs")

