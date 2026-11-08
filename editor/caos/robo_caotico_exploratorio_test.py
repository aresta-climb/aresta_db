# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from pathlib import Path

from editor.caos.motor_robo_caotico import MotorRoboCaoticoQt

DIRETORIO_PADRAO_RECEITAS = Path(__file__).resolve().parent / "caminhos_regressao"


def test_campanha_exploratoria_robo_caotico(tmp_path: Path) -> None:
    """
    Executa uma campanha exploratória do Robô Caótico sobre o Editor Aresta.
    Configurável via variáveis de ambiente para execuções longas na CI:
    - DURACAO_CAMPANHA_CAOS_SEGUNDOS (padrão: 4.0s localmente; 300s no workflow de release)
    - MAX_SEMENTES_CAOS (padrão: 2 localmente ou 1000 quando DURACAO_CAMPANHA_CAOS_SEGUNDOS é definido)
    - PASSOS_POR_SEMENTE_CAOS (padrão: 25)
    - REPORTAR_SENTRY_CAOS (padrão: "1", enviando falhas inéditas e o arquivo .json ao Sentry)
    """
    duracao_env = os.environ.get("DURACAO_CAMPANHA_CAOS_SEGUNDOS")
    duracao_segundos = float(duracao_env) if duracao_env else 4.0
    max_sementes_padrao = 1000 if duracao_env else 2
    max_sementes = int(os.environ.get("MAX_SEMENTES_CAOS", str(max_sementes_padrao)))
    passos_por_semente = int(os.environ.get("PASSOS_POR_SEMENTE_CAOS", "25"))
    seed_inicial = int(os.environ.get("SEED_INICIAL_CAOS", "2026"))
    reportar_sentry = os.environ.get("REPORTAR_SENTRY_CAOS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    dir_receitas_env = os.environ.get("DIRETORIO_SAIDA_RECEITAS_CAOS")
    diretorio_receitas = (
        Path(dir_receitas_env) if dir_receitas_env else (tmp_path / "receitas_encontradas")
    )

    resumo = MotorRoboCaoticoQt.executar_campanha(
        raiz_tmp=tmp_path / "campanha_exploratoria",
        duracao_segundos=duracao_segundos,
        seed_inicial=seed_inicial,
        max_sementes=max_sementes,
        passos_por_semente=passos_por_semente,
        diretorio_receitas=diretorio_receitas,
        reportar_sentry=reportar_sentry,
    )

    assert resumo.sementes_executadas >= 1
    assert resumo.falhas_totais == 0, (
        f"Robô Caótico encontrou {resumo.falhas_totais} falha(s) "
        f"({resumo.falhas_unicas} única(s)). Receitas salvas: {resumo.receitas_salvas}"
    )
