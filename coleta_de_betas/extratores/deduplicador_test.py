# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from coleta_de_betas.extratores.deduplicador import (
    deduplicar_midias,
    normalizar_url,
    obter_urls_conhecidas_escalada,
)


def test_normalizar_url_instagram_youtube_e_blog() -> None:
    url1 = "https://www.instagram.com/p/Cxyz123/?igsh=abc12345"
    url2 = "http://instagram.com/p/Cxyz123"
    url3 = "https://instagram.com/p/Cxyz123/"

    assert (
        normalizar_url(url1)
        == normalizar_url(url2)
        == normalizar_url(url3)
        == "https://instagram.com/p/Cxyz123"
    )
    assert (
        normalizar_url("https://www.instagram.com/usuario")
        == "https://instagram.com/usuario"
    )

    yt1 = "https://www.youtube.com/watch?v=vid123&feature=share"
    yt2 = "https://youtu.be/vid123"
    yt3 = "https://youtube.com/watch?v=vid123"
    assert (
        normalizar_url(yt1)
        == normalizar_url(yt2)
        == normalizar_url(yt3)
        == "https://youtube.com/watch?v=vid123"
    )

    blog1 = "https://www.blogescalada.com.br/post-via/"
    blog2 = "http://blogescalada.com.br/post-via"
    assert (
        normalizar_url(blog1)
        == normalizar_url(blog2)
        == "https://blogescalada.com.br/post-via"
    )
    assert normalizar_url("   ") == ""


def test_deduplicar_midias_mescla_informacoes_e_filtra_urls_conhecidas() -> None:
    # Item 1 do Vertex
    m1 = beta_pb2.CandidatoMidiaBeta()
    m1.midia.url = "https://www.instagram.com/p/Cxyz123/?utm_source=ig_web"
    m1.midia.titulo = ""
    m1.midia.fonte = beta_pb2.FonteMidia.INSTAGRAM
    m1.match_nome_no_snippet = True
    m1.snippets.append("Trecho do Vertex")

    # Item 2 do DuckDuckGo (mesma URL base, preenche título)
    m2 = beta_pb2.CandidatoMidiaBeta()
    m2.midia.url = "https://instagram.com/p/Cxyz123"
    m2.midia.titulo = "Vídeo do Crux - DDG"
    m2.midia.fonte = beta_pb2.FonteMidia.INSTAGRAM
    m2.match_nome_no_snippet = False
    m2.snippets.append("Trecho do DuckDuckGo")

    # Item 3 do YouTube (URL diferente)
    m3 = beta_pb2.CandidatoMidiaBeta()
    m3.midia.url = "https://youtube.com/watch?v=vid999"
    m3.midia.titulo = "Vídeo YouTube"
    m3.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
    m3.match_nome_no_snippet = True
    m3.snippets.append("Descrição do YouTube")

    # Item 4 já rejeitado anteriormente (deve ser filtrado!)
    m4 = beta_pb2.CandidatoMidiaBeta()
    m4.midia.url = "https://youtu.be/rejeitado1"
    m4.midia.titulo = "Vídeo Já Rejeitado"
    m4.midia.fonte = beta_pb2.FonteMidia.YOUTUBE

    # Item 5 sem URL (ignorado)
    m5 = beta_pb2.CandidatoMidiaBeta()

    escalada = croqui_pb2.Escalada(uid="esc-1")
    escalada.betas.add(
        url="https://blog.com/ja-aprovado",
        titulo="Blog Aprovado",
        fonte=beta_pb2.FonteMidia.BLOG,
    )

    curadoria = beta_pb2.CuradoriaBetasEscalada(escalada_uid="esc-1")
    curadoria.betas_nao_scorados.add().midia.url = "https://instagram.com/p/nao_scorado"
    curadoria.betas_nao_revisados.add().midia.url = "https://instagram.com/p/nao_revisado"
    curadoria.betas_rejeitados.add(
        url="https://www.youtube.com/watch?v=rejeitado1",
        titulo="Rejeitado",
        fonte=beta_pb2.FonteMidia.YOUTUBE,
    )

    urls_conhecidas = obter_urls_conhecidas_escalada(escalada, curadoria)
    assert "https://blog.com/ja-aprovado" in urls_conhecidas
    assert "https://instagram.com/p/nao_scorado" in urls_conhecidas
    assert "https://instagram.com/p/nao_revisado" in urls_conhecidas
    assert "https://youtube.com/watch?v=rejeitado1" in urls_conhecidas

    resultado = deduplicar_midias([[m1, m3, m4, m5], [m2]], urls_ja_conhecidas=urls_conhecidas)

    assert len(resultado) == 2

    instagram_item = next(m for m in resultado if "instagram.com" in m.midia.url)
    assert instagram_item.midia.url == "https://instagram.com/p/Cxyz123"
    assert instagram_item.midia.titulo == "Vídeo do Crux - DDG"
    assert instagram_item.match_multiplas_fontes is True
    assert instagram_item.match_nome_no_snippet is True
    assert list(instagram_item.snippets) == ["Trecho do Vertex", "Trecho do DuckDuckGo"]

    youtube_item = next(m for m in resultado if "youtube.com" in m.midia.url)
    assert youtube_item.midia.url == "https://youtube.com/watch?v=vid999"
    assert youtube_item.match_multiplas_fontes is False
    assert youtube_item.match_nome_no_snippet is True
    assert list(youtube_item.snippets) == ["Descrição do YouTube"]
