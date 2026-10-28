# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import re
from pathlib import Path
from typing import Any

import yaml
from google.protobuf.descriptor import Descriptor, EnumDescriptor, FieldDescriptor

from aresta_api.proto.generated import croqui_pb2
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
        mensagens[msg_desc.name.lower()] = msg_desc
        for enum_sub in msg_desc.enum_types:
            enums[enum_sub.name.lower()] = enum_sub
        for msg_sub in msg_desc.nested_types:
            _visitar_mensagem(msg_sub)

    for msg_top in croqui_pb2.DESCRIPTOR.message_types_by_name.values():
        _visitar_mensagem(msg_top)

    return mensagens, enums


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

    opcoes_enum = (
        [v.name for v in field.enum_type.values] if field.enum_type is not None else None
    )
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
            dados = yaml.safe_load(partes[1])
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
) -> None:
    """
    Registra no `ServidorMCP` as ferramentas e recursos de descoberta de esquema Protobuf
    (`aresta_obter_esquema_proto`, `aresta://esquema/proto`) e de consulta às skills de domínio
    (`aresta_listar_skills`, `aresta_ler_skill`, `aresta://skills`).
    """
    raiz_repo = Path(__file__).resolve().parents[2]
    dir_skills = diretorio_skills or (raiz_repo / ".agents" / "skills")
    arq_proto = caminho_proto or (raiz_repo / "aresta_api" / "proto" / "croqui.proto")

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
            campos = [
                _descrever_campo(msg_desc, f, comentarios) for f in msg_desc.fields
            ]
            oneofs = {
                oneof.name: [f.name for f in oneof.fields] for oneof in msg_desc.oneofs
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
                "valores_enum": [
                    {"nome": v.name, "numero": v.number} for v in enum_desc.values
                ],
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
