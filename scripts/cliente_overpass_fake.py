# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca de Fake determinístico em memória para ClienteOverpass.

Permite testar a extração e o cálculo de malha rodoviária OSM e a geração
incremental do catálogo SQLite sem realizar requisições HTTP externas.
"""

from __future__ import annotations

from typing import Any

from scripts.gerar_malha_estrada_lib import ClienteOverpass


class ClienteOverpassFake(ClienteOverpass):
    """Fake determinístico em memória para consultas à Overpass API."""

    def __init__(
        self,
        elementos_padrao: list[dict[str, Any]] | None = None,
        simular_erro: Exception | None = None,
    ) -> None:
        super().__init__(url_endpoint="https://overpass.fake/api/interpreter")
        self.elementos_padrao: list[dict[str, Any]] = (
            list(elementos_padrao) if elementos_padrao is not None else []
        )
        self.respostas_por_coordenada: dict[tuple[int, int], list[dict[str, Any]]] = {}
        self.historico_consultas: list[tuple[float, float]] = []
        self.simular_erro = simular_erro

    def registrar_resposta(
        self,
        latitude: float,
        longitude: float,
        elementos: list[dict[str, Any]],
    ) -> None:
        """Registra uma lista específica de elementos OSM para o par (latitude, longitude)."""
        chave = (int(round(latitude * 1e7)), int(round(longitude * 1e7)))
        self.respostas_por_coordenada[chave] = list(elementos)

    def consultar_malha(
        self,
        latitude: float,
        longitude: float,
        *,
        ao_progresso: Any = None,
        verificador_cancelamento: Any = None,
    ) -> list[dict[str, Any]]:
        """Retorna os elementos pré-configurados em memória ou levanta o erro simulado."""
        if self.simular_erro is not None:
            raise self.simular_erro

        self.historico_consultas.append((latitude, longitude))
        chave = (int(round(latitude * 1e7)), int(round(longitude * 1e7)))
        if chave in self.respostas_por_coordenada:
            return list(self.respostas_por_coordenada[chave])
        return list(self.elementos_padrao)
