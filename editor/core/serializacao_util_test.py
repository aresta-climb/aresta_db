# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para utilitários de sanitização de serialização de croquis.
"""

from editor.core.serializacao_util import sanitizar_dicionario_sem_extensoes


def test_sanitizar_dicionario_sem_extensoes_primitivos():
    """Garante que tipos primitivos e não-coleções são retornados sem alteração."""
    assert sanitizar_dicionario_sem_extensoes(123) == 123
    assert sanitizar_dicionario_sem_extensoes("texto") == "texto"
    assert sanitizar_dicionario_sem_extensoes(3.14) == 3.14
    assert sanitizar_dicionario_sem_extensoes(True) is True
    assert sanitizar_dicionario_sem_extensoes(None) is None


def test_sanitizar_dicionario_sem_extensoes_chaves_simples():
    """Garante que chaves de extensão de shadow state são removidas de dicionários simples."""
    dados = {
        "nome": "Setor Exemplo",
        "uid": "abc123xyz45678",
        "[aresta.ArquivoSetor.ext_metadados_arquivo]": {"caminho_original": "antigo.md"},
        "ext_metadados": "vazado",
        "outra_ext_metadados_campo": 123,
    }

    resultado = sanitizar_dicionario_sem_extensoes(dados)

    assert resultado == {
        "nome": "Setor Exemplo",
        "uid": "abc123xyz45678",
    }


def test_sanitizar_dicionario_sem_extensoes_aninhados_e_listas():
    """Garante a sanitização recursiva em árvores profundas com dicionários e listas."""
    dados = {
        "croqui": {
            "picos": [
                {
                    "nome": "Pico Principal",
                    "[aresta.ArquivoMapas.ext_metadados_arquivo]": {"caminho_original": "mapas.md"},
                    "setores": [
                        {
                            "nome": "Setor 1",
                            "ext_metadados_arquivo": {"shadow": True},
                            "escaladas": [{"nome": "Via 1", "uid": "via12345678901"}],
                        }
                    ],
                }
            ],
            "[aresta.Croqui.ext_metadados_arquivo]": {"caminho_original": "croqui.yaml"},
        }
    }

    resultado = sanitizar_dicionario_sem_extensoes(dados)

    assert resultado == {
        "croqui": {
            "picos": [
                {
                    "nome": "Pico Principal",
                    "setores": [
                        {
                            "nome": "Setor 1",
                            "escaladas": [{"nome": "Via 1", "uid": "via12345678901"}],
                        }
                    ],
                }
            ]
        }
    }


def test_sanitizar_dicionario_sem_extensoes_chaves_nao_string():
    """Garante suporte robusto a dicionários que possuam chaves que não sejam string."""
    dados = {
        1: "um",
        2: "dois",
        "[ext_invalida]": "remover",
    }

    resultado = sanitizar_dicionario_sem_extensoes(dados)

    assert resultado == {
        1: "um",
        2: "dois",
    }
