# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pygit2
import github
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
        
        # 3. Configura remote e faz fetch
        remote = repo.remotes.create("origin", url_repositorio)
        remote.fetch(callbacks=callbacks)
        
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

    def obter_url_clone(self, g: github.Github, repositorio_base: str = "aresta-climb/aresta_db") -> str:
        """
        Garante a existência de um fork do repositório base para o usuário logado
        e retorna a URL do fork. OBRIGATÓRIO pelo novo design, mesmo se o usuário 
        tiver acesso de escrita no base.
        """
        repo = g.get_repo(repositorio_base)
        usuario = g.get_user()
        
        # Tenta pegar diretamente pelo nome
        try:
            nome_repo_base = repositorio_base.split("/")[-1]
            fork = usuario.get_repo(nome_repo_base)
            if fork.fork and fork.parent.full_name == repositorio_base:
                return fork.clone_url
        except Exception:
            pass
            
        # Procura por um fork existente
        for fork in repo.get_forks():
            if fork.owner.login == usuario.login:
                return fork.clone_url
                
        # Se não existir, cria um novo fork
        print(f"Criando fork de {repositorio_base} para {usuario.login}...")
        try:
            fork = usuario.create_fork(repo)
            return fork.clone_url
        except github.GithubException as e:
            if e.status == 403:
                print(f"[AVISO] O token não tem permissão para criar forks (erro 403). Usando o repositório base como fallback.")
                return repo.clone_url
            raise

    def configurar_remotes(self, g: github.Github, url_upstream: str = "https://github.com/aresta-climb/aresta_db.git"):
        """
        Garante que o repositório local tem os remotes necessários:
        'origin' -> O fork do usuário.
        'upstream' -> O repositório oficial (aresta_db).
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        remotes_names = [r.name for r in repo.remotes]
        
        if "upstream" not in remotes_names:
            repo.remotes.create("upstream", url_upstream)
        else:
            repo.remotes.set_url("upstream", url_upstream)
            
        url_fork = self.obter_url_clone(g)
        if "origin" not in remotes_names:
            repo.remotes.create("origin", url_fork)
        else:
            repo.remotes.set_url("origin", url_fork)

    def fazer_fetch(self, progresso_callback: Optional[Callable[[float], None]] = None):
        """
        Faz fetch de todos os remotes (origin e upstream).
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        callbacks = self._obter_callbacks(progresso_callback)
        
        for remote in repo.remotes:
            remote.fetch(callbacks=callbacks)

    def fazer_checkout_main_upstream(self):
        """
        Faz checkout da branch main do upstream de forma limpa,
        descartando as alterações locais na main se houver.
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        branch_upstream = repo.branches.remote["upstream/main"]
        
        # Atualiza ou cria a branch local 'main' apontando para 'upstream/main'
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

    def criar_pull_request(self, g: github.Github, branch_origem: str, titulo: str, corpo: str, repositorio_base: str = "aresta-climb/aresta_db") -> github.PullRequest.PullRequest:
        repo_base = g.get_repo(repositorio_base)
        user = g.get_user()
        
        # Verifica se o push foi feito para o fork ou direto para o base
        repo_local = pygit2.Repository(str(self.caminho_repo))
        url_origin = repo_local.remotes["origin"].url
        
        if repositorio_base in url_origin:
            # Fallback ativado: push foi direto no repositório principal
            head = branch_origem
        else:
            # Push foi no fork do usuário
            head = f"{user.login}:{branch_origem}"
            
        base = "main"
        
        return repo_base.create_pull(title=titulo, body=corpo, head=head, base=base)
