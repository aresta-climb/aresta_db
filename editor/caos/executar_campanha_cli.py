# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import argparse
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ_REPO))

DIRETORIO_PADRAO_RECEITAS = Path(__file__).resolve().parent / "caminhos_regressao"


def construir_parser_cli() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos de linha de comando para execução local do Robô Caótico."""
    parser = argparse.ArgumentParser(
        description="Executa localmente uma campanha de Fuzz Testing do Robô Caótico no Editor Aresta."
    )
    parser.add_argument(
        "--duracao",
        type=float,
        default=60.0,
        help="Duração máxima da campanha em segundos (padrão: 60.0).",
    )
    parser.add_argument(
        "--passos",
        type=int,
        default=60,
        help="Quantidade máxima de passos por semente (padrão: 60).",
    )
    parser.add_argument(
        "--max-sementes",
        type=int,
        default=1000,
        help="Limite máximo de sementes na campanha (padrão: 1000).",
    )
    parser.add_argument(
        "--seed-inicial",
        type=int,
        default=5000,
        help="Semente inicial determinística da campanha (padrão: 5000).",
    )
    parser.add_argument(
        "--diretorio-receitas",
        type=Path,
        default=DIRETORIO_PADRAO_RECEITAS,
        help="Diretório onde receitas .json de crashes inéditos serão salvas.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa em modo offscreen (sem abrir janela visível na tela).",
    )
    parser.add_argument(
        "--sem-sentry",
        action="store_true",
        help="Desativa o envio automático de crashes inéditos e anexos .json ao Sentry.",
    )
    return parser


def configurar_plataforma_qt_cli(headless: bool) -> None:
    """Define a plataforma gráfica do Qt (offscreen para headless ou janela nativa visível por padrão)."""
    if headless:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    else:
        os.environ.pop("QT_QPA_PLATFORM", None)


def executar_cli(
    argv: Sequence[str] | None = None,
    injetar_falha_no_passo: int | None = None,
) -> int:
    """
    Ponto de entrada programático e de linha de comando para rodar o Fuzz Testing localmente.
    Retorna 0 se nenhuma falha for encontrada, ou 1 caso ao menos um crash seja detectado.
    """
    parser = construir_parser_cli()
    args = parser.parse_args(list(argv) if argv is not None else None)
    configurar_plataforma_qt_cli(headless=bool(args.headless))

    from editor.caos.motor_robo_caotico import MotorRoboCaoticoQt

    reportar_sentry = not bool(args.sem_sentry)
    status_sentry = "ativo (com anexo .json)" if reportar_sentry else "desativado"
    print(
        f"🤖 Iniciando campanha do Robô Caótico "
        f"(duração={args.duracao}s, passos={args.passos}, "
        f"seed_inicial={args.seed_inicial}, sentry={status_sentry})..."
    )

    with tempfile.TemporaryDirectory(prefix="aresta_caos_") as pasta_tmp:
        resumo = MotorRoboCaoticoQt.executar_campanha(
            raiz_tmp=Path(pasta_tmp),
            duracao_segundos=float(args.duracao),
            seed_inicial=int(args.seed_inicial),
            max_sementes=int(args.max_sementes),
            passos_por_semente=int(args.passos),
            diretorio_receitas=Path(args.diretorio_receitas),
            reportar_sentry=reportar_sentry,
            injetar_falha_no_passo=injetar_falha_no_passo,
        )

    if resumo.falhas_totais > 0:
        caminhos_str = ", ".join(str(p) for p in resumo.receitas_salvas)
        print(
            f"❌ Campanha encontrou {resumo.falhas_totais} falha(s) "
            f"({resumo.falhas_unicas} única(s)) em {resumo.sementes_executadas} semente(s). "
            f"Receitas salvas: {caminhos_str}"
        )
        return 1

    print(
        f"✅ Campanha concluída sem falhas ({resumo.sementes_executadas} semente(s) executada(s))."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(executar_cli())
