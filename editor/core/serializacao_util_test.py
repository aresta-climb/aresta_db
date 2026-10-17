# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para utilitários de sanitização de serialização de croquis.
"""

from pathlib import Path
from unittest.mock import patch

import yaml

from editor.core.serializacao_util import (
    configurar_yaml_representer,
    escrever_texto_se_modificado,
    sanitizar_dicionario_sem_extensoes,
)


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


def test_representar_string_yaml_e_configurar_representer():
    """Garante formatação com '|' para multilinhas e aspas simples para dígitos positivos e negativos."""
    configurar_yaml_representer()
    dados = {
        "id_positivo": "08",
        "id_negativo": "-12",
        "texto_simples": "Setor Principal",
        "descricao": "Linha 1\n\nLinha 2",
    }

    saida_dumper = yaml.dump(dados, allow_unicode=True, sort_keys=False)
    saida_safe = yaml.safe_dump(dados, allow_unicode=True, sort_keys=False)

    for saida in (saida_dumper, saida_safe):
        assert "id_positivo: '08'" in saida
        assert "id_negativo: '-12'" in saida
        assert "texto_simples: Setor Principal" in saida
        assert "descricao: |-\n  Linha 1\n\n  Linha 2" in saida


def test_escrever_texto_se_modificado_cria_e_preserva_quando_igual(tmp_path: Path):
    """Garante escrita em LF, não-reescrita quando o conteúdo lógico é igual e atualização quando muda."""
    arq = tmp_path / "sub" / "teste.md"

    # 1. Criação inicial (converte CRLF para LF)
    modificado = escrever_texto_se_modificado(arq, "linha 1\r\nlinha 2\r\n")
    assert modificado is True
    assert arq.read_bytes() == b"linha 1\nlinha 2\n"

    # 2. Mesmo conteúdo (em LF ou CRLF) não deve reescrever o arquivo
    with patch("builtins.open", wraps=open) as mock_open:
        assert escrever_texto_se_modificado(arq, "linha 1\nlinha 2\n") is False
        assert escrever_texto_se_modificado(arq, "linha 1\r\nlinha 2\r\n") is False
        mock_open.assert_not_called()

    # 3. Se o arquivo no disco tiver CRLF legado mas o mesmo conteúdo lógico:
    arq.write_bytes(b"linha 1\r\nlinha 2\r\n")
    assert escrever_texto_se_modificado(arq, "linha 1\nlinha 2\n", forcar_lf_no_disco=False) is False
    assert arq.read_bytes() == b"linha 1\r\nlinha 2\r\n"

    # 4. Com forcar_lf_no_disco=True, regrava se o disco estiver em CRLF:
    assert escrever_texto_se_modificado(arq, "linha 1\nlinha 2\n", forcar_lf_no_disco=True) is True
    assert arq.read_bytes() == b"linha 1\nlinha 2\n"
    assert escrever_texto_se_modificado(arq, "linha 1\nlinha 2\n", forcar_lf_no_disco=True) is False

    # 5. Quando o conteúdo muda, regrava com LF:
    assert escrever_texto_se_modificado(arq, "linha 1\nlinha 3\n") is True
    assert arq.read_bytes() == b"linha 1\nlinha 3\n"

    # 6. Quando o arquivo existente tem bytes inválidos UTF-8, sobrescreve normalmente:
    arq.write_bytes(b"\xff\xfe\x00")
    assert escrever_texto_se_modificado(arq, "novo texto\n") is True
    assert arq.read_bytes() == b"novo texto\n"

