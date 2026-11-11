# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca e utilitário de linha de comando para integração automatizada de Pull Requests
aprovadas no repositório Aresta (`pr-integrator.yml`).

Responsabilidades:
- Obter metadados da Pull Request (`branch`, `base_branch`, `pr_number`).
- Validar todos os status checks ativos com fail-fast, ignorando o próprio check `integrate`
  para evitar auto-deadlock em eventos `pull_request_review` e bloqueios em re-execuções.
- Sincronizar previamente a branch da PR com `origin/<base_branch>`, resolvendo conflitos
  em artefatos compilados (`generated/`) e conflitos espúrios de quebra de linha final (EOF).
- Realizar commit assinado com DCO (`-s`), verificar aprovação do check `DCO` e efetuar merge
  com ressincronização automática caso outro PR avance a branch base concorrentemente.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))


class ErroClienteGhIntegrador(RuntimeError):
    """Exceção lançada quando a consulta de metadados obrigatórios via GitHub CLI falha."""


@dataclass(frozen=True)
class InfoPullRequest:
    """Metadados de branches e identificação de uma Pull Request."""

    numero: int
    branch_head: str
    branch_base: str


@dataclass(frozen=True)
class CheckPullRequest:
    """Representa um status check individual associado a uma Pull Request."""

    nome: str
    bucket: str
    state: str


@dataclass(frozen=True)
class EstadoMergePullRequest:
    """Estado de mergeabilidade calculado pelo GitHub para uma Pull Request."""

    mergeable: str
    merge_state_status: str


class InterfaceClienteGhIntegrador(Protocol):
    """Protocolo compartilhado entre `ClienteGhIntegrador` e `ClienteGhIntegradorFake`."""

    def obter_info_pr(self, numero_pr: int) -> InfoPullRequest: ...

    def listar_checks_pr(self, numero_pr: int) -> list[CheckPullRequest]: ...

    def obter_id_usuario_bot(self, nome_bot: str) -> str: ...

    def obter_estado_merge_pr(self, numero_pr: int) -> EstadoMergePullRequest: ...

    def realizar_merge_pr(self, numero_pr: int) -> bool: ...


def _executar_gh_padrao(cmd: list[str]) -> subprocess.CompletedProcess[str]:  # pragma: no cover
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


class ClienteGhIntegrador:
    """Implementação real que interage com o GitHub via GitHub CLI (`gh`)."""

    def __init__(
        self,
        repositorio: str,
        executor_comando: Callable[
            [list[str]], subprocess.CompletedProcess[str]
        ] = _executar_gh_padrao,
    ) -> None:
        self._repositorio = repositorio
        self._executor = executor_comando

    def obter_info_pr(self, numero_pr: int) -> InfoPullRequest:
        """Obtém `headRefName` e `baseRefName` da Pull Request."""
        res = self._executor(
            [
                "gh",
                "pr",
                "view",
                str(numero_pr),
                "--repo",
                self._repositorio,
                "--json",
                "headRefName,baseRefName",
            ]
        )
        if res.returncode != 0:
            raise ErroClienteGhIntegrador(
                f"Falha ao obter informações da PR #{numero_pr}: {res.stderr.strip()}"
            )
        dados = json.loads(res.stdout)
        return InfoPullRequest(
            numero=numero_pr,
            branch_head=str(dados["headRefName"]),
            branch_base=str(dados["baseRefName"]),
        )

    def listar_checks_pr(self, numero_pr: int) -> list[CheckPullRequest]:
        """Lista todos os checks ativos da Pull Request; retorna lista vazia em caso de erro transitório."""
        res = self._executor(
            [
                "gh",
                "pr",
                "checks",
                str(numero_pr),
                "--repo",
                self._repositorio,
                "--json",
                "name,bucket,state",
            ]
        )
        if res.returncode != 0 or not res.stdout.strip():
            return []
        itens = json.loads(res.stdout)
        return [
            CheckPullRequest(
                nome=str(item.get("name", "")),
                bucket=str(item.get("bucket", "")),
                state=str(item.get("state", "")),
            )
            for item in itens
            if isinstance(item, dict)
        ]

    def obter_id_usuario_bot(self, nome_bot: str) -> str:
        """Obtém o ID numérico do usuário bot no GitHub para compor o e-mail noreply."""
        res = self._executor(["gh", "api", f"/users/{nome_bot}", "--jq", ".id"])
        if res.returncode != 0:
            return ""
        return res.stdout.strip()

    def obter_estado_merge_pr(self, numero_pr: int) -> EstadoMergePullRequest:
        """Consulta `mergeable` e `mergeStateStatus` da Pull Request."""
        res = self._executor(
            [
                "gh",
                "pr",
                "view",
                str(numero_pr),
                "--repo",
                self._repositorio,
                "--json",
                "mergeable,mergeStateStatus",
            ]
        )
        if res.returncode != 0 or not res.stdout.strip():
            return EstadoMergePullRequest(mergeable="UNKNOWN", merge_state_status="UNKNOWN")
        dados = json.loads(res.stdout)
        return EstadoMergePullRequest(
            mergeable=str(dados.get("mergeable", "UNKNOWN")),
            merge_state_status=str(dados.get("mergeStateStatus", "UNKNOWN")),
        )

    def realizar_merge_pr(self, numero_pr: int) -> bool:
        """Executa `gh pr merge --merge --delete-branch` e retorna True em caso de sucesso."""
        res = self._executor(
            [
                "gh",
                "pr",
                "merge",
                str(numero_pr),
                "--repo",
                self._repositorio,
                "--merge",
                "--delete-branch",
            ]
        )
        return res.returncode == 0


def _registrar_github_output(caminho: Path | None, chave: str, valor: str) -> None:
    if caminho is not None:
        with open(caminho, "a", encoding="utf-8") as arq:
            arq.write(f"{chave}={valor}\n")


def obter_informacoes_pr(
    numero_pr: int,
    cliente_gh: InterfaceClienteGhIntegrador,
    *,
    caminho_github_output: Path | None = None,
) -> InfoPullRequest:
    """Obtém metadados da PR e exporta `branch`, `base_branch` e `pr_number` no GITHUB_OUTPUT."""
    info = cliente_gh.obter_info_pr(numero_pr)
    _registrar_github_output(caminho_github_output, "branch", info.branch_head)
    _registrar_github_output(caminho_github_output, "base_branch", info.branch_base)
    _registrar_github_output(caminho_github_output, "pr_number", str(info.numero))
    return info


def aguardar_e_validar_checks_pr(
    numero_pr: int,
    cliente_gh: InterfaceClienteGhIntegrador,
    *,
    max_tentativas: int = 72,
    intervalo_segundos: float = 10.0,
    funcao_espera: Callable[[float], None] = time.sleep,
    caminho_github_output: Path | None = None,
    nome_check_ignorado: str = "integrate",
) -> int:
    """
    Aguarda a conclusão de todas as checagens ativas do PR (exceto `nome_check_ignorado`),
    abortando imediatamente (fail-fast) em caso de falha ou cancelamento.
    """
    if numero_pr <= 0:
        _registrar_github_output(caminho_github_output, "codigo_saida", "2")
        return 2

    print(f"Aguardando e validando todas as checagens ativas do PR #{numero_pr}...")

    for tentativa in range(1, max_tentativas + 1):
        todos_checks = cliente_gh.listar_checks_pr(numero_pr)
        checks = [c for c in todos_checks if c.nome != nome_check_ignorado]

        if not checks:
            print(
                f"Tentativa {tentativa}/{max_tentativas}: Nenhuma checagem encontrada ainda. "
                f"Aguardando {int(intervalo_segundos)}s..."
            )
            funcao_espera(intervalo_segundos)
            continue

        falhas = [c for c in checks if c.bucket in ("fail", "cancel")]
        if falhas:
            print(f"❌ ERRO: Checagens com falha ou canceladas detectadas no PR #{numero_pr}:")
            for c in falhas:
                print(f"  - {c.nome} (bucket={c.bucket}, state={c.state})")
            print("Abortando execução do integrador (fail-fast).")
            _registrar_github_output(caminho_github_output, "codigo_saida", "1")
            return 1

        pendentes = [c for c in checks if c.bucket == "pending"]
        if not pendentes:
            print(f"✅ Todas as checagens ativas ({len(checks)}) foram concluídas com sucesso!")
            for c in checks:
                print(f" - {c.nome}: {c.bucket} ({c.state})")
            _registrar_github_output(caminho_github_output, "codigo_saida", "0")
            return 0

        print(
            f"Tentativa {tentativa}/{max_tentativas}: Aguardando checagens pendentes no PR #{numero_pr}:"
        )
        for c in pendentes:
            print(f"  - {c.nome} (pendente)")
        funcao_espera(intervalo_segundos)

    print(f"❌ ERRO: Tempo limite esgotado aguardando checagens do PR #{numero_pr}.")
    _registrar_github_output(caminho_github_output, "codigo_saida", "1")
    return 1


def configurar_identidade_git_bot(
    app_slug: str,
    cliente_gh: InterfaceClienteGhIntegrador,
    diretorio_repo: Path,
) -> tuple[str, str]:
    """Configura `user.name` e `user.email` no repositório Git local com a identidade DCO do bot."""
    nome_bot = f"{app_slug}[bot]"
    id_bot = cliente_gh.obter_id_usuario_bot(nome_bot)
    if id_bot:
        email_bot = f"{id_bot}+{nome_bot}@users.noreply.github.com"
    else:
        email_bot = f"{nome_bot}@users.noreply.github.com"

    subprocess.run(["git", "config", "user.name", nome_bot], cwd=diretorio_repo, check=True)
    subprocess.run(["git", "config", "user.email", email_bot], cwd=diretorio_repo, check=True)
    return nome_bot, email_bot


def sincronizar_branch_com_base(
    branch_base: str,
    diretorio_repo: Path,
) -> int:
    """
    Faz `git fetch origin <branch_base>` e mescla `origin/<branch_base>` na árvore atual,
    resolvendo conflitos em `generated/` (via base) e conflitos de quebra de linha final (EOF).
    """
    print(f"Sincronizando a branch do PR com origin/{branch_base}...")
    subprocess.run(
        ["git", "fetch", "origin", branch_base],
        cwd=diretorio_repo,
        check=True,
    )

    res_merge = subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", f"origin/{branch_base}"],
        cwd=diretorio_repo,
        check=False,
    )
    if res_merge.returncode == 0:
        return 0

    print(f"Verificando conflitos de merge com origin/{branch_base}...")
    conflitos = (
        subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=diretorio_repo,
            text=True,
        )
        .strip()
        .splitlines()
    )

    for arq in conflitos:
        if arq.startswith("generated/"):
            subprocess.run(
                ["git", "checkout", "--theirs", "--", arq],
                cwd=diretorio_repo,
                check=True,
            )
            subprocess.run(["git", "add", "--", arq], cwd=diretorio_repo, check=True)
            print(f"Conflito em artefato gerado resolvido via base: {arq}")
        else:
            caminhos_tmp: list[Path] = []
            for estagio, sufixo in [
                ("1", ".merge_base"),
                ("2", ".merge_ours"),
                ("3", ".merge_theirs"),
            ]:
                blob = subprocess.check_output(
                    ["git", "show", f":{estagio}:{arq}"],
                    cwd=diretorio_repo,
                )
                if not blob.endswith(b"\n"):
                    blob += b"\n"
                caminho_tmp = diretorio_repo / sufixo
                caminho_tmp.write_bytes(blob)
                caminhos_tmp.append(caminho_tmp)

            res_mf = subprocess.run(
                [
                    "git",
                    "merge-file",
                    "-p",
                    str(caminhos_tmp[1]),
                    str(caminhos_tmp[0]),
                    str(caminhos_tmp[2]),
                ],
                cwd=diretorio_repo,
                capture_output=True,
                check=False,
            )
            for caminho_tmp in caminhos_tmp:
                caminho_tmp.unlink(missing_ok=True)

            if res_mf.returncode == 0:
                (diretorio_repo / arq).write_bytes(res_mf.stdout)
                subprocess.run(["git", "add", "--", arq], cwd=diretorio_repo, check=True)
                print(
                    f"Conflito de quebra de linha final (EOF) resolvido automaticamente em: {arq}"
                )

    restantes = (
        subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=diretorio_repo,
            text=True,
        )
        .strip()
        .splitlines()
    )
    if restantes:
        print(f"❌ ERRO: Conflitos reais não resolvidos automaticamente: {restantes}")
        return 1

    return 0


def commitar_e_enviar_alteracoes(
    diretorio_repo: Path,
    mensagem_commit: str = "chore: compilação automática para deploy [skip ci]",
) -> bool:
    """Adiciona `generated/` e `database/`, realiza commit assinado (`-s`) e faz `git push`."""
    subprocess.run(
        ["git", "add", "generated/", "database/"],
        cwd=diretorio_repo,
        check=True,
    )
    res_commit = subprocess.run(
        ["git", "commit", "-s", "-m", mensagem_commit],
        cwd=diretorio_repo,
        check=False,
    )
    if res_commit.returncode != 0:
        print("Nenhuma alteração para commitar")
        return False

    subprocess.run(["git", "push"], cwd=diretorio_repo, check=True)
    return True


def aguardar_check_dco(
    numero_pr: int,
    cliente_gh: InterfaceClienteGhIntegrador,
    *,
    max_tentativas: int = 15,
    intervalo_segundos: float = 3.0,
    espera_inicial_segundos: float = 3.0,
    funcao_espera: Callable[[float], None] = time.sleep,
) -> int:
    """Aguarda e verifica se o status check `DCO` da Pull Request foi aprovado."""
    print(f"Verificando o status check do DCO para o PR #{numero_pr}...")
    funcao_espera(espera_inicial_segundos)

    for tentativa in range(1, max_tentativas + 1):
        checks = cliente_gh.listar_checks_pr(numero_pr)
        check_dco = next((c for c in checks if c.nome == "DCO"), None)
        status_str = f"{check_dco.bucket}|{check_dco.state}" if check_dco else ""
        print(f"Tentativa {tentativa} de {max_tentativas} - Status DCO: '{status_str}'")

        if check_dco is not None:
            if check_dco.bucket == "pass" or check_dco.state == "SUCCESS":
                print("✅ Check do DCO aprovado com sucesso!")
                return 0
            if check_dco.bucket in ("fail", "cancel") or check_dco.state in (
                "FAILURE",
                "ACTION_REQUIRED",
            ):
                print(
                    f"❌ ERRO: O status check do DCO falhou para o PR #{numero_pr}. Merge bloqueado."
                )
                return 1

        print("Aguardando o processamento do check DCO...")
        funcao_espera(intervalo_segundos)

    print(
        f"❌ ERRO: Tempo limite esgotado aguardando aprovação do check DCO para o PR #{numero_pr}."
    )
    return 1


def _executar_deploy_generated_padrao(  # pragma: no cover
    pastas_alteradas: list[str],
    diretorio_repo: Path,
) -> None:
    subprocess.run(
        [sys.executable, "scripts/deploy_generated.py", "--target", *pastas_alteradas],
        cwd=diretorio_repo,
        check=True,
    )


def realizar_merge_com_ressincronizacao(
    numero_pr: int,
    branch_base: str,
    cliente_gh: InterfaceClienteGhIntegrador,
    diretorio_repo: Path,
    *,
    pastas_alteradas: list[str] | None = None,
    compilador_deploy: Callable[[list[str], Path], None] = _executar_deploy_generated_padrao,
    max_tentativas: int = 10,
    intervalo_segundos: float = 4.0,
    espera_inicial_segundos: float = 3.0,
    funcao_espera: Callable[[float], None] = time.sleep,
) -> int:
    """
    Executa o merge da Pull Request com loop de tentativas e ressincronização automática
    caso `mergeable == 'CONFLICTING'` (por avanço concorrente de `origin/<branch_base>`).
    """
    print(f"Aguardando o GitHub processar o estado de merge do PR #{numero_pr} após o push...")
    funcao_espera(espera_inicial_segundos)

    for tentativa in range(1, max_tentativas + 1):
        estado = cliente_gh.obter_estado_merge_pr(numero_pr)
        print(
            f"Tentativa {tentativa} de {max_tentativas} - Estado do PR: "
            f"mergeable={estado.mergeable}, status={estado.merge_state_status}"
        )

        if estado.mergeable == "CONFLICTING":
            print(
                f"⚠️ Conflito detectado com origin/{branch_base} "
                "(outro PR pode ter sido integrado concorrentemente). Ressincronizando..."
            )
            if sincronizar_branch_com_base(branch_base, diretorio_repo) != 0:
                return 1
            if pastas_alteradas:
                compilador_deploy(pastas_alteradas, diretorio_repo)
            commitar_e_enviar_alteracoes(
                diretorio_repo,
                mensagem_commit="chore: ressincronizar e recompilar para deploy [skip ci]",
            )
            funcao_espera(intervalo_segundos)

        if cliente_gh.realizar_merge_pr(numero_pr):
            print("Merge realizado com sucesso!")
            return 0

        print("Aguardando o GitHub finalizar a análise de mergeabilidade...")
        funcao_espera(intervalo_segundos)

    print(
        "Falha ao realizar o merge após várias tentativas. "
        "Pode haver um conflito real ou bloqueio de branch protection."
    )
    return 1


def executar_cli(
    argv: list[str] | None = None,
    *,
    cliente_gh: InterfaceClienteGhIntegrador | None = None,
    diretorio_repo: Path | None = None,
    funcao_espera: Callable[[float], None] = time.sleep,
    compilador_deploy: Callable[[list[str], Path], None] = _executar_deploy_generated_padrao,
) -> int:
    """Ponto de entrada CLI do integrador de Pull Requests."""
    for stream in (sys.stdout, sys.stderr):
        getattr(stream, "reconfigure", lambda **_kw: None)(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Integrador automatizado de Pull Requests Aresta.")
    subparsers = parser.add_subparsers(dest="subcomando", required=True)

    p_info = subparsers.add_parser("obter-info")
    p_info.add_argument("--pr", type=int, required=True)
    p_info.add_argument("--repo", type=str, required=True)
    p_info.add_argument("--github-output", type=str, default=None)

    p_checks = subparsers.add_parser("validar-checks")
    p_checks.add_argument("--pr", type=int, default=0)
    p_checks.add_argument("--repo", type=str, required=True)
    p_checks.add_argument("--github-output", type=str, default=None)

    p_sync = subparsers.add_parser("sincronizar-base")
    p_sync.add_argument("--base-branch", type=str, required=True)
    p_sync.add_argument("--app-slug", type=str, required=True)
    p_sync.add_argument("--repo", type=str, required=True)

    p_commit = subparsers.add_parser("commitar-e-enviar")
    p_commit.add_argument("--app-slug", type=str, required=True)
    p_commit.add_argument("--repo", type=str, required=True)

    p_dco = subparsers.add_parser("verificar-dco")
    p_dco.add_argument("--pr", type=int, required=True)
    p_dco.add_argument("--repo", type=str, required=True)

    p_merge = subparsers.add_parser("realizar-merge")
    p_merge.add_argument("--pr", type=int, required=True)
    p_merge.add_argument("--repo", type=str, required=True)
    p_merge.add_argument("--base-branch", type=str, required=True)
    p_merge.add_argument("--pastas", nargs="*", default=[])

    args = parser.parse_args(argv)
    gh_inst = cliente_gh or ClienteGhIntegrador(repositorio=args.repo)  # pragma: no cover
    repo_dir = diretorio_repo or _RAIZ_REPOSITORIO

    if args.subcomando == "obter-info":
        caminho_out = Path(args.github_output) if args.github_output else None
        obter_informacoes_pr(args.pr, gh_inst, caminho_github_output=caminho_out)
        return 0

    if args.subcomando == "validar-checks":
        caminho_out = Path(args.github_output) if args.github_output else None
        return aguardar_e_validar_checks_pr(
            args.pr,
            gh_inst,
            funcao_espera=funcao_espera,
            caminho_github_output=caminho_out,
        )

    if args.subcomando == "sincronizar-base":
        configurar_identidade_git_bot(args.app_slug, gh_inst, repo_dir)
        return sincronizar_branch_com_base(args.base_branch, repo_dir)

    if args.subcomando == "commitar-e-enviar":
        configurar_identidade_git_bot(args.app_slug, gh_inst, repo_dir)
        commitar_e_enviar_alteracoes(repo_dir)
        return 0

    if args.subcomando == "verificar-dco":
        return aguardar_check_dco(args.pr, gh_inst, funcao_espera=funcao_espera)

    return realizar_merge_com_ressincronizacao(
        args.pr,
        args.base_branch,
        gh_inst,
        repo_dir,
        pastas_alteradas=[p for p in args.pastas if p],
        compilador_deploy=compilador_deploy,
        funcao_espera=funcao_espera,
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(executar_cli())
