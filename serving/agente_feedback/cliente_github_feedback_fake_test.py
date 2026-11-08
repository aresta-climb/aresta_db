# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes para a biblioteca test-only `ClienteGithubFeedbackFake`, validando
o cumprimento do contrato de consulta de Issues/PRs, criação de PRs,
comentários e download de anexos em memória.
"""

from __future__ import annotations

import pytest

from serving.agente_feedback.cliente_github_feedback import (
    DadosIssueOuPr,
    ErroComunicacaoGithub,
)
from serving.agente_feedback.cliente_github_feedback_fake import ClienteGithubFeedbackFake


def test_fake_gerencia_issues_prs_comentarios_e_anexos_em_memoria() -> None:
    fake = ClienteGithubFeedbackFake()
    fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=42,
            titulo="[Croqui | br_mg_araxa] Ajuste",
            corpo="Descrição do feedback",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    fake.registrar_arquivos_pr(99, ["database/br_mg_araxa/setor_a.md"])
    fake.registrar_anexo(
        "https://feedback.arestaclimb.com/anexos/1/screenshot.webp", b"img_bytes", "image/webp"
    )

    issue = fake.obter_issue_ou_pr(42)
    assert issue.numero == 42
    assert issue.eh_pull_request is False

    assert fake.obter_arquivos_modificados_pr(99) == ["database/br_mg_araxa/setor_a.md"]
    assert fake.buscar_pr_aberta_por_branch("ai-fix/issue-42") is None

    pr_criada = fake.criar_pull_request(
        branch_head="ai-fix/issue-42",
        titulo="fix: corrige grau",
        corpo="Closes #42",
    )
    assert pr_criada.numero == 100
    assert fake.buscar_pr_aberta_por_branch("ai-fix/issue-42") == pr_criada

    fake.publicar_comentario(42, "PR aberta com sucesso!")
    assert fake.comentarios_publicados == [(42, "PR aberta com sucesso!")]

    anexo = fake.baixar_imagem_anexo("https://feedback.arestaclimb.com/anexos/1/screenshot.webp")
    assert anexo == (b"img_bytes", "image/webp")
    assert fake.baixar_imagem_anexo("https://nao.existe/foto.webp") is None


def test_fake_simula_erros_deterministicos() -> None:
    fake = ClienteGithubFeedbackFake(erro_simulado="Falha de permissão 403")

    with pytest.raises(ErroComunicacaoGithub, match="403"):
        fake.obter_issue_ou_pr(1)

    with pytest.raises(ErroComunicacaoGithub, match="403"):
        fake.criar_pull_request("branch", "titulo", "corpo")
