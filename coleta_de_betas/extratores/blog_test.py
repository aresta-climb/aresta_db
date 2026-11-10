# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from types import SimpleNamespace
from typing import Any

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import (
    ExtratorBlog,
    _BuscadorDuckDuckGoPadrao,
    classificar_fonte_url,
    eh_url_bloqueada,
    menciona_contexto_pico,
    menciona_nome_via,
    sanitizar_termo_busca,
)
from coleta_de_betas.extratores.cliente_http_fake import (
    BuscadorWebFake,
    ClienteHttpFake,
)


def test_sanitizar_termo_busca_remove_parenteses_sufixo_mapa_e_pontuacao() -> None:
    assert sanitizar_termo_busca("Lua Cheia (Setor Gruta - Mapa 3)") == "Lua Cheia"
    assert sanitizar_termo_busca("Setor Gruta - Mapa 3") == "Setor Gruta"
    assert sanitizar_termo_busca('"Ajoelhou tem que Rezar" [Projeto]') == "Ajoelhou tem que Rezar"
    assert sanitizar_termo_busca("  Karren-Glass! ") == "Karren Glass"


def test_menciona_nome_via_suporta_espacos_colapsados_bidirecionais_e_typos() -> None:
    # Via separada ("Karren Glass") encontrando texto junto ("Karrenglass")
    assert menciona_nome_via("Mandando a clássica Karrenglass na Lapinha!", "Karren Glass") is True
    # Via junta ("Karrenglass") encontrando texto separado ("Karren Glass")
    assert menciona_nome_via("Vídeo da via Karren Glass 7b", "Karrenglass") is True
    # Pequeno typo ("Karenglass" com um 'r' só vs "Karren Glass")
    assert menciona_nome_via("Cadena da via Karenglass hoje cedo", "Karren Glass") is True
    # Insensível a acentos e caixa
    assert menciona_nome_via("Subindo a via Sonho de Icaro no Cipo", "Sonho de Ícaro") is True
    # Texto sobre outra via não deve dar match
    assert menciona_nome_via("Escalada da via Favo de Mel na Lapinha", "Karren Glass") is False
    assert menciona_nome_via("", "Karren Glass") is False
    assert menciona_nome_via("Qualquer texto", "") is False


def test_menciona_contexto_pico_valida_token_significativo() -> None:
    assert menciona_contexto_pico("Escalada na Lapinha MG", "Gruta da Lapinha") is True
    assert menciona_contexto_pico("Setor clássico no Cipó", "Serra do Cipó") is True
    # Apenas a stopword "Gruta" não basta para "Gruta da Lapinha"
    assert menciona_contexto_pico("Visita à Gruta de Maquiné", "Gruta da Lapinha") is False
    # Quando nome_pico é vazio ou tem apenas tokens curtos (< 3 chars), não restringe
    assert menciona_contexto_pico("Qualquer relato de escalada", "") is True
    assert menciona_contexto_pico("Qualquer relato de escalada", "Sé") is True
    # Texto vazio com pico válido retorna False
    assert menciona_contexto_pico("", "Gruta da Lapinha") is False


def test_eh_url_bloqueada_filtra_agregadores_pdfs_e_trilhas() -> None:
    assert eh_url_bloqueada("") is False
    assert eh_url_bloqueada("https://pt.scribd.com/document/123/Guia-Lapinha") is True
    assert eh_url_bloqueada("https://www.thecrag.com/pt/escalando/brazil/route/123") is True
    assert eh_url_bloqueada("https://www.escaladas.com.br/via/castelinho") is True
    assert eh_url_bloqueada("https://pt.wikiloc.com/trilhas/lapinha") is True
    assert eh_url_bloqueada("https://www.instagram.com/reels/audio/123456/") is True
    assert eh_url_bloqueada("https://music.youtube.com/watch?v=abc") is True

    assert eh_url_bloqueada("https://www.instagram.com/reel/Cx123/") is False
    assert eh_url_bloqueada("https://www.youtube.com/watch?v=abc123") is False
    assert eh_url_bloqueada("https://blogmontanha.com.br/via-do-sol") is False


def test_extrator_blog_executa_5_queries_sem_setor_e_sem_scrape_html() -> None:
    buscador = BuscadorWebFake()
    http = ClienteHttpFake()

    url_post = "https://blogmontanha.com.br/escaladas-serra-do-cipo"
    buscador.registrar_resultados(
        "Via do Sol",
        [
            {"href": "", "title": "Sem URL", "body": ""},
            {
                "href": url_post,
                "title": "Via do Sol - Escaladas na Serra do Cipó",
                "body": "A clássica Via do Sol (7a) no Cipó tem um crux técnico na terceira chapeleta.",
            },
        ],
    )

    extrator = ExtratorBlog(buscador=buscador, cliente_http=http)
    assert (
        extrator.montar_query("Via do Sol (Setor Principal - Mapa 2)", "Setor Principal", "Serra do Cipó")
        == "Via do Sol Serra do Cipó escalada"
    )
    queries = extrator.montar_queries_identificadas(
        nome_escalada="Via do Sol (Setor Principal - Mapa 2)",
        nome_pico="Serra do Cipó",
    )
    assert [origem for origem, _ in queries] == [
        "instagram",
        "youtube",
        "tiktok",
        "facebook",
        "geral",
    ]
    for _origem, q in queries:
        assert "Setor Principal" not in q
        assert "Mapa 2" not in q
        assert '"' not in q

    candidatos = extrator.buscar(
        nome_escalada="Via do Sol (Setor Principal - Mapa 2)",
        nome_setor="Setor Principal - Mapa 2",
        nome_pico="Serra do Cipó",
    )
    assert len(candidatos) == 1
    cand = candidatos[0]
    assert cand.midia.url == url_post
    assert cand.midia.titulo == "Via do Sol - Escaladas na Serra do Cipó"
    assert cand.midia.fonte == beta_pb2.FonteMidia.BLOG
    assert cand.match_nome_no_snippet is True
    assert "crux técnico na terceira chapeleta" in cand.snippets[0]
    # Zero chamadas HTTP de download de HTML durante a coleta
    assert http.chamadas_get == []


def test_extrator_blog_buscar_com_rejeitados_registra_query_origem_e_motivo() -> None:
    buscador = BuscadorWebFake()

    buscador.registrar_resultados(
        "site:instagram.com",
        [
            {
                "href": "https://www.instagram.com/reel/ig_karren/",
                "title": "Mandando a Karrenglass na Lapinha",
                "body": "Beta completo da via na Gruta da Lapinha.",
            },
            {
                "href": "https://www.instagram.com/perfil_generico/",
                "title": "Perfil Instagram sem post",
                "body": "Karren Glass Lapinha",
            },
            {
                "href": "https://www.instagram.com/p/ig_outra_via/",
                "title": "Escalando na Gruta da Lapinha",
                "body": "Hoje fizemos a Favo de Mel.",
            },
        ],
    )
    buscador.registrar_resultados(
        "site:youtube.com",
        [
            {
                "href": "https://www.youtube.com/watch?v=yt_outro_pico",
                "title": "Via Karren Glass em Itatiaia",
                "body": "Escalada tradicional no Parque Nacional.",
            }
        ],
    )
    buscador.registrar_resultados(
        "karren glass gruta da lapinha escalada",
        [
            {
                "href": "https://pt.scribd.com/document/999/Croqui-Lapinha",
                "title": "Croqui Gruta da Lapinha PDF - Karren Glass",
                "body": "Lista de vias da Lapinha.",
            },
            {
                "href": "https://www.thecrag.com/route/karren-glass",
                "title": "Karren Glass - TheCrag Lapinha",
                "body": "Topo da via Karren Glass na Lapinha.",
            },
        ],
    )

    extrator = ExtratorBlog(buscador=buscador)
    candidatos, rejeitados = extrator.buscar_com_rejeitados(
        nome_escalada="Karren Glass",
        nome_setor="Setor Gruta - Mapa 3",
        nome_pico="Gruta da Lapinha",
    )

    assert len(candidatos) == 1
    assert candidatos[0].midia.url == "https://www.instagram.com/reel/ig_karren/"
    assert candidatos[0].midia.fonte == beta_pb2.FonteMidia.INSTAGRAM

    urls_rejeitadas = {m.url: m.titulo for m in rejeitados}
    assert "https://www.instagram.com/perfil_generico/" not in urls_rejeitadas
    assert urls_rejeitadas["https://www.instagram.com/p/ig_outra_via/"].startswith(
        "[Query: instagram | Auto-filtrado: sem menção à via]"
    )
    assert urls_rejeitadas["https://www.youtube.com/watch?v=yt_outro_pico"].startswith(
        "[Query: youtube | Auto-filtrado: sem menção ao pico]"
    )
    assert "Auto-filtrado: domínio bloqueado]" in urls_rejeitadas[
        "https://pt.scribd.com/document/999/Croqui-Lapinha"
    ]
    assert "Auto-filtrado: domínio bloqueado]" in urls_rejeitadas[
        "https://www.thecrag.com/route/karren-glass"
    ]


def test_extrator_blog_propaga_erro_quando_buscador_falha() -> None:
    buscador = BuscadorWebFake()
    buscador.registrar_erro("Serviço indisponível")
    extrator = ExtratorBlog(buscador=buscador, cliente_http=ClienteHttpFake())

    with pytest.raises(RuntimeError, match="Erro na busca de blogs"):
        extrator.buscar("Via Teste")


def test_buscador_duckduckgo_padrao_mantem_sessao_persistente_e_retorna_vazio_em_no_results() -> None:
    chamadas: list[tuple[str, str, str, int]] = []
    tempos_dormidos: list[float] = []
    instancias_criadas: list[int] = []
    engines_configuradas: list[Any] = []
    relogio_atual = [100.0]

    def _relogio_fake() -> float:
        return relogio_atual[0]

    def _dormir_fake(segundos: float) -> None:
        tempos_dormidos.append(round(segundos, 3))
        relogio_atual[0] += segundos

    class _SessaoDdgsFake:
        def __init__(self) -> None:
            instancias_criadas.append(1)

        def _get_engines(self, categoria: str, backend: str) -> list[Any]:
            _ = (categoria, backend)
            eng = SimpleNamespace(http_client=SimpleNamespace(client=None))
            engines_configuradas.append(eng)
            return [eng]

        def text(
            self,
            query: str,
            *,
            region: str = "us-en",
            backend: str = "auto",
            max_results: int = 10,
        ) -> list[dict[str, str]]:
            chamadas.append((query, region, backend, max_results))
            if query == "Via Sem Resultado":
                raise RuntimeError("No results found.")
            if query == "Via Falha Total":
                raise RuntimeError("Falha de rede em todos os motores")
            if backend == "yahoo" and query == "Via Com Rate Limit":
                raise RuntimeError("HTTP 429 Rate Limit")
            return [{"href": "https://blog.com/post", "title": query, "body": backend}]

    buscador_padrao = _BuscadorDuckDuckGoPadrao(
        fabrica_ddgs=_SessaoDdgsFake,
        backends=("yahoo", "brave"),
        intervalo_minimo_s=0.5,
        relogio=_relogio_fake,
        dormir=_dormir_fake,
    )

    # 1ª chamada usa yahoo com region="br-pt" e configura client desktop nas engines
    res1 = buscador_padrao.buscar_texto("Via 1", max_resultados=5)
    assert res1 == [{"href": "https://blog.com/post", "title": "Via 1", "body": "yahoo"}]
    assert chamadas[-1] == ("Via 1", "br-pt", "yahoo", 5)
    assert len(engines_configuradas) == 2
    assert engines_configuradas[0].http_client.client is not None

    # 2ª chamada com "No results found." retorna [] IMEDIATAMENTE na 1ª tentativa sem cascatear
    relogio_atual[0] += 0.2  # passaram 0.2s -> dorme 0.3s
    res_vazio = buscador_padrao.buscar_texto("Via Sem Resultado", max_resultados=5)
    assert res_vazio == []
    assert len(chamadas) == 2
    assert tempos_dormidos[0] == 0.3

    # 3ª chamada com erro de transporte/rate-limit no yahoo faz fallback para brave
    relogio_atual[0] += 1.0
    res_fallback = buscador_padrao.buscar_texto("Via Com Rate Limit", max_resultados=5)
    assert res_fallback == [
        {"href": "https://blog.com/post", "title": "Via Com Rate Limit", "body": "brave"}
    ]

    # 4ª chamada onde todos os motores falham propaga a última exceção
    relogio_atual[0] += 1.0
    with pytest.raises(RuntimeError, match="Falha de rede em todos os motores"):
        buscador_padrao.buscar_texto("Via Falha Total", max_resultados=5)

    # A fábrica foi instanciada apenas 1 única vez (sessão HTTP/TLS persistente)
    assert len(instancias_criadas) == 1
    assert _BuscadorDuckDuckGoPadrao()._fabrica_ddgs.__module__.startswith("ddgs")


def test_classificar_fonte_url_8_categorias() -> None:
    assert classificar_fonte_url("") is None
    assert classificar_fonte_url("ftp://invalido.com/video") is None

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
    assert classificar_fonte_url("https://vm.tiktok.com/ZM12345/") == (
        beta_pb2.FonteMidia.TIKTOK
    )
    assert classificar_fonte_url("https://www.tiktok.com/@user") is None

    assert classificar_fonte_url("https://www.facebook.com/user/videos/98765") == (
        beta_pb2.FonteMidia.FACEBOOK
    )
    assert classificar_fonte_url("https://fb.watch/abc123/") == beta_pb2.FonteMidia.FACEBOOK
    assert classificar_fonte_url("https://www.facebook.com/watch?v=12345") == (
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
    assert classificar_fonte_url("https://redd.it/abc123") == beta_pb2.FonteMidia.REDDIT
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
