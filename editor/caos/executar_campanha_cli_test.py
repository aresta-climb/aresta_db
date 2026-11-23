# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from pathlib import Path

from editor.caos.executar_campanha_cli import (
    configurar_plataforma_qt_cli,
    construir_parser_cli,
    executar_cli,
    resolver_seed_inicial_campanha,
)


def test_parser_cli_possui_padroes_amigaveis_para_execucao_local() -> None:
    parser = construir_parser_cli()
    args = parser.parse_args([])

    assert args.duracao == 60.0
    assert args.passos == 60
    assert args.max_sementes == 1000
    assert args.seed_inicial == 0
    assert args.headless is False
    assert args.sem_sentry is False
    assert Path(args.diretorio_receitas).name == "caminhos_regressao"


def test_resolver_seed_inicial_campanha_gera_semente_variavel_por_padrao_e_preserva_explicita() -> (
    None
):
    import time

    seed_a = resolver_seed_inicial_campanha(None)
    time.sleep(0.003)
    seed_b = resolver_seed_inicial_campanha(0)
    seed_c = resolver_seed_inicial_campanha("0")
    seed_vazia = resolver_seed_inicial_campanha("   ")

    for s in (seed_a, seed_b, seed_c, seed_vazia):
        assert 1 <= s < 100_000_000
    assert seed_a != seed_b

    assert resolver_seed_inicial_campanha(4242) == 4242
    assert resolver_seed_inicial_campanha("7777") == 7777


def test_configurar_plataforma_qt_cli_alterna_entre_visivel_e_offscreen() -> None:
    plataforma_original = os.environ.get("QT_QPA_PLATFORM")
    try:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        configurar_plataforma_qt_cli(headless=False)
        assert "QT_QPA_PLATFORM" not in os.environ

        configurar_plataforma_qt_cli(headless=True)
        assert os.environ.get("QT_QPA_PLATFORM") == "offscreen"
    finally:
        if plataforma_original is None:
            os.environ.pop("QT_QPA_PLATFORM", None)
        else:
            os.environ["QT_QPA_PLATFORM"] = plataforma_original


def test_executar_cli_retorna_zero_sem_falhas_e_um_quando_encontra_crash(
    tmp_path: Path,
) -> None:
    import runpy
    import sys

    import pytest

    pasta_receitas = tmp_path / "receitas_cli"
    argv_original = sys.argv[:]
    try:
        sys.argv = [
            "executar_campanha_cli.py",
            "--headless",
            "--sem-sentry",
            "--duracao",
            "3.0",
            "--max-sementes",
            "1",
            "--passos",
            "4",
            "--seed-inicial",
            "6001",
            "--diretorio-receitas",
            str(pasta_receitas),
        ]
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("editor.caos.executar_campanha_cli", run_name="__main__")
        assert exc_info.value.code == 0
    finally:
        sys.argv = argv_original

    codigo_falha = executar_cli(
        [
            "--headless",
            "--sem-sentry",
            "--duracao",
            "5.0",
            "--max-sementes",
            "1",
            "--passos",
            "5",
            "--seed-inicial",
            "6002",
            "--diretorio-receitas",
            str(pasta_receitas),
        ],
        injetar_falha_no_passo=2,
    )
    assert codigo_falha == 1
    arquivos_gerados = list(pasta_receitas.glob("crash_seed_6002_*.json"))
    assert len(arquivos_gerados) == 1
