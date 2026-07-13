import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from editor.core.sync import GerenciadorSincronizacao

class TestGerenciadorSincronizacao(unittest.TestCase):
    """Testes unitários para o GerenciadorSincronizacao (100% Coverage Target)."""

    def setUp(self):
        self.caminho_fake = Path("/fake/repo")
        self.gerenciador = GerenciadorSincronizacao(self.caminho_fake, "fake-token")

    @patch("editor.core.sync.github.Github")
    def test_obter_url_clone_sempre_retorna_fork(self, mock_github_class):
        """Obrigatório: Deve sempre retornar a URL do fork, mesmo se tiver acesso ao base."""
        mock_g = mock_github_class.return_value
        mock_repo = MagicMock()
        mock_g.get_repo.return_value = mock_repo
        
        mock_user = MagicMock()
        mock_user.login = "usuario_teste"
        mock_g.get_user.return_value = mock_user
        
        # Simula que o usuário NÃO tem o fork ainda, então deve criar e retornar
        mock_user.get_repo.side_effect = Exception("Not Found")
        mock_fork = MagicMock()
        mock_fork.clone_url = "https://github.com/usuario_teste/aresta_db.git"
        mock_user.create_fork.return_value = mock_fork
        
        url = self.gerenciador.obter_url_clone(mock_g, "aresta-climb/aresta_db")
        
        # Assegura que criou o fork e retornou a URL correta
        mock_user.create_fork.assert_called_once_with(mock_repo)
        self.assertEqual(url, "https://github.com/usuario_teste/aresta_db.git")

    @patch("editor.core.sync.github.Github")
    def test_obter_url_clone_retorna_fork_existente(self, mock_github_class):
        """Se o fork já existe, retorna ele."""
        mock_g = mock_github_class.return_value
        mock_user = MagicMock()
        mock_user.login = "usuario_teste"
        mock_g.get_user.return_value = mock_user
        
        mock_fork = MagicMock()
        mock_fork.clone_url = "https://github.com/usuario_teste/aresta_db.git"
        mock_fork.fork = True
        mock_fork.parent.full_name = "aresta-climb/aresta_db"
        mock_user.get_repo.return_value = mock_fork
        
        url = self.gerenciador.obter_url_clone(mock_g, "aresta-climb/aresta_db")
        
        mock_user.create_fork.assert_not_called()
        self.assertEqual(url, "https://github.com/usuario_teste/aresta_db.git")

    def test_obter_url_clone_falha_403_amigavel(self):
        """Se create_fork retornar 403, deve fazer fallback para o repositório principal."""
        mock_g = MagicMock()
        mock_repo = MagicMock()
        mock_repo.clone_url = "https://github.com/aresta-climb/aresta_db.git"
        mock_g.get_repo.return_value = mock_repo
        
        mock_usuario = MagicMock()
        mock_g.get_user.return_value = mock_usuario
        
        # Simula que o repositório não existe no usuário
        import github
        mock_usuario.get_repo.side_effect = github.UnknownObjectException(404, "Not Found")
        
        # Simula erro 403 ao tentar criar fork
        mock_usuario.create_fork.side_effect = github.GithubException(403, "Resource not accessible by integration")
        
        url = self.gerenciador.obter_url_clone(mock_g)
        self.assertEqual(url, "https://github.com/aresta-climb/aresta_db.git")

    @patch("editor.core.sync.pygit2")
    def test_configurar_remotes(self, mock_pygit2):
        """Deve criar remote upstream se não existir."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        # Simula que tem o 'origin', mas não o 'upstream'
        mock_origin = MagicMock()
        mock_origin.configure_mock(name="origin")
        
        mock_remotes_collection = MagicMock()
        mock_remotes_collection.__iter__.return_value = iter([mock_origin])
        mock_repo.remotes = mock_remotes_collection
        
        mock_g = MagicMock()
        mock_fork = MagicMock()
        mock_fork.clone_url = "https://github.com/usuario_teste/aresta_db.git"
        with patch.object(self.gerenciador, "obter_url_clone", return_value=mock_fork.clone_url):
            self.gerenciador.configurar_remotes(mock_g)
        
        mock_remotes_collection.create.assert_called_once_with("upstream", "https://github.com/aresta-climb/aresta_db.git")
        mock_remotes_collection.set_url.assert_called_once_with("origin", mock_fork.clone_url)

    @patch("editor.core.sync.pygit2")
    def test_fazer_fetch_all(self, mock_pygit2):
        """Deve iterar sobre todos os remotes e fazer fetch."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        mock_origin = MagicMock()
        mock_origin.configure_mock(name="origin")
        mock_upstream = MagicMock()
        mock_upstream.configure_mock(name="upstream")
        
        mock_repo.remotes = [mock_origin, mock_upstream]
        
        # Testando _obter_callbacks indiretamente para cobertura
        self.gerenciador.fazer_fetch()
        
        mock_origin.fetch.assert_called_once()
        mock_upstream.fetch.assert_called_once()

    @patch("editor.core.sync.pygit2")
    def test_criar_pull_request_head_format(self, mock_pygit2):
        """O 'head' deve usar username:branch para fork, e apenas branch para repositório base."""
        mock_g = MagicMock()
        mock_repo_base = MagicMock()
        mock_g.get_repo.return_value = mock_repo_base
        
        mock_user = MagicMock()
        mock_user.login = "renatoutsch"
        mock_g.get_user.return_value = mock_user
        
        mock_repo_local = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo_local
        
        mock_origin = MagicMock()
        mock_repo_local.remotes = {"origin": mock_origin}
        
        # Teste 1: Fork
        mock_origin.url = "https://github.com/renatoutsch/aresta_db.git"
        self.gerenciador.criar_pull_request(mock_g, "minha_branch", "Titulo", "Corpo")
        mock_repo_base.create_pull.assert_called_with(title="Titulo", body="Corpo", head="renatoutsch:minha_branch", base="main")
        
        # Teste 2: Repositório Base (Fallback)
        mock_origin.url = "https://github.com/aresta-climb/aresta_db.git"
        self.gerenciador.criar_pull_request(mock_g, "minha_branch", "Titulo", "Corpo")
        mock_repo_base.create_pull.assert_called_with(title="Titulo", body="Corpo", head="minha_branch", base="main")

if __name__ == "__main__":
    unittest.main()
