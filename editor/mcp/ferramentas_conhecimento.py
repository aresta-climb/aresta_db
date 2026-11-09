# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import re
from pathlib import Path
from typing import Any

from google.protobuf.descriptor import Descriptor, EnumDescriptor, FieldDescriptor

from aresta_api.proto.generated import croqui_pb2
from editor.core.serializacao_util import carregar_yaml
from editor.mcp.servidor import ServidorMCP

_MAPA_TIPOS_ESCALARES: dict[int, str] = {
    FieldDescriptor.TYPE_BOOL: "bool",
    FieldDescriptor.TYPE_INT32: "int32",
    FieldDescriptor.TYPE_SINT32: "sint32",
    FieldDescriptor.TYPE_UINT32: "uint32",
    FieldDescriptor.TYPE_INT64: "int64",
    FieldDescriptor.TYPE_SINT64: "sint64",
    FieldDescriptor.TYPE_UINT64: "uint64",
    FieldDescriptor.TYPE_FLOAT: "float",
    FieldDescriptor.TYPE_DOUBLE: "double",
    FieldDescriptor.TYPE_STRING: "string",
    FieldDescriptor.TYPE_BYTES: "bytes",
}

_GUIA_USO_MCP = (
    "Guia Rápido das Ferramentas MCP do Editor Aresta:\n"
    "1. Introspecção do estado atual: use `aresta_obter_arvore` (aceita `alvo` e `campo`, "
    "retornando `tamanhos_repeated` com a contagem de itens de todas as listas).\n"
    "2. Edição de campos (escalares, enums, submensagens `dict` ou `oneofs`): use "
    "`aresta_alterar_campo` passando `campo` + `valor` (ou `campos: dict` para atualização "
    "em lote em um único passo de Undo/Redo).\n"
    "3. Manipulação de listas (`repeated`): use `aresta_adicionar_repeated` (aceita `valores` "
    "como item único ou lista de dicts/escalares), `aresta_remover_repeated` e "
    "`aresta_mover_repeated`. Para editar um item já existente na lista, use "
    "`aresta_alterar_campo` apontando para o item indexado (ex: `alvo='escaladas[0]'`).\n"
    "4. Guias passo a passo de domínio: consulte `aresta_listar_skills` e `aresta_ler_skill`."
)


def _coletar_descritores_proto() -> tuple[dict[str, Descriptor], dict[str, EnumDescriptor]]:
    """Coleta recursivamente todas as mensagens e enums definidos em `croqui_pb2`."""
    mensagens: dict[str, Descriptor] = {}
    enums: dict[str, EnumDescriptor] = {}

    def _visitar_mensagem(msg_desc: Descriptor) -> None:
        mensagens.setdefault(msg_desc.name.lower(), msg_desc)
        mensagens.setdefault(msg_desc.full_name.removeprefix("aresta.").lower(), msg_desc)
        for enum_sub in msg_desc.enum_types:
            enums[enum_sub.name.lower()] = enum_sub
        for msg_sub in msg_desc.nested_types:
            _visitar_mensagem(msg_sub)

    for msg_top in croqui_pb2.DESCRIPTOR.message_types_by_name.values():
        _visitar_mensagem(msg_top)

    return mensagens, enums


_CAMPOS_ENDERECAMENTO_MCP: frozenset[str] = frozenset({"uid", "alvo_uid", "pontos_uids"})


def _eh_campo_oculto_mcp(field: FieldDescriptor) -> bool:
    """Retorna True se o campo for interno (`INVISIVEL`) ou depreciado, preservando UIDs de endereçamento."""
    if field.name in _CAMPOS_ENDERECAMENTO_MCP:
        return False
    opcoes = field.GetOptions()
    if getattr(opcoes, "deprecated", False):
        return True
    if opcoes.Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.INVISIVEL:
        return True
    return bool(
        field.message_type is not None
        and field.message_type.GetOptions().Extensions[croqui_pb2.mensagem_formato_na_ui]
        == croqui_pb2.MensagemFormatoUi.INVISIVEL
    )


def _construir_campos_ocultos_mcp() -> dict[str, frozenset[str]]:
    """Pré-computa em $O(1)$ os nomes de campos ocultos por `Descriptor.full_name`."""
    ocultos_por_msg: dict[str, frozenset[str]] = {}

    def _visitar(msg_desc: Descriptor) -> None:
        ocultos_por_msg[msg_desc.full_name] = frozenset(
            f.name for f in msg_desc.fields if _eh_campo_oculto_mcp(f)
        )
        for sub in msg_desc.nested_types:
            _visitar(sub)

    for msg_top in croqui_pb2.DESCRIPTOR.message_types_by_name.values():
        _visitar(msg_top)

    return ocultos_por_msg


_CAMPOS_OCULTOS_MCP: dict[str, frozenset[str]] = _construir_campos_ocultos_mcp()


def obter_campos_ocultos_mcp(msg_desc: Descriptor) -> frozenset[str]:
    """Retorna em $O(1)$ o conjunto de campos ocultos no MCP para `msg_desc`."""
    return _CAMPOS_OCULTOS_MCP.get(msg_desc.full_name, frozenset())


def filtrar_dict_mcp(msg_desc: Descriptor, dados: dict[str, Any]) -> dict[str, Any]:
    """Remove recursivamente extensões `[aresta.*]` e campos internos/invisíveis de um dict serializado."""
    ocultos = obter_campos_ocultos_mcp(msg_desc)
    resultado: dict[str, Any] = {}
    for chave, valor in dados.items():
        if chave.startswith("[") or chave in ocultos:
            continue
        f_desc = msg_desc.fields_by_name.get(chave)
        if f_desc is not None and f_desc.message_type is not None:
            if isinstance(valor, dict):
                resultado[chave] = filtrar_dict_mcp(f_desc.message_type, valor)
            else:
                resultado[chave] = [filtrar_dict_mcp(f_desc.message_type, item) for item in valor]
        else:
            resultado[chave] = valor
    return resultado


def _extrair_comentarios_campos_proto(texto_proto: str) -> dict[tuple[str, str], str]:
    """
    Extrai comentários precedentes (`// ...`) associados a campos de mensagens
    no arquivo `croqui.proto`, indexados por `(nome_mensagem_lower, nome_campo)`.
    """
    comentarios: dict[tuple[str, str], str] = {}
    pilha_mensagens: list[str] = []
    buffer_comentario: list[str] = []

    padrao_msg = re.compile(r"^\s*message\s+([A-Za-z0-9_]+)\s*\{")
    padrao_campo = re.compile(r"^\s*(?:repeated\s+)?[A-Za-z0-9_.]+\s+([a-z0-9_]+)\s*=\s*\d+[^;]*;")

    for linha in texto_proto.splitlines():
        limpa = linha.strip()
        if limpa.startswith("//"):
            buffer_comentario.append(limpa.lstrip("/").strip())
            continue

        m_msg = padrao_msg.match(linha)
        if m_msg:
            pilha_mensagens.append(m_msg.group(1).lower())
            buffer_comentario.clear()
            continue

        m_campo = padrao_campo.match(linha)
        if m_campo and pilha_mensagens:
            nome_campo = m_campo.group(1)
            comentarios[(pilha_mensagens[-1], nome_campo)] = " ".join(buffer_comentario)
            buffer_comentario.clear()
            continue

        if limpa == "}" and pilha_mensagens:
            pilha_mensagens.pop()
        buffer_comentario.clear()

    return comentarios


def _descrever_campo(
    msg_desc: Descriptor,
    field: FieldDescriptor,
    comentarios: dict[tuple[str, str], str],
) -> dict[str, Any]:
    if field.message_type is not None:
        nome_tipo = field.message_type.name
    elif field.enum_type is not None:
        nome_tipo = field.enum_type.name
    else:
        nome_tipo = _MAPA_TIPOS_ESCALARES.get(field.type, "scalar")

    opcoes_enum = [v.name for v in field.enum_type.values] if field.enum_type is not None else None
    return {
        "nome": field.name,
        "numero": field.number,
        "tipo": nome_tipo,
        "repeated": bool(field.is_repeated),
        "oneof": field.containing_oneof.name if field.containing_oneof is not None else None,
        "opcoes_enum": opcoes_enum,
        "descricao": comentarios.get((msg_desc.name.lower(), field.name), ""),
    }


def _extrair_metadados_frontmatter_skill(pasta_skill: Path, texto_markdown: str) -> tuple[str, str]:
    """Extrai `(nome, descricao)` do YAML frontmatter de um arquivo `SKILL.md`."""
    if texto_markdown.startswith("---"):
        partes = texto_markdown.split("---", 2)
        if len(partes) >= 3:
            dados = carregar_yaml(partes[1])
            if isinstance(dados, dict):
                nome = str(dados.get("name") or pasta_skill.name)
                descricao = str(dados.get("description") or "").strip()
                return nome, descricao
    primeira_linha = texto_markdown.strip().splitlines()[0].lstrip("#").strip()
    return pasta_skill.name, primeira_linha


def registrar_ferramentas_conhecimento(
    servidor: ServidorMCP,
    diretorio_skills: Path | None = None,
    caminho_proto: Path | None = None,
    model: Any = None,
    diretorio_database: Path | None = None,
) -> None:
    """
    Registra no `ServidorMCP` as ferramentas e recursos de descoberta de esquema Protobuf
    (`aresta_obter_esquema_proto`, `aresta://esquema/proto`), de consulta às skills de domínio
    (`aresta_listar_skills`, `aresta_ler_skill`, `aresta://skills`) e de diagnóstico do painel
    de qualidade (`aresta_avaliar_qualidade`).
    """
    raiz_repo = Path(__file__).resolve().parents[2]
    dir_skills = diretorio_skills or (raiz_repo / ".agents" / "skills")
    arq_proto = caminho_proto or (raiz_repo / "aresta_api" / "proto" / "croqui.proto")
    dir_db = diretorio_database or (raiz_repo / "database")

    mensagens_por_nome, enums_por_nome = _coletar_descritores_proto()

    def _obter_esquema_proto(args: dict[str, Any]) -> dict[str, Any]:
        texto_proto = arq_proto.read_text(encoding="utf-8")
        comentarios = _extrair_comentarios_campos_proto(texto_proto)
        filtro = str(args.get("tipo_mensagem") or "").strip()

        if not filtro:
            return {
                "guia_uso_mcp": _GUIA_USO_MCP,
                "mensagens_disponiveis": sorted({m.name for m in mensagens_por_nome.values()}),
                "enums_disponiveis": sorted({e.name for e in enums_por_nome.values()}),
                "conteudo_proto": texto_proto,
            }

        chave = filtro.lower()
        if chave in mensagens_por_nome:
            msg_desc = mensagens_por_nome[chave]
            ocultos = obter_campos_ocultos_mcp(msg_desc)
            campos = [
                _descrever_campo(msg_desc, f, comentarios)
                for f in msg_desc.fields
                if f.name not in ocultos
            ]
            oneofs = {
                oneof.name: [f.name for f in oneof.fields if f.name not in ocultos]
                for oneof in msg_desc.oneofs
            }
            valores_enum = [
                {"nome": v.name, "numero": v.number}
                for enum_sub in msg_desc.enum_types
                for v in enum_sub.values
            ]
            return {
                "tipo": "message",
                "nome": msg_desc.name,
                "nome_completo": msg_desc.full_name,
                "campos": campos,
                "oneofs": oneofs,
                "valores_enum": valores_enum,
            }

        if chave in enums_por_nome:
            enum_desc = enums_por_nome[chave]
            return {
                "tipo": "enum",
                "nome": enum_desc.name,
                "nome_completo": enum_desc.full_name,
                "valores_enum": [{"nome": v.name, "numero": v.number} for v in enum_desc.values],
            }

        disponiveis = ", ".join(sorted({m.name for m in mensagens_por_nome.values()}))
        raise ValueError(
            f"Tipo '{filtro}' não encontrado em croqui.proto. "
            f"Mensagens disponíveis: [{disponiveis}]."
        )

    def _listar_skills(_args: dict[str, Any]) -> dict[str, Any]:
        skills: list[dict[str, str]] = []
        for pasta in sorted(dir_skills.iterdir()):
            arq_skill = pasta / "SKILL.md"
            if pasta.is_dir() and arq_skill.is_file():
                texto = arq_skill.read_text(encoding="utf-8")
                nome, descricao = _extrair_metadados_frontmatter_skill(pasta, texto)
                skills.append(
                    {
                        "nome": nome,
                        "pasta": pasta.name,
                        "descricao": descricao,
                    }
                )
        return {"skills": skills}

    def _ler_skill(args: dict[str, Any]) -> dict[str, Any]:
        nome_skill = str(args.get("nome_skill") or "").strip()
        pasta_skill = dir_skills / nome_skill
        arq_skill = pasta_skill / "SKILL.md"
        if not nome_skill or not arq_skill.is_file():
            disponiveis = [s["pasta"] for s in _listar_skills({})["skills"]]
            raise ValueError(
                f"Skill '{nome_skill}' não encontrada. Skills disponíveis: {disponiveis}."
            )
        conteudo_md = arq_skill.read_text(encoding="utf-8")
        arquivos_auxiliares = sorted(
            p.relative_to(pasta_skill).as_posix()
            for p in pasta_skill.rglob("*")
            if p.is_file() and p.name != "SKILL.md"
        )
        return {
            "nome": nome_skill,
            "conteudo_markdown": conteudo_md,
            "arquivos_auxiliares": arquivos_auxiliares,
        }

    def _avaliar_qualidade(args: dict[str, Any]) -> dict[str, Any]:
        from editor.core.avaliador_nota_qualidade import avaliar_nota_qualidade_croqui

        id_solicitado = str(args.get("id_croqui") or "").strip()
        usar_modelo_em_memoria = model is not None and (
            not id_solicitado
            or id_solicitado == servidor.id_croqui_ativo
            or id_solicitado == str(getattr(model.obter_croqui_readonly(), "id", ""))
        )

        if usar_modelo_em_memoria:
            caminho_db_ativo = (
                Path(servidor.caminho_database_ativo)
                if servidor.caminho_database_ativo
                else None
            )
            resultado = avaliar_nota_qualidade_croqui(model, croqui_path=caminho_db_ativo)
        else:
            id_alvo = id_solicitado or servidor.id_croqui_ativo
            pasta_croqui = dir_db / id_alvo if id_alvo else None
            if pasta_croqui is None or not (pasta_croqui / "croqui.yaml").is_file():
                raise ValueError(
                    f"Não foi possível localizar o croqui '{id_alvo}' para avaliação de qualidade."
                )
            resultado = avaliar_nota_qualidade_croqui(None, croqui_path=pasta_croqui)

        etapas_json: list[dict[str, Any]] = []
        tarefas_pendentes: list[dict[str, Any]] = []
        for etapa in resultado.etapas:
            tarefas_etapa_json: list[dict[str, Any]] = []
            for t in etapa.tarefas:
                dict_t = {
                    "id_tarefa": t.id_tarefa,
                    "titulo": t.titulo,
                    "descricao": t.descricao,
                    "etapa": t.etapa,
                    "pontos_obtidos": t.pontos_obtidos,
                    "pontos_maximos": t.pontos_maximos,
                    "ganho_potencial": t.ganho_potencial,
                    "concluida": t.concluida,
                    "progresso_atual": t.progresso_atual,
                    "progresso_total": t.progresso_total,
                    "acoes": [
                        {"rotulo": a.rotulo, "uri_contexto": a.uri_contexto} for a in t.acoes
                    ],
                }
                tarefas_etapa_json.append(dict_t)
                if not t.concluida:
                    tarefas_pendentes.append(dict_t)

            etapas_json.append(
                {
                    "numero_etapa": etapa.numero_etapa,
                    "titulo": etapa.titulo,
                    "pontos_obtidos": etapa.pontos_obtidos,
                    "pontos_maximos": etapa.pontos_maximos,
                    "tarefas_concluidas": etapa.tarefas_concluidas,
                    "total_tarefas": etapa.total_tarefas,
                    "concluida": etapa.concluida,
                    "tarefas": tarefas_etapa_json,
                }
            )

        tarefas_pendentes.sort(key=lambda item: (item["etapa"], -item["ganho_potencial"]))
        return {
            "nota_qualidade": resultado.nota_qualidade,
            "nota_maxima": resultado.nota_maxima,
            "pronto_para_publicar": resultado.pronto_para_publicar,
            "publicado": resultado.publicado,
            "etapas": etapas_json,
            "tarefas_pendentes": tarefas_pendentes,
        }

    servidor.registrar_ferramenta(
        nome="aresta_obter_esquema_proto",
        descricao=(
            "Retorna o esquema de dados de `croqui.proto`, incluindo campos, tipos, `oneofs`, "
            "valores de `Enum` e comentários de documentação. Sem `tipo_mensagem`, retorna a "
            "visão geral com todas as mensagens/enums disponíveis e o guia de uso MCP."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "tipo_mensagem": {
                    "type": "string",
                    "description": (
                        "Nome opcional da mensagem ou enum (ex: 'Croqui', 'Escalada', "
                        "'ViaEsportiva', 'GrauVia', 'PontoDeInteresse')."
                    ),
                }
            },
        },
        manipulador=_obter_esquema_proto,
        requer_croqui=False,
    )

    servidor.registrar_ferramenta(
        nome="aresta_listar_skills",
        descricao=(
            "Lista todas as skills de domínio disponíveis em `.agents/skills/` com seus nomes "
            "e descrições para orientar o processamento e edição de croquis."
        ),
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_listar_skills,
        requer_croqui=False,
    )

    servidor.registrar_ferramenta(
        nome="aresta_ler_skill",
        descricao=(
            "Lê o conteúdo completo (`SKILL.md`) e lista os arquivos auxiliares de uma skill "
            "de domínio específica."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "nome_skill": {
                    "type": "string",
                    "description": "Nome da skill (ex: 'preencher_croqui_yaml').",
                }
            },
            "required": ["nome_skill"],
        },
        manipulador=_ler_skill,
        requer_croqui=False,
    )

    servidor.registrar_ferramenta(
        nome="aresta_avaliar_qualidade",
        descricao=(
            "Avalia a nota de qualidade do croqui (escala aditiva até 8770 pontos nas Etapas 1, 2 e 3) "
            "e retorna o diagnóstico estruturado com o progresso de cada tarefa, pontos obtidos, "
            "ganho potencial e lista priorizada de `tarefas_pendentes` com `acoes` (`uri_contexto`)."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "id_croqui": {
                    "type": "string",
                    "description": "ID opcional do croqui a avaliar (se omitido, avalia o croqui aberto na sessão).",
                }
            },
        },
        manipulador=_avaliar_qualidade,
        requer_croqui=False,
    )

    servidor.registrar_recurso(
        uri="aresta://esquema/proto",
        nome="Esquema Protobuf do Croqui (croqui.proto)",
        descricao="Definição completa e guia de uso do esquema Protobuf Croqui.",
        leitor=lambda: _obter_esquema_proto({}),
    )

    servidor.registrar_recurso(
        uri="aresta://skills",
        nome="Catálogo de Skills de Domínio Aresta",
        descricao="Lista de todas as skills disponíveis para automação de croquis no Editor Aresta.",
        leitor=lambda: _listar_skills({}),
    )
