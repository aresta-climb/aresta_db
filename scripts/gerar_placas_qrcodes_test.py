# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para o utilitário CLI scripts/gerar_placas_qrcodes.py."""

from pathlib import Path
import pytest

from scripts.gerar_placas_qrcodes import main


def test_cli_ajuda(capsys: pytest.CaptureFixture[str]) -> None:
    """Verifica se o CLI exibe instruções de ajuda quando solicitado."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    saida = capsys.readouterr().out
    assert "Geração de placas físicas e QR Codes" in saida
    assert "--pico" in saida
    assert "--lote-pico" in saida


def test_cli_modo_individual_sucesso(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Testa geração de placa única via CLI em formato PNG e SVG (com flag --svg)."""
    pasta_saida = tmp_path / "placas_cli"
    pasta_saida.mkdir()

    codigo = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--titulo", "Setor Savassinha",
        "--subtitulo", "Pedra Grande · Igarapé, MG",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--svg",
    ])

    assert codigo == 0
    saida = capsys.readouterr().out
    assert "Placa individual gerada com sucesso" in saida
    arquivos = list(pasta_saida.glob("placa_*"))
    assert len(arquivos) >= 2  # PNG e SVG


def test_cli_modo_individual_apenas_png(tmp_path: Path) -> None:
    """Testa geração individual padrão (apenas PNG A4 600 DPI)."""
    pasta_saida = tmp_path / "placas_cli_png"
    pasta_saida.mkdir()

    codigo = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
    ])

    assert codigo == 0
    arquivos_png = list(pasta_saida.glob("*.png"))
    arquivos_svg = list(pasta_saida.glob("*.svg"))
    assert len(arquivos_png) == 1
    assert len(arquivos_svg) == 0


def test_cli_modo_individual_apenas_svg(tmp_path: Path) -> None:
    """Testa geração individual com filtro apenas SVG."""
    pasta_saida = tmp_path / "placas_cli_svg"
    pasta_saida.mkdir()

    codigo = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])

    assert codigo == 0
    arquivos_png = list(pasta_saida.glob("*.png"))
    arquivos_svg = list(pasta_saida.glob("*.svg"))
    assert len(arquivos_png) == 0
    assert len(arquivos_svg) == 1


def test_cli_modo_lote_sucesso(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Testa geração em lote para todos os setores de um pico."""
    pasta_saida = tmp_path / "lote_cli"
    pasta_saida.mkdir()

    codigo = main([
        "--lote-pico", "br_mg_igarape_pedra_grande",
        "--limite", "2",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
    ])

    assert codigo == 0
    saida = capsys.readouterr().out
    assert "Exportação em lote concluída" in saida
    arquivos = list(pasta_saida.glob("placa_*"))
    assert len(arquivos) >= 2


def test_cli_parametros_insuficientes(capsys: pytest.CaptureFixture[str]) -> None:
    """Testa erro ao executar sem especificar nem --pico nem --lote-pico."""
    codigo = main([])
    assert codigo != 0
    saida = capsys.readouterr().err
    assert "Erro: você deve informar" in saida


def test_cli_titulos_derivados_via_e_grupo(tmp_path: Path) -> None:
    """Testa derivação automática de título e subtítulo para via, grupo e pico."""
    pasta_saida = tmp_path / "titulos"
    pasta_saida.mkdir()

    # Via
    cod_via = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--via", "teto_da_aresta",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])
    assert cod_via == 0
    assert (pasta_saida / "placa_teto_da_aresta.svg").exists()

    # Grupo
    cod_grupo = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--grupo", "grupo_estacionamento",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])
    assert cod_grupo == 0
    assert (pasta_saida / "placa_grupo_estacionamento.svg").exists()

    # Pico apenas
    cod_pico = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])
    assert cod_pico == 0
    assert (pasta_saida / "placa_br_mg_igarape_pedra_grande.svg").exists()


def test_cli_execucao_modulo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa execução como script __main__."""
    import scripts.gerar_placas_qrcodes as modulo
    monkeypatch.setattr("sys.argv", ["gerar_placas_qrcodes", "--help"])
    with pytest.raises(SystemExit) as exc:
        modulo.main()
    assert exc.value.code == 0


def test_cli_cor_borda_logo(tmp_path: Path) -> None:
    """Testa suporte a --cor-borda-logo no modo individual e em lote."""
    pasta_saida = tmp_path / "bordas"
    pasta_saida.mkdir()

    # Individual com cor personalizada e SVG
    cod = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--cor-borda-logo", "laranja",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--svg",
    ])
    assert cod == 0
    svg_conteudo = (pasta_saida / "placa_savassinha.svg").read_text(encoding="utf-8")
    assert 'stroke="#ea5341"' in svg_conteudo

    # Lote com cor padrão ou hex
    pasta_lote = tmp_path / "lote_borda"
    pasta_lote.mkdir()
    cod_lote = main([
        "--lote-pico", "br_mg_igarape_pedra_grande",
        "--limite", "1",
        "--cor-borda-logo", "preta",
        "--saida", str(pasta_lote),
        "--largura", "800",
        "--altura", "1000",
    ])
    assert cod_lote == 0


def test_cli_logo_aresta(tmp_path: Path) -> None:
    """Testa suporte a --logo-aresta personalizado no modo individual e em lote."""
    pasta_saida = tmp_path / "logos_aresta"
    pasta_saida.mkdir()

    logo_custom = tmp_path / "custom_aresta.png"
    from PIL import Image
    Image.new("RGBA", (100, 100), (255, 100, 0, 255)).save(logo_custom)

    cod = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--logo-aresta", str(logo_custom),
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--svg",
    ])
    assert cod == 0
    assert (pasta_saida / "placa_savassinha.svg").exists()

    # Lote com logo aresta customizado
    pasta_lote = tmp_path / "lote_aresta"
    pasta_lote.mkdir()
    cod_lote = main([
        "--lote-pico", "br_mg_igarape_pedra_grande",
        "--limite", "1",
        "--logo-aresta", str(logo_custom),
        "--saida", str(pasta_lote),
        "--largura", "800",
        "--altura", "1000",
    ])
    assert cod_lote == 0
