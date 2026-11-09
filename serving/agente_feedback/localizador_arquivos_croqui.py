# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Localizador em cascata de arquivos `.md`/`.yaml` de croqui e extrator de contexto
de Issues e comentários (`/ai-fix`) para resolução automatizada de feedbacks.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from editor.core.serializacao_util import carregar_yaml


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
class ResultadoLocalizacaoArquivos:
    """Resultado da busca em cascata pelos arquivos-fonte do croqui."""

    estrategia: str
    arquivos_relativos: list[str]
    precisa_desambiguacao_ia: bool
    indice_compacto: str


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


def _extrair_frontmatter_yaml(caminho_md: Path) -> dict[str, Any]:
    """Lê o bloco YAML frontmatter de um arquivo `.md` se existir e for válido."""
    texto = caminho_md.read_text(encoding="utf-8")
    if not texto.startswith("---\n") or "\n---\n" not in texto:
        return {}
    bloco_yaml = texto.split("\n---\n", 1)[0][4:]
    try:
        dados = carregar_yaml(bloco_yaml)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def _extrair_escaladas_resumo(dados_setor: dict[str, Any]) -> list[tuple[str, str]]:
    """Retorna lista de pares `(nome_via, dificuldade)` a partir do dicionário YAML do setor."""
    escaladas = dados_setor.get("escaladas") or []
    resultado: list[tuple[str, str]] = []
    for item in escaladas:
        for chave_modalidade in ("via_esportiva", "boulder", "via_tradicional", "dws", "psicobloc"):
            bloco = item.get(chave_modalidade)
            if isinstance(bloco, dict) and bloco.get("nome"):
                nome = str(bloco["nome"])
                dificuldade = str(bloco.get("dificuldade", "PROJETO"))
                resultado.append((nome, dificuldade))
    return resultado


def gerar_indice_compacto_croqui(pasta_croqui: Path) -> str:
    """
    Constrói uma representação textual enxuta de todos os arquivos `.md` de um croqui,
    listando nome do arquivo, nome do setor e escaladas (com dificuldade), omitindo
    coordenadas pesadas de mapas.
    """
    if not pasta_croqui.is_dir():
        return ""

    linhas: list[str] = []
    for caminho_md in sorted(pasta_croqui.glob("*.md")):
        dados = _extrair_frontmatter_yaml(caminho_md)
        nome_setor = dados.get("nome")
        escaladas = _extrair_escaladas_resumo(dados)
        if nome_setor or escaladas:
            vias_str = ", ".join(f"{n} ({d})" for n, d in escaladas)
            linhas.append(f"- {caminho_md.name} | Setor: {nome_setor} | Escaladas: [{vias_str}]")
        else:
            linhas.append(f"- {caminho_md.name} (documento textual)")
    return "\n".join(linhas)


def localizar_arquivos_candidatos_croqui(
    diretorio_database: Path,
    contexto: ContextoFeedbackExtraido,
    instrucao_extra: str = "",
    arquivos_modificados_pr: list[str] | None = None,
) -> ResultadoLocalizacaoArquivos:
    """
    Executa a busca em cascata (1: Determinística por PR ou Árvore de Navegação,
    2: Busca Textual Local, 3: Índice Compacto para Desambiguação por IA) para
    selecionar quais arquivos `.md`/`.yaml` de `database/<croqui_id>/` devem ser inspecionados.
    """
    pasta_croqui = diretorio_database / (contexto.croqui_id or "")

    # Nível 1A: Arquivos já modificados na Pull Request (quando acionado via /ai-fix em PR)
    if arquivos_modificados_pr and contexto.croqui_id:
        prefixo = f"database/{contexto.croqui_id}/"
        relativos_pr = [
            arq[len(prefixo) :]
            for arq in arquivos_modificados_pr
            if arq.startswith(prefixo) and arq.endswith((".md", ".yaml"))
        ]
        if relativos_pr:
            return ResultadoLocalizacaoArquivos(
                estrategia="deterministica_pr",
                arquivos_relativos=sorted(set(relativos_pr)),
                precisa_desambiguacao_ia=False,
                indice_compacto="",
            )

    arquivos_md = sorted(pasta_croqui.glob("*.md")) if pasta_croqui.is_dir() else []
    metadados_por_arquivo: list[tuple[str, str, list[str]]] = []
    for caminho_md in arquivos_md:
        dados = _extrair_frontmatter_yaml(caminho_md)
        nome_setor = str(dados.get("nome", ""))
        nomes_vias = [n for n, _ in _extrair_escaladas_resumo(dados)]
        metadados_por_arquivo.append((caminho_md.name, nome_setor, nomes_vias))

    # Nível 1B: Localização determinística pela Árvore de Navegação (Setor ou Via)
    if contexto.nome_setor:
        alvo_setor = normalizar_texto_busca(contexto.nome_setor)
        encontrados = [
            arq
            for arq, setor, _ in metadados_por_arquivo
            if setor and normalizar_texto_busca(setor) == alvo_setor
        ]
        if encontrados:
            return ResultadoLocalizacaoArquivos(
                estrategia="deterministica",
                arquivos_relativos=encontrados,
                precisa_desambiguacao_ia=False,
                indice_compacto="",
            )

    if contexto.nome_via:
        alvo_via = normalizar_texto_busca(contexto.nome_via)
        encontrados = [
            arq
            for arq, _, vias in metadados_por_arquivo
            if any(normalizar_texto_busca(v) == alvo_via for v in vias)
        ]
        if encontrados:
            return ResultadoLocalizacaoArquivos(
                estrategia="deterministica",
                arquivos_relativos=encontrados,
                precisa_desambiguacao_ia=False,
                indice_compacto="",
            )

    # Nível 2: Busca textual local normalizada no corpo do feedback + instrução extra
    texto_combinado = normalizar_texto_busca(f"{contexto.descricao_usuario} {instrucao_extra}")
    candidatos_texto: list[str] = []
    for arq, setor, vias in metadados_por_arquivo:
        setor_norm = normalizar_texto_busca(setor) if setor else ""
        bateu_setor = len(setor_norm) >= 4 and setor_norm in texto_combinado
        bateu_via = any(
            len(normalizar_texto_busca(v)) >= 4 and normalizar_texto_busca(v) in texto_combinado
            for v in vias
        )
        if bateu_setor or bateu_via:
            candidatos_texto.append(arq)

    if candidatos_texto:
        return ResultadoLocalizacaoArquivos(
            estrategia="busca_textual",
            arquivos_relativos=candidatos_texto,
            precisa_desambiguacao_ia=False,
            indice_compacto="",
        )

    # Nível 3: Desambiguação multimodal com índice compacto
    return ResultadoLocalizacaoArquivos(
        estrategia="desambiguacao_ia",
        arquivos_relativos=[],
        precisa_desambiguacao_ia=True,
        indice_compacto=gerar_indice_compacto_croqui(pasta_croqui),
    )
