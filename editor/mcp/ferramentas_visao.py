# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import json
from collections.abc import Callable
from typing import Any

from google.protobuf.json_format import MessageToDict
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QWidget

from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def _desembrulhar_proto(msg: Any) -> Any:
    return getattr(msg, "_obj", msg)


def _serializar_objeto_proto(obj: Any) -> Any:
    desembrulhado = _desembrulhar_proto(obj)
    if hasattr(desembrulhado, "DESCRIPTOR"):
        return MessageToDict(desembrulhado, preserving_proto_field_name=True)
    return desembrulhado


def registrar_ferramentas_visao(
    servidor: ServidorMCP,
    model: CroquiModel,
    provedor_widget_alvo: Callable[[str], QWidget | None] | None = None,
    provedor_selecao_atual: Callable[[], dict[str, Any]] | None = None,
) -> None:
    """
    Registra no `ServidorMCP` as ferramentas de visão multimodal (`aresta_capturar_canvas`)
    e inspeção estrutural (`aresta_obter_arvore`, `aresta_obter_selecao_atual`).
    """

    def _capturar_canvas(args: dict[str, Any]) -> dict[str, Any]:
        alvo_viewport = str(args.get("alvo_viewport") or "janela")
        widget = provedor_widget_alvo(alvo_viewport) if provedor_widget_alvo else None
        if widget is None:
            raise ValueError(f"Viewport '{alvo_viewport}' não disponível para captura no momento.")

        pixmap = widget.grab()
        matriz_bytes = QByteArray()
        buffer = QBuffer(matriz_bytes)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        buffer.close()

        dados_b64 = base64.b64encode(bytes(matriz_bytes)).decode("ascii")
        metadados = {
            "viewport": alvo_viewport,
            "largura": pixmap.width(),
            "altura": pixmap.height(),
            "mime_type": "image/png",
        }
        return {
            "_mcp_content": [
                {"type": "image", "data": dados_b64, "mimeType": "image/png"},
                {"type": "text", "text": json.dumps(metadados, ensure_ascii=False)},
            ]
        }

    def _obter_arvore(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo") or "")
        campo = str(args.get("campo") or "")
        incluir_indice_arg = args.get("incluir_indice_uids")
        incluir_indice = (
            bool(incluir_indice_arg)
            if incluir_indice_arg is not None
            else (not alvo and not campo)
        )

        msg, caminho = resolver_alvo_mcp(model, alvo, campo_nome=campo or None)
        msg_proto = _desembrulhar_proto(msg)

        if not hasattr(msg_proto, "DESCRIPTOR"):
            itens = [_serializar_objeto_proto(it) for it in msg_proto]
            return {
                "caminho": alvo,
                "tipo_campo": "repeated",
                "tamanho": len(itens),
                "itens": itens,
            }

        if campo:
            if "." in campo and campo.split(".", 1)[1].isdigit():
                nome_base, idx_str = campo.split(".", 1)
                colecao = getattr(msg_proto, nome_base)
                idx = int(idx_str)
                if idx < 0 or idx >= len(colecao):
                    raise IndexError(
                        f"Índice fora de alcance ({idx}) para o campo '{nome_base}' "
                        f"de tamanho {len(colecao)}."
                    )
                return {
                    "caminho": caminho,
                    "campo": campo,
                    "tipo_campo": "repeated_item",
                    "indice": idx,
                    "tamanho_colecao": len(colecao),
                    "valor": _serializar_objeto_proto(colecao[idx]),
                }

            if campo in msg_proto.DESCRIPTOR.oneofs_by_name:
                ativo = msg_proto.WhichOneof(campo)
                val_oneof = (
                    _serializar_objeto_proto(getattr(msg_proto, ativo)) if ativo else None
                )
                return {
                    "caminho": caminho,
                    "campo": campo,
                    "tipo_campo": "oneof",
                    "variante_ativa": ativo,
                    "valor": val_oneof,
                }

            if campo not in msg_proto.DESCRIPTOR.fields_by_name:
                raise ValueError(
                    f"Campo '{campo}' não existe na mensagem '{msg_proto.DESCRIPTOR.name}'."
                )

            desc_c = msg_proto.DESCRIPTOR.fields_by_name[campo]
            eh_rep = getattr(desc_c, "label", None) == 3 or getattr(
                desc_c, "is_repeated", False
            )
            if eh_rep:
                colecao = getattr(msg_proto, campo)
                return {
                    "caminho": caminho,
                    "campo": campo,
                    "tipo_campo": "repeated",
                    "tamanho": len(colecao),
                    "itens": [_serializar_objeto_proto(it) for it in colecao],
                }

            return {
                "caminho": caminho,
                "campo": campo,
                "tipo_campo": "singular",
                "valor": _serializar_objeto_proto(getattr(msg_proto, campo)),
            }

        tamanhos_repeated = {
            f.name: len(getattr(msg_proto, f.name))
            for f in msg_proto.DESCRIPTOR.fields
            if getattr(f, "label", None) == 3 or getattr(f, "is_repeated", False)
        }
        dados_dict = MessageToDict(msg_proto, preserving_proto_field_name=True)

        resultado: dict[str, Any] = {
            "caminho": caminho,
            "tipo_mensagem": msg_proto.DESCRIPTOR.name,
            "tamanhos_repeated": tamanhos_repeated,
            "dados": dados_dict,
        }
        if incluir_indice:
            resultado["indice_uids"] = [
                {
                    "uid": reg.uid,
                    "tipo_id": int(reg.tipo_id),
                    "caminho_formatado": reg.obter_caminho_formatado(),
                }
                for reg in model.indice_uids.listar()
            ]
        return resultado

    def _obter_selecao_atual(_args: dict[str, Any]) -> dict[str, Any]:
        info = (
            dict(provedor_selecao_atual())
            if provedor_selecao_atual is not None
            else {"uid": "", "caminho_selecionado": "", "aba_ativa": ""}
        )
        uid_sel = str(info.get("uid") or "")
        info["caminho_formatado"] = (
            (model.indice_uids.obter_caminho(uid_sel) or "") if uid_sel else ""
        )
        return info

    servidor.registrar_ferramenta(
        nome="aresta_capturar_canvas",
        descricao="Captura o frame renderizado do viewport solicitado (mapa, foto, dados ou janela) em PNG Base64.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo_viewport": {
                    "type": "string",
                    "description": "Viewport alvo: 'mapa', 'foto', 'dados' ou 'janela'.",
                }
            },
        },
        manipulador=_capturar_canvas,
    )
    servidor.registrar_ferramenta(
        nome="aresta_obter_arvore",
        descricao=(
            "Retorna a árvore do croqui, subárvore ou campo específico (incluindo listas repeated "
            "e o mapa 'tamanhos_repeated' com o tamanho atual de todas as coleções da mensagem)."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "Opcional: UID ou caminho da entidade. Vazio retorna o croqui inteiro.",
                },
                "campo": {
                    "type": "string",
                    "description": "Opcional: Nome do campo, oneof, coleção repeated ou item indexado ('campo.0') a inspecionar.",
                },
                "incluir_indice_uids": {
                    "type": "boolean",
                    "description": "Opcional: Se True, inclui o índice completo de UIDs do croqui (padrão: True apenas na raiz).",
                },
            },
        },
        manipulador=_obter_arvore,
    )
    servidor.registrar_ferramenta(
        nome="aresta_obter_selecao_atual",
        descricao="Retorna o elemento e a aba atualmente selecionados na interface gráfica do Editor Aresta.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_obter_selecao_atual,
    )
    servidor.registrar_recurso(
        uri="aresta://croqui/arvore",
        nome="Árvore Estrutural do Croqui",
        descricao="Representação JSON completa da árvore do croqui ativo e seus UIDs.",
        leitor=lambda: _obter_arvore({}),
    )
