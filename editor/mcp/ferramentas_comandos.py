# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
from pathlib import Path
from typing import Any

from google.protobuf.json_format import ParseDict

from aresta_api.proto.generated import croqui_pb2
from editor.commands.comandos_protobuf import garantir_uids_em_mensagem
from editor.controllers.croqui_controller import CroquiController
from editor.controllers.mapas_controller import MapasController
from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.mcp.servidor import ServidorMCP


def _decodificar_bytes_entrada(
    conteudo_base64: str | None = None, caminho_arquivo_disco: str | None = None
) -> bytes | None:
    if conteudo_base64:
        return base64.b64decode(conteudo_base64)
    if caminho_arquivo_disco:
        return Path(caminho_arquivo_disco).read_bytes()
    return None


def _instanciar_mensagem_de_dict(desc_msg: Any, dados_brutos: dict[str, Any]) -> tuple[Any, str]:
    """
    Constrói uma mensagem Protobuf a partir de um dicionário JSON, suportando
    atalhos ergonômicos para wrappers (`SetorOuGrupo`, `ArquivoSetor`, `ArquivoGrupo`, `Escalada`)
    e gerando automaticamente o `uid` NanoID quando aplicável.
    """
    cls_item = desc_msg._concrete_class
    novo_obj = cls_item()
    dados = dict(dados_brutos)
    nome_tipo = desc_msg.name

    if nome_tipo == "SetorOuGrupo" and "setor" not in dados and "grupo" not in dados:
        tipo_escolhido = str(dados.pop("tipo", "setor")).lower()
        alvo_conteudo = (
            novo_obj.grupo.conteudo if tipo_escolhido == "grupo" else novo_obj.setor.conteudo
        )
        ParseDict(dados, alvo_conteudo, ignore_unknown_fields=False)
    elif (
        nome_tipo in ("ArquivoSetor", "ArquivoGrupo")
        and "conteudo" not in dados
        and "caminho" not in dados
    ):
        ParseDict(dados, novo_obj.conteudo, ignore_unknown_fields=False)
    elif nome_tipo == "Escalada" and not any(
        k in dados
        for k in (
            "via_esportiva",
            "via_movel",
            "boulder",
            "via_multiplas_enfiadas",
            "highline",
        )
    ):
        tipo_esc = str(dados.pop("tipo", "via_esportiva"))
        nomes_variantes = [f.name for f in novo_obj.DESCRIPTOR.oneofs_by_name["tipo"].fields]
        if tipo_esc not in nomes_variantes:
            opcoes = ", ".join(nomes_variantes)
            raise ValueError(
                f"Variante de escalada '{tipo_esc}' inválida. Opções válidas: {opcoes}."
            )
        sub_var = getattr(novo_obj, tipo_esc)
        sub_var.SetInParent()
        ParseDict(dados, sub_var, ignore_unknown_fields=False)
    else:
        ParseDict(dados, novo_obj, ignore_unknown_fields=False)

    uid_gerado = garantir_uids_em_mensagem(novo_obj)
    return novo_obj, uid_gerado


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

    dados_dict = dict(dados_item) if isinstance(dados_item, dict) else {}
    return _instanciar_mensagem_de_dict(desc_campo.message_type, dados_dict)


def _coagir_valor_para_campo(msg: Any, nome_campo: str, valor_bruto: Any) -> Any:
    """
    Converte um valor vindo do JSON-RPC (dict de submensagem, nome textual de Enum, etc.)
    para o tipo nativo esperado pelo `CmdAlterarCampo` antes de despachar ao Controller.
    """
    if valor_bruto is None:
        return None

    desc = msg.DESCRIPTOR
    if "." in nome_campo and not nome_campo.startswith("ext_"):
        campo_base, _ = nome_campo.split(".", 1)
        if campo_base in desc.fields_by_name:
            val_item, _ = _instanciar_valor_para_campo_repeated(msg, campo_base, valor_bruto)
            return val_item

    if nome_campo in desc.oneofs_by_name:
        if isinstance(valor_bruto, dict) and len(valor_bruto) == 1:
            var_nome, dados_var = next(iter(valor_bruto.items()))
            val_var = _coagir_valor_para_campo(msg, str(var_nome), dados_var)
            return (str(var_nome), val_var)
        raise ValueError(
            f"Para alterar o oneof '{nome_campo}', informe um dicionário com a variante "
            f"(ex: {{'boulder': {{'nome': '...'}}}}) ou altere o campo da variante diretamente."
        )

    desc_campo = desc.fields_by_name.get(nome_campo)
    if desc_campo is None:
        return valor_bruto

    eh_repeated = getattr(desc_campo, "label", None) == 3 or getattr(
        desc_campo, "is_repeated", False
    )
    if eh_repeated:
        return valor_bruto

    if desc_campo.message_type is not None and isinstance(valor_bruto, dict):
        obj_msg, _ = _instanciar_mensagem_de_dict(desc_campo.message_type, valor_bruto)
        return obj_msg

    if desc_campo.enum_type is not None and isinstance(valor_bruto, str):
        val_enum = desc_campo.enum_type.values_by_name.get(
            valor_bruto
        ) or desc_campo.enum_type.values_by_name.get(valor_bruto.upper())
        if val_enum is None:
            opcoes = ", ".join(v.name for v in desc_campo.enum_type.values)
            raise ValueError(
                f"Valor de enum '{valor_bruto}' inválido para o campo '{nome_campo}' "
                f"({desc_campo.enum_type.name}). Opções válidas: {opcoes}."
            )
        return int(val_enum.number)

    return valor_bruto


def registrar_ferramentas_comandos(
    servidor: ServidorMCP,
    croqui_controller: CroquiController,
    mapas_controller: MapasController | None = None,
) -> None:
    """
    Registra no `ServidorMCP` o catálogo de ferramentas canônicas mapeadas à interface
    de `CroquiController` e `MapasController`.
    """
    model = croqui_controller.model
    ctrl_mapas = mapas_controller or MapasController(model, croqui_controller.undo_stack)

    def _alterar_campo(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        mapa_entrada: dict[str, Any] = {}
        if isinstance(args.get("campos"), dict):
            mapa_entrada.update(args["campos"])
        if args.get("campo"):
            mapa_entrada[str(args["campo"])] = args.get("valor")
        if not mapa_entrada:
            raise ValueError(
                "Informe 'campo' (com 'valor') ou o dicionário 'campos' para alterar."
            )

        mapa_coagido: dict[str, Any] = {}
        ultimo_caminho = ""
        for nome_c, val_bruto in mapa_entrada.items():
            msg_c, ultimo_caminho = resolver_alvo_mcp(model, alvo, campo_nome=nome_c)
            mapa_coagido[nome_c] = _coagir_valor_para_campo(msg_c, nome_c, val_bruto)

        croqui_controller.alterar_campo(alvo=alvo, campos=mapa_coagido)
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "alvo": alvo,
            "caminho": ultimo_caminho,
            "campos_alterados": list(mapa_coagido.keys()),
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
            "tamanho": len(colecao),
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
            "tamanho": len(colecao),
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

    def _alterar_imagem(args: dict[str, Any]) -> dict[str, Any]:
        caminho_rel = str(args["caminho_relativo"])
        bytes_novo = _decodificar_bytes_entrada(
            args.get("imagem_base64"), args.get("caminho_arquivo_disco")
        )
        if bytes_novo is None:
            raise ValueError(
                "Informe 'imagem_base64' ou 'caminho_arquivo_disco' para atualizar a imagem."
            )
        croqui_controller.substituir_imagem(caminho_rel, bytes_novo)
        return {
            "status": "ok",
            "caminho_relativo": caminho_rel,
            "tamanho_bytes": len(bytes_novo),
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

    servidor.registrar_ferramenta(
        nome="aresta_alterar_campo",
        descricao=(
            "Altera um ou mais campos de uma entidade por UID ou caminho (primitivos, "
            "enums por nome, submensagens via dict, oneofs ou itens indexados 'campo.0'). "
            "Quando 'campos' possui múltiplas chaves, agrupa a alteração em um único comando atômico."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "UID NanoID ou caminho da mensagem alvo (vazio ou 'root' para a raiz).",
                },
                "campo": {
                    "type": "string",
                    "description": "Nome do campo único a alterar (ex: 'nome', 'dificuldade', 'boulder', 'creditos.0').",
                },
                "valor": {
                    "description": "Novo valor para 'campo' (primitivo, nome de Enum, dict para submensagem/oneof ou null)."
                },
                "campos": {
                    "type": "object",
                    "description": "Dicionário {campo: valor} para alterar múltiplos campos atomicamente no mesmo alvo.",
                },
            },
            "required": ["alvo"],
        },
        manipulador=_alterar_campo,
    )
    servidor.registrar_ferramenta(
        nome="aresta_adicionar_repeated",
        descricao="Adiciona um item a uma coleção repeated gerando e retornando imediatamente o UID NanoID e o tamanho atualizado.",
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
        descricao="Remove um item de uma coleção repeated pelo seu índice e retorna o tamanho atualizado.",
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
        nome="aresta_alterar_imagem",
        descricao="Substitui ou adiciona os bytes de uma imagem (.webp) em memória RAM.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "caminho_relativo": {"type": "string"},
                "imagem_base64": {"type": "string"},
                "caminho_arquivo_disco": {"type": "string"},
            },
            "required": ["caminho_relativo"],
        },
        manipulador=_alterar_imagem,
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
