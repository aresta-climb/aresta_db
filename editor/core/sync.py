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
        Clona um repositório para o caminho especificado.
        """
        callbacks = self._obter_callbacks(progresso_callback)
        pygit2.clone_repository(url_repositorio, str(self.caminho_repo), callbacks=callbacks)

    def obter_url_clone(self, g: github.Github, repositorio_base: str = "aresta-climb/aresta_db") -> str:
        """
        Verifica se o usuário tem permissão de escrita. 
        Se não, cria um fork e retorna a URL do fork.
        """
        repo = g.get_repo(repositorio_base)
        usuario = g.get_user()
        
        try:
            # Tenta ver se o usuário tem permissão de escrita
            permissao = repo.get_collaborator_permission(usuario.login)
            if permissao in ["admin", "write"]:
                return repo.clone_url
        except Exception:
            # Se der erro ou não for colaborador, tenta achar fork
            pass
            
        # Procura por um fork existente
        for fork in repo.get_forks():
            if fork.owner.login == usuario.login:
                return fork.clone_url
                
        # Se não existir, cria um novo fork
        print(f"Criando fork de {repositorio_base} para {usuario.login}...")
        fork = usuario.create_fork(repo)
        return fork.clone_url

    def sincronizar(self, progresso_callback: Optional[Callable[[float], None]] = None):
        """
        Sincroniza o repositório existente (fetch + reset hard).
        """
        repo = pygit2.Repository(str(self.caminho_repo))
        remoto = repo.remotes["origin"]
        
        callbacks = self._obter_callbacks(progresso_callback)
        remoto.fetch(callbacks=callbacks)
        
        # Reset hard para a branch principal (origin/main)
        try:
            id_remoto_principal = repo.lookup_reference('refs/remotes/origin/main').target
            repo.reset(id_remoto_principal, pygit2.GIT_RESET_HARD)
        except KeyError:
            # Tentar master se main não existir
            id_remoto_principal = repo.lookup_reference('refs/remotes/origin/master').target
            repo.reset(id_remoto_principal, pygit2.GIT_RESET_HARD)

    def criar_pull_request(self, g: github.Github, branch_origem: str, titulo: str, corpo: str, repositorio_base: str = "aresta-climb/aresta_db") -> github.PullRequest.PullRequest:
        """
        Cria um Pull Request do fork do usuário para o repositório base.
        """
        repo_base = g.get_repo(repositorio_base)
        usuario = g.get_user()
        
        # O branch de origem deve estar no formato "usuario:branch"
        head = f"{usuario.login}:{branch_origem}"
        base = "main"
        
        return repo_base.create_pull(title=titulo, body=corpo, head=head, base=base)
