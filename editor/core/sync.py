# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pygit2
from pathlib import Path
from typing import Optional, Callable

class GerenciadorSincronizacao:
    """
    Gerencia operações Git (clone, fetch, reset) usando pygit2.
    """
    
    def __init__(self, caminho_repo: Path, token: Optional[str] = None):
        self.caminho_repo = caminho_repo
        self.token = token

    def _obter_callbacks(self, progresso_callback: Optional[Callable[[float], None]] = None):
        """
        Cria os callbacks do pygit2 com suporte a autenticação e progresso.
        """
        class ChamadasGit(pygit2.RemoteCallbacks):
            def __init__(self, token, p_callback):
                super().__init__()
                self.token = token
                self.p_callback = p_callback

            def credentials(self, url, username_from_url, allowed_types):
                # Para GitHub, usamos o token como usuário (ou x-access-token)
                if self.token:
                    return pygit2.UserPass(self.token, "x-oauth-basic")
                return None

            def transfer_progress(self, stats):
                if self.p_callback:
                    if stats.total_objects > 0:
                        percentual = (stats.received_objects / stats.total_objects) * 100
                        self.p_callback(percentual)

        return ChamadasGit(self.token, progresso_callback)

    def clonar(self, url_repositorio: str, progresso_callback: Optional[Callable[[float], None]] = None):
        """
        Clona um repositório para o caminho especificado garantindo suporte a caminhos longos (core.longpaths).
        """
        callbacks = self._obter_callbacks(progresso_callback)
        
        # 1. Inicializa o repositório
        repo = pygit2.init_repository(str(self.caminho_repo), False)
        
        # 2. Configura suporte a MAX_PATH no Windows
        repo.config['core.longpaths'] = True
        
        # 3. Configura remote e faz fetch (clone raso para agilizar)
        remote = repo.remotes.create("origin", url_repositorio)
        remote.fetch(callbacks=callbacks, depth=1)
        
        # 4. Faz checkout da main
        branch_remota = repo.branches.remote.get("origin/main")
        if not branch_remota:
            branch_remota = repo.branches.remote.get("origin/master")
            
        if branch_remota:
            nome_local = branch_remota.branch_name.replace("origin/", "")
            branch_local = repo.branches.local.create(nome_local, repo[branch_remota.target])
            repo.checkout(branch_local)
        else:
            raise RuntimeError(f"Não foi possível encontrar a branch main ou master no repositório {url_repositorio}")

    def obter_url_clone(self, repositorio_base: str = "aresta-climb/aresta_db") -> str:
        """
        Retorna a URL oficial do repositório base público.
        """
        return f"https://github.com/{repositorio_base}.git"

    def configurar_remotes(self, url_upstream: str = "https://github.com/aresta-climb/aresta_db.git"):
        """
        Garante que o repositório local tem os remotes necessários:
        'origin' -> O repositório base oficial.
        'upstream' -> O repositório oficial (aresta_db).
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        remotes_names = [r.name for r in repo.remotes]
        
        if "upstream" not in remotes_names:
            repo.remotes.create("upstream", url_upstream)
        else:
            repo.remotes.set_url("upstream", url_upstream)
            
        if "origin" not in remotes_names:
            repo.remotes.create("origin", url_upstream)
        else:
            repo.remotes.set_url("origin", url_upstream)

        if "proxy" in remotes_names:
            try:
                repo.remotes.delete("proxy")
            except Exception:
                pass

    def fazer_fetch(self, progresso_callback: Optional[Callable[[float], None]] = None):
        """
        Faz fetch apenas dos remotes oficiais (origin e upstream).
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        callbacks = self._obter_callbacks(progresso_callback)
        
        remotes_para_fetch = [r for r in repo.remotes if getattr(r, "name", None) in ("origin", "upstream")]
        for remote in remotes_para_fetch:
            remote.fetch(callbacks=callbacks)

    def fazer_checkout_main_upstream(self):
        """
        Faz checkout da branch main do upstream ou origin de forma limpa.
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        branch_upstream = repo.branches.remote.get("upstream/main") or repo.branches.remote.get("origin/main")
        if not branch_upstream:
            return
        
        # Atualiza ou cria a branch local 'main' apontando para a branch remota
        if "main" not in repo.branches.local:
            branch_local = repo.branches.local.create("main", repo[branch_upstream.target])
        else:
            branch_local = repo.branches.local["main"]
            branch_local.set_target(branch_upstream.target)

        # Faz o checkout forçado
        repo.checkout(branch_local, strategy=pygit2.GIT_CHECKOUT_FORCE)
        
    def reset_hard(self):
        """
        Reseta o workspace local para o commit atual da branch HEAD.
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        repo.reset(repo.head.target, pygit2.GIT_RESET_HARD)
