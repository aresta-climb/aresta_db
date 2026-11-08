# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pygit2


class ErroSincronizacaoGit(Exception):
    """Exceção levantada em caso de falha de conexão, transporte ou sincronização com Git."""

    pass


def _tratar_erro_git(e: pygit2.GitError) -> ErroSincronizacaoGit:
    """Traduz exceções pygit2.GitError, tratando especificamente a mensagem opaca 'no error'."""
    msg = str(e).strip()
    if msg.lower() == "no error" or "no error" in msg.lower():
        return ErroSincronizacaoGit(
            "Tempo limite esgotado ou falha de conexão segura (SSL) ao conectar com o GitHub."
        )
    return ErroSincronizacaoGit(f"Erro no Git ao sincronizar: {msg}")


class GerenciadorSincronizacao:
    """
    Gerencia operações Git (clone, fetch, reset) usando pygit2.
    """

    def __init__(
        self, caminho_repo: Path, token: str | None = None, url_upstream: str | None = None
    ) -> None:
        self.caminho_repo: Path = caminho_repo
        self.token: str | None = token
        self.url_upstream: str | None = url_upstream

    def _obter_callbacks(
        self, progresso_callback: Callable[[float], None] | None = None
    ) -> pygit2.RemoteCallbacks:
        """
        Cria os callbacks do pygit2 com suporte a autenticação e progresso.
        """

        class ChamadasGit(pygit2.RemoteCallbacks):
            def __init__(
                self, token: str | None, p_callback: Callable[[float], None] | None
            ) -> None:
                super().__init__()
                self.token: str | None = token
                self.p_callback: Callable[[float], None] | None = p_callback

            def credentials(
                self, url: str, username_from_url: str | None, allowed_types: int
            ) -> Any:
                # Para GitHub, usamos o token como usuário (ou x-access-token)
                if self.token:
                    return pygit2.UserPass(self.token, "x-oauth-basic")
                raise pygit2.Passthrough()

            def transfer_progress(self, stats: Any) -> None:
                if self.p_callback:
                    if getattr(stats, "total_objects", 0) > 0:
                        percentual = (stats.received_objects / stats.total_objects) * 100
                        self.p_callback(percentual)

        return ChamadasGit(self.token, progresso_callback)

    def clonar(
        self, url_repositorio: str, progresso_callback: Callable[[float], None] | None = None
    ) -> None:
        """
        Clona um repositório para o caminho especificado garantindo suporte a caminhos longos (core.longpaths).
        """
        callbacks = self._obter_callbacks(progresso_callback)

        # 1. Inicializa o repositório
        repo = pygit2.init_repository(str(self.caminho_repo), False)

        # 2. Configura suporte a MAX_PATH no Windows e preserva LF estrito
        repo.config["core.longpaths"] = True
        repo.config["core.autocrlf"] = False

        # 3. Configura remote e faz fetch (clone raso para URLs HTTP/HTTPS; completo para caminho local)
        remote = repo.remotes.create("origin", url_repositorio)
        try:
            if url_repositorio.startswith(("http://", "https://")):
                remote.fetch(callbacks=callbacks, depth=1)
            else:
                remote.fetch(callbacks=callbacks)
        except pygit2.GitError as e:
            raise _tratar_erro_git(e) from e

        # 4. Faz checkout da main
        branch_remota = repo.branches.remote.get("origin/main")
        if not branch_remota:
            branch_remota = repo.branches.remote.get("origin/master")

        if branch_remota:
            nome_local = branch_remota.branch_name.replace("origin/", "")
            branch_local = repo.branches.local.create(
                nome_local, cast(pygit2.Commit, repo[branch_remota.target])
            )
            repo.checkout(branch_local)
        else:
            raise RuntimeError(
                f"Não foi possível encontrar a branch main ou master no repositório {url_repositorio}"
            )

    def obter_url_clone(self, repositorio_base: str = "aresta-climb/aresta_db") -> str:
        """
        Retorna a URL oficial do repositório base público, respeitando override explícito ou ARESTA_GIT_UPSTREAM_URL.
        """
        if self.url_upstream:
            return self.url_upstream
        if repositorio_base == "aresta-climb/aresta_db":
            override_env = os.environ.get("ARESTA_GIT_UPSTREAM_URL", "").strip()
            if override_env:
                return override_env
        return f"https://github.com/{repositorio_base}.git"

    def configurar_remotes(self, url_upstream: str | None = None) -> None:
        """
        Garante que o repositório local possui exclusivamente o remote oficial 'origin',
        removendo remotes legados ('upstream') ou efêmeros ('proxy').
        """
        url_alvo = url_upstream or self.obter_url_clone()
        repo = pygit2.Repository(str(self.caminho_repo))
        remotes_names = [r.name for r in repo.remotes]

        if "origin" not in remotes_names:
            repo.remotes.create("origin", url_alvo)
        else:
            repo.remotes.set_url("origin", url_alvo)

        for nome_obsoleto in ("upstream", "proxy"):
            if nome_obsoleto in remotes_names:
                repo.remotes.delete(nome_obsoleto)

    def fazer_fetch(self, progresso_callback: Callable[[float], None] | None = None) -> None:
        """
        Faz fetch do remote oficial (origin).
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        callbacks = self._obter_callbacks(progresso_callback)
        remote = repo.remotes["origin"]

        try:
            remote.fetch(callbacks=callbacks)
        except pygit2.GitError as e:
            raise _tratar_erro_git(e) from e

    def fazer_checkout_main_upstream(self) -> None:
        """
        Faz checkout da branch main a partir de origin/main de forma limpa.
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        repo.config["core.autocrlf"] = False
        branch_remota = repo.branches.remote.get("origin/main")
        if not branch_remota:
            return

        # Atualiza ou cria a branch local 'main' apontando para a branch remota
        if "main" not in repo.branches.local:
            branch_local = repo.branches.local.create(
                "main", cast(pygit2.Commit, repo[branch_remota.target])
            )
        else:
            branch_local = repo.branches.local["main"]
            branch_local.set_target(branch_remota.target)

        # Faz o checkout forçado
        repo.checkout(branch_local, strategy=pygit2.GIT_CHECKOUT_FORCE)

    def reset_hard(self) -> None:
        """
        Reseta o workspace local para o commit atual da branch HEAD.
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        repo.reset(repo.head.target, cast(Any, pygit2.GIT_RESET_HARD))
