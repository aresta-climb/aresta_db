# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para serving/sincronizar_d1_lib.py."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.gerar_catalogo_sqlite_lib import (
    calcular_versao_catalogo,
    inicializar_banco_catalogo,
    inserir_croqui_no_catalogo,
)
from serving.sincronizar_d1_lib import (
    ClienteCloudflareD1,
    aplicar_upserts_e_deletes_d1,
    inicializar_schema_d1,
    obter_ultima_versao_d1,
    sincronizar_catalogo_d1,
)


def _criar_catalogo_teste(
    caminho: Path,
    croquis_com_vias: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> str:
    conexao = inicializar_banco_catalogo(caminho)
    with conexao:
        for croqui, vias in croquis_com_vias:
            dados_croqui = dict(croqui)
            dados_croqui.setdefault("atualizado_em", 100)
            inserir_croqui_no_catalogo(conexao, dados_croqui, vias)
        versao = calcular_versao_catalogo(conexao)
    conexao.close()
    return versao


def test_cliente_d1_a_partir_do_ambiente_sucesso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc-123")
    monkeypatch.setenv("CLOUDFLARE_CATALOGO_D1_DATABASE_ID", "db-456")
    monkeypatch.setenv("CLOUDFLARE_CATALOGO_D1_API_TOKEN", "tok-789")

    cliente = ClienteCloudflareD1.a_partir_do_ambiente()
    assert cliente.account_id == "acc-123"
    assert cliente.database_id == "db-456"
    assert cliente.api_token == "tok-789"


def test_cliente_d1_a_partir_do_ambiente_sem_credenciais(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_CATALOGO_D1_DATABASE_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_CATALOGO_D1_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="Credenciais do Cloudflare D1 ausentes"):
        ClienteCloudflareD1.a_partir_do_ambiente()


def test_cliente_d1_executar_query_sucesso() -> None:
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1")
    resposta_falsa = {
        "success": True,
        "result": [{"results": [{"versao_hash": "abcd1234abcd1234"}]}],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resposta_falsa).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        linhas = cliente.executar_query("SELECT versao_hash FROM deltas_catalogo", ["p1"])
        assert linhas == [{"versao_hash": "abcd1234abcd1234"}]

        req = mock_urlopen.call_args[0][0]
        assert (
            req.full_url
            == "https://api.cloudflare.com/client/v4/accounts/acc-1/d1/database/db-1/query"
        )
        assert req.headers["Authorization"] == "Bearer tok-1"
        corpo = json.loads(req.data.decode("utf-8"))
        assert corpo == {
            "sql": "SELECT versao_hash FROM deltas_catalogo",
            "params": ["p1"],
        }


def test_cliente_d1_executar_query_resultado_vazio() -> None:
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1")
    resposta_falsa = {"success": True, "result": []}

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resposta_falsa).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        assert cliente.executar_query("DELETE FROM catalogo_croquis") == []


def test_cliente_d1_executar_query_erro_api() -> None:
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1")
    resposta_falsa = {
        "success": False,
        "errors": [{"message": "syntax error near SELECT"}],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resposta_falsa).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with pytest.raises(RuntimeError, match="Falha na query do Cloudflare D1"):
            cliente.executar_query("SELECT *")


def test_cliente_d1_executar_query_erro_http() -> None:
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1")

    with patch("urllib.request.urlopen") as mock_urlopen:
        erro_http = urllib.error.HTTPError(
            url="https://api.cloudflare.com",
            code=401,
            msg="Unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b'{"errors":[{"message":"Invalid token"}]}'),
        )
        mock_urlopen.side_effect = erro_http

        with pytest.raises(RuntimeError, match="Erro HTTP 401 no Cloudflare D1"):
            cliente.executar_query("SELECT 1")


def test_inicializar_schema_e_obter_ultima_versao() -> None:
    cliente = MagicMock(spec=ClienteCloudflareD1)
    inicializar_schema_d1(cliente)
    assert cliente.executar_query.call_count == 4

    cliente.executar_query.return_value = []
    assert obter_ultima_versao_d1(cliente) is None

    cliente.executar_query.return_value = [{"versao_hash": "1122334455667788"}]
    assert obter_ultima_versao_d1(cliente) == "1122334455667788"


def test_aplicar_upserts_e_deletes_d1_em_lotes() -> None:
    cliente = MagicMock(spec=ClienteCloudflareD1)
    deltas = {
        "croquis": {
            "upserts": [
                {
                    "croqui_uid": f"c{i}",
                    "id_slug": f"slug_{i}",
                    "nome": f"Pico {i}",
                    "cidade": "BH",
                    "uf": "MG",
                }
                for i in range(16)
            ],
            "deletes": ["c_del_1", "c_del_2"],
        },
        "vias": {
            "upserts": [
                {
                    "uid": f"v{i}",
                    "croqui_uid": "c0",
                    "nome": f"Via {i}",
                    "grau": "6sup",
                    "tipo": "esportiva",
                    "setor_nome": "Setor",
                    "setor_uid": "s1",
                }
                for i in range(13)
            ],
            "deletes": ["v_del_1"],
        },
    }

    aplicar_upserts_e_deletes_d1(cliente, deltas)

    # 1 lote delete vias + 1 lote delete croquis + 2 lotes upsert croquis (15+1) + 2 lotes upsert vias (12+1) = 6 queries
    assert cliente.executar_query.call_count == 6


def test_sincronizar_catalogo_d1_ja_atualizado(tmp_path: Path) -> None:
    caminho_novo = tmp_path / "novo.db"
    versao = _criar_catalogo_teste(
        caminho_novo,
        [
            (
                {
                    "croqui_uid": "c1",
                    "id_slug": "br_mg_bh_1",
                    "nome": "Pico 1",
                    "cidade": "BH",
                    "uf": "MG",
                },
                [],
            )
        ],
    )

    cliente = MagicMock(spec=ClienteCloudflareD1)
    cliente.executar_query.side_effect = [
        [],  # CREATE TABLE catalogo_croquis
        [],  # CREATE TABLE catalogo_aresta
        [],  # CREATE TABLE deltas_catalogo
        [],  # CREATE INDEX idx_deltas_versao_hash
        [{"versao_hash": versao}],  # SELECT versao_hash
    ]

    status = sincronizar_catalogo_d1(caminho_novo, None, cliente=cliente)
    assert status == "atualizado"
    assert cliente.executar_query.call_count == 5


def test_sincronizar_catalogo_d1_bootstrap_quando_d1_vazio(tmp_path: Path) -> None:
    caminho_novo = tmp_path / "novo.db"
    versao_nova = _criar_catalogo_teste(
        caminho_novo,
        [
            (
                {
                    "croqui_uid": "c1",
                    "id_slug": "br_mg_bh_1",
                    "nome": "Pico 1",
                    "cidade": "BH",
                    "uf": "MG",
                },
                [
                    {
                        "uid": "v1",
                        "croqui_uid": "c1",
                        "nome": "Via 1",
                        "grau": "6sup",
                        "tipo": "esportiva",
                        "setor_nome": "S1",
                        "setor_uid": "s1",
                    }
                ],
            )
        ],
    )

    cliente = MagicMock(spec=ClienteCloudflareD1)
    cliente.executar_query.return_value = []

    status = sincronizar_catalogo_d1(caminho_novo, None, cliente=cliente)
    assert status == "bootstrap"

    # Verifica que inseriu o registro inicial em deltas_catalogo com a versao_nova
    ultima_chamada = cliente.executar_query.call_args_list[-1]
    sql_final, params_finais = ultima_chamada[0]
    assert "INSERT INTO deltas_catalogo" in sql_final
    assert params_finais[0] == versao_nova


def test_sincronizar_catalogo_d1_delta_incremental(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui_base = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "uf": "MG",
    }
    via_1 = {
        "uid": "v1",
        "croqui_uid": "c1",
        "nome": "Via 1",
        "grau": "6sup",
        "tipo": "esportiva",
        "setor_nome": "S1",
        "setor_uid": "s1",
    }
    via_2 = {
        "uid": "v2",
        "croqui_uid": "c1",
        "nome": "Via 2",
        "grau": "7a",
        "tipo": "esportiva",
        "setor_nome": "S1",
        "setor_uid": "s1",
    }

    versao_ant = _criar_catalogo_teste(caminho_ant, [(croqui_base, [via_1])])
    versao_nova = _criar_catalogo_teste(caminho_novo, [(croqui_base, [via_1, via_2])])

    cliente = MagicMock(spec=ClienteCloudflareD1)
    cliente.executar_query.side_effect = [
        [],  # CREATE TABLE catalogo_croquis
        [],  # CREATE TABLE catalogo_aresta
        [],  # CREATE TABLE deltas_catalogo
        [],  # CREATE INDEX idx_deltas_versao_hash
        [{"versao_hash": versao_ant}],  # SELECT versao_hash (bate com o R2 anterior!)
        [],  # INSERT OR REPLACE INTO catalogo_aresta (via_2)
        [],  # INSERT INTO deltas_catalogo
    ]

    monkeypatch.setattr(
        ClienteCloudflareD1,
        "a_partir_do_ambiente",
        classmethod(lambda cls: cliente),
    )

    status = sincronizar_catalogo_d1(
        caminho_catalogo_novo=caminho_novo,
        caminho_catalogo_anterior_r2=caminho_ant,
        cliente=None,
    )
    assert status == "delta"

    ultima_chamada = cliente.executar_query.call_args_list[-1]
    sql_final, params_finais = ultima_chamada[0]
    assert "INSERT INTO deltas_catalogo" in sql_final
    assert params_finais[0] == versao_nova
    upserts_salvos = json.loads(params_finais[1])
    assert len(upserts_salvos["vias"]) == 1
    assert upserts_salvos["vias"][0]["uid"] == "v2"
