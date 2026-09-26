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
    ResultadoSnap,
    TipoSnap,
    detectar_snap_nos,
    projetar_ponto_em_segmento,
    detectar_snap_curva,
    calcular_snap,
    fatiar_linha_em_no,
    fatiar_linha_em_ponto_curva,
    fatiar_linha_triplo,
    atualizar_referencias_apos_fatiamento,
    formatar_rotulo_inicio,
    adicionar_numero_inicio,
    remover_numero_inicio,
    obter_proxima_letra_top,
    desambiguar_topos,
    obter_rotulo_escalada_no_setor,
    calcular_proximo_numero_inicio_setor,
    gerar_id_poi_disjunto_setor,
)


def _criar_linha_pb(id_linha: str, pontos: list, rotulo_inicio: str = "", rotulo_fim: str = ""):
    """Função auxiliar para criar um PontoDeInteresse do tipo linha para testes."""
    poi = croqui_pb2.Mapa.PontoDeInteresse(id=id_linha)
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
        poi_circulo = croqui_pb2.Mapa.PontoDeInteresse(id="circ_1")
        poi_circulo.circulo.x = 100
        poi_linha_1_no = _criar_linha_pb("linha_curta", [(50, 50)])

        snap_no = detectar_snap_nos(Ponto2D(100, 100), [poi_circulo], raio_snap=20.0)
        assert snap_no is None

        snap_curva = detectar_snap_curva(Ponto2D(50, 50), [poi_circulo, poi_linha_1_no], raio_snap=20.0)
        assert snap_curva is None

    def test_calcular_snap_sem_convergencia_retorna_livre(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)])
        snap = calcular_snap(Ponto2D(500, 500), [linha], raio_snap=15.0)
        assert snap.tipo == TipoSnap.LIVRE
        assert snap.coordenada == Ponto2D(500, 500)


class TestFatiamentoTrajeto:
    def test_fatiar_linha_em_no_existente(self):
        linha = _criar_linha_pb("linha_original", [(100, 500), (120, 350), (140, 200), (150, 100)], rotulo_inicio="1")
        
        sub1, sub2 = fatiar_linha_em_no(linha, indice_no=2, id_sub1="seg_1", id_sub2="seg_2")
        
        # Sub1: nós 0..2
        nos1 = sub1.linha.conteudo.nos
        assert len(nos1) == 3
        assert (nos1[0].x, nos1[0].y) == (100, 500)
        assert (nos1[2].x, nos1[2].y) == (140, 200)
        assert sub1.id == "seg_1"
        assert nos1[0].rotulo == "1"

        # Sub2: nós 2..3
        nos2 = sub2.linha.conteudo.nos
        assert len(nos2) == 2
        assert (nos2[0].x, nos2[0].y) == (140, 200)
        assert (nos2[1].x, nos2[1].y) == (150, 100)
        assert sub2.id == "seg_2"

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
        sub1, sub2 = fatiar_linha_em_no(linha, indice_no=1, id_sub1="s1", id_sub2="s2", preservar_tipo_no_corte=True)
        assert sub1.linha.conteudo.nos[1].tipo == croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA
        assert sub1.linha.conteudo.nos[1].rotulo == "P1"
        assert sub2.linha.conteudo.nos[0].tipo == croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA
        assert sub2.linha.conteudo.nos[0].rotulo == "P1"

    def test_fatiar_linha_em_ponto_curva_insere_no_de_corte(self):
        linha = _criar_linha_pb("linha_original", [(100, 500), (100, 300), (100, 100)], rotulo_inicio="1")
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
            linha, indice_entrada=1, indice_saida=2,
            id_sub1="ini", id_sub2="meio", id_sub3="fim"
        )
        assert len(sub_inicio.linha.conteudo.nos) == 2  # 0..1
        assert len(sub_meio.linha.conteudo.nos) == 2    # 1..2
        assert len(sub_fim.linha.conteudo.nos) == 2     # 2..3
        assert (sub_meio.linha.conteudo.nos[0].x, sub_meio.linha.conteudo.nos[0].y) == (100, 400)
        assert (sub_meio.linha.conteudo.nos[1].x, sub_meio.linha.conteudo.nos[1].y) == (100, 300)

    def test_fatiar_linha_triplo_indices_invalidos_levanta_erro(self):
        linha = _criar_linha_pb("linha_base", [(100, 500), (100, 400), (100, 300), (100, 200)])
        # Entrada maior que saída
        with pytest.raises(ValueError):
            fatiar_linha_triplo(linha, indice_entrada=2, indice_saida=1, id_sub1="a", id_sub2="b", id_sub3="c")
        # Índices negativos
        with pytest.raises(ValueError):
            fatiar_linha_triplo(linha, indice_entrada=-1, indice_saida=2, id_sub1="a", id_sub2="b", id_sub3="c")
        # Entrada igual a saída (mesmo nó)
        with pytest.raises(ValueError):
            fatiar_linha_triplo(linha, indice_entrada=1, indice_saida=1, id_sub1="a", id_sub2="b", id_sub3="c")
        # Entrada no índice 0 (não intermediário, sub1 ficaria com 1 nó)
        with pytest.raises(ValueError):
            fatiar_linha_triplo(linha, indice_entrada=0, indice_saida=2, id_sub1="a", id_sub2="b", id_sub3="c")
        # Saída no último nó (não intermediário, sub3 ficaria com 1 nó)
        with pytest.raises(ValueError):
            fatiar_linha_triplo(linha, indice_entrada=1, indice_saida=3, id_sub1="a", id_sub2="b", id_sub3="c")
        # Linha com menos de 4 nós
        linha_curta = _criar_linha_pb("curta", [(100, 500), (100, 400), (100, 300)])
        with pytest.raises(ValueError):
            fatiar_linha_triplo(linha_curta, indice_entrada=1, indice_saida=2, id_sub1="a", id_sub2="b", id_sub3="c")

    def test_atualizar_referencias_apos_fatiamento(self):
        mapa = croqui_pb2.Mapa()
        ref1 = mapa.referencias.add(escalada="Via 1", ids=["linha_outra", "linha_velha", "linha_fim"])
        ref2 = mapa.referencias.add(escalada="Via 2", ids=["linha_velha"])
        
        atualizar_referencias_apos_fatiamento(mapa.referencias, "linha_velha", ["seg_1", "seg_2"])
        
        assert list(ref1.ids) == ["linha_outra", "seg_1", "seg_2", "linha_fim"]
        assert list(ref2.ids) == ["seg_1", "seg_2"]


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
        linha_sem_nos = croqui_pb2.Mapa.PontoDeInteresse(id="linha_vazia")
        linha_sem_nos.linha.estilo = croqui_pb2.LinhaTrajeto.EstiloTraco.TRACEJADO
        ref_vazia = croqui_pb2.Mapa.Referencia(escalada="Vazia")
        ref_inexistente = croqui_pb2.Mapa.Referencia(escalada="NaoExiste", ids=["linha_fantasma"])
        ref_linha_sem_nos = croqui_pb2.Mapa.Referencia(escalada="SemNos", ids=["linha_vazia"])

        # Não deve lançar exceção
        desambiguar_topos([linha, linha_sem_nos], [ref_vazia, ref_inexistente, ref_linha_sem_nos])

    def test_desambiguar_topos_rota_isolada_sem_circulo(self):
        linha = _criar_linha_pb("linha_1", [(100, 500), (100, 100)], rotulo_inicio="1")
        ref = croqui_pb2.Mapa.Referencia(escalada="Via 1", ids=["linha_1"])
        
        desambiguar_topos([linha], [ref])
        
        assert linha.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert linha.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_variantes_com_topos_distintos(self):
        seg_comum = _criar_linha_pb("comum", [(100, 500), (100, 300)], rotulo_inicio="1, 2")
        seg_v1 = _criar_linha_pb("v1", [(100, 300), (80, 100)])
        seg_v2 = _criar_linha_pb("v2", [(100, 300), (120, 100)])

        ref1 = croqui_pb2.Mapa.Referencia(escalada="Via 1", ids=["comum", "v1"])
        ref2 = croqui_pb2.Mapa.Referencia(escalada="Via 2", ids=["comum", "v2"])

        desambiguar_topos([seg_comum, seg_v1, seg_v2], [ref1, ref2])

        assert seg_v1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v1.linha.conteudo.nos[-1].rotulo == "A"
        assert seg_v2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v2.linha.conteudo.nos[-1].rotulo == "B"

    def test_desambiguar_topos_convergencia_mesmo_topo(self):
        linha1 = _criar_linha_pb("v1", [(50, 500), (100, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("v2", [(150, 500), (100, 100)], rotulo_inicio="2")

        ref1 = croqui_pb2.Mapa.Referencia(escalada="Via 1", ids=["v1"])
        ref2 = croqui_pb2.Mapa.Referencia(escalada="Via 2", ids=["v2"])

        desambiguar_topos([linha1, linha2], [ref1, ref2])

        assert linha1.linha.conteudo.nos[-1].rotulo == "A"
        assert linha2.linha.conteudo.nos[-1].rotulo == "A"
        assert linha1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP

    def test_desambiguar_topos_multiplas_rotas_isoladas_sem_circulo(self):
        linha1 = _criar_linha_pb("v1", [(50, 500), (50, 100)], rotulo_inicio="1")
        linha2 = _criar_linha_pb("v2", [(150, 500), (150, 100)], rotulo_inicio="2")
        linha3 = _criar_linha_pb("v3", [(250, 500), (250, 100)], rotulo_inicio="3")

        ref1 = croqui_pb2.Mapa.Referencia(escalada="Via 1", ids=["v1"])
        ref2 = croqui_pb2.Mapa.Referencia(escalada="Via 2", ids=["v2"])
        ref3 = croqui_pb2.Mapa.Referencia(escalada="Via 3", ids=["v3"])

        desambiguar_topos([linha1, linha2, linha3], [ref1, ref2, ref3])

        for l in [linha1, linha2, linha3]:
            assert l.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
            assert l.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_cenario_misto_isolada_variante_convergente(self):
        # 1 e 2: bifurcação
        seg_comum = _criar_linha_pb("comum", [(100, 500), (100, 300)], rotulo_inicio="1, 2")
        seg_v1 = _criar_linha_pb("v1", [(100, 300), (80, 100)])
        seg_v2 = _criar_linha_pb("v2", [(100, 300), (120, 100)])
        ref1 = croqui_pb2.Mapa.Referencia(escalada="Via 1", ids=["comum", "v1"])
        ref2 = croqui_pb2.Mapa.Referencia(escalada="Via 2", ids=["comum", "v2"])

        # 3 e 4: convergência no mesmo topo (250, 100)
        linha3 = _criar_linha_pb("v3", [(200, 500), (250, 100)], rotulo_inicio="3")
        linha4 = _criar_linha_pb("v4", [(300, 500), (250, 100)], rotulo_inicio="4")
        ref3 = croqui_pb2.Mapa.Referencia(escalada="Via 3", ids=["v3"])
        ref4 = croqui_pb2.Mapa.Referencia(escalada="Via 4", ids=["v4"])

        # 5: rota isolada
        linha5 = _criar_linha_pb("v5", [(400, 500), (400, 100)], rotulo_inicio="5")
        ref5 = croqui_pb2.Mapa.Referencia(escalada="Via 5", ids=["v5"])

        desambiguar_topos(
            [seg_comum, seg_v1, seg_v2, linha3, linha4, linha5],
            [ref1, ref2, ref3, ref4, ref5]
        )

        # Variantes ganham A e B
        assert seg_v1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v1.linha.conteudo.nos[-1].rotulo == "A"
        assert seg_v2.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert seg_v2.linha.conteudo.nos[-1].rotulo == "B"

        # Convergência ganha C compartilhado
        assert linha3.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha3.linha.conteudo.nos[-1].rotulo == "C"
        assert linha4.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        assert linha4.linha.conteudo.nos[-1].rotulo == "C"

        # Rota isolada permanece PASSAGEM e sem rótulo
        assert linha5.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert linha5.linha.conteudo.nos[-1].rotulo == ""

    def test_desambiguar_topos_restauracao_apos_remocao_de_variante(self):
        seg_comum = _criar_linha_pb("comum", [(100, 500), (100, 300)], rotulo_inicio="1")
        seg_v1 = _criar_linha_pb("v1", [(100, 300), (80, 100)], rotulo_fim="A")

        ref1 = croqui_pb2.Mapa.Referencia(escalada="Via 1", ids=["comum", "v1"])

        # Via 1 agora é a única referência
        desambiguar_topos([seg_comum, seg_v1], [ref1])

        # O topo "A" deve ser revertido para PASSAGEM sem rótulo
        assert seg_v1.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
        assert seg_v1.linha.conteudo.nos[-1].rotulo == ""



class TestEscopoSetor:
    def test_obter_rotulo_escalada_no_setor(self):
        setor = croqui_pb2.Setor(nome="Setor Teste")
        m1 = setor.mapas.add()
        l1 = _criar_linha_pb("l1", [(100, 500), (100, 100)], rotulo_inicio="1")
        m1.pontos_de_interesse.append(l1)
        m1.referencias.add(escalada="Via Central", ids=["l1"])

        m2 = setor.mapas.add()

        rotulo = obter_rotulo_escalada_no_setor(setor, "Via Central")
        assert rotulo == "1"

        rotulo_inexistente = obter_rotulo_escalada_no_setor(setor, "Via Fantasma")
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
        m1.pontos_de_interesse.add(id="linha_1")
        m1.pontos_de_interesse.add(id="linha_2")

        m2 = setor.mapas.add()
        m2.pontos_de_interesse.add(id="linha_3")

        novo_id = gerar_id_poi_disjunto_setor(setor, prefixo="linha")
        assert novo_id == "linha_4"
        assert novo_id not in ["linha_1", "linha_2", "linha_3"]

    def test_fatiar_linha_preserva_cor_e_label(self):
        linha = _criar_linha_pb("l_custom", [(0, 0), (50, 50), (100, 100)])
        linha.cor = "#FF0055"
        linha.label = "Super Via"
        sub1, sub2 = fatiar_linha_em_no(linha, 1, "sub1", "sub2")
        assert sub1.cor == "#FF0055"
        assert sub1.label == "Super Via"
        assert sub2.cor == "#FF0055"
        assert sub2.label == "Super Via"

    def test_fatiar_linha_triplo_com_nos_intermediarios(self):
        linha = _criar_linha_pb("l_longa", [(0, 0), (10, 10), (20, 20), (30, 30), (40, 40)])
        sub1, sub2, sub3 = fatiar_linha_triplo(linha, 1, 3, "s1", "s2", "s3")
        assert len(sub2.linha.conteudo.nos) == 3
        assert sub2.linha.conteudo.nos[1].x == 20
        assert sub2.linha.conteudo.nos[1].y == 20
