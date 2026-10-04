# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from editor.core.classificador_mensagens import (
    eh_linha_de_erro,
    eh_linha_de_aviso,
    eh_linha_de_aviso_ou_erro,
    filtrar_mensagens_de_log,
)


def test_eh_linha_de_erro_casos_positivos():
    casos = [
        "Erro: arquivo yaml invalido.",
        "ERRO: falha ao processar imagem.",
        "[ERRO] Falha de validação",
        "The compilation failed to start.",
        "ERROR 500",
        "Um ErRo Aconteceu",
        "Falhou miseravelmente",
        "RuntimeError: croqui não encontrado",
        "ValueError: campo obrigatório ausente",
        "Traceback (most recent call last):",
        "Exception: falha fatal",
    ]
    for caso in casos:
        assert eh_linha_de_erro(caso) is True, f"Deveria ser erro: {caso}"


def test_eh_linha_de_erro_falsos_positivos_ferros_e_afins():
    casos = [
        "Alvos específicos  : [WindowsPath('database/br_mg_ferros_ferros')]",
        "[br_mg_ferros_ferros] (1/1)",
        "  Gerando thumbnail: imagens/capa_p0_i0.webp -> thumbnails/br_mg_ferros_ferros.webp",
        "  Imagens copiadas: generated/br_mg_ferros_ferros/imagens",
        "  107 imagem(ns) indexada(s) em arquivos_externos",
        "Via Ferrovia do Diabo",
        "Uso de ferramenta apropriada",
        "Parede de ferro oxidado",
    ]
    for caso in casos:
        assert eh_linha_de_erro(caso) is False, f"Não deveria ser erro: {caso}"


def test_eh_linha_de_aviso_casos_positivos():
    casos = [
        "Aviso: ID duplicado.",
        "AVISO: processo cancelado.",
        "Avisos detectados durante validação",
        "Warning: chave depreciada",
        "WARNING: imagem com resolução baixa",
    ]
    for caso in casos:
        assert eh_linha_de_aviso(caso) is True, f"Deveria ser aviso: {caso}"


def test_eh_linha_de_aviso_falsos_positivos():
    casos = [
        "Travessia das Sombras",
        "Avisado previamente pelo guia",  # Não é a palavra aviso/warning isolada
        "[br_mg_ferros_ferros] (1/1)",
        "Compilação concluída com sucesso.",
    ]
    for caso in casos:
        assert eh_linha_de_aviso(caso) is False, f"Não deveria ser aviso: {caso}"


def test_eh_linha_de_aviso_ou_erro():
    assert eh_linha_de_aviso_ou_erro("Erro: teste") is True
    assert eh_linha_de_aviso_ou_erro("Aviso: teste") is True
    assert eh_linha_de_aviso_ou_erro("[br_mg_ferros_ferros] (1/1)") is False
    assert eh_linha_de_aviso_ou_erro("Isso é um print normal.") is False


def test_filtrar_mensagens_de_log():
    saida = (
        "Isso é um print normal.\n"
        "Alvos específicos  : [WindowsPath('database/br_mg_ferros_ferros')]\n"
        "[br_mg_ferros_ferros] (1/1)\n"
        "  Gerando thumbnail: imagens/capa_p0_i0.webp\n"
        "  Imagens copiadas: generated/br_mg_ferros_ferros/imagens\n"
        "  107 imagem(ns) indexada(s) em arquivos_externos\n"
        "Aviso: ID duplicado.\n"
        "  continuação sem palavra chave na linha indentada\n"
        "\n"
        "Outro texto normal após linha vazia\n"
        "Erro ao compilar via.\n"
        "  Traceback detalhado\n"
        "\n"
    )

    mensagens = filtrar_mensagens_de_log(saida)

    assert "Aviso: ID duplicado." in mensagens
    assert "  continuação sem palavra chave na linha indentada" in mensagens
    assert "" in mensagens
    assert "Erro ao compilar via." in mensagens
    assert "  Traceback detalhado" in mensagens

    # As mensagens de Ferros NÃO devem ser capturadas!
    assert "Alvos específicos  : [WindowsPath('database/br_mg_ferros_ferros')]" not in mensagens
    assert "[br_mg_ferros_ferros] (1/1)" not in mensagens
    assert "  Gerando thumbnail: imagens/capa_p0_i0.webp" not in mensagens
    assert "  Imagens copiadas: generated/br_mg_ferros_ferros/imagens" not in mensagens
    assert "  107 imagem(ns) indexada(s) em arquivos_externos" not in mensagens
    assert "Isso é um print normal." not in mensagens
    assert "Outro texto normal após linha vazia" not in mensagens
    assert mensagens[-1] != ""
