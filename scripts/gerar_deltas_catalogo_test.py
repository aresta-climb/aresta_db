# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para scripts/gerar_deltas_catalogo.py."""

import json
from pathlib import Path

import pytest

from scripts.gerar_catalogo_sqlite_lib import (
    inicializar_banco_catalogo,
    inserir_croqui_no_catalogo,
)
from scripts.gerar_deltas_catalogo import (
    calcular_deltas_catalogo,
    gerar_payload_d1,
    gerar_sql_insercao_delta_d1,
    main,
)


def _criar_banco_com_dados(caminho: Path, croquis_com_vias: list[tuple[dict, list[dict]]]) -> None:
    conexao = inicializar_banco_catalogo(caminho)
    with conexao:
        for dados_croqui, vias in croquis_com_vias:
            inserir_croqui_no_catalogo(conexao, dados_croqui, vias)
    conexao.close()


def test_calcular_deltas_sem_banco_anterior(tmp_path: Path) -> None:
    caminho_novo = tmp_path / "novo.db"
    croqui = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "uf": "MG",
        "atualizado_em": 100,
    }
    vias = [
        {
            "uid": "v1",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "grau": "6sup",
            "tipo": "esportiva",
            "setor_nome": "S1",
            "setor_uid": "s1",
        }
    ]
    _criar_banco_com_dados(caminho_novo, [(croqui, vias)])

    deltas = calcular_deltas_catalogo(caminho_anterior=None, caminho_novo=caminho_novo)

    assert len(deltas["croquis"]["upserts"]) == 1
    assert deltas["croquis"]["upserts"][0]["croqui_uid"] == "c1"
    assert deltas["croquis"]["deletes"] == []

    assert len(deltas["vias"]["upserts"]) == 1
    assert deltas["vias"]["upserts"][0]["uid"] == "v1"
    assert deltas["vias"]["deletes"] == []


def test_calcular_deltas_sem_modificacoes(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "uf": "MG",
        "atualizado_em": 100,
    }
    vias = [
        {
            "uid": "v1",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "grau": "6sup",
            "tipo": "esportiva",
            "setor_nome": "S1",
            "setor_uid": "s1",
        }
    ]
    _criar_banco_com_dados(caminho_ant, [(croqui, vias)])
    _criar_banco_com_dados(caminho_novo, [(croqui, vias)])

    deltas = calcular_deltas_catalogo(caminho_anterior=caminho_ant, caminho_novo=caminho_novo)

    assert deltas["croquis"]["upserts"] == []
    assert deltas["croquis"]["deletes"] == []
    assert deltas["vias"]["upserts"] == []
    assert deltas["vias"]["deletes"] == []


def test_calcular_deltas_alteracao_e_remocao(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui_ant = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "uf": "MG",
        "atualizado_em": 100,
    }
    vias_ant = [
        {
            "uid": "v1",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "grau": "6sup",
            "tipo": "esportiva",
            "setor_nome": "S1",
            "setor_uid": "s1",
        },
        {
            "uid": "v2",
            "croqui_uid": "c1",
            "nome": "Via 2 Removida",
            "grau": "7a",
            "tipo": "esportiva",
            "setor_nome": "S1",
            "setor_uid": "s1",
        },
    ]
    _criar_banco_com_dados(caminho_ant, [(croqui_ant, vias_ant)])

    # Novo: v1 teve grau alterado para 7b, v2 foi removida, v3 foi adicionada
    croqui_novo = dict(croqui_ant)
    croqui_novo["nome"] = "Pico 1 Renomeado"

    vias_novas = [
        {
            "uid": "v1",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "grau": "7b",
            "tipo": "esportiva",
            "setor_nome": "S1",
            "setor_uid": "s1",
        },
        {
            "uid": "v3",
            "croqui_uid": "c1",
            "nome": "Via 3 Nova",
            "grau": "8a",
            "tipo": "esportiva",
            "setor_nome": "S1",
            "setor_uid": "s1",
        },
    ]
    _criar_banco_com_dados(caminho_novo, [(croqui_novo, vias_novas)])

    deltas = calcular_deltas_catalogo(caminho_anterior=caminho_ant, caminho_novo=caminho_novo)

    # Croqui alterado
    assert len(deltas["croquis"]["upserts"]) == 1
    assert deltas["croquis"]["upserts"][0]["nome"] == "Pico 1 Renomeado"
    assert deltas["croquis"]["deletes"] == []

    # Vias: v1 (alterada) e v3 (adicionada) em upserts
    uids_upsert = {v["uid"] for v in deltas["vias"]["upserts"]}
    assert uids_upsert == {"v1", "v3"}
    v1_upsert = next(v for v in deltas["vias"]["upserts"] if v["uid"] == "v1")
    assert v1_upsert["grau"] == "7b"

    # Vias: v2 em deletes
    assert deltas["vias"]["deletes"] == ["v2"]
    assert len(deltas["versao_hash"]) == 16


def test_gerar_payload_d1_e_sql() -> None:
    deltas = {
        "versao_hash": "def9a51c1b66df98",
        "croquis": {
            "upserts": [{"croqui_uid": "c1", "nome": "Pico"}],
            "deletes": ["c0"],
        },
        "vias": {
            "upserts": [{"uid": "v1", "nome": "Via"}],
            "deletes": ["v0"],
        },
    }

    upserts_json, deletes_json = gerar_payload_d1(deltas)
    upserts = json.loads(upserts_json)
    deletes = json.loads(deletes_json)

    assert "croquis" in upserts
    assert "vias" in upserts
    assert "croquis" in deletes
    assert "vias" in deletes

    sql = gerar_sql_insercao_delta_d1(deltas)
    assert "INSERT INTO deltas_catalogo" in sql
    assert "versao_hash" in sql
    assert "def9a51c1b66df98" in sql
    assert "upserts_json" in sql
    assert "deletes_json" in sql


def test_main_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"
    caminho_saida = tmp_path / "deltas.json"
    caminho_sql = tmp_path / "inserir_delta.sql"

    _criar_banco_com_dados(caminho_ant, [])
    _criar_banco_com_dados(caminho_novo, [])

    monkeypatch.setattr(
        "sys.argv",
        [
            "gerar_deltas_catalogo.py",
            "--anterior",
            str(caminho_ant),
            "--novo",
            str(caminho_novo),
            "--saida",
            str(caminho_saida),
            "--sql",
            str(caminho_sql),
        ],
    )

    codigo = main()
    assert codigo == 0
    assert caminho_saida.exists()
    assert caminho_sql.exists()

    dados_salvos = json.loads(caminho_saida.read_text(encoding="utf-8"))
    assert "croquis" in dados_salvos
    assert "vias" in dados_salvos
    assert "INSERT INTO deltas_catalogo" in caminho_sql.read_text(encoding="utf-8")
    assert "vias" in dados_salvos
