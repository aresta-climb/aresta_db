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
    raiz = tmp_path / "projeto"
    criar_croqui_teste_pb(raiz, pico_id="br_mg_igarape_pedra_grande")
    pasta_saida = tmp_path / "lote_cli"
    pasta_saida.mkdir()

    codigo = main([
        "--lote-pico", "br_mg_igarape_pedra_grande",
        "--raiz-projeto", str(raiz),
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
    raiz_borda = tmp_path / "raiz_borda"
    criar_croqui_teste_pb(raiz_borda, pico_id="br_mg_igarape_pedra_grande")
    pasta_lote = tmp_path / "lote_borda"
    pasta_lote.mkdir()
    cod_lote = main([
        "--lote-pico", "br_mg_igarape_pedra_grande",
        "--raiz-projeto", str(raiz_borda),
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
    raiz_aresta = tmp_path / "raiz_aresta"
    criar_croqui_teste_pb(raiz_aresta, pico_id="br_mg_igarape_pedra_grande")
    pasta_lote = tmp_path / "lote_aresta"
    pasta_lote.mkdir()
    cod_lote = main([
        "--lote-pico", "br_mg_igarape_pedra_grande",
        "--raiz-projeto", str(raiz_aresta),
        "--limite", "1",
        "--logo-aresta", str(logo_custom),
        "--saida", str(pasta_lote),
        "--largura", "800",
        "--altura", "1000",
    ])
    assert cod_lote == 0


def test_cli_parametros_utm(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Testa inclusão de parâmetros UTM padrão e customizados no CLI."""
    pasta_saida = tmp_path / "utm"
    pasta_saida.mkdir()

    cod = main([
        "--pico", "br_mg_igarape_pedra_grande",
        "--setor", "savassinha",
        "--utm-source", "teste_fonte",
        "--utm-medium", "teste_midia",
        "--utm-campaign", "teste_campanha",
        "--saida", str(pasta_saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])
    assert cod == 0
    saida = capsys.readouterr().out
    assert "utm_source=teste_fonte" in saida
    assert "utm_medium=teste_midia" in saida
    assert "utm_campaign=teste_campanha" in saida


def criar_croqui_teste_pb(raiz: Path, pico_id: str = "pico_teste") -> Path:
    """Cria uma árvore hermética de teste com um compilado.binarypb válido."""
    from aresta_api.proto.generated import croqui_pb2

    pasta_compilado = raiz / "generated" / pico_id
    pasta_compilado.mkdir(parents=True, exist_ok=True)
    caminho_pb = pasta_compilado / "compilado.binarypb"

    croqui = croqui_pb2.Croqui()
    croqui.nome = "Pedra Grande de Teste"

    pico = croqui.picos.add()
    pico.nome = "Pedra Grande"

    elem_setor = pico.setores_ou_grupos.add()
    setor = elem_setor.setor.conteudo
    setor.nome = "Savassinha"

    via_esp = setor.escaladas.add()
    via_esp.via_esportiva.nome = "Dama de Ferro"
    via_esp.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A

    boulder = setor.escaladas.add()
    boulder.boulder.nome = "Boulder Teste"
    boulder.boulder.dificuldade = croqui_pb2.GrauBoulder.V3

    elem_grupo = pico.setores_ou_grupos.add()
    grupo = elem_grupo.grupo.conteudo
    grupo.nome = "Grupo Estacionamento"

    arq_setor = grupo.setores.add()
    setor_filho = arq_setor.conteudo
    setor_filho.nome = "Bloco Dengoso"

    via_filho = setor_filho.escaladas.add()
    via_filho.via_esportiva.nome = "Via Dengosa"
    via_filho.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP

    caminho_pb.write_bytes(croqui.SerializeToString())
    return caminho_pb


def test_cli_raiz_projeto_customizada(tmp_path: Path) -> None:
    """Testa execução do modo lote com --raiz-projeto explícita."""
    raiz_custom = tmp_path / "raiz_custom"
    criar_croqui_teste_pb(raiz_custom, pico_id="pico_custom")
    saida = tmp_path / "saida_custom"

    codigo = main([
        "--lote-pico", "pico_custom",
        "--raiz-projeto", str(raiz_custom),
        "--limite", "1",
        "--saida", str(saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])
    assert codigo == 0
    assert len(list(saida.glob("*.svg"))) >= 1


def test_cli_lote_raiz_padrao_com_monkeypatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Testa que o CLI usa DIRETORIO_RAIZ_PADRAO quando --raiz-projeto é omitido."""
    import scripts.gerar_placas_qrcodes_lib as lib

    criar_croqui_teste_pb(tmp_path, pico_id="pico_raiz_padrao")
    monkeypatch.setattr(lib, "DIRETORIO_RAIZ_PADRAO", tmp_path)

    saida = tmp_path / "saida_padrao"
    codigo = main([
        "--lote-pico", "pico_raiz_padrao",
        "--limite", "1",
        "--saida", str(saida),
        "--largura", "800",
        "--altura", "1000",
        "--apenas-svg",
    ])
    assert codigo == 0
    assert len(list(saida.glob("*.svg"))) >= 1


