# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca test-only de Fake determinístico em memória para `ClienteGeminiFeedback`.
Permite simular desambiguação de arquivos, sequências de propostas (incluindo autoretry)
e falhas determinísticas de comunicação/cota sem acesso à rede externa.
"""

from __future__ import annotations

from typing import Any

from serving.agente_feedback.cliente_gemini_feedback import (
    ErroComunicacaoGemini,
    RespostaPropostaGemini,
)
from serving.agente_feedback.renderizador_regua_mapa import MapaAnotadoEmMemoria


class ClienteGeminiFeedbackFake:
    """Fake determinístico em memória que cumpre `InterfaceClienteGeminiFeedback`."""

    def __init__(
        self,
        arquivos_desambiguados: list[str] | None = None,
        respostas_proposta: list[RespostaPropostaGemini] | None = None,
        erro_simulado: str | None = None,
    ) -> None:
        self._arquivos_desambiguados = list(arquivos_desambiguados or [])
        self._respostas_proposta = list(respostas_proposta or [])
        self._erro_simulado = erro_simulado
        self.chamadas_desambiguacao: list[dict[str, Any]] = []
        self.chamadas_proposta: list[dict[str, Any]] = []

    def desambiguar_arquivos_croqui(
        self,
        indice_compacto: str,
        descricao_feedback: str,
        instrucao_extra: str = "",
        screenshot_bytes: bytes | None = None,
        screenshot_mime: str = "image/webp",
    ) -> list[str]:
        """Registra a chamada e retorna a lista determinística de arquivos desambiguados."""
        self.chamadas_desambiguacao.append(
            {
                "indice_compacto": indice_compacto,
                "descricao_feedback": descricao_feedback,
                "instrucao_extra": instrucao_extra,
                "screenshot_bytes": screenshot_bytes,
                "screenshot_mime": screenshot_mime,
            }
        )
        if self._erro_simulado:
            raise ErroComunicacaoGemini(self._erro_simulado)
        return list(self._arquivos_desambiguados)

    def gerar_proposta_alteracao(
        self,
        croqui_id: str,
        descricao_feedback: str,
        instrucao_extra: str,
        arquivos_atuais: dict[str, str],
        screenshot_bytes: bytes | None = None,
        screenshot_mime: str = "image/webp",
        mapas_anotados: list[MapaAnotadoEmMemoria] | None = None,
        erro_validacao_anterior: str = "",
    ) -> RespostaPropostaGemini:
        """Registra a chamada e retorna a próxima `RespostaPropostaGemini` configurada."""
        self.chamadas_proposta.append(
            {
                "croqui_id": croqui_id,
                "descricao_feedback": descricao_feedback,
                "instrucao_extra": instrucao_extra,
                "arquivos_atuais": dict(arquivos_atuais),
                "screenshot_bytes": screenshot_bytes,
                "screenshot_mime": screenshot_mime,
                "mapas_anotados": list(mapas_anotados or []),
                "erro_validacao_anterior": erro_validacao_anterior,
            }
        )
        if self._erro_simulado:
            raise ErroComunicacaoGemini(self._erro_simulado)
        if len(self._respostas_proposta) > 1:
            return self._respostas_proposta.pop(0)
        return self._respostas_proposta[0]
