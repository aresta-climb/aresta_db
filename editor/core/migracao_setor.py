# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Módulo de validação e regras de negócio para movimentação e migração de setores na árvore de dados."""

import re
from typing import Optional, Set
from editor.core.formatacao import para_snake_case


TIPOS_VALIDOS_REORDENACAO: Set[str] = {
    "setor",
    "arquivosetor",
    "grupo",
    "arquivogrupo",
    "botao",
    "pico",
    "escalada",
}


def validar_movimento_permitido(origem_tipo: str, destino_tipo: str, eh_sobre_item: bool) -> bool:
    """Verifica se o movimento de arrastar e soltar é compatível com o schema Protobuf.

    Args:
        origem_tipo: Tipo do nó arrastado ("setor", "grupo", "botao", "pico", etc.).
        destino_tipo: Tipo do nó alvo ("setor", "grupo", "botao", "pico", "no_adicao", etc.).
        eh_sobre_item: Se a soltura ocorre diretamente sobre o item (True) ou entre itens (False).

    Returns:
        True se o movimento for permitido; False caso contrário.
    """
    if origem_tipo in ("no_adicao", "expando") or origem_tipo not in TIPOS_VALIDOS_REORDENACAO:
        return False

    if destino_tipo == "no_adicao":
        # Permite soltar entre itens antes do botão de adição para mover ao final da lista
        return not eh_sobre_item

    if destino_tipo not in TIPOS_VALIDOS_REORDENACAO:
        return False

    tipos_setor = {"setor", "arquivosetor"}
    tipos_grupo = {"grupo", "arquivogrupo"}

    if origem_tipo in tipos_setor:
        if destino_tipo in tipos_setor:
            return not eh_sobre_item
        elif destino_tipo in tipos_grupo:
            # Setor pode ser solto entre grupos ou sobre um grupo (para migrar para dentro dele)
            return True

    elif origem_tipo in tipos_grupo:
        if destino_tipo in (tipos_grupo | tipos_setor):
            # Grupos só podem ser reordenados na raiz do pico (entre outros itens), nunca aninhados
            return not eh_sobre_item

    elif origem_tipo == destino_tipo:
        # Reordenação de mesma lista (ex: botao e botao, pico e pico)
        return not eh_sobre_item

    return False



def calcular_novo_caminho_setor(caminho_atual: str, nome_setor: str, nome_grupo_destino: Optional[str] = None) -> str:
    """Calcula o novo nome de arquivo de um setor ao ser migrado entre o Pico e um Grupo ou entre Grupos.

    Args:
        caminho_atual: Nome de arquivo atual do setor (ex: "setor_savassinha.md").
        nome_setor: Nome legível do setor (ex: "Savassinha").
        nome_grupo_destino: Nome do grupo de destino, ou None se estiver sendo movido para a raiz do Pico.

    Returns:
        Novo nome de arquivo padronizado com extensão .md.
    """
    nome_base = caminho_atual.strip()
    if nome_base.endswith(".md"):
        nome_base = nome_base[:-3]

    # Remove qualquer prefixo existente de grupo (ex: "grupo_vale_oculto_setor_x" -> "setor_x")
    if "_setor_" in nome_base:
        nome_sem_grupo = re.sub(r"^grupo_.*?_(?=setor_)", "", nome_base)
    else:
        nome_sem_grupo = re.sub(r"^grupo_[a-z0-9_]+?_", "", nome_base)

    if not nome_sem_grupo.startswith("setor_"):
        slug_setor = para_snake_case(nome_setor)
        if slug_setor.startswith("setor_"):
            nome_sem_grupo = slug_setor
        else:
            nome_sem_grupo = f"setor_{slug_setor}" if slug_setor else "setor"

    if nome_grupo_destino:
        slug_grupo = para_snake_case(nome_grupo_destino)
        return f"grupo_{slug_grupo}_{nome_sem_grupo}.md"
    else:
        return f"{nome_sem_grupo}.md"


def verificar_colisao_nome_arquivo(
    novo_caminho: str,
    caminhos_existentes: Set[str],
    caminho_atual_proprio: Optional[str] = None
) -> bool:
    """Verifica se o novo nome de arquivo colide com arquivos já existentes no croqui.

    Args:
        novo_caminho: Nome de arquivo proposto.
        caminhos_existentes: Conjunto com nomes de arquivos existentes no disco e agendados em memória.
        caminho_atual_proprio: Nome de arquivo atual do próprio item que está sendo movido.

    Returns:
        True se houver colisão de nomes; False se o caminho estiver livre.
    """
    alvo_normalizado = novo_caminho.strip().lower()

    proprio_normalizado = caminho_atual_proprio.strip().lower() if caminho_atual_proprio else None
    if proprio_normalizado and alvo_normalizado == proprio_normalizado:
        return False

    for existente in caminhos_existentes:
        if existente and existente.strip().lower() == alvo_normalizado:
            return True

    return False
