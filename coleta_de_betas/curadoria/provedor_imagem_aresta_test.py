# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage, QPixmap

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.provedor_imagem_aresta import (
    MAX_WORKERS_THUMBNAIL,
    ProvedorImagemAresta,
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
    cores_esperadas = {
        beta_pb2.FonteMidia.YOUTUBE: "#ff0000",
        beta_pb2.FonteMidia.INSTAGRAM: "#e1306c",
        beta_pb2.FonteMidia.BLOG: "#2563eb",
        beta_pb2.FonteMidia.TIKTOK: "#111827",
        beta_pb2.FonteMidia.FACEBOOK: "#1877f2",
        beta_pb2.FonteMidia.TWITTER: "#0f172a",
        beta_pb2.FonteMidia.REDDIT: "#ff4500",
        beta_pb2.FonteMidia.OUTRO_UGC: "#0d9488",
        beta_pb2.FonteMidia.INDEFINIDO: "#4b5563",
    }
    for fonte, cor_hex in cores_esperadas.items():
        pixmap = obter_pixmap_fallback(fonte, largura=100, altura=80)
        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.width() == 100
        assert pixmap.height() == 80
        assert pixmap.toImage().pixelColor(1, 1).name().lower() == cor_hex


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

    # Caso onde o GET do HTML ou o GET da imagem lança exceção de rede
    http.registrar_erro("https://blogescalada.com/erro-html", "Timeout HTML")
    pix_erro_html = provedor.obter_pixmap(
        "https://blogescalada.com/erro-html",
        beta_pb2.FonteMidia.BLOG,
        largura=90,
        altura=70,
    )
    assert pix_erro_html.width() == 90

    http.registrar_texto(
        "https://blogescalada.com/erro-img",
        '<html><head><meta property="og:image" content="https://blogescalada.com/quebrada.png"></head></html>',
        status_code=200,
    )
    http.registrar_erro("https://blogescalada.com/quebrada.png", "Timeout Imagem")
    pix_erro_img = provedor.obter_pixmap(
        "https://blogescalada.com/erro-img",
        beta_pb2.FonteMidia.BLOG,
        largura=90,
        altura=70,
    )
    assert pix_erro_img.width() == 90


def test_provedor_imagem_aresta_cache_ram_e_cache_negativo_evita_novas_requisicoes(
    tmp_path: Path, qtbot
) -> None:
    _ = qtbot
    http = ClienteHttpFake()
    png_bytes = _gerar_png_bytes(QColor("#228844"), largura=7, altura=6)
    url_ok = "https://blog.com/com-og"
    url_img = "https://blog.com/thumb.png"
    url_sem_og = "https://blog.com/sem-og"

    http.registrar_texto(
        url_ok,
        f'<html><head><meta property="og:image" content="{url_img}"></head></html>',
        status_code=200,
    )
    http.registrar_bytes(url_img, png_bytes, status_code=200)
    http.registrar_texto(url_sem_og, "<html><head></head></html>", status_code=200)

    provedor = ProvedorImagemAresta(diretorio_cache=tmp_path / "cache_ram", cliente_http=http)

    # Antes de resolver, obter_pixmap_imediato retorna None para URL desconhecida e fallback para vazio
    assert provedor.obter_pixmap_imediato(url_ok, beta_pb2.FonteMidia.BLOG) is None
    assert provedor.obter_pixmap_imediato("", beta_pb2.FonteMidia.BLOG) is not None

    # Resolve url_ok (2 GETs: HTML + imagem) -> passa a estar disponível imediatamente em RAM
    pix1 = provedor.obter_pixmap(url_ok, beta_pb2.FonteMidia.BLOG)
    assert pix1.width() == 7
    assert len(http.chamadas_get) == 2

    imediato_ok = provedor.obter_pixmap_imediato(url_ok, beta_pb2.FonteMidia.BLOG)
    assert imediato_ok is not None
    assert imediato_ok.width() == 7
    assert len(provedor._cache_pixmap_ram) == 1
    assert len(http.chamadas_get) == 2

    # Resolve url_sem_og (1 GET: HTML sem og:image) -> entra no cache negativo
    pix_falha_1 = provedor.obter_pixmap(
        url_sem_og, beta_pb2.FonteMidia.BLOG, largura=80, altura=60
    )
    assert pix_falha_1.width() == 80
    assert len(http.chamadas_get) == 3

    # Nova chamada para url_sem_og (imediata ou obter_pixmap) NÃO faz novo HTTP GET
    imediato_neg = provedor.obter_pixmap_imediato(
        url_sem_og, beta_pb2.FonteMidia.BLOG, largura=80, altura=60
    )
    assert imediato_neg is not None
    assert imediato_neg.width() == 80
    pix_falha_2 = provedor.obter_pixmap(
        url_sem_og, beta_pb2.FonteMidia.BLOG, largura=80, altura=60
    )
    assert pix_falha_2.width() == 80
    assert len(http.chamadas_get) == 3


def test_solicitar_pixmap_assincrono_usa_pool_4_workers_sem_io_disco_na_ui_thread(
    tmp_path: Path, qtbot
) -> None:
    assert MAX_WORKERS_THUMBNAIL == 4
    http = ClienteHttpFake()
    png_bytes = _gerar_png_bytes(QColor("#ABCDEF"), largura=5, altura=5)
    url_yt = "https://www.youtube.com/watch?v=xyz"
    http.registrar_bytes("https://i.ytimg.com/vi/xyz/hqdefault.jpg", png_bytes, status_code=200)

    cache_dir = tmp_path / "cache_worker"
    provedor = ProvedorImagemAresta(diretorio_cache=cache_dir, cliente_http=http)
    assert provedor.max_workers == 4

    recebidos_1: list[QPixmap] = []
    recebidos_2: list[QPixmap] = []
    recebidos_cancelado: list[QPixmap] = []

    chave_1 = provedor.solicitar_pixmap_assincrono(
        url_yt, beta_pb2.FonteMidia.YOUTUBE, recebidos_1.append
    )
    chave_2 = provedor.solicitar_pixmap_assincrono(
        url_yt, beta_pb2.FonteMidia.YOUTUBE, recebidos_2.append
    )
    chave_cancel = provedor.solicitar_pixmap_assincrono(
        url_yt, beta_pb2.FonteMidia.YOUTUBE, recebidos_cancelado.append
    )
    assert chave_1 != ""
    assert chave_1 == chave_2 == chave_cancel

    provedor.cancelar_callback_assincrono(chave_cancel, recebidos_cancelado.append)
    provedor.cancelar_callback_assincrono("chave_inexistente", recebidos_cancelado.append)

    qtbot.waitUntil(lambda: len(recebidos_1) == 1 and len(recebidos_2) == 1, timeout=3000)
    assert not recebidos_1[0].isNull()
    assert recebidos_1[0].width() == 5
    assert recebidos_2[0].width() == 5
    assert len(recebidos_cancelado) == 0
    assert len(http.chamadas_get) == 1

    # Quando já está em RAM, solicitar_pixmap_assincrono entrega imediatamente de forma síncrona
    recebidos_imediato: list[QPixmap] = []
    chave_imediata = provedor.solicitar_pixmap_assincrono(
        url_yt, beta_pb2.FonteMidia.YOUTUBE, recebidos_imediato.append
    )
    assert chave_imediata == ""
    assert len(recebidos_imediato) == 1
    assert recebidos_imediato[0].width() == 5

    # Um novo provedor com cache frio em RAM NÃO deve ler do disco em obter_pixmap_imediato (zero I/O na UI thread)
    provedor_frio = ProvedorImagemAresta(
        diretorio_cache=cache_dir, cliente_http=ClienteHttpFake()
    )
    assert provedor_frio.obter_pixmap_imediato(url_yt, beta_pb2.FonteMidia.YOUTUBE) is None

    # E carrega do cache em disco em background via pool de workers
    recebidos_disco: list[QPixmap] = []
    provedor_frio.solicitar_pixmap_assincrono(
        url_yt, beta_pb2.FonteMidia.YOUTUBE, recebidos_disco.append
    )
    qtbot.waitUntil(lambda: len(recebidos_disco) == 1, timeout=3000)
    assert recebidos_disco[0].width() == 5

    # Caso sem thumbnail (fallback assíncrono)
    recebidos_fb: list[QPixmap] = []
    provedor_frio.solicitar_pixmap_assincrono(
        "https://instagram.com/p/sem_thumb",
        beta_pb2.FonteMidia.INSTAGRAM,
        recebidos_fb.append,
        largura=70,
        altura=50,
    )
    qtbot.waitUntil(lambda: len(recebidos_fb) == 1, timeout=3000)
    assert recebidos_fb[0].width() == 70
    assert recebidos_fb[0].height() == 50

    provedor.encerrar_workers(esperar=True)
    provedor_frio.encerrar_workers(esperar=True)
