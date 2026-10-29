# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a biblioteca de topologia e fatiamento de trajetos.
Princípios II (Library-First) e IV (TDD) de AGENTS.md.
100% de cobertura requerida.
"""

import pytest

from aresta_api.proto.generated import croqui_pb2
from editor.core.spline_catmull_rom import Ponto2D
from editor.core.topologia_trajeto import (
    ResultadoAnaliseConfluencia,
    ResultadoSnap,
    TipoSnap,
    adicionar_numero_inicio,
    atualizar_referencias_apos_fatiamento,
    calcular_proximo_numero_inicio_setor,
    calcular_snap,
    desambiguar_topos,
    descobrir_caminhos_confluencia,
    detectar_snap_curva,
    detectar_snap_nos,
    fatiar_linha_em_no,
    fatiar_linha_em_ponto_curva,
    fatiar_linha_triplo,
    formatar_rotulo_inicio,
    gerar_id_poi_disjunto_setor,
    obter_proxima_letra_top,
    obter_rotulo_escalada_no_setor,
    projetar_ponto_em_segmento,
    remover_numero_inicio,
)
from scripts.gerenciar_uids_lib import validar_uid


def _criar_linha_pb(id_linha: str, pontos: list, rotulo_inicio: str = "", rotulo_fim: str = ""):
    """Função auxiliar para criar um PontoDeInteresse do tipo linha para testes."""
    poi = croqui_pb2.Mapa.PontoDeInteresse(uid=id_linha)
    poi.linha.estilo = croqui_pb2.LinhaTrajeto.EstiloTraco.TRACEJADO
    for i, (x, y) in enumerate(pontos):
        no = poi.linha.conteudo.nos.add(x=int(x), y=int(y))
        if i == 0 and rotulo_inicio:
            no.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
            no.rotulo = rotulo_inicio
        elif i == len(pontos) - 1 and rotulo_fim:
            no.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
            no.rotulo = rotulo_fim
        else:
            no.tipo = croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
    return poi


class TestSnapGeometrico:
    def test_projetar_ponto_em_segmento(self):
        p1 = Ponto2D(0, 0)
        p2 = Ponto2D(100, 0)

        # Ponto perpendicular no meio
        p_proj, t, dist = projetar_ponto_em_segmento(Ponto2D(50, 20), p1, p2)
        assert p_proj.x == pytest.approx(50)
        assert p_proj.y == pytest.approx(0)
        assert t == pytest.approx(0.5)
        assert dist == pytest.approx(20)

        # Ponto antes do início do segmento (clamp em p1)
        p_proj_ant, t_ant, dist_ant = projetar_ponto_em_segmento(Ponto2D(-20, 0), p1, p2)
        assert p_proj_ant.x == pytest.approx(0)
        assert t_ant == 0.0
        assert dist_ant == pytest.approx(20)

        # Ponto após o fim do segmento (clamp em p2)
        p_proj_pos, t_pos, dist_pos = projetar_ponto_em_segmento(Ponto2D(120, 0), p1, p2)
        assert p_proj_pos.x == pytest.approx(100)
        assert t_pos == 1.0
        assert dist_pos == pytest.approx(20)

        # Segmento degenerado (p1 == p2)
        p_deg, t_deg, dist_deg = projetar_ponto_em_segmento(Ponto2D(10, 10), p1, p1)
        assert p_deg == p1
        assert t_deg == 0.0
        assert dist_deg == pytest.approx(math_dist := Ponto2D(10, 10).distancia_ate(p1))

    def test_detectar_snap_nos_encontra_no_mais_proximo(self):
        linha1 = _criar_linha_pb("linha_1", [(100, 500), (120, 350), (140, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("linha_2", [(300, 500), (300, 100)], rotulo_inicio="2")

        snap = detectar_snap_nos(Ponto2D(102, 503), [linha1, linha2], raio_snap=10.0)
        assert snap is not None
        assert snap.tipo == TipoSnap.NO
        assert snap.coordenada.x == 100
        assert snap.coordenada.y == 500
        assert snap.id_linha == "linha_1"
        assert snap.indice_no == 0
        assert snap.rotulo == "1"

    def test_detectar_snap_nos_fora_do_raio_retorna_none(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (140, 100)])
        snap = detectar_snap_nos(Ponto2D(150, 500), [linha], raio_snap=10.0)
        assert snap is None

    def test_detectar_snap_curva_encontra_ponto_no_corpo_da_linha(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 300), (100, 100)])
        # Ponto próximo da vertical x=100 em y=400
        snap = detectar_snap_curva(Ponto2D(103, 400), [linha], raio_snap=10.0)
        assert snap is not None
        assert snap.tipo == TipoSnap.CURVA
        assert snap.coordenada.x == pytest.approx(100)
        assert snap.coordenada.y == pytest.approx(400)
        assert snap.id_linha == "linha_1"
        assert snap.indice_segmento == 0
        assert 0.0 < snap.fator_t < 1.0

    def test_detectar_snap_curva_fora_do_raio_retorna_none(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)])
        snap = detectar_snap_curva(Ponto2D(150, 300), [linha], raio_snap=10.0)
        assert snap is None

    def test_calcular_snap_prioriza_no_sobre_curva(self):
        # Nó em (100, 500). Ponto em (102, 498) está perto do nó E da linha que vai até (100, 100)
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)], rotulo_inicio="1")
        snap = calcular_snap(Ponto2D(102, 498), [linha], raio_snap=15.0)
        assert snap.tipo == TipoSnap.NO
        assert snap.coordenada.x == 100
        assert snap.coordenada.y == 500

    def test_calcular_snap_captura_curva_quando_longe_de_nos(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)], rotulo_inicio="1")
        # Ponto em (103, 300) está longe dos nós (100, 500) e (100, 100), mas a 3px da linha
        snap = calcular_snap(Ponto2D(103, 300), [linha], raio_snap=10.0)
        assert snap.tipo == TipoSnap.CURVA
        assert snap.coordenada.x == pytest.approx(100)
        assert snap.coordenada.y == pytest.approx(300)

    def test_snap_ignora_poi_sem_linha_e_linha_com_menos_de_dois_nos(self):
        poi_circulo = croqui_pb2.Mapa.PontoDeInteresse(uid="circ_1")
        poi_circulo.circulo.x = 100
        poi_linha_1_no = _criar_linha_pb("linha_curta", [(50, 50)])

        snap_no = detectar_snap_nos(Ponto2D(100, 100), [poi_circulo], raio_snap=20.0)
        assert snap_no is None

        snap_curva = detectar_snap_curva(
            Ponto2D(50, 50), [poi_circulo, poi_linha_1_no], raio_snap=20.0
        )
        assert snap_curva is None

    def test_calcular_snap_sem_convergencia_retorna_livre(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)])
        snap = calcular_snap(Ponto2D(500, 500), [linha], raio_snap=15.0)
        assert snap.tipo == TipoSnap.LIVRE
        assert snap.coordenada == Ponto2D(500, 500)


class TestFatiamentoTrajeto:
    def test_fatiar_linha_em_no_existente(self):
        linha = _criar_linha_pb(
            "linha_original", [(100, 500), (120, 350), (140, 200), (150, 100)], rotulo_inicio="1"
        )

        sub1, sub2 = fatiar_linha_em_no(linha, indice_no=2, id_sub1="seg_1", id_sub2="seg_2")

        # Sub1: nós 0..2
        nos1 = sub1.linha.conteudo.nos
        assert len(nos1) == 3
        assert (nos1[0].x, nos1[0].y) == (100, 500)
        assert (nos1[2].x, nos1[2].y) == (140, 200)
        assert sub1.uid == "seg_1"
        assert nos1[0].rotulo == "1"

        # Sub2: nós 2..3
        nos2 = sub2.linha.conteudo.nos
        assert len(nos2) == 2
        assert (nos2[0].x, nos2[0].y) == (140, 200)
        assert (nos2[1].x, nos2[1].y) == (150, 100)
        assert sub2.uid == "seg_2"

    def test_fatiar_linha_em_no_extremos_levanta_erro(self):
        linha = _criar_linha_pb("linha_original", [(100, 500), (120, 350), (140, 200)])
        with pytest.raises(ValueError):
            fatiar_linha_em_no(linha, indice_no=0, id_sub1="seg_1", id_sub2="seg_2")
        with pytest.raises(ValueError):
            fatiar_linha_em_no(linha, indice_no=2, id_sub1="seg_1", id_sub2="seg_2")

    def test_fatiar_linha_em_no_preservando_tipo_no_corte(self):
        linha = _criar_linha_pb("linha_original", [(100, 500), (120, 350), (140, 200)])
        linha.linha.conteudo.nos[1].tipo = croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA
        linha.linha.conteudo.nos[1].rotulo = "P1"
        sub1, sub2 = fatiar_linha_em_no(
            linha, indice_no=1, id_sub1="s1", id_sub2="s2", preservar_tipo_no_corte=True
        )
        assert sub1.linha.conteudo.nos[1].tipo == croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA
        assert sub1.linha.conteudo.nos[1].rotulo == "P1"
        assert sub2.linha.conteudo.nos[0].tipo == croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA
        assert sub2.linha.conteudo.nos[0].rotulo == "P1"

    def test_fatiar_linha_em_ponto_curva_insere_no_de_corte(self):
        linha = _criar_linha_pb(
            "linha_original", [(100, 500), (100, 300), (100, 100)], rotulo_inicio="1"
        )
        ponto_corte = Ponto2D(100, 200)  # no segmento entre nó 1 e nó 2

        sub1, sub2 = fatiar_linha_em_ponto_curva(
            linha, ponto_corte=ponto_corte, indice_segmento=1, id_sub1="seg_a", id_sub2="seg_b"
        )

        nos1 = sub1.linha.conteudo.nos
        assert len(nos1) == 3
        assert (nos1[2].x, nos1[2].y) == (100, 200)

        nos2 = sub2.linha.conteudo.nos
        assert len(nos2) == 2
        assert (nos2[0].x, nos2[0].y) == (100, 200)
        assert (nos2[1].x, nos2[1].y) == (100, 100)

    def test_fatiar_linha_triplo_travessia(self):
        linha = _criar_linha_pb("linha_base", [(100, 500), (100, 400), (100, 300), (100, 100)])
        sub_inicio, sub_meio, sub_fim = fatiar_linha_triplo(
            linha, indice_entrada=1, indice_saida=2, id_sub1="ini", id_sub2="meio", id_sub3="fim"
        )
        assert len(sub_inicio.linha.conteudo.nos) == 2  # 0..1
        assert len(sub_meio.linha.conteudo.nos) == 2  # 1..2
        assert len(sub_fim.linha.conteudo.nos) == 2  # 2..3
        assert (sub_meio.linha.conteudo.nos[0].x, sub_meio.linha.conteudo.nos[0].y) == (100, 400)
        assert (sub_meio.linha.conteudo.nos[1].x, sub_meio.linha.conteudo.nos[1].y) == (100, 300)

    def test_fatiar_linha_triplo_indices_invalidos_levanta_erro(self):
        linha = _criar_linha_pb("linha_base", [(100, 500), (100, 400), (100, 300), (100, 200)])
        # Entrada maior que saída
        with pytest.raises(ValueError):
            fatiar_linha_triplo(
                linha, indice_entrada=2, indice_saida=1, id_sub1="a", id_sub2="b", id_sub3="c"
            )
        # Índices negativos
        with pytest.raises(ValueError):
            fatiar_linha_triplo(
                linha, indice_entrada=-1, indice_saida=2, id_sub1="a", id_sub2="b", id_sub3="c"
            )
        # Entrada igual a saída (mesmo nó)
        with pytest.raises(ValueError):
            fatiar_linha_triplo(
                linha, indice_entrada=1, indice_saida=1, id_sub1="a", id_sub2="b", id_sub3="c"
            )
        # Entrada no índice 0 (não intermediário, sub1 ficaria com 1 nó)
        with pytest.raises(ValueError):
            fatiar_linha_triplo(
                linha, indice_entrada=0, indice_saida=2, id_sub1="a", id_sub2="b", id_sub3="c"
            )
        # Saída no último nó (não intermediário, sub3 ficaria com 1 nó)
        with pytest.raises(ValueError):
            fatiar_linha_triplo(
                linha, indice_entrada=1, indice_saida=3, id_sub1="a", id_sub2="b", id_sub3="c"
            )
        # Linha com menos de 4 nós
        linha_curta = _criar_linha_pb("curta", [(100, 500), (100, 400), (100, 300)])
        with pytest.raises(ValueError):
            fatiar_linha_triplo(
                linha_curta, indice_entrada=1, indice_saida=2, id_sub1="a", id_sub2="b", id_sub3="c"
            )

    def test_atualizar_referencias_apos_fatiamento(self):
        mapa = croqui_pb2.Mapa()
        ref1 = mapa.referencias.add(
            alvo_uid="Via 1", pontos_uids=["linha_outra", "linha_velha", "linha_fim"]
        )
        ref2 = mapa.referencias.add(alvo_uid="Via 2", pontos_uids=["linha_velha"])

        atualizar_referencias_apos_fatiamento(mapa.referencias, "linha_velha", ["seg_1", "seg_2"])

        assert list(ref1.pontos_uids) == ["linha_outra", "seg_1", "seg_2", "linha_fim"]
        assert list(ref2.pontos_uids) == ["seg_1", "seg_2"]


class TestConvencaoSemanticaOuroboulder:
    def test_formatar_rotulo_inicio(self):
        assert formatar_rotulo_inicio([1]) == "1"
        assert formatar_rotulo_inicio([1, 2]) == "1, 2"
        assert formatar_rotulo_inicio([3, 1, 2]) == "1, 2, 3"
        assert formatar_rotulo_inicio([]) == ""
        assert formatar_rotulo_inicio(["invalido", None, 5]) == "5"

    def test_adicionar_numero_inicio(self):
        assert adicionar_numero_inicio("", 1) == "1"
        assert adicionar_numero_inicio("1", 2) == "1, 2"
        assert adicionar_numero_inicio("2", 1) == "1, 2"
        assert adicionar_numero_inicio("1, 2", 2) == "1, 2"  # não duplica
        assert adicionar_numero_inicio("1, 3", 2) == "1, 2, 3"

    def test_remover_numero_inicio(self):
        assert remover_numero_inicio("1, 2", 2) == "1"
        assert remover_numero_inicio("1, 2", 1) == "2"
        assert remover_numero_inicio("1", 1) == ""
        assert remover_numero_inicio("1, 2, 3", 2) == "1, 3"

    def test_obter_proxima_letra_top(self):
        assert obter_proxima_letra_top([]) == "A"
        assert obter_proxima_letra_top(["A"]) == "B"
        assert obter_proxima_letra_top(["A", "B"]) == "C"
        assert obter_proxima_letra_top(["B", "A"]) == "C"
        # Quando todo o alfabeto de A a Z estiver em uso, fallback para 'Z'
        todas_as_letras = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        assert obter_proxima_letra_top(todas_as_letras) == "Z"

    def test_desambiguar_topos_com_referencias_vazias_ou_inexistentes(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)])
        ref_vazia = croqui_pb2.Mapa.Referencia(alvo_uid="Vazia")
        ref_inexistente = croqui_pb2.Mapa.Referencia(
            alvo_uid="NaoExiste", pontos_uids=["linha_fantasma"]
        )

        # Não deve lançar exceção
        desambiguar_topos([linha], [ref_vazia, ref_inexistente])

    def test_desambiguar_topos_rota_isolada_sem_circulo(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)], rotulo_inicio="1")
        ref = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["linha_1"])

        desambiguar_topos([linha], [ref])

        assert linha.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert linha.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_variantes_com_topos_distintos(self):
        seg_comum = _criar_linha_pb("comum", [(100, 500), (100, 300)], rotulo_inicio="1, 2")
        seg_v1 = _criar_linha_pb("v1", [(100, 300), (80, 100)])
        seg_v2 = _criar_linha_pb("v2", [(100, 300), (120, 100)])

        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["comum", "v1"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["comum", "v2"])

        desambiguar_topos([seg_comum, seg_v1, seg_v2], [ref1, ref2])

        assert seg_v1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v1.linha.conteudo.nos[-1].rotulo == "A"
        assert seg_v2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v2.linha.conteudo.nos[-1].rotulo == "B"

    def test_desambiguar_topos_convergencia_mesmo_topo(self):
        linha1 = _criar_linha_pb("v1", [(50, 500), (100, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("v2", [(150, 500), (100, 100)], rotulo_inicio="2")

        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["v1"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["v2"])

        desambiguar_topos([linha1, linha2], [ref1, ref2])

        assert linha1.linha.conteudo.nos[-1].rotulo == "A"
        assert linha2.linha.conteudo.nos[-1].rotulo == "A"
        assert linha1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP

    def test_desambiguar_topos_multiplas_rotas_isoladas_sem_letras(self):
        linha1 = _criar_linha_pb("v1", [(50, 500), (50, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("v2", [(150, 500), (150, 100)], rotulo_inicio="2")
        linha3 = _criar_linha_pb("v3", [(250, 500), (250, 100)], rotulo_inicio="3")

        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["v1"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["v2"])
        ref3 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 3", pontos_uids=["v3"])

        desambiguar_topos([linha1, linha2, linha3], [ref1, ref2, ref3])

        for l in (linha1, linha2, linha3):
            assert l.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
            assert l.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_rota_isolada_junto_com_bifurcacao(self):
        seg_comum = _criar_linha_pb("comum", [(100, 500), (100, 300)], rotulo_inicio="1, 2")
        seg_v1 = _criar_linha_pb("v1", [(100, 300), (80, 100)])
        seg_v2 = _criar_linha_pb("v2", [(100, 300), (120, 100)])
        linha_isolada = _criar_linha_pb("isolada", [(300, 500), (300, 100)], rotulo_inicio="3")

        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["comum", "v1"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["comum", "v2"])
        ref3 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 3 Isolada", pontos_uids=["isolada"])

        desambiguar_topos([seg_comum, seg_v1, seg_v2, linha_isolada], [ref1, ref2, ref3])

        # As variantes ganham letras distintas
        assert seg_v1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v1.linha.conteudo.nos[-1].rotulo == "A"
        assert seg_v2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v2.linha.conteudo.nos[-1].rotulo == "B"

        # A rota isolada NÃO ganha letra nem círculo de topo
        assert linha_isolada.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert linha_isolada.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_reversao_restaura_rota_isolada(self):
        # Linha que antes tinha FIM_TOP e rótulo 'A' de quando havia uma variante
        linha = _criar_linha_pb("v1", [(50, 500), (50, 100)], rotulo_inicio="1")
        linha.linha.conteudo.nos[-1].tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        linha.linha.conteudo.nos[-1].rotulo = "A"

        ref = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["v1"])
        desambiguar_topos([linha], [ref])

        assert linha.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert linha.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_sem_referencias_normaliza_fim_top(self):
        linha = _criar_linha_pb("v1", [(50, 500), (50, 100)], rotulo_inicio="1")
        linha.linha.conteudo.nos[-1].tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        linha.linha.conteudo.nos[-1].rotulo = "A"

        desambiguar_topos([linha], [])
        assert linha.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert linha.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_inicio_compartilhado_sem_id_comum(self):
        linha1 = _criar_linha_pb("v1", [(100, 500), (80, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("v2", [(100, 500), (120, 100)], rotulo_inicio="2")
        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["v1"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["v2"])

        desambiguar_topos([linha1, linha2], [ref1, ref2])
        assert linha1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha1.linha.conteudo.nos[-1].rotulo == "A"
        assert linha2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha2.linha.conteudo.nos[-1].rotulo == "B"

    def test_desambiguar_topos_no_intermediario_compartilhado(self):
        linha1 = _criar_linha_pb("v1", [(50, 500), (100, 300), (50, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("v2", [(150, 500), (100, 300), (150, 100)], rotulo_inicio="2")
        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["v1"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["v2"])

        desambiguar_topos([linha1, linha2], [ref1, ref2])
        assert linha1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP

        desambiguar_topos([linha1, linha2], [ref1, ref2])
        assert linha1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP


class TestEscopoSetor:
    def test_obter_rotulo_escalada_no_setor(self):
        setor = croqui_pb2.Setor(nome="Setor Teste")
        esc_outra = setor.escaladas.add(uid="uid_outra")
        esc_outra.boulder.nome = "Outra Via"
        esc_central = setor.escaladas.add(uid="uid_via_central")
        esc_central.boulder.nome = "Via Central"

        m1 = setor.mapas.add()
        l1 = _criar_linha_pb("l1", [(100, 500), (100, 100)], rotulo_inicio="1")
        m1.pontos_de_interesse.append(l1)
        m1.referencias.add(alvo_uid="uid_via_central", pontos_uids=["l1"])

        m2 = setor.mapas.add()

        rotulo_por_uid = obter_rotulo_escalada_no_setor(setor, "uid_via_central")
        assert rotulo_por_uid == "1"

        rotulo_por_nome = obter_rotulo_escalada_no_setor(setor, "Via Central")
        assert rotulo_por_nome == "1"

        rotulo_inexistente = obter_rotulo_escalada_no_setor(setor, "uid_via_fantasma")
        assert rotulo_inexistente is None

    def test_calcular_proximo_numero_inicio_setor(self):
        setor = croqui_pb2.Setor(nome="Setor Teste")
        # Sem mapas
        assert calcular_proximo_numero_inicio_setor(setor) == 1

        # Com mapas e rótulos
        m1 = setor.mapas.add()
        l1 = _criar_linha_pb("l1", [(100, 500), (100, 100)], rotulo_inicio="1, 2")
        m1.pontos_de_interesse.append(l1)

        m2 = setor.mapas.add()
        l2 = _criar_linha_pb("l2", [(200, 500), (200, 100)], rotulo_inicio="4")
        m2.pontos_de_interesse.append(l2)

        # Maior número usado é 4 -> próximo é 5
        assert calcular_proximo_numero_inicio_setor(setor) == 5

    def test_gerar_id_poi_disjunto_setor(self):
        setor = croqui_pb2.Setor(nome="Setor Teste")
        m1 = setor.mapas.add()
        m1.pontos_de_interesse.add(uid="linha_1")
        m1.pontos_de_interesse.add(uid="linha_2")

        m2 = setor.mapas.add()
        m2.pontos_de_interesse.add(uid="linha_3")

        novo_id = gerar_id_poi_disjunto_setor(setor, prefixo="linha")
        assert validar_uid(novo_id)
        assert novo_id not in ["linha_1", "linha_2", "linha_3"]

    def test_desembrulhar_setor_formatos(self):
        from editor.core.topologia_trajeto import desembrulhar_setor
        from editor.models.readonly_proxy import ReadOnlyProxy

        setor = croqui_pb2.Setor(nome="Setor Direto")
        assert desembrulhar_setor(setor) == setor

        arq = croqui_pb2.ArquivoSetor(conteudo=setor)
        assert desembrulhar_setor(arq) == setor

        proxy_setor = ReadOnlyProxy(setor)
        assert desembrulhar_setor(proxy_setor) == setor

        proxy_arq = ReadOnlyProxy(arq)
        assert desembrulhar_setor(proxy_arq) == setor

        sg = croqui_pb2.SetorOuGrupo(setor=arq)
        assert desembrulhar_setor(sg) == setor

        assert desembrulhar_setor(None) is None

    def test_obter_rotulo_escalada_no_setor_invalido_ou_vazio(self):
        assert obter_rotulo_escalada_no_setor(None, "uid_via") is None
        setor_vazio = croqui_pb2.Setor()
        assert obter_rotulo_escalada_no_setor(setor_vazio, "uid_via") is None

    def test_calcular_proximo_numero_inicio_setor_mapa_sem_pontos(self):
        mapa_vazio = croqui_pb2.Mapa()
        assert calcular_proximo_numero_inicio_setor(None, mapa_ativo=mapa_vazio) == 1
        assert calcular_proximo_numero_inicio_setor(None, mapa_ativo="invalido") == 1

    def test_gerar_id_poi_disjunto_setor_com_arquivo_setor(self):
        setor = croqui_pb2.Setor(nome="Setor Interno")
        m = setor.mapas.add()
        m.pontos_de_interesse.add(uid="linha_1")
        arq = croqui_pb2.ArquivoSetor(conteudo=setor)

        novo_id = gerar_id_poi_disjunto_setor(arq, prefixo="linha")
        assert validar_uid(novo_id)
        assert novo_id != "linha_1"

    def test_gerar_id_poi_disjunto_setor_com_mapa_ativo_prioritario(self):
        mapa_ativo = croqui_pb2.Mapa()
        mapa_ativo.pontos_de_interesse.add(uid="linha_1")
        mapa_ativo.pontos_de_interesse.add(uid="sai1")
        mapa_ativo.pontos_de_interesse.add(uid="linha_2")

        # Setor vazio ou None: deve inspecionar mapa_ativo
        novo_id = gerar_id_poi_disjunto_setor(None, prefixo="linha", mapa_ativo=mapa_ativo)
        assert validar_uid(novo_id)
        assert novo_id not in ["linha_1", "sai1", "linha_2"]

    def test_calcular_proximo_numero_inicio_setor_com_arquivo_setor_e_mapa_ativo(self):
        setor = croqui_pb2.Setor(nome="Setor")
        m1 = setor.mapas.add()
        l1 = _criar_linha_pb("l1", [(100, 500), (100, 100)], rotulo_inicio="5")
        m1.pontos_de_interesse.append(l1)
        arq = croqui_pb2.ArquivoSetor(conteudo=setor)

        # Inspeciona através de ArquivoSetor
        assert calcular_proximo_numero_inicio_setor(arq) == 6

        # Com mapa ativo trazendo número maior
        mapa_ativo = croqui_pb2.Mapa()
        l_ativo = _criar_linha_pb("l_at", [(200, 500), (200, 100)], rotulo_inicio="8")
        mapa_ativo.pontos_de_interesse.append(l_ativo)

        assert calcular_proximo_numero_inicio_setor(arq, mapa_ativo=mapa_ativo) == 9

    def test_fatiar_linha_preserva_cor_e_label(self):
        linha = _criar_linha_pb("l_custom", [(0, 0), (50, 50), (100, 100)])
        linha.cor = "#FF0055"
        linha.rotulo = "Super Via"
        sub1, sub2 = fatiar_linha_em_no(linha, 1, "sub1", "sub2")
        assert sub1.cor == "#FF0055"
        assert sub1.rotulo == "Super Via"
        assert sub2.cor == "#FF0055"
        assert sub2.rotulo == "Super Via"

    def test_fatiar_linha_triplo_com_nos_intermediarios(self):
        linha = _criar_linha_pb("l_longa", [(0, 0), (10, 10), (20, 20), (30, 30), (40, 40)])
        sub1, sub2, sub3 = fatiar_linha_triplo(linha, 1, 3, "s1", "s2", "s3")
        assert len(sub2.linha.conteudo.nos) == 3
        assert sub2.linha.conteudo.nos[1].x == 20
        assert sub2.linha.conteudo.nos[1].y == 20


class TestDescobertaCaminhosConfluencia:
    def test_snap_livre_ou_linha_invalida_retorna_vazio(self):
        linha = _criar_linha_pb("l1", [(100, 500), (100, 100)])
        snap_livre = ResultadoSnap(tipo=TipoSnap.LIVRE, coordenada=Ponto2D(50, 50))
        res_livre = descobrir_caminhos_confluencia(snap_livre, [linha], [])
        assert res_livre == ResultadoAnaliseConfluencia(eh_topo_final=False, opcoes=())

        snap_inexistente = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 500), id_linha="inexistente", indice_no=0
        )
        res_inex = descobrir_caminhos_confluencia(snap_inexistente, [linha], [])
        assert res_inex == ResultadoAnaliseConfluencia(eh_topo_final=False, opcoes=())

    def test_snap_em_no_intermediario_de_rota_unica(self):
        linha = _criar_linha_pb(
            "l1", [(100, 500), (100, 350), (100, 200), (100, 100)], rotulo_inicio="1"
        )
        ref = croqui_pb2.Mapa.Referencia(alvo_uid="uid_v1", pontos_uids=["l1"])
        snap = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 350), id_linha="l1", indice_no=1
        )

        res = descobrir_caminhos_confluencia(
            snap, [linha], [ref], nomes_por_uid={"uid_v1": "Fissura Principal"}
        )

        assert res.eh_topo_final is False
        assert len(res.opcoes) == 1
        op = res.opcoes[0]
        assert op.rotulo_exibicao == 'Seguir até o topo de "Fissura Principal"'
        assert op.nomes_escaladas == ("Fissura Principal",)
        assert op.rotulo_topo == ""
        assert op.coordenadas_remanescentes == (
            Ponto2D(100, 350),
            Ponto2D(100, 200),
            Ponto2D(100, 100),
        )
        assert op.id_linha_alvo == "l1"
        assert op.requer_fatiamento is True
        assert op.incluir_segunda_sublinha_fatiada is True
        assert op.uids_subsequentes == ()

    def test_snap_em_ponto_curva_projeta_caminho_remanescente(self):
        linha = _criar_linha_pb("l1", [(100, 500), (100, 300), (100, 100)], rotulo_inicio="1")
        ref = croqui_pb2.Mapa.Referencia(alvo_uid="Via Central", pontos_uids=["l1"])
        snap = ResultadoSnap(
            tipo=TipoSnap.CURVA,
            coordenada=Ponto2D(100, 400),
            id_linha="l1",
            indice_segmento=0,
            fator_t=0.5,
        )

        res = descobrir_caminhos_confluencia(snap, [linha], [ref])

        assert res.eh_topo_final is False
        assert len(res.opcoes) == 1
        op = res.opcoes[0]
        assert op.requer_fatiamento is True
        assert op.incluir_segunda_sublinha_fatiada is True
        assert op.coordenadas_remanescentes == (
            Ponto2D(100, 400),
            Ponto2D(100, 300),
            Ponto2D(100, 100),
        )
        assert op.uids_subsequentes == ()

    def test_multiplas_rotas_divergentes_adiante_gera_opcoes_distintas(self):
        seg_base = _criar_linha_pb(
            "base", [(100, 500), (100, 350), (100, 250)], rotulo_inicio="1, 2"
        )
        seg_topo_a = _criar_linha_pb("topo_a", [(100, 250), (70, 100)], rotulo_fim="A")
        seg_topo_b = _criar_linha_pb("topo_b", [(100, 250), (130, 100)], rotulo_fim="B")
        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via Esquerda", pontos_uids=["base", "topo_a"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via Direita", pontos_uids=["base", "topo_b"])

        snap = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 350), id_linha="base", indice_no=1
        )
        res = descobrir_caminhos_confluencia(snap, [seg_base, seg_topo_a, seg_topo_b], [ref1, ref2])

        assert res.eh_topo_final is False
        assert len(res.opcoes) == 2

        op1, op2 = res.opcoes
        assert op1.rotulo_exibicao == 'Seguir até Topo A via "Via Esquerda"'
        assert op1.rotulo_topo == "A"
        assert op1.uids_subsequentes == ("topo_a",)
        assert op1.coordenadas_remanescentes == (
            Ponto2D(100, 350),
            Ponto2D(100, 250),
            Ponto2D(70, 100),
        )

        assert op2.rotulo_exibicao == 'Seguir até Topo B via "Via Direita"'
        assert op2.rotulo_topo == "B"
        assert op2.uids_subsequentes == ("topo_b",)
        assert op2.coordenadas_remanescentes == (
            Ponto2D(100, 350),
            Ponto2D(100, 250),
            Ponto2D(130, 100),
        )

    def test_deduplicacao_caminhos_remanescentes_identicos(self):
        seg_v1 = _criar_linha_pb("v1", [(60, 500), (100, 350)], rotulo_inicio="1")
        seg_v2 = _criar_linha_pb("v2", [(140, 500), (100, 350)], rotulo_inicio="2")
        seg_comum = _criar_linha_pb("comum", [(100, 350), (100, 200), (100, 100)], rotulo_fim="A")
        ref1 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["v1", "comum"])
        ref2 = croqui_pb2.Mapa.Referencia(alvo_uid="Via 2", pontos_uids=["v2", "comum"])

        snap = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 200), id_linha="comum", indice_no=1
        )
        res = descobrir_caminhos_confluencia(snap, [seg_v1, seg_v2, seg_comum], [ref1, ref2])

        assert len(res.opcoes) == 1
        op = res.opcoes[0]
        assert op.nomes_escaladas == ("Via 1", "Via 2")
        assert op.rotulo_exibicao == 'Seguir até Topo A via "Via 1 / Via 2"'

    def test_juncao_existente_entre_sublinhas_nao_requer_fatiamento(self):
        seg1 = _criar_linha_pb("s1", [(100, 500), (100, 300)], rotulo_inicio="1")
        seg2 = _criar_linha_pb("s2", [(100, 300), (100, 100)], rotulo_fim="A")
        ref = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["s1", "s2"])

        # Caso A: Snap capturou o último nó de s1 (que continua em s2)
        snap_fim_s1 = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 300), id_linha="s1", indice_no=1
        )
        res_a = descobrir_caminhos_confluencia(snap_fim_s1, [seg1, seg2], [ref])
        assert res_a.eh_topo_final is False
        assert len(res_a.opcoes) == 1
        assert res_a.opcoes[0].requer_fatiamento is False
        assert res_a.opcoes[0].incluir_segunda_sublinha_fatiada is False
        assert res_a.opcoes[0].uids_subsequentes == ("s2",)
        assert res_a.opcoes[0].coordenadas_remanescentes == (
            Ponto2D(100, 300),
            Ponto2D(100, 100),
        )

        # Caso B: Snap capturou o primeiro nó (índice 0) de s2
        snap_ini_s2 = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 300), id_linha="s2", indice_no=0
        )
        res_b = descobrir_caminhos_confluencia(snap_ini_s2, [seg1, seg2], [ref])
        assert res_b.eh_topo_final is False
        assert len(res_b.opcoes) == 1
        assert res_b.opcoes[0].requer_fatiamento is False
        assert res_b.opcoes[0].incluir_segunda_sublinha_fatiada is False
        assert res_b.opcoes[0].uids_subsequentes == ("s2",)
        assert res_b.opcoes[0].coordenadas_remanescentes == (
            Ponto2D(100, 300),
            Ponto2D(100, 100),
        )

    def test_snap_no_topo_final_real_sinaliza_eh_topo_final(self):
        seg1 = _criar_linha_pb("s1", [(100, 500), (100, 300)], rotulo_inicio="1")
        seg2 = _criar_linha_pb("s2", [(100, 300), (100, 100)], rotulo_fim="A")
        ref = croqui_pb2.Mapa.Referencia(alvo_uid="Via 1", pontos_uids=["s1", "s2"])

        snap_topo = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 100), id_linha="s2", indice_no=1
        )
        res = descobrir_caminhos_confluencia(snap_topo, [seg1, seg2], [ref])

        assert res.eh_topo_final is True
        assert res.opcoes == ()

    def test_linha_avulsa_sem_referencia_gera_opcao_generica_e_detecta_topo(self):
        linha_avulsa = _criar_linha_pb("avulsa", [(100, 500), (100, 300), (100, 100)])

        snap_meio = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 300), id_linha="avulsa", indice_no=1
        )
        res_meio = descobrir_caminhos_confluencia(snap_meio, [linha_avulsa], [])
        assert res_meio.eh_topo_final is False
        assert len(res_meio.opcoes) == 1
        assert res_meio.opcoes[0].rotulo_exibicao == "Seguir até o fim da linha"
        assert res_meio.opcoes[0].requer_fatiamento is True
        assert res_meio.opcoes[0].coordenadas_remanescentes == (
            Ponto2D(100, 300),
            Ponto2D(100, 100),
        )

        snap_fim = ResultadoSnap(
            tipo=TipoSnap.NO, coordenada=Ponto2D(100, 100), id_linha="avulsa", indice_no=2
        )
        res_fim = descobrir_caminhos_confluencia(snap_fim, [linha_avulsa], [])
        assert res_fim.eh_topo_final is True
        assert res_fim.opcoes == ()
