# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
from pathlib import Path

import pytest
from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.controllers.mapas_controller import MapasController
from editor.mcp.despachante import DespachanteQt
from editor.mcp.ferramentas_comandos import registrar_ferramentas_comandos
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def _montar_ambiente_comandos(
    tmp_path: Path,
) -> tuple[CroquiModel, QUndoStack, CroquiController, MapasController, ServidorMCP]:
    croqui = croqui_pb2.Croqui(uid="uid_croqui_raiz", nome="Croqui Inicial")
    pico = croqui.picos.add(nome="Pico 1")

    sg_setor = pico.setores_ou_grupos.add()
    setor = sg_setor.setor.conteudo
    setor.uid = "uid_setor_base"
    setor.nome = "Setor Base"

    sg_grupo = pico.setores_ou_grupos.add()
    grupo = sg_grupo.grupo.conteudo
    grupo.uid = "uid_grupo_base"
    grupo.nome = "Grupo Base"

    esc = setor.escaladas.add(uid="uid_via_base01")
    esc.via_esportiva.nome = "Via Antiga"
    esc.via_esportiva.extensao = 15

    mapa = setor.mapas.add(caminho_imagem_mapa="imagens/mapa_base.webp")
    mapa.pontos_de_interesse.add(uid="uid_poi_base01", rotulo="1")

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    croqui_ctrl = CroquiController(model, undo_stack)
    mapas_ctrl = MapasController(model, undo_stack)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_comandos(servidor, croqui_ctrl, mapas_ctrl)
    return model, undo_stack, croqui_ctrl, mapas_ctrl, servidor


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


def test_aresta_alterar_campo_primitivo_enum_submensagem_oneof_e_lote(qapp, tmp_path: Path):
    """
    Testa aresta_alterar_campo unificado para primitivos, enums por nome, submensagens via dict,
    oneofs (por variante direta e pelo nome do oneof), itens indexados repeated e lote de campos.
    """
    model, undo_stack, _, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    # 1. Alterar primitivo na raiz e em uma escalada por UID (incluindo renomeação sincronizada)
    res_raiz = _chamar(
        servidor,
        "aresta_alterar_campo",
        {"alvo": "uid_croqui_raiz", "campo": "nome", "valor": "Croqui Novo"},
    )
    assert res_raiz["campos_alterados"] == ["nome"]
    assert raiz.nome == "Croqui Novo"

    # 2. Alterar múltiplos campos em lote (primitivo + enum por string + renomeação) em 1 CmdMacro
    res_lote = _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "uid_via_base01",
            "campos": {
                "nome": "Via Atualizada Lote",
                "extensao": 35,
                "dificuldade": "BR_7a",
            },
        },
    )
    assert set(res_lote["campos_alterados"]) == {"nome", "extensao", "dificuldade"}
    esc_proxy = raiz.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0]
    assert esc_proxy.via_esportiva.nome == "Via Atualizada Lote"
    assert esc_proxy.via_esportiva.extensao == 35
    assert esc_proxy.via_esportiva.dificuldade == croqui_pb2.GrauVia.BR_7A
    assert model.indice_uids.obter("uid_via_base01").nome_escalada == "Via Atualizada Lote"

    # Um único undo desfaz o lote inteiro
    undo_stack.undo()
    assert esc_proxy.via_esportiva.nome == "Via Antiga"
    assert esc_proxy.via_esportiva.extensao == 15

    # 3. Alterar submensagem singular (localizacao em Pico) passando dict JSON
    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "picos.0",
            "campo": "localizacao",
            "valor": {"latitude": -195000000, "longitude": -439000000},
        },
    )
    assert raiz.picos[0].localizacao.latitude == -195000000
    assert raiz.picos[0].localizacao.longitude == -439000000

    # 4. Alterar oneof passando diretamente o nome da variante (boulder) com dict
    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "uid_via_base01",
            "campo": "boulder",
            "valor": {"nome": "Boulder Convertido", "dificuldade": "V5"},
        },
    )
    assert esc_proxy.WhichOneof("tipo") == "boulder"
    assert esc_proxy.boulder.nome == "Boulder Convertido"
    assert esc_proxy.boulder.dificuldade == croqui_pb2.GrauBoulder.V5

    undo_stack.undo()
    assert esc_proxy.WhichOneof("tipo") == "via_esportiva"

    # Alterar oneof pelo nome do grupo oneof ("tipo") passando dict {variante: dados} e depois None
    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "uid_via_base01",
            "campo": "tipo",
            "valor": {"boulder": {"nome": "Boulder Via Tipo"}},
        },
    )
    assert esc_proxy.WhichOneof("tipo") == "boulder"
    assert esc_proxy.boulder.nome == "Boulder Via Tipo"

    _chamar(
        servidor,
        "aresta_alterar_campo",
        {"alvo": "uid_via_base01", "campo": "tipo", "valor": None},
    )
    assert esc_proxy.WhichOneof("tipo") is None
    undo_stack.undo()
    undo_stack.undo()

    # Alterar SetorOuGrupo trocando variante para grupo com atalho de dict sem chave 'conteudo'
    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "picos.0.setores_ou_grupos.0",
            "campo": "grupo",
            "valor": {"nome": "Convertido em Grupo"},
        },
    )
    assert raiz.picos[0].setores_ou_grupos[0].WhichOneof("tipo") == "grupo"
    assert raiz.picos[0].setores_ou_grupos[0].grupo.conteudo.nome == "Convertido em Grupo"
    undo_stack.undo()

    # 5. Erros de validação defensiva (sem campo, enum inválido, campo inexistente, repeated sem índice)
    with pytest.raises(RuntimeError, match="Informe 'campo'"):
        _chamar(servidor, "aresta_alterar_campo", {"alvo": "uid_croqui_raiz"})

    with pytest.raises(RuntimeError, match="Opções válidas"):
        _chamar(
            servidor,
            "aresta_alterar_campo",
            {"alvo": "uid_via_base01", "campo": "dificuldade", "valor": "GRAU_INEXISTENTE"},
        )

    with pytest.raises(RuntimeError, match="Campo 'inexistente'"):
        _chamar(
            servidor,
            "aresta_alterar_campo",
            {"alvo": "uid_croqui_raiz", "campo": "inexistente", "valor": "x"},
        )

    with pytest.raises(RuntimeError, match="repeated"):
        _chamar(
            servidor,
            "aresta_alterar_campo",
            {"alvo": "uid_croqui_raiz", "campo": "creditos", "valor": ["A"]},
        )

    with pytest.raises(RuntimeError, match="oneof 'tipo'"):
        _chamar(
            servidor,
            "aresta_alterar_campo",
            {"alvo": "uid_via_base01", "campo": "tipo", "valor": {"a": 1, "b": 2}},
        )


def test_operacoes_repeated_e_alterar_campo_indexado(qapp, tmp_path: Path):
    """Testa adicionar, remover, mover e alterar itens indexados via aresta_alterar_campo."""
    model, undo_stack, _, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    # 1. Adicionar escalada por UID do setor (atalho ergonômico com campos da variante e geração de UID)
    res_esc = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {
            "alvo": "uid_setor_base",
            "campo": "escaladas",
            "valor": {"nome": "Nova Via MCP", "extensao": 22},
        },
    )
    novo_uid_esc = res_esc["uid"]
    assert len(novo_uid_esc) == 14
    assert res_esc["tamanho"] == 2
    assert model.indice_uids.existe(novo_uid_esc)
    setor_proxy = raiz.picos[0].setores_ou_grupos[0].setor.conteudo
    assert setor_proxy.escaladas[1].via_esportiva.nome == "Nova Via MCP"
    assert setor_proxy.escaladas[1].via_esportiva.extensao == 22

    # Adicionar escalada com variante explícita inválida deve falhar
    with pytest.raises(RuntimeError, match="Variante de escalada"):
        _chamar(
            servidor,
            "aresta_adicionar_repeated",
            {
                "alvo": "uid_setor_base",
                "campo": "escaladas",
                "valor": {"tipo": "variante_invalida", "nome": "Via Erro"},
            },
        )

    # Adicionar escalada passando o envelope explícito {"boulder": {"nome": "..."}}
    res_boulder = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {
            "alvo": "uid_setor_base",
            "campo": "escaladas",
            "valor": {"boulder": {"nome": "Bloco Explicito"}},
        },
    )
    assert len(res_boulder["uid"]) == 14
    assert res_boulder["tamanho"] == 3

    # Adicionar setor em grupo e SetorOuGrupo no pico
    res_setor_grupo = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {
            "alvo": "uid_grupo_base",
            "campo": "setores",
            "valor": {"nome": "Setor Dentro do Grupo"},
        },
    )
    assert len(res_setor_grupo["uid"]) == 14

    res_sg_pico = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {
            "alvo": "picos.0",
            "campo": "setores_ou_grupos",
            "valor": {"tipo": "grupo", "nome": "Segundo Grupo"},
        },
    )
    assert len(res_sg_pico["uid"]) == 14

    res_sg_setor_pico = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {
            "alvo": "picos.0",
            "campo": "setores_ou_grupos",
            "valor": {"nome": "Setor Direto no Pico"},
        },
    )
    assert len(res_sg_setor_pico["uid"]) == 14

    # 2. Adicionar primitivos em repeated (creditos)
    res_c1 = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "valor": "Autor 1"},
    )
    assert res_c1["tamanho"] == 1
    res_c2 = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "valor": "Autor 2"},
    )
    assert res_c2["tamanho"] == 2
    assert list(raiz.creditos) == ["Autor 1", "Autor 2"]

    # 3. Mover repeated
    _chamar(
        servidor,
        "aresta_mover_repeated",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "creditos",
            "indice_origem": 0,
            "indice_destino": 1,
        },
    )
    assert list(raiz.creditos) == ["Autor 2", "Autor 1"]

    # 4. Alterar item único e múltiplos itens repeated via aresta_alterar_campo ("creditos.0", "creditos.1")
    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "creditos.0",
            "valor": "Autor Principal",
        },
    )
    assert list(raiz.creditos) == ["Autor Principal", "Autor 1"]

    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "uid_croqui_raiz",
            "campos": {
                "creditos.0": "Coautor A",
                "creditos.1": "Coautor B",
            },
        },
    )
    assert list(raiz.creditos) == ["Coautor A", "Coautor B"]

    # Alterar item composto repeated via aresta_alterar_campo ("trilhas.0")
    _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_setor_base", "campo": "trilhas", "valor": {"nome": "Trilha A"}},
    )
    _chamar(
        servidor,
        "aresta_alterar_campo",
        {
            "alvo": "uid_setor_base",
            "campo": "trilhas.0",
            "valor": {"nome": "Trilha B", "tempo_aproximacao": "20min"},
        },
    )
    assert setor_proxy.trilhas[0].nome == "Trilha B"

    # 5. Remover item repeated e validações de erro
    res_rem = _chamar(
        servidor,
        "aresta_remover_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "indice": 1},
    )
    assert res_rem["tamanho"] == 1
    assert list(raiz.creditos) == ["Coautor A"]

    undo_stack.undo()
    assert list(raiz.creditos) == ["Coautor A", "Coautor B"]

    with pytest.raises(RuntimeError, match="Índice fora de alcance"):
        _chamar(
            servidor,
            "aresta_remover_repeated",
            {"alvo": "uid_croqui_raiz", "campo": "creditos", "indice": 99},
        )

    with pytest.raises(RuntimeError, match="não é uma coleção repeated"):
        _chamar(
            servidor,
            "aresta_adicionar_repeated",
            {"alvo": "uid_croqui_raiz", "campo": "nome", "valor": "x"},
        )


def test_migrar_imagens_markdown_e_mapas_sem_expor_macro(qapp, tmp_path: Path):
    """Testa migrar setor, alterar imagens, markdown, mapas e garante que macros manuais não são expostas."""
    model, undo_stack, croqui_ctrl, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    # Registrar sem passar mapas_controller explícito também deve instanciar MapasController automaticamente
    servidor_auto = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_comandos(servidor_auto, croqui_ctrl)

    # Garante que aresta_iniciar_macro e aresta_finalizar_macro não existem no catálogo MCP
    resp_list = servidor.processar_mensagem_jsonrpc(
        {"jsonrpc": "2.0", "id": 99, "method": "tools/list", "params": {}}
    )
    nomes_tools = {t["name"] for t in resp_list["result"]["tools"]}
    assert "aresta_iniciar_macro" not in nomes_tools
    assert "aresta_finalizar_macro" not in nomes_tools
    assert "aresta_alterar_primitivo" not in nomes_tools
    assert "aresta_alterar_campo" in nomes_tools

    # 1. Vincular referência no mapa apontando para uid_via_base01
    res_ref = _chamar(
        servidor,
        "aresta_vincular_referencia_mapa",
        {
            "alvo_mapa": "uid_setor_base.mapas.0",
            "alvo_uid": "uid_via_base01",
            "pontos_uids": ["uid_poi_base01"],
        },
    )
    assert res_ref["alvo_uid"] == "uid_via_base01"
    mapa_proxy = raiz.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    assert len(mapa_proxy.referencias) == 1

    # 2. Alterar campo de imagem e substituir imagem em RAM (via base64 e via arquivo em disco)
    bytes_img = b"webp_conteudo_teste"
    b64_img = base64.b64encode(bytes_img).decode("ascii")
    _chamar(
        servidor,
        "aresta_alterar_campo_imagem",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "caminho_thumbnail",
            "caminho_novo": "imagens/thumb.webp",
            "imagem_base64": b64_img,
        },
    )
    assert raiz.caminho_thumbnail == "imagens/thumb.webp"
    assert model.obter_bytes_imagem("imagens/thumb.webp") == bytes_img

    bytes_subst = b"webp_substituido"
    _chamar(
        servidor,
        "aresta_alterar_imagem",
        {
            "caminho_relativo": "imagens/thumb.webp",
            "imagem_base64": base64.b64encode(bytes_subst).decode("ascii"),
        },
    )
    assert model.obter_bytes_imagem("imagens/thumb.webp") == bytes_subst

    with pytest.raises(RuntimeError, match="Informe 'imagem_base64' ou 'caminho_arquivo_disco'"):
        _chamar(
            servidor,
            "aresta_alterar_imagem",
            {"caminho_relativo": "imagens/thumb.webp"},
        )

    arq_disco = tmp_path / "mapa_disco.webp"
    arq_disco.write_bytes(b"bytes_disco")
    _chamar(
        servidor,
        "aresta_adicionar_mapa_arquivo",
        {
            "alvo": "uid_setor_base",
            "caminho_imagem_mapa": "imagens/mapa_disco.webp",
            "caminho_arquivo_disco": str(arq_disco),
            "indice": 1,
        },
    )
    assert len(raiz.picos[0].setores_ou_grupos[0].setor.conteudo.mapas) == 2

    # 3. Inserir imagem e botão no Markdown (com e sem novos bytes)
    _chamar(
        servidor,
        "aresta_inserir_imagem_markdown",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "descricao",
            "texto_novo": "![Foto](imagens/foto_md.webp)",
            "caminho_imagem": "imagens/foto_md.webp",
            "imagem_base64": b64_img,
        },
    )
    assert raiz.descricao == "![Foto](imagens/foto_md.webp)"

    _chamar(
        servidor,
        "aresta_inserir_imagem_markdown",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "descricao",
            "texto_novo": "![Foto existente](imagens/foto_md.webp)",
        },
    )
    assert raiz.descricao == "![Foto existente](imagens/foto_md.webp)"

    # Adicionar entidade sem campo uid (Pico)
    res_pico = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "picos", "valor": {"nome": "Pico 2"}},
    )
    assert res_pico["uid"] == ""
    assert len(raiz.picos) == 2

    _chamar(
        servidor,
        "aresta_inserir_botao_markdown",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "descricao",
            "texto_novo": "[Anexo](anexos/doc.pdf)",
            "caminho_anexo": "anexos/doc.pdf",
            "anexo_base64": b64_img,
        },
    )
    assert raiz.descricao == "[Anexo](anexos/doc.pdf)"

    # 4. Migrar setor do Pico para dentro do Grupo Base
    _chamar(
        servidor,
        "aresta_migrar_setor",
        {
            "alvo_origem": "picos.0",
            "campo_origem": "setores_ou_grupos",
            "indice_origem": 0,
            "alvo_destino": "uid_grupo_base",
            "campo_destino": "setores",
            "indice_destino": 0,
            "caminho_novo": "grupo_base_setor_base.md",
            "caminho_antigo": "setor_base.md",
        },
    )
    assert len(raiz.picos[0].setores_ou_grupos) == 1
    assert len(raiz.picos[0].setores_ou_grupos[0].grupo.conteudo.setores) == 1
    undo_stack.undo()
    assert len(raiz.picos[0].setores_ou_grupos) == 2
