# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para scripts/gerar_catalogo_sqlite_lib.py."""

import gzip
import sqlite3
from pathlib import Path

from aresta_api.proto.generated import croqui_pb2
from scripts.gerar_catalogo_sqlite_lib import (
    compactar_catalogo_gzip,
    extrair_dados_croqui_para_catalogo,
    extrair_localidade_do_slug,
    formatar_grau_escalada,
    formatar_tipo_escalada,
    gerar_catalogo_completo,
    inicializar_banco_catalogo,
    inserir_croqui_no_catalogo,
    remover_croqui_do_catalogo,
)


def _criar_croqui_exemplo() -> croqui_pb2.Croqui:
    """Cria um Croqui protobuf de exemplo com vias e setores para testes."""
    croqui = croqui_pb2.Croqui()
    croqui.uid = "croqui12345678"
    croqui.id = "br_mg_ferros_pico_dos_ferros"
    croqui.nome = "Pico dos Ferros"

    pico = croqui.picos.add()
    pico.nome = "Pico dos Ferros"

    # Setor 1: Grupo com setores
    setor_ou_grupo_1 = pico.setores_ou_grupos.add()
    setor_1 = setor_ou_grupo_1.setor
    setor_conteudo_1 = setor_1.conteudo
    setor_conteudo_1.uid = "setor_cachoeir"
    setor_conteudo_1.nome = "Cachoeira"

    # Via Esportiva
    esc1 = setor_conteudo_1.escaladas.add()
    esc1.uid = "via_pe_na_chap"
    esc1.via_esportiva.nome = "Pé na Chapa"
    esc1.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A

    # Via Móvel (Tradicional)
    esc2 = setor_conteudo_1.escaladas.add()
    esc2.uid = "via_fissura_br"
    esc2.via_movel.nome = "Fissura Branca"
    esc2.via_movel.dificuldade = croqui_pb2.GrauVia.BR_6SUP

    # Setor 2: Dentro de um Grupo
    setor_ou_grupo_2 = pico.setores_ou_grupos.add()
    grupo = setor_ou_grupo_2.grupo
    setor_2 = grupo.conteudo.setores.add()
    setor_conteudo_2 = setor_2.conteudo
    setor_conteudo_2.uid = "setor_boulders"
    setor_conteudo_2.nome = "Boulders da Entrada"

    # Boulder
    esc3 = setor_conteudo_2.escaladas.add()
    esc3.uid = "boulder_dinamo"
    esc3.boulder.nome = "Dinâmico Monstro"
    esc3.boulder.dificuldade = croqui_pb2.GrauBoulder.V5

    # Multiplas enfiadas
    esc4 = setor_conteudo_2.escaladas.add()
    esc4.uid = "multiplas_fura"
    esc4.via_multiplas_enfiadas.nome = "Furacão"
    esc4.via_multiplas_enfiadas.dificuldade_maxima = croqui_pb2.GrauVia.BR_8A

    # Highline
    esc5 = setor_conteudo_2.escaladas.add()
    esc5.uid = "highline_teto"
    esc5.highline.nome = "Teto do Céu"
    esc5.highline.distancia = 120

    return croqui


def test_inicializar_banco_catalogo(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo.db"
    conexao = inicializar_banco_catalogo(caminho_db)

    cursor = conexao.cursor()
    # Verifica se as tabelas existem
    tabelas = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "catalogo_croquis" in tabelas
    assert "catalogo_aresta" in tabelas

    # Verifica os índices
    indices = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    }
    assert "idx_catalogo_aresta_croqui" in indices
    assert "idx_catalogo_aresta_nome" in indices

    conexao.close()


def test_extrair_localidade_do_slug() -> None:
    assert extrair_localidade_do_slug("br_mg_araxa_bocaina") == ("Araxa", "MG")
    assert extrair_localidade_do_slug("br_rj_rio-de-janeiro_urca") == ("Rio De Janeiro", "RJ")
    assert extrair_localidade_do_slug("slug_invalido") == ("", "")


def test_formatar_tipo_escalada() -> None:
    esc = croqui_pb2.Escalada()
    assert formatar_tipo_escalada(esc) == ""

    esc.via_esportiva.nome = "Teste"
    assert formatar_tipo_escalada(esc) == "esportiva"

    esc2 = croqui_pb2.Escalada()
    esc2.via_movel.nome = "Teste 2"
    assert formatar_tipo_escalada(esc2) == "tradicional"

    esc3 = croqui_pb2.Escalada()
    esc3.boulder.nome = "Boulder 1"
    assert formatar_tipo_escalada(esc3) == "boulder"

    esc4 = croqui_pb2.Escalada()
    esc4.via_multiplas_enfiadas.nome = "Multiplas 1"
    assert formatar_tipo_escalada(esc4) == "multiplas_enfiadas"

    esc5 = croqui_pb2.Escalada()
    esc5.highline.nome = "Highline 1"
    assert formatar_tipo_escalada(esc5) == "highline"


def test_formatar_grau_escalada() -> None:
    esc_esp = croqui_pb2.Escalada()
    esc_esp.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A
    assert formatar_grau_escalada(esc_esp) == "7a"

    esc_boulder = croqui_pb2.Escalada()
    esc_boulder.boulder.dificuldade = croqui_pb2.GrauBoulder.V5
    assert formatar_grau_escalada(esc_boulder) == "V5"

    esc_mult = croqui_pb2.Escalada()
    esc_mult.via_multiplas_enfiadas.dificuldade_media = croqui_pb2.GrauVia.BR_6SUP
    assert formatar_grau_escalada(esc_mult) == "6sup"

    esc_mult_max = croqui_pb2.Escalada()
    esc_mult_max.via_multiplas_enfiadas.dificuldade_maxima = croqui_pb2.GrauVia.BR_7B
    assert formatar_grau_escalada(esc_mult_max) == "7b"

    esc_high = croqui_pb2.Escalada()
    esc_high.highline.distancia = 80
    assert formatar_grau_escalada(esc_high) == "80m"

    esc_vazio = croqui_pb2.Escalada()
    assert formatar_grau_escalada(esc_vazio) == ""


def test_extrair_dados_croqui_para_catalogo() -> None:
    croqui = _criar_croqui_exemplo()
    dados_croqui, vias = extrair_dados_croqui_para_catalogo(croqui, "br_mg_ferros_pico_dos_ferros")

    assert dados_croqui["croqui_uid"] == "croqui12345678"
    assert dados_croqui["id_slug"] == "br_mg_ferros_pico_dos_ferros"
    assert dados_croqui["nome"] == "Pico dos Ferros"
    assert dados_croqui["cidade"] == "Ferros"
    assert dados_croqui["uf"] == "MG"
    assert isinstance(dados_croqui["atualizado_em"], int)

    assert len(vias) == 5

    via_esp = next(v for v in vias if v["uid"] == "via_pe_na_chap")
    assert via_esp["nome"] == "Pé na Chapa"
    assert via_esp["grau"] == "7a"
    assert via_esp["tipo"] == "esportiva"
    assert via_esp["setor_nome"] == "Cachoeira"
    assert via_esp["setor_uid"] == "setor_cachoeir"

    via_boulder = next(v for v in vias if v["uid"] == "boulder_dinamo")
    assert via_boulder["nome"] == "Dinâmico Monstro"
    assert via_boulder["grau"] == "V5"
    assert via_boulder["tipo"] == "boulder"
    assert via_boulder["setor_nome"] == "Boulders da Entrada"
    assert via_boulder["setor_uid"] == "setor_boulders"


def test_extrair_dados_croqui_fallback_id() -> None:
    croqui = croqui_pb2.Croqui()
    dados_croqui, vias = extrair_dados_croqui_para_catalogo(croqui, "fallback-slug")
    assert dados_croqui["croqui_uid"] == "fallback-slug"
    assert dados_croqui["id_slug"] == "fallback-slug"
    assert len(vias) == 0


def test_inserir_e_remover_croqui_no_catalogo(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo.db"
    conexao = inicializar_banco_catalogo(caminho_db)

    croqui = _criar_croqui_exemplo()
    dados_croqui, vias = extrair_dados_croqui_para_catalogo(croqui)

    inserir_croqui_no_catalogo(conexao, dados_croqui, vias)

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM catalogo_croquis WHERE croqui_uid = ?", ("croqui12345678",)
    )
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT COUNT(*) FROM catalogo_aresta WHERE croqui_uid = ?", ("croqui12345678",))
    assert cursor.fetchone()[0] == 5

    # Testa remoção seletiva
    remover_croqui_do_catalogo(conexao, "croqui12345678")

    cursor.execute(
        "SELECT COUNT(*) FROM catalogo_croquis WHERE croqui_uid = ?", ("croqui12345678",)
    )
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM catalogo_aresta WHERE croqui_uid = ?", ("croqui12345678",))
    assert cursor.fetchone()[0] == 0

    conexao.close()


def test_compactar_catalogo_gzip(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo.db"
    conexao = inicializar_banco_catalogo(caminho_db)
    conexao.close()

    caminho_gz = compactar_catalogo_gzip(caminho_db)
    assert caminho_gz.exists()
    assert caminho_gz.name == "catalogo.db.gz"

    with gzip.open(caminho_gz, "rb") as f:
        conteudo = f.read()
    assert len(conteudo) > 0


def test_gerar_catalogo_completo(tmp_path: Path) -> None:
    pasta_gerados = tmp_path / "generated"
    pasta_gerados.mkdir()

    # Cria dois croquis em pastas separadas
    croqui1 = _criar_croqui_exemplo()
    croqui1.uid = "croqui11111111"
    croqui1.id = "br_mg_ferros_croqui1"
    croqui1_dir = pasta_gerados / "br_mg_ferros_croqui1"
    croqui1_dir.mkdir()
    (croqui1_dir / "compilado.binarypb").write_bytes(croqui1.SerializeToString())

    croqui2 = _criar_croqui_exemplo()
    croqui2.uid = "croqui22222222"
    croqui2.id = "br_mg_araxa_croqui2"
    croqui2.nome = "Segundo Croqui"
    uid_counter = 0
    for pico in croqui2.picos:
        for sg in pico.setores_ou_grupos:
            setores = [sg.setor] if sg.HasField("setor") else list(sg.grupo.conteudo.setores)
            for s in setores:
                for esc in s.conteudo.escaladas:
                    esc.uid = f"c2_esc_{uid_counter}"
                    uid_counter += 1
    croqui2_dir = pasta_gerados / "br_mg_araxa_croqui2"
    croqui2_dir.mkdir()
    (croqui2_dir / "compilado.binarypb").write_bytes(croqui2.SerializeToString())

    caminho_db = pasta_gerados / "catalogo.db"

    # 1. Geração total
    res_db = gerar_catalogo_completo(pasta_gerados, caminho_db)
    assert res_db.exists()

    conexao = sqlite3.connect(caminho_db)
    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) FROM catalogo_croquis")
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT COUNT(*) FROM catalogo_aresta")
    assert cursor.fetchone()[0] == 10
    conexao.close()

    # 2. Deploy seletivo (apenas croqui-1 atualizado)
    croqui1.nome = "Pico dos Ferros Atualizado"
    (croqui1_dir / "compilado.binarypb").write_bytes(croqui1.SerializeToString())

    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["br_mg_ferros_croqui1"])

    conexao = sqlite3.connect(caminho_db)
    cursor = conexao.cursor()
    cursor.execute("SELECT nome FROM catalogo_croquis WHERE croqui_uid = 'croqui11111111'")
    assert cursor.fetchone()[0] == "Pico dos Ferros Atualizado"
    # Croqui 2 ainda deve estar lá
    cursor.execute("SELECT COUNT(*) FROM catalogo_croquis WHERE croqui_uid = 'croqui22222222'")
    assert cursor.fetchone()[0] == 1
    conexao.close()

    # 3. Alvo que não possui compilado.binarypb
    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["alvo_fantasma"])


def test_compactar_catalogo_gzip_caminho_customizado(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo.db"
    conexao = inicializar_banco_catalogo(caminho_db)
    conexao.close()

    caminho_custom = tmp_path / "customizado.db.gz"
    res = compactar_catalogo_gzip(caminho_db, caminho_custom)
    assert res == caminho_custom
    assert caminho_custom.exists()


def test_extrair_dados_setores_e_escaladas_incompletos() -> None:
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()

    # Setor sem conteudo
    sg1 = pico.setores_ou_grupos.add()
    sg1.setor.caminho = "setor_sem_conteudo.md"

    # Setor com escalada sem tipo definido
    sg2 = pico.setores_ou_grupos.add()
    s2 = sg2.setor.conteudo
    s2.nome = "Setor Incompleto"
    _ = s2.escaladas.add()

    dados_croqui, vias = extrair_dados_croqui_para_catalogo(croqui, "br_mg_bh_incompleto")
    assert dados_croqui["id_slug"] == "br_mg_bh_incompleto"
    assert len(vias) == 0


def test_formatar_grau_highline_zero() -> None:
    esc = croqui_pb2.Escalada()
    esc.highline.distancia = 0
    assert formatar_grau_escalada(esc) == ""
