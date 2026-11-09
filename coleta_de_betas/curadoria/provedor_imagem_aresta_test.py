# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage, QPixmap

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.provedor_imagem_aresta import (
    ProvedorImagemAresta,
    WorkerProvedorImagem,
    extrair_id_video_youtube,
    extrair_url_opengraph_html,
    obter_pixmap_fallback,
)
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpFake


def _gerar_png_bytes(cor: QColor, largura: int = 4, altura: int = 4) -> bytes:
    img = QImage(largura, altura, QImage.Format.Format_RGB32)
    img.fill(cor)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba.data())


def test_obter_pixmap_fallback_para_todas_as_fontes(qtbot) -> None:
    _ = qtbot
    for fonte in (
        beta_pb2.FonteMidia.YOUTUBE,
        beta_pb2.FonteMidia.INSTAGRAM,
        beta_pb2.FonteMidia.BLOG,
        beta_pb2.FonteMidia.INDEFINIDO,
    ):
        pixmap = obter_pixmap_fallback(fonte, largura=100, altura=80)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.width() == 100
        assert pixmap.height() == 80


def test_extrair_id_video_youtube_formatos_variados() -> None:
    assert extrair_id_video_youtube("https://www.youtube.com/watch?v=abc123XYZ") == "abc123XYZ"
    assert extrair_id_video_youtube("https://youtu.be/abc123XYZ?t=10") == "abc123XYZ"
    assert extrair_id_video_youtube("https://www.youtube.com/shorts/short999") == "short999"
    assert extrair_id_video_youtube("https://youtube.com/watch?feature=share") == ""
    assert extrair_id_video_youtube("https://blog.com/post") == ""


def test_extrair_url_opengraph_html_og_image_e_twitter_image() -> None:
    html_og = """
    <html>
      <head>
        <meta property="og:title" content="Post"/>
        <meta property="og:image" content="https://cdn.blog.com/capa.jpg"/>
      </head>
    </html>
    """
    assert (
        extrair_url_opengraph_html(html_og, "https://blog.com/post")
        == "https://cdn.blog.com/capa.jpg"
    )

    html_twitter_relativo = """
    <html>
      <head>
        <meta content="/imagens/preview.png" name="twitter:image"/>
      </head>
    </html>
    """
    assert (
        extrair_url_opengraph_html(html_twitter_relativo, "https://blog.com/artigos/via-1")
        == "https://blog.com/imagens/preview.png"
    )

    assert extrair_url_opengraph_html("<html><head></head></html>", "https://blog.com") == ""


def test_provedor_imagem_aresta_resolve_youtube_e_persiste_cache_offline(
    tmp_path: Path, qtbot
) -> None:
    _ = qtbot
    http = ClienteHttpFake()
    png_bytes = _gerar_png_bytes(QColor("#00FF00"), largura=6, altura=6)
    url_midia = "https://www.youtube.com/watch?v=vid777"
    url_thumb_yt = "https://i.ytimg.com/vi/vid777/hqdefault.jpg"
    http.registrar_bytes(url_thumb_yt, png_bytes, status_code=200)

    cache_dir = tmp_path / "cache_thumbs"
    provedor = ProvedorImagemAresta(diretorio_cache=cache_dir, cliente_http=http)

    pixmap_1 = provedor.obter_pixmap(url_midia, beta_pb2.FonteMidia.YOUTUBE)
    assert not pixmap_1.isNull()
    assert pixmap_1.width() == 6
    assert len(http.chamadas_get) == 1

    # Segunda chamada com URL equivalente (youtu.be) deve ler do cache offline sem rede
    http_offline = ClienteHttpFake()
    http_offline.registrar_erro(url_thumb_yt, "Sem internet")
    provedor_offline = ProvedorImagemAresta(diretorio_cache=cache_dir, cliente_http=http_offline)

    pixmap_2 = provedor_offline.obter_pixmap(
        "https://youtu.be/vid777", beta_pb2.FonteMidia.YOUTUBE
    )
    assert not pixmap_2.isNull()
    assert pixmap_2.width() == 6
    assert len(http_offline.chamadas_get) == 0


def test_provedor_imagem_aresta_resolve_opengraph_blog_e_instagram_e_fallback(
    tmp_path: Path, qtbot
) -> None:
    _ = qtbot
    http = ClienteHttpFake()
    png_bytes = _gerar_png_bytes(QColor("#112233"), largura=8, altura=5)

    url_blog = "https://blogescalada.com/via-classica"
    url_og_img = "https://blogescalada.com/media/foto-via.png"
    http.registrar_texto(
        url_blog,
        f'<html><head><meta property="og:image" content="{url_og_img}"></head></html>',
        status_code=200,
    )
    http.registrar_bytes(url_og_img, png_bytes, status_code=200)

    provedor = ProvedorImagemAresta(diretorio_cache=tmp_path / "cache", cliente_http=http)
    pixmap_blog = provedor.obter_pixmap(url_blog, beta_pb2.FonteMidia.BLOG)
    assert not pixmap_blog.isNull()
    assert pixmap_blog.width() == 8
    assert pixmap_blog.height() == 5

    # Caso sem URL ou com falha de rede retorna fallback temático
    pixmap_vazio = provedor.obter_pixmap("", beta_pb2.FonteMidia.BLOG, largura=90, altura=70)
    assert pixmap_vazio.width() == 90
    assert pixmap_vazio.height() == 70

    pixmap_falha = provedor.obter_pixmap(
        "https://instagram.com/p/inexistente",
        beta_pb2.FonteMidia.INSTAGRAM,
        largura=90,
        altura=70,
    )
    assert pixmap_falha.width() == 90
    assert pixmap_falha.height() == 70


def test_worker_provedor_imagem_emite_sinal_assincrono(tmp_path: Path, qtbot) -> None:
    http = ClienteHttpFake()
    png_bytes = _gerar_png_bytes(QColor("#ABCDEF"), largura=5, altura=5)
    http.registrar_bytes("https://i.ytimg.com/vi/xyz/hqdefault.jpg", png_bytes, status_code=200)

    provedor = ProvedorImagemAresta(diretorio_cache=tmp_path / "cache_worker", cliente_http=http)
    worker = WorkerProvedorImagem(
        "https://www.youtube.com/watch?v=xyz",
        beta_pb2.FonteMidia.YOUTUBE,
        provedor=provedor,
    )

    recebidos: list[QPixmap] = []
    worker.imagem_carregada.connect(recebidos.append)
    worker.run()

    assert len(recebidos) == 1
    assert recebidos[0].width() == 5
