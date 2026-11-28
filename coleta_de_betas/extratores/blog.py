# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Extrator web de redes sociais e blogs via `ddgs` (Instagram, TikTok, Facebook e Web/Blogs),
com exclusão de resultados do YouTube (tratados em extrator dedicado), filtragem de vias
placeholder, contexto geográfico ampliado (Pico + Cidade + Croqui), blocklist de agregadores,
extração leve de vídeos embutidos apenas em páginas BLOG aprovadas e auditoria de descartes.
"""

import re
import threading
import time
import unicodedata
from collections.abc import Callable, Sequence
from difflib import SequenceMatcher
from typing import Any, cast
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
        "complexo",
        "area",
        "regiao",
        "nucleo",
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

_PADRAO_PLACEHOLDER = re.compile(
    r"^(?:sem nome|projeto|via inacabada|via sem nome|boulder sem nome|a definir|desconhecid[ao])(?:\s+\d+)?$"
)
_PADRAO_PREFIXO_COMPLEXO = re.compile(
    r"^(?:complexo(?:\s+d[aeo]s?)?\s+)+",
    flags=re.IGNORECASE,
)
_PADRAO_PREFIXO_AUTO_FILTRADO = re.compile(
    r"^\[Query:\s*[^|\]]+\|\s*Auto-filtrado:[^\]]+\]\s*(.*)$"
)
_PADRAO_EMBED_YOUTUBE = re.compile(
    r"(?:https?:)?//(?:www\.|m\.)?(?:youtube\.com/(?:embed/|watch\?v=|shorts/)|youtu\.be/)[A-Za-z0-9_-]{6,}",
    flags=re.IGNORECASE,
)
_PADRAO_EMBED_INSTAGRAM = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:p|reel|reels)/[A-Za-z0-9_-]+/?",
    flags=re.IGNORECASE,
)

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


def eh_nome_escalada_placeholder(nome_escalada: str) -> bool:
    """Retorna True se o nome da escalada for vazio ou um marcador genérico sem nome próprio."""
    norm = _normalizar_texto(sanitizar_termo_busca(nome_escalada))
    if not norm:
        return True
    return bool(_PADRAO_PLACEHOLDER.match(norm))


def limpar_nome_pico_para_query(nome_pico: str) -> str:
    """Sanitiza o nome do pico removendo prefixos administrativos como 'Complexo' para busca."""
    sanitizado = sanitizar_termo_busca(nome_pico)
    sem_complexo = _PADRAO_PREFIXO_COMPLEXO.sub("", sanitizado).strip()
    return sem_complexo or sanitizado


def extrair_titulo_original_auto_filtrado(titulo: str) -> str | None:
    """
    Extrai o título original caso a mídia possua o prefixo `[Query: ... | Auto-filtrado: ...]`.
    Retorna `None` quando não houver prefixo (indicando rejeição humana que não deve ser reavaliada).
    """
    match = _PADRAO_PREFIXO_AUTO_FILTRADO.match(titulo.strip())
    if match is None:
        return None
    return match.group(1).strip()


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


def _extrair_tokens_contexto(valor: str) -> tuple[list[str], list[str]]:
    norm = _normalizar_texto(sanitizar_termo_busca(valor))
    todos = [t for t in norm.split() if len(t) >= 3]
    significativos = [t for t in todos if t not in STOPWORDS_PICO]
    return significativos, todos


def menciona_contexto_local(
    texto: str,
    nome_pico: str,
    cidade: str = "",
    nome_croqui: str = "",
) -> bool:
    """
    Verifica se o texto contém pelo menos um token geográfico significativo do pico,
    da cidade (`Pico.cidade`) ou do nome do croqui (`Croqui.nome`), incluindo parênteses.
    """
    alvos_sig: list[str] = []
    alvos_todos: list[str] = []
    for fonte_ctx in (nome_pico, cidade):
        sig, todos = _extrair_tokens_contexto(fonte_ctx)
        alvos_sig.extend(sig)
        alvos_todos.extend(todos)

    if nome_croqui:
        croqui_norm = _normalizar_texto(re.sub(r"[\"'“”‘’«»!?,.;:/\\|()+-]+", " ", nome_croqui))
        todos_c = [t for t in croqui_norm.split() if len(t) >= 3]
        sig_c = [t for t in todos_c if t not in STOPWORDS_PICO]
        alvos_sig.extend(sig_c)
        alvos_todos.extend(todos_c)

    alvos = list(dict.fromkeys(alvos_sig)) or list(dict.fromkeys(alvos_todos))
    if not alvos:
        return True

    texto_norm = _normalizar_texto(texto)
    if not texto_norm:
        return False

    texto_compacto = texto_norm.replace(" ", "")
    return any(tok in texto_norm or tok in texto_compacto for tok in alvos)


def menciona_contexto_pico(texto: str, nome_pico: str) -> bool:
    """Atalho compatível que verifica contexto geográfico exclusivamente por `nome_pico`."""
    return menciona_contexto_local(texto, nome_pico=nome_pico)


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


def extrair_midias_embutidas_html(
    html: str,
    titulo_pagina: str,
    url_pagina: str,
) -> list[beta_pb2.CandidatoMidiaBeta]:
    """
    Extrai links de vídeos do YouTube e posts/reels do Instagram embutidos no HTML de
    uma página de Blog já aprovada nos filtros de relevância.
    """
    urls_brutas = [
        *(
            (f"https:{m.group(0)}" if m.group(0).startswith("//") else m.group(0))
            for m in _PADRAO_EMBED_YOUTUBE.finditer(html)
        ),
        *(m.group(0) for m in _PADRAO_EMBED_INSTAGRAM.finditer(html)),
    ]

    candidatos: list[beta_pb2.CandidatoMidiaBeta] = []
    urls_vistas: set[str] = set()
    titulo_limpo = titulo_pagina.strip() or url_pagina

    for url_bruta in urls_brutas:
        url_norm = normalizar_url(url_bruta)
        if not url_norm or url_norm in urls_vistas:
            continue
        fonte = classificar_fonte_url(url_norm)
        assert fonte is not None
        urls_vistas.add(url_norm)

        cand = beta_pb2.CandidatoMidiaBeta()
        cand.midia.url = url_norm
        cand.midia.titulo = f"Vídeo embutido em: {titulo_limpo}"
        cand.midia.fonte = fonte
        cand.match_nome_no_snippet = True
        cand.snippets.append(f"Extraído da página aprovada: {url_pagina}")
        candidatos.append(cand)

    return candidatos


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


def montar_base_query_geografica(
    nome_escalada: str,
    nome_pico: str = "",
    cidade: str = "",
) -> str:
    """
    Constrói os termos base compartilhados entre extratores combinando via sanitizada,
    pico sem prefixo 'Complexo' e cidade (sem duplicação quando já contida no pico).
    """
    via_limpa = sanitizar_termo_busca(nome_escalada)
    pico_limpo = limpar_nome_pico_para_query(nome_pico)
    cidade_limpa = sanitizar_termo_busca(cidade)
    partes = [p for p in (via_limpa, pico_limpo) if p]
    if cidade_limpa and _normalizar_texto(cidade_limpa) not in _normalizar_texto(pico_limpo):
        partes.append(cidade_limpa)
    return " ".join(partes)


class ExtratorBlog:
    """
    Extrator web de redes sociais e blogs via `ddgs` que executa 4 queries identificadas
    (Instagram, TikTok, Facebook e Geral), ignora URLs do YouTube na SERP, aplica filtros
    de precisão com contexto local (`Pico.cidade` e `Croqui.nome`), extrai embeds de blogs
    aprovados e registra descartes auditáveis em `betas_rejeitados`.
    """

    def __init__(
        self,
        buscador: BuscadorWebProtocolo | None = None,
        cliente_http: ClienteHttpProtocolo | None = None,
    ) -> None:
        self._buscador: BuscadorWebProtocolo = buscador or _BuscadorDuckDuckGoPadrao()
        self._cliente_http: ClienteHttpProtocolo = cliente_http or cast(
            ClienteHttpProtocolo,
            primp.Client(
                impersonate="chrome",
                impersonate_os="windows",
                timeout=6,
                verify=True,
            ),
        )

    def montar_queries_identificadas(
        self,
        nome_escalada: str,
        nome_pico: str = "",
        cidade: str = "",
    ) -> list[tuple[str, str]]:
        """
        Retorna as 4 queries identificadas (origem, query) omitindo YouTube e nome do setor:
        instagram, tiktok, facebook e geral.
        """
        base_geo = montar_base_query_geografica(nome_escalada, nome_pico, cidade)
        base = f"{base_geo} escalada".strip()
        return [
            ("instagram", f"{base} site:instagram.com"),
            ("tiktok", f"{base} site:tiktok.com"),
            ("facebook", f"{base} site:facebook.com"),
            ("geral", base),
        ]

    def montar_query(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        cidade: str = "",
    ) -> str:
        """Retorna a query geral sanitizada (sem o nome do setor)."""
        _ = nome_setor
        return self.montar_queries_identificadas(nome_escalada, nome_pico, cidade)[-1][1]

    def _coletar_embeds_blog_aprovado(
        self,
        url_blog: str,
        titulo_base: str,
        candidatos_por_url: dict[str, beta_pb2.CandidatoMidiaBeta],
        rejeitados_por_url: dict[str, beta_pb2.MidiaBeta],
    ) -> None:
        """
        Busca o HTML de uma página `FonteMidia.BLOG` já aprovada nos filtros para recuperar
        vídeos embutidos de YouTube/Instagram. Falhas de rede de terceiros são toleradas sem
        descartar o candidato de blog original.
        """
        try:
            resposta = self._cliente_http.get(url_blog, timeout=6)
        except Exception:
            return
        if resposta.status_code != 200 or not resposta.text:
            return

        for cand_embed in extrair_midias_embutidas_html(
            resposta.text,
            titulo_pagina=titulo_base,
            url_pagina=url_blog,
        ):
            chave_emb = normalizar_url(cand_embed.midia.url)
            if not chave_emb or chave_emb in candidatos_por_url:
                continue
            rejeitados_por_url.pop(chave_emb, None)
            candidatos_por_url[chave_emb] = cand_embed

    def buscar_com_rejeitados(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 8,
        cidade: str = "",
        nome_croqui: str = "",
    ) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
        """
        Executa as 4 queries identificadas para a escalada e retorna
        (candidatos_aprovados_para_avaliacao, midias_auto_rejeitadas_com_motivo).
        """
        _ = nome_setor
        if eh_nome_escalada_placeholder(nome_escalada):
            return [], []

        queries = self.montar_queries_identificadas(nome_escalada, nome_pico, cidade)

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

                fonte = classificar_fonte_url(link)
                if fonte == beta_pb2.FonteMidia.YOUTUBE:
                    continue

                chave_url = normalizar_url(link) or link
                if chave_url in candidatos_por_url:
                    continue

                titulo_busca = item.get("title", "").strip()
                body_busca = item.get("body", "").strip()
                titulo_base = titulo_busca or link

                if eh_url_bloqueada(link):
                    if chave_url not in rejeitados_por_url:
                        fonte_bloq = fonte or beta_pb2.FonteMidia.BLOG
                        rejeitados_por_url[chave_url] = beta_pb2.MidiaBeta(
                            url=link,
                            titulo=(
                                f"[Query: {origem} | Auto-filtrado: domínio bloqueado] "
                                f"{titulo_base}"
                            ),
                            fonte=fonte_bloq,
                        )
                    continue

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

                if not menciona_contexto_local(
                    texto_completo,
                    nome_pico=nome_pico,
                    cidade=cidade,
                    nome_croqui=nome_croqui,
                ):
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

                if fonte == beta_pb2.FonteMidia.BLOG:
                    self._coletar_embeds_blog_aprovado(
                        link,
                        titulo_base,
                        candidatos_por_url,
                        rejeitados_por_url,
                    )

        return list(candidatos_por_url.values()), list(rejeitados_por_url.values())

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 8,
        cidade: str = "",
        nome_croqui: str = "",
    ) -> list[beta_pb2.CandidatoMidiaBeta]:
        """Executa a busca para a escalada e retorna a lista de candidatos aprovados."""
        candidatos, _ = self.buscar_com_rejeitados(
            nome_escalada=nome_escalada,
            nome_setor=nome_setor,
            nome_pico=nome_pico,
            max_resultados=max_resultados,
            cidade=cidade,
            nome_croqui=nome_croqui,
        )
        return candidatos
