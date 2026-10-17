# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração e sincronização do catálogo SQLite (catalogo.db).

Responsável por:
- Criar a estrutura e índices das tabelas catalogo_croquis, catalogo_aresta e catalogo_meta.
- Detectar e migrar automaticamente o schema de catalogo_aresta para a versão normalizada por UID.
- Extrair metadados de croquis, botões, grupos, setores e escaladas a partir de arquivos Protobuf compilados.
- Inserir, atualizar ou remover croquis de forma atômica no banco de dados.
- Suportar tanto compilação completa quanto deploy parcial incremental.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any

from aresta_api.sql.generated.python.catalogo_sql import (
    COMANDOS_DDL,
    LinhaCatalogoAresta,
    LinhaCatalogoCroquis,
)

try:
    from aresta_api.proto.generated import croqui_pb2
except ImportError:  # pragma: no cover
    croqui_pb2 = None  # type: ignore[assignment]


def inicializar_banco_catalogo(caminho_banco: Path | str) -> sqlite3.Connection:
    """
    Inicializa a conexão com o banco SQLite do catálogo e garante que a estrutura
    das tabelas e índices necessários existam, migrando automaticamente schemas legados.
    """
    caminho = Path(caminho_banco)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(str(caminho))
    cursor = conexao.cursor()

    # Detecta se a tabela catalogo_croquis existe com schema legado (sem a coluna estado)
    cursor.execute("PRAGMA table_info(catalogo_croquis)")
    colunas_croquis = [linha[1] for linha in cursor.fetchall()]
    if colunas_croquis and "estado" not in colunas_croquis:
        cursor.execute("DROP TABLE catalogo_croquis")

    # Detecta se a tabela catalogo_aresta existe com schema legado (sem a coluna escalada_tipo)
    cursor.execute("PRAGMA table_info(catalogo_aresta)")
    colunas_existentes = [linha[1] for linha in cursor.fetchall()]
    if colunas_existentes and "escalada_tipo" not in colunas_existentes:
        cursor.execute("DROP TABLE catalogo_aresta")

    for comando_ddl in COMANDOS_DDL:
        cursor.execute(comando_ddl)

    conexao.commit()
    return conexao


def extrair_localidade_do_slug(id_slug: str) -> tuple[str, str]:
    """
    Extrai cidade e estado a partir do padrão de slug do Aresta (ex: br_mg_araxa_bocaina -> ('Araxa', 'MG')).
    """
    partes = id_slug.split("_")
    if len(partes) >= 3 and len(partes[0]) == 2 and len(partes[1]) == 2:
        estado = partes[1].upper()
        cidade = partes[2].replace("-", " ").title()
        return cidade, estado
    return "", ""


def formatar_tipo_escalada(escalada: croqui_pb2.Escalada) -> str:
    """
    Retorna uma string amigável para o tipo de escalada baseado no oneof 'tipo'.
    """
    qual_tipo = escalada.WhichOneof("tipo")
    if not qual_tipo:
        return ""

    mapeamento = {
        "via_esportiva": "esportiva",
        "via_movel": "tradicional",
        "boulder": "boulder",
        "via_multiplas_enfiadas": "multienfiada",
        "highline": "highline",
    }
    return mapeamento.get(qual_tipo, qual_tipo)


def formatar_grau_escalada(escalada: croqui_pb2.Escalada) -> str:
    """
    Extrai e formata a graduação de uma escalada para exibição textual no catálogo.
    """
    qual_tipo = escalada.WhichOneof("tipo")
    if not qual_tipo:
        return ""

    dados_via = getattr(escalada, qual_tipo)

    if qual_tipo in ("via_esportiva", "via_movel") and hasattr(dados_via, "dificuldade"):
        grau_val = dados_via.dificuldade
        if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauVia.GrauVia.values():
            nome = str(croqui_pb2.GrauVia.GrauVia.Name(grau_val))
            if nome.startswith("BR_"):
                nome = nome[3:]
            return str(nome.replace("_BARRA_", "/").lower())

    elif qual_tipo == "boulder" and hasattr(dados_via, "dificuldade"):
        grau_val = dados_via.dificuldade
        if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauBoulder.GrauBoulder.values():
            nome = str(croqui_pb2.GrauBoulder.GrauBoulder.Name(grau_val))
            return str(nome.replace("_BARRA_", "/"))

    elif qual_tipo == "via_multiplas_enfiadas":
        if getattr(dados_via, "dificuldade_maxima", 0):
            grau_val = dados_via.dificuldade_maxima
            if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauVia.GrauVia.values():
                nome = str(croqui_pb2.GrauVia.GrauVia.Name(grau_val))
                if nome.startswith("BR_"):
                    nome = nome[3:]
                return str(nome.replace("_BARRA_", "/").lower())
        elif getattr(dados_via, "dificuldade_media", 0):
            grau_val = dados_via.dificuldade_media
            if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauVia.GrauVia.values():
                nome = str(croqui_pb2.GrauVia.GrauVia.Name(grau_val))
                if nome.startswith("BR_"):
                    nome = nome[3:]
                return str(nome.replace("_BARRA_", "/").lower())

    elif qual_tipo == "highline":
        distancia = getattr(dados_via, "distancia", 0)
        if distancia > 0:
            return f"{distancia}m"

    return ""


def extrair_dados_croqui_para_catalogo(
    croqui: croqui_pb2.Croqui,
    id_fallback: str = "",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Extrai as informações resumidas do croqui e todos os registros normalizados
    endereçáveis por UID (botões, grupos, setores e escaladas) para catalogo_aresta.

    Retorna:
        tuple[dict[str, Any], list[dict[str, Any]]]:
            (dados_croqui, registros_aresta)
    """
    id_slug = getattr(croqui, "id", "").strip() or id_fallback
    croqui_uid = getattr(croqui, "uid", "").strip() or id_slug
    nome = getattr(croqui, "nome", "").strip() or id_slug
    cidade, estado = extrair_localidade_do_slug(id_slug)
    atualizado_em = int(time.time())

    dados_croqui: LinhaCatalogoCroquis = {
        "croqui_uid": croqui_uid,
        "id_slug": id_slug,
        "nome": nome,
        "cidade": cidade,
        "estado": estado,
        "atualizado_em": atualizado_em,
    }

    registros: list[LinhaCatalogoAresta] = []

    # 1. Extração de Botões do croqui
    for botao in getattr(croqui, "botoes", []):
        b_uid = getattr(botao, "uid", "").strip()
        if not b_uid:
            continue
        registros.append(
            {
                "uid": b_uid,
                "tipo": "botao",
                "croqui_uid": croqui_uid,
                "nome": getattr(botao, "texto", "").strip(),
                "escalada_grau": None,
                "escalada_tipo": None,
                "setor_uid": None,
                "grupo_uid": None,
            }
        )

    def _processar_setor(setor_arq: Any, grupo_uid: str | None) -> None:
        if not setor_arq.HasField("conteudo"):
            return
        setor_conteudo = setor_arq.conteudo
        s_uid = getattr(setor_conteudo, "uid", "").strip() or getattr(setor_arq, "uid", "").strip()
        s_nome = getattr(setor_conteudo, "nome", "").strip()

        if s_uid:
            registros.append(
                {
                    "uid": s_uid,
                    "tipo": "setor",
                    "croqui_uid": croqui_uid,
                    "nome": s_nome,
                    "escalada_grau": None,
                    "escalada_tipo": None,
                    "setor_uid": None,
                    "grupo_uid": grupo_uid,
                }
            )

        for esc in setor_conteudo.escaladas:
            tipo_via = esc.WhichOneof("tipo")
            if not tipo_via:
                continue

            dados_via = getattr(esc, tipo_via)
            nome_via = getattr(dados_via, "nome", "").strip()
            uid_via = getattr(esc, "uid", "").strip()
            if not uid_via:
                continue

            grau_via = formatar_grau_escalada(esc)
            tipo_amigavel = formatar_tipo_escalada(esc)

            registros.append(
                {
                    "uid": uid_via,
                    "tipo": "escalada",
                    "croqui_uid": croqui_uid,
                    "nome": nome_via,
                    "escalada_grau": grau_via,
                    "escalada_tipo": tipo_amigavel,
                    "setor_uid": s_uid or None,
                    "grupo_uid": grupo_uid,
                }
            )

    # 2. Extração de Grupos, Setores e Escaladas por Pico
    for pico in getattr(croqui, "picos", []):
        for setor_grupo in pico.setores_ou_grupos:
            if setor_grupo.HasField("grupo") and setor_grupo.grupo.HasField("conteudo"):
                grupo_conteudo = setor_grupo.grupo.conteudo
                g_uid = (
                    getattr(grupo_conteudo, "uid", "").strip()
                    or getattr(setor_grupo.grupo, "uid", "").strip()
                )
                g_nome = getattr(grupo_conteudo, "nome", "").strip()

                if g_uid:
                    registros.append(
                        {
                            "uid": g_uid,
                            "tipo": "grupo",
                            "croqui_uid": croqui_uid,
                            "nome": g_nome,
                            "escalada_grau": None,
                            "escalada_tipo": None,
                            "setor_uid": None,
                            "grupo_uid": None,
                        }
                    )

                for setor_arq in grupo_conteudo.setores:
                    _processar_setor(setor_arq, grupo_uid=g_uid or None)

            elif setor_grupo.HasField("setor"):
                _processar_setor(setor_grupo.setor, grupo_uid=None)

    return dict(dados_croqui), [dict(r) for r in registros]


def remover_croqui_do_catalogo(conexao: sqlite3.Connection, croqui_uid: str) -> None:
    """
    Remove todos os registros pertencentes a um determinado croqui_uid do catálogo.
    """
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM catalogo_croquis WHERE croqui_uid = ?", (croqui_uid,))
    cursor.execute("DELETE FROM catalogo_aresta WHERE croqui_uid = ?", (croqui_uid,))
    conexao.commit()


def inserir_croqui_no_catalogo(
    conexao: sqlite3.Connection,
    dados_croqui: dict[str, Any],
    registros_aresta: list[dict[str, Any]],
) -> None:
    """
    Insere ou substitui os metadados do croqui e suas entidades de catalogo_aresta no banco SQLite.
    """
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO catalogo_croquis (
            croqui_uid, id_slug, nome, cidade, estado, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            dados_croqui["croqui_uid"],
            dados_croqui["id_slug"],
            dados_croqui["nome"],
            dados_croqui.get("cidade", ""),
            dados_croqui.get("estado", ""),
            dados_croqui["atualizado_em"],
        ),
    )

    for reg in registros_aresta:
        cursor.execute(
            """
            INSERT OR REPLACE INTO catalogo_aresta (
                uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reg["uid"],
                reg["tipo"],
                reg["croqui_uid"],
                reg["nome"],
                reg.get("escalada_grau"),
                reg.get("escalada_tipo"),
                reg.get("setor_uid"),
                reg.get("grupo_uid"),
            ),
        )
    conexao.commit()


def calcular_versao_catalogo(conexao: sqlite3.Connection) -> str:
    """
    Calcula o hash lógico determinístico (SHA-256 curto de 16 caracteres) sobre o
    conteúdo ordenado de catalogo_croquis e catalogo_aresta e o persiste em catalogo_meta.
    """
    cursor = conexao.cursor()
    hasher = hashlib.sha256()

    for linha in cursor.execute(
        "SELECT croqui_uid, id_slug, nome, cidade, estado FROM catalogo_croquis ORDER BY croqui_uid"
    ):
        hasher.update(repr(linha).encode("utf-8"))

    for linha in cursor.execute(
        "SELECT uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid "
        "FROM catalogo_aresta ORDER BY uid"
    ):
        hasher.update(repr(linha).encode("utf-8"))

    versao_hash = hasher.hexdigest()[:16]
    cursor.execute(
        "INSERT OR REPLACE INTO catalogo_meta (chave, valor) VALUES ('versao_catalogo', ?)",
        (versao_hash,),
    )
    conexao.commit()
    return versao_hash


def obter_versao_catalogo(caminho_db: Path | str) -> str:
    """
    Lê a versao_catalogo persistida em catalogo_meta ou calcula-a caso ainda não exista.
    Retorna string vazia se o arquivo de banco não existir.
    """
    caminho = Path(caminho_db)
    if not caminho.exists():
        return ""

    conexao = inicializar_banco_catalogo(caminho)
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM catalogo_meta WHERE chave = 'versao_catalogo'")
        linha = cursor.fetchone()
        if linha and linha[0]:
            return str(linha[0])
        return calcular_versao_catalogo(conexao)
    finally:
        conexao.close()


def gerar_catalogo_completo(
    diretorio_gerados: Path | str,
    caminho_saida_db: Path | str,
    alvos: list[str] | None = None,
) -> Path:
    """
    Gera ou atualiza incrementalmente o catálogo SQLite a partir dos compilado.binarypb.

    Args:
        diretorio_gerados: Diretório onde os croquis compilados estão salvos (ex: generated/).
        caminho_saida_db: Caminho final do arquivo catalogo.db.
        alvos: Lista de IDs de croquis específicos para deploy parcial. Se None, processa todos.

    Returns:
        Path: Caminho do banco gerado.
    """
    pasta_base = Path(diretorio_gerados)
    caminho_db = Path(caminho_saida_db)

    conexao = inicializar_banco_catalogo(caminho_db)

    try:
        if alvos is not None:
            pastas_alvo = [pasta_base / a for a in alvos]
        else:
            # Seleciona todas as subpastas que possuem compilado.binarypb
            pastas_alvo = [
                p
                for p in pasta_base.iterdir()
                if p.is_dir() and (p / "compilado.binarypb").exists()
            ]

        with conexao:
            for pasta in pastas_alvo:
                arquivo_pb = pasta / "compilado.binarypb"
                if not arquivo_pb.exists():
                    continue

                croqui = croqui_pb2.Croqui()
                croqui.ParseFromString(arquivo_pb.read_bytes())

                dados_croqui, registros_aresta = extrair_dados_croqui_para_catalogo(
                    croqui, id_fallback=pasta.name
                )

                # Se estamos atualizando, remove a versão anterior deste croqui
                remover_croqui_do_catalogo(conexao, dados_croqui["croqui_uid"])
                inserir_croqui_no_catalogo(conexao, dados_croqui, registros_aresta)

            calcular_versao_catalogo(conexao)

    finally:
        conexao.close()

    return caminho_db
