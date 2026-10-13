# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração e sincronização do catálogo SQLite (catalogo.db).

Responsável por:
- Criar a estrutura e índices das tabelas catalogo_croquis e catalogo_aresta.
- Extrair metadados de croquis e escaladas a partir de arquivos Protobuf compilados.
- Inserir, atualizar ou remover croquis de forma atômica no banco de dados.
- Compactar o catálogo gerado em formato gzip (catalogo.db.gz).
- Suportar tanto compilação completa quanto deploy parcial incremental.
"""

from __future__ import annotations

import gzip
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any

from aresta_api.proto.generated import croqui_pb2


def inicializar_banco_catalogo(caminho_banco: Path | str) -> sqlite3.Connection:
    """
    Inicializa a conexão com o banco SQLite do catálogo e garante que a estrutura
    das tabelas e índices necessários existam.
    """
    caminho = Path(caminho_banco)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(str(caminho))
    cursor = conexao.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS catalogo_croquis (
            croqui_uid TEXT PRIMARY KEY,
            id_slug TEXT NOT NULL,
            nome TEXT NOT NULL,
            cidade TEXT,
            uf TEXT,
            atualizado_em INTEGER NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS catalogo_aresta (
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

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_catalogo_aresta_croqui
        ON catalogo_aresta(croqui_uid);
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_catalogo_aresta_nome
        ON catalogo_aresta(nome COLLATE NOCASE);
        """
    )

    conexao.commit()
    return conexao


def extrair_localidade_do_slug(id_slug: str) -> tuple[str, str]:
    """
    Extrai cidade e UF a partir do padrão de slug do Aresta (ex: br_mg_araxa_bocaina -> ('Araxa', 'MG')).
    """
    partes = id_slug.split("_")
    if len(partes) >= 3 and len(partes[0]) == 2 and len(partes[1]) == 2:
        uf = partes[1].upper()
        cidade = partes[2].replace("-", " ").title()
        return cidade, uf
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
        "via_multiplas_enfiadas": "multiplas_enfiadas",
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
            nome = croqui_pb2.GrauVia.GrauVia.Name(grau_val)
            if nome.startswith("BR_"):
                nome = nome[3:]
            return nome.replace("_BARRA_", "/").lower()

    elif qual_tipo == "boulder" and hasattr(dados_via, "dificuldade"):
        grau_val = dados_via.dificuldade
        if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauBoulder.GrauBoulder.values():
            nome = croqui_pb2.GrauBoulder.GrauBoulder.Name(grau_val)
            return nome.replace("_BARRA_", "/")

    elif qual_tipo == "via_multiplas_enfiadas":
        if getattr(dados_via, "dificuldade_maxima", 0):
            grau_val = dados_via.dificuldade_maxima
            if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauVia.GrauVia.values():
                nome = croqui_pb2.GrauVia.GrauVia.Name(grau_val)
                if nome.startswith("BR_"):
                    nome = nome[3:]
                return nome.replace("_BARRA_", "/").lower()
        elif getattr(dados_via, "dificuldade_media", 0):
            grau_val = dados_via.dificuldade_media
            if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauVia.GrauVia.values():
                nome = croqui_pb2.GrauVia.GrauVia.Name(grau_val)
                if nome.startswith("BR_"):
                    nome = nome[3:]
                return nome.replace("_BARRA_", "/").lower()

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
    Extrai as informações resumidas do croqui e a lista de vias para o catálogo.

    Retorna:
        tuple[dict[str, Any], list[dict[str, Any]]]:
            (dados_croqui, lista_de_vias)
    """
    id_slug = getattr(croqui, "id", "").strip() or id_fallback
    croqui_uid = getattr(croqui, "uid", "").strip() or id_slug
    nome = getattr(croqui, "nome", "").strip() or id_slug
    cidade, uf = extrair_localidade_do_slug(id_slug)
    atualizado_em = int(time.time())

    dados_croqui = {
        "croqui_uid": croqui_uid,
        "id_slug": id_slug,
        "nome": nome,
        "cidade": cidade,
        "uf": uf,
        "atualizado_em": atualizado_em,
    }

    vias: list[dict[str, Any]] = []

    for pico in croqui.picos:
        for setor_grupo in pico.setores_ou_grupos:
            setores = []
            if setor_grupo.HasField("setor"):
                setores.append(setor_grupo.setor)
            elif setor_grupo.HasField("grupo") and setor_grupo.grupo.HasField("conteudo"):
                setores.extend(setor_grupo.grupo.conteudo.setores)

            for setor_arq in setores:
                if not setor_arq.HasField("conteudo"):
                    continue
                setor_conteudo = setor_arq.conteudo
                setor_uid = (
                    getattr(setor_conteudo, "uid", "").strip()
                    or getattr(setor_arq, "uid", "").strip()
                )
                setor_nome = getattr(setor_conteudo, "nome", "").strip()

                for esc in setor_conteudo.escaladas:
                    tipo_via = esc.WhichOneof("tipo")
                    if not tipo_via:
                        continue

                    dados_via = getattr(esc, tipo_via)
                    nome_via = getattr(dados_via, "nome", "").strip()
                    uid_via = getattr(esc, "uid", "").strip()
                    grau_via = formatar_grau_escalada(esc)
                    tipo_amigavel = formatar_tipo_escalada(esc)

                    vias.append(
                        {
                            "uid": uid_via,
                            "croqui_uid": croqui_uid,
                            "nome": nome_via,
                            "grau": grau_via,
                            "tipo": tipo_amigavel,
                            "setor_nome": setor_nome,
                            "setor_uid": setor_uid,
                        }
                    )

    return dados_croqui, vias


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
    vias: list[dict[str, Any]],
) -> None:
    """
    Insere ou substitui os metadados do croqui e suas respectivas vias no banco SQLite.
    """
    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO catalogo_croquis (
            croqui_uid, id_slug, nome, cidade, uf, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            dados_croqui["croqui_uid"],
            dados_croqui["id_slug"],
            dados_croqui["nome"],
            dados_croqui.get("cidade", ""),
            dados_croqui.get("uf", ""),
            dados_croqui["atualizado_em"],
        ),
    )

    for via in vias:
        cursor.execute(
            """
            INSERT OR REPLACE INTO catalogo_aresta (
                uid, croqui_uid, nome, grau, tipo, setor_nome, setor_uid
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                via["uid"],
                via["croqui_uid"],
                via["nome"],
                via.get("grau", ""),
                via.get("tipo", ""),
                via.get("setor_nome", ""),
                via.get("setor_uid", ""),
            ),
        )
    conexao.commit()


def compactar_catalogo_gzip(caminho_db: Path | str, caminho_gz: Path | str | None = None) -> Path:
    """
    Compacta o arquivo catalogo.db gerando catalogo.db.gz.
    """
    caminho_origem = Path(caminho_db)
    if caminho_gz is None:
        caminho_destino = caminho_origem.with_suffix(".db.gz")
    else:
        caminho_destino = Path(caminho_gz)

    with (
        open(caminho_origem, "rb") as f_in,
        gzip.open(caminho_destino, "wb", compresslevel=9) as f_out,
    ):
        shutil.copyfileobj(f_in, f_out)

    return caminho_destino


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

                dados_croqui, vias = extrair_dados_croqui_para_catalogo(
                    croqui, id_fallback=pasta.name
                )

                # Se estamos atualizando, remove a versão anterior deste croqui
                remover_croqui_do_catalogo(conexao, dados_croqui["croqui_uid"])
                inserir_croqui_no_catalogo(conexao, dados_croqui, vias)

    finally:
        conexao.close()

    return caminho_db
