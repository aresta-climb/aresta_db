# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para utilitários de sanitização de serialização de croquis.
"""

import ast
import os
import tomllib
from pathlib import Path

from editor.core.serializacao_util import (
    CABECALHO_SPDX_YAML,
    DUMPER_YAML,
    LOADER_YAML,
    carregar_yaml,
    configurar_yaml_representer,
    escrever_texto_se_modificado,
    sanitizar_dicionario_sem_extensoes,
    serializar_yaml,
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

    saida = serializar_yaml(dados, incluir_cabecalho_spdx=False)

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

    # 2. Mesmo conteúdo (em LF ou CRLF) não deve reescrever o arquivo (preservando mtime)
    mtime_antigo = 1_600_000_000
    os.utime(arq, (mtime_antigo, mtime_antigo))
    assert escrever_texto_se_modificado(arq, "linha 1\nlinha 2\n") is False
    assert escrever_texto_se_modificado(arq, "linha 1\r\nlinha 2\r\n") is False
    assert int(arq.stat().st_mtime) == mtime_antigo

    # 3. Se o arquivo no disco tiver CRLF legado mas o mesmo conteúdo lógico:
    arq.write_bytes(b"linha 1\r\nlinha 2\r\n")
    assert (
        escrever_texto_se_modificado(arq, "linha 1\nlinha 2\n", forcar_lf_no_disco=False) is False
    )
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


def test_carregar_e_serializar_yaml_com_cabecalho_spdx():
    """Garante round-trip determinístico com CSafeLoader/CSafeDumper e injeção opcional de SPDX."""
    dados = {
        "uid": "x8siJek3FiG3aB",
        "nome": "Serra do Cipó",
        "rotulo": "01",
        "negativo": "-5",
        "descricao": "Primeira linha\nSegunda linha",
    }

    texto_sem_spdx = serializar_yaml(dados, incluir_cabecalho_spdx=False)
    assert not texto_sem_spdx.startswith("# SPDX-License-Identifier:")
    assert "rotulo: '01'" in texto_sem_spdx
    assert "negativo: '-5'" in texto_sem_spdx
    assert "descricao: |-\n  Primeira linha\n  Segunda linha" in texto_sem_spdx
    assert "Serra do Cipó" in texto_sem_spdx

    texto_com_spdx = serializar_yaml(dados, incluir_cabecalho_spdx=True)
    assert texto_com_spdx.startswith(CABECALHO_SPDX_YAML)
    assert texto_com_spdx == CABECALHO_SPDX_YAML + texto_sem_spdx

    # Carregamento via carregar_yaml deve ignorar comentários de cabeçalho e reconstruir os dados
    reconstruido = carregar_yaml(texto_com_spdx)
    assert reconstruido == dados

    import io

    buf = io.StringIO()
    retornado = serializar_yaml(dados, buf, incluir_cabecalho_spdx=True)
    assert buf.getvalue() == retornado
    buf.seek(0)
    assert carregar_yaml(buf) == dados


def test_libyaml_csafeloader_e_csafedumper_obrigatorios_e_configurados_no_pyproject():
    """Garante que CSafeLoader e CSafeDumper (LibYAML em C) estão ativos e protegidos contra build sem LibYAML."""
    assert LOADER_YAML.__name__ == "CSafeLoader"
    assert DUMPER_YAML.__name__ == "CSafeDumper"

    raiz_repo = Path(__file__).resolve().parent.parent.parent
    pyproject_path = raiz_repo / "pyproject.toml"
    dados_toml = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    no_build = dados_toml.get("tool", {}).get("uv", {}).get("no-build-package", [])
    assert "pyyaml" in [p.lower() for p in no_build], (
        "pyproject.toml deve conter 'pyyaml' em [tool.uv].no-build-package para garantir instalação de wheel com LibYAML."
    )

    spec_path = raiz_repo / "editor" / "EditorAresta.spec"
    assert "yaml._yaml" in spec_path.read_text(encoding="utf-8"), (
        "EditorAresta.spec deve incluir 'yaml._yaml' em hiddenimports."
    )


def test_arquitetura_proibe_import_yaml_fora_dos_modulos_autorizados():
    """
    Garante arquiteturalmente que nenhum arquivo Python do repositório (exceto
    editor/core/serializacao_util.py e scripts/markdown_frontmatter_lib.py) importe
    diretamente 'yaml' ou 'ruamel'.
    """
    raiz_repo = Path(__file__).resolve().parent.parent.parent
    arquivos_autorizados = {
        "editor/core/serializacao_util.py",
        "scripts/markdown_frontmatter_lib.py",
    }
    pastas_monitoradas = ("editor", "scripts", "serving", "coleta_de_betas", "migracoes", "tests")

    violacoes: list[str] = []
    for nome_pasta in pastas_monitoradas:
        pasta = raiz_repo / nome_pasta
        if not pasta.exists():
            continue
        for caminho_py in sorted(pasta.rglob("*.py")):
            if any(p in ("build", "dist", "__pycache__") for p in caminho_py.parts):
                continue
            rel = caminho_py.relative_to(raiz_repo).as_posix()
            if rel in arquivos_autorizados:
                continue
            arvore = ast.parse(caminho_py.read_text(encoding="utf-8"), filename=rel)
            for no in ast.walk(arvore):
                if isinstance(no, ast.Import):
                    for alias in no.names:
                        if alias.name in ("yaml", "ruamel") or alias.name.startswith(
                            ("yaml.", "ruamel.")
                        ):
                            violacoes.append(f"{rel}:{no.lineno} (import {alias.name})")
                elif isinstance(no, ast.ImportFrom) and no.module:
                    if no.module in ("yaml", "ruamel") or no.module.startswith(
                        ("yaml.", "ruamel.")
                    ):
                        violacoes.append(f"{rel}:{no.lineno} (from {no.module} import ...)")

    assert not violacoes, (
        "Importação direta de 'yaml' ou 'ruamel' é proibida fora de "
        f"{sorted(arquivos_autorizados)}. Use carregar_yaml / serializar_yaml de "
        "editor.core.serializacao_util.\nViolações encontradas:\n  - " + "\n  - ".join(violacoes)
    )
