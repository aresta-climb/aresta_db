# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Provedor de previews visuais estilo WhatsApp para mídias de beta com cache offline persistente.
"""

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpProtocolo
from coleta_de_betas.extratores.deduplicador import normalizar_url

DIRETORIO_CACHE_PADRAO = Path.home() / ".cache" / "aresta" / "thumbnails_betas"


def obter_pixmap_fallback(fonte: int, largura: int = 120, altura: int = 90) -> QPixmap:
    """
    Gera um QPixmap com visual estilizado temático (YouTube, Instagram, Blog ou Mídia)
    para servir de fallback quando a thumbnail não estiver disponível.
    """
    pixmap = QPixmap(largura, altura)
    if fonte == beta_pb2.FonteMidia.INSTAGRAM:
        cor_fundo = QColor("#E1306C")
        texto = "Instagram"
    elif fonte == beta_pb2.FonteMidia.YOUTUBE:
        cor_fundo = QColor("#FF0000")
        texto = "YouTube"
    elif fonte == beta_pb2.FonteMidia.BLOG:
        cor_fundo = QColor("#2563EB")
        texto = "Blog"
    else:
        cor_fundo = QColor("#4B5563")
        texto = "Mídia"

    pixmap.fill(cor_fundo)
    painter = QPainter(pixmap)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), 0x0084, texto)
    painter.end()
    return pixmap


def extrair_id_video_youtube(url_midia: str) -> str:
    """Extrai o ID de vídeo do YouTube de URLs watch?v=, youtu.be/ ou /shorts/."""
    parsed = urlparse(url_midia.strip())
    netloc = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "youtu.be" in netloc:
        return path.split("/")[0]

    if "youtube.com" in netloc:
        qs = parse_qs(parsed.query)
        if qs.get("v"):
            return qs["v"][0]
        match_shorts = re.match(r"^(?:shorts|embed)/([^/?#]+)", path)
        if match_shorts:
            return match_shorts.group(1)

    return ""


class _ExtratorMetaOpenGraph(HTMLParser):
    """Extrai a primeira URL de imagem de meta tags OpenGraph (og:image / twitter:image)."""

    def __init__(self) -> None:
        super().__init__()
        self.url_imagem: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.url_imagem or tag.lower() != "meta":
            return
        mapa = {k.lower(): (v or "").strip() for k, v in attrs}
        chave_meta = (mapa.get("property") or mapa.get("name") or "").lower()
        conteudo = mapa.get("content", "")
        if chave_meta in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
            if conteudo:
                self.url_imagem = conteudo


def extrair_url_opengraph_html(conteudo_html: str, url_base: str) -> str:
    """Extrai e resolve a URL absoluta da imagem de preview OpenGraph a partir do HTML."""
    parser = _ExtratorMetaOpenGraph()
    parser.feed(conteudo_html)
    if not parser.url_imagem:
        return ""
    return urljoin(url_base, parser.url_imagem)


class ProvedorImagemAresta:
    """
    Resolve thumbnails de links de beta (YouTube, Instagram, Blogs) estilo preview do WhatsApp
    e mantém cache persistente em disco para acesso instantâneo e offline.
    """

    def __init__(
        self,
        diretorio_cache: Path | None = None,
        cliente_http: ClienteHttpProtocolo | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.diretorio_cache = diretorio_cache or DIRETORIO_CACHE_PADRAO
        self._cliente_http: ClienteHttpProtocolo = cliente_http or cast(
            ClienteHttpProtocolo, requests
        )
        self.timeout = timeout

    def _caminho_arquivo_cache(self, url_midia: str) -> Path:
        url_chave = normalizar_url(url_midia) or url_midia.strip()
        digest = hashlib.sha256(url_chave.encode("utf-8")).hexdigest()
        return self.diretorio_cache / f"{digest}.img"

    def _resolver_url_thumbnail(self, url_midia: str, fonte: int) -> str:
        video_id = extrair_id_video_youtube(url_midia)
        if video_id or fonte == beta_pb2.FonteMidia.YOUTUBE:
            if video_id:
                return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        try:
            resp_html = self._cliente_http.get(
                url_midia,
                headers={"User-Agent": "WhatsApp/2.24.0 ArestaBot/1.0"},
                timeout=self.timeout,
            )
            if resp_html.status_code == 200 and resp_html.text:
                return extrair_url_opengraph_html(resp_html.text, url_midia)
        except Exception:
            return ""
        return ""

    def obter_pixmap(
        self,
        url_midia: str,
        fonte: int,
        largura: int = 120,
        altura: int = 90,
    ) -> QPixmap:
        """
        Retorna o QPixmap da miniatura a partir do cache em disco ou faz o download/resolução
        e persiste no cache offline. Em caso de falha, retorna o fallback temático.
        """
        url_limpa = url_midia.strip()
        if not url_limpa:
            return obter_pixmap_fallback(fonte, largura, altura)

        arq_cache = self._caminho_arquivo_cache(url_limpa)
        if arq_cache.is_file():
            img_cache = QImage()
            if img_cache.loadFromData(arq_cache.read_bytes()):
                return QPixmap.fromImage(img_cache)

        url_thumb = self._resolver_url_thumbnail(url_limpa, fonte)
        if url_thumb:
            try:
                resp_img = self._cliente_http.get(
                    url_thumb,
                    headers={"User-Agent": "WhatsApp/2.24.0 ArestaBot/1.0"},
                    timeout=self.timeout,
                )
                if resp_img.status_code == 200 and resp_img.content:
                    imagem = QImage()
                    if imagem.loadFromData(resp_img.content):
                        self.diretorio_cache.mkdir(parents=True, exist_ok=True)
                        arq_cache.write_bytes(resp_img.content)
                        return QPixmap.fromImage(imagem)
            except Exception:
                pass

        return obter_pixmap_fallback(fonte, largura, altura)


class WorkerProvedorImagem(QThread):
    """
    Worker assíncrono para resolução e download de thumbnail sem bloquear a thread da UI.
    """

    imagem_carregada = Signal(QPixmap)

    def __init__(
        self,
        url_midia: str,
        fonte: int,
        provedor: ProvedorImagemAresta | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.url_midia = url_midia
        self.fonte = fonte
        self.provedor = provedor or ProvedorImagemAresta()

    def run(self) -> None:
        pixmap = self.provedor.obter_pixmap(self.url_midia, self.fonte)
        self.imagem_carregada.emit(pixmap)
