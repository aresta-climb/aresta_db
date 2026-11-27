# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes para a biblioteca test-only `ClienteGeminiFeedbackFake`, garantindo que o
Fake determinístico cumpre fielmente o contrato `InterfaceClienteGeminiFeedback`.
"""

from __future__ import annotations

from typing import Any

import pytest

from serving.agente_feedback.cliente_gemini_feedback import (
    NOME_FERRAMENTA_FINALIZAR,
    ChamadaFerramentaAgente,
    ErroComunicacaoGemini,
)
from serving.agente_feedback.cliente_gemini_feedback_fake import ClienteGeminiFeedbackFake


def test_fake_executa_fila_de_turnos_e_repete_ultimo_quando_esgotado() -> None:
    t1 = [ChamadaFerramentaAgente("aresta_obter_arvore", {"alvo": ""})]
    t2 = [
        ChamadaFerramentaAgente(
            NOME_FERRAMENTA_FINALIZAR,
            {"acao": "nao_acionavel", "motivo": "Vago"},
        )
    ]
    fake = ClienteGeminiFeedbackFake(turnos_programados=[t1, t2])

    r1 = fake.executar_turno_agente([{"role": "user", "parts": []}], [])
    r2 = fake.executar_turno_agente([{"role": "user", "parts": []}], [])
    r3 = fake.executar_turno_agente([{"role": "user", "parts": []}], [])

    assert r1.chamadas == t1
    assert r2.chamadas == t2
    assert r3.chamadas == t2
    assert len(fake.chamadas_turnos) == 3


def test_fake_suporta_roteiro_dinamico_e_erro_simulado() -> None:
    def roteiro(
        historico: list[dict[str, Any]], indice_turno: int
    ) -> list[ChamadaFerramentaAgente]:
        return [
            ChamadaFerramentaAgente(
                NOME_FERRAMENTA_FINALIZAR,
                {"acao": "abrir_pr", "titulo_pr": f"t-{indice_turno}-{len(historico)}"},
            )
        ]

    fake_din = ClienteGeminiFeedbackFake(roteiro_dinamico=roteiro)
    resp = fake_din.executar_turno_agente([{"role": "user", "parts": []}], [])
    assert resp.chamadas[0].argumentos["titulo_pr"] == "t-0-1"

    fake_erro = ClienteGeminiFeedbackFake(erro_simulado="HTTP 429: RESOURCE_EXHAUSTED")
    with pytest.raises(ErroComunicacaoGemini, match="RESOURCE_EXHAUSTED"):
        fake_erro.executar_turno_agente([], [])
