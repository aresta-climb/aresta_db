# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Extrator de postagens e relatos de escalada em blogs da web.
"""

import html
import re
from html.parser import HTMLParser
from typing import Any, cast

import requests
from ddgs import DDGS

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import (
    BuscadorWebProtocolo,
    ClienteHttpProtocolo,
)

DOMINIOS_EXCLUIDOS_BLOG: tuple[str, ...] = (
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com",
    "tiktok.com",
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
    """Adaptador padrão para busca textual via pacote ddgs."""

    def __init__(self, fabrica_ddgs: Any = DDGS) -> None:
        self._fabrica_ddgs = fabrica_ddgs

    def buscar_texto(self, query: str, max_resultados: int = 10) -> list[dict[str, str]]:
        with self._fabrica_ddgs() as ddgs:
            return [dict(item) for item in ddgs.text(query, max_results=max_resultados)]


class ExtratorBlog:
    """
    Extrator de relatos e descrições técnicas de escaladas em páginas de blog (FonteMidia.BLOG).
    Opera em dois estágios:
    1. Busca web ancorada excluindo redes sociais de vídeo/post curto.
    2. Download (com cache em memória por URL) e extração de janelas de texto (+/- 300 chars)
       ao redor das menções ao nome da via em páginas que contenham vocabulário de escalada.
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
        """Monta a query ancorada para localizar postagens de blog sobre a escalada."""
        partes = [f'"{nome_escalada}"']
        if nome_setor:
            partes.append(f'"{nome_setor}"')
        if nome_pico:
            partes.append(f'"{nome_pico}"')
        partes.append("(escalada OR boulder OR via OR croqui)")
        partes.extend(f"-site:{dominio}" for dominio in DOMINIOS_EXCLUIDOS_BLOG)
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
        Executa a busca de blogs, inspeciona o conteúdo das páginas retornadas e
        devolve candidatos que mencionem a escalada dentro de contexto de montanhismo/escalada.
        """
        query = self.montar_query(nome_escalada, nome_setor, nome_pico)
        try:
            resultados_busca = self._buscador.buscar_texto(query, max_resultados=max_resultados)
        except Exception as e:
            raise RuntimeError(f"Erro na busca de blogs: {e}")

        candidatos: list[beta_pb2.CandidatoMidiaBeta] = []
        for item in resultados_busca:
            link = item.get("href", "").strip()
            if not link:
                continue

            link_lower = link.lower()
            if any(dominio in link_lower for dominio in DOMINIOS_EXCLUIDOS_BLOG):
                continue

            pagina = self._obter_pagina_processada(link)
            if pagina is None:
                continue

            titulo_html, texto_limpo = pagina
            texto_lower = texto_limpo.lower()
            if not self._contem_vocabulario_escalada(texto_lower):
                continue

            janelas = self._extrair_janelas_de_contexto(texto_limpo, nome_escalada)
            if not janelas:
                continue

            candidato = beta_pb2.CandidatoMidiaBeta()
            candidato.midia.url = link
            candidato.midia.titulo = titulo_html or item.get("title", "")
            candidato.midia.fonte = beta_pb2.FonteMidia.BLOG
            candidato.match_nome_no_snippet = True
            candidato.snippets.extend(janelas)
            candidatos.append(candidato)

        return candidatos
