# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest

from editor.caos.motor_robo_caotico import ConfiguracaoSessaoCaos, MotorRoboCaoticoQt
from editor.caos.receita_crash_robo import ReceitaCrashRobo

DIRETORIO_CAMINHOS_REGRESSAO = Path(__file__).resolve().parent / "caminhos_regressao"


def listar_receitas_regressao() -> list[Path]:
    if not DIRETORIO_CAMINHOS_REGRESSAO.is_dir():
        return []
    return sorted(DIRETORIO_CAMINHOS_REGRESSAO.glob("*.json"))


@pytest.mark.parametrize(
    "caminho_receita",
    listar_receitas_regressao(),
    ids=lambda p: p.stem,
)
def test_reproduzir_receita_regressao_sem_falhas(
    caminho_receita: Path,
    tmp_path: Path,
) -> None:
    """
    Reproduz deterministicamente cada receita de crash salva em editor/caos/caminhos_regressao/
    garantindo que os bugs históricos corrigidos nunca voltem a ocorrer.
    """
    receita = ReceitaCrashRobo.carregar_json(caminho_receita)
    cfg = ConfiguracaoSessaoCaos(
        seed=receita.seed,
        max_passos=max(1, len(receita.passos_minimos)),
        dataset=receita.dataset,
        escopo=receita.escopo,
    )
    motor = MotorRoboCaoticoQt(tmp_path / f"regressao_{caminho_receita.stem}", cfg)
    falha = motor.reproduzir_passos(receita.passos_minimos)
    assert falha is None, (
        f"Falha ao reproduzir receita de regressão '{caminho_receita.name}': "
        f"[{falha.oraculo}] {falha.tipo_excecao}: {falha.mensagem}"
    )
