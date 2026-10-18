# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca de Fake determinístico em memória para ClienteCloudflareD1.

Permite testes de alta fidelidade sem mocks, utilizando SQLite em memória
para emular com exatidão as tabelas, índices e queries do Cloudflare D1.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from serving.sincronizar_d1_lib import ClienteCloudflareD1


class ClienteCloudflareD1Fake(ClienteCloudflareD1):
    """Fake determinístico em memória do cliente Cloudflare D1."""

    def __init__(self, simular_erro: Exception | None = None) -> None:
        super().__init__(
            account_id="fake-account-id",
            database_id="fake-database-id",
            api_token="fake-api-token",
        )
        self.conexao = sqlite3.connect(":memory:")
        self.conexao.row_factory = sqlite3.Row
        self.historico_queries: list[tuple[str, list[Any]]] = []
        self.simular_erro = simular_erro

    def executar_query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Executa a instrução SQL no banco SQLite em memória simulando o D1."""
        if self.simular_erro is not None:
            raise self.simular_erro

        parametros = list(params) if params is not None else []
        self.historico_queries.append((sql, parametros))

        cursor = self.conexao.cursor()
        cursor.execute(sql, parametros)

        if cursor.description:
            linhas = [dict(linha) for linha in cursor.fetchall()]
            return linhas

        self.conexao.commit()
        return []
