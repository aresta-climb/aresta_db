# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Módulo de utilitários para deduplicação, validação e geração padronizada de nomes de arquivos e mapas."""

import re
from collections.abc import Sequence
from typing import Any

from aresta_api.proto.generated import croqui_pb2
from editor.core.formatacao import para_snake_case

LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD: int = 100
_PADRAO_NOME_ARQUIVO_MD = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*\.md$")
_CARACTERES_ILEGAIS_SO = frozenset('<>:"/\\|?*')


def deduplicar_prefixo(nome: str | None, prefixo: str) -> str:
    """Deduplica o prefixo em nomes de entidades para geração de nomes em snake_case.

    Evita nomes redundantes como 'setor_setor_fugitivos' ou 'setor_bloco_fugitivos'.
    Caso a entidade seja um setor e seu nome utilize 'bloco' ou 'blocos', adota 'bloco'
    como prefixo automaticamente ao invés de forçar 'setor_'.

    Exemplos:
        deduplicar_prefixo("Setor Fugitivos I", "setor") -> "setor_fugitivos_i"
        deduplicar_prefixo("Bloco Fugitivos I", "setor") -> "bloco_fugitivos_i"
        deduplicar_prefixo("Blocos da Entrada", "setor") -> "blocos_da_entrada"
        deduplicar_prefixo("Fugitivos I", "setor") -> "setor_fugitivos_i"
        deduplicar_prefixo("Setor", "setor") -> "setor"
        deduplicar_prefixo("Bloco", "setor") -> "bloco"
        deduplicar_prefixo("", "setor") -> "setor"
    """
    prefixo_limpo = prefixo.strip().lower()
    if not nome:
        return prefixo_limpo

    slug = para_snake_case(nome)
    if not slug or slug == prefixo_limpo:
        return prefixo_limpo

    # Se a entidade for setor e o nome iniciar com 'bloco' ou 'blocos', adota o próprio bloco como prefixo
    if prefixo_limpo == "setor" and (
        slug in ("bloco", "blocos") or slug.startswith("bloco_") or slug.startswith("blocos_")
    ):
        return slug

    if slug.startswith(f"{prefixo_limpo}_"):
        return slug

    return f"{prefixo_limpo}_{slug}"


def extrair_prefixo_e_nome_escalada(obj: Any) -> tuple[str, str | None]:
    """Extrai o prefixo ('boulder', 'via', 'highline') e o nome de uma escalada ou sub-mensagem."""
    if isinstance(obj, croqui_pb2.Escalada):
        campo_tipo = obj.WhichOneof("tipo")
        if campo_tipo:
            sub = getattr(obj, campo_tipo)
            prefixo = (
                "boulder"
                if campo_tipo == "boulder"
                else ("highline" if campo_tipo == "highline" else "via")
            )
            nome = getattr(sub, "nome", None)
            return prefixo, nome
        return "escalada", None

    if isinstance(obj, croqui_pb2.Boulder):
        return "boulder", getattr(obj, "nome", None)
    if isinstance(
        obj, (croqui_pb2.ViaEsportiva, croqui_pb2.ViaMovel, croqui_pb2.ViaMultiplasEnfiadas)
    ):
        return "via", getattr(obj, "nome", None)
    return "highline", getattr(obj, "nome", None)


def gerar_nome_mapa_sugerido(entidade: Any, indice: int) -> str:
    """Gera nome sugerido de mapa para Setor, Grupo, Escalada ou ColecaoDeMapas com sufixo de página.

    Exemplos:
        Setor com nome "Setor Fugitivos I", indice 0 -> "setor_fugitivos_i_p0.webp"
        Setor com nome "Pedra do Sino", indice 0 -> "setor_pedra_do_sino_p0.webp"
        Escalada Boulder com nome "La Bamba", indice 0 -> "boulder_la_bamba_p0.webp"
        Escalada Via com nome "Fenda da Ilusão", indice 0 -> "via_fenda_da_ilusao_p0.webp"
        ColecaoDeMapas, indice 0 -> "mapas_gerais_p0.webp"
    """
    obj = getattr(entidade, "_obj", entidade)

    if isinstance(obj, croqui_pb2.Setor):
        base = deduplicar_prefixo(getattr(obj, "nome", None), "setor")
    elif isinstance(obj, croqui_pb2.Grupo):
        base = deduplicar_prefixo(getattr(obj, "nome", None), "grupo")
    elif isinstance(
        obj,
        (
            croqui_pb2.Escalada,
            croqui_pb2.Boulder,
            croqui_pb2.ViaEsportiva,
            croqui_pb2.ViaMovel,
            croqui_pb2.ViaMultiplasEnfiadas,
            croqui_pb2.Highline,
        ),
    ):
        prefixo, nome = extrair_prefixo_e_nome_escalada(obj)
        base = deduplicar_prefixo(nome, prefixo)
    else:
        base = "mapas_gerais"

    return f"{base}_p{indice}.webp"


def gerar_nome_arquivo_entidade(nome: str | None, tipo: str) -> str:
    """Gera nome de arquivo Markdown para um Setor ou Grupo deduplicando prefixo.

    Exemplos:
        gerar_nome_arquivo_entidade("Setor do Meio", "setor") -> "setor_do_meio.md"
        gerar_nome_arquivo_entidade("Falésia", "setor") -> "setor_falesia.md"
        gerar_nome_arquivo_entidade("Grupo Principal", "grupo") -> "grupo_principal.md"
    """
    base = deduplicar_prefixo(nome, tipo)
    return f"{base}.md"


def normalizar_entrada_nome_arquivo_md(texto: str) -> str:
    """Normaliza a entrada do usuário para nome de arquivo Markdown.

    Remove espaços nas extremidades, converte sequências de espaços internos em '_'
    e garante a extensão '.md' quando o texto não for vazio.
    """
    limpo = texto.strip()
    if not limpo:
        return ""
    sem_espacos = re.sub(r"\s+", "_", limpo)
    if not sem_espacos.endswith(".md"):
        sem_espacos = f"{sem_espacos}.md"
    return sem_espacos


def validar_nome_arquivo_md(
    texto: str,
    arquivos_existentes: Sequence[str] = (),
    arquivo_atual: str = "",
) -> tuple[bool, str, str]:
    """Valida se o nome do arquivo Markdown cumpre todas as regras de formato, tamanho e unicidade.

    Retorna uma tupla (valido, nome_normalizado, mensagem_erro).
    """
    normalizado = normalizar_entrada_nome_arquivo_md(texto)
    if not normalizado or normalizado == ".md":
        return False, normalizado, "O nome do arquivo não pode ser vazio."

    if len(normalizado) > LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD:
        return (
            False,
            normalizado,
            f"O nome do arquivo deve ter no máximo {LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD} caracteres.",
        )

    if not _PADRAO_NOME_ARQUIVO_MD.match(normalizado):
        return (
            False,
            normalizado,
            "Use apenas letras minúsculas sem acento (a-z), números (0-9) e '_' (snake_case).",
        )

    atual_lower = arquivo_atual.strip().lower()
    normalizado_lower = normalizado.lower()
    existentes_lower = {arq.strip().lower() for arq in arquivos_existentes if arq.strip()}
    if normalizado_lower != atual_lower and normalizado_lower in existentes_lower:
        return (
            False,
            normalizado,
            f"Já existe um arquivo com o nome '{normalizado}' em uso no croqui.",
        )

    return True, normalizado, ""


def _eh_caminho_original_seguro_em_disco(caminho: str) -> bool:
    """Verifica se um caminho original legado é um nome simples `.md` seguro para o sistema de arquivos."""
    limpo = caminho.strip()
    return (
        bool(limpo)
        and limpo.endswith(".md")
        and len(limpo) > 3
        and len(limpo) <= LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD
        and not any(ch in _CARACTERES_ILEGAIS_SO or ord(ch) < 32 for ch in limpo)
    )


def garantir_nome_arquivo_md_seguro(
    caminho_proposto: str | None,
    nome_entidade: str | None,
    prefixo_padrao: str,
    caminho_original: str | None = None,
) -> str:
    """Garante que um nome de arquivo Markdown seja seguro para escrita em disco (Windows/POSIX).

    - Se `caminho_proposto` já for um nome `.md` estritamente válido, retorna-o.
    - Caso contrário, se `caminho_original` for um nome de arquivo simples seguro para o SO
      (preservando arquivos legados já existentes em disco quando `caminho_proposto` estiver
      vazio ou igual ao original), retorna `caminho_original`.
    - Caso contrário, gera um nome seguro em `snake_case` a partir de `nome_entidade` e
      `prefixo_padrao`, truncado em até 100 caracteres.
    """
    proposto = (caminho_proposto or "").strip()
    original = (caminho_original or "").strip()

    if (
        proposto
        and _PADRAO_NOME_ARQUIVO_MD.match(proposto)
        and len(proposto) <= LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD
    ):
        return proposto

    if (not proposto or proposto == original) and _eh_caminho_original_seguro_em_disco(original):
        return original

    limite_base = LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD - 3  # reserva 3 chars para ".md"
    base = deduplicar_prefixo(nome_entidade, prefixo_padrao)[:limite_base].rstrip("_")
    return f"{base}.md"
