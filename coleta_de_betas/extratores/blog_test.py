# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import (
    ExtratorBlog,
    _BuscadorDuckDuckGoPadrao,
    classificar_fonte_url,
)
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
                "href": "https://www.instagram.com/perfil_generico/",
                "title": "Perfil Instagram sem post",
                "body": "Sonho de Ícaro",
            },
            {
                "href": "https://www.youtube.com/@canal_escalada",
                "title": "Canal YouTube sem vídeo",
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
    chamadas: list[tuple[str, str, str, int]] = []
    tempos_dormidos: list[float] = []
    relogio_atual = [100.0]

    def _relogio_fake() -> float:
        return relogio_atual[0]

    def _dormir_fake(segundos: float) -> None:
        tempos_dormidos.append(round(segundos, 3))
        relogio_atual[0] += segundos

    class _SessaoDdgsFake:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def text(
            self,
            query: str,
            *,
            region: str = "us-en",
            backend: str = "auto",
            max_results: int = 10,
        ) -> list[dict[str, str]]:
            chamadas.append((query, region, backend, max_results))
            if backend == "yahoo" and query == "Via Sem Resultado":
                raise RuntimeError("No results found.")
            if backend == "duckduckgo" and query == "Via Com Fallback":
                raise RuntimeError("HTTP 202 Rate Limit")
            if query == "Via Sem Resultado":
                raise RuntimeError("No results found.")
            return [{"href": "https://blog.com/post", "title": query, "body": backend}]

    buscador_padrao = _BuscadorDuckDuckGoPadrao(
        fabrica_ddgs=_SessaoDdgsFake,
        backends=("yahoo", "duckduckgo", "startpage"),
        intervalo_minimo_s=0.5,
        relogio=_relogio_fake,
        dormir=_dormir_fake,
    )

    # 1ª chamada usa yahoo com region="br-pt"
    res1 = buscador_padrao.buscar_texto("Via 1", max_resultados=5)
    assert res1 == [{"href": "https://blog.com/post", "title": "Via 1", "body": "yahoo"}]
    assert chamadas[-1] == ("Via 1", "br-pt", "yahoo", 5)

    # 2ª chamada avança o round-robin para duckduckgo, faz fallback se falhar -> startpage, e respeita pacing
    relogio_atual[0] += 0.2  # passaram apenas 0.2s, então deve dormir 0.3s
    res2 = buscador_padrao.buscar_texto("Via Com Fallback", max_resultados=5)
    assert res2 == [
        {"href": "https://blog.com/post", "title": "Via Com Fallback", "body": "startpage"}
    ]
    assert tempos_dormidos[0] == 0.3

    # Busca sem nenhum resultado em todos os backends retorna [] sem levantar exceção
    res_vazio = buscador_padrao.buscar_texto("Via Sem Resultado", max_resultados=5)
    assert res_vazio == []
    assert _BuscadorDuckDuckGoPadrao()._fabrica_ddgs.__module__.startswith("ddgs")


def test_classificar_fonte_url_e_busca_aberta_unificada_8_categorias() -> None:
    # Valida classificar_fonte_url para as 8 categorias e descarte de perfis vazios
    assert classificar_fonte_url("https://www.youtube.com/watch?v=abc123") == (
        beta_pb2.FonteMidia.YOUTUBE
    )
    assert classificar_fonte_url("https://youtu.be/abc123") == beta_pb2.FonteMidia.YOUTUBE
    assert classificar_fonte_url("https://www.youtube.com/shorts/xyz") == (
        beta_pb2.FonteMidia.YOUTUBE
    )
    assert classificar_fonte_url("https://www.youtube.com/@canal") is None

    assert classificar_fonte_url("https://www.instagram.com/reel/Cx123/") == (
        beta_pb2.FonteMidia.INSTAGRAM
    )
    assert classificar_fonte_url("https://www.instagram.com/p/Cx123/") == (
        beta_pb2.FonteMidia.INSTAGRAM
    )
    assert classificar_fonte_url("https://www.instagram.com/climbcipo/") is None

    assert classificar_fonte_url("https://www.tiktok.com/@user/video/123456") == (
        beta_pb2.FonteMidia.TIKTOK
    )
    assert classificar_fonte_url("https://www.tiktok.com/@user") is None

    assert classificar_fonte_url("https://www.facebook.com/user/videos/98765") == (
        beta_pb2.FonteMidia.FACEBOOK
    )
    assert classificar_fonte_url("https://www.facebook.com/paginagenerica") is None

    assert classificar_fonte_url("https://x.com/climber/status/112233") == (
        beta_pb2.FonteMidia.TWITTER
    )
    assert classificar_fonte_url("https://twitter.com/climber") is None

    assert classificar_fonte_url("https://www.reddit.com/r/climbing/comments/abc/castelinho/") == (
        beta_pb2.FonteMidia.REDDIT
    )
    assert classificar_fonte_url("https://www.reddit.com/r/climbing/") is None

    assert classificar_fonte_url("https://www.thecrag.com/pt/escalando/brazil/route/123") == (
        beta_pb2.FonteMidia.OUTRO_UGC
    )
    assert classificar_fonte_url("https://pt.wikiloc.com/trilhas-escalada-na-rocha/lapinha") == (
        beta_pb2.FonteMidia.OUTRO_UGC
    )
    assert classificar_fonte_url("https://climbcipo.com.br/via-castelinho/") == (
        beta_pb2.FonteMidia.BLOG
    )

    # Testa busca aberta unificada retornando múltiplas categorias em 1 única requisição
    buscador = BuscadorWebFake()
    http = ClienteHttpFake()
    buscador.registrar_resultados(
        "Castelinho",
        [
            {
                "href": "https://www.youtube.com/watch?v=yt_castelinho",
                "title": "Via Castelinho - Gruta da Lapinha",
                "body": "Beta completo da via Castelinho.",
            },
            {
                "href": "https://www.instagram.com/reel/ig_castelinho/",
                "title": "Mandando a Castelinho",
                "body": "Crux da Castelinho na Lapinha.",
            },
            {
                "href": "https://www.tiktok.com/@climber/video/999",
                "title": "TikTok Castelinho",
                "body": "Escalada na Lapinha.",
            },
            {
                "href": "https://www.thecrag.com/route/castelinho",
                "title": "Castelinho - TheCrag",
                "body": "Via Castelinho 6o grau no setor Castelinho.",
            },
        ],
    )
    # TheCrag bloqueia HTTP com 403, mas o snippet da busca menciona "Castelinho"
    http.registrar_texto("https://www.thecrag.com/route/castelinho", "Forbidden", status_code=403)

    extrator = ExtratorBlog(buscador=buscador, cliente_http=http)
    query_gerada = extrator.montar_query("Castelinho", "Setor Castelinho", "Gruta da Lapinha")
    assert "-site:" not in query_gerada

    cands = extrator.buscar("Castelinho", "Setor Castelinho", "Gruta da Lapinha")
    assert len(cands) == 4
    fontes = [c.midia.fonte for c in cands]
    assert fontes == [
        beta_pb2.FonteMidia.YOUTUBE,
        beta_pb2.FonteMidia.INSTAGRAM,
        beta_pb2.FonteMidia.TIKTOK,
        beta_pb2.FonteMidia.OUTRO_UGC,
    ]
    assert cands[0].match_nome_no_snippet is True
    assert cands[3].snippets == ["Via Castelinho 6o grau no setor Castelinho."]


