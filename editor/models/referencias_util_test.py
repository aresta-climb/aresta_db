# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from aresta_api.proto.generated import croqui_pb2
from editor.models.referencias_util import (
    referencia_aponta_para_escalada,
    obter_contexto_escalada,
    buscar_referencias_para_escalada,
    extrair_nome_escalada,
)


def test_referencia_aponta_para_escalada_mesmo_setor_implicito():
    ref = croqui_pb2.Mapa.Referencia(escalada="Via Teste")
    # No mesmo setor, setor e grupo são implícitos pelo mapa
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome="Setor A",
        mapa_grupo_nome="Grupo 1",
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome="Grupo 1",
    ) is True


def test_referencia_aponta_para_escalada_nome_diferente():
    ref = croqui_pb2.Mapa.Referencia(escalada="Outra Via")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome="Setor A",
        mapa_grupo_nome=None,
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome=None,
    ) is False


def test_referencia_aponta_para_escalada_sem_escalada():
    ref = croqui_pb2.Mapa.Referencia(setor="Setor A")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome="Setor A",
        mapa_grupo_nome=None,
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome=None,
    ) is False


def test_referencia_aponta_para_escalada_setor_vizinho_explicito():
    # Mapa está no Setor B, mas referência aponta explicitamente para Setor A
    ref = croqui_pb2.Mapa.Referencia(setor="Setor A", escalada="Via Teste")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome="Setor B",
        mapa_grupo_nome=None,
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome=None,
    ) is True


def test_referencia_aponta_para_escalada_setor_divergente():
    # Referência no Setor B sem especificar setor aponta para via do Setor B, não Setor A
    ref = croqui_pb2.Mapa.Referencia(escalada="Via Teste")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome="Setor B",
        mapa_grupo_nome=None,
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome=None,
    ) is False


def test_referencia_aponta_para_escalada_mapa_de_grupo_implicito():
    # Mapa do Grupo 1: setor é explícito na ref ("Setor A"), grupo é implícito pelo mapa ("Grupo 1")
    ref = croqui_pb2.Mapa.Referencia(setor="Setor A", escalada="Via Teste")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome=None,
        mapa_grupo_nome="Grupo 1",
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome="Grupo 1",
    ) is True


def test_referencia_aponta_para_escalada_grupo_divergente():
    # Referência aponta explicitamente para outro grupo
    ref = croqui_pb2.Mapa.Referencia(grupo="Grupo 2", setor="Setor A", escalada="Via Teste")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome=None,
        mapa_grupo_nome="Grupo 1",
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome="Grupo 1",
    ) is False


def test_referencia_aponta_para_escalada_sem_grupo_mas_ref_com_grupo():
    # Escalada alvo não tem grupo, mas ref ou mapa tem grupo
    ref = croqui_pb2.Mapa.Referencia(grupo="Grupo 1", setor="Setor A", escalada="Via Teste")
    assert referencia_aponta_para_escalada(
        ref=ref,
        mapa_setor_nome=None,
        mapa_grupo_nome="Grupo 1",
        alvo_escalada_nome="Via Teste",
        alvo_setor_nome="Setor A",
        alvo_grupo_nome=None,
    ) is False


def _criar_croqui_com_arvore_completa():
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico dos Sonhos")

    # Mapa no Pico
    mapa_pico = pico.mapas_gerais.conteudo.mapas.add(caminho_imagem_mapa="mapa_pico.webp")
    ref_pico = mapa_pico.referencias.add(
        grupo="Grupo Alfa", setor="Setor Sul", escalada="Fenda Infinita"
    )

    # 1. Grupo Alfa com Setor Sul
    sg_grupo = pico.setores_ou_grupos.add()
    grupo = sg_grupo.grupo.conteudo
    grupo.nome = "Grupo Alfa"
    mapa_grupo = grupo.mapas.add(caminho_imagem_mapa="mapa_grupo.webp")
    ref_grupo = mapa_grupo.referencias.add(
        setor="Setor Sul", escalada="Fenda Infinita"
    )

    setor_item = grupo.setores.add()
    setor_sul = setor_item.conteudo
    setor_sul.nome = "Setor Sul"
    mapa_setor_sul = setor_sul.mapas.add(caminho_imagem_mapa="mapa_sul.webp")
    ref_sul = mapa_setor_sul.referencias.add(escalada="Fenda Infinita")

    # Escaladas no Setor Sul
    esc1 = setor_sul.escaladas.add()
    esc1.via_esportiva.nome = "Fenda Infinita"

    esc_mult = setor_sul.escaladas.add()
    esc_mult.via_multiplas_enfiadas.nome = "Grande Parede"
    mapa_mult = esc_mult.via_multiplas_enfiadas.mapas.add(caminho_imagem_mapa="mapa_mult.webp")
    ref_mult = mapa_mult.referencias.add(escalada="Enfiada Crux")
    enf1 = esc_mult.via_multiplas_enfiadas.enfiadas.add()
    enf1.via_esportiva.nome = "Enfiada Crux"

    # 2. Setor Isolado (Direto no Pico)
    sg_setor = pico.setores_ou_grupos.add()
    setor_norte = sg_setor.setor.conteudo
    setor_norte.nome = "Setor Norte"
    mapa_norte = setor_norte.mapas.add(caminho_imagem_mapa="mapa_norte.webp")
    # Referência cross-sector no Setor Norte apontando para a Fenda Infinita no Setor Sul
    ref_cross = mapa_norte.referencias.add(
        grupo="Grupo Alfa", setor="Setor Sul", escalada="Fenda Infinita"
    )
    # Referência para via própria do Setor Norte
    ref_norte_propria = mapa_norte.referencias.add(escalada="Via do Norte")
    esc_norte = setor_norte.escaladas.add()
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
    via_orfa = croqui_pb2.ViaEsportiva(nome="Órfã")
    refs = buscar_referencias_para_escalada(croqui, via_orfa)
    assert refs == []


def test_cobertura_proxy_e_wrapper_escalada():
    from editor.models.readonly_proxy import ReadOnlyProxy
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
    mapa_mult = esc_mult.via_multiplas_enfiadas.mapas.add(caminho_imagem_mapa="mapa_trad.webp")
    ref_enf = mapa_mult.referencias.add(escalada="P2 Isolada")

    enf = esc_mult.via_multiplas_enfiadas.enfiadas.add()
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
    from unittest.mock import MagicMock
    pico_mock = MagicMock()
    mapa_mock = MagicMock()
    ref_mock = MagicMock()
    ref_mock.escalada = "Via Mock"
    ref_mock.setor = "Setor M"
    ref_mock.grupo = ""
    mapa_mock.referencias = [ref_mock]
    del pico_mock.mapas_gerais
    pico_mock.mapas = [mapa_mock]
    pico_mock.setores_ou_grupos = []

    croqui_mock = MagicMock()
    croqui_mock.picos = [pico_mock]

    via_mock = MagicMock()
    via_mock.nome = "Via Mock"

    # Contexto manual
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "editor.models.referencias_util.obter_contexto_escalada",
            lambda r, m: (pico_mock, None, MagicMock(nome="Setor M"), "Via Mock"),
        )
        refs = buscar_referencias_para_escalada(croqui_mock, via_mock)
        assert len(refs) == 1

