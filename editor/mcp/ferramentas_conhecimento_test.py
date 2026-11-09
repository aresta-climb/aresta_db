# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest

from editor.mcp.despachante import DespachanteQt
from editor.mcp.ferramentas_conhecimento import registrar_ferramentas_conhecimento
from editor.mcp.servidor import ServidorMCP


def _chamar(servidor: ServidorMCP, nome: str, argumentos: dict) -> dict:
    resp = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": nome, "arguments": argumentos},
        }
    )
    assert resp is not None
    res = resp["result"]
    if res.get("isError"):
        raise RuntimeError(res["content"][0]["text"])
    return res["structuredContent"]


def test_aresta_obter_esquema_proto_visao_geral_mensagem_e_enum(qapp, tmp_path: Path):
    """Valida a introspecção geral de croqui.proto, filtro por mensagem, wrapper de enum e enum direto."""
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_conhecimento(servidor)

    # 1. Visão geral (sem filtro) e via recurso MCP aresta://esquema/proto
    geral = _chamar(servidor, "aresta_obter_esquema_proto", {})
    assert "aresta_alterar_campo" in geral["guia_uso_mcp"]
    assert "Croqui" in geral["mensagens_disponiveis"]
    assert "Escalada" in geral["mensagens_disponiveis"]
    assert "ViaEsportiva" in geral["mensagens_disponiveis"]
    assert "message Croqui" in geral["conteudo_proto"]

    resp_recurso = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {"uri": "aresta://esquema/proto"},
        }
    )
    assert resp_recurso is not None
    assert "aresta_alterar_campo" in resp_recurso["result"]["contents"][0]["text"]

    # 2. Introspecção de mensagem com oneof (Escalada) e com enum/primitivos (ViaEsportiva)
    esc_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "Escalada"})
    assert esc_info["tipo"] == "message"
    assert esc_info["nome"] == "Escalada"
    assert "via_esportiva" in esc_info["oneofs"]["tipo"]
    assert "boulder" in esc_info["oneofs"]["tipo"]

    via_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "viaesportiva"})
    assert via_info["nome"] == "ViaEsportiva"
    campos_via = {c["nome"]: c for c in via_info["campos"]}
    assert campos_via["dificuldade"]["opcoes_enum"] is not None
    assert "BR_7A" in campos_via["dificuldade"]["opcoes_enum"]
    assert campos_via["conquistadores"]["repeated"] is True
    assert campos_via["nome"]["descricao"] != ""

    # 3. Introspecção de mensagem wrapper de Enum (GrauVia) e Enum direto (TipoNo)
    grau_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "GrauVia"})
    nomes_graus = [v["nome"] for v in grau_info["valores_enum"]]
    assert "BR_7A" in nomes_graus

    enum_direto = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "TipoNo"})
    assert enum_direto["tipo"] == "enum"
    nomes_no = [v["nome"] for v in enum_direto["valores_enum"]]
    assert "PROTECAO_FIXA" in nomes_no

    # 4. Tipo inexistente lança erro descritivo
    with pytest.raises(RuntimeError, match="não encontrado em croqui.proto"):
        _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "TipoInexistenteXYZ"})


def test_aresta_obter_esquema_proto_omite_campos_invisiveis_preservando_uids(qapp, tmp_path: Path):
    """Valida que campos INVISIVEL internos/legados são omitidos do schema, mantendo uid, alvo_uid e pontos_uids."""
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_conhecimento(servidor)

    croqui_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "Croqui"})
    nomes_croqui = {c["nome"] for c in croqui_info["campos"]}
    assert "uid" in nomes_croqui
    assert "nome" in nomes_croqui
    assert "arquivos_externos" not in nomes_croqui
    assert "ultima_migracao" not in nomes_croqui
    assert "curadoria_betas" not in nomes_croqui

    pico_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "Pico"})
    nomes_pico = {c["nome"] for c in pico_info["campos"]}
    assert "precomputados" not in nomes_pico
    assert "malha_estrada" not in nomes_pico

    setor_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "Setor"})
    nomes_setor = {c["nome"] for c in setor_info["campos"]}
    assert "uid" in nomes_setor
    assert "precomputados" not in nomes_setor

    ref_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "Referencia"})
    nomes_ref = {c["nome"] for c in ref_info["campos"]}
    assert "alvo_uid" in nomes_ref
    assert "pontos_uids" in nomes_ref
    assert "id" not in nomes_ref
    assert "ids" not in nomes_ref
    assert "escalada" not in nomes_ref
    assert "setor" not in nomes_ref
    assert "grupo" not in nomes_ref
    assert "alvo_referencia" not in ref_info["oneofs"]
    assert "identificador_ponto" not in ref_info["oneofs"]

    poi_info = _chamar(
        servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "PontoDeInteresse"}
    )
    nomes_poi = {c["nome"] for c in poi_info["campos"]}
    assert "uid" in nomes_poi
    assert "rotulo" in nomes_poi
    assert "id" not in nomes_poi
    assert "label" not in nomes_poi

    linha_info = _chamar(servidor, "aresta_obter_esquema_proto", {"tipo_mensagem": "LinhaTrajeto"})
    nomes_linha = {c["nome"] for c in linha_info["campos"]}
    assert "compilado" not in nomes_linha


def test_aresta_listar_e_ler_skills_reais_e_customizadas(qapp, tmp_path: Path):
    """Valida a listagem e leitura de skills do repositório e de um diretório customizado."""
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_conhecimento(servidor)

    # 1. Listar skills reais do repositório e ler recurso aresta://skills
    lista = _chamar(servidor, "aresta_listar_skills", {})
    nomes_skills = {s["nome"] for s in lista["skills"]}
    assert "preencher_croqui_yaml" in nomes_skills
    assert "mapa_extrair_pontos_de_interesse" in nomes_skills

    resp_rec_skills = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/read",
            "params": {"uri": "aresta://skills"},
        }
    )
    assert resp_rec_skills is not None
    assert "preencher_croqui_yaml" in resp_rec_skills["result"]["contents"][0]["text"]

    # 2. Ler uma skill específica real
    detalhe = _chamar(servidor, "aresta_ler_skill", {"nome_skill": "preencher_croqui_yaml"})
    assert detalhe["nome"] == "preencher_croqui_yaml"
    assert len(detalhe["conteudo_markdown"]) > 50
    assert isinstance(detalhe["arquivos_auxiliares"], list)

    # 3. Skill inexistente deve falhar listando as disponíveis
    with pytest.raises(RuntimeError, match="Skill 'skill_inexistente' não encontrada"):
        _chamar(servidor, "aresta_ler_skill", {"nome_skill": "skill_inexistente"})

    # 4. Diretório de skills customizado (incluindo SKILL.md sem frontmatter YAML e arquivo proto customizado)
    dir_skills_tmp = tmp_path / "skills_custom"
    pasta_s1 = dir_skills_tmp / "minha_skill"
    pasta_s1.mkdir(parents=True)
    (pasta_s1 / "SKILL.md").write_text("# Minha Skill Sem Frontmatter\nConteúdo.", encoding="utf-8")
    (pasta_s1 / "exemplo.txt").write_text("exemplo", encoding="utf-8")

    arq_proto_tmp = tmp_path / "custom.proto"
    arq_proto_tmp.write_text('syntax = "proto3";\n', encoding="utf-8")

    servidor_custom = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_conhecimento(
        servidor_custom,
        diretorio_skills=dir_skills_tmp,
        caminho_proto=arq_proto_tmp,
    )
    lista_custom = _chamar(servidor_custom, "aresta_listar_skills", {})
    assert len(lista_custom["skills"]) == 1
    assert lista_custom["skills"][0]["nome"] == "minha_skill"

    lida_custom = _chamar(servidor_custom, "aresta_ler_skill", {"nome_skill": "minha_skill"})
    assert "exemplo.txt" in lida_custom["arquivos_auxiliares"]


def test_aresta_avaliar_qualidade_em_memoria_e_em_disco(qapp, tmp_path: Path):
    """Valida a ferramenta MCP aresta_avaliar_qualidade sobre o CroquiModel ativo e sobre diretório em disco."""
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel

    croqui = croqui_pb2.Croqui(
        id="br_mg_lapinha",
        uid="uid_lapinha_01",
        nome="Gruta da Lapinha",
        descricao="Clássico de calcário em Lagoa Santa.",
        caminho_thumbnail="imagens/capa.webp",
    )
    pico = croqui.picos.add(nome="Gruta da Lapinha")
    pico.localizacao.latitude = -195622616
    pico.localizacao.longitude = -439595684
    model = CroquiModel(croqui)

    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    servidor.definir_croqui_ativo("br_mg_lapinha", str(tmp_path))
    registrar_ferramentas_conhecimento(servidor, model=model)

    # 1. Avaliação do modelo em memória (nota 1000 da identidade_capa e parcial da localização)
    diag = _chamar(servidor, "aresta_avaliar_qualidade", {})
    assert diag["nota_maxima"] == 8770
    assert diag["nota_qualidade"] >= 1000
    assert diag["pronto_para_publicar"] is False
    assert len(diag["etapas"]) == 3
    ids_pendentes = [t["id_tarefa"] for t in diag["tarefas_pendentes"]]
    assert "etapa1_malha_estrada_picos" in ids_pendentes

    # 2. Avaliação de um croqui em disco informando id_croqui quando não há model ou id_croqui é outro
    dir_db = tmp_path / "database" / "br_rj_urca"
    dir_db.mkdir(parents=True)
    (dir_db / "croqui.yaml").write_text(
        "id: br_rj_urca\nnome: Morro da Urca\ndescricao: Desc\ncaminho_thumbnail: img/t.webp\n",
        encoding="utf-8",
    )
    servidor_disco = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_conhecimento(
        servidor_disco, diretorio_database=tmp_path / "database"
    )
    diag_disco = _chamar(
        servidor_disco, "aresta_avaliar_qualidade", {"id_croqui": "br_rj_urca"}
    )
    assert diag_disco["nota_qualidade"] == 1000
    assert diag_disco["nota_maxima"] == 8770

    # 3. Erro claro se não houver croqui aberto nem id_croqui válido em disco
    with pytest.raises(RuntimeError, match="Não foi possível localizar o croqui"):
        _chamar(
            servidor_disco, "aresta_avaliar_qualidade", {"id_croqui": "croqui_inexistente"}
        )
