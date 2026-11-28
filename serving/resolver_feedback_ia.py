# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Ponto de entrada de linha de comando (CLI) para execução do agente de resolução
automatizada de feedbacks de croqui em Issues e Pull Requests via Editor Headless.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from serving.agente_feedback.cliente_gemini_feedback import (
    ClienteGeminiFeedback,
    InterfaceClienteGeminiFeedback,
)
from serving.agente_feedback.cliente_github_feedback import (
    ClienteGithubFeedback,
    InterfaceClienteGithubFeedback,
)
from serving.agente_feedback.orquestrador_resolucao_feedback import OrquestradorResolucaoFeedback

STATUS_FALHA_CLI: frozenset[str] = frozenset({"falha_validacao", "croqui_nao_identificado"})


def construir_url_execucao_actions(ambiente: Mapping[str, str]) -> str:
    """Constrói a URL direta para os logs da execução no GitHub Actions quando disponível."""
    run_id = ambiente.get("GITHUB_RUN_ID", "").strip()
    repositorio = ambiente.get("GITHUB_REPOSITORY", "").strip()
    servidor = ambiente.get("GITHUB_SERVER_URL", "https://github.com").strip().rstrip("/")
    if run_id and repositorio:
        return f"{servidor}/{repositorio}/actions/runs/{run_id}"
    return ""


def executar_commit_e_push_git(
    branch_alvo: str,
    mensagem_commit: str,
    pasta_croqui: Path,
    diretorio_repo: Path = _RAIZ_REPOSITORIO,
) -> None:
    """
    Cria/atualiza a branch `branch_alvo`, adiciona exclusivamente as adições, edições
    e deleções dentro de `pasta_croqui` (`git add -A -- <pasta_croqui>`), realiza commit
    assinado com DCO (`-s`) e faz push para `origin`.
    """
    subprocess.run(
        ["git", "checkout", "-B", branch_alvo],
        cwd=diretorio_repo,
        check=True,
    )
    subprocess.run(
        ["git", "add", "-A", "--", str(pasta_croqui)],
        cwd=diretorio_repo,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-s", "-m", mensagem_commit],
        cwd=diretorio_repo,
        check=True,
    )
    subprocess.run(
        ["git", "push", "--force-with-lease", "origin", f"HEAD:refs/heads/{branch_alvo}"],
        cwd=diretorio_repo,
        check=True,
    )


def executar_cli(
    argv: list[str] | None = None,
    *,
    cliente_gemini: InterfaceClienteGeminiFeedback | None = None,
    cliente_github: InterfaceClienteGithubFeedback | None = None,
    executor_git: Callable[[str, str, Path], None] | None = None,
    ambiente: Mapping[str, str] | None = None,
) -> int:
    """Analisa argumentos CLI, executa o `OrquestradorResolucaoFeedback` e retorna código de saída POSIX."""
    env = os.environ if ambiente is None else ambiente

    parser = argparse.ArgumentParser(
        description="Agente de IA para resolução de feedbacks de croqui (Editor Headless + Gemini Flash)."
    )
    parser.add_argument(
        "--numero-alvo",
        type=int,
        required=True,
        help="Número da Issue ou Pull Request no GitHub.",
    )
    parser.add_argument(
        "--comentario",
        type=str,
        default=None,
        help="Corpo do comentário quando disparado por issue_comment (/ai-fix).",
    )
    parser.add_argument(
        "--associacao-autor",
        type=str,
        default="",
        help="author_association do autor do comentário (ex: OWNER, MEMBER, COLLABORATOR).",
    )
    parser.add_argument(
        "--diretorio-database",
        type=str,
        default=str(_RAIZ_REPOSITORIO / "database"),
        help="Caminho para o diretório database/ do repositório.",
    )
    parser.add_argument(
        "--repositorio",
        type=str,
        default=env.get("GITHUB_REPOSITORY", "aresta-climb/aresta_db"),
        help="Repositório GitHub no formato dono/nome.",
    )
    parser.add_argument(
        "--url-execucao",
        type=str,
        default=construir_url_execucao_actions(env),
        help="URL da execução do workflow no GitHub Actions para inclusão nos comentários.",
    )

    args = parser.parse_args(argv)

    gemini_inst = cliente_gemini or ClienteGeminiFeedback(  # pragma: no cover
        api_key=env["GEMINI_API_KEY"],
    )
    github_inst = cliente_github or ClienteGithubFeedback(  # pragma: no cover
        token=env["GH_TOKEN"],
        repositorio=args.repositorio,
    )
    git_fn = executor_git or executar_commit_e_push_git

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=Path(args.diretorio_database),
        cliente_gemini=gemini_inst,
        cliente_github=github_inst,
        executor_git=git_fn,
        url_execucao=args.url_execucao,
    )

    resultado = orquestrador.processar_evento(
        numero_issue_ou_pr=args.numero_alvo,
        corpo_comentario=args.comentario,
        associacao_autor=args.associacao_autor,
    )
    codigo_saida = 1 if resultado.status in STATUS_FALHA_CLI else 0
    print(
        f"[AI-Feedback-Solver] Status final: {resultado.status} ({resultado.detalhe}) | exit_code={codigo_saida}",
        flush=True,
    )
    return codigo_saida


if __name__ == "__main__":  # pragma: no cover
    sys.exit(executar_cli())
