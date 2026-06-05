import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from editor.core.sync import GerenciadorSincronizacao

class TestSincronizacao(unittest.TestCase):
    def setUp(self):
        self.sincronizador = GerenciadorSincronizacao(caminho_repo=Path("/fake/repo"))

    @patch("pygit2.clone_repository")
    def test_clonar_repositorio(self, mock_clone):
        self.sincronizador.clonar("https://github.com/aresta-climb/aresta_db.git")
        mock_clone.assert_called_once()
        args, kwargs = mock_clone.call_args
        self.assertEqual(args[0], "https://github.com/aresta-climb/aresta_db.git")
        self.assertEqual(Path(args[1]), self.sincronizador.caminho_repo)

    @patch("pygit2.Repository")
    def test_sincronizar_faz_fetch_e_reset(self, mock_repo_class):
        mock_repo = mock_repo_class.return_value
        mock_remote = mock_repo.remotes["origin"]
        
        self.sincronizador.sincronizar()
        
        mock_remote.fetch.assert_called_once()
        # Verificaria o reset aqui se implementado

    def test_criar_pull_request(self):
        mock_github = MagicMock()
        mock_repo = mock_github.get_repo.return_value
        mock_user = mock_github.get_user.return_value
        mock_user.login = "usuario_teste"
        
        self.sincronizador.criar_pull_request(
            mock_github, 
            branch_origem="nova_branch", 
            titulo="PR Teste", 
            corpo="Corpo da PR"
        )
        
        mock_repo.create_pull.assert_called_once_with(
            title="PR Teste",
            body="Corpo da PR",
            head="usuario_teste:nova_branch",
            base="main"
        )

if __name__ == "__main__":
    unittest.main()
