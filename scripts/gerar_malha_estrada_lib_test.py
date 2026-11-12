# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes orientados a comportamento para scripts/gerar_malha_estrada_lib.py."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
import zlib
from typing import Any

import brotli  # type: ignore[import-untyped]
import pytest
import zstandard

from aresta_api.proto.generated import croqui_pb2
from scripts.cliente_overpass_fake import ClienteOverpassFake
from scripts.gerar_malha_estrada_lib import (
    DISTANCIA_MAXIMA_ESTRADA_METROS,
    ESPELHOS_OVERPASS_PADRAO,
    RAIO_ANEL_3_KM,
    VERSAO_ATUAL_MALHA_ESTRADA,
    ClienteOverpass,
    ErroMalhaEstradaCancelada,
    _calcular_bbox_graus,
    calcular_velocidade_sem_transito_kmh,
    construir_malha_estrada_pico_proto,
    construir_query_overpass,
    extrair_linhas_malha_de_pico_proto,
    gerar_malha_estrada_pico,
    malha_estrada_pico_atualizada,
    malha_estrada_pico_sincronizada,
    obter_versao_malha_estrada_pico,
    prioridade_intrinseca_no,
)


def test_construir_query_overpass_inclui_tres_bboxes_disjuntas_e_out_body_qt() -> None:
    query = construir_query_overpass(-19.5622616, -43.9595684)
    bbox_60 = _calcular_bbox_graus(-19.5622616, -43.9595684, 60.0)
    bbox_150 = _calcular_bbox_graus(-19.5622616, -43.9595684, 150.0)

    assert "around:" not in query
    assert "[out:json][timeout:60];" in query
    assert "residential|living_street|road|track|service|unclassified" in query
    assert query.count("unclassified") == 1
    assert f'way["highway"="tertiary"]({bbox_60});' in query
    assert f'way["highway"="tertiary_link"]({bbox_60});' in query
    assert f'way["highway"="motorway"]({bbox_150});' in query
    assert f'way["highway"="secondary_link"]({bbox_150});' in query
    assert RAIO_ANEL_3_KM == 150.0
    assert DISTANCIA_MAXIMA_ESTRADA_METROS == 200_000.0
    assert "out geom qt;" in query
    assert "out skel qt;" not in query
    assert ">;" not in query
    assert ESPELHOS_OVERPASS_PADRAO == (
        "https://lz4.overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    )


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
        if len(chamadas) == 3:
            raise urllib.error.HTTPError(
                req.full_url,
                502,
                "Bad Gateway",
                hdrs=None,  # type: ignore[arg-type]
                fp=io.BytesIO(b"Bad Gateway"),
            )
        resposta = io.BytesIO(corpo_ok)
        resposta.status = 200  # type: ignore[attr-defined]
        return resposta

    cliente = ClienteOverpass(
        url_endpoint=list(ESPELHOS_OVERPASS_PADRAO),
        abridor_url=abridor_com_failover,
    )
    assert len(ESPELHOS_OVERPASS_PADRAO) == 3
    eventos_failover: list[tuple[str, int]] = []
    elementos = cliente.consultar_malha(
        -19.5,
        -43.9,
        ao_progresso=lambda msg, pct: eventos_failover.append((msg, pct)),
    )
    assert elementos == [{"type": "node", "id": 77, "lat": -19.5, "lon": -43.9}]
    assert chamadas == [
        ESPELHOS_OVERPASS_PADRAO[0],
        ESPELHOS_OVERPASS_PADRAO[0].replace("/interpreter", "/kill_my_queries"),
        ESPELHOS_OVERPASS_PADRAO[1],
        ESPELHOS_OVERPASS_PADRAO[2],
    ]
    assert any("Falha em lz4.overpass-api.de" in msg for msg, _ in eventos_failover)
    assert any("Falha em z.overpass-api.de (HTTP 502)" in msg for msg, _ in eventos_failover)

    cliente_padrao = ClienteOverpass(abridor_url=abridor_com_failover)
    assert cliente_padrao.urls_endpoints == ESPELHOS_OVERPASS_PADRAO
    assert cliente_padrao.timeout_segundos == 60


def test_cliente_overpass_negocia_e_descomprime_zstd_br_gzip_deflate_e_aciona_kill_my_queries() -> (
    None
):
    payload = json.dumps(
        {"elements": [{"type": "node", "id": 42, "lat": -19.5, "lon": -43.9}]}
    ).encode("utf-8")

    comp_gzip = zlib.compress(payload, wbits=16 + zlib.MAX_WBITS)
    comp_deflate = zlib.compress(payload)
    comp_br = brotli.compress(payload)
    comp_zstd = zstandard.ZstdCompressor().compress(payload)

    for codificacao, bytes_comprimidos in [
        ("zstd", comp_zstd),
        ("br", comp_br),
        ("gzip", comp_gzip),
        ("deflate", comp_deflate),
        ("identity", payload),
    ]:

        def abridor_codificado(
            req: urllib.request.Request,
            timeout: float,
            _enc: str = codificacao,
            _dados: bytes = bytes_comprimidos,
        ) -> Any:
            assert req.get_header("Accept-encoding") == "zstd, br, gzip, deflate"
            resp = io.BytesIO(_dados)
            resp.status = 200  # type: ignore[attr-defined]
            resp.headers = {"Content-Encoding": _enc}  # type: ignore[attr-defined]
            return resp

        cliente = ClienteOverpass(
            url_endpoint="https://overpass.exemplo/api/interpreter",
            abridor_url=abridor_codificado,
        )
        assert cliente.consultar_malha(-19.5, -43.9) == [
            {"type": "node", "id": 42, "lat": -19.5, "lon": -43.9}
        ]

    # Verifica que ao cancelar durante o streaming de blocos, chama /api/kill_my_queries (mesmo se kill_my_queries falhar)
    urls_chamadas: list[str] = []

    def abridor_cancelado(req: urllib.request.Request, timeout: float) -> Any:
        urls_chamadas.append(req.full_url)
        if req.full_url.endswith("/kill_my_queries"):
            raise urllib.error.URLError("kill_my_queries offline")
        resp = io.BytesIO(comp_zstd)
        resp.status = 200  # type: ignore[attr-defined]
        resp.headers = {"Content-Encoding": "zstd"}  # type: ignore[attr-defined]
        return resp

    passos = 0

    def cancelar_apos_abrir() -> bool:
        nonlocal passos
        passos += 1
        return passos >= 2

    cliente_canc = ClienteOverpass(
        url_endpoint="https://overpass.exemplo/api/interpreter",
        abridor_url=abridor_cancelado,
    )
    with pytest.raises(ErroMalhaEstradaCancelada):
        cliente_canc.consultar_malha(-19.5, -43.9, verificador_cancelamento=cancelar_apos_abrir)
    assert urls_chamadas == [
        "https://overpass.exemplo/api/interpreter",
        "https://overpass.exemplo/api/kill_my_queries",
    ]


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

    etapas_progresso: list[tuple[str, int]] = []
    malha_proto = construir_malha_estrada_pico_proto(
        -200000000,
        -440000000,
        fake,
        ao_progresso=lambda msg, pct: etapas_progresso.append((msg, pct)),
    )
    assert len(etapas_progresso) >= 4
    assert etapas_progresso[-1][1] == 100

    pico.malha_estrada.conteudo.CopyFrom(malha_proto)
    assert VERSAO_ATUAL_MALHA_ESTRADA == 2
    assert pico.malha_estrada.conteudo.versao == 2
    assert obter_versao_malha_estrada_pico(pico) == 2
    assert malha_estrada_pico_sincronizada(pico) is True
    assert malha_estrada_pico_atualizada(pico) is True

    nos, dists = extrair_linhas_malha_de_pico_proto("uid_1", pico)
    assert [n["no_osm_id"] for n in nos] == [100, 101]
    assert [d["croqui_uid"] for d in dists] == ["uid_1", "uid_1"]
    assert dists[0]["distancia_metros"] == 0
    assert dists[1]["na_borda"] == 1

    # Se a versão for anterior (< 2), continua sincronizada (exportando para o catálogo), mas NÃO atualizada
    pico.malha_estrada.conteudo.versao = 1
    assert obter_versao_malha_estrada_pico(pico) == 1
    assert malha_estrada_pico_sincronizada(pico) is True
    assert malha_estrada_pico_atualizada(pico) is False
    nos_v1, dists_v1 = extrair_linhas_malha_de_pico_proto("uid_1", pico)
    assert len(nos_v1) == 2
    assert len(dists_v1) == 2
    pico.malha_estrada.conteudo.versao = 2

    # Ao alterar a coordenada do pico sem regerar a malha, ela passa a ser detectada como defasada
    pico.localizacao.latitude = -201000000
    assert malha_estrada_pico_sincronizada(pico) is False
    assert malha_estrada_pico_atualizada(pico) is False
    assert extrair_linhas_malha_de_pico_proto("uid_1", pico) == ([], [])

    # Se a coordenada bater, mas algum nó com distancia_metros > 0 estiver sem duracao_minutos (> 0), também é detectada como defasada
    pico.localizacao.latitude = -200000000
    assert malha_estrada_pico_atualizada(pico) is True
    for no_proto in pico.malha_estrada.conteudo.nos:
        if no_proto.distancia_metros > 0:
            no_proto.duracao_minutos = 0
    assert malha_estrada_pico_sincronizada(pico) is False
    assert malha_estrada_pico_atualizada(pico) is False

    # Cancelamento cooperativo levanta ErroMalhaEstradaCancelada
    with pytest.raises(ErroMalhaEstradaCancelada, match="cancelada"):
        construir_malha_estrada_pico_proto(
            -200000000,
            -440000000,
            fake,
            verificador_cancelamento=lambda: True,
        )

    # Também funciona quando o pico está em formato dict compilado (usado por deploy_generated.py)
    assert obter_versao_malha_estrada_pico({"nome": "Sem Malha"}) == 0
    assert malha_estrada_pico_atualizada({"nome": "Sem Localizacao"}) is False
    assert (
        malha_estrada_pico_atualizada(
            {
                "localizacao": {"latitude": 0, "longitude": 0},
                "malha_estrada": {"conteudo": {"nos": [{"no_osm_id": 1}]}},
            }
        )
        is False
    )
    assert (
        malha_estrada_pico_atualizada(
            {
                "localizacao": {"latitude": -200000000, "longitude": -440000000},
                "malha_estrada": {
                    "conteudo": {
                        "latitude_referencia_e7": -200000000,
                        "longitude_referencia_e7": -440000000,
                        "nos": [],
                    }
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
                    "conteudo": {
                        "latitude_referencia_e7": -201000000,
                        "longitude_referencia_e7": -440000000,
                        "nos": [{"no_osm_id": 100}],
                    }
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
                    "conteudo": {
                        "latitude_referencia_e7": -200000000,
                        "longitude_referencia_e7": -440000000,
                        "versao": 2,
                        "nos": [{"no_osm_id": 100, "distancia_metros": 3500, "duracao_minutos": 0}],
                    }
                },
            }
        )
        is False
    )
    # Em dict, se versao < 2, malha_estrada_pico_sincronizada é True mas malha_estrada_pico_atualizada é False
    dict_v1 = {
        "localizacao": {"latitude": -200000000, "longitude": -440000000},
        "malha_estrada": {
            "conteudo": {
                "latitude_referencia_e7": -200000000,
                "longitude_referencia_e7": -440000000,
                "versao": 1,
                "nos": [
                    {"no_osm_id": 100, "distancia_metros": 0, "duracao_minutos": 0},
                    {"no_osm_id": 101, "distancia_metros": 3500, "duracao_minutos": 5},
                ],
            }
        },
    }
    assert obter_versao_malha_estrada_pico(dict_v1) == 1
    assert malha_estrada_pico_sincronizada(dict_v1) is True
    assert malha_estrada_pico_atualizada(dict_v1) is False

    dict_v2 = {
        "localizacao": {"latitude": -200000000, "longitude": -440000000},
        "malha_estrada": {
            "conteudo": {
                "latitude_referencia_e7": -200000000,
                "longitude_referencia_e7": -440000000,
                "versao": 2,
                "nos": [
                    {"no_osm_id": 100, "distancia_metros": 0, "duracao_minutos": 0},
                    {"no_osm_id": 101, "distancia_metros": 3500, "duracao_minutos": 5},
                ],
            }
        },
    }
    assert obter_versao_malha_estrada_pico(dict_v2) == 2
    assert malha_estrada_pico_sincronizada(dict_v2) is True
    assert malha_estrada_pico_atualizada(dict_v2) is True


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
        # Malha principal conectada (4 nós em diferentes células, via geometry inline de out geom qt)
        # Entradas inválidas/incompletas que devem ser ignoradas com segurança
        {"type": "node", "id": 999},
        {"type": "way", "id": 91, "nodes": [100], "tags": {"highway": "primary"}},
        {"type": "way", "id": 92, "nodes": [100, 888], "tags": {"highway": "primary"}},
        {"type": "way", "id": 93, "nodes": [100, 101], "tags": {"highway": "footway"}},
        {
            "type": "way",
            "id": 10,
            "nodes": [100, 101, 102, 103],
            "geometry": [
                {"lat": -20.0010, "lon": -44.0010},
                {"lat": -20.0300, "lon": -44.0010},
                {"lat": -20.0600, "lon": -44.0010},
                {"lat": -20.0900, "lon": -44.0010},
            ],
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
        {"type": "node", "id": 8, "lat": 1.400, "lon": 0.000},
        {"type": "node", "id": 10, "lat": 0.900, "lon": 1.000},
        {"type": "way", "id": 100, "nodes": [7, 1, 2, 4, 6, 8], "tags": {"highway": "motorway"}},
        {"type": "way", "id": 105, "nodes": [6, 10], "tags": {"highway": "motorway"}},
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
    # No Anel 3, Nós 6 e 7 entram e são marcados como portais de borda;
    # Nó 8 (>150 km em linha reta: ~155.6 km) e Nó 10 (~149 km em linha reta, mas >211 km por estrada via Nó 6) ficam de fora!
    assert 6 in ids_escolhidos
    assert 7 in ids_escolhidos
    assert 8 not in ids_escolhidos
    assert 10 not in ids_escolhidos

    portais = {d["no_osm_id"] for d in distancias if d["na_borda"] == 1}
    assert portais == {6, 7}

    # Verifica que prioridade_intrinseca_no é determinística
    assert prioridade_intrinseca_no(2, 1, 3) < prioridade_intrinseca_no(3, 5, 1)


def test_cliente_overpass_streaming_progresso_em_mb_e_cancelamento_entre_blocos() -> None:
    # Gera um payload JSON > 128 KB para atravessar múltiplos blocos de 64 KB
    nos_grandes = [
        {"type": "node", "id": i, "lat": -19.5, "lon": -43.9, "pad": "x" * 200}
        for i in range(1, 700)
    ]
    corpo_grande = json.dumps({"elements": nos_grandes}).encode("utf-8")
    assert len(corpo_grande) > 131072

    def abridor_streaming(req: urllib.request.Request, timeout: float) -> Any:
        resposta = io.BytesIO(corpo_grande)
        resposta.status = 200  # type: ignore[attr-defined]
        return resposta

    cliente = ClienteOverpass(
        url_endpoint="https://overpass.exemplo/api/interpreter",
        abridor_url=abridor_streaming,
    )
    eventos: list[tuple[str, int]] = []
    elementos = cliente.consultar_malha(
        -19.5,
        -43.9,
        ao_progresso=lambda msg, pct: eventos.append((msg, pct)),
    )
    assert len(elementos) == 699
    assert any("overpass.exemplo" in msg and "MB" in msg for msg, _ in eventos)
    assert all(15 <= pct <= 42 for _, pct in eventos)

    # Cancelamento após o primeiro bloco lido interrompe imediatamente
    leituras = 0

    def verificar_cancelamento_no_meio() -> bool:
        nonlocal leituras
        leituras += 1
        return leituras >= 3

    with pytest.raises(ErroMalhaEstradaCancelada, match="cancelada"):
        cliente.consultar_malha(
            -19.5,
            -43.9,
            verificador_cancelamento=verificar_cancelamento_no_meio,
        )


def test_calcular_velocidade_sem_transito_e_dijkstra_escolhe_caminho_mais_rapido() -> None:
    assert calcular_velocidade_sem_transito_kmh({"highway": "motorway"}) == 95.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "trunk"}) == 80.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "primary"}) == 70.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "secondary"}) == 55.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "tertiary"}) == 45.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "unclassified"}) == 35.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "residential"}) == 25.0
    assert calcular_velocidade_sem_transito_kmh({"highway": "track"}) == 20.0
    assert (
        calcular_velocidade_sem_transito_kmh({"highway": "secondary", "surface": "unpaved"}) == 30.0
    )
    assert (
        calcular_velocidade_sem_transito_kmh({"highway": "unclassified", "surface": "dirt"}) == 25.0
    )
    assert (
        calcular_velocidade_sem_transito_kmh({"highway": "primary", "maxspeed": "100 km/h"}) == 85.0
    )
    assert (
        calcular_velocidade_sem_transito_kmh({"highway": "primary", "maxspeed": "signals"}) == 70.0
    )

    # Pico em (0.0, 0.0) -> nó 1
    # Nó de origem 2 em (0.09, 0.0) (~10 km em linha reta):
    # - Rota A (direta por track de terra, ~10 km a 20 km/h => ~30 min): 1 -> 2
    # - Rota B (desvio por motorway via nó 3 em (0.045, 0.07), ~18.7 km a 95 km/h => ~12 min): 1 -> 3 -> 2
    elementos: list[dict[str, Any]] = [
        {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
        {"type": "node", "id": 2, "lat": 0.09, "lon": 0.0},
        {"type": "node", "id": 3, "lat": 0.045, "lon": 0.07},
        {"type": "way", "id": 10, "nodes": [1, 2], "tags": {"highway": "track"}},
        {"type": "way", "id": 20, "nodes": [1, 3, 2], "tags": {"highway": "motorway"}},
    ]
    fake = ClienteOverpassFake(elementos_padrao=elementos)

    pico = croqui_pb2.Pico(nome="Pico Rápido")
    pico.localizacao.latitude = 0
    pico.localizacao.longitude = 100
    malha_proto = construir_malha_estrada_pico_proto(0, 100, fake)
    pico.malha_estrada.conteudo.CopyFrom(malha_proto)

    _, dists = extrair_linhas_malha_de_pico_proto("uid_rapido", pico)
    mapa_dist = {d["no_osm_id"]: d for d in dists}

    assert mapa_dist[1]["distancia_metros"] == 0
    assert mapa_dist[1]["duracao_minutos"] == 0
    # Nó 2 deve ter sido alcançado pela Rota B (motorway: ~18.7 km e ~12 min, em vez de ~10 km e ~30 min)
    assert mapa_dist[2]["distancia_metros"] > 15000
    assert 10 <= mapa_dist[2]["duracao_minutos"] <= 14


def test_eleicao_por_quadrante_inteiro_e_grau_estavel_por_camada() -> None:
    # 1. Quadrante (1, 6, 0) de 0.02° [0.12°, 0.14°) cortado pela fronteira de 15 km:
    #    - Nó 20 (secondary, rank 3) em lat=0.130° (~14.47 km do pico em 0.0 -> <= 15 km)
    #    - Nó 21 (motorway, rank 1) em lat=0.138° (~15.36 km do pico em 0.0 -> > 15 km)
    #    O quadrante (1, 6, 0) é ativado pelo Nó 20 (<= 15 km), mas deve eleger o vencedor
    #    intrínseco do quadrante inteiro (Nó 21, motorway), sem partir o quadrante ao meio!
    # 2. Quadrante (3, 5, 0) de 0.18° [0.90°, 1.08°) cortado pelo limite de 200 km por estrada:
    #    - Nó 30 (secondary, rank 3) em lat=0.91°, lon=0.01° alcançado a ~195 km por estrada (<= 200 km)
    #    - Nó 31 (motorway, rank 1) em lat=0.95°, lon=0.01° alcançado a ~202 km por estrada (> 200 km)
    #    Como o quadrante (3, 5, 0) está dentro de 200 km por estrada via Nó 30, deve eleger seu
    #    vencedor intrínseco oficial (Nó 31) mesmo que Nó 31 esteja um pouco acima de 200 km.
    # 3. Grau estável por camada no quadrante (1, 2, 0) [0.04°, 0.06°):
    #    - Nós 40 e 41 ambos em rodovia tertiary (rank 4) com grau 2 na camada rank <= 4,
    #      mas o nó de pior CRC32 recebe uma rua residential (rank 5) extra.
    #      A rua residential (rank 5) não deve inflar o grau do nó tertiary (rank 4).
    id_melhor_crc, id_pior_crc = (
        (40, 41)
        if prioridade_intrinseca_no(40, 4, 2) < prioridade_intrinseca_no(41, 4, 2)
        else (41, 40)
    )
    elementos: list[dict[str, Any]] = [
        {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0},
        # Caso 1: quadrante (1, 6, 0) [0.12°, 0.14°) na borda de 15 km
        # Nó 20 (secondary, rank 3) em 0.130° (~14.47 km <= 15 km)
        # Nó 22 (intermediário em 0.145°, fora do quadrante 6) faz a transição para motorway
        # Nó 21 (motorway, rank 1) em 0.138° (~15.36 km > 15 km, mas dentro do quadrante 6!)
        {"type": "node", "id": 20, "lat": 0.130, "lon": 0.005},
        {"type": "node", "id": 22, "lat": 0.145, "lon": 0.005},
        {"type": "node", "id": 21, "lat": 0.138, "lon": 0.010},
        {"type": "way", "id": 200, "nodes": [1, 20, 22], "tags": {"highway": "secondary"}},
        {"type": "way", "id": 201, "nodes": [22, 21], "tags": {"highway": "motorway"}},
        # Caso 2: quadrante (3, 5, 0) [0.90°, 1.08°) na borda de 200 km por estrada
        # Nó 30 (secondary, rank 3) em (0.91, 0.01) alcançado via Nó 29 (0.45, 0.70) a ~186 km (<= 200 km)
        # Nó 32 (intermediário em 1.10°, fora do quadrante 5) leva ao Nó 31 (motorway, rank 1) em (0.95, 0.05) a ~225 km (> 200 km)
        {"type": "node", "id": 29, "lat": 0.450, "lon": 0.700},
        {"type": "node", "id": 30, "lat": 0.910, "lon": 0.010},
        {"type": "node", "id": 32, "lat": 1.100, "lon": 0.010},
        {"type": "node", "id": 31, "lat": 0.950, "lon": 0.050},
        {"type": "way", "id": 300, "nodes": [1, 29, 30, 32], "tags": {"highway": "secondary"}},
        {"type": "way", "id": 301, "nodes": [32, 31], "tags": {"highway": "motorway"}},
        # Caso 3: quadrante (1, 2, 0) com via tertiary (rank 4) + rua residential (rank 5)
        {"type": "node", "id": 39, "lat": 0.035, "lon": 0.005},
        {"type": "node", "id": id_melhor_crc, "lat": 0.045, "lon": 0.005},
        {"type": "node", "id": id_pior_crc, "lat": 0.050, "lon": 0.005},
        {"type": "node", "id": 42, "lat": 0.065, "lon": 0.005},
        {"type": "node", "id": 43, "lat": 0.050, "lon": 0.010},
        {
            "type": "way",
            "id": 400,
            "nodes": [1, 39, id_melhor_crc, id_pior_crc, 42],
            "tags": {"highway": "tertiary"},
        },
        {
            "type": "way",
            "id": 401,
            "nodes": [id_pior_crc, 43],
            "tags": {"highway": "residential"},
        },
    ]
    fake = ClienteOverpassFake(elementos_padrao=elementos)
    _, distancias = gerar_malha_estrada_pico("uid_quadrante", 0, 100, fake)
    ids_escolhidos = {d["no_osm_id"] for d in distancias}

    # Caso 1: Nó 21 (motorway) vence o quadrante (1, 6, 0) inteiro
    assert 21 in ids_escolhidos
    assert 20 not in ids_escolhidos
    # Caso 2: Nó 31 (motorway, ~202 km por estrada) vence o quadrante (3, 5, 0) ativado pelo Nó 30 (~198 km)
    assert 31 in ids_escolhidos
    assert 30 not in ids_escolhidos
    # Caso 3: id_melhor_crc vence id_pior_crc pois a rua residential (rank 5) não infla o grau do nó tertiary (rank 4)
    assert id_melhor_crc in ids_escolhidos
    assert id_pior_crc not in ids_escolhidos
