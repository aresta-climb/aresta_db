# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca test-only de Fake determinístico em memória para `InterfaceClienteGhIntegrador`.
"""

from __future__ import annotations

from serving.integrador_pr_lib import (
    CheckPullRequest,
    ErroClienteGhIntegrador,
    EstadoMergePullRequest,
    InfoPullRequest,
)


class ClienteGhIntegradorFake:
    """Fake determinístico em memória que cumpre `InterfaceClienteGhIntegrador`."""

    def __init__(self, erro_simulado: str | None = None) -> None:
        self._erro_simulado = erro_simulado
        self._infos_pr: dict[int, InfoPullRequest] = {}
        self._filas_checks: dict[int, list[list[CheckPullRequest]]] = {}
        self._ids_bots: dict[str, str] = {}
        self._filas_estados_merge: dict[int, list[EstadoMergePullRequest]] = {}
        self._filas_resultados_merge: dict[int, list[bool]] = {}
        self.merges_solicitados: list[int] = []

    def registrar_info_pr(self, info: InfoPullRequest) -> None:
        """Registra metadados de uma Pull Request em memória."""
        self._infos_pr[info.numero] = info

    def registrar_sequencia_checks(
        self,
        numero_pr: int,
        sequencia: list[list[CheckPullRequest]],
    ) -> None:
        """Registra uma sequência de snapshots de checks para simular evolução de polling."""
        self._filas_checks[numero_pr] = [list(s) for s in sequencia]

    def registrar_id_bot(self, nome_bot: str, id_bot: str) -> None:
        """Registra o ID numérico de um usuário bot do GitHub."""
        self._ids_bots[nome_bot] = id_bot

    def registrar_sequencia_estados_merge(
        self,
        numero_pr: int,
        sequencia: list[EstadoMergePullRequest],
    ) -> None:
        """Registra uma sequência de estados de mergeabilidade para `numero_pr`."""
        self._filas_estados_merge[numero_pr] = list(sequencia)

    def registrar_sequencia_resultados_merge(
        self,
        numero_pr: int,
        sequencia: list[bool],
    ) -> None:
        """Registra uma sequência de sucessos/falhas para chamadas a `realizar_merge_pr`."""
        self._filas_resultados_merge[numero_pr] = list(sequencia)

    def obter_info_pr(self, numero_pr: int) -> InfoPullRequest:
        """Retorna `InfoPullRequest` registrada ou lança `ErroClienteGhIntegrador`."""
        if self._erro_simulado:
            raise ErroClienteGhIntegrador(self._erro_simulado)
        return self._infos_pr[numero_pr]

    def listar_checks_pr(self, numero_pr: int) -> list[CheckPullRequest]:
        """Consome o próximo snapshot de checks da fila (mantendo o último quando esgotar)."""
        fila = self._filas_checks.get(numero_pr)
        if not fila:
            return []
        if len(fila) > 1:
            return list(fila.pop(0))
        return list(fila[0])

    def obter_id_usuario_bot(self, nome_bot: str) -> str:
        """Retorna o ID numérico registrado para `nome_bot` ou string vazia."""
        return self._ids_bots.get(nome_bot, "")

    def obter_estado_merge_pr(self, numero_pr: int) -> EstadoMergePullRequest:
        """Consome o próximo estado de mergeabilidade da fila (padrão MERGEABLE/CLEAN)."""
        fila = self._filas_estados_merge.get(numero_pr)
        if not fila:
            return EstadoMergePullRequest(mergeable="MERGEABLE", merge_state_status="CLEAN")
        if len(fila) > 1:
            return fila.pop(0)
        return fila[0]

    def realizar_merge_pr(self, numero_pr: int) -> bool:
        """Registra a tentativa de merge e retorna o próximo resultado configurado (padrão True)."""
        self.merges_solicitados.append(numero_pr)
        fila = self._filas_resultados_merge.get(numero_pr)
        if not fila:
            return True
        if len(fila) > 1:
            return fila.pop(0)
        return fila[0]
