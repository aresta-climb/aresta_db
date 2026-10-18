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

import csv
import hashlib
import io
import sqlite3
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
    precisa_ddl = False

    # Detecta se a tabela catalogo_croquis existe com schema legado
    cursor.execute("PRAGMA table_info(catalogo_croquis)")
    colunas_croquis = [linha[1] for linha in cursor.fetchall()]
    if colunas_croquis and "estado" not in colunas_croquis:
        cursor.execute("DROP TABLE catalogo_croquis")
        precisa_ddl = True
    elif colunas_croquis and "atualizado_em" in colunas_croquis:
        cursor.execute("ALTER TABLE catalogo_croquis DROP COLUMN atualizado_em")
        conexao.commit()

    # Detecta se a tabela catalogo_aresta existe com schema legado (sem a coluna escalada_tipo)
    cursor.execute("PRAGMA table_info(catalogo_aresta)")
    colunas_existentes = [linha[1] for linha in cursor.fetchall()]
    if colunas_existentes and "escalada_tipo" not in colunas_existentes:
        cursor.execute("DROP TABLE catalogo_aresta")
        precisa_ddl = True

    cursor.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'index')")
    objetos_existentes = {linha[0] for linha in cursor.fetchall()}
    objetos_esperados = {
        "catalogo_croquis",
        "catalogo_aresta",
        "catalogo_meta",
        "idx_catalogo_aresta_croqui",
        "idx_catalogo_aresta_nome",
        "idx_catalogo_aresta_tipo",
    }
    if not objetos_esperados.issubset(objetos_existentes):
        precisa_ddl = True

    if precisa_ddl:
        for comando_ddl in COMANDOS_DDL:
            cursor.execute(comando_ddl)
        conexao.commit()

    return conexao


_PREFIXOS_CIDADES_CONHECIDOS: tuple[tuple[str, str], ...] = (
    ("conceicao_do_mato_dentro", "Conceição do Mato Dentro"),
    ("nova_friburgobom_jardim", "Nova Friburgo / Bom Jardim"),
    ("sao_thome_das_letras", "São Thomé das Letras"),
    ("santana_do_paraiso", "Santana do Paraíso"),
    ("santana_do_riacho", "Santana do Riacho"),
    ("sao_joao_del_rei", "São João del-Rei"),
    ("barao_de_cocais", "Barão de Cocais"),
    ("pocos_de_caldas", "Poços de Caldas"),
    ("pedro_leopoldo", "Pedro Leopoldo"),
    ("ipatinga_ipaba", "Ipatinga / Ipaba"),
    ("montes_claros", "Montes Claros"),
    ("paraisopolis", "Paraisópolis"),
    ("lagoa_santa", "Lagoa Santa"),
    ("milho_verde", "Milho Verde"),
    ("passa_vinte", "Passa Vinte"),
    ("santa_luzia", "Santa Luzia"),
    ("sete_lagoas", "Sete Lagoas"),
    ("ouro_preto", "Ouro Preto"),
    ("januaria", "Januária"),
    ("igarape", "Igarapé"),
    ("sabara", "Sabará"),
    ("araxa", "Araxá"),
    ("caete", "Caeté"),
    ("unai", "Unaí"),
)


def extrair_localidade_do_slug(id_slug: str) -> tuple[str, str]:
    """
    Extrai cidade e estado a partir do padrão de slug do Aresta
    (ex: br_mg_pedro_leopoldo_gruta_do_bau -> ('Pedro Leopoldo', 'MG')).
    """
    partes = id_slug.split("_")
    if len(partes) >= 3 and len(partes[0]) == 2 and len(partes[1]) == 2:
        estado = partes[1].upper()
        restante = "_".join(partes[2:]).lower()
        for prefixo, nome_cidade in _PREFIXOS_CIDADES_CONHECIDOS:
            if restante == prefixo or restante.startswith(f"{prefixo}_"):
                return nome_cidade, estado
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
    cidade_slug, estado_slug = extrair_localidade_do_slug(id_slug)

    primeiro_pico = croqui.picos[0] if len(getattr(croqui, "picos", ())) > 0 else None
    cidade_pico = getattr(primeiro_pico, "cidade", "").strip() if primeiro_pico is not None else ""
    estado_pico = getattr(primeiro_pico, "estado", "").strip() if primeiro_pico is not None else ""

    cidade = cidade_pico or cidade_slug
    estado = (
        estado_pico.upper()
        if len(estado_pico) == 2
        else (estado_slug or estado_pico)
    )

    dados_croqui: LinhaCatalogoCroquis = {
        "croqui_uid": croqui_uid,
        "id_slug": id_slug,
        "nome": nome,
        "cidade": cidade,
        "estado": estado,
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


def remover_croqui_do_catalogo(
    conexao: sqlite3.Connection,
    croqui_uid: str,
    id_slug: str | None = None,
) -> None:
    """
    Remove todos os registros pertencentes a um determinado croqui_uid (e opcionalmente
    qualquer registro legado/órfão associado ao mesmo id_slug) do catálogo.
    """
    cursor = conexao.cursor()
    uids_para_remover = {croqui_uid}
    if id_slug:
        for (uid_existente,) in cursor.execute(
            "SELECT croqui_uid FROM catalogo_croquis WHERE id_slug = ?",
            (id_slug,),
        ).fetchall():
            uids_para_remover.add(uid_existente)

    for uid_alvo in sorted(uids_para_remover):
        cursor.execute("DELETE FROM catalogo_croquis WHERE croqui_uid = ?", (uid_alvo,))
        cursor.execute("DELETE FROM catalogo_aresta WHERE croqui_uid = ?", (uid_alvo,))
    if id_slug:
        cursor.execute("DELETE FROM catalogo_croquis WHERE id_slug = ?", (id_slug,))
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
            croqui_uid, id_slug, nome, cidade, estado
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            dados_croqui["croqui_uid"],
            dados_croqui["id_slug"],
            dados_croqui["nome"],
            dados_croqui.get("cidade", ""),
            dados_croqui.get("estado", ""),
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


def _croqui_modificado_no_catalogo(
    conexao: sqlite3.Connection,
    dados_croqui: dict[str, Any],
    registros_aresta: list[dict[str, Any]],
) -> bool:
    """
    Verifica se os dados lógicos do croqui ou de suas entidades em catalogo_aresta
    diferem do que já está persistido no banco SQLite para este croqui_uid.
    """
    croqui_uid = dados_croqui["croqui_uid"]
    cursor = conexao.cursor()
    linha_croqui = cursor.execute(
        "SELECT croqui_uid, id_slug, nome, cidade, estado "
        "FROM catalogo_croquis WHERE croqui_uid = ?",
        (croqui_uid,),
    ).fetchone()

    tupla_esperada_croqui = (
        croqui_uid,
        dados_croqui["id_slug"],
        dados_croqui["nome"],
        dados_croqui.get("cidade", ""),
        dados_croqui.get("estado", ""),
    )
    if linha_croqui != tupla_esperada_croqui:
        return True

    linhas_aresta_atuais = cursor.execute(
        "SELECT uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid "
        "FROM catalogo_aresta WHERE croqui_uid = ? ORDER BY uid",
        (croqui_uid,),
    ).fetchall()

    mapa_esperado = {
        reg["uid"]: (
            reg["uid"],
            reg["tipo"],
            reg["croqui_uid"],
            reg["nome"],
            reg.get("escalada_grau"),
            reg.get("escalada_tipo"),
            reg.get("setor_uid"),
            reg.get("grupo_uid"),
        )
        for reg in registros_aresta
    }
    linhas_aresta_esperadas = [mapa_esperado[uid] for uid in sorted(mapa_esperado)]
    return linhas_aresta_atuais != linhas_aresta_esperadas


def gerar_catalogo_completo(
    diretorio_gerados: Path | str,
    caminho_saida_db: Path | str,
    alvos: list[str] | None = None,
    ids_permitidos: set[str] | list[str] | None = None,
    apenas_publicados: bool = True,
) -> Path:
    """
    Gera ou atualiza incrementalmente o catálogo SQLite a partir dos compilado.binarypb,
    garantindo paridade 1:1 com os croquis permitidos no índice ativo e ignorando
    ou removendo croquis marcados como rascunho (publicar_croqui == False).

    Args:
        diretorio_gerados: Diretório onde os croquis compilados estão salvos (ex: generated/).
        caminho_saida_db: Caminho final do arquivo catalogo.db.
        alvos: Lista de IDs de croquis específicos para deploy parcial. Se None, processa todos.
        ids_permitidos: Conjunto/lista opcional de id_slugs que compõem o indice.binarypb.
            Quando informado, garante que todos os ids_permitidos estejam catalogados e
            expurga quaisquer croquis cujo id_slug não pertença a ids_permitidos.
        apenas_publicados: Se True (padrão), ignora e remove do catálogo croquis que
            possuam publicar_croqui == False no protobuf.

    Returns:
        Path: Caminho do banco gerado.
    """
    pasta_base = Path(diretorio_gerados)
    caminho_db = Path(caminho_saida_db)

    conexao = inicializar_banco_catalogo(caminho_db)

    try:
        conjunto_permitidos = set(ids_permitidos) if ids_permitidos is not None else None

        if alvos is not None:
            alvos_efetivos = list(dict.fromkeys(alvos))
            if conjunto_permitidos is not None:
                slugs_no_banco = {
                    linha[0]
                    for linha in conexao.execute("SELECT id_slug FROM catalogo_croquis").fetchall()
                }
                for id_perm in sorted(conjunto_permitidos - slugs_no_banco):
                    if id_perm not in alvos_efetivos:
                        alvos_efetivos.append(id_perm)
            pastas_alvo = [pasta_base / a for a in alvos_efetivos]
        elif conjunto_permitidos is not None:
            pastas_alvo = [
                pasta_base / a
                for a in sorted(conjunto_permitidos)
                if (pasta_base / a / "compilado.binarypb").exists()
            ]
        else:
            # Seleciona todas as subpastas que possuem compilado.binarypb
            pastas_alvo = [
                p
                for p in pasta_base.iterdir()
                if p.is_dir() and (p / "compilado.binarypb").exists()
            ]

        houve_alteracao = False
        uids_processados: set[str] = set()

        for pasta in pastas_alvo:
            arquivo_pb = pasta / "compilado.binarypb"
            if not arquivo_pb.exists():
                continue

            croqui = croqui_pb2.Croqui()
            croqui.ParseFromString(arquivo_pb.read_bytes())

            dados_croqui, registros_aresta = extrair_dados_croqui_para_catalogo(
                croqui, id_fallback=pasta.name
            )
            croqui_uid = dados_croqui["croqui_uid"]
            id_slug = dados_croqui["id_slug"]

            if apenas_publicados and not croqui.publicar_croqui:
                estava_no_banco = bool(
                    conexao.execute(
                        "SELECT 1 FROM catalogo_croquis WHERE croqui_uid = ? OR id_slug = ?",
                        (croqui_uid, id_slug),
                    ).fetchone()
                )
                if estava_no_banco:
                    remover_croqui_do_catalogo(conexao, croqui_uid, id_slug=id_slug)
                    houve_alteracao = True
                continue

            uids_processados.add(croqui_uid)

            uids_mesmo_slug = {
                r[0]
                for r in conexao.execute(
                    "SELECT croqui_uid FROM catalogo_croquis WHERE id_slug = ?",
                    (id_slug,),
                ).fetchall()
            }
            tem_uid_antigo_mesmo_slug = bool(uids_mesmo_slug - {croqui_uid})

            if tem_uid_antigo_mesmo_slug or _croqui_modificado_no_catalogo(
                conexao, dados_croqui, registros_aresta
            ):
                remover_croqui_do_catalogo(conexao, croqui_uid, id_slug=id_slug)
                inserir_croqui_no_catalogo(conexao, dados_croqui, registros_aresta)
                houve_alteracao = True

        if conjunto_permitidos is not None:
            linhas_existentes = conexao.execute(
                "SELECT croqui_uid, id_slug FROM catalogo_croquis"
            ).fetchall()
            for uid_existente, slug_existente in linhas_existentes:
                if slug_existente not in conjunto_permitidos:
                    remover_croqui_do_catalogo(conexao, uid_existente, id_slug=slug_existente)
                    houve_alteracao = True

        if alvos is None:
            uids_existentes = {
                linha[0]
                for linha in conexao.execute("SELECT croqui_uid FROM catalogo_croquis").fetchall()
            }
            for uid_orfao in sorted(uids_existentes - uids_processados):
                remover_croqui_do_catalogo(conexao, uid_orfao)
                houve_alteracao = True

        orfaos_aresta = conexao.execute(
            "SELECT COUNT(*) FROM catalogo_aresta "
            "WHERE croqui_uid NOT IN (SELECT croqui_uid FROM catalogo_croquis)"
        ).fetchone()[0]
        if orfaos_aresta > 0:
            conexao.execute(
                "DELETE FROM catalogo_aresta "
                "WHERE croqui_uid NOT IN (SELECT croqui_uid FROM catalogo_croquis)"
            )
            conexao.commit()
            houve_alteracao = True

        tem_versao = (
            conexao.execute(
                "SELECT valor FROM catalogo_meta WHERE chave = 'versao_catalogo'"
            ).fetchone()
            is not None
        )
        if houve_alteracao or not tem_versao:
            calcular_versao_catalogo(conexao)

        pasta_saida_csv = caminho_db.parent
        csvs_existem = all(
            (pasta_saida_csv / nome_csv).is_file()
            for nome_csv in (
                "catalogo_croquis.csv",
                "catalogo_aresta.csv",
                "catalogo_meta.csv",
            )
        )
        if houve_alteracao or not tem_versao or not csvs_existem:
            exportar_catalogo_csv(conexao, pasta_saida_csv)

    finally:
        conexao.close()

    return caminho_db


def exportar_catalogo_csv(
    conexao: sqlite3.Connection,
    diretorio_saida: Path | str,
) -> None:
    """
    Exporta as 3 tabelas do catálogo SQLite para arquivos CSV determinísticos (UTF-8, LF):
    - catalogo_croquis.csv (ordenado por id_slug, croqui_uid, sem atualizado_em)
    - catalogo_aresta.csv (ordenado por croqui_uid, uid)
    - catalogo_meta.csv (ordenado por chave)
    """
    pasta = Path(diretorio_saida)
    cursor = conexao.cursor()

    especificacoes = (
        (
            "catalogo_croquis.csv",
            ("croqui_uid", "id_slug", "nome", "cidade", "estado"),
            "SELECT croqui_uid, id_slug, nome, cidade, estado "
            "FROM catalogo_croquis ORDER BY id_slug, croqui_uid",
        ),
        (
            "catalogo_aresta.csv",
            (
                "uid",
                "tipo",
                "croqui_uid",
                "nome",
                "escalada_grau",
                "escalada_tipo",
                "setor_uid",
                "grupo_uid",
            ),
            "SELECT uid, tipo, croqui_uid, nome, escalada_grau, escalada_tipo, setor_uid, grupo_uid "
            "FROM catalogo_aresta ORDER BY croqui_uid, uid",
        ),
        (
            "catalogo_meta.csv",
            ("chave", "valor"),
            "SELECT chave, valor FROM catalogo_meta ORDER BY chave",
        ),
    )

    for nome_arquivo, cabecalho, consulta_sql in especificacoes:
        buffer = io.StringIO()
        escritor = csv.writer(buffer, lineterminator="\n")
        escritor.writerow(cabecalho)
        for linha in cursor.execute(consulta_sql):
            escritor.writerow(["" if val is None else val for val in linha])

        conteudo = buffer.getvalue()
        caminho_csv = pasta / nome_arquivo
        if not caminho_csv.is_file() or caminho_csv.read_text(encoding="utf-8") != conteudo:
            caminho_csv.write_text(conteudo, encoding="utf-8", newline="\n")


