# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Ponto de entrada de linha de comando (CLI) para execução do agente de resolução
automatizada de feedbacks de croqui em Issues e Pull Requests.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from scripts.deploy_generated import deploy
from serving.agente_feedback.cliente_gemini_feedback import (
    ClienteGeminiFeedback,
    InterfaceClienteGeminiFeedback,
)
from serving.agente_feedback.cliente_github_feedback import (
    ClienteGithubFeedback,
    InterfaceClienteGithubFeedback,
)
from serving.agente_feedback.orquestrador_resolucao_feedback import OrquestradorResolucaoFeedback


def validar_pasta_croqui_local(pasta_croqui: Path) -> list[str]:
    """
    Compila `pasta_croqui` em um diretório temporário descartável utilizando a pipeline
    oficial (`deploy()`) para validar integridade de YAML, referências e enums Protobuf.
    """
    with tempfile.TemporaryDirectory() as dir_temp:
        try:
            deploy(
                output_dir=Path(dir_temp),
                target_paths=[pasta_croqui],
                database_dir=pasta_croqui.resolve().parent,
                force_thumbnails=False,
                gerar_arquivos_de_debug=False,
                is_producao=False,
                verbose=False,
                sair_ao_falhar=False,
            )
            return []
        except Exception as erro:
            return [f"Falha ao validar compilação do croqui '{pasta_croqui.name}': {erro!s}"]


def executar_commit_e_push_git(
    branch_alvo: str,
    mensagem_commit: str,
    arquivos_modificados: list[Path],
    diretorio_repo: Path = _RAIZ_REPOSITORIO,
) -> None:
    """
    Cria/atualiza a branch `branch_alvo`, adiciona exclusivamente `arquivos_modificados`,
    realiza commit assinado com DCO (`-s`) e faz push para `origin`.
    """
    subprocess.run(
        ["git", "checkout", "-B", branch_alvo],
        cwd=diretorio_repo,
        check=True,
    )
    caminhos_str = [str(p) for p in arquivos_modificados]
    subprocess.run(
        ["git", "add", "--", *caminhos_str],
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
    executor_git: Callable[[str, str, list[Path]], None] | None = None,
) -> int:
    """Analisa argumentos CLI e executa o `OrquestradorResolucaoFeedback`."""
    parser = argparse.ArgumentParser(
        description="Agente de IA para resolução de feedbacks de croqui (Gemini Flash)."
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
        default=os.environ.get("GITHUB_REPOSITORY", "aresta-climb/aresta_db"),
        help="Repositório GitHub no formato dono/nome.",
    )

    args = parser.parse_args(argv)

    gemini_inst = cliente_gemini or ClienteGeminiFeedback(  # pragma: no cover
        api_key=os.environ["GEMINI_API_KEY"],
    )
    github_inst = cliente_github or ClienteGithubFeedback(  # pragma: no cover
        token=os.environ["GH_TOKEN"],
        repositorio=args.repositorio,
    )
    git_fn = executor_git or executar_commit_e_push_git

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=Path(args.diretorio_database),
        cliente_gemini=gemini_inst,
        cliente_github=github_inst,
        executor_git=git_fn,
        validador_croqui=validar_pasta_croqui_local,
    )

    resultado = orquestrador.processar_evento(
        numero_issue_ou_pr=args.numero_alvo,
        corpo_comentario=args.comentario,
        associacao_autor=args.associacao_autor,
    )
    print(f"[AI-Feedback-Solver] Status final: {resultado.status} ({resultado.detalhe})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(executar_cli())
