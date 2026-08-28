# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.deduplicador import normalizar_url, deduplicar_midias

def test_normalizar_url_instagram():
    url1 = "https://www.instagram.com/p/Cxyz123/?igsh=abc12345"
    url2 = "http://instagram.com/p/Cxyz123"
    url3 = "https://instagram.com/p/Cxyz123/"
    
    norm1 = normalizar_url(url1)
    norm2 = normalizar_url(url2)
    norm3 = normalizar_url(url3)

    assert norm1 == norm2 == norm3 == "https://instagram.com/p/Cxyz123"


def test_normalizar_url_youtube():
    url1 = "https://www.youtube.com/watch?v=vid123&feature=share"
    url2 = "https://youtu.be/vid123"
    url3 = "https://youtube.com/watch?v=vid123"

    norm1 = normalizar_url(url1)
    norm2 = normalizar_url(url2)
    norm3 = normalizar_url(url3)

    assert norm1 == norm2 == norm3 == "https://youtube.com/watch?v=vid123"


def test_deduplicar_midias_mescla_informacoes():
    # Item 1 do Vertex
    m1 = beta_pb2.MidiaBeta()
    m1.url = "https://www.instagram.com/p/Cxyz123/?utm_source=ig_web"
    m1.titulo = "Vídeo do Crux - Vertex"
    m1.thumbnail_url = "https://instagram.com/thumb1.jpg"
    m1.fonte = beta_pb2.FonteMidia.INSTAGRAM
    m1.match_nome_no_snippet = True
    m1.snippets.append("Trecho do Vertex")

    # Item 2 do DuckDuckGo (mesma URL base)
    m2 = beta_pb2.MidiaBeta()
    m2.url = "https://instagram.com/p/Cxyz123"
    m2.titulo = "Vídeo do Crux - DDG"
    m2.thumbnail_url = "" # Sem thumbnail
    m2.fonte = beta_pb2.FonteMidia.INSTAGRAM
    m2.match_nome_no_snippet = False
    m2.snippets.append("Trecho do DuckDuckGo")

    # Item 3 do YouTube (URL diferente)
    m3 = beta_pb2.MidiaBeta()
    m3.url = "https://youtube.com/watch?v=vid999"
    m3.titulo = "Vídeo YouTube"
    m3.thumbnail_url = "https://img.youtube.com/vi/vid999/hqdefault.jpg"
    m3.fonte = beta_pb2.FonteMidia.YOUTUBE
    m3.match_nome_no_snippet = True
    m3.snippets.append("Descrição do YouTube")

    resultado = deduplicar_midias([[m1, m3], [m2]])

    assert len(resultado) == 2
    
    # Valida item mesclado do Instagram
    instagram_item = next(m for m in resultado if "instagram.com" in m.url)
    assert instagram_item.url == "https://instagram.com/p/Cxyz123"
    assert instagram_item.thumbnail_url == "https://instagram.com/thumb1.jpg"
    assert instagram_item.match_multiplas_fontes is True
    assert instagram_item.match_nome_no_snippet is True
    assert len(instagram_item.snippets) == 2
    assert "Trecho do Vertex" in instagram_item.snippets
    assert "Trecho do DuckDuckGo" in instagram_item.snippets

    # Valida item único do YouTube
    youtube_item = next(m for m in resultado if "youtube.com" in m.url)
    assert youtube_item.url == "https://youtube.com/watch?v=vid999"
    assert youtube_item.match_multiplas_fontes is False
    assert youtube_item.match_nome_no_snippet is True
    assert len(youtube_item.snippets) == 1
