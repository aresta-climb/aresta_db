# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Sequence

from editor.caos.encolhedor_caminho_crash import EncolhedorCaminhoCrash
from editor.caos.receita_crash_robo import (
    FalhaCapturadaRobo,
    PassoRobo,
    ReceitaCrashRobo,
    SeletorAlvoQt,
)


def _criar_passo(indice: int, acao: str, mutou: bool = True) -> PassoRobo:
    return PassoRobo(
        indice=indice,
        tipo_acao=acao,
        seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor=acao),
        mutou_estado=mutou,
    )


def test_encolhedor_ddmin_reduz_sequencia_longa_para_minima_reproduzivel() -> None:
    passos_originais = tuple(_criar_passo(i, f"acao_{i}", mutou=(i % 4 != 0)) for i in range(1, 21))
    falha_alvo = FalhaCapturadaRobo(
        oraculo="excecao_nao_tratada",
        tipo_excecao="RuntimeError",
        mensagem="Crash combinacao 3 + 11 + 20",
        frame_principal="area_principal.py:500",
    )
    falha_diferente = FalhaCapturadaRobo(
        oraculo="excecao_nao_tratada",
        tipo_excecao="ValueError",
        mensagem="Outro erro irrelevante",
        frame_principal="outro.py:10",
    )

    receita_bruta = ReceitaCrashRobo(
        seed=42,
        dataset="toxico",
        escopo="aplicativo_completo",
        falha=falha_alvo,
        passos_minimos=passos_originais,
        passos_originais=passos_originais,
    )

    def _avaliar(candidato: Sequence[PassoRobo]) -> FalhaCapturadaRobo | None:
        acoes = {p.tipo_acao for p in candidato}
        if "acao_2" in acoes and "acao_3" not in acoes:
            return falha_diferente
        if {"acao_3", "acao_11", "acao_20"}.issubset(acoes):
            return falha_alvo
        return None

    encolhedor = EncolhedorCaminhoCrash(avaliar_candidato=_avaliar, max_tentativas=40)
    receita_encolhida = encolhedor.encolher(receita_bruta)

    acoes_minimas = [p.tipo_acao for p in receita_encolhida.passos_minimos]
    assert acoes_minimas == ["acao_3", "acao_11", "acao_20"]
    assert len(receita_encolhida.passos_originais) == 20


def test_encolhedor_respeita_limite_tentativas_e_receita_unitaria() -> None:
    passo_unico = (_criar_passo(1, "acao_1"),)
    falha = FalhaCapturadaRobo(
        oraculo="excecao_nao_tratada",
        tipo_excecao="RuntimeError",
        mensagem="Erro imediato",
        frame_principal="main.py:1",
    )
    receita_1 = ReceitaCrashRobo(
        seed=7,
        dataset="normal",
        escopo="janela_principal",
        falha=falha,
        passos_minimos=passo_unico,
        passos_originais=passo_unico,
    )

    chamadas = 0

    def _avaliar_nunca_reproduz(candidato: Sequence[PassoRobo]) -> FalhaCapturadaRobo | None:
        nonlocal chamadas
        chamadas += 1
        return None

    encolhedor = EncolhedorCaminhoCrash(avaliar_candidato=_avaliar_nunca_reproduz, max_tentativas=3)
    assert encolhedor.encolher(receita_1) == receita_1
    assert chamadas == 0

    passos_irredutiveis = tuple(_criar_passo(i, f"acao_{i}") for i in range(1, 8))
    receita_8 = ReceitaCrashRobo(
        seed=8,
        dataset="normal",
        escopo="janela_principal",
        falha=falha,
        passos_minimos=passos_irredutiveis,
        passos_originais=passos_irredutiveis,
    )
    resultado = encolhedor.encolher(receita_8)
    assert resultado.passos_minimos == passos_irredutiveis
    assert chamadas == 3
