# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QWidget

from editor.mcp.ferramentas_conhecimento import filtrar_dict_mcp, obter_campos_ocultos_mcp
from editor.mcp.renderizador_mapa_mcp import renderizar_pacote_visual_mapa
from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def _desembrulhar_proto(msg: Any) -> Any:
    return getattr(msg, "_obj", msg)


def _serializar_objeto_proto(obj: Any) -> Any:
    desembrulhado = _desembrulhar_proto(obj)
    if hasattr(desembrulhado, "DESCRIPTOR"):
        bruto = MessageToDict(desembrulhado, preserving_proto_field_name=True)
        return filtrar_dict_mcp(desembrulhado.DESCRIPTOR, bruto)
    return desembrulhado


def _extrair_rotulo_poi(poi: Any) -> str:
    rotulos = [
        str(getattr(poi, "rotulo", "") or "").strip(),
        *(str(n.rotulo or "").strip() for n in poi.linha.conteudo.nos),
    ]
    return next((r for r in rotulos if r), "")


def _coletar_referencias_por_alvo(mapas: list[Any]) -> dict[str, tuple[list[str], list[str]]]:
    """Mapeia `alvo_uid -> (rotulos_mapa, pontos_uids)` a partir de uma sequência de `Mapa`."""
    indice: dict[str, tuple[list[str], list[str]]] = {}
    for mapa in mapas:
        rotulo_por_poi = {str(p.uid): _extrair_rotulo_poi(p) for p in mapa.pontos_de_interesse}
        for ref in mapa.referencias:
            alvo_uid = str(ref.alvo_uid or "")
            rotulos, pontos = indice.setdefault(alvo_uid, ([], []))
            for p_uid in ref.pontos_uids:
                p_str = str(p_uid)
                if p_str not in pontos:
                    pontos.append(p_str)
                rot = rotulo_por_poi.get(p_str, "")
                if rot and rot not in rotulos:
                    rotulos.append(rot)
    return indice


def _extrair_candidatos_vetoriais_mapa(
    caminho_db: Path | None, caminho_imagem: str
) -> list[dict[str, Any]]:
    """Procura metadados JSON gerados pelo `repartir_pdf` para a imagem do mapa e extrai spans de texto."""
    nome_arq = Path(caminho_imagem).stem
    candidatos: list[dict[str, Any]] = []
    arquivos_json = (
        sorted((caminho_db / "raw_pdf_contents" / "imagens").rglob("*.json"))
        if caminho_db is not None and (caminho_db / "raw_pdf_contents" / "imagens").is_dir()
        else []
    )
    for arq_json in arquivos_json:
        if arq_json.stem in nome_arq or nome_arq.endswith(arq_json.stem):
            dados = json.loads(arq_json.read_text(encoding="utf-8"))
            for bloco in dados.get("texto", []):
                for linha in bloco.get("lines", []):
                    for span in linha.get("spans", []):
                        texto = str(span.get("text") or "").strip()
                        if texto:
                            candidatos.append(
                                {
                                    "texto": texto,
                                    "bbox": span.get("bbox"),
                                    "origin": span.get("origin"),
                                }
                            )
    return candidatos


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

        dados_b64 = base64.b64encode(matriz_bytes.data()).decode("ascii")
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
            bool(incluir_indice_arg) if incluir_indice_arg is not None else (not alvo and not campo)
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
                val_oneof = _serializar_objeto_proto(getattr(msg_proto, ativo)) if ativo else None
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
            eh_rep = getattr(desc_c, "label", None) == 3 or getattr(desc_c, "is_repeated", False)
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

        ocultos_msg = obter_campos_ocultos_mcp(msg_proto.DESCRIPTOR)
        tamanhos_repeated = {
            f.name: len(getattr(msg_proto, f.name))
            for f in msg_proto.DESCRIPTOR.fields
            if (getattr(f, "label", None) == 3 or getattr(f, "is_repeated", False))
            and f.name not in ocultos_msg
        }
        dados_dict = _serializar_objeto_proto(msg_proto)

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

    def _renderizar_mapa(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo") or "")
        indice_mapa = int(args.get("indice_mapa", 0))
        incluir_grade = bool(args.get("incluir_grade", True))
        incluir_recortes = bool(args.get("incluir_recortes_pois", True))

        msg, _ = resolver_alvo_mcp(model, alvo)
        msg_proto = _desembrulhar_proto(msg)
        mapa_proto = (
            msg_proto.mapas[indice_mapa]
            if msg_proto.DESCRIPTOR.name != "Mapa" and hasattr(msg_proto, "mapas")
            else msg_proto
        )
        caminho_img = str(getattr(mapa_proto, "caminho_imagem_mapa", "") or "")
        bytes_img = model.obter_bytes_imagem(caminho_img) or model.obter_bytes_imagem(
            f"imagens/{Path(caminho_img).name}"
        )
        if not bytes_img:
            raise ValueError(f"Imagem do mapa '{caminho_img}' não encontrada.")

        candidatos = _extrair_candidatos_vetoriais_mapa(
            getattr(model, "_caminho_db_atual", None), caminho_img
        )
        blocos = renderizar_pacote_visual_mapa(
            bytes_imagem=bytes_img,
            pontos_de_interesse=mapa_proto.pontos_de_interesse,
            incluir_grade=incluir_grade,
            incluir_recortes_pois=incluir_recortes,
            candidatos_vetoriais=candidatos,
        )
        return {"_mcp_content": blocos}

    def _listar_escaladas(args: dict[str, Any]) -> dict[str, Any]:
        alvo_setor = str(args.get("alvo_setor") or "").strip()
        filtro_nome = str(args.get("filtro_nome") or "").strip().lower()
        setor_filtrado = (
            _desembrulhar_proto(resolver_alvo_mcp(model, alvo_setor)[0]) if alvo_setor else None
        )
        croqui_proto = _desembrulhar_proto(model.obter_croqui_readonly())

        escaladas_lista: list[dict[str, Any]] = []
        for pico in croqui_proto.picos:
            mapas_pico = list(pico.mapas_gerais.conteudo.mapas)
            for sg in pico.setores_ou_grupos:
                eh_grupo = sg.HasField("grupo")
                setores_sg = (
                    [arq_s.conteudo for arq_s in sg.grupo.conteudo.setores]
                    if eh_grupo
                    else [sg.setor.conteudo]
                )
                mapas_grupo = list(sg.grupo.conteudo.mapas) if eh_grupo else []
                for setor in setores_sg:
                    if setor_filtrado is not None and setor is not setor_filtrado:
                        continue
                    refs_por_uid = _coletar_referencias_por_alvo(
                        [*mapas_pico, *mapas_grupo, *setor.mapas]
                    )
                    for idx_esc, esc in enumerate(setor.escaladas):
                        tipo_esc = str(esc.WhichOneof("tipo") or "")
                        sub = getattr(esc, tipo_esc)
                        nome_via = str(getattr(sub, "nome", "") or "")
                        if filtro_nome and filtro_nome not in nome_via.lower():
                            continue
                        campo_dif = sub.DESCRIPTOR.fields_by_name.get("dificuldade")
                        val_dif = int(getattr(sub, "dificuldade", 0) or 0)
                        nome_dif = (
                            campo_dif.enum_type.values_by_number[val_dif].name
                            if campo_dif is not None and val_dif
                            else ""
                        )
                        rotulos_mapa, pontos_uids = refs_por_uid.get(str(esc.uid), ([], []))
                        escaladas_lista.append(
                            {
                                "uid": str(esc.uid),
                                "indice_no_setor": idx_esc,
                                "setor_uid": str(setor.uid),
                                "setor_nome": str(setor.nome),
                                "rotulos_mapa": rotulos_mapa,
                                "pontos_uids": pontos_uids,
                                "tipo": tipo_esc,
                                "nome": nome_via,
                                "dificuldade": nome_dif,
                                "data_abertura": str(getattr(sub, "data_abertura", "") or ""),
                                "conquistadores": list(getattr(sub, "conquistadores", [])),
                            }
                        )
        return {
            "total_escaladas": len(escaladas_lista),
            "escaladas": escaladas_lista,
        }

    servidor.registrar_ferramenta(
        nome="aresta_listar_escaladas",
        descricao=(
            "Lista as escaladas do croqui (ou de um setor específico) cruzadas automaticamente "
            "com os rótulos ('rotulos_mapa') e 'pontos_uids' referenciados nos mapas dos setores "
            "e em 'mapas_gerais'."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo_setor": {
                    "type": "string",
                    "description": "Opcional: UID ou caminho de um Setor específico para filtrar.",
                },
                "filtro_nome": {
                    "type": "string",
                    "description": "Opcional: Substring case-insensitive para filtrar pelo nome da escalada.",
                },
            },
        },
        manipulador=_listar_escaladas,
    )

    servidor.registrar_ferramenta(
        nome="aresta_renderizar_mapa",
        descricao=(
            "Renderiza o mapa indicado com os POIs em vermelho, grade métrica semitransparente "
            "de 100px com réguas nas bordas (X/Y) e recortes ampliados centrados em cada POI "
            "com mira relativa (-50px a +50px), retornando uma lista intercalada de blocos "
            "[Texto, Imagem] para extração e ajuste preciso de coordenadas."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {
                    "type": "string",
                    "description": (
                        "UID ou caminho do Setor/Grupo/ColecaoDeMapas ou caminho direto do Mapa."
                    ),
                },
                "indice_mapa": {
                    "type": "integer",
                    "description": "Índice do mapa (0-based) quando 'alvo' aponta para Setor/Grupo.",
                },
                "incluir_grade": {
                    "type": "boolean",
                    "description": "Incluir grade métrica de 100px e réguas nas bordas da imagem geral.",
                },
                "incluir_recortes_pois": {
                    "type": "boolean",
                    "description": "Incluir recortes ampliados de cada POI com mira relativa (-50..+50).",
                },
            },
            "required": ["alvo"],
        },
        manipulador=_renderizar_mapa,
    )

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
