# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para serving/sincronizar_d1_lib.py."""

from __future__ import annotations

import http.server
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from scripts.gerar_catalogo_sqlite_lib import (
    calcular_versao_catalogo,
    inicializar_banco_catalogo,
    inserir_croqui_no_catalogo,
)
from serving.cliente_cloudflare_d1_fake import ClienteCloudflareD1Fake
from serving.sincronizar_d1_lib import (
    ClienteCloudflareD1,
    aplicar_upserts_e_deletes_d1,
    inicializar_schema_d1,
    obter_ultima_versao_d1,
    sincronizar_catalogo_d1,
)


def _criar_catalogo_teste(
    caminho: Path,
    croquis_com_registros: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> str:
    conexao = inicializar_banco_catalogo(caminho)
    with conexao:
        for croqui, registros in croquis_com_registros:
            dados_croqui = dict(croqui)
            dados_croqui.setdefault("atualizado_em", 100)
            inserir_croqui_no_catalogo(conexao, dados_croqui, registros)
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


class _ManipuladorHttpD1ParaTestes(http.server.BaseHTTPRequestHandler):
    """Servidor HTTP em memória para testar chamadas REST reais de ClienteCloudflareD1."""

    respostas: list[tuple[int, dict[str, Any]]] = []
    requisicoes_recebidas: list[tuple[str, dict[str, str], bytes]] = []

    def do_POST(self) -> None:
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = self.rfile.read(tamanho)
        headers_dict = dict(self.headers.items())
        _ManipuladorHttpD1ParaTestes.requisicoes_recebidas.append((self.path, headers_dict, corpo))

        if _ManipuladorHttpD1ParaTestes.respostas:
            codigo, payload = _ManipuladorHttpD1ParaTestes.respostas.pop(0)
        else:
            codigo, payload = 200, {"success": True, "result": []}

        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def servidor_http_d1():
    _ManipuladorHttpD1ParaTestes.respostas = []
    _ManipuladorHttpD1ParaTestes.requisicoes_recebidas = []
    servidor = http.server.HTTPServer(("127.0.0.1", 0), _ManipuladorHttpD1ParaTestes)
    thread = threading.Thread(target=servidor.serve_forever)
    thread.daemon = True
    thread.start()

    porta = servidor.server_address[1]
    yield f"http://127.0.0.1:{porta}"

    servidor.shutdown()
    servidor.server_close()


def test_cliente_d1_executar_query_sucesso(servidor_http_d1: str) -> None:
    _ManipuladorHttpD1ParaTestes.respostas = [
        (200, {"success": True, "result": [{"results": [{"versao_hash": "abcd1234abcd1234"}]}]})
    ]

    cliente = ClienteCloudflareD1(
        account_id="acc-1",
        database_id="db-1",
        api_token="tok-1",
        base_url=servidor_http_d1,
    )
    linhas = cliente.executar_query("SELECT versao_hash FROM deltas_catalogo", ["p1"])
    assert linhas == [{"versao_hash": "abcd1234abcd1234"}]

    caminho, headers, corpo = _ManipuladorHttpD1ParaTestes.requisicoes_recebidas[0]
    assert caminho == "/accounts/acc-1/d1/database/db-1/query"
    assert headers["Authorization"] == "Bearer tok-1"
    dados = json.loads(corpo.decode("utf-8"))
    assert dados["sql"] == "SELECT versao_hash FROM deltas_catalogo"
    assert dados["params"] == ["p1"]


def test_cliente_d1_executar_query_resultado_vazio(servidor_http_d1: str) -> None:
    _ManipuladorHttpD1ParaTestes.respostas = [(200, {"success": True, "result": []})]
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1", base_url=servidor_http_d1)
    assert cliente.executar_query("DELETE FROM catalogo_croquis") == []


def test_cliente_d1_executar_query_erro_api(servidor_http_d1: str) -> None:
    _ManipuladorHttpD1ParaTestes.respostas = [
        (200, {"success": False, "errors": [{"message": "syntax error near SELECT"}]})
    ]
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1", base_url=servidor_http_d1)
    with pytest.raises(RuntimeError, match="Falha na query do Cloudflare D1"):
        cliente.executar_query("SELECT *")


def test_cliente_d1_executar_query_erro_http(servidor_http_d1: str) -> None:
    _ManipuladorHttpD1ParaTestes.respostas = [(401, {"errors": [{"message": "Invalid token"}]})]
    cliente = ClienteCloudflareD1("acc-1", "db-1", "tok-1", base_url=servidor_http_d1)
    with pytest.raises(RuntimeError, match="Erro HTTP 401 no Cloudflare D1"):
        cliente.executar_query("SELECT 1")


def test_inicializar_schema_d1_criacao_e_migracao_legado() -> None:
    fake = ClienteCloudflareD1Fake()

    # 1. Primeira inicialização: cria tabelas e índices
    inicializar_schema_d1(fake)

    info_tabela = fake.executar_query("PRAGMA table_info(catalogo_aresta)")
    colunas = [linha["name"] for linha in info_tabela]
    assert colunas == [
        "uid",
        "tipo",
        "croqui_uid",
        "nome",
        "escalada_grau",
        "escalada_tipo",
        "setor_uid",
        "grupo_uid",
    ]

    # 2. Simula schema legado no D1 (catalogo_croquis com uf, catalogo_aresta antiga e registros em deltas_catalogo)
    fake.executar_query("DROP TABLE catalogo_croquis")
    fake.executar_query(
        """
        CREATE TABLE catalogo_croquis (
            croqui_uid TEXT PRIMARY KEY,
            id_slug TEXT NOT NULL,
            nome TEXT NOT NULL,
            cidade TEXT,
            uf TEXT
        );
        """
    )
    fake.executar_query("DROP TABLE catalogo_aresta")
    fake.executar_query(
        """
        CREATE TABLE catalogo_aresta (
            uid TEXT PRIMARY KEY,
            croqui_uid TEXT NOT NULL,
            nome TEXT NOT NULL,
            grau TEXT,
            tipo TEXT,
            setor_nome TEXT,
            setor_uid TEXT
        );
        """
    )
    fake.executar_query(
        "INSERT INTO deltas_catalogo (versao_hash, criado_em, upserts_json, deletes_json) "
        "VALUES ('versao_antiga', datetime('now'), '{}', '{}')"
    )
    assert len(fake.executar_query("SELECT * FROM deltas_catalogo")) == 1

    # Ao rodar inicializar_schema_d1 novamente, detecta ausência de estado / escalada_tipo e migra
    inicializar_schema_d1(fake)

    info_croquis_migrada = fake.executar_query("PRAGMA table_info(catalogo_croquis)")
    colunas_croquis_migradas = [linha["name"] for linha in info_croquis_migrada]
    assert "estado" in colunas_croquis_migradas
    assert "uf" not in colunas_croquis_migradas

    info_migrada = fake.executar_query("PRAGMA table_info(catalogo_aresta)")
    colunas_migradas = [linha["name"] for linha in info_migrada]
    assert "escalada_tipo" in colunas_migradas
    assert "setor_nome" not in colunas_migradas
    # Deltas antigos foram limpos para forçar bootstrap limpo
    assert len(fake.executar_query("SELECT * FROM deltas_catalogo")) == 0


def test_obter_ultima_versao_d1() -> None:
    fake = ClienteCloudflareD1Fake()
    inicializar_schema_d1(fake)
    assert obter_ultima_versao_d1(fake) is None

    fake.executar_query(
        "INSERT INTO deltas_catalogo (versao_hash, criado_em, upserts_json, deletes_json) "
        "VALUES ('versao1234567890', datetime('now'), '{}', '{}')"
    )
    assert obter_ultima_versao_d1(fake) == "versao1234567890"


def test_aplicar_upserts_e_deletes_d1_em_lotes() -> None:
    fake = ClienteCloudflareD1Fake()
    inicializar_schema_d1(fake)

    deltas = {
        "croquis": {
            "upserts": [
                {
                    "croqui_uid": f"c{i}",
                    "id_slug": f"slug_{i}",
                    "nome": f"Pico {i}",
                    "cidade": "BH",
                    "estado": "MG",
                }
                for i in range(16)
            ],
            "deletes": ["c_del_1", "c_del_2"],
        },
        "entidades": {
            "upserts": [
                {
                    "uid": f"v{i}",
                    "tipo": "escalada",
                    "croqui_uid": "c0",
                    "nome": f"Via {i}",
                    "escalada_grau": "6sup",
                    "escalada_tipo": "esportiva",
                    "setor_uid": "s1",
                    "grupo_uid": None,
                }
                for i in range(13)
            ],
            "deletes": ["v_del_1"],
        },
    }

    aplicar_upserts_e_deletes_d1(fake, deltas)

    linhas_croquis = fake.executar_query("SELECT COUNT(*) AS total FROM catalogo_croquis")
    assert linhas_croquis[0]["total"] == 16

    linhas_aresta = fake.executar_query("SELECT COUNT(*) AS total FROM catalogo_aresta")
    assert linhas_aresta[0]["total"] == 13


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
                    "estado": "MG",
                },
                [],
            )
        ],
    )

    fake = ClienteCloudflareD1Fake()
    inicializar_schema_d1(fake)
    fake.executar_query(
        "INSERT INTO deltas_catalogo (versao_hash, criado_em, upserts_json, deletes_json) "
        "VALUES (?, datetime('now'), '{}', '{}')",
        [versao],
    )

    status = sincronizar_catalogo_d1(caminho_novo, None, cliente=fake)
    assert status == "atualizado"


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
                    "estado": "MG",
                },
                [
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
                ],
            )
        ],
    )

    fake = ClienteCloudflareD1Fake()

    status = sincronizar_catalogo_d1(caminho_novo, None, cliente=fake)
    assert status == "bootstrap"

    assert obter_ultima_versao_d1(fake) == versao_nova
    linhas_aresta = fake.executar_query("SELECT uid, tipo, nome FROM catalogo_aresta")
    assert len(linhas_aresta) == 1
    assert linhas_aresta[0]["uid"] == "v1"
    assert linhas_aresta[0]["tipo"] == "escalada"


def test_sincronizar_catalogo_d1_delta_incremental(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui_base = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "estado": "MG",
    }
    setor = {
        "uid": "s1",
        "tipo": "setor",
        "croqui_uid": "c1",
        "nome": "Setor 1",
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

    versao_ant = _criar_catalogo_teste(caminho_ant, [(croqui_base, [setor, via_1])])
    versao_nova = _criar_catalogo_teste(caminho_novo, [(croqui_base, [setor, via_1, via_2])])

    fake = ClienteCloudflareD1Fake()
    # Roda bootstrap na versão anterior
    sincronizar_catalogo_d1(caminho_catalogo_novo=caminho_ant, cliente=fake)
    assert obter_ultima_versao_d1(fake) == versao_ant

    # Aplica delta incremental para a nova versão
    status = sincronizar_catalogo_d1(
        caminho_catalogo_novo=caminho_novo,
        caminho_catalogo_anterior_r2=caminho_ant,
        cliente=fake,
    )
    assert status == "delta"
    assert obter_ultima_versao_d1(fake) == versao_nova

    # Verifica o delta salvo
    ultimo_delta = fake.executar_query(
        "SELECT upserts_json FROM deltas_catalogo ORDER BY id DESC LIMIT 1"
    )
    upserts = json.loads(ultimo_delta[0]["upserts_json"])
    assert len(upserts["entidades"]) == 1
    assert upserts["entidades"][0]["uid"] == "v2"
    assert upserts["entidades"][0]["tipo"] == "escalada"


def test_sincronizar_catalogo_d1_renomear_setor_gera_um_upsert(tmp_path: Path) -> None:
    caminho_ant = tmp_path / "ant.db"
    caminho_novo = tmp_path / "novo.db"

    croqui_base = {
        "croqui_uid": "c1",
        "id_slug": "br_mg_bh_1",
        "nome": "Pico 1",
        "cidade": "BH",
        "estado": "MG",
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

    _criar_catalogo_teste(caminho_ant, [(croqui_base, [setor_ant, via_1])])

    setor_novo = dict(setor_ant)
    setor_novo["nome"] = "Setor Renomeado"
    _criar_catalogo_teste(caminho_novo, [(croqui_base, [setor_novo, via_1])])

    fake = ClienteCloudflareD1Fake()
    sincronizar_catalogo_d1(caminho_catalogo_novo=caminho_ant, cliente=fake)

    status = sincronizar_catalogo_d1(
        caminho_catalogo_novo=caminho_novo,
        caminho_catalogo_anterior_r2=caminho_ant,
        cliente=fake,
    )
    assert status == "delta"

    ultimo_delta = fake.executar_query(
        "SELECT upserts_json FROM deltas_catalogo ORDER BY id DESC LIMIT 1"
    )
    upserts = json.loads(ultimo_delta[0]["upserts_json"])
    assert len(upserts["entidades"]) == 1
    assert upserts["entidades"][0]["uid"] == "s1"
    assert upserts["entidades"][0]["tipo"] == "setor"
    assert upserts["entidades"][0]["nome"] == "Setor Renomeado"


def test_sincronizar_catalogo_d1_cliente_padrao_ambiente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, servidor_http_d1: str
) -> None:
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
                    "estado": "MG",
                },
                [],
            )
        ],
    )

    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc-env")
    monkeypatch.setenv("CLOUDFLARE_CATALOGO_D1_DATABASE_ID", "db-env")
    monkeypatch.setenv("CLOUDFLARE_CATALOGO_D1_API_TOKEN", "tok-env")
    monkeypatch.setenv("CLOUDFLARE_D1_BASE_URL", servidor_http_d1)

    _ManipuladorHttpD1ParaTestes.respostas = [
        (
            200,
            {
                "success": True,
                "result": [{"results": [{"name": "croqui_uid"}, {"name": "estado"}]}],
            },
        ),
        (
            200,
            {
                "success": True,
                "result": [{"results": [{"name": "uid"}, {"name": "escalada_tipo"}]}],
            },
        ),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": []}),
        (200, {"success": True, "result": [{"results": [{"versao_hash": versao}]}]}),
    ]

    status = sincronizar_catalogo_d1(caminho_novo, None, cliente=None)
    assert status == "atualizado"
