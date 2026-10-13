# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário para cálculo e extração de deltas SQL do catálogo para o Cloudflare D1.

Compara duas versões do catálogo SQLite (versão anterior vs. versão nova gerada)
utilizando operações de conjunto nativas do SQLite (EXCEPT), produzindo o changeset
de inserções/atualizações (upserts) e deleções (deletes) em formato JSON para a tabela
deltas_catalogo no Cloudflare D1.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


def calcular_deltas_catalogo(
    caminho_anterior: Path | str | None,
    caminho_novo: Path | str,
) -> dict[str, Any]:
    """
    Compara o banco SQLite novo com o banco anterior e calcula os deltas de croquis e vias.

    Retorna:
        dict: Estrutura contendo:
            {
                "croquis": {"upserts": [...], "deletes": [...]},
                "vias": {"upserts": [...], "deletes": [...]}
            }
    """
    novo_path = Path(caminho_novo)
    con_novo = sqlite3.connect(str(novo_path))
    con_novo.row_factory = sqlite3.Row
    cur = con_novo.cursor()

    resultado: dict[str, Any] = {
        "croquis": {"upserts": [], "deletes": []},
        "vias": {"upserts": [], "deletes": []},
    }

    try:
        # Se não há banco anterior, todos os registros do novo são upserts
        if caminho_anterior is None or not Path(caminho_anterior).exists():
            cur.execute(
                "SELECT croqui_uid, id_slug, nome, cidade, uf FROM catalogo_croquis ORDER BY croqui_uid"
            )
            resultado["croquis"]["upserts"] = [dict(row) for row in cur.fetchall()]

            cur.execute(
                "SELECT uid, croqui_uid, nome, grau, tipo, setor_nome, setor_uid FROM catalogo_aresta ORDER BY uid"
            )
            resultado["vias"]["upserts"] = [dict(row) for row in cur.fetchall()]

            return resultado

        # Anexa o banco anterior
        ant_path = Path(caminho_anterior)
        cur.execute("ATTACH DATABASE ? AS anterior", (str(ant_path),))

        # 1. Croquis: Upserts (novos ou modificados)
        cur.execute(
            """
            SELECT croqui_uid, id_slug, nome, cidade, uf FROM catalogo_croquis
            EXCEPT
            SELECT croqui_uid, id_slug, nome, cidade, uf FROM anterior.catalogo_croquis
            ORDER BY croqui_uid
            """
        )
        resultado["croquis"]["upserts"] = [dict(row) for row in cur.fetchall()]

        # 2. Croquis: Deletes (presentes no anterior mas não no novo)
        cur.execute(
            """
            SELECT croqui_uid FROM anterior.catalogo_croquis
            EXCEPT
            SELECT croqui_uid FROM catalogo_croquis
            ORDER BY croqui_uid
            """
        )
        resultado["croquis"]["deletes"] = [row["croqui_uid"] for row in cur.fetchall()]

        # 3. Vias: Upserts (novas ou modificadas)
        cur.execute(
            """
            SELECT uid, croqui_uid, nome, grau, tipo, setor_nome, setor_uid FROM catalogo_aresta
            EXCEPT
            SELECT uid, croqui_uid, nome, grau, tipo, setor_nome, setor_uid FROM anterior.catalogo_aresta
            ORDER BY uid
            """
        )
        resultado["vias"]["upserts"] = [dict(row) for row in cur.fetchall()]

        # 4. Vias: Deletes (presentes no anterior mas não no novo)
        cur.execute(
            """
            SELECT uid FROM anterior.catalogo_aresta
            EXCEPT
            SELECT uid FROM catalogo_aresta
            ORDER BY uid
            """
        )
        resultado["vias"]["deletes"] = [row["uid"] for row in cur.fetchall()]

    finally:
        con_novo.close()

    return resultado


def gerar_payload_d1(deltas: dict[str, Any]) -> tuple[str, str]:
    """
    Formata o dicionário de deltas nos campos JSON para armazenamento no Cloudflare D1.

    Retorna:
        tuple[str, str]: (upserts_json, deletes_json)
    """
    upserts = {
        "croquis": deltas["croquis"]["upserts"],
        "vias": deltas["vias"]["upserts"],
    }
    deletes = {
        "croquis": deltas["croquis"]["deletes"],
        "vias": deltas["vias"]["deletes"],
    }
    return json.dumps(upserts, ensure_ascii=False), json.dumps(deletes, ensure_ascii=False)


def gerar_sql_insercao_delta_d1(deltas: dict[str, Any]) -> str:
    """
    Gera o comando SQL parametrizável para inserir o delta na tabela deltas_catalogo no D1.
    """
    upserts_json, deletes_json = gerar_payload_d1(deltas)
    sql = (
        "INSERT INTO deltas_catalogo (criado_em, upserts_json, deletes_json)\n"
        f"VALUES (datetime('now'), '{upserts_json}', '{deletes_json}');"
    )
    return sql


def main() -> int:
    """Interface de linha de comando para cálculo de deltas."""
    parser = argparse.ArgumentParser(
        description="Calcula a diferença entre duas versões de catalogo.db para alimentar o Cloudflare D1."
    )
    parser.add_argument(
        "--anterior",
        type=Path,
        default=None,
        help="Caminho para o catalogo.db da versão anterior.",
    )
    parser.add_argument(
        "--novo",
        type=Path,
        required=True,
        help="Caminho para o catalogo.db da nova versão gerada.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Caminho do arquivo JSON de saída para salvar os deltas.",
    )
    parser.add_argument(
        "--sql",
        type=Path,
        default=None,
        help="Caminho opcional para salvar o comando SQL de inserção no D1.",
    )

    args = parser.parse_args()

    deltas = calcular_deltas_catalogo(args.anterior, args.novo)

    qtd_croquis_upsert = len(deltas["croquis"]["upserts"])
    qtd_croquis_delete = len(deltas["croquis"]["deletes"])
    qtd_vias_upsert = len(deltas["vias"]["upserts"])
    qtd_vias_delete = len(deltas["vias"]["deletes"])

    print("Deltas calculados:")
    print(f"  Croquis : {qtd_croquis_upsert} upserts, {qtd_croquis_delete} deletes")
    print(f"  Vias    : {qtd_vias_upsert} upserts, {qtd_vias_delete} deletes")

    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(deltas, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Salvo em: {args.saida}")

    if args.sql:
        args.sql.parent.mkdir(parents=True, exist_ok=True)
        sql_content = gerar_sql_insercao_delta_d1(deltas)
        args.sql.write_text(sql_content, encoding="utf-8")
        print(f"SQL salvo em: {args.sql}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
