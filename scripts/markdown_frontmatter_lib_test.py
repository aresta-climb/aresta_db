# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest

from scripts.markdown_frontmatter_lib import (
    parse_md_com_frontmatter,
    salvar_md_com_frontmatter,
)


def test_parse_md_com_frontmatter_arquivo_com_frontmatter_valido(tmp_path: Path) -> None:
    """Garante a extração correta de frontmatter YAML e corpo de markdown."""
    arquivo = tmp_path / "exemplo.md"
    conteudo = "---\ntitulo: Pico Teste\naltitude: 1200\n---\n\nEste é o corpo do texto.\n"
    arquivo.write_text(conteudo, encoding="utf-8")

    frontmatter, corpo = parse_md_com_frontmatter(arquivo)

    assert frontmatter == {"titulo": "Pico Teste", "altitude": 1200}
    assert corpo == "Este é o corpo do texto."


def test_parse_md_com_frontmatter_sem_frontmatter(tmp_path: Path) -> None:
    """Garante que arquivos sem cabeçalho frontmatter retornem None e o corpo preservado."""
    arquivo = tmp_path / "sem_fm.md"
    conteudo = "# Apenas Markdown\n\nNenhum frontmatter aqui.\n"
    arquivo.write_text(conteudo, encoding="utf-8")

    frontmatter, corpo = parse_md_com_frontmatter(arquivo)

    assert frontmatter is None
    assert corpo == "# Apenas Markdown\n\nNenhum frontmatter aqui."


def test_parse_md_com_frontmatter_frontmatter_vazio(tmp_path: Path) -> None:
    """Garante tratamento gracioso de frontmatter delimitado mas vazio."""
    arquivo = tmp_path / "vazio.md"
    conteudo = "---\n---\nCorpo após frontmatter vazio."
    arquivo.write_text(conteudo, encoding="utf-8")

    frontmatter, corpo = parse_md_com_frontmatter(arquivo)

    assert frontmatter is None
    assert corpo == "Corpo após frontmatter vazio."


def test_parse_md_com_frontmatter_yaml_invalido_lanca_value_error(tmp_path: Path) -> None:
    """Garante que erro de sintaxe YAML resulte em ValueError quando solicitado."""
    arquivo = tmp_path / "invalido.md"
    conteudo = "---\n[sintaxe: invalida: :\n---\nCorpo"
    arquivo.write_text(conteudo, encoding="utf-8")

    with pytest.raises(ValueError, match="Erro de YAML no frontmatter"):
        parse_md_com_frontmatter(arquivo, lancar_erro_yaml=True)


def test_parse_md_com_frontmatter_yaml_invalido_retorna_dicionario_vazio_por_padrao(tmp_path: Path) -> None:
    """Garante que erro de sintaxe YAML retorne dicionário vazio por padrão."""
    arquivo = tmp_path / "invalido_padrao.md"
    conteudo = "---\n[sintaxe: invalida: :\n---\nCorpo"
    arquivo.write_text(conteudo, encoding="utf-8")

    frontmatter, corpo = parse_md_com_frontmatter(arquivo)
    assert frontmatter == {}
    assert corpo == "Corpo"


def test_parse_md_com_frontmatter_erro_leitura_arquivo(tmp_path: Path) -> None:
    """Garante lançamento de RuntimeError em falha de acesso/leitura do arquivo."""
    arquivo_inexistente = tmp_path / "inexistente.md"

    with pytest.raises(RuntimeError, match="Erro ao ler arquivo"):
        parse_md_com_frontmatter(arquivo_inexistente)


def test_parse_md_com_frontmatter_aceita_caminho_string(tmp_path: Path) -> None:
    """Garante que a função aceite str como caminho."""
    arquivo = tmp_path / "caminho_str.md"
    arquivo.write_text("---\nchave: valor\n---\nCorpo", encoding="utf-8")

    frontmatter, corpo = parse_md_com_frontmatter(str(arquivo))

    assert frontmatter == {"chave": "valor"}
    assert corpo == "Corpo"


def test_salvar_md_com_frontmatter_com_dados(tmp_path: Path) -> None:
    """Garante a escrita do frontmatter com metadados SPDX e Copyright adequados."""
    arquivo = tmp_path / "salvo.md"
    frontmatter = {"nome": "Setor Falésia", "grau": "7a"}
    corpo = "Descrição da falésia."

    salvar_md_com_frontmatter(arquivo, frontmatter, corpo)

    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    assert linhas[0].strip() == "---"
    assert linhas[1].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[2].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"

    fm_lido, corpo_lido = parse_md_com_frontmatter(arquivo)
    assert fm_lido == frontmatter
    assert corpo_lido == corpo


def test_salvar_md_com_frontmatter_sem_frontmatter_apenas_corpo(tmp_path: Path) -> None:
    """Garante que quando frontmatter for None, apenas o corpo é gravado sem blocos YAML."""
    arquivo = tmp_path / "apenas_corpo.md"
    corpo = "# Título Puro\n\nTexto sem frontmatter."

    salvar_md_com_frontmatter(arquivo, None, corpo)

    conteudo_salvo = arquivo.read_text(encoding="utf-8")
    assert not conteudo_salvo.startswith("---")
    assert conteudo_salvo == corpo


def test_salvar_md_com_frontmatter_aceita_caminho_string(tmp_path: Path) -> None:
    """Garante que salvar_md_com_frontmatter aceite str além de Path."""
    arquivo = tmp_path / "salvo_str.md"
    salvar_md_com_frontmatter(str(arquivo), {"ok": True}, "Texto")

    fm_lido, corpo_lido = parse_md_com_frontmatter(arquivo)
    assert fm_lido == {"ok": True}
    assert corpo_lido == "Texto"


def test_salvar_md_com_frontmatter_escreve_lf_preserva_mtime_e_usa_bloco_literal(
    tmp_path: Path,
) -> None:
    """Garante que salvar_md_com_frontmatter grava em LF, usa '|-' em multilinhas e preserva mtime quando igual."""
    import os

    arquivo = tmp_path / "salvo_lf.md"
    frontmatter = {"id": "09", "descricao": "Linha 1\n\nLinha 2"}
    corpo = "Corpo linha 1\r\nCorpo linha 2"

    salvar_md_com_frontmatter(arquivo, frontmatter, corpo)

    raw_bytes = arquivo.read_bytes()
    assert b"\r\n" not in raw_bytes
    texto = raw_bytes.decode("utf-8")
    assert "id: '09'" in texto
    assert "descricao: |-\n  Linha 1\n\n  Linha 2" in texto

    mtime_antigo = 1_600_000_000
    os.utime(arquivo, (mtime_antigo, mtime_antigo))

    salvar_md_com_frontmatter(arquivo, frontmatter, "Corpo linha 1\nCorpo linha 2")
    assert int(arquivo.stat().st_mtime) == mtime_antigo

