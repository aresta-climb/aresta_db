# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para scripts/gerar_catalogo_sqlite_lib.py."""

import sqlite3
from pathlib import Path

from aresta_api.proto.generated import croqui_pb2
from scripts.gerar_catalogo_sqlite_lib import (
    calcular_versao_catalogo,
    extrair_dados_croqui_para_catalogo,
    extrair_localidade_do_slug,
    formatar_grau_escalada,
    formatar_tipo_escalada,
    gerar_catalogo_completo,
    inicializar_banco_catalogo,
    inserir_croqui_no_catalogo,
    obter_versao_catalogo,
    remover_croqui_do_catalogo,
)


def _criar_croqui_exemplo() -> croqui_pb2.Croqui:
    """Cria um Croqui protobuf de exemplo com botões, grupos, setores e vias para testes."""
    croqui = croqui_pb2.Croqui()
    croqui.uid = "croqui12345678"
    croqui.id = "br_mg_ferros_pico_dos_ferros"
    croqui.nome = "Pico dos Ferros"

    # Botão no croqui
    botao = croqui.botoes.add()
    botao.uid = "botao_pix_1234"
    botao.texto = "Chave Pix"

    pico = croqui.picos.add()
    pico.nome = "Pico dos Ferros"

    # Setor 1: Setor avulso (sem grupo)
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
    grupo.conteudo.uid = "grupo_boulders"
    grupo.conteudo.nome = "Setor dos Boulders"

    setor_2 = grupo.conteudo.setores.add()
    setor_conteudo_2 = setor_2.conteudo
    setor_conteudo_2.uid = "setor_boulders"
    setor_conteudo_2.nome = "Boulders da Entrada"

    # Boulder
    esc3 = setor_conteudo_2.escaladas.add()
    esc3.uid = "boulder_dinamo"
    esc3.boulder.nome = "Dinâmico Monstro"
    esc3.boulder.dificuldade = croqui_pb2.GrauBoulder.V5

    # Multiplas enfiadas (multienfiada)
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
    assert "catalogo_meta" in tabelas

    # Verifica os índices
    indices = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    }
    assert "idx_catalogo_aresta_croqui" in indices
    assert "idx_catalogo_aresta_nome" in indices
    assert "idx_catalogo_aresta_tipo" in indices

    # Verifica as colunas da tabela catalogo_croquis (sem atualizado_em)
    cursor.execute("PRAGMA table_info(catalogo_croquis)")
    colunas_croquis = [linha[1] for linha in cursor.fetchall()]
    assert colunas_croquis == [
        "croqui_uid",
        "id_slug",
        "nome",
        "cidade",
        "estado",
    ]

    # Verifica as colunas da tabela catalogo_aresta
    cursor.execute("PRAGMA table_info(catalogo_aresta)")
    colunas = [linha[1] for linha in cursor.fetchall()]
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

    conexao.close()


def test_migracao_automatica_schema_legado(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo_legado.db"
    conexao = sqlite3.connect(caminho_db)
    cursor = conexao.cursor()

    # Cria tabelas com schema legado (catalogo_croquis com uf e catalogo_aresta sem escalada_tipo)
    cursor.execute(
        """
        CREATE TABLE catalogo_croquis (
            croqui_uid TEXT PRIMARY KEY,
            id_slug TEXT NOT NULL,
            nome TEXT NOT NULL,
            cidade TEXT,
            uf TEXT,
            atualizado_em INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    cursor.execute(
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
    cursor.execute("INSERT INTO catalogo_croquis VALUES ('c1', 'slug', 'Pico', 'BH', 'MG', 0)")
    cursor.execute(
        "INSERT INTO catalogo_aresta VALUES ('v1', 'c1', 'Via', '6a', 'esp', 'S1', 's1')"
    )
    conexao.commit()
    conexao.close()

    # Chama inicializar_banco_catalogo para disparar migração automática
    conexao_migrada = inicializar_banco_catalogo(caminho_db)
    cursor_migrado = conexao_migrada.cursor()
    cursor_migrado.execute("PRAGMA table_info(catalogo_croquis)")
    colunas_croquis_migradas = [linha[1] for linha in cursor_migrado.fetchall()]
    assert "estado" in colunas_croquis_migradas
    assert "uf" not in colunas_croquis_migradas
    assert "atualizado_em" not in colunas_croquis_migradas

    cursor_migrado.execute("PRAGMA table_info(catalogo_aresta)")
    colunas_migradas = [linha[1] for linha in cursor_migrado.fetchall()]

    assert "escalada_tipo" in colunas_migradas
    assert "setor_nome" not in colunas_migradas
    conexao_migrada.close()


def test_migracao_automatica_remove_coluna_atualizado_em_preservando_dados(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo_com_atualizado_em.db"
    conexao = sqlite3.connect(caminho_db)
    conexao.execute(
        """
        CREATE TABLE catalogo_croquis (
            croqui_uid TEXT PRIMARY KEY,
            id_slug TEXT NOT NULL,
            nome TEXT NOT NULL,
            cidade TEXT,
            estado TEXT,
            atualizado_em INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conexao.execute("INSERT INTO catalogo_croquis VALUES ('c1', 'slug1', 'Pico 1', 'BH', 'MG', 99)")
    conexao.commit()
    conexao.close()

    conexao_migrada = inicializar_banco_catalogo(caminho_db)
    try:
        colunas = [
            linha[1]
            for linha in conexao_migrada.execute("PRAGMA table_info(catalogo_croquis)").fetchall()
        ]
        assert colunas == ["croqui_uid", "id_slug", "nome", "cidade", "estado"]
        linha = conexao_migrada.execute("SELECT * FROM catalogo_croquis").fetchone()
        assert linha == ("c1", "slug1", "Pico 1", "BH", "MG")
    finally:
        conexao_migrada.close()


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
    assert formatar_tipo_escalada(esc4) == "multienfiada"

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
    dados_croqui, registros_aresta = extrair_dados_croqui_para_catalogo(
        croqui, "br_mg_ferros_pico_dos_ferros"
    )

    assert dados_croqui == {
        "croqui_uid": "croqui12345678",
        "id_slug": "br_mg_ferros_pico_dos_ferros",
        "nome": "Pico dos Ferros",
        "cidade": "Ferros",
        "estado": "MG",
    }

    # 1 botao + 1 grupo + 2 setores + 5 escaladas = 9 registros
    assert len(registros_aresta) == 9

    # Botão
    reg_botao = next(r for r in registros_aresta if r["uid"] == "botao_pix_1234")
    assert reg_botao["tipo"] == "botao"
    assert reg_botao["nome"] == "Chave Pix"
    assert reg_botao["escalada_grau"] is None
    assert reg_botao["escalada_tipo"] is None
    assert reg_botao["setor_uid"] is None
    assert reg_botao["grupo_uid"] is None

    # Grupo
    reg_grupo = next(r for r in registros_aresta if r["uid"] == "grupo_boulders")
    assert reg_grupo["tipo"] == "grupo"
    assert reg_grupo["nome"] == "Setor dos Boulders"
    assert reg_grupo["escalada_grau"] is None
    assert reg_grupo["escalada_tipo"] is None
    assert reg_grupo["setor_uid"] is None
    assert reg_grupo["grupo_uid"] is None

    # Setor 1 (sem grupo)
    reg_s1 = next(r for r in registros_aresta if r["uid"] == "setor_cachoeir")
    assert reg_s1["tipo"] == "setor"
    assert reg_s1["nome"] == "Cachoeira"
    assert reg_s1["grupo_uid"] is None

    # Setor 2 (com grupo)
    reg_s2 = next(r for r in registros_aresta if r["uid"] == "setor_boulders")
    assert reg_s2["tipo"] == "setor"
    assert reg_s2["nome"] == "Boulders da Entrada"
    assert reg_s2["grupo_uid"] == "grupo_boulders"

    # Escalada esportiva
    via_esp = next(r for r in registros_aresta if r["uid"] == "via_pe_na_chap")
    assert via_esp["tipo"] == "escalada"
    assert via_esp["nome"] == "Pé na Chapa"
    assert via_esp["escalada_grau"] == "7a"
    assert via_esp["escalada_tipo"] == "esportiva"
    assert via_esp["setor_uid"] == "setor_cachoeir"
    assert via_esp["grupo_uid"] is None

    # Escalada multienfiada (com grupo)
    via_mult = next(r for r in registros_aresta if r["uid"] == "multiplas_fura")
    assert via_mult["tipo"] == "escalada"
    assert via_mult["nome"] == "Furacão"
    assert via_mult["escalada_grau"] == "8a"
    assert via_mult["escalada_tipo"] == "multienfiada"
    assert via_mult["setor_uid"] == "setor_boulders"
    assert via_mult["grupo_uid"] == "grupo_boulders"


def test_extrair_dados_croqui_fallback_id() -> None:
    croqui = croqui_pb2.Croqui()
    dados_croqui, registros_aresta = extrair_dados_croqui_para_catalogo(croqui, "fallback-slug")
    assert dados_croqui["croqui_uid"] == "fallback-slug"
    assert dados_croqui["id_slug"] == "fallback-slug"
    assert len(registros_aresta) == 0


def test_inserir_e_remover_croqui_no_catalogo(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo.db"
    conexao = inicializar_banco_catalogo(caminho_db)

    croqui = _criar_croqui_exemplo()
    dados_croqui, registros = extrair_dados_croqui_para_catalogo(croqui)

    inserir_croqui_no_catalogo(conexao, dados_croqui, registros)

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM catalogo_croquis WHERE croqui_uid = ?", ("croqui12345678",)
    )
    assert cursor.fetchone()[0] == 1

    cursor.execute("SELECT COUNT(*) FROM catalogo_aresta WHERE croqui_uid = ?", ("croqui12345678",))
    assert cursor.fetchone()[0] == 9

    # Testa remoção seletiva
    remover_croqui_do_catalogo(conexao, "croqui12345678")

    cursor.execute(
        "SELECT COUNT(*) FROM catalogo_croquis WHERE croqui_uid = ?", ("croqui12345678",)
    )
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM catalogo_aresta WHERE croqui_uid = ?", ("croqui12345678",))
    assert cursor.fetchone()[0] == 0

    conexao.close()


def test_consulta_aresta_cc_via_left_join(tmp_path: Path) -> None:
    caminho_db = tmp_path / "catalogo.db"
    conexao = inicializar_banco_catalogo(caminho_db)

    croqui = _criar_croqui_exemplo()
    dados_croqui, registros = extrair_dados_croqui_para_catalogo(croqui)
    inserir_croqui_no_catalogo(conexao, dados_croqui, registros)

    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT
            e.nome AS escalada_nome,
            e.escalada_grau,
            e.escalada_tipo,
            s.nome AS setor_nome,
            g.nome AS grupo_nome,
            c.nome AS pico_nome,
            c.estado AS estado
        FROM catalogo_aresta e
        LEFT JOIN catalogo_aresta s ON s.uid = e.setor_uid
        LEFT JOIN catalogo_aresta g ON g.uid = e.grupo_uid
        LEFT JOIN catalogo_croquis c ON c.croqui_uid = e.croqui_uid
        WHERE e.uid = ? AND e.tipo = 'escalada'
        """,
        ("multiplas_fura",),
    )
    linha = cursor.fetchone()
    assert linha is not None
    escalada_nome, grau, tipo, setor, grupo, pico, estado = linha
    assert escalada_nome == "Furacão"
    assert grau == "8a"
    assert tipo == "multienfiada"
    assert setor == "Boulders da Entrada"
    assert grupo == "Setor dos Boulders"
    assert pico == "Pico dos Ferros"
    assert estado == "MG"

    conexao.close()


def test_calcular_e_obter_versao_catalogo_determinismo(tmp_path: Path) -> None:
    db1 = tmp_path / "db1.db"
    db2 = tmp_path / "db2.db"

    con1 = inicializar_banco_catalogo(db1)
    con2 = inicializar_banco_catalogo(db2)

    croqui = _criar_croqui_exemplo()
    dados1, registros1 = extrair_dados_croqui_para_catalogo(croqui)
    dados2, registros2 = extrair_dados_croqui_para_catalogo(croqui)

    inserir_croqui_no_catalogo(con1, dados1, registros1)
    # Em db2, insere um croqui extra, remove-o e depois insere o mesmo croqui de db1
    inserir_croqui_no_catalogo(
        con2,
        {
            "croqui_uid": "temp_uid",
            "id_slug": "temp",
            "nome": "Temp",
            "cidade": "",
            "estado": "",
        },
        [],
    )
    remover_croqui_do_catalogo(con2, "temp_uid")
    inserir_croqui_no_catalogo(con2, dados2, registros2)

    v1 = calcular_versao_catalogo(con1)
    v2 = calcular_versao_catalogo(con2)

    assert len(v1) == 16
    assert v1 == v2

    con1.close()
    con2.close()

    # Banco com versao_catalogo já gravada em catalogo_meta lê diretamente
    assert obter_versao_catalogo(db1) == v1

    # Banco ainda sem versao_catalogo gravada em catalogo_meta calcula automaticamente
    db3 = tmp_path / "db3_sem_meta.db"
    con3 = inicializar_banco_catalogo(db3)
    inserir_croqui_no_catalogo(con3, dados1, registros1)
    con3.close()
    assert obter_versao_catalogo(db3) == v1

    # Caminho inexistente retorna string vazia
    assert obter_versao_catalogo(tmp_path / "inexistente.db") == ""


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
    for b in croqui2.botoes:
        b.uid = f"c2_botao_{uid_counter}"
        uid_counter += 1
    for pico in croqui2.picos:
        for sg in pico.setores_ou_grupos:
            if sg.HasField("grupo") and sg.grupo.HasField("conteudo"):
                sg.grupo.conteudo.uid = f"c2_grupo_{uid_counter}"
                uid_counter += 1
                setores = list(sg.grupo.conteudo.setores)
            elif sg.HasField("setor"):
                setores = [sg.setor]
            else:
                setores = []
            for s in setores:
                s.conteudo.uid = f"c2_setor_{uid_counter}"
                uid_counter += 1
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
    versao_inicial = obter_versao_catalogo(caminho_db)
    assert len(versao_inicial) == 16

    conexao = sqlite3.connect(caminho_db)
    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) FROM catalogo_croquis")
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT COUNT(*) FROM catalogo_aresta")
    assert cursor.fetchone()[0] == 18
    cursor.execute("SELECT valor FROM catalogo_meta WHERE chave = 'versao_catalogo'")
    assert cursor.fetchone()[0] == versao_inicial
    conexao.close()

    # 2. Deploy seletivo (apenas croqui-1 atualizado)
    croqui1.nome = "Pico dos Ferros Atualizado"
    (croqui1_dir / "compilado.binarypb").write_bytes(croqui1.SerializeToString())

    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["br_mg_ferros_croqui1"])
    versao_atualizada = obter_versao_catalogo(caminho_db)
    assert len(versao_atualizada) == 16
    assert versao_atualizada != versao_inicial

    conexao = sqlite3.connect(caminho_db)
    cursor = conexao.cursor()
    cursor.execute("SELECT nome FROM catalogo_croquis WHERE croqui_uid = 'croqui11111111'")
    assert cursor.fetchone()[0] == "Pico dos Ferros Atualizado"
    # Croqui 2 ainda deve estar lá
    cursor.execute("SELECT COUNT(*) FROM catalogo_croquis WHERE croqui_uid = 'croqui22222222'")
    assert cursor.fetchone()[0] == 1
    conexao.close()

    # 3. Alvo que não possui compilado.binarypb mantém a mesma versão
    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["alvo_fantasma"])
    assert obter_versao_catalogo(caminho_db) == versao_atualizada


def test_extrair_dados_setores_e_escaladas_incompletos() -> None:
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()

    # Botão sem uid
    b_invalido = croqui.botoes.add()
    b_invalido.texto = "Sem UID"

    # Setor sem conteudo
    sg1 = pico.setores_ou_grupos.add()
    sg1.setor.caminho = "setor_sem_conteudo.md"

    # Setor com escalada sem tipo definido
    sg2 = pico.setores_ou_grupos.add()
    s2 = sg2.setor.conteudo
    s2.nome = "Setor Incompleto"
    _ = s2.escaladas.add()

    # Setor com escalada com tipo mas sem UID
    esc_sem_uid = s2.escaladas.add()
    esc_sem_uid.via_esportiva.nome = "Sem UID"
    esc_sem_uid.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_5

    dados_croqui, registros = extrair_dados_croqui_para_catalogo(croqui, "br_mg_bh_incompleto")
    assert dados_croqui["id_slug"] == "br_mg_bh_incompleto"
    assert len(registros) == 0


def test_formatar_grau_highline_zero() -> None:
    esc = croqui_pb2.Escalada()
    esc.highline.distancia = 0
    assert formatar_grau_escalada(esc) == ""


def test_gerar_catalogo_completo_nao_modifica_banco_quando_dados_logicos_inalterados(
    tmp_path: Path,
) -> None:
    pasta_gerados = tmp_path / "generated"
    croqui_dir = pasta_gerados / "br_mg_ferros_croqui1"
    croqui_dir.mkdir(parents=True)

    croqui = _criar_croqui_exemplo()
    croqui.uid = "croqui11111111"
    croqui.id = "br_mg_ferros_croqui1"
    (croqui_dir / "compilado.binarypb").write_bytes(croqui.SerializeToString())

    caminho_db = pasta_gerados / "catalogo.db"
    gerar_catalogo_completo(pasta_gerados, caminho_db)

    bytes_antes = caminho_db.read_bytes()

    # Altera apenas a descrição do croqui (que não faz parte do catálogo SQLite)
    croqui.descricao = "Descrição atualizada que não afeta o catálogo"
    (croqui_dir / "compilado.binarypb").write_bytes(croqui.SerializeToString())

    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["br_mg_ferros_croqui1"])

    assert caminho_db.read_bytes() == bytes_antes

    # Altera apenas uma escalada em catalogo_aresta (mantendo catalogo_croquis igual) -> deve atualizar
    croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva.nome = (
        "Pé na Chapa Renovada"
    )
    (croqui_dir / "compilado.binarypb").write_bytes(croqui.SerializeToString())
    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["br_mg_ferros_croqui1"])
    assert "Pé na Chapa Renovada" in (pasta_gerados / "catalogo_aresta.csv").read_text(
        encoding="utf-8"
    )


def test_gerar_catalogo_completo_remove_orfaos_por_id_slug_e_sincroniza_ids_permitidos(
    tmp_path: Path,
) -> None:
    import contextlib

    pasta_gerados = tmp_path / "generated"
    c1_dir = pasta_gerados / "br_mg_ferros_c1"
    c2_dir = pasta_gerados / "br_mg_araxa_c2"
    c1_dir.mkdir(parents=True)
    c2_dir.mkdir(parents=True)

    c1 = croqui_pb2.Croqui(uid="uid_c1_antigo", id="br_mg_ferros_c1", nome="Croqui 1")
    b1 = c1.botoes.add()
    b1.uid = "botao_c1_antigo"
    b1.texto = "Botão Antigo"

    c2 = croqui_pb2.Croqui(uid="uid_c2", id="br_mg_araxa_c2", nome="Croqui 2")
    b2 = c2.botoes.add()
    b2.uid = "botao_c2"
    b2.texto = "Botão C2"

    (c1_dir / "compilado.binarypb").write_bytes(c1.SerializeToString())
    (c2_dir / "compilado.binarypb").write_bytes(c2.SerializeToString())

    caminho_db = pasta_gerados / "catalogo.db"
    gerar_catalogo_completo(pasta_gerados, caminho_db)

    # 1. Croqui 1 muda de croqui_uid mantendo o mesmo id_slug (br_mg_ferros_c1)
    c1_novo = croqui_pb2.Croqui(uid="uid_c1_novo", id="br_mg_ferros_c1", nome="Croqui 1")
    b1_novo = c1_novo.botoes.add()
    b1_novo.uid = "botao_c1_novo"
    b1_novo.texto = "Botão Novo"
    (c1_dir / "compilado.binarypb").write_bytes(c1_novo.SerializeToString())

    # Insere também uma entidade órfã avulsa sem pai em catalogo_croquis
    with contextlib.closing(sqlite3.connect(caminho_db)) as con:
        con.execute(
            "INSERT INTO catalogo_aresta (uid, tipo, croqui_uid, nome) "
            "VALUES ('entidade_orfa', 'botao', 'croqui_inexistente', 'Órfã')"
        )
        con.commit()

    # Executa deploy parcial restringindo ids_permitidos apenas a br_mg_ferros_c1 (como no modo experimental)
    gerar_catalogo_completo(
        pasta_gerados,
        caminho_db,
        alvos=["br_mg_ferros_c1"],
        ids_permitidos={"br_mg_ferros_c1"},
    )

    with contextlib.closing(sqlite3.connect(caminho_db)) as con:
        croquis = con.execute("SELECT croqui_uid, id_slug FROM catalogo_croquis").fetchall()
        entidades = [r[0] for r in con.execute("SELECT uid FROM catalogo_aresta").fetchall()]

    # Deve conter exclusivamente uid_c1_novo e botao_c1_novo (sem uid_c1_antigo, sem uid_c2 e sem entidade_orfa)
    assert croquis == [("uid_c1_novo", "br_mg_ferros_c1")]
    assert entidades == ["botao_c1_novo"]

    # 2. Se ids_permitidos passar a incluir novamente br_mg_araxa_c2, deve recompilar o croqui ausente do banco
    gerar_catalogo_completo(
        pasta_gerados,
        caminho_db,
        alvos=["br_mg_ferros_c1"],
        ids_permitidos={"br_mg_ferros_c1", "br_mg_araxa_c2"},
    )
    with contextlib.closing(sqlite3.connect(caminho_db)) as con:
        slugs = {r[0] for r in con.execute("SELECT id_slug FROM catalogo_croquis").fetchall()}
    assert slugs == {"br_mg_ferros_c1", "br_mg_araxa_c2"}

    # 3. Se alvos=None e ids_permitidos={"br_mg_araxa_c2"}, filtra apenas o permitido na compilação total
    gerar_catalogo_completo(
        pasta_gerados,
        caminho_db,
        alvos=None,
        ids_permitidos={"br_mg_araxa_c2"},
    )
    with contextlib.closing(sqlite3.connect(caminho_db)) as con:
        slugs_finais = {
            r[0] for r in con.execute("SELECT id_slug FROM catalogo_croquis").fetchall()
        }
    assert slugs_finais == {"br_mg_araxa_c2"}


def test_gerar_catalogo_completo_remove_croqui_orfao_em_compilacao_total(
    tmp_path: Path,
) -> None:
    import contextlib
    import shutil

    pasta_gerados = tmp_path / "generated"
    c1_dir = pasta_gerados / "br_mg_ferros_c1"
    c2_dir = pasta_gerados / "br_mg_araxa_c2"
    c1_dir.mkdir(parents=True)
    c2_dir.mkdir(parents=True)

    c1 = croqui_pb2.Croqui(uid="uid_c1", id="br_mg_ferros_c1", nome="Croqui 1")
    c2 = croqui_pb2.Croqui(uid="uid_c2", id="br_mg_araxa_c2", nome="Croqui 2")
    b2 = c2.botoes.add()
    b2.uid = "uid_botao_c2"
    b2.texto = "Botão C2"

    (c1_dir / "compilado.binarypb").write_bytes(c1.SerializeToString())
    (c2_dir / "compilado.binarypb").write_bytes(c2.SerializeToString())

    caminho_db = pasta_gerados / "catalogo.db"
    gerar_catalogo_completo(pasta_gerados, caminho_db)
    versao_com_dois = obter_versao_catalogo(caminho_db)

    # Remove a pasta compilada de c2 e roda compilação total (alvos=None)
    shutil.rmtree(c2_dir)
    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=None)

    versao_sem_c2 = obter_versao_catalogo(caminho_db)
    assert versao_sem_c2 != versao_com_dois

    with contextlib.closing(sqlite3.connect(caminho_db)) as con:
        uids_croquis = [
            r[0] for r in con.execute("SELECT croqui_uid FROM catalogo_croquis").fetchall()
        ]
        uids_aresta = [r[0] for r in con.execute("SELECT uid FROM catalogo_aresta").fetchall()]

    assert uids_croquis == ["uid_c1"]
    assert "uid_botao_c2" not in uids_aresta


def test_gerar_catalogo_completo_exporta_tres_csvs_ordenados_e_preserva_quando_inalterado(
    tmp_path: Path,
) -> None:
    import csv
    import os

    pasta_gerados = tmp_path / "generated"
    c1_dir = pasta_gerados / "br_mg_ferros_c1"
    c2_dir = pasta_gerados / "br_mg_araxa_c2"
    c1_dir.mkdir(parents=True)
    c2_dir.mkdir(parents=True)

    c1 = _criar_croqui_exemplo()
    c1.uid = "croqui_z"
    c1.id = "br_mg_ferros_c1"
    (c1_dir / "compilado.binarypb").write_bytes(c1.SerializeToString())

    c2 = croqui_pb2.Croqui(uid="croqui_a", id="br_mg_araxa_c2", nome="Croqui Araxá")
    b2 = c2.botoes.add()
    b2.uid = "z_botao_c2"
    b2.texto = "Botão C2"
    (c2_dir / "compilado.binarypb").write_bytes(c2.SerializeToString())

    caminho_db = pasta_gerados / "catalogo.db"
    gerar_catalogo_completo(pasta_gerados, caminho_db)

    csv_croquis = pasta_gerados / "catalogo_croquis.csv"
    csv_aresta = pasta_gerados / "catalogo_aresta.csv"
    csv_meta = pasta_gerados / "catalogo_meta.csv"

    assert csv_croquis.is_file()
    assert csv_aresta.is_file()
    assert csv_meta.is_file()

    # 1. Verifica catalogo_croquis.csv (sem atualizado_em, ordenado por id_slug, croqui_uid)
    linhas_croquis = list(csv.reader(csv_croquis.read_text(encoding="utf-8").splitlines()))
    assert linhas_croquis[0] == ["croqui_uid", "id_slug", "nome", "cidade", "estado"]
    assert [linha[1] for linha in linhas_croquis[1:]] == [
        "br_mg_araxa_c2",
        "br_mg_ferros_c1",
    ]

    # 2. Verifica catalogo_aresta.csv (ordenado por croqui_uid, uid -> bloco contíguo por croqui)
    linhas_aresta = list(csv.reader(csv_aresta.read_text(encoding="utf-8").splitlines()))
    assert linhas_aresta[0] == [
        "uid",
        "tipo",
        "croqui_uid",
        "nome",
        "escalada_grau",
        "escalada_tipo",
        "setor_uid",
        "grupo_uid",
    ]
    # Primeira linha de dados deve ser de croqui_a (mesmo seu uid sendo 'z_botao_c2'),
    # seguida de todas as 9 linhas de croqui_z ordenadas por uid
    assert linhas_aresta[1] == ["z_botao_c2", "botao", "croqui_a", "Botão C2", "", "", "", ""]
    uids_croqui_z = [linha[0] for linha in linhas_aresta[2:]]
    assert len(uids_croqui_z) == 9
    assert uids_croqui_z == sorted(uids_croqui_z)

    # 3. Verifica catalogo_meta.csv
    linhas_meta = list(csv.reader(csv_meta.read_text(encoding="utf-8").splitlines()))
    assert linhas_meta == [
        ["chave", "valor"],
        ["versao_catalogo", obter_versao_catalogo(caminho_db)],
    ]

    # 4. Short-circuit: se nada mudou e os 3 CSVs existem, não reescreve no disco
    mtime_antigo = 1_600_000_000_000_000_000
    for arq in (csv_croquis, csv_aresta, csv_meta):
        os.utime(arq, ns=(mtime_antigo, mtime_antigo))

    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["br_mg_ferros_c1"])
    for arq in (csv_croquis, csv_aresta, csv_meta):
        assert arq.stat().st_mtime_ns == mtime_antigo

    # 5. Se um dos arquivos CSV for apagado, deve recriá-lo mesmo sem mudança no SQLite
    csv_meta.unlink()
    gerar_catalogo_completo(pasta_gerados, caminho_db, alvos=["br_mg_ferros_c1"])
    assert csv_meta.is_file()



