# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from editor.core.migracao_setor import (
    validar_movimento_permitido,
    calcular_novo_caminho_setor,
    verificar_colisao_nome_arquivo,
)


def test_validar_movimento_permitido_setor_entre_itens():
    """Setor pode ser solto entre itens em uma lista de setores ou setores_ou_grupos."""
    assert validar_movimento_permitido("setor", "setor", eh_sobre_item=False) is True
    assert validar_movimento_permitido("setor", "grupo", eh_sobre_item=False) is True


def test_validar_movimento_permitido_setor_sobre_grupo():
    """Setor pode ser solto sobre um nó de grupo para ser aninhado nele."""
    assert validar_movimento_permitido("setor", "grupo", eh_sobre_item=True) is True


def test_validar_movimento_permitido_setor_sobre_setor_invalido():
    """Setor NÃO pode ser solto sobre outro setor (não existe aninhamento de setor)."""
    assert validar_movimento_permitido("setor", "setor", eh_sobre_item=True) is False


def test_validar_movimento_permitido_grupo_sobre_grupo_invalido():
    """Grupo NÃO pode ser solto sobre outro grupo (não existem grupos aninhados)."""
    assert validar_movimento_permitido("grupo", "grupo", eh_sobre_item=True) is False


def test_validar_movimento_permitido_grupo_sobre_setor_invalido():
    """Grupo NÃO pode ser solto sobre um setor."""
    assert validar_movimento_permitido("grupo", "setor", eh_sobre_item=True) is False


def test_validar_movimento_permitido_grupo_entre_itens_no_pico():
    """Grupo pode ser reordenado entre outros itens na raiz do pico."""
    assert validar_movimento_permitido("grupo", "grupo", eh_sobre_item=False) is True
    assert validar_movimento_permitido("grupo", "setor", eh_sobre_item=False) is True


def test_validar_movimento_permitido_botoes():
    """Botões podem ser reordenados entre si, mas nunca aninhados."""
    assert validar_movimento_permitido("botao", "botao", eh_sobre_item=False) is True
    assert validar_movimento_permitido("botao", "botao", eh_sobre_item=True) is False
    assert validar_movimento_permitido("botao", "setor", eh_sobre_item=False) is False
    assert validar_movimento_permitido("botao", "grupo", eh_sobre_item=False) is False


def test_validar_movimento_permitido_picos():
    """Picos podem ser reordenados entre si, mas nunca aninhados."""
    assert validar_movimento_permitido("pico", "pico", eh_sobre_item=False) is True
    assert validar_movimento_permitido("pico", "pico", eh_sobre_item=True) is False
    assert validar_movimento_permitido("pico", "setor", eh_sobre_item=False) is False


def test_validar_movimento_permitido_nos_virtuais_e_expandos():
    """Nós virtuais de adição podem receber drops entre itens (inserção no fim), mas nunca sobre eles."""
    assert validar_movimento_permitido("no_adicao", "setor", eh_sobre_item=False) is False
    assert validar_movimento_permitido("expando", "setor", eh_sobre_item=False) is False
    assert validar_movimento_permitido("setor", "no_adicao", eh_sobre_item=False) is True
    assert validar_movimento_permitido("botao", "no_adicao", eh_sobre_item=False) is True
    assert validar_movimento_permitido("setor", "no_adicao", eh_sobre_item=True) is False
    assert validar_movimento_permitido("botao", "no_adicao", eh_sobre_item=True) is False



def test_calcular_novo_caminho_setor_raiz_para_grupo():
    """Ao mover setor da raiz para dentro de um grupo, adiciona prefixo grupo_{slug}."""
    novo = calcular_novo_caminho_setor("setor_savassinha.md", "Savassinha", nome_grupo_destino="Vale Oculto")
    assert novo == "grupo_vale_oculto_setor_savassinha.md"


def test_calcular_novo_caminho_setor_grupo_para_raiz():
    """Ao mover setor de dentro de um grupo para a raiz do pico, remove prefixo grupo_{slug}."""
    novo = calcular_novo_caminho_setor("grupo_vale_oculto_setor_savassinha.md", "Savassinha", nome_grupo_destino=None)
    assert novo == "setor_savassinha.md"


def test_calcular_novo_caminho_setor_entre_grupos():
    """Ao mover setor de um grupo para outro, substitui o prefixo do grupo."""
    novo = calcular_novo_caminho_setor(
        "grupo_vale_oculto_setor_savassinha.md",
        "Savassinha",
        nome_grupo_destino="Falésia Central"
    )
    assert novo == "grupo_falesia_central_setor_savassinha.md"


def test_calcular_novo_caminho_setor_nome_livre_sem_prefixo():
    """Garante que arquivos com nomes fora do padrão recebam prefixo consistente."""
    novo_grupo = calcular_novo_caminho_setor("meu_setor.md", "Meu Setor", nome_grupo_destino="Vale Oculto")
    assert novo_grupo == "grupo_vale_oculto_setor_meu_setor.md"

    novo_raiz = calcular_novo_caminho_setor("meu_setor.md", "Meu Setor", nome_grupo_destino=None)
    assert novo_raiz == "setor_meu_setor.md"

    # Nome legível do setor já começa com "Setor"
    novo_com_palavra_setor = calcular_novo_caminho_setor("arquivo.md", "Setor Principal", nome_grupo_destino="Vale")
    assert novo_com_palavra_setor == "grupo_vale_setor_principal.md"


def test_verificar_colisao_nome_arquivo():
    """Verifica se há conflito de nomes considerando case-insensitivity e ignorando o próprio arquivo."""
    existentes = {"setor_a.md", "grupo_x_setor_b.md"}

    # Conflito exato
    assert verificar_colisao_nome_arquivo("setor_a.md", existentes) is True

    # Conflito case-insensitive
    assert verificar_colisao_nome_arquivo("SETOR_A.MD", existentes) is True

    # Sem conflito
    assert verificar_colisao_nome_arquivo("setor_c.md", existentes) is False

    # Ignora o próprio arquivo atual do setor
    assert verificar_colisao_nome_arquivo("setor_a.md", existentes, caminho_atual_proprio="setor_a.md") is False


def test_validar_movimento_permitido_tipos_desconhecidos():
    """Garante recusa de tipos desconhecidos ou alvos inválidos."""
    assert validar_movimento_permitido("desconhecido", "setor", eh_sobre_item=False) is False
    assert validar_movimento_permitido("grupo", "desconhecido", eh_sobre_item=False) is False
    assert validar_movimento_permitido("setor", "desconhecido", eh_sobre_item=False) is False


def test_calcular_novo_caminho_setor_nome_vazio():
    """Quando o nome do setor for vazio ou sem caracteres alfanuméricos."""
    assert calcular_novo_caminho_setor("invalido", "", nome_grupo_destino=None) == "setor.md"

