# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para sincronização transacional do catálogo SQLite com o Cloudflare D1.

Responsável por:
- Comunicar-se com a API REST do Cloudflare D1 via urllib.request.
- Garantir a criação e migração automática do schema (catalogo_croquis, catalogo_aresta, deltas_catalogo).
- Executar bootstrap completo em lotes seguros quando o banco D1 estiver vazio ou dessincronizado.
- Calcular e aplicar deltas incrementais (upserts e deletes) e registrar a versão em deltas_catalogo.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.gerar_catalogo_sqlite_lib import obter_versao_catalogo
from scripts.gerar_deltas_catalogo import calcular_deltas_catalogo, gerar_payload_d1

TAMANHO_LOTE_DELETE = 50
TAMANHO_LOTE_UPSERT_CROQUIS = 15
TAMANHO_LOTE_UPSERT_ENTIDADES = 10


class ClienteCloudflareD1:
    """Cliente REST para execução de queries SQL parametrizadas no Cloudflare D1."""

    def __init__(
        self,
        account_id: str,
        database_id: str,
        api_token: str,
        base_url: str = "https://api.cloudflare.com/client/v4",
    ) -> None:
        self.account_id = account_id
        self.database_id = database_id
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")

    @classmethod
    def a_partir_do_ambiente(cls) -> ClienteCloudflareD1:
        """Instancia o cliente lendo as variáveis de ambiente exigidas no pipeline."""
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        database_id = os.environ.get("CLOUDFLARE_CATALOGO_D1_DATABASE_ID", "").strip()
        api_token = os.environ.get("CLOUDFLARE_CATALOGO_D1_API_TOKEN", "").strip()
        base_url = (
            os.environ.get("CLOUDFLARE_D1_BASE_URL", "").strip()
            or "https://api.cloudflare.com/client/v4"
        )

        if not account_id or not database_id or not api_token:
            raise ValueError(
                "Credenciais do Cloudflare D1 ausentes "
                "(CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_CATALOGO_D1_DATABASE_ID ou "
                "CLOUDFLARE_CATALOGO_D1_API_TOKEN)."
            )
        return cls(
            account_id=account_id,
            database_id=database_id,
            api_token=api_token,
            base_url=base_url,
        )

    def executar_query(
        self, sql: str, params: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Executa uma instrução SQL parametrizada no Cloudflare D1 via API REST."""
        url = (
            f"{self.base_url}/accounts/{self.account_id}"
            f"/d1/database/{self.database_id}/query"
        )
        corpo = json.dumps({"sql": sql, "params": params or []}).encode("utf-8")
        requisicao = urllib.request.Request(
            url,
            data=corpo,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(requisicao) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Erro HTTP {erro.code} no Cloudflare D1: {detalhe}"
            ) from erro

        if not dados.get("success", False):
            erros = dados.get("errors", [])
            raise RuntimeError(f"Falha na query do Cloudflare D1: {erros}")

        resultados = dados.get("result", [])
        if resultados and isinstance(resultados, list):
            return list(resultados[0].get("results", []))
        return []


def inicializar_schema_d1(cliente: ClienteCloudflareD1) -> None:
    """Garante que as tabelas e índices do catálogo e de deltas existam no Cloudflare D1."""
    # Detecta se catalogo_aresta já existe com formato legado (sem a coluna escalada_tipo)
    info_tabela = cliente.executar_query("PRAGMA table_info(catalogo_aresta)")
    colunas = [linha["name"] for linha in info_tabela if "name" in linha]
    if colunas and "escalada_tipo" not in colunas:
        cliente.executar_query("DROP TABLE catalogo_aresta")
        cliente.executar_query("DELETE FROM deltas_catalogo")

    cliente.executar_query(
        """
        CREATE TABLE IF NOT EXISTS catalogo_croquis (
            croqui_uid TEXT PRIMARY KEY,
            id_slug TEXT NOT NULL,
            nome TEXT NOT NULL,
            cidade TEXT,
            uf TEXT
        );
        """
    )
    cliente.executar_query(
        """
        CREATE TABLE IF NOT EXISTS catalogo_aresta (
            uid TEXT PRIMARY KEY,
            tipo TEXT NOT NULL,
            croqui_uid TEXT NOT NULL,
            nome TEXT NOT NULL,
            escalada_grau TEXT,
            escalada_tipo TEXT,
            setor_uid TEXT,
            grupo_uid TEXT
        );
        """
    )
    cliente.executar_query(
        """
        CREATE TABLE IF NOT EXISTS deltas_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            versao_hash TEXT NOT NULL UNIQUE,
            criado_em TEXT NOT NULL,
            upserts_json TEXT NOT NULL,
            deletes_json TEXT NOT NULL
        );
        """
    )
    cliente.executar_query(
        """
        CREATE INDEX IF NOT EXISTS idx_catalogo_aresta_croqui
        ON catalogo_aresta(croqui_uid);
        """
    )
    cliente.executar_query(
        """
        CREATE INDEX IF NOT EXISTS idx_catalogo_aresta_nome
        ON catalogo_aresta(nome COLLATE NOCASE);
        """
    )
    cliente.executar_query(
        """
        CREATE INDEX IF NOT EXISTS idx_catalogo_aresta_tipo
        ON catalogo_aresta(tipo);
        """
    )
    cliente.executar_query(
        """
        CREATE INDEX IF NOT EXISTS idx_deltas_versao_hash
        ON deltas_catalogo(versao_hash);
        """
    )


def obter_ultima_versao_d1(cliente: ClienteCloudflareD1) -> str | None:
    """Retorna o versao_hash do último delta registrado no Cloudflare D1, ou None se vazio."""
    linhas = cliente.executar_query(
        "SELECT versao_hash FROM deltas_catalogo ORDER BY id DESC LIMIT 1"
    )
    if linhas and linhas[0].get("versao_hash"):
        return str(linhas[0]["versao_hash"])
    return None


def aplicar_upserts_e_deletes_d1(
    cliente: ClienteCloudflareD1, deltas: dict[str, Any]
) -> None:
    """
    Aplica as deleções e inserções/atualizações nas tabelas espelho do D1 em lotes
    compatíveis com o limite de bind parameters da API D1.
    """
    entidades_deletes: list[str] = deltas.get("entidades", {}).get(
        "deletes", []
    )
    for i in range(0, len(entidades_deletes), TAMANHO_LOTE_DELETE):
        lote = entidades_deletes[i : i + TAMANHO_LOTE_DELETE]
        marcadores = ", ".join("?" for _ in lote)
        cliente.executar_query(
            f"DELETE FROM catalogo_aresta WHERE uid IN ({marcadores})",
            lote,
        )

    croquis_deletes: list[str] = deltas["croquis"]["deletes"]
    for i in range(0, len(croquis_deletes), TAMANHO_LOTE_DELETE):
        lote = croquis_deletes[i : i + TAMANHO_LOTE_DELETE]
        marcadores = ", ".join("?" for _ in lote)
        cliente.executar_query(
            f"DELETE FROM catalogo_croquis WHERE croqui_uid IN ({marcadores})",
            lote,
        )

    croquis_upserts: list[dict[str, Any]] = deltas["croquis"]["upserts"]
    for i in range(0, len(croquis_upserts), TAMANHO_LOTE_UPSERT_CROQUIS):
        lote_croquis = croquis_upserts[i : i + TAMANHO_LOTE_UPSERT_CROQUIS]
        marcadores = ", ".join("(?, ?, ?, ?, ?)" for _ in lote_croquis)
        parametros: list[Any] = []
        for c in lote_croquis:
            parametros.extend(
                [
                    c["croqui_uid"],
                    c["id_slug"],
                    c["nome"],
                    c.get("cidade", ""),
                    c.get("uf", ""),
                ]
            )
        cliente.executar_query(
            f"INSERT OR REPLACE INTO catalogo_croquis (croqui_uid, id_slug, nome, cidade, uf) VALUES {marcadores}",
            parametros,
        )

    entidades_upserts: list[dict[str, Any]] = deltas.get("entidades", {}).get(
        "upserts", []
    )
    for i in range(0, len(entidades_upserts), TAMANHO_LOTE_UPSERT_ENTIDADES):
        lote_entidades = entidades_upserts[i : i + TAMANHO_LOTE_UPSERT_ENTIDADES]
        marcadores = ", ".join("(?, ?, ?, ?, ?, ?, ?, ?)" for _ in lote_entidades)
        parametros_entidades: list[Any] = []
        for e in lote_entidades:
            parametros_entidades.extend(
                [
                    e["uid"],
                    e["tipo"],
                    e["croqui_uid"],
                    e["nome"],
                    e.get("escalada_grau"),
                    e.get("escalada_tipo"),
                    e.get("setor_uid"),
                    e.get("grupo_uid"),
                ]
            )
        cliente.executar_query(
            "INSERT OR REPLACE INTO catalogo_aresta "
            "(uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid) "
            f"VALUES {marcadores}",
            parametros_entidades,
        )


def sincronizar_catalogo_d1(
    caminho_catalogo_novo: Path | str,
    caminho_catalogo_anterior_r2: Path | str | None = None,
    cliente: ClienteCloudflareD1 | None = None,
) -> str:
    """
    Sincroniza o estado do catálogo local com o banco Cloudflare D1.

    Retorna:
        str: "atualizado" se o D1 já estava na versão destino,
             "bootstrap" se foi realizado o carregamento completo inicial,
             "delta" se foi aplicado um delta incremental.
    """
    if cliente is None:
        cliente = ClienteCloudflareD1.a_partir_do_ambiente()

    novo_path = Path(caminho_catalogo_novo)
    versao_nova = obter_versao_catalogo(novo_path)

    inicializar_schema_d1(cliente)
    ultima_versao_d1 = obter_ultima_versao_d1(cliente)

    if ultima_versao_d1 == versao_nova:
        print(f"Cloudflare D1 já está sincronizado na versão {versao_nova}.")
        return "atualizado"

    ant_path = Path(caminho_catalogo_anterior_r2) if caminho_catalogo_anterior_r2 else None
    versao_anterior_r2 = (
        obter_versao_catalogo(ant_path)
        if (ant_path is not None and ant_path.exists())
        else ""
    )

    precisa_bootstrap = (
        ultima_versao_d1 is None
        or not versao_anterior_r2
        or ultima_versao_d1 != versao_anterior_r2
    )

    if precisa_bootstrap:
        print(
            f"Executando bootstrap completo do Cloudflare D1 para versão {versao_nova}..."
        )
        cliente.executar_query("DELETE FROM catalogo_aresta")
        cliente.executar_query("DELETE FROM catalogo_croquis")
        cliente.executar_query("DELETE FROM deltas_catalogo")

        deltas_completos = calcular_deltas_catalogo(None, novo_path)
        aplicar_upserts_e_deletes_d1(cliente, deltas_completos)

        vazio_json = json.dumps({"croquis": [], "entidades": []}, ensure_ascii=False)
        cliente.executar_query(
            "INSERT INTO deltas_catalogo (versao_hash, criado_em, upserts_json, deletes_json) "
            "VALUES (?, datetime('now'), ?, ?)",
            [versao_nova, vazio_json, vazio_json],
        )
        return "bootstrap"

    print(
        f"Aplicando delta incremental no Cloudflare D1 ({versao_anterior_r2} -> {versao_nova})..."
    )
    deltas = calcular_deltas_catalogo(ant_path, novo_path)
    aplicar_upserts_e_deletes_d1(cliente, deltas)
    upserts_json, deletes_json = gerar_payload_d1(deltas)
    cliente.executar_query(
        "INSERT INTO deltas_catalogo (versao_hash, criado_em, upserts_json, deletes_json) "
        "VALUES (?, datetime('now'), ?, ?)",
        [versao_nova, upserts_json, deletes_json],
    )
    return "delta"
