# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Extrator dedicado para YouTube utilizando o endpoint JSON InnerTube (`/youtubei/v1/search`),
sem necessidade de chave da Data API v3, com cadência (pacing) por host, suporte a vídeos
tradicionais (`videoRenderer`) e Shorts (`shortsLockupViewModel` / `reelItemRenderer`),
filtragem por nome de via e contexto geográfico ampliado.
"""

import threading
import time
from collections.abc import Callable
from typing import Any, cast

import primp

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import (
    eh_nome_escalada_placeholder,
    menciona_contexto_local,
    menciona_nome_via,
    montar_base_query_geografica,
)
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpProtocolo
from coleta_de_betas.extratores.deduplicador import normalizar_url

URL_INNERTUBE_SEARCH = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"


def _texto_runs(no: Any) -> str:
    if "simpleText" in no:
        return str(no["simpleText"] or "").strip()
    if "content" in no:
        return str(no["content"] or "").strip()
    return "".join(
        str(r.get("text") or "") for r in no.get("runs", []) if isinstance(r, dict)
    ).strip()


def _extrair_itens_innertube(dados: Any, max_resultados: int) -> list[tuple[str, str, str]]:
    """
    Percorre recursivamente o JSON retornado pelo YouTube InnerTube extraindo
    tuplas `(url, titulo, descricao)` de `videoRenderer`, `reelItemRenderer` e `shortsLockupViewModel`.
    """
    itens: list[tuple[str, str, str]] = []
    urls_vistas: set[str] = set()

    def _adicionar(url: str, titulo: str, descricao: str) -> None:
        if len(itens) >= max_resultados or url in urls_vistas:
            return
        urls_vistas.add(url)
        itens.append((url, titulo, descricao))

    def _visitar(no: Any) -> None:
        if len(itens) >= max_resultados:
            return
        if isinstance(no, list):
            for elem in no:
                _visitar(elem)
            return
        if not isinstance(no, dict):
            return

        if "videoRenderer" in no and isinstance(no["videoRenderer"], dict):
            vr = no["videoRenderer"]
            vid = str(vr.get("videoId") or "").strip()
            if vid:
                titulo = _texto_runs(vr.get("title") or {})
                canal = _texto_runs(vr.get("ownerText") or {}) or _texto_runs(
                    vr.get("longBylineText") or {}
                )
                partes_desc: list[str] = []
                if canal:
                    partes_desc.append(f"Canal: {canal}")
                desc_sim = _texto_runs(vr.get("descriptionSnippet") or {})
                if desc_sim:
                    partes_desc.append(desc_sim)
                for snp in vr.get("detailedMetadataSnippets", []):
                    if isinstance(snp, dict):
                        txt = _texto_runs(snp.get("snippetText") or {})
                        if txt and txt not in partes_desc:
                            partes_desc.append(txt)
                _adicionar(
                    f"https://www.youtube.com/watch?v={vid}",
                    titulo,
                    " | ".join(partes_desc),
                )

        if "reelItemRenderer" in no and isinstance(no["reelItemRenderer"], dict):
            rr = no["reelItemRenderer"]
            vid = str(rr.get("videoId") or "").strip()
            if vid:
                titulo = _texto_runs(rr.get("headline") or {})
                _adicionar(f"https://www.youtube.com/shorts/{vid}", titulo, "")

        if "shortsLockupViewModel" in no and isinstance(no["shortsLockupViewModel"], dict):
            sl = no["shortsLockupViewModel"]
            vid = str(
                sl.get("onTap", {})
                .get("innertubeCommand", {})
                .get("reelWatchEndpoint", {})
                .get("videoId")
                or ""
            ).strip()
            if vid:
                titulo = (
                    _texto_runs(sl.get("overlayMetadata", {}).get("primaryText") or {})
                    or str(sl.get("accessibilityText") or "").strip()
                )
                _adicionar(f"https://www.youtube.com/shorts/{vid}", titulo, "")

        for valor in no.values():
            _visitar(valor)

    _visitar(dados)
    return itens


class ExtratorYouTube:
    """
    Extrator dedicado de vídeos e Shorts do YouTube via endpoint JSON InnerTube WEB.
    """

    def __init__(
        self,
        cliente_http: ClienteHttpProtocolo | None = None,
        intervalo_minimo_s: float = 0.4,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._cliente_http: ClienteHttpProtocolo = cliente_http or cast(
            ClienteHttpProtocolo,
            primp.Client(
                impersonate="chrome",
                impersonate_os="windows",
                timeout=10,
                verify=True,
            ),
        )
        self._intervalo_minimo_s = float(intervalo_minimo_s)
        self._relogio = relogio
        self._dormir = dormir
        self._ultima_requisicao_s: float | None = None
        self._lock = threading.Lock()

    def _aguardar_pacing(self) -> None:
        with self._lock:
            if self._intervalo_minimo_s > 0 and self._ultima_requisicao_s is not None:
                decorrido = self._relogio() - self._ultima_requisicao_s
                if decorrido < self._intervalo_minimo_s:
                    self._dormir(self._intervalo_minimo_s - decorrido)
            self._ultima_requisicao_s = self._relogio()

    def montar_query(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        cidade: str = "",
    ) -> str:
        """
        Monta a query do YouTube combinando via sanitizada, pico sem prefixo 'Complexo' e cidade,
        sem incluir nome do setor e sem forçar a palavra 'escalada'.
        """
        _ = nome_setor
        return montar_base_query_geografica(nome_escalada, nome_pico, cidade)

    def buscar_com_rejeitados(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
        cidade: str = "",
        nome_croqui: str = "",
    ) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
        """
        Pesquisa no YouTube InnerTube e retorna `(candidatos_aprovados, midias_auto_rejeitadas)`.
        """
        if eh_nome_escalada_placeholder(nome_escalada):
            return [], []

        query = self.montar_query(nome_escalada, nome_setor, nome_pico, cidade=cidade)
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20250301.01.00",
                    "hl": "pt",
                    "gl": "BR",
                }
            },
            "query": query,
        }

        self._aguardar_pacing()
        try:
            resposta = self._cliente_http.post(
                URL_INNERTUBE_SEARCH,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except Exception as e:
            raise RuntimeError(f"Erro na conexão com o YouTube InnerTube: {e}") from e

        if resposta.status_code != 200:
            raise RuntimeError(
                f"Erro no YouTube InnerTube ({resposta.status_code}): {resposta.text}"
            )

        itens = _extrair_itens_innertube(resposta.json(), max_resultados=max_resultados)
        candidatos: list[beta_pb2.CandidatoMidiaBeta] = []
        rejeitados: list[beta_pb2.MidiaBeta] = []

        for url_bruta, titulo, descricao in itens:
            url_norm = normalizar_url(url_bruta) or url_bruta
            texto_completo = f"{titulo} {descricao}"
            titulo_base = titulo or url_norm

            if not menciona_nome_via(texto_completo, nome_escalada):
                rejeitados.append(
                    beta_pb2.MidiaBeta(
                        url=url_norm,
                        titulo=f"[Query: youtube | Auto-filtrado: sem menção à via] {titulo_base}",
                        fonte=beta_pb2.FonteMidia.YOUTUBE,
                    )
                )
                continue

            if not menciona_contexto_local(
                texto_completo,
                nome_pico=nome_pico,
                cidade=cidade,
                nome_croqui=nome_croqui,
            ):
                rejeitados.append(
                    beta_pb2.MidiaBeta(
                        url=url_norm,
                        titulo=f"[Query: youtube | Auto-filtrado: sem menção ao pico] {titulo_base}",
                        fonte=beta_pb2.FonteMidia.YOUTUBE,
                    )
                )
                continue

            candidato = beta_pb2.CandidatoMidiaBeta()
            candidato.midia.url = url_norm
            candidato.midia.titulo = titulo
            candidato.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
            candidato.match_nome_no_snippet = True
            if descricao:
                candidato.snippets.append(descricao)
            candidatos.append(candidato)

        return candidatos, rejeitados

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
        cidade: str = "",
        nome_croqui: str = "",
    ) -> list[beta_pb2.CandidatoMidiaBeta]:
        """Executa a pesquisa no YouTube e retorna apenas os candidatos aprovados."""
        candidatos, _ = self.buscar_com_rejeitados(
            nome_escalada=nome_escalada,
            nome_setor=nome_setor,
            nome_pico=nome_pico,
            max_resultados=max_resultados,
            cidade=cidade,
            nome_croqui=nome_croqui,
        )
        return candidatos
