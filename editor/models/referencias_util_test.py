# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import MagicMock
from aresta_api.proto.generated import croqui_pb2
from editor.models.readonly_proxy import ReadOnlyProxy
from editor.models.referencias_util import (
    referencia_aponta_para_escalada,
    obter_contexto_escalada,
    buscar_referencias_para_escalada,
    extrair_nome_escalada,
    obter_contexto_por_uid,
    resolver_caminho_referencia,
)


def test_referencia_aponta_para_escalada_uid_correspondente():
    ref = croqui_pb2.Mapa.Referencia(alvo_uid="via_123")
    assert referencia_aponta_para_escalada(ref, "via_123") is True


def test_referencia_aponta_para_escalada_uid_divergente():
    ref = croqui_pb2.Mapa.Referencia(alvo_uid="via_123")
    assert referencia_aponta_para_escalada(ref, "via_456") is False


def test_referencia_aponta_para_escalada_alvo_uid_vazio_ou_nulo():
    ref = croqui_pb2.Mapa.Referencia()
    assert referencia_aponta_para_escalada(ref, "") is False
    assert referencia_aponta_para_escalada(None, "via_123") is False
    assert referencia_aponta_para_escalada(ref, "via_123") is False


def test_referencia_aponta_para_escalada_com_readonly_proxy():
    ref = croqui_pb2.Mapa.Referencia(alvo_uid="via_proxy")
    proxy = ReadOnlyProxy(ref)
    assert referencia_aponta_para_escalada(proxy, "via_proxy") is True
    assert referencia_aponta_para_escalada(proxy, "outro") is False


def _criar_croqui_com_arvore_completa():
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico dos Sonhos")

    # Mapa no Pico
    mapa_pico = pico.mapas_gerais.conteudo.mapas.add(caminho_imagem_mapa="mapa_pico.webp")
    ref_pico = mapa_pico.referencias.add(alvo_uid="uid_esc1", pontos_uids=["poi_pico"])

    # 1. Grupo Alfa com Setor Sul
    sg_grupo = pico.setores_ou_grupos.add()
    grupo = sg_grupo.grupo.conteudo
    grupo.nome = "Grupo Alfa"
    grupo.uid = "uid_grupo_alfa"
    mapa_grupo = grupo.mapas.add(caminho_imagem_mapa="mapa_grupo.webp")
    ref_grupo = mapa_grupo.referencias.add(alvo_uid="uid_esc1", pontos_uids=["poi_grupo"])

    setor_item = grupo.setores.add()
    setor_sul = setor_item.conteudo
    setor_sul.nome = "Setor Sul"
    setor_sul.uid = "uid_setor_sul"
    mapa_setor_sul = setor_sul.mapas.add(caminho_imagem_mapa="mapa_sul.webp")
    ref_sul = mapa_setor_sul.referencias.add(alvo_uid="uid_esc1", pontos_uids=["poi_sul"])

    # Escaladas no Setor Sul
    esc1 = setor_sul.escaladas.add()
    esc1.uid = "uid_esc1"
    esc1.via_esportiva.nome = "Fenda Infinita"

    esc_mult = setor_sul.escaladas.add()
    esc_mult.uid = "uid_esc_mult"
    esc_mult.via_multiplas_enfiadas.nome = "Grande Parede"
    mapa_mult = esc_mult.mapas.add(caminho_imagem_mapa="mapa_mult.webp")
    ref_mult = mapa_mult.referencias.add(alvo_uid="uid_enf1", pontos_uids=["poi_mult"])
    enf1 = esc_mult.via_multiplas_enfiadas.enfiadas.add()
    enf1.uid = "uid_enf1"
    enf1.via_esportiva.nome = "Enfiada Crux"

    # 2. Setor Isolado (Direto no Pico)
    sg_setor = pico.setores_ou_grupos.add()
    setor_norte = sg_setor.setor.conteudo
    setor_norte.nome = "Setor Norte"
    setor_norte.uid = "uid_setor_norte"
    mapa_norte = setor_norte.mapas.add(caminho_imagem_mapa="mapa_norte.webp")
    ref_cross = mapa_norte.referencias.add(alvo_uid="uid_esc1", pontos_uids=["poi_cross"])
    ref_norte_propria = mapa_norte.referencias.add(alvo_uid="uid_boulder_norte", pontos_uids=["poi_norte"])

    esc_norte = setor_norte.escaladas.add()
    esc_norte.uid = "uid_boulder_norte"
    esc_norte.boulder.nome = "Via do Norte"

    return {
        "croqui": croqui,
        "pico": pico,
        "grupo": grupo,
        "setor_sul": setor_sul,
        "setor_norte": setor_norte,
        "esc1": esc1.via_esportiva,
        "enf1": enf1.via_esportiva,
        "esc_norte": esc_norte.boulder,
        "ref_pico": ref_pico,
        "ref_grupo": ref_grupo,
        "ref_sul": ref_sul,
        "ref_cross": ref_cross,
        "ref_norte_propria": ref_norte_propria,
        "ref_mult": ref_mult,
    }


def test_obter_contexto_escalada_em_grupo():
    dados = _criar_croqui_com_arvore_completa()
    pico, grupo, setor, nome = obter_contexto_escalada(dados["croqui"], dados["esc1"])
    assert pico.nome == "Pico dos Sonhos"
    assert grupo.nome == "Grupo Alfa"
    assert setor.nome == "Setor Sul"
    assert nome == "Fenda Infinita"


def test_obter_contexto_escalada_isolada():
    dados = _criar_croqui_com_arvore_completa()
    pico, grupo, setor, nome = obter_contexto_escalada(dados["croqui"], dados["esc_norte"])
    assert pico.nome == "Pico dos Sonhos"
    assert grupo is None
    assert setor.nome == "Setor Norte"
    assert nome == "Via do Norte"


def test_obter_contexto_enfiada_em_via_multiplas_enfiadas():
    dados = _criar_croqui_com_arvore_completa()
    pico, grupo, setor, nome = obter_contexto_escalada(dados["croqui"], dados["enf1"])
    assert pico.nome == "Pico dos Sonhos"
    assert grupo.nome == "Grupo Alfa"
    assert setor.nome == "Setor Sul"
    assert nome == "Enfiada Crux"


def test_obter_contexto_escalada_orfa():
    croqui = croqui_pb2.Croqui()
    via_orfa = croqui_pb2.ViaEsportiva(nome="Órfã")
    pico, grupo, setor, nome = obter_contexto_escalada(croqui, via_orfa)
    assert pico is None
    assert grupo is None
    assert setor is None
    assert nome == "Órfã"


def test_buscar_referencias_para_escalada():
    dados = _criar_croqui_com_arvore_completa()
    refs = buscar_referencias_para_escalada(dados["croqui"], dados["esc1"])

    # Deve encontrar: ref_pico, ref_grupo, ref_sul e ref_cross
    assert len(refs) == 4
    assert dados["ref_pico"] in refs
    assert dados["ref_grupo"] in refs
    assert dados["ref_sul"] in refs
    assert dados["ref_cross"] in refs
    # Não deve encontrar referências a outras vias
    assert dados["ref_norte_propria"] not in refs
    assert dados["ref_mult"] not in refs


def test_buscar_referencias_para_enfiada():
    dados = _criar_croqui_com_arvore_completa()
    refs = buscar_referencias_para_escalada(dados["croqui"], dados["enf1"])
    assert len(refs) == 1
    assert dados["ref_mult"] in refs


def test_buscar_referencias_sem_pico():
    croqui = croqui_pb2.Croqui()
    via_orfa = croqui_pb2.Escalada(uid="uid_orfa")
    via_orfa.via_esportiva.nome = "Órfã"
    refs = buscar_referencias_para_escalada(croqui, via_orfa)
    assert refs == []


def test_buscar_referencias_sem_uid():
    croqui = croqui_pb2.Croqui()
    via_sem_uid = croqui_pb2.Escalada()
    via_sem_uid.via_esportiva.nome = "Sem UID"
    refs = buscar_referencias_para_escalada(croqui, via_sem_uid)
    assert refs == []


def test_cobertura_proxy_e_wrapper_escalada():
    dados = _criar_croqui_com_arvore_completa()
    croqui_proxy = ReadOnlyProxy(dados["croqui"])
    esc_proxy = ReadOnlyProxy(dados["esc1"])

    # Proxy desempacotado com sucesso
    pico, grupo, setor, nome = obter_contexto_escalada(croqui_proxy, esc_proxy)
    assert nome == "Fenda Infinita"
    assert pico.nome == "Pico dos Sonhos"

    # Wrapper Escalada direto
    setor_sul = dados["setor_sul"]
    esc_wrapper = setor_sul.escaladas[0]
    pico2, grupo2, setor2, nome2 = obter_contexto_escalada(dados["croqui"], esc_wrapper)
    assert nome2 == "Fenda Infinita"

    # Objeto sem nome
    assert extrair_nome_escalada(object()) == ""


def test_cobertura_objeto_sem_picos():
    pico, grupo, setor, nome = obter_contexto_escalada(object(), "invalido")
    assert pico is None
    assert grupo is None
    assert setor is None


def test_cobertura_enfiada_em_setor_isolado_sem_grupo():
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 2")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Isolado"

    esc_mult = setor.escaladas.add()
    esc_mult.via_multiplas_enfiadas.nome = "Via Trad Isolada"
    mapa_mult = esc_mult.mapas.add(caminho_imagem_mapa="mapa_trad.webp")
    ref_enf = mapa_mult.referencias.add(alvo_uid="uid_enf_isolada")

    enf = esc_mult.via_multiplas_enfiadas.enfiadas.add()
    enf.uid = "uid_enf_isolada"
    enf.via_esportiva.nome = "P2 Isolada"

    pico_ctx, grupo_ctx, setor_ctx, nome = obter_contexto_escalada(croqui, enf.via_esportiva)
    assert pico_ctx.nome == "Pico 2"
    assert grupo_ctx is None
    assert setor_ctx.nome == "Setor Isolado"
    assert nome == "P2 Isolada"

    refs = buscar_referencias_para_escalada(croqui, enf.via_esportiva)
    assert len(refs) == 1
    assert ref_enf in refs


def test_cobertura_pico_com_mapas_diretos():
    pico_mock = MagicMock()
    mapa_mock = MagicMock()
    ref_mock = MagicMock()
    ref_mock.alvo_uid = "uid_mock"
    mapa_mock.referencias = [ref_mock]
    del pico_mock.mapas_gerais
    pico_mock.mapas = [mapa_mock]
    pico_mock.setores_ou_grupos = []

    croqui_mock = MagicMock()
    croqui_mock.picos = [pico_mock]

    via_mock = MagicMock()
    via_mock.uid = "uid_mock"
    via_mock.nome = "Via Mock"

    # Contexto manual
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "editor.models.referencias_util.obter_contexto_escalada",
            lambda r, m: (pico_mock, None, MagicMock(nome="Setor M"), "Via Mock"),
        )
        refs = buscar_referencias_para_escalada(croqui_mock, via_mock)
        assert len(refs) == 1


def test_obter_contexto_por_uid_e_resolver_caminho_referencia():
    dados = _criar_croqui_com_arvore_completa()
    croqui = dados["croqui"]

    # Grupo
    ctx_grupo = obter_contexto_por_uid(croqui, "uid_grupo_alfa")
    assert ctx_grupo == ("Grupo", "Grupo Alfa")

    # Setor em Grupo
    ctx_setor = obter_contexto_por_uid(croqui, "uid_setor_sul")
    assert ctx_setor == ("Setor", "Grupo Alfa > Setor Sul")

    # Escalada em Grupo > Setor
    ctx_esc = obter_contexto_por_uid(croqui, "uid_esc1")
    assert ctx_esc == ("Escalada", "Grupo Alfa > Setor Sul > Fenda Infinita")

    # Enfiada em Grupo > Setor > Via Múltiplas Enfiadas
    ctx_enf = obter_contexto_por_uid(croqui, "uid_enf1")
    assert ctx_enf == ("Escalada", "Grupo Alfa > Setor Sul > Grande Parede (1ª Enfiada)")

    # Setor Isolado
    ctx_setor_norte = obter_contexto_por_uid(croqui, "uid_setor_norte")
    assert ctx_setor_norte == ("Setor", "Setor Norte")

    # Escalada em Setor Isolado
    ctx_boulder = obter_contexto_por_uid(croqui, "uid_boulder_norte")
    assert ctx_boulder == ("Escalada", "Setor Norte > Via do Norte")

    # Enfiada em Setor Isolado > Via Múltiplas Enfiadas
    esc_mult_iso = dados["setor_norte"].escaladas.add()
    esc_mult_iso.via_multiplas_enfiadas.nome = "Paredão Norte"
    enf_iso = esc_mult_iso.via_multiplas_enfiadas.enfiadas.add()
    enf_iso.uid = "uid_enf_norte"
    enf_iso.via_esportiva.nome = "E1"
    ctx_enf_iso = obter_contexto_por_uid(croqui, "uid_enf_norte")
    assert ctx_enf_iso == ("Escalada", "Setor Norte > Paredão Norte (1ª Enfiada)")

    # UID inexistente ou vazio
    assert obter_contexto_por_uid(croqui, "uid_inexistente") is None
    assert obter_contexto_por_uid(croqui, "") is None
    assert obter_contexto_por_uid(None, "uid_esc1") is None

    # resolver_caminho_referencia
    assert resolver_caminho_referencia(croqui, dados["ref_pico"]) == "Grupo Alfa > Setor Sul > Fenda Infinita"
    assert resolver_caminho_referencia(croqui, dados["ref_norte_propria"]) == "Setor Norte > Via do Norte"

    ref_invalida = croqui_pb2.Mapa.Referencia(alvo_uid="inexistente")
    assert resolver_caminho_referencia(croqui, ref_invalida) == "Referência Inválida"
    assert resolver_caminho_referencia(None, dados["ref_pico"]) == "Referência Inválida"
