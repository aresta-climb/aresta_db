# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Extrator web unificado de betas de escalada (YouTube, Instagram, TikTok, Facebook,
Twitter/X, Reddit, portais UGC e Blogs) via ddgs com sessão TLS persistente,
5 queries identificadas por escalada, sanitização, matching bidirecional de espaços/typos,
blocklist de agregadores e auditoria de descartes em betas_rejeitados.
"""

import re
import threading
import time
import unicodedata
from collections.abc import Callable, Sequence
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qs, urlparse

import primp
from ddgs import DDGS
from ddgs.engines.yahoo import Yahoo

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import (
    BuscadorWebProtocolo,
    ClienteHttpProtocolo,
)
from coleta_de_betas.extratores.deduplicador import normalizar_url

BACKENDS_WEB_PADRAO: tuple[str, ...] = (
    "yahoo",
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

DOMINIOS_BLOQUEADOS: tuple[str, ...] = (
    "scribd.com",
    "ptdocz.com",
    "doceru.com",
    "slideshare.net",
    "issuu.com",
    "academia.edu",
    "researchgate.net",
    "thecrag.com",
    "escaladas.com.br",
    "wikiloc.com",
    "mountainproject.com",
    "8a.nu",
    "27crags.com",
    "thetopo.com",
    "vertical-life.info",
    "summitpost.org",
    "ukclimbing.com",
    "tripadvisor.com",
    "tripadvisor.com.br",
    "wikipedia.org",
    "linktr.ee",
    "pinterest.com",
    "music.youtube.com",
)

STOPWORDS_PICO: frozenset[str] = frozenset(
    {
        "gruta",
        "pedra",
        "morro",
        "serra",
        "pico",
        "monte",
        "parque",
        "vale",
        "canyon",
        "canion",
        "cachoeira",
        "setor",
        "parede",
        "falesia",
        "estadual",
        "nacional",
        "municipal",
        "natural",
        "monumento",
        "das",
        "dos",
        "para",
        "com",
        "por",
        "uma",
        "uns",
    }
)

LIMIAR_SIMILARIDADE_TYPO = 0.86

# Garante que o motor Yahoo do ddgs suporte tanto classes 'algo-sr' quanto 'relsrch' em desktop
Yahoo.items_xpath = "//div[contains(@class, 'algo-sr') or contains(@class, 'relsrch')]"


def sanitizar_termo_busca(texto: str) -> str:
    """
    Remove anotações técnicas entre parênteses/colchetes, sufixos de numeração de mapa/setor
    (ex.: '- Mapa 3'), aspas e caracteres especiais ruidosos.
    """
    limpo = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", texto)
    limpo = re.sub(
        r"\s*[-–—]\s*(?:mapa|setor|parte)\s*\d+.*$",
        " ",
        limpo,
        flags=re.IGNORECASE,
    )
    limpo = re.sub(r"[\"'“”‘’«»!?,.;:/\\|+-]+", " ", limpo)
    return re.sub(r"\s+", " ", limpo).strip()


def _normalizar_texto(texto: str) -> str:
    """Remove acentos, converte para minúsculas e mantém apenas caracteres alfanuméricos."""
    decomposed = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join(c for c in decomposed if not unicodedata.combining(c))
    alfa = re.sub(r"[^a-z0-9]+", " ", sem_acentos.lower())
    return re.sub(r"\s+", " ", alfa).strip()


def menciona_nome_via(texto: str, nome_via: str) -> bool:
    """
    Verifica se o texto menciona o nome da via com:
    1. Substring normalizada direta;
    2. Matching bidirecional de espaços colapsados ('Karren Glass' <-> 'Karrenglass');
    3. Tolerância a pequenos typos (SequenceMatcher >= 0.86 em janelas de tokens).
    """
    via_norm = _normalizar_texto(sanitizar_termo_busca(nome_via))
    texto_norm = _normalizar_texto(texto)
    if not via_norm or not texto_norm:
        return False

    if via_norm in texto_norm:
        return True

    via_compacta = via_norm.replace(" ", "")
    texto_compacto = texto_norm.replace(" ", "")
    if len(via_compacta) >= 4 and via_compacta in texto_compacto:
        return True

    if len(via_compacta) >= 5:
        palavras_texto = texto_norm.split()
        n_via = len(via_norm.split())
        tam_min = max(1, n_via - 1)
        tam_max = min(len(palavras_texto), n_via + 1)
        for tam in range(tam_min, tam_max + 1):
            for idx in range(len(palavras_texto) - tam + 1):
                janela_compacta = "".join(palavras_texto[idx : idx + tam])
                if abs(len(janela_compacta) - len(via_compacta)) > 2:
                    continue
                ratio = SequenceMatcher(None, via_compacta, janela_compacta).ratio()
                if ratio >= LIMIAR_SIMILARIDADE_TYPO:
                    return True

    return False


def menciona_contexto_pico(texto: str, nome_pico: str) -> bool:
    """
    Verifica se o texto contém pelo menos um token significativo do nome do pico
    (ex.: 'lapinha' para 'Gruta da Lapinha', 'cipo' para 'Serra do Cipó').
    """
    pico_norm = _normalizar_texto(sanitizar_termo_busca(nome_pico))
    if not pico_norm:
        return True

    texto_norm = _normalizar_texto(texto)
    if not texto_norm:
        return False

    tokens_todos = [t for t in pico_norm.split() if len(t) >= 3]
    tokens_significativos = [t for t in tokens_todos if t not in STOPWORDS_PICO]
    alvos = tokens_significativos or tokens_todos
    if not alvos:
        return True

    texto_compacto = texto_norm.replace(" ", "")
    return any(tok in texto_norm or tok in texto_compacto for tok in alvos)


def eh_url_bloqueada(url: str) -> bool:
    """
    Retorna True se a URL pertencer à blocklist de agregadores de croquis,
    repositórios de PDFs, portais de trilhas genéricas ou páginas de áudio.
    """
    url_limpa = url.strip().lower()
    if not url_limpa:
        return False
    parsed = urlparse(url_limpa)
    netloc = parsed.netloc.lower()
    if any(netloc == dom or netloc.endswith(f".{dom}") for dom in DOMINIOS_BLOQUEADOS):
        return True
    if "/reels/audio/" in parsed.path.lower():
        return True
    return False


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


MAX_REQUISICOES_POR_SESSAO_DDGS = 15


class _BuscadorDuckDuckGoPadrao:
    """
    Adaptador padrão para busca textual via pacote ddgs com sessão HTTP/TLS isolada
    por thread (threading.local), renovação periódica contra flood HTTP/2 (ENHANCE_YOUR_CALM),
    User-Agent desktop fixo e controle de cadência (pacing) thread-safe.
    """

    def __init__(
        self,
        fabrica_ddgs: Any = DDGS,
        backends: Sequence[str] = BACKENDS_WEB_PADRAO,
        regiao: str = "br-pt",
        intervalo_minimo_s: float = 0.15,
        max_requisicoes_por_sessao: int = MAX_REQUISICOES_POR_SESSAO_DDGS,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._fabrica_ddgs = fabrica_ddgs
        self._backends = tuple(backends) if backends else BACKENDS_WEB_PADRAO
        self._regiao = regiao
        self._intervalo_minimo_s = intervalo_minimo_s
        self._max_requisicoes_por_sessao = max(1, int(max_requisicoes_por_sessao))
        self._relogio = relogio
        self._dormir = dormir
        self._ultima_requisicao_s: float | None = None
        self._lock = threading.Lock()
        self._local = threading.local()

    def _obter_sessao_ddgs(self) -> Any:
        sessao = getattr(self._local, "sessao_ddgs", None)
        contagem = int(getattr(self._local, "contagem_reqs", 0))
        if sessao is None or contagem >= self._max_requisicoes_por_sessao:
            instancia = self._fabrica_ddgs()
            if hasattr(instancia, "_get_engines"):
                for nome_backend in self._backends:
                    for eng in instancia._get_engines("text", nome_backend):
                        eng.http_client.client = primp.Client(
                            impersonate="chrome",
                            impersonate_os="windows",
                            timeout=10,
                            verify=True,
                        )
            self._local.sessao_ddgs = instancia
            self._local.contagem_reqs = 1
            return instancia
        self._local.contagem_reqs = contagem + 1
        return sessao

    def _descartar_sessao_thread(self) -> None:
        self._local.sessao_ddgs = None
        self._local.contagem_reqs = 0

    def _aguardar_pacing(self) -> None:
        with self._lock:
            if self._intervalo_minimo_s > 0 and self._ultima_requisicao_s is not None:
                decorrido = self._relogio() - self._ultima_requisicao_s
                if decorrido < self._intervalo_minimo_s:
                    self._dormir(self._intervalo_minimo_s - decorrido)
            self._ultima_requisicao_s = self._relogio()

    def buscar_texto(self, query: str, max_resultados: int = 10) -> list[dict[str, str]]:
        ultimo_erro: Exception | None = None

        for backend_atual in self._backends:
            sessao = self._obter_sessao_ddgs()
            self._aguardar_pacing()
            try:
                itens = sessao.text(
                    query,
                    region=self._regiao,
                    backend=backend_atual,
                    max_results=max_resultados,
                )
                return [dict(item) for item in itens]
            except Exception as e:
                if "no results found" in str(e).lower():
                    return []
                self._descartar_sessao_thread()
                ultimo_erro = e

        assert ultimo_erro is not None
        raise ultimo_erro


class ExtratorBlog:
    """
    Extrator web unificado de betas de escalada que executa 5 queries identificadas por escalada
    (Instagram, YouTube, TikTok, Facebook e Geral), sem download de HTML durante a coleta,
    aplicando blocklist de agregadores, filtro de precisão (via + pico) e registrando itens
    descartados como MidiaBeta auto-rejeitados com identificação da query de origem.
    """

    def __init__(
        self,
        buscador: BuscadorWebProtocolo | None = None,
        cliente_http: ClienteHttpProtocolo | None = None,
    ) -> None:
        _ = cliente_http
        self._buscador: BuscadorWebProtocolo = buscador or _BuscadorDuckDuckGoPadrao()

    def montar_queries_identificadas(
        self,
        nome_escalada: str,
        nome_pico: str = "",
    ) -> list[tuple[str, str]]:
        """
        Retorna as 5 queries identificadas (origem, query) omitindo o nome do setor:
        instagram, youtube, tiktok, facebook e geral.
        """
        via_limpa = sanitizar_termo_busca(nome_escalada)
        pico_limpo = sanitizar_termo_busca(nome_pico)
        partes_base = [p for p in (via_limpa, pico_limpo, "escalada") if p]
        base = " ".join(partes_base)
        return [
            ("instagram", f"{base} site:instagram.com"),
            ("youtube", f"{base} site:youtube.com"),
            ("tiktok", f"{base} site:tiktok.com"),
            ("facebook", f"{base} site:facebook.com"),
            ("geral", base),
        ]

    def montar_query(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
    ) -> str:
        """Retorna a query geral sanitizada (sem o nome do setor)."""
        _ = nome_setor
        return self.montar_queries_identificadas(nome_escalada, nome_pico)[-1][1]

    def buscar_com_rejeitados(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 8,
    ) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
        """
        Executa as 5 queries identificadas para a escalada e retorna
        (candidatos_aprovados_para_avaliacao, midias_auto_rejeitadas_com_motivo).
        """
        _ = nome_setor
        queries = self.montar_queries_identificadas(nome_escalada, nome_pico)

        candidatos_por_url: dict[str, beta_pb2.CandidatoMidiaBeta] = {}
        rejeitados_por_url: dict[str, beta_pb2.MidiaBeta] = {}

        for origem, query in queries:
            try:
                resultados_busca = self._buscador.buscar_texto(
                    query,
                    max_resultados=max_resultados,
                )
            except Exception as e:
                raise RuntimeError(f"Erro na busca de blogs: {e}")

            for item in resultados_busca:
                link = item.get("href", "").strip()
                if not link:
                    continue

                chave_url = normalizar_url(link) or link
                if chave_url in candidatos_por_url:
                    continue

                titulo_busca = item.get("title", "").strip()
                body_busca = item.get("body", "").strip()
                titulo_base = titulo_busca or link

                if eh_url_bloqueada(link):
                    if chave_url not in rejeitados_por_url:
                        fonte_bloq = classificar_fonte_url(link) or beta_pb2.FonteMidia.BLOG
                        rejeitados_por_url[chave_url] = beta_pb2.MidiaBeta(
                            url=link,
                            titulo=(
                                f"[Query: {origem} | Auto-filtrado: domínio bloqueado] "
                                f"{titulo_base}"
                            ),
                            fonte=fonte_bloq,
                        )
                    continue

                fonte = classificar_fonte_url(link)
                if fonte is None:
                    continue

                texto_completo = f"{titulo_busca} {body_busca} {link}"

                if not menciona_nome_via(texto_completo, nome_escalada):
                    if chave_url not in rejeitados_por_url:
                        rejeitados_por_url[chave_url] = beta_pb2.MidiaBeta(
                            url=link,
                            titulo=(
                                f"[Query: {origem} | Auto-filtrado: sem menção à via] {titulo_base}"
                            ),
                            fonte=fonte,
                        )
                    continue

                if not menciona_contexto_pico(texto_completo, nome_pico):
                    if chave_url not in rejeitados_por_url:
                        rejeitados_por_url[chave_url] = beta_pb2.MidiaBeta(
                            url=link,
                            titulo=(
                                f"[Query: {origem} | Auto-filtrado: sem menção ao pico] "
                                f"{titulo_base}"
                            ),
                            fonte=fonte,
                        )
                    continue

                rejeitados_por_url.pop(chave_url, None)
                candidato = beta_pb2.CandidatoMidiaBeta()
                candidato.midia.url = link
                candidato.midia.titulo = titulo_busca
                candidato.midia.fonte = fonte
                candidato.match_nome_no_snippet = True
                if body_busca:
                    candidato.snippets.append(body_busca)
                candidatos_por_url[chave_url] = candidato

        return list(candidatos_por_url.values()), list(rejeitados_por_url.values())

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 8,
    ) -> list[beta_pb2.CandidatoMidiaBeta]:
        """Executa a busca para a escalada e retorna a lista de candidatos aprovados."""
        candidatos, _ = self.buscar_com_rejeitados(
            nome_escalada=nome_escalada,
            nome_setor=nome_setor,
            nome_pico=nome_pico,
            max_resultados=max_resultados,
        )
        return candidatos
