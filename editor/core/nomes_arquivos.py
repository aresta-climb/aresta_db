# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Módulo de utilitários para deduplicação e geração padronizada de nomes de arquivos e mapas."""

from typing import Any, Optional
from aresta_api.proto.generated import croqui_pb2
from editor.core.formatacao import para_snake_case


def deduplicar_prefixo(nome: Optional[str], prefixo: str) -> str:
    """Deduplica o prefixo em nomes de entidades para geração de nomes em snake_case.

    Evita nomes redundantes como 'setor_setor_fugitivos'.

    Exemplos:
        deduplicar_prefixo("Setor Fugitivos I", "setor") -> "setor_fugitivos_i"
        deduplicar_prefixo("Fugitivos I", "setor") -> "setor_fugitivos_i"
        deduplicar_prefixo("Setor", "setor") -> "setor"
        deduplicar_prefixo("", "setor") -> "setor"
    """
    prefixo_limpo = prefixo.strip().lower()
    if not nome:
        return prefixo_limpo

    slug = para_snake_case(nome)
    if not slug or slug == prefixo_limpo:
        return prefixo_limpo

    if slug.startswith(f"{prefixo_limpo}_"):
        return slug

    return f"{prefixo_limpo}_{slug}"


def gerar_nome_mapa_sugerido(entidade: Any, indice: int) -> str:
    """Gera nome sugerido de mapa para Setor, Grupo ou ColecaoDeMapas com sufixo de página.

    Exemplos:
        Setor com nome "Setor Fugitivos I", indice 0 -> "setor_fugitivos_i_p0.webp"
        Setor com nome "Pedra do Sino", indice 0 -> "setor_pedra_do_sino_p0.webp"
        ColecaoDeMapas, indice 0 -> "mapas_gerais_p0.webp"
    """
    obj = getattr(entidade, "_obj", entidade)

    if isinstance(obj, croqui_pb2.Setor):
        base = deduplicar_prefixo(getattr(obj, "nome", None), "setor")
    elif isinstance(obj, croqui_pb2.Grupo):
        base = deduplicar_prefixo(getattr(obj, "nome", None), "grupo")
    else:
        base = "mapas_gerais"

    return f"{base}_p{indice}.webp"


def gerar_nome_arquivo_entidade(nome: Optional[str], tipo: str) -> str:
    """Gera nome de arquivo Markdown para um Setor ou Grupo deduplicando prefixo.

    Exemplos:
        gerar_nome_arquivo_entidade("Setor do Meio", "setor") -> "setor_do_meio.md"
        gerar_nome_arquivo_entidade("Falésia", "setor") -> "setor_falesia.md"
        gerar_nome_arquivo_entidade("Grupo Principal", "grupo") -> "grupo_principal.md"
    """
    base = deduplicar_prefixo(nome, tipo)
    return f"{base}.md"
