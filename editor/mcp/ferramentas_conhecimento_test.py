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
