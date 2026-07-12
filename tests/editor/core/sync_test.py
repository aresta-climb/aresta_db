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

    @patch("editor.core.sync.pygit2")
    def test_configurar_remotes(self, mock_pygit2):
        """Deve criar remote upstream se não existir."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        # Simula que tem o 'origin', mas não o 'upstream'
        mock_remotes = MagicMock()
        mock_remotes.__iter__.return_value = ["origin"]
        mock_repo.remotes = mock_remotes
        
        self.gerenciador.configurar_remotes()
        
        mock_repo.remotes.create.assert_called_once_with("upstream", "https://github.com/aresta-climb/aresta_db.git")

    @patch("editor.core.sync.pygit2")
    def test_fazer_fetch_all(self, mock_pygit2):
        """Deve iterar sobre todos os remotes e fazer fetch."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        mock_origin = MagicMock()
        mock_upstream = MagicMock()
        
        mock_repo.remotes = {"origin": mock_origin, "upstream": mock_upstream}
        
        # Testando _obter_callbacks indiretamente para cobertura
        self.gerenciador.fazer_fetch()
        
        mock_origin.fetch.assert_called_once()
        mock_upstream.fetch.assert_called_once()

if __name__ == "__main__":
    unittest.main()
