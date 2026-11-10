# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Provedor de previews visuais estilo WhatsApp para mídias de beta com cache offline persistente.
"""

import hashlib
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpProtocolo
from coleta_de_betas.extratores.deduplicador import normalizar_url

DIRETORIO_CACHE_PADRAO = Path.home() / ".cache" / "aresta" / "thumbnails_betas"
MAX_WORKERS_THUMBNAIL = 4


_ESTILO_FALLBACK_POR_FONTE: dict[int, tuple[str, str]] = {
    beta_pb2.FonteMidia.YOUTUBE: ("#FF0000", "YouTube"),
    beta_pb2.FonteMidia.INSTAGRAM: ("#E1306C", "Instagram"),
    beta_pb2.FonteMidia.BLOG: ("#2563EB", "Blog"),
    beta_pb2.FonteMidia.TIKTOK: ("#111827", "TikTok"),
    beta_pb2.FonteMidia.FACEBOOK: ("#1877F2", "Facebook"),
    beta_pb2.FonteMidia.TWITTER: ("#0F172A", "Twitter"),
    beta_pb2.FonteMidia.REDDIT: ("#FF4500", "Reddit"),
    beta_pb2.FonteMidia.OUTRO_UGC: ("#0D9488", "Outro UGC"),
}


_CACHE_FALLBACK_PIXMAP: dict[tuple[int, int, int], QPixmap] = {}


def obter_pixmap_fallback(fonte: int, largura: int = 120, altura: int = 90) -> QPixmap:
    """
    Gera um QPixmap com visual estilizado temático (YouTube, Instagram, Blog, TikTok,
    Facebook, Twitter, Reddit, Outro UGC ou Mídia) para servir de fallback quando a
    thumbnail não estiver disponível.
    """
    chave_fb = (int(fonte), int(largura), int(altura))
    cached = _CACHE_FALLBACK_PIXMAP.get(chave_fb)
    if cached is not None and not cached.isNull():
        return cached
    pixmap = QPixmap(largura, altura)
    cor_hex, texto = _ESTILO_FALLBACK_POR_FONTE.get(fonte, ("#4B5563", "Mídia"))
    cor_fundo = QColor(cor_hex)

    pixmap.fill(cor_fundo)
    painter = QPainter(pixmap)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), 0x0084, texto)
    painter.end()
    _CACHE_FALLBACK_PIXMAP[chave_fb] = pixmap
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


class _PonteSinalThumbnail(QObject):
    """Ponte de sinal Qt para entregar QImage decodificada das worker threads para a UI thread."""

    imagem_pronta = Signal(str, int, QImage)


class ProvedorImagemAresta:
    """
    Resolve thumbnails de links de beta (YouTube, Instagram, Blogs) estilo preview do WhatsApp
    com cache persistente em disco e pool de 4 worker threads para não bloquear a UI thread.
    """

    def __init__(
        self,
        diretorio_cache: Path | None = None,
        cliente_http: ClienteHttpProtocolo | None = None,
        timeout: float = 5.0,
        max_workers: int = MAX_WORKERS_THUMBNAIL,
    ) -> None:
        self.diretorio_cache = diretorio_cache or DIRETORIO_CACHE_PADRAO
        self._cliente_http: ClienteHttpProtocolo = cliente_http or cast(
            ClienteHttpProtocolo, requests
        )
        self.timeout = timeout
        self.max_workers = max(1, int(max_workers))
        self._lock = threading.Lock()
        self._cache_pixmap_ram: dict[str, QPixmap] = {}
        self._urls_sem_thumbnail: set[str] = set()
        self._callbacks_pendentes: dict[str, list[tuple[Callable[[QPixmap], Any], int, int]]] = {}
        self._chaves_em_voo: set[str] = set()
        self._executor: ThreadPoolExecutor | None = None
        self._ponte_sinal = _PonteSinalThumbnail()
        self._ponte_sinal.imagem_pronta.connect(self._entregar_imagem_na_ui_thread)

    @staticmethod
    def _chave_url(url_midia: str) -> str:
        return normalizar_url(url_midia) or url_midia.strip()

    def _caminho_arquivo_cache(self, url_midia: str) -> Path:
        url_chave = self._chave_url(url_midia)
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

    def obter_pixmap_imediato(
        self,
        url_midia: str,
        fonte: int,
        largura: int = 120,
        altura: int = 90,
    ) -> QPixmap | None:
        """
        Retorna imediatamente o QPixmap sem I/O de disco ou rede quando a URL for vazia,
        já estiver no cache em RAM ou no cache negativo da sessão.
        Retorna None quando ainda for necessário consultar o disco ou a rede em background.
        """
        url_limpa = url_midia.strip()
        if not url_limpa:
            return obter_pixmap_fallback(fonte, largura, altura)

        chave = self._chave_url(url_limpa)
        with self._lock:
            pix_ram = self._cache_pixmap_ram.get(chave)
            negativo = chave in self._urls_sem_thumbnail

        if pix_ram is not None and not pix_ram.isNull():
            return pix_ram

        if negativo:
            return obter_pixmap_fallback(fonte, largura, altura)

        return None

    def _carregar_qimage_disco_ou_rede(self, url_limpa: str, chave: str, fonte: int) -> QImage:
        arq_cache = self._caminho_arquivo_cache(url_limpa)
        if arq_cache.is_file():
            dados_disco = arq_cache.read_bytes()
            img_cache = QImage()
            if img_cache.loadFromData(dados_disco):
                return img_cache

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
                        return imagem
            except Exception:
                pass

        with self._lock:
            self._urls_sem_thumbnail.add(chave)
        return QImage()

    def obter_pixmap(
        self,
        url_midia: str,
        fonte: int,
        largura: int = 120,
        altura: int = 90,
    ) -> QPixmap:
        """
        Retorna o QPixmap da miniatura a partir do cache em RAM/disco ou faz o download/resolução
        e persiste no cache offline. Em caso de falha, registra no cache negativo da sessão e
        retorna o fallback temático.
        """
        imediato = self.obter_pixmap_imediato(url_midia, fonte, largura, altura)
        if imediato is not None:
            return imediato

        url_limpa = url_midia.strip()
        chave = self._chave_url(url_limpa)
        imagem = self._carregar_qimage_disco_ou_rede(url_limpa, chave, fonte)
        if not imagem.isNull():
            pix_rede = QPixmap.fromImage(imagem)
            with self._lock:
                self._cache_pixmap_ram[chave] = pix_rede
            return pix_rede

        return obter_pixmap_fallback(fonte, largura, altura)

    def solicitar_pixmap_assincrono(
        self,
        url_midia: str,
        fonte: int,
        callback: Callable[[QPixmap], Any],
        largura: int = 120,
        altura: int = 90,
    ) -> str:
        """
        Agenda o carregamento de thumbnail no pool de 4 worker threads (disco ou rede)
        e invoca `callback(pixmap)` na thread de UI quando pronto.
        """
        imediato = self.obter_pixmap_imediato(url_midia, fonte, largura, altura)
        if imediato is not None:
            callback(imediato)
            return ""

        url_limpa = url_midia.strip()
        chave = self._chave_url(url_limpa)
        disparar = False
        with self._lock:
            self._callbacks_pendentes.setdefault(chave, []).append((callback, largura, altura))
            if chave not in self._chaves_em_voo:
                self._chaves_em_voo.add(chave)
                disparar = True
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="thumb_aresta",
                )
            executor = self._executor

        if disparar:
            executor.submit(self._executar_worker_thumbnail, url_limpa, chave, fonte)
        return chave

    def _executar_worker_thumbnail(self, url_limpa: str, chave: str, fonte: int) -> None:
        imagem = self._carregar_qimage_disco_ou_rede(url_limpa, chave, fonte)
        self._ponte_sinal.imagem_pronta.emit(chave, int(fonte), imagem)

    def _entregar_imagem_na_ui_thread(self, chave: str, fonte: int, imagem: QImage) -> None:
        with self._lock:
            self._chaves_em_voo.discard(chave)
            pendentes = list(self._callbacks_pendentes.pop(chave, []))

        pix_valido: QPixmap | None = None
        if not imagem.isNull():
            pix_valido = QPixmap.fromImage(imagem)
            with self._lock:
                self._cache_pixmap_ram[chave] = pix_valido

        for cb, largura, altura in pendentes:
            cb(
                pix_valido
                if pix_valido is not None
                else obter_pixmap_fallback(fonte, largura, altura)
            )

    def cancelar_callback_assincrono(
        self,
        chave: str,
        callback: Callable[[QPixmap], Any],
    ) -> None:
        """Remove um callback específico da fila de espera de uma URL."""
        with self._lock:
            lista = self._callbacks_pendentes.get(chave)
            if lista is not None:
                self._callbacks_pendentes[chave] = [
                    item for item in lista if item[0] != callback
                ]

    def encerrar_workers(self, esperar: bool = False) -> None:
        """Cancela callbacks pendentes e encerra o pool de worker threads."""
        with self._lock:
            self._callbacks_pendentes.clear()
            self._chaves_em_voo.clear()
            executor = self._executor
            self._executor = None
        if executor is not None:
            executor.shutdown(wait=esperar, cancel_futures=True)
