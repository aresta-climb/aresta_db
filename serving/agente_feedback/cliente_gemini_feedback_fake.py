# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca test-only de Fake determinístico em memória para `ClienteGeminiFeedback`,
suportando filas de turnos de Function Calling, roteiros dinâmicos baseados nas
respostas do Editor Headless e simulação determinística de erros de rede/cota.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from serving.agente_feedback.cliente_gemini_feedback import (
    ChamadaFerramentaAgente,
    ErroComunicacaoGemini,
    RespostaTurnoGemini,
)


class ClienteGeminiFeedbackFake:
    """Fake determinístico em memória que cumpre `InterfaceClienteGeminiFeedback`."""

    def __init__(
        self,
        turnos_programados: list[list[ChamadaFerramentaAgente]] | None = None,
        roteiro_dinamico: Callable[[list[dict[str, Any]], int], list[ChamadaFerramentaAgente]]
        | None = None,
        erro_simulado: str | None = None,
    ) -> None:
        self._turnos = [list(t) for t in (turnos_programados or [])]
        self._roteiro_dinamico = roteiro_dinamico
        self._erro_simulado = erro_simulado
        self.chamadas_turnos: list[list[dict[str, Any]]] = []

    def executar_turno_agente(
        self,
        historico_contents: list[dict[str, Any]],
        declaracoes_ferramentas: list[dict[str, Any]],
    ) -> RespostaTurnoGemini:
        """Registra o snapshot do histórico recebido e devolve as chamadas programadas do turno."""
        _ = declaracoes_ferramentas
        indice_turno = len(self.chamadas_turnos)
        copia_historico = copy.deepcopy(historico_contents)
        self.chamadas_turnos.append(copia_historico)

        if self._erro_simulado:
            raise ErroComunicacaoGemini(self._erro_simulado)

        if self._roteiro_dinamico is not None:
            chamadas = list(self._roteiro_dinamico(copia_historico, indice_turno))
        elif len(self._turnos) > 1:
            chamadas = self._turnos.pop(0)
        else:
            chamadas = list(self._turnos[0])

        partes_modelo = [
            {"functionCall": {"name": c.nome, "args": dict(c.argumentos)}} for c in chamadas
        ]
        return RespostaTurnoGemini(
            chamadas=chamadas,
            conteudo_modelo_bruto={"role": "model", "parts": partes_modelo},
        )
