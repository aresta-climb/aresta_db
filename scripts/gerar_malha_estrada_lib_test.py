# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes orientados a comportamento para scripts/gerar_malha_estrada_lib.py."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from aresta_api.proto.generated import croqui_pb2
from scripts.cliente_overpass_fake import ClienteOverpassFake
from scripts.gerar_malha_estrada_lib import (
    ESPELHOS_OVERPASS_PADRAO,
    ClienteOverpass,
    construir_malha_estrada_pico_proto,
    construir_query_overpass,
    extrair_linhas_malha_de_pico_proto,
    gerar_malha_estrada_pico,
    malha_estrada_pico_atualizada,
    prioridade_intrinseca_no,
)


def test_construir_query_overpass_inclui_tres_aneis_escalonados() -> None:
    query = construir_query_overpass(-19.5622616, -43.9595684)

    assert "around:15000,-19.5622616,-43.9595684" in query
    assert "around:60000,-19.5622616,-43.9595684" in query
    assert "around:180000,-19.5622616,-43.9595684" in query
    assert "out skel qt;" in query


def test_cliente_overpass_http_executa_post_e_retorna_elements() -> None:
    corpo_resposta = json.dumps(
        {"elements": [{"type": "node", "id": 10, "lat": -19.5, "lon": -43.9}]}
    ).encode("utf-8")

    def abridor_falso(req: urllib.request.Request, timeout: float) -> Any:
        assert req.get_method() == "POST"
        assert timeout == 30
        resposta = io.BytesIO(corpo_resposta)
        resposta.status = 200  # type: ignore[attr-defined]
        return resposta

    cliente = ClienteOverpass(
        url_endpoint="https://overpass.exemplo/api/interpreter",
        timeout_segundos=30,
        abridor_url=abridor_falso,
    )
    elementos = cliente.consultar_malha(-19.5, -43.9)
    assert elementos == [{"type": "node", "id": 10, "lat": -19.5, "lon": -43.9}]


def test_cliente_overpass_http_propaga_runtime_error_em_falha_http() -> None:
    def abridor_erro(req: urllib.request.Request, timeout: float) -> Any:
        raise urllib.error.HTTPError(
            req.full_url,
            504,
            "Gateway Timeout",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"Timeout no Overpass"),
        )

    cliente = ClienteOverpass(abridor_url=abridor_erro)
    with pytest.raises(RuntimeError, match="Erro HTTP 504 na Overpass API"):
        cliente.consultar_malha(-19.5, -43.9)


def test_cliente_overpass_realiza_failover_entre_espelhos_publicos() -> None:
    chamadas: list[str] = []
    corpo_ok = json.dumps(
        {"elements": [{"type": "node", "id": 77, "lat": -19.5, "lon": -43.9}]}
    ).encode("utf-8")

    def abridor_com_failover(req: urllib.request.Request, timeout: float) -> Any:
        chamadas.append(req.full_url)
        assert "ArestaClimbEditor/1.0" in req.get_header("User-agent", "")
        if len(chamadas) == 1:
            raise urllib.error.URLError("Servidor 1 indisponivel")
        resposta = io.BytesIO(corpo_ok)
        resposta.status = 200  # type: ignore[attr-defined]
        return resposta

    cliente = ClienteOverpass(
        url_endpoint=list(ESPELHOS_OVERPASS_PADRAO[:2]),
        abridor_url=abridor_com_failover,
    )
    assert len(ESPELHOS_OVERPASS_PADRAO) >= 2
    elementos = cliente.consultar_malha(-19.5, -43.9)
    assert elementos == [{"type": "node", "id": 77, "lat": -19.5, "lon": -43.9}]
    assert chamadas == list(ESPELHOS_OVERPASS_PADRAO[:2])

    cliente_padrao = ClienteOverpass(abridor_url=abridor_com_failover)
    assert cliente_padrao.urls_endpoints == ESPELHOS_OVERPASS_PADRAO


def test_malha_estrada_pico_proto_conversao_e_deteccao_de_defasagem() -> None:
    elementos: list[dict[str, Any]] = [
        {"type": "node", "id": 100, "lat": -20.0010, "lon": -44.0010},
        {"type": "node", "id": 101, "lat": -20.0300, "lon": -44.0010},
        {"type": "way", "id": 10, "nodes": [100, 101], "tags": {"highway": "primary"}},
    ]
    fake = ClienteOverpassFake(elementos_padrao=elementos)

    pico = croqui_pb2.Pico(nome="Pico Teste")
    assert malha_estrada_pico_atualizada(pico) is False
    assert extrair_linhas_malha_de_pico_proto("uid_1", pico) == ([], [])

    pico.localizacao.latitude = -200000000
    pico.localizacao.longitude = -440000000
    assert malha_estrada_pico_atualizada(pico) is False

    malha_proto = construir_malha_estrada_pico_proto(-200000000, -440000000, fake)
    pico.malha_estrada.CopyFrom(malha_proto)
    assert malha_estrada_pico_atualizada(pico) is True

    nos, dists = extrair_linhas_malha_de_pico_proto("uid_1", pico)
    assert [n["no_osm_id"] for n in nos] == [100, 101]
    assert [d["croqui_uid"] for d in dists] == ["uid_1", "uid_1"]
    assert dists[0]["distancia_metros"] == 0
    assert dists[1]["e_portal_borda"] == 1

    # Ao alterar a coordenada do pico sem regerar a malha, ela passa a ser detectada como defasada
    pico.localizacao.latitude = -201000000
    assert malha_estrada_pico_atualizada(pico) is False
    assert extrair_linhas_malha_de_pico_proto("uid_1", pico) == ([], [])

    # Também funciona quando o pico está em formato dict compilado (usado por deploy_generated.py)
    assert malha_estrada_pico_atualizada({"nome": "Sem Localizacao"}) is False
    assert (
        malha_estrada_pico_atualizada(
            {
                "localizacao": {"latitude": 0, "longitude": 0},
                "malha_estrada": {"nos": [{"no_osm_id": 1}]},
            }
        )
        is False
    )
    assert (
        malha_estrada_pico_atualizada(
            {
                "localizacao": {"latitude": -200000000, "longitude": -440000000},
                "malha_estrada": {
                    "latitude_referencia_e7": -200000000,
                    "longitude_referencia_e7": -440000000,
                    "nos": [],
                },
            }
        )
        is False
    )
    assert (
        malha_estrada_pico_atualizada(
            {
                "localizacao": {"latitude": -200000000, "longitude": -440000000},
                "malha_estrada": {
                    "latitude_referencia_e7": -200000000,
                    "longitude_referencia_e7": -440000000,
                    "nos": [{"no_osm_id": 100}],
                },
            }
        )
        is True
    )


def test_gerar_malha_retorna_vazio_para_coordenada_zero_ou_resposta_vazia() -> None:
    fake = ClienteOverpassFake(elementos_padrao=[])

    nos_zero, dists_zero = gerar_malha_estrada_pico("uid_pico", 0, 0, fake)
    assert nos_zero == []
    assert dists_zero == []
    assert fake.historico_consultas == []

    nos_vazio, dists_vazio = gerar_malha_estrada_pico("uid_pico", -195000000, -439000000, fake)
    assert nos_vazio == []
    assert dists_vazio == []


def test_gerar_malha_descarta_ilha_isolada_e_inclui_estacionamento_com_distancia_zero() -> None:
    # Pico em (-20.0000, -44.0000)
    # Ilha isolada com 2 nós muito próxima do pico (-20.0001, -44.0001)
    # Componente principal maior com 4 nós começando em (-20.0010, -44.0010)
    elementos: list[dict[str, Any]] = [
        # Ilha isolada (2 nós)
        {"type": "node", "id": 900, "lat": -20.0001, "lon": -44.0001},
        {"type": "node", "id": 901, "lat": -20.0002, "lon": -44.0002},
        {"type": "way", "id": 90, "nodes": [900, 901], "tags": {"highway": "track"}},
        # Malha principal conectada (4 nós em diferentes células)
        {"type": "node", "id": 100, "lat": -20.0010, "lon": -44.0010},
        {"type": "node", "id": 101, "lat": -20.0300, "lon": -44.0010},
        {"type": "node", "id": 102, "lat": -20.0600, "lon": -44.0010},
        {"type": "node", "id": 103, "lat": -20.0900, "lon": -44.0010},
        # Entradas inválidas/incompletas que devem ser ignoradas com segurança
        {"type": "node", "id": 999},
        {"type": "way", "id": 91, "nodes": [100], "tags": {"highway": "primary"}},
        {"type": "way", "id": 92, "nodes": [100, 888], "tags": {"highway": "primary"}},
        {"type": "way", "id": 93, "nodes": [100, 101], "tags": {"highway": "footway"}},
        {
            "type": "way",
            "id": 10,
            "nodes": [100, 101, 102, 103],
            "tags": {"highway": "primary"},
        },
    ]
    fake = ClienteOverpassFake(elementos_padrao=elementos)

    nos, distancias = gerar_malha_estrada_pico("uid_lapinha", -200000000, -440000000, fake)

    ids_nos = {n["no_osm_id"] for n in nos}
    assert 900 not in ids_nos
    assert 901 not in ids_nos
    assert 100 in ids_nos

    mapa_dist = {d["no_osm_id"]: d for d in distancias}
    assert mapa_dist[100]["distancia_metros"] == 0
    assert mapa_dist[101]["distancia_metros"] > 3000
    assert mapa_dist[102]["distancia_metros"] > mapa_dist[101]["distancia_metros"]
    assert mapa_dist[103]["distancia_metros"] > mapa_dist[102]["distancia_metros"]


def test_amostragem_tres_aneis_deduplica_pela_prioridade_intrinseca_e_marca_portais() -> None:
    # Pico em (0.0, 0.0) para facilitar contas de graus (1° lat ~= 111.195 km):
    # - Nó 1 (0.0, 0.0): estacionamento (Anel 1)
    # - Nós 2 e 3 na mesma célula de 0.02° do Anel 1 (~5.5 km -> lat 0.05, lon 0.01):
    #   Nó 2 está num cruzamento de motorway (rank 1, grau 3)
    #   Nó 3 está numa via residential (rank 5, grau 2) -> Nó 2 deve vencer na célula!
    # - Nó 4 no Anel 2 (~33 km -> lat 0.30, lon 0.0): secondary (rank 3)
    # - Nó 5 no Anel 2 (~33 km -> lat 0.31, lon 0.0): residential (rank 5, ignorado no Anel 2 pois rank > 4)
    # - Nó 6 no Anel 3 (~100 km -> lat 0.90, lon 0.0): primary (rank 2, Norte -> Portal de Borda!)
    # - Nó 7 no Anel 3 (~100 km -> lat -0.90, lon 0.0): motorway (rank 1, Sul -> Portal de Borda!)
    # - Nó 8 fora de 180 km (~200 km -> lat 1.85, lon 0.0): ignorado
    elementos: list[dict[str, Any]] = [
        {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
        {"type": "node", "id": 2, "lat": 0.050, "lon": 0.010},
        {"type": "node", "id": 3, "lat": 0.051, "lon": 0.011},
        {"type": "node", "id": 9, "lat": 0.060, "lon": -0.005},
        {"type": "node", "id": 4, "lat": 0.300, "lon": 0.000},
        {"type": "node", "id": 5, "lat": 0.310, "lon": 0.000},
        {"type": "node", "id": 6, "lat": 0.900, "lon": 0.000},
        {"type": "node", "id": 7, "lat": -0.900, "lon": 0.000},
        {"type": "node", "id": 8, "lat": 1.850, "lon": 0.000},
        {"type": "way", "id": 100, "nodes": [7, 1, 2, 4, 6, 8], "tags": {"highway": "motorway"}},
        {"type": "way", "id": 101, "nodes": [2, 3, 4], "tags": {"highway": "residential"}},
        {"type": "way", "id": 102, "nodes": [4, 5], "tags": {"highway": "service"}},
        {"type": "way", "id": 103, "nodes": [1, 9, 4], "tags": {"highway": "tertiary"}},
        {"type": "way", "id": 104, "nodes": [4, 6], "tags": {"highway": "secondary"}},
    ]
    fake = ClienteOverpassFake(elementos_padrao=elementos)

    nos, distancias = gerar_malha_estrada_pico("uid_pico", 0, 100, fake)

    ids_escolhidos = {d["no_osm_id"] for d in distancias}
    # Nó 1 (estacionamento) incluído
    assert 1 in ids_escolhidos
    # Na célula (floor(0.05/0.02)=2, floor(0.01/0.02)=0), Nó 2 vence Nó 3
    assert 2 in ids_escolhidos
    assert 3 not in ids_escolhidos
    # No Anel 2, Nó 4 entra e Nó 5 (service, rank 6 > 4) é filtrado
    assert 4 in ids_escolhidos
    assert 5 not in ids_escolhidos
    # No Anel 3, Nós 6 e 7 entram e são marcados como portais de borda; Nó 8 (>180 km) fica de fora
    assert 6 in ids_escolhidos
    assert 7 in ids_escolhidos
    assert 8 not in ids_escolhidos

    portais = {d["no_osm_id"] for d in distancias if d["e_portal_borda"] == 1}
    assert portais == {6, 7}

    # Verifica que prioridade_intrinseca_no é determinística
    assert prioridade_intrinseca_no(2, 1, 3) < prioridade_intrinseca_no(3, 5, 1)
