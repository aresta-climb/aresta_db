# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from aresta_api.proto.generated import croqui_pb2
from editor.models.readonly_proxy import ReadOnlyProxy
from editor.core.rotulos_referencia import extrair_rotulo_referencia


def test_extrair_rotulo_referencia_sem_ids():
    """Retorna string vazia quando a referência não possui IDs ou é nula."""
    mapa = croqui_pb2.Mapa()
    ref = croqui_pb2.Mapa.Referencia()
    assert extrair_rotulo_referencia(mapa, ref) == ""
    assert extrair_rotulo_referencia(None, ref) == ""
    assert extrair_rotulo_referencia(mapa, None) == ""


def test_extrair_rotulo_referencia_poi_convencional_com_label():
    """Retorna o rótulo de um POI convencional que possui label."""
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add()
    poi.id = "poi_1"
    poi.label = "P1"

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("poi_1")

    assert extrair_rotulo_referencia(mapa, ref) == "P1"


def test_extrair_rotulo_referencia_poi_convencional_sem_label():
    """Retorna vazio se o POI convencional tem label vazio (sem fallback para id)."""
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add()
    poi.id = "poi_sem_label"
    poi.label = ""

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("poi_sem_label")

    assert extrair_rotulo_referencia(mapa, ref) == ""


def test_extrair_rotulo_referencia_caminho_vetorial_multiplos_segmentos():
    """Extrai início e top de caminho vetorial com múltiplos segmentos (ex: 5-C)."""
    mapa = croqui_pb2.Mapa()

    # Segmento 1: início com círculo identificador "5"
    p1 = mapa.pontos_de_interesse.add()
    p1.id = "linha_12"
    m1 = p1.linha.compilado.marcadores.add()
    m1.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    m1.rotulo = "5"

    # Segmento 2: passagem intermediária (sem círculo)
    p2 = mapa.pontos_de_interesse.add()
    p2.id = "linha_16"
    m2 = p2.linha.compilado.marcadores.add()
    m2.tipo = croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
    m2.rotulo = ""

    # Segmento 3: final com top "C"
    p3 = mapa.pontos_de_interesse.add()
    p3.id = "linha_21"
    m3 = p3.linha.compilado.marcadores.add()
    m3.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    m3.rotulo = "C"

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.extend(["linha_12", "linha_16", "linha_21"])

    assert extrair_rotulo_referencia(mapa, ref) == "5-C"


def test_extrair_rotulo_referencia_multiplos_circulos_identificadores():
    """Extrai múltiplos nós identificadores na ordem sequencial exata."""
    mapa = croqui_pb2.Mapa()

    p = mapa.pontos_de_interesse.add()
    p.id = "linha_complexa"

    m1 = p.linha.compilado.marcadores.add()
    m1.tipo = croqui_pb2.NoTrajeto.TipoNo.INICIO_AGACHADO
    m1.rotulo = "SS"

    m2 = p.linha.compilado.marcadores.add()
    m2.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    m2.rotulo = "1"

    m3 = p.linha.compilado.marcadores.add()
    m3.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    m3.rotulo = "TOP"

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("linha_complexa")

    assert extrair_rotulo_referencia(mapa, ref) == "SS-1-TOP"


def test_extrair_rotulo_referencia_modo_edicao_conteudo_nos():
    """Extrai rótulos de nós contidos em conteudo.nos durante a edição no editor."""
    mapa = croqui_pb2.Mapa()

    p = mapa.pontos_de_interesse.add()
    p.id = "linha_edicao"

    n1 = p.linha.conteudo.nos.add()
    n1.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    n1.rotulo = "42"

    n2 = p.linha.conteudo.nos.add()
    n2.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    n2.rotulo = "X"

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("linha_edicao")

    # Testa com ReadOnlyProxy também
    proxy_mapa = ReadOnlyProxy(mapa)
    assert extrair_rotulo_referencia(proxy_mapa, ref) == "42-X"


def test_extrair_rotulo_referencia_deduplicacao_consecutiva():
    """Deduplica rótulos consecutivos idênticos de segmentos contíguos."""
    mapa = croqui_pb2.Mapa()

    p1 = mapa.pontos_de_interesse.add()
    p1.id = "seg_1"
    n1 = p1.linha.conteudo.nos.add()
    n1.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    n1.rotulo = "5"

    p2 = mapa.pontos_de_interesse.add()
    p2.id = "seg_2"
    # Ambos os segmentos têm o nó compartilhado "5"
    n2a = p2.linha.conteudo.nos.add()
    n2a.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    n2a.rotulo = "5"
    n2b = p2.linha.conteudo.nos.add()
    n2b.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    n2b.rotulo = "C"

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.extend(["seg_1", "seg_2"])

    assert extrair_rotulo_referencia(mapa, ref) == "5-C"


def test_extrair_rotulo_referencia_sem_circulos_retorna_vazio():
    """Retorna vazio para linhas sem círculos identificadores (nunca expõe linha_XX)."""
    mapa = croqui_pb2.Mapa()

    p = mapa.pontos_de_interesse.add()
    p.id = "linha_pura"
    n = p.linha.conteudo.nos.add()
    n.tipo = croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
    n.rotulo = ""

    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("linha_pura")

    assert extrair_rotulo_referencia(mapa, ref) == ""


def test_extrair_rotulo_referencia_com_dicionarios():
    """Funciona também com estruturas em formato dict (compatibilidade)."""
    mapa_dict = {
        "pontos_de_interesse": [
            {
                "id": "p_dict_1",
                "linha": {
                    "conteudo": {
                        "nos": [
                            {"tipo": "circulo_identificador", "rotulo": "A"},
                            {"tipo": "FIM_TOP", "rotulo": "B"}
                        ]
                    }
                }
            }
        ]
    }
    ref_dict = {
        "ids": ["p_dict_1", "id_inexistente"]
    }
    assert extrair_rotulo_referencia(mapa_dict, ref_dict) == "A-B"

