# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import re
from collections.abc import Iterable, Sequence
from urllib.parse import parse_qs, urlparse

from aresta_api.proto.generated import beta_pb2, croqui_pb2


def normalizar_url(url: str) -> str:
    """
    Normaliza URLs de redes sociais e blogs removendo parâmetros de query irrelevantes e prefixos www.
    """
    url_limpa = url.strip()
    if not url_limpa:
        return ""
    parsed = urlparse(url_limpa)
    netloc = parsed.netloc.lower()
    if not netloc:
        return ""
    path = parsed.path.rstrip("/")

    if "instagram.com" in netloc:
        match = re.search(r"/(p|reel|tv)/([^/?#]+)", path)
        if match:
            tipo, post_id = match.groups()
            return f"https://instagram.com/{tipo}/{post_id}"
        return f"https://instagram.com{path}"

    if "youtube.com" in netloc or "youtu.be" in netloc:
        if "youtu.be" in netloc:
            video_id = path.lstrip("/")
            return f"https://youtube.com/watch?v={video_id}"
        qs = parse_qs(parsed.query)
        if qs.get("v"):
            video_id = qs["v"][0]
            return f"https://youtube.com/watch?v={video_id}"

    return f"https://{netloc.replace('www.', '')}{path}"


def obter_urls_conhecidas_escalada(
    escalada: croqui_pb2.Escalada | None = None,
    curadoria: beta_pb2.CuradoriaBetasEscalada | None = None,
) -> set[str]:
    """
    Coleta e normaliza todas as URLs já presentes nas 4 listas da escalada
    (betas aprovados, não scorados, não revisados e rejeitados).
    """
    urls: set[str] = set()
    if escalada is not None:
        for midia in escalada.betas:
            norm = normalizar_url(midia.url)
            if norm:
                urls.add(norm)
    if curadoria is not None:
        for cand in curadoria.betas_nao_scorados:
            norm = normalizar_url(cand.midia.url)
            if norm:
                urls.add(norm)
        for cand in curadoria.betas_nao_revisados:
            norm = normalizar_url(cand.midia.url)
            if norm:
                urls.add(norm)
        for midia_rej in curadoria.betas_rejeitados:
            norm = normalizar_url(midia_rej.url)
            if norm:
                urls.add(norm)
    return urls


def deduplicar_midias(
    listas_de_midias: Iterable[Sequence[beta_pb2.CandidatoMidiaBeta]],
    urls_ja_conhecidas: Iterable[str] = (),
) -> list[beta_pb2.CandidatoMidiaBeta]:
    """
    Agrupa e deduplica candidatos a partir de suas URLs normalizadas,
    descartando URLs já presentes nas listas conhecidas da escalada e
    mesclando títulos, snippets e a flag match_multiplas_fontes.
    """
    conhecidas_norm = {normalizar_url(u) for u in urls_ja_conhecidas if u}
    conhecidas_norm.discard("")

    mapa_candidatos: dict[str, beta_pb2.CandidatoMidiaBeta] = {}
    contagem_fontes: dict[str, int] = {}

    for lista in listas_de_midias:
        for cand in lista:
            url_norm = normalizar_url(cand.midia.url)
            if not url_norm or url_norm in conhecidas_norm:
                continue

            contagem_fontes[url_norm] = contagem_fontes.get(url_norm, 0) + 1

            if url_norm not in mapa_candidatos:
                novo_cand = beta_pb2.CandidatoMidiaBeta()
                novo_cand.CopyFrom(cand)
                novo_cand.midia.url = url_norm
                mapa_candidatos[url_norm] = novo_cand
            else:
                existente = mapa_candidatos[url_norm]
                if cand.match_nome_no_snippet:
                    existente.match_nome_no_snippet = True
                if not existente.midia.titulo and cand.midia.titulo:
                    existente.midia.titulo = cand.midia.titulo
                for s in cand.snippets:
                    if s and s not in existente.snippets:
                        existente.snippets.append(s)

    for url_norm, cand_final in mapa_candidatos.items():
        if contagem_fontes.get(url_norm, 0) > 1:
            cand_final.match_multiplas_fontes = True

    return list(mapa_candidatos.values())
