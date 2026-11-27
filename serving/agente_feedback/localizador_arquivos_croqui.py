# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Extrator de contexto de Issues e comentários (`/ai-fix`) e construtor do pacote
estrutural pré-aquecido (*Warm-Start*) sobre `SessaoEditorHeadless` (0 chamadas de IA).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from editor.mcp.sessao_headless import SessaoEditorHeadless


@dataclass(frozen=True)
class ContextoFeedbackExtraido:
    """Metadados estruturados extraídos de uma Issue de feedback de croqui."""

    croqui_id: str | None
    descricao_usuario: str
    nome_grupo: str | None
    nome_setor: str | None
    nome_via: str | None
    url_screenshot: str | None


@dataclass(frozen=True)
class PacoteWarmStartCroqui:
    """Contexto completo pré-aquecido do croqui carregado em memória para o Turno 1 do agente."""

    croqui_id: str
    descricao_usuario: str
    instrucoes_skill: str
    catalogo_skills: str
    indice_estrutural: str
    uid_foco: str
    subarvore_foco_json: str

    def montar_prompt_inicial(self, instrucao_extra: str = "") -> str:
        """Constrói o prompt unificado do primeiro turno com instruções, índice de UIDs e foco."""
        partes = [
            self.instrucoes_skill.strip(),
            f"### Catálogo de Skills Disponíveis via `aresta_ler_skill`:\n{self.catalogo_skills}",
            f"### Índice Estrutural Completo do Croqui (`{self.croqui_id}`):\n{self.indice_estrutural}",
        ]
        if self.subarvore_foco_json:
            partes.append(
                f"### Subárvore Detalhada do Alvo em Foco (`uid={self.uid_foco}`):\n"
                f"```json\n{self.subarvore_foco_json}\n```"
            )
        partes.append(f"### Feedback do Usuário:\n{self.descricao_usuario}")
        if instrucao_extra:
            partes.append(f"### Instrução Autorizada do Mantenedor (`/ai-fix`):\n{instrucao_extra}")
        return "\n\n".join(partes)


_REGEX_SECAO_DESCRICAO = re.compile(
    r"##\s*Descrição\s*\n(.*?)(?=\n###\s*Captura de Tela|\n##\s*Informações Gerais|\Z)",
    re.DOTALL,
)
_REGEX_SCREENSHOT_URL = re.compile(
    r'(?:href|src)="(https?://[^"]+/screenshot\.(?:webp|png|jpg|jpeg))"',
    re.IGNORECASE,
)
_REGEX_PICO_CORPO = re.compile(r"\*\*Pico\s*/\s*Croqui:\*\*\s*`([^`]+)`")
_REGEX_PICO_ARVORE = re.compile(r"Pico\s*\(([^)]+)\)")
_REGEX_GRUPO_ARVORE = re.compile(r"Grupo\s*\(([^)]+)\)")
_REGEX_SETOR_ARVORE = re.compile(r"Setor\s*\(([^)]+)\)")
_REGEX_VIA_ARVORE = re.compile(r"Via\s*\(([^)]+)\)")
_REGEX_TITULO_CROQUI = re.compile(r"\[\s*Croqui\s*\|\s*([^\]]+)\s*\]")
_REGEX_COMANDO_AI_FIX = re.compile(r"(?:^|\n)\s*/ai-fix(?:\s+(.*))?$", re.DOTALL)


def normalizar_texto_busca(texto: str) -> str:
    """Remove acentos, converte para minúsculas e normaliza espaços para comparação textual."""
    decomposicao = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(c for c in decomposicao if unicodedata.category(c) != "Mn")
    return " ".join(sem_acentos.lower().split())


def extrair_contexto_issue_feedback(
    titulo_issue: str,
    corpo_issue: str,
    labels: list[str],
) -> ContextoFeedbackExtraido:
    """
    Extrai `croqui_id`, descrição textual do usuário, nós da árvore de navegação
    (`Grupo`, `Setor`, `Via`) e URL do screenshot a partir dos dados de uma GitHub Issue.
    """
    match_desc = _REGEX_SECAO_DESCRICAO.search(corpo_issue)
    descricao = match_desc.group(1).strip() if match_desc else corpo_issue.strip()

    match_screenshot = _REGEX_SCREENSHOT_URL.search(corpo_issue)
    url_screenshot = match_screenshot.group(1) if match_screenshot else None

    croqui_id: str | None = None
    match_pico_corpo = _REGEX_PICO_CORPO.search(corpo_issue)
    if match_pico_corpo:
        croqui_id = match_pico_corpo.group(1).strip()

    if not croqui_id:
        match_titulo = _REGEX_TITULO_CROQUI.search(titulo_issue)
        if match_titulo:
            croqui_id = match_titulo.group(1).strip()

    if not croqui_id:
        for label in labels:
            if label.startswith("pico:"):
                croqui_id = label.split("pico:", 1)[1].strip()
                break

    if not croqui_id:
        match_pico_arvore = _REGEX_PICO_ARVORE.search(corpo_issue)
        if match_pico_arvore:
            croqui_id = match_pico_arvore.group(1).strip()

    match_grupo = _REGEX_GRUPO_ARVORE.search(corpo_issue)
    match_setor = _REGEX_SETOR_ARVORE.search(corpo_issue)
    match_via = _REGEX_VIA_ARVORE.search(corpo_issue)

    return ContextoFeedbackExtraido(
        croqui_id=croqui_id,
        descricao_usuario=descricao,
        nome_grupo=match_grupo.group(1).strip() if match_grupo else None,
        nome_setor=match_setor.group(1).strip() if match_setor else None,
        nome_via=match_via.group(1).strip() if match_via else None,
        url_screenshot=url_screenshot,
    )


def extrair_instrucao_comentario_ai_fix(corpo_comentario: str) -> str | None:
    """
    Verifica se o comentário contém o comando `/ai-fix` e retorna a instrução
    fornecida pelo mantenedor (ou string vazia se `/ai-fix` sem argumentos).
    Retorna `None` caso o comentário não contenha `/ai-fix`.
    """
    match = _REGEX_COMANDO_AI_FIX.search(corpo_comentario)
    if not match:
        return None
    instrucao = match.group(1)
    return instrucao.strip() if instrucao else ""


def _descrever_escalada_linha(esc: Any) -> tuple[str, str]:
    """Retorna `(nome_via, linha_formatada)` para o índice estrutural compacto."""
    modalidade = str(esc.WhichOneof("tipo") or "")
    sub = getattr(esc, modalidade)
    nome_via = str(getattr(sub, "nome", "") or "")
    campo_dif = sub.DESCRIPTOR.fields_by_name.get("dificuldade")
    val_dif = int(getattr(sub, "dificuldade", 0) or 0)
    grau = (
        campo_dif.enum_type.values_by_number[val_dif].name
        if campo_dif is not None and val_dif in campo_dif.enum_type.values_by_number
        else "PROJETO"
    )
    conqs = ", ".join(str(c) for c in getattr(sub, "conquistadores", []))
    sufixo_conq = f" | conquistadores=[{conqs}]" if conqs else ""
    linha = (
        f"      * Escalada uid={esc.uid} | {modalidade} | "
        f"nome={nome_via!r} | grau={grau}{sufixo_conq}"
    )
    return nome_via, linha


def _montar_indice_e_candidatos_foco(
    sessao: SessaoEditorHeadless,
) -> tuple[str, list[tuple[str, str, list[str]]]]:
    """
    Percorre a árvore Protobuf ativa e retorna `(indice_textual, candidatos_setor)`
    onde cada item de `candidatos_setor` é `(uid_setor, nome_setor, nomes_escaladas)`.
    """
    raiz = getattr(sessao.croqui_model.obter_croqui_readonly(), "_obj", None)
    assert raiz is not None

    linhas: list[str] = [
        f"- Croqui id={raiz.id!r} | uid={raiz.uid} | nome={raiz.nome!r} | botoes={len(raiz.botoes)}"
    ]
    for idx_b, botao in enumerate(raiz.botoes):
        linhas.append(f"  - Botao[{idx_b}] uid={botao.uid} | texto={botao.texto!r}")

    candidatos_setor: list[tuple[str, str, list[str]]] = []
    for idx_p, pico in enumerate(raiz.picos):
        linhas.append(
            f"- Pico picos.{idx_p} | nome={pico.nome!r} | cidade={pico.cidade!r} | estado={pico.estado}"
        )
        for idx_sg, sg in enumerate(pico.setores_ou_grupos):
            if sg.HasField("grupo"):
                grp = sg.grupo.conteudo
                linhas.append(
                    f"  - Grupo uid={grp.uid} (picos.{idx_p}.setores_ou_grupos.{idx_sg}) | "
                    f"nome={grp.nome!r} | mapas={len(grp.mapas)} | setores={len(grp.setores)}"
                )
                setores_iter = [arq_s.conteudo for arq_s in grp.setores]
            else:
                setores_iter = [sg.setor.conteudo]

            for setor in setores_iter:
                linhas.append(
                    f"    - Setor uid={setor.uid} | nome={setor.nome!r} | "
                    f"mapas={len(setor.mapas)} | escaladas={len(setor.escaladas)}"
                )
                nomes_vias: list[str] = []
                for esc in setor.escaladas:
                    nome_v, linha_esc = _descrever_escalada_linha(esc)
                    nomes_vias.append(nome_v)
                    linhas.append(linha_esc)
                candidatos_setor.append((str(setor.uid), str(setor.nome), nomes_vias))

    return "\n".join(linhas), candidatos_setor


def _resolver_uid_setor_foco(
    contexto: ContextoFeedbackExtraido,
    candidatos_setor: list[tuple[str, str, list[str]]],
) -> str:
    if contexto.nome_setor:
        alvo_setor = normalizar_texto_busca(contexto.nome_setor)
        for uid_s, nome_s, _ in candidatos_setor:
            if nome_s and normalizar_texto_busca(nome_s) == alvo_setor:
                return uid_s

    if contexto.nome_via:
        alvo_via = normalizar_texto_busca(contexto.nome_via)
        for uid_s, _, vias in candidatos_setor:
            if any(normalizar_texto_busca(v) == alvo_via for v in vias):
                return uid_s

    texto_desc = normalizar_texto_busca(contexto.descricao_usuario)
    for uid_s, nome_s, vias in candidatos_setor:
        nome_norm = normalizar_texto_busca(nome_s)
        bateu_setor = len(nome_norm) >= 4 and nome_norm in texto_desc
        bateu_via = any(
            len(normalizar_texto_busca(v)) >= 4 and normalizar_texto_busca(v) in texto_desc
            for v in vias
        )
        if bateu_setor or bateu_via:
            return uid_s

    return ""


def construir_pacote_warm_start(
    sessao: SessaoEditorHeadless,
    contexto: ContextoFeedbackExtraido,
) -> PacoteWarmStartCroqui:
    """
    Extrai o pacote *Warm-Start* completo diretamente da `SessaoEditorHeadless` sem
    realizar nenhuma chamada de IA.
    """
    res_skill = sessao.chamar_ferramenta(
        "aresta_ler_skill", {"nome_skill": "resolver_feedback_croqui"}
    )
    instrucoes_skill = str(res_skill["structuredContent"]["conteudo_markdown"])

    res_lista = sessao.chamar_ferramenta("aresta_listar_skills", {})
    skills = res_lista["structuredContent"]["skills"]
    catalogo_skills = "\n".join(f"- `{item['nome']}`: {item['descricao']}" for item in skills)

    indice_estrutural, candidatos_setor = _montar_indice_e_candidatos_foco(sessao)
    uid_foco = _resolver_uid_setor_foco(contexto, candidatos_setor)
    subarvore_json = ""
    if uid_foco:
        res_arvore = sessao.chamar_ferramenta(
            "aresta_obter_arvore",
            {"alvo": uid_foco, "incluir_indice_uids": False},
        )
        subarvore_json = json.dumps(res_arvore["structuredContent"], ensure_ascii=False, indent=2)

    return PacoteWarmStartCroqui(
        croqui_id=sessao.id_croqui,
        descricao_usuario=contexto.descricao_usuario,
        instrucoes_skill=instrucoes_skill,
        catalogo_skills=catalogo_skills,
        indice_estrutural=indice_estrutural,
        uid_foco=uid_foco,
        subarvore_foco_json=subarvore_json,
    )
