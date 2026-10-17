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
        for dados_croqui, registros in croquis_com_vias:
            inserir_croqui_no_catalogo(conexao, dados_croqui, registros)
    conexao.close()


def test_calcular_deltas_sem_banco_anterior(tmp_path: Path) -> None:
    caminho_novo = tmp_path / "novo.db"
    croqui = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "estado": "MG",
        "atualizado_em": 100,
    }
    registros = [
        {
            "uid": "v1",
            "tipo": "escalada",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "escalada_grau": "6sup",
            "escalada_tipo": "esportiva",
            "setor_uid": "s1",
            "grupo_uid": None,
        }
    ]
    _criar_banco_com_dados(caminho_novo, [(croqui, registros)])

    deltas = calcular_deltas_catalogo(caminho_anterior=None, caminho_novo=caminho_novo)

    assert len(deltas["croquis"]["upserts"]) == 1
    assert deltas["croquis"]["upserts"][0]["croqui_uid"] == "c1"
    assert deltas["croquis"]["deletes"] == []

    assert len(deltas["entidades"]["upserts"]) == 1
    assert deltas["entidades"]["upserts"][0]["uid"] == "v1"
    assert deltas["entidades"]["deletes"] == []


def test_calcular_deltas_sem_modificacoes(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "estado": "MG",
        "atualizado_em": 100,
    }
    registros = [
        {
            "uid": "v1",
            "tipo": "escalada",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "escalada_grau": "6sup",
            "escalada_tipo": "esportiva",
            "setor_uid": "s1",
            "grupo_uid": None,
        }
    ]
    _criar_banco_com_dados(caminho_ant, [(croqui, registros)])
    _criar_banco_com_dados(caminho_novo, [(croqui, registros)])

    deltas = calcular_deltas_catalogo(caminho_anterior=caminho_ant, caminho_novo=caminho_novo)

    assert deltas["croquis"]["upserts"] == []
    assert deltas["croquis"]["deletes"] == []
    assert deltas["entidades"]["upserts"] == []
    assert deltas["entidades"]["deletes"] == []


def test_calcular_deltas_alteracao_e_remocao(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui_ant = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "estado": "MG",
        "atualizado_em": 100,
    }
    registros_ant = [
        {
            "uid": "v1",
            "tipo": "escalada",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "escalada_grau": "6sup",
            "escalada_tipo": "esportiva",
            "setor_uid": "s1",
            "grupo_uid": None,
        },
        {
            "uid": "v2",
            "tipo": "escalada",
            "croqui_uid": "c1",
            "nome": "Via 2 Removida",
            "escalada_grau": "7a",
            "escalada_tipo": "esportiva",
            "setor_uid": "s1",
            "grupo_uid": None,
        },
    ]
    _criar_banco_com_dados(caminho_ant, [(croqui_ant, registros_ant)])

    # Novo: v1 teve grau alterado para 7b, v2 foi removida, v3 foi adicionada
    croqui_novo = dict(croqui_ant)
    croqui_novo["nome"] = "Pico 1 Renomeado"

    registros_novos = [
        {
            "uid": "v1",
            "tipo": "escalada",
            "croqui_uid": "c1",
            "nome": "Via 1",
            "escalada_grau": "7b",
            "escalada_tipo": "esportiva",
            "setor_uid": "s1",
            "grupo_uid": None,
        },
        {
            "uid": "v3",
            "tipo": "escalada",
            "croqui_uid": "c1",
            "nome": "Via 3 Nova",
            "escalada_grau": "8a",
            "escalada_tipo": "esportiva",
            "setor_uid": "s1",
            "grupo_uid": None,
        },
    ]
    _criar_banco_com_dados(caminho_novo, [(croqui_novo, registros_novos)])

    deltas = calcular_deltas_catalogo(caminho_anterior=caminho_ant, caminho_novo=caminho_novo)

    # Croqui alterado
    assert len(deltas["croquis"]["upserts"]) == 1
    assert deltas["croquis"]["upserts"][0]["nome"] == "Pico 1 Renomeado"
    assert deltas["croquis"]["deletes"] == []

    # Registros: v1 (alterada) e v3 (adicionada) em upserts
    uids_upsert = {v["uid"] for v in deltas["entidades"]["upserts"]}
    assert uids_upsert == {"v1", "v3"}
    v1_upsert = next(v for v in deltas["entidades"]["upserts"] if v["uid"] == "v1")
    assert v1_upsert["escalada_grau"] == "7b"

    # Registros: v2 em deletes
    assert deltas["entidades"]["deletes"] == ["v2"]
    assert len(deltas["versao_hash"]) == 16


def test_renomear_setor_gera_apenas_um_upsert_sem_afetar_escaladas(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "estado": "MG",
        "atualizado_em": 100,
    }
    setor_ant = {
        "uid": "s1",
        "tipo": "setor",
        "croqui_uid": "c1",
        "nome": "Setor Antigo",
        "escalada_grau": None,
        "escalada_tipo": None,
        "setor_uid": None,
        "grupo_uid": None,
    }
    via_1 = {
        "uid": "v1",
        "tipo": "escalada",
        "croqui_uid": "c1",
        "nome": "Via 1",
        "escalada_grau": "6sup",
        "escalada_tipo": "esportiva",
        "setor_uid": "s1",
        "grupo_uid": None,
    }
    via_2 = {
        "uid": "v2",
        "tipo": "escalada",
        "croqui_uid": "c1",
        "nome": "Via 2",
        "escalada_grau": "7a",
        "escalada_tipo": "esportiva",
        "setor_uid": "s1",
        "grupo_uid": None,
    }

    _criar_banco_com_dados(caminho_ant, [(croqui, [setor_ant, via_1, via_2])])

    # No banco novo, apenas o setor s1 foi renomeado
    setor_novo = dict(setor_ant)
    setor_novo["nome"] = "Setor Renomeado"
    _criar_banco_com_dados(caminho_novo, [(croqui, [setor_novo, via_1, via_2])])

    deltas = calcular_deltas_catalogo(caminho_anterior=caminho_ant, caminho_novo=caminho_novo)

    # Exatamente 1 upsert em entidades (o próprio setor), e zero upserts para as escaladas v1 e v2!
    assert len(deltas["entidades"]["upserts"]) == 1
    assert deltas["entidades"]["upserts"][0]["uid"] == "s1"
    assert deltas["entidades"]["upserts"][0]["tipo"] == "setor"
    assert deltas["entidades"]["upserts"][0]["nome"] == "Setor Renomeado"
    assert deltas["entidades"]["deletes"] == []


def test_gerar_payload_d1_e_sql() -> None:
    deltas = {
        "versao_hash": "def9a51c1b66df98",
        "croquis": {
            "upserts": [{"croqui_uid": "c1", "nome": "Pico"}],
            "deletes": ["c0"],
        },
        "entidades": {
            "upserts": [{"uid": "v1", "nome": "Via"}],
            "deletes": ["v0"],
        },
    }

    upserts_json, deletes_json = gerar_payload_d1(deltas)
    upserts = json.loads(upserts_json)
    deletes = json.loads(deletes_json)

    assert "croquis" in upserts
    assert "entidades" in upserts
    assert "croquis" in deletes
    assert "entidades" in deletes

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
    assert "entidades" in dados_salvos
    assert "INSERT INTO deltas_catalogo" in caminho_sql.read_text(encoding="utf-8")
