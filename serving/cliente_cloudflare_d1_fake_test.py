# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para serving/cliente_cloudflare_d1_fake.py."""

from __future__ import annotations

import pytest

from serving.cliente_cloudflare_d1_fake import ClienteCloudflareD1Fake


def test_fake_executar_query_ddl_e_dml() -> None:
    fake = ClienteCloudflareD1Fake()

    fake.executar_query("CREATE TABLE teste (id INTEGER PRIMARY KEY, valor TEXT)")
    fake.executar_query("INSERT INTO teste (id, valor) VALUES (?, ?)", [1, "alpha"])
    fake.executar_query("INSERT INTO teste (id, valor) VALUES (?, ?)", [2, "beta"])

    linhas = fake.executar_query("SELECT id, valor FROM teste ORDER BY id")
    assert linhas == [
        {"id": 1, "valor": "alpha"},
        {"id": 2, "valor": "beta"},
    ]
    assert len(fake.historico_queries) == 4


def test_fake_executar_query_simular_erro() -> None:
    erro_esperado = RuntimeError("Erro simulado no D1")
    fake = ClienteCloudflareD1Fake(simular_erro=erro_esperado)

    with pytest.raises(RuntimeError, match="Erro simulado no D1"):
        fake.executar_query("SELECT 1")
