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


def _normalizar_dict_proto(desc_msg: Any, dados_brutos: dict[str, Any]) -> dict[str, Any]:
    """
    Normaliza recursivamente um dicionário JSON para ParseDict do Protobuf,
    expandindo atalhos ergonômicos (`SetorOuGrupo`, `ArquivoSetor`, `ArquivoGrupo`, `Escalada`)
    e convertendo valores textuais de Enum (case-insensitive) para seus nomes canônicos.
    """
    dados = dict(dados_brutos)
    nome_tipo = desc_msg.name

    if nome_tipo == "SetorOuGrupo" and "setor" not in dados and "grupo" not in dados:
        tipo_escolhido = str(dados.pop("tipo", "setor")).lower()
        chave_ramo = "grupo" if tipo_escolhido == "grupo" else "setor"
        dados = {chave_ramo: {"conteudo": dados}}
    elif (
        nome_tipo in ("ArquivoSetor", "ArquivoGrupo")
        and "conteudo" not in dados
        and "caminho" not in dados
    ):
        dados = {"conteudo": dados}
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
        uid_esc = dados.pop("uid", None)
        tipo_esc = str(dados.pop("tipo", "via_esportiva"))
        nomes_variantes = [f.name for f in desc_msg.oneofs_by_name["tipo"].fields]
        if tipo_esc not in nomes_variantes:
            opcoes = ", ".join(nomes_variantes)
            raise ValueError(
                f"Variante de escalada '{tipo_esc}' inválida. Opções válidas: {opcoes}."
            )
        dados = {tipo_esc: dados}
        if uid_esc:
            dados["uid"] = str(uid_esc)

    resultado: dict[str, Any] = {}
    for chave, valor in dados.items():
        f_desc = desc_msg.fields_by_name.get(chave)
        if f_desc is not None and f_desc.enum_type is not None and isinstance(valor, str):
            val_enum = f_desc.enum_type.values_by_name.get(valor.upper())
            resultado[chave] = val_enum.name if val_enum is not None else valor
        elif f_desc is not None and f_desc.message_type is not None and isinstance(valor, list):
            resultado[chave] = [
                _normalizar_dict_proto(f_desc.message_type, item)
                if isinstance(item, dict)
                else item
                for item in valor
            ]
        elif f_desc is not None and f_desc.message_type is not None and isinstance(valor, dict):
            resultado[chave] = _normalizar_dict_proto(f_desc.message_type, valor)
        else:
            resultado[chave] = valor
    return resultado


def _instanciar_mensagem_de_dict(desc_msg: Any, dados_brutos: dict[str, Any]) -> tuple[Any, str]:
    """
    Constrói uma mensagem Protobuf a partir de um dicionário JSON, suportando
    atalhos ergonômicos para wrappers (`SetorOuGrupo`, `ArquivoSetor`, `ArquivoGrupo`, `Escalada`)
    e gerando automaticamente o `uid` NanoID quando aplicável.
    """
    cls_item = desc_msg._concrete_class
    novo_obj = cls_item()
    dados_norm = _normalizar_dict_proto(desc_msg, dados_brutos)
    ParseDict(dados_norm, novo_obj, ignore_unknown_fields=False)
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
        if isinstance(valor_bruto, list):
            return [
                _instanciar_valor_para_campo_repeated(msg, nome_campo, item)[0]
                for item in valor_bruto
            ]
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
    cliente_overpass: Any = None,
) -> None:
    """
    Registra no `ServidorMCP` o catálogo de ferramentas canônicas mapeadas à interface
    de `CroquiController` e `MapasController`.
    """
    model = croqui_controller.model
    ctrl_mapas = mapas_controller or MapasController(model, croqui_controller.undo_stack)

    def _preparar_mapa_coagido(item_args: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        alvo = str(item_args.get("alvo", ""))
        mapa_entrada: dict[str, Any] = {}
        if isinstance(item_args.get("campos"), dict):
            mapa_entrada.update(item_args["campos"])
        if item_args.get("campo"):
            mapa_entrada[str(item_args["campo"])] = item_args.get("valor")
        if not mapa_entrada:
            raise ValueError("Informe 'campo' (com 'valor') ou o dicionário 'campos' para alterar.")

        mapa_coagido: dict[str, Any] = {}
        ultimo_caminho = ""
        for nome_c, val_bruto in mapa_entrada.items():
            msg_c, ultimo_caminho = resolver_alvo_mcp(model, alvo, campo_nome=nome_c)
            mapa_coagido[nome_c] = _coagir_valor_para_campo(msg_c, nome_c, val_bruto)
        return alvo, ultimo_caminho, mapa_coagido

    def _alterar_campo(args: dict[str, Any]) -> dict[str, Any]:
        alvo, ultimo_caminho, mapa_coagido = _preparar_mapa_coagido(args)
        croqui_controller.alterar_campo(
            alvo=alvo,
            campos=mapa_coagido,
            preservar_campos_compativeis=bool(args.get("preservar_campos_compativeis", False)),
        )
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "alvo": alvo,
            "caminho": ultimo_caminho,
            "campos_alterados": list(mapa_coagido.keys()),
        }

    def _alterar_em_lote(args: dict[str, Any]) -> dict[str, Any]:
        operacoes_brutas = args.get("operacoes")
        if not isinstance(operacoes_brutas, list) or not operacoes_brutas:
            raise ValueError("Informe uma lista não vazia em 'operacoes' para alterar em lote.")

        preservar_padrao = bool(args.get("preservar_campos_compativeis", False))
        operacoes_coagidas: list[dict[str, Any]] = []
        alvos_alterados: list[str] = []
        total_campos = 0
        for item in operacoes_brutas:
            alvo_op, _, mapa_coagido = _preparar_mapa_coagido(item)
            operacoes_coagidas.append(
                {
                    "alvo": alvo_op,
                    "campos": mapa_coagido,
                    "preservar_campos_compativeis": bool(
                        item.get("preservar_campos_compativeis", preservar_padrao)
                    ),
                }
            )
            alvos_alterados.append(alvo_op)
            total_campos += len(mapa_coagido)

        croqui_controller.alterar_em_lote(
            operacoes=operacoes_coagidas,
            texto_macro=args.get("descricao_macro"),
            preservar_campos_compativeis=preservar_padrao,
        )
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "quantidade_operacoes": len(operacoes_coagidas),
            "total_campos_alterados": total_campos,
            "alvos_alterados": alvos_alterados,
        }

    def _adicionar_repeated(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo", ""))
        campo = str(args["campo"])
        valores_brutos = args.get("valores")
        if isinstance(valores_brutos, list) and valores_brutos:
            lista_bruta = valores_brutos
        elif "valor" in args and args["valor"] is not None:
            lista_bruta = [args["valor"]]
        else:
            raise ValueError(
                "Informe 'valor' (1 item) ou 'valores' (lista não vazia de itens) para adicionar."
            )

        indice = args.get("indice")
        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo)
        itens_proto: list[Any] = []
        uids_gerados: list[str] = []
        for item_bruto in lista_bruta:
            item_proto, uid_item = _instanciar_valor_para_campo_repeated(msg, campo, item_bruto)
            itens_proto.append(item_proto)
            uids_gerados.append(uid_item)

        colecao = getattr(msg, campo)
        idx_final = len(colecao) if indice is None or int(indice) < 0 else int(indice)
        croqui_controller.adicionar_multiplos_repeated(msg, campo, idx_final, itens_proto)
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        caminho_item = f"{caminho}.{campo}.{idx_final}" if caminho else f"{campo}.{idx_final}"
        resposta: dict[str, Any] = {
            "status": "ok",
            "uid": uids_gerados[0] if len(uids_gerados) == 1 else "",
            "uids_gerados": uids_gerados,
            "caminho": caminho_item,
            "indice": idx_final,
            "indice_inicial_inserido": idx_final,
            "tamanho": len(colecao),
        }
        if len(uids_gerados) == 1:
            resposta["uid_gerado"] = uids_gerados[0]
        return resposta

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

    def _migrar_escalada(args: dict[str, Any]) -> dict[str, Any]:
        alvo_escalada = str(args["alvo_escalada"])
        alvo_setor_destino = str(args["alvo_setor_destino"])
        msg_esc, caminho_esc = resolver_alvo_mcp(model, alvo_escalada)
        partes = caminho_esc.rsplit(".escaladas.", 1)
        if len(partes) != 2 or not partes[1].isdigit():
            raise ValueError(
                f"O alvo '{alvo_escalada}' ('{caminho_esc}') não corresponde a uma Escalada pertencente a um Setor."
            )
        caminho_setor_origem = partes[0]
        indice_origem = int(partes[1])
        setor_origem, _ = resolver_alvo_mcp(model, caminho_setor_origem, campo_nome="escaladas")
        setor_destino, caminho_setor_destino = resolver_alvo_mcp(
            model, alvo_setor_destino, campo_nome="escaladas"
        )
        idx_final = croqui_controller.migrar_escalada(
            setor_origem=setor_origem,
            indice_origem=indice_origem,
            setor_destino=setor_destino,
            indice_destino=args.get("indice_destino"),
        )
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return {
            "status": "ok",
            "uid": str(getattr(msg_esc, "uid", "")),
            "setor_origem": caminho_setor_origem,
            "indice_origem": indice_origem,
            "setor_destino": caminho_setor_destino,
            "indice_destino": idx_final,
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

    def _remover_referencia_mapa(args: dict[str, Any]) -> dict[str, Any]:
        alvo_mapa = str(args["alvo_mapa"])
        alvo_uid = str(args["alvo_uid"])
        pontos_brutos = args.get("pontos_uids")
        pontos_uids = [str(p) for p in pontos_brutos] if pontos_brutos else None
        msg_mapa, caminho = resolver_alvo_mcp(model, alvo_mapa)
        afetadas = ctrl_mapas.remover_referencia(
            msg_mapa, alvo_uid=alvo_uid, pontos_uids=pontos_uids
        )
        return {
            "status": "ok",
            "caminho_mapa": caminho,
            "alvo_uid": alvo_uid,
            "referencias_afetadas": afetadas,
        }

    def _gerar_malha_estrada(args: dict[str, Any]) -> dict[str, Any]:
        from scripts.gerar_malha_estrada_lib import (
            ClienteOverpass,
            construir_malha_estrada_pico_proto,
        )

        alvo_bruto = str(args.get("alvo") or "").strip()
        if alvo_bruto in ("", "root"):
            alvo_bruto = "picos.0"
        raiz_ro = model.obter_croqui_readonly()
        if alvo_bruto == "picos.0" and len(raiz_ro.picos) == 0:
            raise ValueError("O croqui atual não possui picos cadastrados.")

        msg_alvo, caminho_pico = resolver_alvo_mcp(model, alvo_bruto)
        if msg_alvo.DESCRIPTOR.name != "Pico":
            raise ValueError(
                f"O alvo '{alvo_bruto}' ('{caminho_pico}') não corresponde a um Pico."
            )

        lat_e7 = int(msg_alvo.localizacao.latitude or 0)
        lon_e7 = int(msg_alvo.localizacao.longitude or 0)
        if lat_e7 == 0 and lon_e7 == 0:
            raise ValueError(
                "O pico não possui coordenadas de localização válidas (latitude/longitude) "
                "para gerar o mapa de pontos de estrada."
            )

        cliente = cliente_overpass or ClienteOverpass()
        malha_proto = construir_malha_estrada_pico_proto(lat_e7, lon_e7, cliente)
        arq_malha = croqui_pb2.ArquivoMalhaEstrada()
        arq_malha.conteudo.CopyFrom(malha_proto)

        croqui_controller.alterar_campo(
            alvo=caminho_pico,
            campos={"malha_estrada": arq_malha},
        )
        return {
            "status": "ok",
            "alvo": caminho_pico,
            "latitude_referencia_e7": int(malha_proto.latitude_referencia_e7),
            "longitude_referencia_e7": int(malha_proto.longitude_referencia_e7),
            "quantidade_nos": len(malha_proto.nos),
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
                "preservar_campos_compativeis": {
                    "type": "boolean",
                    "description": "Quando True ao trocar variante oneof, copia os campos homônimos compatíveis da variante anterior.",
                },
            },
            "required": ["alvo"],
        },
        manipulador=_alterar_campo,
    )
    servidor.registrar_ferramenta(
        nome="aresta_alterar_em_lote",
        descricao=(
            "Altera múltiplos alvos e campos em uma única transação atômica (CmdMacro). "
            "Valida todos os alvos e campos previamente (fail-fast) antes de empilhar no histórico."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "operacoes": {
                    "type": "array",
                    "description": "Lista de operações {alvo, campo?, valor?, campos?, preservar_campos_compativeis?}.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "alvo": {"type": "string"},
                            "campo": {"type": "string"},
                            "valor": {},
                            "campos": {"type": "object"},
                            "preservar_campos_compativeis": {"type": "boolean"},
                        },
                        "required": ["alvo"],
                    },
                },
                "descricao_macro": {
                    "type": "string",
                    "description": "Descrição opcional do macro para a pilha de histórico.",
                },
                "preservar_campos_compativeis": {
                    "type": "boolean",
                    "description": "Valor padrão de preservar_campos_compativeis para as operações do lote.",
                },
            },
            "required": ["operacoes"],
        },
        manipulador=_alterar_em_lote,
    )
    servidor.registrar_ferramenta(
        nome="aresta_adicionar_repeated",
        descricao=(
            "Adiciona um item ('valor') ou múltiplos itens em lote ('valores') a uma coleção "
            "repeated, gerando e retornando imediatamente os UIDs NanoID ('uid', 'uid_gerado', "
            "'uids_gerados') e o tamanho atualizado."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string"},
                "campo": {"type": "string"},
                "valor": {},
                "valores": {"type": "array", "items": {}},
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
        nome="aresta_migrar_escalada",
        descricao=(
            "Migra atomicamente uma Escalada de seu Setor atual para um Setor de destino "
            "preservando seu UID NanoID, imagens em RAM e referências em mapas."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo_escalada": {
                    "type": "string",
                    "description": "UID NanoID ou caminho da Escalada a ser migrada.",
                },
                "alvo_setor_destino": {
                    "type": "string",
                    "description": "UID NanoID ou caminho do Setor de destino.",
                },
                "indice_destino": {
                    "type": "integer",
                    "description": "Índice de inserção em setor_destino.escaladas (opcional; padrão ao final).",
                },
            },
            "required": ["alvo_escalada", "alvo_setor_destino"],
        },
        manipulador=_migrar_escalada,
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
    servidor.registrar_ferramenta(
        nome="aresta_remover_referencia_mapa",
        descricao=(
            "Remove uma referência de mapa para alvo_uid por completo (quando pontos_uids "
            "é omitido) ou remove apenas pontos_uids específicos da referência."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo_mapa": {"type": "string"},
                "alvo_uid": {"type": "string"},
                "pontos_uids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["alvo_mapa", "alvo_uid"],
        },
        manipulador=_remover_referencia_mapa,
    )
    servidor.registrar_ferramenta(
        nome="aresta_gerar_malha_estrada",
        descricao=(
            "Gera ou atualiza o mapa de pontos de estrada (Overpass/OSM com Dijkstra por tempo "
            "`duracao_minutos` e `distancia_metros`) para um Pico do croqui e registra na pilha "
            "de Undo/Redo (`pico.malha_estrada`)."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "Caminho do Pico alvo (opcional; padrão 'picos.0').",
                },
            },
        },
        manipulador=_gerar_malha_estrada,
    )
