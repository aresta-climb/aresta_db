# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Extrator web unificado de betas de escalada (YouTube, Instagram, TikTok, Facebook,
Twitter/X, Reddit, portais UGC e Blogs) via ddgs com prevenção de rate-limit.
"""

import html
import re
import time
from collections.abc import Callable, Sequence
from html.parser import HTMLParser
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import requests
from ddgs import DDGS

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import (
    BuscadorWebProtocolo,
    ClienteHttpProtocolo,
)

BACKENDS_WEB_PADRAO: tuple[str, ...] = (
    "yahoo",
    "duckduckgo",
    "startpage",
    "brave",
)

DOMINIOS_OUTRO_UGC: tuple[str, ...] = (
    "thecrag.com",
    "mountainproject.com",
    "8a.nu",
    "wikiloc.com",
    "escaladas.com.br",
    "summitpost.org",
    "ukclimbing.com",
    "27crags.com",
    "vertical-life.info",
    "vimeo.com",
    "dailymotion.com",
)

FONTES_REDE_SOCIAL_DIRETA: frozenset[int] = frozenset(
    {
        beta_pb2.FonteMidia.YOUTUBE,
        beta_pb2.FonteMidia.INSTAGRAM,
        beta_pb2.FonteMidia.TIKTOK,
        beta_pb2.FonteMidia.FACEBOOK,
        beta_pb2.FonteMidia.TWITTER,
    }
)

VOCABULARIO_ESCALADA: tuple[str, ...] = (
    "escalada",
    "boulder",
    "via",
    "vias",
    "setor",
    "croqui",
    "enfiada",
    "enfiadas",
    "chapeleta",
    "chapeletas",
    "crux",
    "grampo",
    "proteção",
    "fenda",
    "diedro",
    "agarrão",
    "reglete",
    "cume",
    "rapel",
    "cordada",
)

JANELA_CONTEXTO_CARACTERES = 300
MAX_SNIPPETS_POR_PAGINA = 5


def classificar_fonte_url(url: str) -> beta_pb2.FonteMidia.Enum.ValueType | None:
    """
    Classifica uma URL pública em uma das 8 categorias de FonteMidia.Enum.
    Retorna None caso a URL seja inválida ou aponte para uma página genérica
    de perfil/canal sem post ou vídeo específico.
    """
    url_limpa = url.strip()
    if not url_limpa:
        return None
    parsed = urlparse(url_limpa)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return None

    netloc = parsed.netloc.lower()
    path = parsed.path.strip("/")
    qs = parse_qs(parsed.query)

    # 1. YouTube
    if "youtu.be" in netloc:
        return beta_pb2.FonteMidia.YOUTUBE if path else None
    if "youtube.com" in netloc:
        if qs.get("v") or path.startswith(("shorts/", "embed/", "live/", "v/")):
            return beta_pb2.FonteMidia.YOUTUBE
        return None

    # 2. Instagram
    if "instagram.com" in netloc:
        if re.match(r"^(?:[^/]+/)?(?:p|reel|reels|tv)/[^/?#]+", path):
            return beta_pb2.FonteMidia.INSTAGRAM
        return None

    # 3. TikTok
    if "tiktok.com" in netloc:
        if ("vm.tiktok.com" in netloc or "vt.tiktok.com" in netloc) and path:
            return beta_pb2.FonteMidia.TIKTOK
        if "/video/" in f"/{path}/":
            return beta_pb2.FonteMidia.TIKTOK
        return None

    # 4. Facebook
    if "fb.watch" in netloc:
        return beta_pb2.FonteMidia.FACEBOOK if path else None
    if "facebook.com" in netloc or "fb.com" in netloc:
        segmentos_fb = ("/posts/", "/videos/", "/reel/", "/permalink/", "/photos/")
        if any(seg in f"/{path}/" for seg in segmentos_fb):
            return beta_pb2.FonteMidia.FACEBOOK
        if path in ("watch", "story.php", "permalink.php") and (
            qs.get("v") or qs.get("story_fbid") or qs.get("id")
        ):
            return beta_pb2.FonteMidia.FACEBOOK
        return None

    # 5. Twitter / X
    if netloc in ("twitter.com", "www.twitter.com", "x.com", "www.x.com", "mobile.twitter.com"):
        if "/status/" in f"/{path}/":
            return beta_pb2.FonteMidia.TWITTER
        return None

    # 6. Reddit
    if "redd.it" in netloc:
        return beta_pb2.FonteMidia.REDDIT if path else None
    if "reddit.com" in netloc:
        if "/comments/" in f"/{path}/":
            return beta_pb2.FonteMidia.REDDIT
        return None

    # 7. Portais e plataformas UGC de escalada/montanhismo/vídeo
    if any(dom in netloc for dom in DOMINIOS_OUTRO_UGC):
        return beta_pb2.FonteMidia.OUTRO_UGC

    # 8. Demais sites e portais web -> Blog
    return beta_pb2.FonteMidia.BLOG


class _ExtratorTextoHtml(HTMLParser):
    """Extrai o título e o texto limpo de um documento HTML ignorando scripts e estilos."""

    def __init__(self) -> None:
        super().__init__()
        self._tags_ignoradas: int = 0
        self._em_titulo: bool = False
        self.partes_titulo: list[str] = []
        self.partes_texto: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        _ = attrs
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg", "head"):
            if tag_lower != "head":
                self._tags_ignoradas += 1
        elif tag_lower == "title":
            self._em_titulo = True

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self._tags_ignoradas = max(0, self._tags_ignoradas - 1)
        elif tag_lower == "title":
            self._em_titulo = False
        elif tag_lower in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "article", "section"):
            self.partes_texto.append(" ")

    def handle_data(self, data: str) -> None:
        if self._em_titulo:
            self.partes_titulo.append(data)
        elif self._tags_ignoradas == 0:
            self.partes_texto.append(data)


def extrair_titulo_e_texto_html(conteudo_html: str) -> tuple[str, str]:
    """Retorna (titulo, texto_limpo) extraídos de um documento HTML."""
    parser = _ExtratorTextoHtml()
    parser.feed(conteudo_html)
    titulo = re.sub(r"\s+", " ", html.unescape("".join(parser.partes_titulo))).strip()
    texto = re.sub(r"\s+", " ", html.unescape("".join(parser.partes_texto))).strip()
    return titulo, texto


class _BuscadorDuckDuckGoPadrao:
    """
    Adaptador padrão para busca textual via pacote ddgs com rotação round-robin
    entre motores de busca web reais e controle de cadência (pacing) anti-rate-limit.
    """

    def __init__(
        self,
        fabrica_ddgs: Any = DDGS,
        backends: Sequence[str] = BACKENDS_WEB_PADRAO,
        regiao: str = "br-pt",
        intervalo_minimo_s: float = 0.6,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._fabrica_ddgs = fabrica_ddgs
        self._backends = tuple(backends) if backends else BACKENDS_WEB_PADRAO
        self._regiao = regiao
        self._intervalo_minimo_s = intervalo_minimo_s
        self._relogio = relogio
        self._dormir = dormir
        self._indice_backend: int = 0
        self._ultima_requisicao_s: float | None = None

    def _aguardar_pacing(self) -> None:
        if self._intervalo_minimo_s > 0 and self._ultima_requisicao_s is not None:
            decorrido = self._relogio() - self._ultima_requisicao_s
            if decorrido < self._intervalo_minimo_s:
                self._dormir(self._intervalo_minimo_s - decorrido)
        self._ultima_requisicao_s = self._relogio()

    def buscar_texto(self, query: str, max_resultados: int = 10) -> list[dict[str, str]]:
        ultimo_erro: Exception | None = None
        total_backends = len(self._backends)

        for _ in range(total_backends):
            backend_atual = self._backends[self._indice_backend % total_backends]
            self._indice_backend = (self._indice_backend + 1) % total_backends
            self._aguardar_pacing()

            try:
                with self._fabrica_ddgs() as ddgs:
                    itens = ddgs.text(
                        query,
                        region=self._regiao,
                        backend=backend_atual,
                        max_results=max_resultados,
                    )
                    lista = [dict(item) for item in itens]
                    if lista:
                        return lista
            except Exception as e:
                msg = str(e).lower()
                if "no results found" in msg:
                    continue
                ultimo_erro = e
                continue

        if ultimo_erro is not None:
            raise ultimo_erro
        return []


class ExtratorBlog:
    """
    Extrator web unificado de betas de escalada que executa 1 única busca aberta por via
    e roteia/classifica os resultados entre as 8 categorias de FonteMidia.Enum:
    - Redes sociais e vídeo (YOUTUBE, INSTAGRAM, TIKTOK, FACEBOOK, TWITTER): usa título + snippet.
    - Páginas textuais e comunidades (BLOG, REDDIT, OUTRO_UGC): baixa HTML (com cache em memória
      por URL), valida vocabulário de escalada e extrai janelas de +/- 300 chars ao redor do nome
      da via (com fallback para o snippet da busca caso o portal bloqueie scraping direto).
    """

    def __init__(
        self,
        buscador: BuscadorWebProtocolo | None = None,
        cliente_http: ClienteHttpProtocolo | None = None,
    ) -> None:
        self._buscador: BuscadorWebProtocolo = buscador or _BuscadorDuckDuckGoPadrao()
        self._cliente_http: ClienteHttpProtocolo = cliente_http or cast(
            ClienteHttpProtocolo, requests
        )
        self._cache_paginas: dict[str, tuple[str, str] | None] = {}

    def montar_query(self, nome_escalada: str, nome_setor: str = "", nome_pico: str = "") -> str:
        """Monta uma única query aberta para localizar mídias e relatos sobre a escalada."""
        partes = [f'"{nome_escalada}"']
        if nome_setor:
            partes.append(nome_setor)
        if nome_pico:
            partes.append(f'"{nome_pico}"')
        partes.append("escalada")
        return " ".join(partes)

    def _obter_pagina_processada(self, url: str) -> tuple[str, str] | None:
        """Baixa e extrai (titulo, texto) da URL com cache em memória."""
        if url in self._cache_paginas:
            return self._cache_paginas[url]

        try:
            resposta = self._cliente_http.get(
                url,
                headers={"User-Agent": "ArestaBot/1.0 (+https://aresta.org)"},
                timeout=10,
            )
        except Exception:
            self._cache_paginas[url] = None
            return None

        if resposta.status_code != 200 or not resposta.text:
            self._cache_paginas[url] = None
            return None

        processado = extrair_titulo_e_texto_html(resposta.text)
        self._cache_paginas[url] = processado
        return processado

    @staticmethod
    def _contem_vocabulario_escalada(texto_lower: str) -> bool:
        return any(termo in texto_lower for termo in VOCABULARIO_ESCALADA)

    @staticmethod
    def _extrair_janelas_de_contexto(texto: str, nome_escalada: str) -> list[str]:
        padrao = re.compile(re.escape(nome_escalada.strip()), re.IGNORECASE)
        janelas: list[str] = []
        for match in padrao.finditer(texto):
            inicio = max(0, match.start() - JANELA_CONTEXTO_CARACTERES)
            fim = min(len(texto), match.end() + JANELA_CONTEXTO_CARACTERES)
            trecho = texto[inicio:fim].strip()
            if trecho and trecho not in janelas:
                janelas.append(trecho)
            if len(janelas) >= MAX_SNIPPETS_POR_PAGINA:
                break
        return janelas

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
    ) -> list[beta_pb2.CandidatoMidiaBeta]:
        """
        Executa 1 busca web aberta para a escalada e classifica os resultados nas 8 categorias
        de FonteMidia.Enum.
        """
        query = self.montar_query(nome_escalada, nome_setor, nome_pico)
        try:
            resultados_busca = self._buscador.buscar_texto(query, max_resultados=max_resultados)
        except Exception as e:
            raise RuntimeError(f"Erro na busca de blogs: {e}")

        termo_lower = nome_escalada.lower().strip()
        candidatos: list[beta_pb2.CandidatoMidiaBeta] = []

        for item in resultados_busca:
            link = item.get("href", "").strip()
            fonte = classificar_fonte_url(link)
            if fonte is None:
                continue

            titulo_busca = item.get("title", "").strip()
            body_busca = item.get("body", "").strip()
            match_busca = bool(termo_lower and termo_lower in f"{titulo_busca} {body_busca}".lower())

            if fonte in FONTES_REDE_SOCIAL_DIRETA:
                candidato = beta_pb2.CandidatoMidiaBeta()
                candidato.midia.url = link
                candidato.midia.titulo = titulo_busca
                candidato.midia.fonte = fonte
                candidato.match_nome_no_snippet = match_busca
                if body_busca:
                    candidato.snippets.append(body_busca)
                candidatos.append(candidato)
                continue

            # Páginas textuais e comunidades (BLOG, REDDIT, OUTRO_UGC)
            pagina = self._obter_pagina_processada(link)
            if pagina is not None:
                titulo_html, texto_limpo = pagina
                if self._contem_vocabulario_escalada(texto_limpo.lower()):
                    janelas = self._extrair_janelas_de_contexto(texto_limpo, nome_escalada)
                    if janelas:
                        candidato = beta_pb2.CandidatoMidiaBeta()
                        candidato.midia.url = link
                        candidato.midia.titulo = titulo_html or titulo_busca
                        candidato.midia.fonte = fonte
                        candidato.match_nome_no_snippet = True
                        candidato.snippets.extend(janelas)
                        candidatos.append(candidato)
                continue

            # Fallback quando portal de comunidade (REDDIT / OUTRO_UGC) bloqueia HTTP direto,
            # mas o snippet da busca já menciona explicitamente a escalada
            if fonte in (beta_pb2.FonteMidia.REDDIT, beta_pb2.FonteMidia.OUTRO_UGC) and match_busca:
                candidato = beta_pb2.CandidatoMidiaBeta()
                candidato.midia.url = link
                candidato.midia.titulo = titulo_busca
                candidato.midia.fonte = fonte
                candidato.match_nome_no_snippet = True
                if body_busca:
                    candidato.snippets.append(body_busca)
                candidatos.append(candidato)

        return candidatos
