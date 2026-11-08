# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Callable, Sequence

from editor.caos.receita_crash_robo import (
    FalhaCapturadaRobo,
    PassoRobo,
    ReceitaCrashRobo,
)


def _particionar_lista(itens: list[PassoRobo], num_particoes: int) -> list[tuple[int, int]]:
    n = len(itens)
    particoes: list[tuple[int, int]] = []
    for i in range(num_particoes):
        inicio = (i * n) // num_particoes
        fim = ((i + 1) * n) // num_particoes
        if fim > inicio:
            particoes.append((inicio, fim))
    return particoes


class EncolhedorCaminhoCrash:
    """
    Implementa o algoritmo Delta Debugging (ddmin) por busca binária para encontrar
    a menor sub-sequência de PassoRobo que reproduz a mesma assinatura de falha.
    """

    def __init__(
        self,
        avaliar_candidato: Callable[[Sequence[PassoRobo]], FalhaCapturadaRobo | None],
        max_tentativas: int = 25,
    ) -> None:
        self._avaliar_candidato = avaliar_candidato
        self._max_tentativas = max_tentativas

    def encolher(self, receita: ReceitaCrashRobo) -> ReceitaCrashRobo:
        melhor = list(receita.passos_minimos)
        if len(melhor) <= 1:
            return receita

        assinatura_alvo = receita.assinatura_deduplicacao()
        tentativas = 0

        def _reproduz_mesma_falha(candidato: list[PassoRobo]) -> bool:
            nonlocal tentativas
            tentativas += 1
            falha_obtida = self._avaliar_candidato(candidato)
            return (
                falha_obtida is not None
                and falha_obtida.assinatura_deduplicacao() == assinatura_alvo
            )

        # 1. Poda rápida de passos que não mutaram estado (preservando sempre o último passo gatilho)
        sem_noops = [p for p in melhor[:-1] if p.mutou_estado] + [melhor[-1]]
        if len(sem_noops) < len(melhor) and tentativas < self._max_tentativas:
            if _reproduz_mesma_falha(sem_noops):
                melhor = sem_noops

        # 2. Delta Debugging (ddmin) sobre o prefixo anterior ao passo gatilho final
        prefixo = melhor[:-1]
        gatilho = melhor[-1]
        num_particoes = 2

        while len(prefixo) >= 1 and tentativas < self._max_tentativas:
            particoes = _particionar_lista(prefixo, min(num_particoes, len(prefixo)))
            reduziu_nesta_rodada = False

            for inicio, fim in reversed(particoes):
                if tentativas >= self._max_tentativas:
                    break
                complemento_prefixo = prefixo[:inicio] + prefixo[fim:]
                candidato = [*complemento_prefixo, gatilho]
                if _reproduz_mesma_falha(candidato):
                    prefixo = complemento_prefixo
                    num_particoes = max(num_particoes - 1, 2)
                    reduziu_nesta_rodada = True
                    break

            if not reduziu_nesta_rodada:
                if num_particoes >= len(prefixo):
                    break
                num_particoes = min(len(prefixo), num_particoes * 2)

        melhor_final = (*prefixo, gatilho)
        return ReceitaCrashRobo(
            seed=receita.seed,
            dataset=receita.dataset,
            escopo=receita.escopo,
            falha=receita.falha,
            passos_minimos=melhor_final,
            passos_originais=receita.passos_originais,
        )
