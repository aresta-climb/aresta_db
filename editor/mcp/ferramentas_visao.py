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
        msg, caminho = resolver_alvo_mcp(model, alvo)
        msg_proto = _desembrulhar_proto(msg)
        dados_dict = MessageToDict(msg_proto, preserving_proto_field_name=True)

        indice_lista = [
            {
                "uid": reg.uid,
                "tipo_id": int(reg.tipo_id),
                "caminho_formatado": reg.obter_caminho_formatado(),
            }
            for reg in model.indice_uids.listar()
        ]
        return {
            "caminho": caminho,
            "dados": dados_dict,
            "indice_uids": indice_lista,
        }

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
        descricao="Retorna a árvore do croqui (ou subárvore por UID/caminho) junto ao índice completo de UIDs e caminhos formatados.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": "Opcional: UID ou caminho da subárvore. Vazio retorna o croqui inteiro.",
                }
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
