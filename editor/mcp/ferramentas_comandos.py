# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
from pathlib import Path
from typing import Any

from google.protobuf.json_format import ParseDict

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.controllers.mapas_controller import MapasController
from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.mcp.servidor import ServidorMCP
from scripts.gerenciar_uids_lib import gerar_uid


def _decodificar_bytes_entrada(
    conteudo_base64: str | None = None, caminho_arquivo_disco: str | None = None
) -> bytes | None:
    if conteudo_base64:
        return base64.b64decode(conteudo_base64)
    if caminho_arquivo_disco:
        return Path(caminho_arquivo_disco).read_bytes()
    return None


def _garantir_uid_em_mensagem(obj: Any) -> str:
    """Garante que `obj` (ou seu subobjeto `.conteudo` / `.setor.conteudo` / `.grupo.conteudo`) possua UID NanoID."""
    if hasattr(obj, "DESCRIPTOR") and "uid" in obj.DESCRIPTOR.fields_by_name:
        if not getattr(obj, "uid", ""):
            obj.uid = gerar_uid()
        return str(obj.uid)

    if hasattr(obj, "conteudo"):
        return _garantir_uid_em_mensagem(obj.conteudo)

    if hasattr(obj, "WhichOneof") and "tipo" in obj.DESCRIPTOR.oneofs_by_name:
        variante = obj.WhichOneof("tipo")
        if variante:
            return _garantir_uid_em_mensagem(getattr(obj, variante))

    return ""


def _instanciar_valor_para_campo_repeated(msg: Any, campo: str, dados_item: Any) -> tuple[Any, str]:
    """
    Constrói o valor tipado (primitivo ou mensagem Protobuf) para inserção ou alteração
    em um campo `repeated`, preenchendo automaticamente o `uid` quando aplicável.
    """
    desc_campo = msg.DESCRIPTOR.fields_by_name.get(campo)
    eh_repeated = desc_campo is not None and (
        getattr(desc_campo, "label", None) == 3 or getattr(desc_campo, "is_repeated", False)
    )
    if desc_campo is None or not eh_repeated:
        raise ValueError(
            f"O campo '{campo}' não existe ou não é uma coleção repeated em '{msg.DESCRIPTOR.name}'."
        )

    if desc_campo.message_type is None:
        return dados_item, ""

    cls_item = desc_campo.message_type._concrete_class
    novo_obj = cls_item()
    dados = dict(dados_item) if isinstance(dados_item, dict) else {}
    nome_tipo = desc_campo.message_type.name

    if nome_tipo == "SetorOuGrupo" and "setor" not in dados and "grupo" not in dados:
        tipo_escolhido = str(dados.pop("tipo", "setor")).lower()
        alvo_conteudo = (
            novo_obj.grupo.conteudo if tipo_escolhido == "grupo" else novo_obj.setor.conteudo
        )
        ParseDict(dados, alvo_conteudo, ignore_unknown_fields=True)
    elif nome_tipo == "ArquivoSetor" and "conteudo" not in dados:
        ParseDict(dados, novo_obj.conteudo, ignore_unknown_fields=True)
    else:
        ParseDict(dados, novo_obj, ignore_unknown_fields=True)
        if nome_tipo == "Escalada":
            variante = novo_obj.WhichOneof("tipo")
            if not variante:
                novo_obj.via_esportiva.SetInParent()
                variante = "via_esportiva"
            if "nome" in dados:
                getattr(novo_obj, variante).nome = str(dados["nome"])

    uid_gerado = _garantir_uid_em_mensagem(novo_obj)
    return novo_obj, uid_gerado


def registrar_ferramentas_comandos(
    servidor: ServidorMCP,
    croqui_controller: CroquiController,
    mapas_controller: MapasController | None = None,
) -> None:
    """
    Registra no `ServidorMCP` o catálogo de ferramentas 1:1 mapeadas aos comandos
    do editor, despachando exclusivamente via `CroquiController` e `MapasController`.
    """
    model = croqui_controller.model
    ctrl_mapas = mapas_controller or MapasController(model, croqui_controller.undo_stack)

    def _alterar_primitivo(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        valor = args["valor"]
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        if campo not in msg.DESCRIPTOR.fields_by_name:
            raise ValueError(f"Campo '{campo}' não existe na mensagem '{msg.DESCRIPTOR.name}'.")
        valor_antigo = getattr(msg, campo)
        croqui_controller.alterar_primitivo(msg, campo, valor_antigo, valor)
        return {
            "status": "ok",
            "caminho": caminho,
            "campo": campo,
            "valor": getattr(msg, campo),
        }

    def _alterar_oneof(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        oneof = str(args["oneof"])
        campo_novo = args.get("campo_novo")
        valores_iniciais = args.get("valores_iniciais") or {}
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=oneof)
        if oneof not in msg.DESCRIPTOR.oneofs_by_name:
            raise ValueError(f"Oneof '{oneof}' não existe na mensagem '{msg.DESCRIPTOR.name}'.")
        nome_antigo = msg.WhichOneof(oneof)
        valor_antigo = getattr(msg, nome_antigo) if nome_antigo else None

        if campo_novo:
            campo_novo_str = str(campo_novo)
            desc_novo = msg.DESCRIPTOR.fields_by_name.get(campo_novo_str)
            if desc_novo is None:
                raise ValueError(
                    f"Campo '{campo_novo_str}' não existe na mensagem '{msg.DESCRIPTOR.name}'."
                )
            cls_novo = desc_novo.message_type._concrete_class
            valor_novo = cls_novo()
            if isinstance(valores_iniciais, dict) and valores_iniciais:
                ParseDict(valores_iniciais, valor_novo, ignore_unknown_fields=True)
            _garantir_uid_em_mensagem(valor_novo)
        else:
            campo_novo_str = None
            valor_novo = None

        croqui_controller.alterar_oneof(
            msg, oneof, nome_antigo, valor_antigo, campo_novo_str, valor_novo
        )
        return {
            "status": "ok",
            "caminho": caminho,
            "oneof": oneof,
            "campo_ativo": msg.WhichOneof(oneof),
        }

    def _adicionar_repeated(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        valor_bruto = args.get("valor")
        indice = args.get("indice")
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        item_proto, uid_gerado = _instanciar_valor_para_campo_repeated(msg, campo, valor_bruto)
        colecao = getattr(msg, campo)
        idx_final = len(colecao) if indice is None or int(indice) < 0 else int(indice)
        croqui_controller.adicionar_repeated(msg, campo, idx_final, item_proto)
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        caminho_item = f"{caminho}.{campo}.{idx_final}" if caminho else f"{campo}.{idx_final}"
        return {
            "status": "ok",
            "uid": uid_gerado,
            "caminho": caminho_item,
            "indice": idx_final,
        }

    def _remover_repeated(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        indice = int(args["indice"])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        colecao = getattr(msg, campo)
        if indice < 0 or indice >= len(colecao):
            raise IndexError(
                f"Índice fora de alcance ({indice}) para o campo '{campo}' de tamanho {len(colecao)}."
            )
        croqui_controller.remover_repeated(msg, campo, indice, colecao[indice])
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "caminho": caminho,
            "campo": campo,
            "indice_removido": indice,
        }

    def _mover_repeated(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        indice_origem = int(args["indice_origem"])
        indice_destino = int(args["indice_destino"])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        croqui_controller.mover_repeated_para_posicao(msg, campo, indice_origem, indice_destino)
        return {
            "status": "ok",
            "caminho": caminho,
            "campo": campo,
            "indice_origem": indice_origem,
            "indice_destino": indice_destino,
        }

    def _alterar_item_repeated(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        indice = int(args["indice"])
        valor_bruto = args["valor"]
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        colecao = getattr(msg, campo)
        valor_antigo = colecao[indice]
        valor_novo, _ = _instanciar_valor_para_campo_repeated(msg, campo, valor_bruto)
        croqui_controller.alterar_repeated_item(msg, campo, indice, valor_antigo, valor_novo)
        return {
            "status": "ok",
            "caminho": caminho,
            "campo": campo,
            "indice": indice,
        }

    def _alterar_multiplos_repeated(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        alteracoes_in = list(args.get("alteracoes") or [])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        colecao = getattr(msg, campo)
        lista_tuplas: list[tuple[int, Any, Any]] = []
        for item in alteracoes_in:
            idx = int(item["indice"])
            val_novo, _ = _instanciar_valor_para_campo_repeated(msg, campo, item["valor"])
            lista_tuplas.append((idx, colecao[idx], val_novo))
        croqui_controller.alterar_multiplos_repeated_items(msg, campo, lista_tuplas)
        return {
            "status": "ok",
            "caminho": caminho,
            "campo": campo,
            "quantidade": len(lista_tuplas),
        }

    def _renomear_escalada(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args["alvo"])
        nome_novo = str(args["nome_novo"])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome="nome")
        nome_antigo = str(getattr(msg, "nome", ""))
        croqui_controller.renomear_escalada(msg, nome_antigo, nome_novo, pode_mesclar=False)
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "caminho": caminho,
            "nome_antigo": nome_antigo,
            "nome_novo": nome_novo,
        }

    def _migrar_setor(args: dict[str, Any]) -> dict[str, Any]:
        pai_origem, cam_origem = resolver_alvo_mcp(
            model, str(args["alvo_origem"]), campo_nome=str(args["campo_origem"])
        )
        pai_destino, cam_destino = resolver_alvo_mcp(
            model, str(args["alvo_destino"]), campo_nome=str(args["campo_destino"])
        )
        croqui_controller.migrar_setor(
            pai_origem=pai_origem,
            campo_origem=str(args["campo_origem"]),
            indice_origem=int(args["indice_origem"]),
            pai_destino=pai_destino,
            campo_destino=str(args["campo_destino"]),
            indice_destino=int(args.get("indice_destino", 0)),
            caminho_novo=args.get("caminho_novo"),
            caminho_antigo=args.get("caminho_antigo"),
        )
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "origem": cam_origem,
            "destino": cam_destino,
        }

    def _alterar_campo_imagem(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        caminho_novo = str(args["caminho_novo"])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        caminho_antigo = str(getattr(msg, campo, ""))
        bytes_antigo = model.obter_bytes_imagem(caminho_antigo) if caminho_antigo else None
        bytes_novo = _decodificar_bytes_entrada(
            args.get("imagem_base64"), args.get("caminho_arquivo_disco")
        )
        croqui_controller.alterar_campo_imagem(
            msg, campo, caminho_antigo, bytes_antigo, caminho_novo, bytes_novo
        )
        return {
            "status": "ok",
            "caminho": caminho,
            "campo": campo,
            "caminho_novo": caminho_novo,
        }

    def _inserir_imagem_markdown(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        texto_novo = str(args["texto_novo"])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        texto_antigo = str(getattr(msg, campo, ""))
        bytes_img = _decodificar_bytes_entrada(
            args.get("imagem_base64"), args.get("caminho_arquivo_disco")
        )
        croqui_controller.inserir_imagem_markdown(
            msg,
            campo,
            texto_antigo,
            texto_novo,
            caminho_imagem=args.get("caminho_imagem"),
            bytes_imagem=bytes_img,
        )
        return {"status": "ok", "caminho": caminho, "campo": campo}

    def _inserir_botao_markdown(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        texto_novo = str(args["texto_novo"])
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        texto_antigo = str(getattr(msg, campo, ""))
        bytes_anexo = _decodificar_bytes_entrada(
            args.get("anexo_base64"), args.get("caminho_arquivo_disco")
        )
        croqui_controller.inserir_botao_markdown(
            msg,
            campo,
            texto_antigo,
            texto_novo,
            caminho_anexo=args.get("caminho_anexo"),
            bytes_anexo=bytes_anexo,
        )
        return {"status": "ok", "caminho": caminho, "campo": campo}

    def _adicionar_mapa_arquivo(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        caminho_img = str(args["caminho_imagem_mapa"])
        indice = int(args.get("indice", 0))
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome="mapas")
        bytes_img = _decodificar_bytes_entrada(
            args.get("imagem_base64"), args.get("caminho_arquivo_disco")
        )
        novo_mapa = croqui_pb2.Mapa(caminho_imagem_mapa=caminho_img)
        caminho_abs = Path(args.get("caminho_arquivo_disco") or caminho_img)
        croqui_controller.adicionar_mapa_com_arquivo(
            msg, "mapas", indice, novo_mapa, caminho_abs, bytes_img
        )
        caminho_mapa = f"{caminho}.mapas.{indice}" if caminho else f"mapas.{indice}"
        return {
            "status": "ok",
            "caminho": caminho_mapa,
            "caminho_imagem_mapa": caminho_img,
        }

    def _vincular_referencia_mapa(args: dict[str, Any]) -> dict[str, Any]:
        alvo_mapa = str(args["alvo_mapa"])
        alvo_uid = str(args["alvo_uid"])
        pontos_uids = [str(p) for p in (args.get("pontos_uids") or [])]
        msg_mapa, caminho = resolver_alvo_mcp(model, alvo_mapa)
        nova_ref = croqui_pb2.Mapa.Referencia(alvo_uid=alvo_uid, pontos_uids=pontos_uids)
        ctrl_mapas.adicionar_referencia(msg_mapa, nova_ref)
        return {
            "status": "ok",
            "caminho_mapa": caminho,
            "alvo_uid": alvo_uid,
            "pontos_uids": pontos_uids,
        }

    def _iniciar_macro(args: dict[str, Any]) -> dict[str, Any]:
        descricao = str(args.get("descricao") or "Operação MCP em lote")
        croqui_controller.iniciar_grupo_undo(descricao)
        return {"status": "ok", "macro_ativa": True, "descricao": descricao}

    def _finalizar_macro(_args: dict[str, Any]) -> dict[str, Any]:
        croqui_controller.finalizar_grupo_undo()
        return {"status": "ok", "macro_ativa": False}

    servidor.registrar_ferramenta(
        nome="aresta_alterar_primitivo",
        descricao="Altera um campo primitivo (string, número, booleano, enum) de uma entidade por UID ou caminho.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "UID de 14 caracteres ou caminho da mensagem.",
                },
                "campo": {"type": "string", "description": "Nome do campo Protobuf."},
                "valor": {"description": "Novo valor a ser atribuído."},
            },
            "required": ["alvo", "campo", "valor"],
        },
        manipulador=_alterar_primitivo,
    )
    servidor.registrar_ferramenta(
        nome="aresta_alterar_oneof",
        descricao="Altera a variante ativa de um campo oneof (ex: tipo da escalada entre via_esportiva, boulder, etc.).",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "oneof": {"type": "string"},
                "campo_novo": {"type": ["string", "null"]},
                "valores_iniciais": {"type": "object"},
            },
            "required": ["alvo", "oneof"],
        },
        manipulador=_alterar_oneof,
    )
    servidor.registrar_ferramenta(
        nome="aresta_adicionar_repeated",
        descricao="Adiciona um item a uma coleção repeated gerando e retornando imediatamente o UID NanoID.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "valor": {},
                "indice": {"type": "integer"},
            },
            "required": ["alvo", "campo"],
        },
        manipulador=_adicionar_repeated,
    )
    servidor.registrar_ferramenta(
        nome="aresta_remover_repeated",
        descricao="Remove um item de uma coleção repeated pelo seu índice.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "indice": {"type": "integer"},
            },
            "required": ["alvo", "campo", "indice"],
        },
        manipulador=_remover_repeated,
    )
    servidor.registrar_ferramenta(
        nome="aresta_mover_repeated",
        descricao="Reordena um item dentro de uma coleção repeated de indice_origem para indice_destino.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "indice_origem": {"type": "integer"},
                "indice_destino": {"type": "integer"},
            },
            "required": ["alvo", "campo", "indice_origem", "indice_destino"],
        },
        manipulador=_mover_repeated,
    )
    servidor.registrar_ferramenta(
        nome="aresta_alterar_item_repeated",
        descricao="Substitui um item específico de uma coleção repeated pelo seu índice.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "indice": {"type": "integer"},
                "valor": {},
            },
            "required": ["alvo", "campo", "indice", "valor"],
        },
        manipulador=_alterar_item_repeated,
    )
    servidor.registrar_ferramenta(
        nome="aresta_alterar_multiplos_repeated",
        descricao="Substitui múltiplos itens de uma coleção repeated em um único comando atômico.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "alteracoes": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["alvo", "campo", "alteracoes"],
        },
        manipulador=_alterar_multiplos_repeated,
    )
    servidor.registrar_ferramenta(
        nome="aresta_renomear_escalada",
        descricao="Renomeia uma escalada por UID ou caminho mantendo todas as referências de mapas sincronizadas.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "nome_novo": {"type": "string"},
            },
            "required": ["alvo", "nome_novo"],
        },
        manipulador=_renomear_escalada,
    )
    servidor.registrar_ferramenta(
        nome="aresta_migrar_setor",
        descricao="Migra atomicamente um setor entre um Pico e um Grupo.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo_origem": {"type": "string"},
                "campo_origem": {"type": "string"},
                "indice_origem": {"type": "integer"},
                "alvo_destino": {"type": "string"},
                "campo_destino": {"type": "string"},
                "indice_destino": {"type": "integer"},
                "caminho_novo": {"type": "string"},
                "caminho_antigo": {"type": "string"},
            },
            "required": [
                "alvo_origem",
                "campo_origem",
                "indice_origem",
                "alvo_destino",
                "campo_destino",
            ],
        },
        manipulador=_migrar_setor,
    )
    servidor.registrar_ferramenta(
        nome="aresta_alterar_campo_imagem",
        descricao="Altera um campo de caminho de imagem gerenciando os bytes em RAM.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "caminho_novo": {"type": "string"},
                "imagem_base64": {"type": "string"},
                "caminho_arquivo_disco": {"type": "string"},
            },
            "required": ["alvo", "campo", "caminho_novo"],
        },
        manipulador=_alterar_campo_imagem,
    )
    servidor.registrar_ferramenta(
        nome="aresta_inserir_imagem_markdown",
        descricao="Atualiza um campo Markdown inserindo uma imagem gerenciada em RAM.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "texto_novo": {"type": "string"},
                "caminho_imagem": {"type": "string"},
                "imagem_base64": {"type": "string"},
            },
            "required": ["alvo", "campo", "texto_novo"],
        },
        manipulador=_inserir_imagem_markdown,
    )
    servidor.registrar_ferramenta(
        nome="aresta_inserir_botao_markdown",
        descricao="Atualiza um campo Markdown inserindo um botão/link com anexo gerenciado em RAM.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "texto_novo": {"type": "string"},
                "caminho_anexo": {"type": "string"},
                "anexo_base64": {"type": "string"},
            },
            "required": ["alvo", "campo", "texto_novo"],
        },
        manipulador=_inserir_botao_markdown,
    )
    servidor.registrar_ferramenta(
        nome="aresta_adicionar_mapa_arquivo",
        descricao="Adiciona um novo mapa com imagem associada em RAM.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "caminho_imagem_mapa": {"type": "string"},
                "imagem_base64": {"type": "string"},
                "caminho_arquivo_disco": {"type": "string"},
                "indice": {"type": "integer"},
            },
            "required": ["alvo", "caminho_imagem_mapa"],
        },
        manipulador=_adicionar_mapa_arquivo,
    )
    servidor.registrar_ferramenta(
        nome="aresta_vincular_referencia_mapa",
        descricao="Adiciona uma referência em um mapa vinculando alvo_uid aos pontos_uids.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo_mapa": {"type": "string"},
                "alvo_uid": {"type": "string"},
                "pontos_uids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["alvo_mapa", "alvo_uid", "pontos_uids"],
        },
        manipulador=_vincular_referencia_mapa,
    )
    servidor.registrar_ferramenta(
        nome="aresta_iniciar_macro",
        descricao="Inicia um agrupamento transacional CmdMacro na pilha de histórico.",
        esquema_entrada={
            "type": "object",
            "properties": {"descricao": {"type": "string"}},
        },
        manipulador=_iniciar_macro,
    )
    servidor.registrar_ferramenta(
        nome="aresta_finalizar_macro",
        descricao="Finaliza o agrupamento transacional CmdMacro atual na pilha de histórico.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_finalizar_macro,
    )
