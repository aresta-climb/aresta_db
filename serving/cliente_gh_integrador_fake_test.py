# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para o Fake determinístico `ClienteGhIntegradorFake`."""

from __future__ import annotations

import pytest

from serving.cliente_gh_integrador_fake import ClienteGhIntegradorFake
from serving.integrador_pr_lib import (
    CheckPullRequest,
    ErroClienteGhIntegrador,
    EstadoMergePullRequest,
    InfoPullRequest,
)


def test_registrar_e_obter_info_pr_e_erro_simulado() -> None:
    """Garante que o Fake armazena informações de PR e simula falhas determinísticas."""
    fake = ClienteGhIntegradorFake()
    info = InfoPullRequest(numero=78, branch_head="ai-fix/issue-76", branch_base="main")
    fake.registrar_info_pr(info)

    assert fake.obter_info_pr(78) == info

    fake_erro = ClienteGhIntegradorFake(erro_simulado="Falha de rede no GitHub")
    with pytest.raises(ErroClienteGhIntegrador, match="Falha de rede no GitHub"):
        fake_erro.obter_info_pr(78)


def test_sequencia_checks_pr_avanca_fila_e_repete_ultimo_estado() -> None:
    """Garante que o Fake permite simular polling de checks evoluindo de pendente para aprovado."""
    fake = ClienteGhIntegradorFake()
    assert fake.listar_checks_pr(78) == []

    estado_1 = [CheckPullRequest(nome="validate", bucket="pending", state="IN_PROGRESS")]
    estado_2 = [CheckPullRequest(nome="validate", bucket="pass", state="SUCCESS")]
    fake.registrar_sequencia_checks(78, [estado_1, estado_2])

    assert fake.listar_checks_pr(78) == estado_1
    assert fake.listar_checks_pr(78) == estado_2
    assert fake.listar_checks_pr(78) == estado_2


def test_id_bot_estados_merge_e_execucao_merge() -> None:
    """Garante que o Fake retorna IDs de bot, evolução de mergeabilidade e resultados de merge."""
    fake = ClienteGhIntegradorFake()
    assert fake.obter_id_usuario_bot("aresta-bot[bot]") == ""
    fake.registrar_id_bot("aresta-bot[bot]", "998877")
    assert fake.obter_id_usuario_bot("aresta-bot[bot]") == "998877"

    assert fake.obter_estado_merge_pr(78) == EstadoMergePullRequest(
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
    )
    fake.registrar_sequencia_estados_merge(
        78,
        [
            EstadoMergePullRequest(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            EstadoMergePullRequest(mergeable="MERGEABLE", merge_state_status="CLEAN"),
        ],
    )
    assert fake.obter_estado_merge_pr(78).mergeable == "CONFLICTING"
    assert fake.obter_estado_merge_pr(78).mergeable == "MERGEABLE"
    assert fake.obter_estado_merge_pr(78).mergeable == "MERGEABLE"

    assert fake.realizar_merge_pr(78) is True
    fake.registrar_sequencia_resultados_merge(78, [False, True])
    assert fake.realizar_merge_pr(78) is False
    assert fake.realizar_merge_pr(78) is True
    assert fake.realizar_merge_pr(78) is True
    assert fake.merges_solicitados == [78, 78, 78, 78]
