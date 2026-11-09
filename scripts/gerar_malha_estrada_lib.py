# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para extração do grafo rodoviário do OpenStreetMap (Overpass API),
cálculo de caminhos mínimos por Dijkstra invertido e amostragem determinística
em 3 anéis concêntricos para o catálogo offline de distâncias rodoviárias.
"""

from __future__ import annotations

import heapq
import json
import math
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections.abc import Callable, Sequence
from typing import Any

from aresta_api.proto.generated import croqui_pb2
from aresta_api.sql.generated.python.catalogo_sql import (
    LinhaCatalogoDistanciasEstrada,
    LinhaCatalogoNosEstrada,
)

RAIO_TERRA_METROS = 6371000.0

ESPELHOS_OVERPASS_PADRAO: tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)

USER_AGENT_OVERPASS = "ArestaClimbEditor/1.0 (+https://arestaclimb.com)"

RANK_POR_HIGHWAY: dict[str, int] = {
    "motorway": 1,
    "motorway_link": 1,
    "trunk": 1,
    "trunk_link": 1,
    "primary": 2,
    "primary_link": 2,
    "secondary": 3,
    "secondary_link": 3,
    "tertiary": 4,
    "tertiary_link": 4,
    "unclassified": 5,
    "residential": 5,
    "living_street": 5,
    "road": 5,
    "track": 6,
    "service": 6,
}


def calcular_distancia_haversine_metros(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calcula a distância geodésica em metros entre dois pares (lat, lon) em graus."""
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    rad_lat1 = math.radians(lat1)
    rad_lat2 = math.radians(lat2)

    seno_lat = math.sin(d_lat / 2.0)
    seno_lon = math.sin(d_lon / 2.0)
    a = seno_lat * seno_lat + math.cos(rad_lat1) * math.cos(rad_lat2) * seno_lon * seno_lon
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return RAIO_TERRA_METROS * c


def construir_query_overpass(latitude: float, longitude: float) -> str:
    """
    Constrói a query Overpass QL escalonada nos 3 raios concêntricos (15 km, 60 km e 180 km)
    para extrair apenas a hierarquia rodoviária relevante em cada anel.
    """
    coords = f"{latitude},{longitude}"
    vias_anel_1 = (
        "motorway|motorway_link|trunk|trunk_link|primary|primary_link|"
        "secondary|secondary_link|tertiary|tertiary_link|unclassified|"
        "residential|living_street|road|track|service"
    )
    vias_anel_2 = (
        "motorway|motorway_link|trunk|trunk_link|primary|primary_link|"
        "secondary|secondary_link|tertiary|tertiary_link"
    )
    vias_anel_3 = (
        "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link"
    )
    return (
        "[out:json][timeout:120];\n"
        "(\n"
        f'  way["highway"~"^({vias_anel_1})$"](around:15000,{coords});\n'
        f'  way["highway"~"^({vias_anel_2})$"](around:60000,{coords});\n'
        f'  way["highway"~"^({vias_anel_3})$"](around:180000,{coords});\n'
        ");\n"
        "out body;\n"
        ">;\n"
        "out skel qt;\n"
    )


class ClienteOverpass:
    """Cliente HTTP para consulta da malha rodoviária na Overpass API com failover entre espelhos."""

    def __init__(
        self,
        url_endpoint: str | Sequence[str] | None = None,
        timeout_segundos: int = 120,
        abridor_url: Callable[..., Any] | None = None,
    ) -> None:
        if url_endpoint is None:
            self.urls_endpoints: tuple[str, ...] = ESPELHOS_OVERPASS_PADRAO
        elif isinstance(url_endpoint, str):
            self.urls_endpoints = (url_endpoint,)
        else:
            self.urls_endpoints = tuple(url_endpoint)
        self.url_endpoint = self.urls_endpoints[0]
        self.timeout_segundos = timeout_segundos
        self._abridor_url: Callable[..., Any] = abridor_url or urllib.request.urlopen

    def consultar_malha(self, latitude: float, longitude: float) -> list[dict[str, Any]]:
        """Executa a query Overpass para (latitude, longitude) com failover entre espelhos oficiais."""
        query = construir_query_overpass(latitude, longitude)
        corpo = urllib.parse.urlencode({"data": query}).encode("utf-8")
        ultimo_erro: Exception | None = None

        for url in self.urls_endpoints:
            requisicao = urllib.request.Request(
                url,
                data=corpo,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                    "User-Agent": USER_AGENT_OVERPASS,
                },
                method="POST",
            )
            try:
                resposta = self._abridor_url(requisicao, timeout=float(self.timeout_segundos))
                texto = resposta.read().decode("utf-8")
                dados = json.loads(texto)
                elementos = dados.get("elements", [])
                return list(elementos)
            except urllib.error.HTTPError as erro:
                detalhe = erro.read().decode("utf-8", errors="replace")
                ultimo_erro = RuntimeError(f"Erro HTTP {erro.code} na Overpass API: {detalhe}")
            except (urllib.error.URLError, TimeoutError, OSError) as erro:
                ultimo_erro = RuntimeError(f"Falha de conexão na Overpass API ({url}): {erro}")

        assert ultimo_erro is not None
        raise ultimo_erro


def prioridade_intrinseca_no(
    no_osm_id: int,
    rank_rodovia: int,
    grau_cruzamento: int,
) -> tuple[int, int, int]:
    """
    Calcula a tupla de prioridade intrínseca determinística de um nó rodoviário:
    (rank_rodovia, -grau_cruzamento, crc32(no_osm_id)).
    """
    hash_id = zlib.crc32(str(no_osm_id).encode("utf-8"))
    return (rank_rodovia, -grau_cruzamento, hash_id)


def _extrair_grafo_maior_componente(
    elementos: list[dict[str, Any]],
) -> tuple[dict[int, tuple[float, float]], dict[int, dict[int, float]], dict[int, int]]:
    """
    Constrói o grafo não-direcionado a partir dos elementos JSON da Overpass API
    e filtra apenas os nós pertencentes ao maior componente conexo.
    """
    coordenadas: dict[int, tuple[float, float]] = {}
    for elem in elementos:
        if elem.get("type") == "node" and "lat" in elem and "lon" in elem:
            coordenadas[int(elem["id"])] = (float(elem["lat"]), float(elem["lon"]))

    adjacencia: dict[int, dict[int, float]] = {}
    melhor_rank: dict[int, int] = {}

    for elem in elementos:
        if elem.get("type") != "way":
            continue
        tags = elem.get("tags") or {}
        highway = str(tags.get("highway", ""))
        rank = RANK_POR_HIGHWAY.get(highway)
        if rank is None:
            continue

        nos_way = [int(nid) for nid in elem.get("nodes", []) if int(nid) in coordenadas]
        if len(nos_way) < 2:
            continue

        for nid in nos_way:
            rank_ant = melhor_rank.get(nid)
            if rank_ant is None or rank < rank_ant:
                melhor_rank[nid] = rank

        for i in range(len(nos_way) - 1):
            u = nos_way[i]
            v = nos_way[i + 1]
            lat_u, lon_u = coordenadas[u]
            lat_v, lon_v = coordenadas[v]
            dist = calcular_distancia_haversine_metros(lat_u, lon_u, lat_v, lon_v)
            adjacencia.setdefault(u, {})[v] = dist
            adjacencia.setdefault(v, {})[u] = dist

    visitados: set[int] = set()
    maior_componente: set[int] = set()

    for no_inicial in sorted(adjacencia):
        if no_inicial in visitados:
            continue
        pilha = [no_inicial]
        componente_atual: set[int] = set()
        while pilha:
            atual = pilha.pop()
            if atual in componente_atual:
                continue
            componente_atual.add(atual)
            visitados.add(atual)
            for vizinho in adjacencia[atual]:
                if vizinho not in componente_atual:
                    pilha.append(vizinho)

        if len(componente_atual) > len(maior_componente):
            maior_componente = componente_atual

    coords_filtradas = {nid: coordenadas[nid] for nid in maior_componente}
    adj_filtrada = {nid: adjacencia[nid] for nid in maior_componente}
    rank_filtrado = {nid: melhor_rank[nid] for nid in maior_componente}
    return coords_filtradas, adj_filtrada, rank_filtrado


def gerar_malha_estrada_pico(
    croqui_uid: str,
    latitude_e7: int,
    longitude_e7: int,
    cliente: ClienteOverpass,
) -> tuple[list[LinhaCatalogoNosEstrada], list[LinhaCatalogoDistanciasEstrada]]:
    """
    Calcula os nós rodoviários amostrados nos 3 anéis concêntricos e suas distâncias
    por estrada até o estacionamento do pico (`croqui_uid`), marcando os portais de borda.
    """
    if latitude_e7 == 0 and longitude_e7 == 0:
        return [], []

    lat_pico = latitude_e7 / 1e7
    lon_pico = longitude_e7 / 1e7

    elementos = cliente.consultar_malha(lat_pico, lon_pico)
    coordenadas, adjacencia, rank_rodovia = _extrair_grafo_maior_componente(elementos)
    if not coordenadas:
        return [], []

    # 1. Encontra o nó do maior componente conexo mais próximo ao estacionamento (no_pico)
    no_pico = min(
        coordenadas,
        key=lambda nid: (
            calcular_distancia_haversine_metros(
                lat_pico, lon_pico, coordenadas[nid][0], coordenadas[nid][1]
            ),
            nid,
        ),
    )

    # 2. Executa Dijkstra invertido a partir de no_pico
    distancias_estrada: dict[int, float] = {no_pico: 0.0}
    fila: list[tuple[float, int]] = [(0.0, no_pico)]

    while fila:
        dist_atual, u = heapq.heappop(fila)
        if dist_atual > distancias_estrada[u]:
            continue
        for v, peso in adjacencia[u].items():
            nova_dist = dist_atual + peso
            dist_ant = distancias_estrada.get(v)
            if dist_ant is None or nova_dist < dist_ant:
                distancias_estrada[v] = nova_dist
                heapq.heappush(fila, (nova_dist, v))

    # 3. Amostragem determinística nos 3 anéis concêntricos ancorados em (0°, 0°)
    # Chave da célula: (anel, ix, iy) -> (prioridade_tupla, no_osm_id, anel, dist_reta_km)
    vencedores_celula: dict[tuple[int, int, int], tuple[tuple[int, int, int], int, int, float]] = {}

    for nid in distancias_estrada:
        lat_no, lon_no = coordenadas[nid]
        dist_reta_km = (
            calcular_distancia_haversine_metros(lat_pico, lon_pico, lat_no, lon_no) / 1000.0
        )
        rank = rank_rodovia[nid]

        if dist_reta_km <= 15.0:
            anel = 1
            passo = 0.02
            rank_max = 6
        elif dist_reta_km <= 60.0:
            anel = 2
            passo = 0.06
            rank_max = 4
        elif dist_reta_km <= 180.0:
            anel = 3
            passo = 0.18
            rank_max = 3
        else:
            continue

        if rank > rank_max:
            continue

        ix = math.floor(lat_no / passo)
        iy = math.floor(lon_no / passo)
        chave_celula = (anel, ix, iy)
        prio = prioridade_intrinseca_no(nid, rank, len(adjacencia[nid]))

        atual_celula = vencedores_celula.get(chave_celula)
        if atual_celula is None or prio < atual_celula[0]:
            vencedores_celula[chave_celula] = (prio, nid, anel, dist_reta_km)

    ids_selecionados: set[int] = {no_pico}
    metadados_selecionados: dict[int, tuple[int, float]] = {}
    for _, nid, anel, dist_reta_km in vencedores_celula.values():
        ids_selecionados.add(nid)
        metadados_selecionados[nid] = (anel, dist_reta_km)

    # 4. Identifica até 8 portais de borda nos octantes direcionais do anel mais externo
    candidatos_borda = [nid for nid in ids_selecionados if nid != no_pico]
    portais_borda: set[int] = set()
    if candidatos_borda:
        anel_maximo = max(metadados_selecionados[nid][0] for nid in candidatos_borda)
        melhor_por_octante: dict[int, tuple[tuple[int, float, int], int]] = {}
        for nid in candidatos_borda:
            anel, dist_reta_km = metadados_selecionados[nid]
            if anel != anel_maximo:
                continue
            lat_no, lon_no = coordenadas[nid]
            angulo = (
                math.degrees(math.atan2(lon_no - lon_pico, lat_no - lat_pico)) + 360.0 + 22.5
            ) % 360.0
            octante = int(angulo // 45.0)
            rank = rank_rodovia[nid]
            hash_id = zlib.crc32(str(nid).encode("utf-8"))
            # Prefere melhor rank rodoviário (menor rank), depois maior distância radial na borda
            chave_portal = (-rank, round(dist_reta_km, 3), -hash_id)
            atual_octante = melhor_por_octante.get(octante)
            if atual_octante is None or chave_portal > atual_octante[0]:
                melhor_por_octante[octante] = (chave_portal, nid)

        portais_borda = {nid for _, nid in melhor_por_octante.values()}

    # 5. Formata as linhas ordenadas por no_osm_id
    nos_saida: list[LinhaCatalogoNosEstrada] = []
    distancias_saida: list[LinhaCatalogoDistanciasEstrada] = []

    for nid in sorted(ids_selecionados):
        lat_no, lon_no = coordenadas[nid]
        nos_saida.append(
            {
                "no_osm_id": nid,
                "latitude_e7": int(round(lat_no * 1e7)),
                "longitude_e7": int(round(lon_no * 1e7)),
            }
        )
        dist_m = 0 if nid == no_pico else int(round(distancias_estrada[nid]))
        distancias_saida.append(
            {
                "croqui_uid": croqui_uid,
                "no_osm_id": nid,
                "distancia_metros": dist_m,
                "e_portal_borda": 1 if nid in portais_borda else 0,
            }
        )

    return nos_saida, distancias_saida


def malha_estrada_pico_atualizada(pico: Any) -> bool:
    """
    Verifica se a mensagem Pico (ou dict compilado equivalente) possui `localizacao` válida
    e `malha_estrada` não-vazia sincronizada com a coordenada atual do pico.
    """
    if isinstance(pico, dict):
        loc_dict = pico.get("localizacao")
        malha_dict = pico.get("malha_estrada")
        if not isinstance(loc_dict, dict) or not isinstance(malha_dict, dict):
            return False
        lat_loc = int(loc_dict.get("latitude", 0) or 0)
        lon_loc = int(loc_dict.get("longitude", 0) or 0)
        if lat_loc == 0 and lon_loc == 0:
            return False
        nos_dict = malha_dict.get("nos")
        if not isinstance(nos_dict, list) or len(nos_dict) == 0:
            return False
        lat_ref = int(malha_dict.get("latitude_referencia_e7", 0) or 0)
        lon_ref = int(malha_dict.get("longitude_referencia_e7", 0) or 0)
        return lat_ref == lat_loc and lon_ref == lon_loc

    loc = pico.localizacao
    malha = pico.malha_estrada
    lat_loc = int(loc.latitude or 0)
    lon_loc = int(loc.longitude or 0)
    if lat_loc == 0 and lon_loc == 0:
        return False
    if not malha.nos:
        return False
    return (
        int(malha.latitude_referencia_e7 or 0) == lat_loc
        and int(malha.longitude_referencia_e7 or 0) == lon_loc
    )


def construir_malha_estrada_pico_proto(
    latitude_e7: int,
    longitude_e7: int,
    cliente: ClienteOverpass,
) -> croqui_pb2.MalhaEstradaPico:
    """
    Consulta a malha rodoviária para `(latitude_e7, longitude_e7)` e retorna a mensagem
    `MalhaEstradaPico` populada com a coordenada de referência e os nós ordenados.
    """
    malha_msg = croqui_pb2.MalhaEstradaPico(
        latitude_referencia_e7=latitude_e7,
        longitude_referencia_e7=longitude_e7,
    )
    nos_osm, dists_osm = gerar_malha_estrada_pico("pico", latitude_e7, longitude_e7, cliente)
    mapa_dist = {d["no_osm_id"]: d for d in dists_osm}
    for no_osm in nos_osm:
        nid = no_osm["no_osm_id"]
        dist_info = mapa_dist[nid]
        item = malha_msg.nos.add()
        item.no_osm_id = nid
        item.latitude_e7 = no_osm["latitude_e7"]
        item.longitude_e7 = no_osm["longitude_e7"]
        item.distancia_metros = dist_info["distancia_metros"]
        item.e_portal_borda = bool(dist_info.get("e_portal_borda", 0))
    return malha_msg


def extrair_linhas_malha_de_pico_proto(
    croqui_uid: str,
    pico: Any,
) -> tuple[list[LinhaCatalogoNosEstrada], list[LinhaCatalogoDistanciasEstrada]]:
    """
    Extrai de forma 100% offline as linhas de `catalogo_nos_estrada` e
    `catalogo_distancias_estrada` a partir de `pico.malha_estrada`, desde que
    a malha esteja sincronizada com a localização atual do pico.
    """
    if not malha_estrada_pico_atualizada(pico):
        return [], []

    nos_saida: list[LinhaCatalogoNosEstrada] = []
    distancias_saida: list[LinhaCatalogoDistanciasEstrada] = []
    nos_ordenados = sorted(pico.malha_estrada.nos, key=lambda n: int(n.no_osm_id))
    for no in nos_ordenados:
        nid = int(no.no_osm_id)
        nos_saida.append(
            {
                "no_osm_id": nid,
                "latitude_e7": int(no.latitude_e7),
                "longitude_e7": int(no.longitude_e7),
            }
        )
        distancias_saida.append(
            {
                "croqui_uid": croqui_uid,
                "no_osm_id": nid,
                "distancia_metros": int(no.distancia_metros),
                "e_portal_borda": 1 if no.e_portal_borda else 0,
            }
        )
    return nos_saida, distancias_saida
