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


def test_aresta_alterar_primitivo_e_alterar_oneof_com_undo_redo(qapp, tmp_path: Path):
    """Testa aresta_alterar_primitivo (por UID e caminho) e aresta_alterar_oneof com suporte a undo/redo."""
    model, undo_stack, _, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    # 1. Alterar primitivo na raiz e em uma escalada por UID
    res_raiz = _chamar(
        servidor,
        "aresta_alterar_primitivo",
        {"alvo": "uid_croqui_raiz", "campo": "nome", "valor": "Croqui Novo"},
    )
    assert res_raiz["valor"] == "Croqui Novo"
    assert raiz.nome == "Croqui Novo"

    res_via = _chamar(
        servidor,
        "aresta_alterar_primitivo",
        {"alvo": "uid_via_base01", "campo": "extensao", "valor": 30},
    )
    assert res_via["valor"] == 30
    assert (
        raiz.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva.extensao == 30
    )

    # Campo inexistente deve falhar
    with pytest.raises(RuntimeError, match="Campo 'inexistente'"):
        _chamar(
            servidor,
            "aresta_alterar_primitivo",
            {"alvo": "uid_croqui_raiz", "campo": "inexistente", "valor": "x"},
        )

    # 2. Alterar oneof da escalada de via_esportiva para boulder (e depois limpar oneof)
    res_oneof = _chamar(
        servidor,
        "aresta_alterar_oneof",
        {
            "alvo": "uid_via_base01",
            "oneof": "tipo",
            "campo_novo": "boulder",
            "valores_iniciais": {"nome": "Boulder Convertido"},
        },
    )
    assert res_oneof["campo_ativo"] == "boulder"
    esc_proxy = raiz.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0]
    assert esc_proxy.WhichOneof("tipo") == "boulder"
    assert esc_proxy.boulder.nome == "Boulder Convertido"

    undo_stack.undo()
    assert esc_proxy.WhichOneof("tipo") == "via_esportiva"
    assert esc_proxy.via_esportiva.extensao == 30

    # Limpar oneof (campo_novo vazio) e erros de validação
    res_limpar = _chamar(
        servidor,
        "aresta_alterar_oneof",
        {"alvo": "uid_via_base01", "oneof": "tipo", "campo_novo": None},
    )
    assert res_limpar["campo_ativo"] is None
    undo_stack.undo()

    with pytest.raises(RuntimeError, match="Oneof 'inexistente'"):
        _chamar(
            servidor,
            "aresta_alterar_oneof",
            {"alvo": "uid_via_base01", "oneof": "inexistente", "campo_novo": "boulder"},
        )

    with pytest.raises(RuntimeError, match="Campo 'invalido'"):
        _chamar(
            servidor,
            "aresta_alterar_oneof",
            {"alvo": "uid_via_base01", "oneof": "tipo", "campo_novo": "invalido"},
        )


def test_operacoes_repeated_geram_uid_nanoid_e_suportam_undo_redo(qapp, tmp_path: Path):
    """Testa adicionar, remover, mover, alterar item e alterar múltiplos itens repeated com geração de UID."""
    model, undo_stack, _, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    # 1. Adicionar escalada por UID do setor (atalho ergonômico e geração automática de UID)
    res_esc = _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {
            "alvo": "uid_setor_base",
            "campo": "escaladas",
            "valor": {"nome": "Nova Via MCP"},
        },
    )
    novo_uid_esc = res_esc["uid"]
    assert len(novo_uid_esc) == 14
    assert model.indice_uids.existe(novo_uid_esc)

    # Adicionar setor em grupo (atalho ergonômico em ArquivoSetor) e SetorOuGrupo no pico
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

    # 2. Adicionar primitivo em repeated (creditos)
    _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "valor": "Autor 1"},
    )
    _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "valor": "Autor 2"},
    )
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

    # 4. Alterar item único repeated
    _chamar(
        servidor,
        "aresta_alterar_item_repeated",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "creditos",
            "indice": 0,
            "valor": "Autor Principal",
        },
    )
    assert list(raiz.creditos) == ["Autor Principal", "Autor 1"]

    # 5. Alterar múltiplos itens repeated
    _chamar(
        servidor,
        "aresta_alterar_multiplos_repeated",
        {
            "alvo": "uid_croqui_raiz",
            "campo": "creditos",
            "alteracoes": [
                {"indice": 0, "valor": "Coautor A"},
                {"indice": 1, "valor": "Coautor B"},
            ],
        },
    )
    assert list(raiz.creditos) == ["Coautor A", "Coautor B"]

    # 6. Remover item repeated e validações de erro
    _chamar(
        servidor,
        "aresta_remover_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "indice": 1},
    )
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


def test_renomear_migrar_imagens_markdown_e_mapas(qapp, tmp_path: Path):
    """Testa renomear escalada, migrar setor, alterar imagens, markdown e operações de mapas."""
    model, undo_stack, croqui_ctrl, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    # Registrar sem passar mapas_controller explícito também deve instanciar MapasController automaticamente
    servidor_auto = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_comandos(servidor_auto, croqui_ctrl)

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

    # 2. Renomear escalada por UID
    res_ren = _chamar(
        servidor,
        "aresta_renomear_escalada",
        {"alvo": "uid_via_base01", "nome_novo": "Via Renomeada MCP"},
    )
    assert res_ren["nome_novo"] == "Via Renomeada MCP"
    assert (
        raiz.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva.nome
        == "Via Renomeada MCP"
    )

    # 3. Alterar campo de imagem (via base64 e via arquivo em disco)
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

    # 4. Inserir imagem e botão no Markdown (com e sem novos bytes)
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

    # 5. Migrar setor do Pico para dentro do Grupo Base
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


def test_aresta_iniciar_e_finalizar_macro_agrupa_comandos_atomicamente(qapp, tmp_path: Path):
    """Testa que múltiplos comandos MCP entre aresta_iniciar_macro e aresta_finalizar_macro geram um único CmdMacro."""
    model, undo_stack, _, _, servidor = _montar_ambiente_comandos(tmp_path)
    raiz = model.obter_croqui_readonly()

    _chamar(servidor, "aresta_iniciar_macro", {"descricao": "Pacote Atômico MCP"})
    _chamar(
        servidor,
        "aresta_alterar_primitivo",
        {"alvo": "uid_croqui_raiz", "campo": "nome", "valor": "Croqui em Lote"},
    )
    _chamar(
        servidor,
        "aresta_adicionar_repeated",
        {"alvo": "uid_croqui_raiz", "campo": "creditos", "valor": "Crédito Lote"},
    )
    _chamar(
        servidor,
        "aresta_vincular_referencia_mapa",
        {
            "alvo_mapa": "uid_setor_base.mapas.0",
            "alvo_uid": "uid_via_base01",
            "pontos_uids": ["uid_poi_base01"],
        },
    )
    # Enquanto a macro está aberta, a pilha principal ainda tem 0 comandos
    assert undo_stack.count() == 0

    _chamar(servidor, "aresta_finalizar_macro", {})
    assert undo_stack.count() == 1
    assert raiz.nome == "Croqui em Lote"
    assert list(raiz.creditos) == ["Crédito Lote"]

    # Um único undo reverte todas as 3 mutações (CroquiController + MapasController)
    undo_stack.undo()
    assert raiz.nome == "Croqui Inicial"
    assert len(raiz.creditos) == 0
    assert len(raiz.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0].referencias) == 0
