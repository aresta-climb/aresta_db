# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import re
from typing import List, Iterable
from urllib.parse import urlparse, parse_qs
from aresta_api.proto.generated import beta_pb2

def normalizar_url(url: str) -> str:
    """
    Normaliza URLs de redes sociais removendo parâmetros de query irrelevantes e prefixos www.
    """
    url_limpa = url.strip()
    parsed = urlparse(url_limpa)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    if "instagram.com" in netloc:
        # Extrai caminho padrão /p/ID ou /reel/ID
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
        if "v" in qs and qs["v"]:
            video_id = qs["v"][0]
            return f"https://youtube.com/watch?v={video_id}"

    return f"https://{netloc.replace('www.', '')}{path}"


def deduplicar_midias(listas_de_midias: Iterable[List[beta_pb2.MidiaBeta]]) -> List[beta_pb2.MidiaBeta]:
    """
    Agrupa e deduplica mídias a partir de suas URLs normalizadas,
    mesclando thumbnails, títulos e ativando a flag match_multiplas_fontes.
    """
    mapa_midias = {}
    contagem_fontes = {}

    for lista in listas_de_midias:
        for midia in lista:
            url_norm = normalizar_url(midia.url)
            if not url_norm:
                continue

            contagem_fontes[url_norm] = contagem_fontes.get(url_norm, 0) + 1

            if url_norm not in mapa_midias:
                nova_midia = beta_pb2.MidiaBeta()
                nova_midia.CopyFrom(midia)
                nova_midia.url = url_norm
                mapa_midias[url_norm] = nova_midia
            else:
                existente = mapa_midias[url_norm]
                # Preserva thumbnail caso a existente esteja vazia
                if not existente.thumbnail_url and midia.thumbnail_url:
                    existente.thumbnail_url = midia.thumbnail_url
                # Se qualquer uma tiver match de nome, mantém True
                if midia.match_nome_no_snippet:
                    existente.match_nome_no_snippet = True
                # Preserva título se o existente for vazio
                if not existente.titulo and midia.titulo:
                    existente.titulo = midia.titulo
                # Mescla snippets sem duplicar
                for s in midia.snippets:
                    if s and s not in existente.snippets:
                        existente.snippets.append(s)

    # Aplica flag de múltiplas fontes
    for url_norm, midia_final in mapa_midias.items():
        if contagem_fontes.get(url_norm, 0) > 1:
            midia_final.match_multiplas_fontes = True

    return list(mapa_midias.values())
