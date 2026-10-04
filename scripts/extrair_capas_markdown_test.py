# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from PIL import Image
import pytest
from scripts.extrair_capas_markdown import (
    extrair_primeira_imagem_markdown,
    remover_tag_imagem_do_corpo,
    otimizar_imagem_se_necessario,
    encontrar_diretorio_pico,
    promover_capa_arquivo_md,
    processar_diretorio,
    main,
)


def test_extrair_primeira_imagem_markdown():
    corpo = "Texto antes\n\n![Foto Bonita](imagens/setor.webp)\n\nTexto depois"
    resultado = extrair_primeira_imagem_markdown(corpo)
    assert resultado is not None
    alt, caminho, start, end = resultado
    assert alt == "Foto Bonita"
    assert caminho == "imagens/setor.webp"
    assert corpo[start:end] == "![Foto Bonita](imagens/setor.webp)"


def test_extrair_primeira_imagem_markdown_sem_imagem():
    corpo = "Texto sem imagem nenhuma."
    assert extrair_primeira_imagem_markdown(corpo) is None


def test_extrair_primeira_imagem_multiplas():
    corpo = "![Primeira](imagens/1.webp)\n\n![Segunda](imagens/2.webp)"
    resultado = extrair_primeira_imagem_markdown(corpo)
    assert resultado is not None
    alt, caminho, _, _ = resultado
    assert alt == "Primeira"
    assert caminho == "imagens/1.webp"


def test_remover_tag_imagem_do_corpo():
    corpo = "# Titulo\n\n![Capa](imagens/capa.webp)\n\nDescricao do setor."
    resultado = extrair_primeira_imagem_markdown(corpo)
    assert resultado is not None
    _, _, start, end = resultado
    novo_corpo = remover_tag_imagem_do_corpo(corpo, start, end)
    assert "![Capa]" not in novo_corpo
    assert "# Titulo" in novo_corpo
    assert "Descricao do setor." in novo_corpo
    assert novo_corpo == "# Titulo\n\nDescricao do setor."


def test_remover_tag_imagem_no_inicio_do_corpo():
    corpo = "![Capa](imagens/capa.webp)\n\nTexto de abertura."
    resultado = extrair_primeira_imagem_markdown(corpo)
    assert resultado is not None
    _, _, start, end = resultado
    novo_corpo = remover_tag_imagem_do_corpo(corpo, start, end)
    assert novo_corpo == "Texto de abertura."


def test_remover_tag_imagem_preserva_segunda_imagem():
    corpo = "# Titulo\n\n![Capa](imagens/capa.webp)\n\nTexto intermediario\n\n![Segunda](imagens/segunda.webp)"
    resultado = extrair_primeira_imagem_markdown(corpo)
    assert resultado is not None
    _, _, start, end = resultado
    novo_corpo = remover_tag_imagem_do_corpo(corpo, start, end)
    assert "![Capa]" not in novo_corpo
    assert "![Segunda](imagens/segunda.webp)" in novo_corpo


def test_otimizar_imagem_se_necessario_imagem_grande(tmp_path: Path):
    caminho_img = tmp_path / "grande.webp"
    # Cria imagem de 2000 x 1000 = 2.000.000 pixels (excede 1 MP)
    img = Image.new("RGB", (2000, 1000), color=(100, 150, 200))
    img.save(caminho_img, "WEBP")

    modificado = otimizar_imagem_se_necessario(caminho_img, max_area=1_000_000, qualidade=85)
    assert modificado is True

    with Image.open(caminho_img) as img_otimizada:
        w, h = img_otimizada.size
        assert w * h <= 1_000_000


def test_otimizar_imagem_se_necessario_imagem_pequena(tmp_path: Path):
    caminho_img = tmp_path / "pequena.webp"
    # Cria imagem de 800 x 600 = 480.000 pixels (dentro de 1 MP)
    img = Image.new("RGB", (800, 600), color=(50, 50, 50))
    img.save(caminho_img, "WEBP")
    bytes_originais = caminho_img.read_bytes()

    modificado = otimizar_imagem_se_necessario(caminho_img, max_area=1_000_000, qualidade=85)
    assert modificado is False
    assert caminho_img.read_bytes() == bytes_originais


def test_otimizar_imagem_se_necessario_arquivo_inexistente(tmp_path: Path):
    caminho_img = tmp_path / "nao_existe.webp"
    assert otimizar_imagem_se_necessario(caminho_img) is False


def test_encontrar_diretorio_pico(tmp_path: Path):
    pico_dir = tmp_path / "meu_pico"
    pico_dir.mkdir()
    (pico_dir / "croqui.yaml").write_text("nome: Teste\n", encoding="utf-8")

    sub_dir = pico_dir / "sub"
    sub_dir.mkdir()
    arquivo_md = sub_dir / "setor_teste.md"
    arquivo_md.write_text("# Teste\n", encoding="utf-8")

    assert encontrar_diretorio_pico(arquivo_md) == pico_dir


def test_encontrar_diretorio_pico_sem_croqui(tmp_path: Path):
    arquivo_md = tmp_path / "setor_teste.md"
    arquivo_md.write_text("# Teste\n", encoding="utf-8")
    assert encontrar_diretorio_pico(arquivo_md) == tmp_path


def test_promover_capa_arquivo_md_sucesso(tmp_path: Path):
    pico_dir = tmp_path / "pico"
    pico_dir.mkdir()
    (pico_dir / "croqui.yaml").write_text("nome: Pico\n", encoding="utf-8")

    imagens_dir = pico_dir / "imagens"
    imagens_dir.mkdir()
    img_path = imagens_dir / "foto_setor.webp"
    # 1500 x 1000 = 1.5 MP (deve ser otimizada)
    Image.new("RGB", (1500, 1000), color=(10, 20, 30)).save(img_path, "WEBP")

    md_file = pico_dir / "setor_principal.md"
    conteudo_inicial = (
        "---\n"
        "nome: Setor Principal\n"
        "---\n\n"
        "# Setor Principal\n\n"
        "![Vista Geral](imagens/foto_setor.webp)\n\n"
        "Descricao detalhada do setor.\n"
    )
    md_file.write_text(conteudo_inicial, encoding="utf-8")

    modificado = promover_capa_arquivo_md(md_file)
    assert modificado is True

    from scripts.preparar_submissao_lib import parse_md_com_frontmatter
    frontmatter, corpo = parse_md_com_frontmatter(md_file)
    assert frontmatter is not None
    assert frontmatter.get("caminho_imagem_capa") == "imagens/foto_setor.webp"
    assert frontmatter.get("nome") == "Setor Principal"
    assert "![Vista Geral]" not in corpo
    assert "Descricao detalhada do setor." in corpo

    with Image.open(img_path) as img_verif:
        assert img_verif.width * img_verif.height <= 1_000_000


def test_promover_capa_arquivo_md_idempotente(tmp_path: Path):
    md_file = tmp_path / "setor_com_capa.md"
    conteudo = (
        "---\n"
        "caminho_imagem_capa: imagens/ja_tem_capa.webp\n"
        "nome: Setor\n"
        "---\n\n"
        "![Outra](imagens/outra.webp)\n"
    )
    md_file.write_text(conteudo, encoding="utf-8")

    modificado = promover_capa_arquivo_md(md_file)
    assert modificado is False
    assert md_file.read_text(encoding="utf-8") == conteudo


def test_promover_capa_arquivo_md_sem_imagem(tmp_path: Path):
    md_file = tmp_path / "setor_sem_imagem.md"
    conteudo = (
        "---\n"
        "nome: Setor Sem Imagem\n"
        "---\n\n"
        "Apenas texto sem tag de imagem.\n"
    )
    md_file.write_text(conteudo, encoding="utf-8")

    modificado = promover_capa_arquivo_md(md_file)
    assert modificado is False
    assert md_file.read_text(encoding="utf-8") == conteudo


def test_promover_capa_arquivo_md_sem_frontmatter(tmp_path: Path):
    md_file = tmp_path / "arquivo_sem_frontmatter.md"
    conteudo = "# Apenas Markdown\n\n![Foto](imagens/foto.webp)\n"
    md_file.write_text(conteudo, encoding="utf-8")

    modificado = promover_capa_arquivo_md(md_file)
    assert modificado is False
    assert md_file.read_text(encoding="utf-8") == conteudo


def test_promover_capa_arquivo_md_imagem_nao_encontrada(tmp_path: Path):
    md_file = tmp_path / "setor_img_inexistente.md"
    conteudo = (
        "---\n"
        "nome: Setor\n"
        "---\n\n"
        "![Foto Fantasma](imagens/fantasma.webp)\n"
    )
    md_file.write_text(conteudo, encoding="utf-8")

    modificado = promover_capa_arquivo_md(md_file)
    assert modificado is True

    from scripts.preparar_submissao_lib import parse_md_com_frontmatter
    frontmatter, corpo = parse_md_com_frontmatter(md_file)
    assert frontmatter["caminho_imagem_capa"] == "imagens/fantasma.webp"
    assert "![Foto Fantasma]" not in corpo


def test_processar_diretorio(tmp_path: Path):
    pico_dir = tmp_path / "meu_pico"
    pico_dir.mkdir()
    (pico_dir / "croqui.yaml").write_text("nome: Meu Pico\n", encoding="utf-8")

    # Setor 1: tem imagem
    md1 = pico_dir / "setor_1.md"
    md1.write_text("---\nnome: S1\n---\n\n![S1](imagens/s1.webp)\n", encoding="utf-8")

    # Grupo 1: tem imagem
    md2 = pico_dir / "grupo_1.md"
    md2.write_text("---\nnome: G1\n---\n\n![G1](imagens/g1.webp)\n", encoding="utf-8")

    # Setor 2: não tem imagem
    md3 = pico_dir / "setor_2.md"
    md3.write_text("---\nnome: S2\n---\n\nSem imagem\n", encoding="utf-8")

    # Outro arquivo (não setor nem grupo): deve ser ignorado
    md4 = pico_dir / "notas.md"
    md4.write_text("---\nnome: Notas\n---\n\n![Nota](imagens/nota.webp)\n", encoding="utf-8")

    stats = processar_diretorio(pico_dir)
    assert stats["total_verificados"] == 3
    assert stats["promovidos"] == 2
    assert stats["ignorados"] == 1


def test_main_cli(tmp_path: Path, monkeypatch, capsys):
    pico_dir = tmp_path / "meu_pico"
    pico_dir.mkdir()
    (pico_dir / "croqui.yaml").write_text("nome: Meu Pico\n", encoding="utf-8")
    md = pico_dir / "setor_cli.md"
    md.write_text("---\nnome: Setor CLI\n---\n\n![CLI](imagens/cli.webp)\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["extrair_capas_markdown.py", str(pico_dir)])
    main()

    captured = capsys.readouterr()
    assert "Concluído" in captured.out
    assert "Promovidos: 1" in captured.out


def test_otimizar_imagem_se_necessario_erro_corrompida(tmp_path: Path):
    caminho_img = tmp_path / "corrompida.webp"
    caminho_img.write_bytes(b"dados-invalidos-nao-imagem")
    assert otimizar_imagem_se_necessario(caminho_img) is False


def test_promover_capa_arquivo_md_erro_leitura(tmp_path: Path):
    md_file = tmp_path / "setor_invalido.md"
    # YAML inválido provocando exceção no parser
    md_file.write_text("---\n: invalido: :\n---\nCorpo\n", encoding="utf-8")
    assert promover_capa_arquivo_md(md_file) is False


def test_main_cli_arquivo_individual(tmp_path: Path, monkeypatch, capsys):
    md_file = tmp_path / "setor_sozinho.md"
    md_file.write_text("---\nnome: Sozinho\n---\n\n![Img](imagens/img.webp)\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["extrair_capas_markdown.py", str(md_file)])
    main()

    captured = capsys.readouterr()
    assert "Arquivo processado. Promovido: True" in captured.out


def test_main_cli_padrao_database(monkeypatch, capsys):
    from unittest.mock import MagicMock
    import scripts.extrair_capas_markdown as mod

    mock_processar = MagicMock(return_value={"total_verificados": 0, "promovidos": 0, "ignorados": 0})
    monkeypatch.setattr(mod, "processar_diretorio", mock_processar)
    monkeypatch.setattr("sys.argv", ["extrair_capas_markdown.py"])

    main()
    captured = capsys.readouterr()
    assert "Iniciando extração de capas em:" in captured.out
    assert mock_processar.called

