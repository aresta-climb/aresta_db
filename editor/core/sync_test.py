# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pygit2

from editor.core.sync import ErroSincronizacaoGit, GerenciadorSincronizacao


class TestGerenciadorSincronizacao(unittest.TestCase):
    """Testes unitários para o GerenciadorSincronizacao (100% Coverage Target)."""

    def setUp(self):
        self.caminho_fake = Path("/fake/repo")
        self.gerenciador = GerenciadorSincronizacao(self.caminho_fake, "fake-token")

    def test_obter_url_clone_padrao(self):
        """Deve retornar a URL oficial do repositório base público."""
        url = self.gerenciador.obter_url_clone()
        self.assertEqual(url, "https://github.com/aresta-climb/aresta_db.git")

    def test_obter_url_clone_personalizado(self):
        """Deve retornar a URL oficial com base no repositório informado."""
        url = self.gerenciador.obter_url_clone("outro-org/outro_repo")
        self.assertEqual(url, "https://github.com/outro-org/outro_repo.git")

    @patch("editor.core.sync.pygit2")
    def test_configurar_remotes_cria_quando_inexistentes(self, mock_pygit2):
        """Deve criar remote upstream e origin se não existirem."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_remotes_collection = MagicMock()
        mock_remotes_collection.__iter__.return_value = iter([])
        mock_repo.remotes = mock_remotes_collection

        self.gerenciador.configurar_remotes()

        mock_remotes_collection.create.assert_any_call(
            "upstream", "https://github.com/aresta-climb/aresta_db.git"
        )
        mock_remotes_collection.create.assert_any_call(
            "origin", "https://github.com/aresta-climb/aresta_db.git"
        )

    @patch("editor.core.sync.pygit2")
    def test_configurar_remotes_atualiza_quando_existentes(self, mock_pygit2):
        """Deve atualizar URLs de remotes upstream e origin se já existirem."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_upstream = MagicMock(name="upstream")
        mock_upstream.configure_mock(name="upstream")
        mock_origin = MagicMock(name="origin")
        mock_origin.configure_mock(name="origin")

        mock_remotes_collection = MagicMock()
        mock_remotes_collection.__iter__.return_value = iter([mock_upstream, mock_origin])
        mock_repo.remotes = mock_remotes_collection

        self.gerenciador.configurar_remotes()

        mock_remotes_collection.set_url.assert_any_call(
            "upstream", "https://github.com/aresta-climb/aresta_db.git"
        )
        mock_remotes_collection.set_url.assert_any_call(
            "origin", "https://github.com/aresta-climb/aresta_db.git"
        )

    @patch("editor.core.sync.pygit2")
    def test_configurar_remotes_remove_remote_proxy_se_existir(self, mock_pygit2):
        """Deve deletar remote efêmero proxy se existir."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_upstream = MagicMock()
        mock_upstream.configure_mock(name="upstream")
        mock_origin = MagicMock()
        mock_origin.configure_mock(name="origin")
        mock_proxy = MagicMock()
        mock_proxy.configure_mock(name="proxy")

        mock_remotes_collection = MagicMock()
        mock_remotes_collection.__iter__.return_value = iter(
            [mock_upstream, mock_origin, mock_proxy]
        )
        mock_repo.remotes = mock_remotes_collection

        self.gerenciador.configurar_remotes()

        mock_remotes_collection.delete.assert_called_once_with("proxy")

    @patch("editor.core.sync.pygit2")
    def test_configurar_remotes_ignora_erro_ao_deletar_proxy(self, mock_pygit2):
        """Deve capturar silenciosamente qualquer erro ao tentar deletar remote efêmero proxy."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_proxy = MagicMock()
        mock_proxy.configure_mock(name="proxy")
        mock_remotes_collection = MagicMock()
        mock_remotes_collection.__iter__.return_value = iter([mock_proxy])
        mock_remotes_collection.delete.side_effect = RuntimeError("Erro ao deletar")
        mock_repo.remotes = mock_remotes_collection

        # Não deve levantar exceção
        self.gerenciador.configurar_remotes()
        mock_remotes_collection.delete.assert_called_once_with("proxy")

    @patch("editor.core.sync.pygit2")
    def test_fazer_fetch_apenas_origin_e_upstream(self, mock_pygit2):
        """Deve fazer fetch apenas dos remotes oficiais (origin e upstream), ignorando proxy."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_origin = MagicMock()
        mock_origin.configure_mock(name="origin", url="https://github.com/usuario/aresta_db.git")
        mock_upstream = MagicMock()
        mock_upstream.configure_mock(
            name="upstream", url="https://github.com/aresta-climb/aresta_db.git"
        )
        mock_proxy = MagicMock()
        mock_proxy.configure_mock(name="proxy", url="https://proxy.arestaclimb.com.br")

        mock_repo.remotes = [mock_origin, mock_upstream, mock_proxy]

        self.gerenciador.fazer_fetch()

        mock_origin.fetch.assert_called_once()
        mock_upstream.fetch.assert_called_once()
        mock_proxy.fetch.assert_not_called()

    @patch("editor.core.sync.pygit2")
    def test_fazer_fetch_deduplica_remotes_com_mesma_url(self, mock_pygit2):
        """Não deve fazer fetch repetido para remotes apontando para a mesma URL."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_origin = MagicMock()
        mock_origin.configure_mock(
            name="origin", url="https://github.com/aresta-climb/aresta_db.git"
        )
        mock_upstream = MagicMock()
        mock_upstream.configure_mock(
            name="upstream", url="https://github.com/aresta-climb/aresta_db.git"
        )

        mock_repo.remotes = [mock_origin, mock_upstream]

        self.gerenciador.fazer_fetch()

        chamadas_totais = mock_origin.fetch.call_count + mock_upstream.fetch.call_count
        self.assertEqual(chamadas_totais, 1)

    @patch("editor.core.sync.pygit2")
    def test_fazer_fetch_traduz_giterror_no_error(self, mock_pygit2):
        """Deve traduzir GitError com mensagem 'no error' para ErroSincronizacaoGit com mensagem amigável."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_pygit2.GitError = pygit2.GitError

        mock_origin = MagicMock()
        mock_origin.configure_mock(
            name="origin", url="https://github.com/aresta-climb/aresta_db.git"
        )
        mock_origin.fetch.side_effect = pygit2.GitError("no error")
        mock_repo.remotes = [mock_origin]

        with self.assertRaises(ErroSincronizacaoGit) as ctx:
            self.gerenciador.fazer_fetch()

        mensagem = str(ctx.exception).lower()
        self.assertTrue("tempo limite" in mensagem or "conexão" in mensagem or "ssl" in mensagem)

    @patch("editor.core.sync.pygit2")
    def test_fazer_fetch_traduz_outro_giterror(self, mock_pygit2):
        """Deve traduzir qualquer outro GitError para ErroSincronizacaoGit preservando o motivo."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_pygit2.GitError = pygit2.GitError

        mock_origin = MagicMock()
        mock_origin.configure_mock(
            name="origin", url="https://github.com/aresta-climb/aresta_db.git"
        )
        mock_origin.fetch.side_effect = pygit2.GitError("erro generico de rede")
        mock_repo.remotes = [mock_origin]

        with self.assertRaises(ErroSincronizacaoGit) as ctx:
            self.gerenciador.fazer_fetch()

        self.assertIn("erro generico de rede", str(ctx.exception))

    @patch("editor.core.sync.pygit2")
    def test_clonar_sucesso(self, mock_pygit2):
        """Verifica se o clone manual inicializa o repo, configura longpaths e faz checkout."""
        mock_repo = MagicMock()
        mock_repo.config = {}
        mock_pygit2.init_repository.return_value = mock_repo

        mock_remote = MagicMock()
        mock_repo.remotes.create.return_value = mock_remote

        mock_branch = MagicMock()
        mock_branch.branch_name = "origin/main"
        mock_branch.target = "fake_target"
        mock_repo.branches.remote.get.side_effect = lambda name: (
            mock_branch if name == "origin/main" else None
        )

        mock_local_branch = MagicMock()
        mock_repo.branches.local.create.return_value = mock_local_branch

        self.gerenciador.clonar("https://github.com/aresta-climb/aresta_db.git")

        mock_pygit2.init_repository.assert_called_once_with(str(self.caminho_fake), False)
        self.assertTrue(mock_repo.config.get("core.longpaths"))
        mock_repo.remotes.create.assert_called_once_with(
            "origin", "https://github.com/aresta-climb/aresta_db.git"
        )
        mock_remote.fetch.assert_called_once_with(callbacks=unittest.mock.ANY, depth=1)
        mock_repo.checkout.assert_called_once_with(mock_local_branch)

    @patch("editor.core.sync.pygit2")
    def test_clonar_falha_sem_branch(self, mock_pygit2):
        """Verifica se lança RuntimeError quando não acha origin/main ou origin/master."""
        mock_repo = MagicMock()
        mock_repo.config = {}
        mock_pygit2.init_repository.return_value = mock_repo
        mock_repo.branches.remote.get.return_value = None

        with self.assertRaisesRegex(
            RuntimeError, "Não foi possível encontrar a branch main ou master"
        ):
            self.gerenciador.clonar("https://github.com/url_invalida.git")

    @patch("editor.core.sync.pygit2")
    def test_clonar_traduz_giterror_no_error(self, mock_pygit2):
        """Verifica se clone traduz GitError 'no error' para ErroSincronizacaoGit."""
        mock_repo = MagicMock()
        mock_repo.config = {}
        mock_pygit2.init_repository.return_value = mock_repo
        mock_pygit2.GitError = pygit2.GitError

        mock_remote = MagicMock()
        mock_remote.fetch.side_effect = pygit2.GitError("no error")
        mock_repo.remotes.create.return_value = mock_remote

        with self.assertRaises(ErroSincronizacaoGit) as ctx:
            self.gerenciador.clonar("https://github.com/aresta-climb/aresta_db.git")

        self.assertTrue(
            "tempo limite" in str(ctx.exception).lower() or "conexão" in str(ctx.exception).lower()
        )

    @patch("editor.core.sync.pygit2")
    def test_fazer_checkout_main_upstream_cria_branch(self, mock_pygit2):
        """Testa criação da branch local main se ela não existir ao fazer checkout."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_remote_branch = MagicMock()
        mock_remote_branch.target = "target_commit"
        mock_repo.branches.remote.get.return_value = mock_remote_branch

        mock_local_branches = MagicMock()
        mock_local_branches.__contains__.return_value = False
        mock_local_branch = MagicMock()
        mock_local_branches.create.return_value = mock_local_branch
        mock_repo.branches.local = mock_local_branches

        self.gerenciador.fazer_checkout_main_upstream()

        mock_local_branches.create.assert_called_once()
        mock_repo.checkout.assert_called_once_with(
            mock_local_branch, strategy=mock_pygit2.GIT_CHECKOUT_FORCE
        )

    @patch("editor.core.sync.pygit2")
    def test_fazer_checkout_main_upstream_atualiza_branch(self, mock_pygit2):
        """Testa atualização do target da branch local main se ela já existir."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo

        mock_remote_branch = MagicMock()
        mock_remote_branch.target = "target_commit"
        mock_repo.branches.remote.get.return_value = mock_remote_branch

        mock_local_branch = MagicMock()
        mock_repo.branches.local = {"main": mock_local_branch}

        self.gerenciador.fazer_checkout_main_upstream()

        mock_local_branch.set_target.assert_called_once_with("target_commit")
        mock_repo.checkout.assert_called_once_with(
            mock_local_branch, strategy=mock_pygit2.GIT_CHECKOUT_FORCE
        )

    @patch("editor.core.sync.pygit2")
    def test_fazer_checkout_main_upstream_sem_remoto_nao_faz_nada(self, mock_pygit2):
        """Se não houver branch remota upstream/main ou origin/main, não executa checkout."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_repo.branches.remote.get.return_value = None

        self.gerenciador.fazer_checkout_main_upstream()
        mock_repo.checkout.assert_not_called()

    @patch("editor.core.sync.pygit2")
    def test_reset_hard(self, mock_pygit2):
        """Testa reset hard para a HEAD do repo."""
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_repo.head.target = "head_target"

        self.gerenciador.reset_hard()

        mock_repo.reset.assert_called_once_with("head_target", mock_pygit2.GIT_RESET_HARD)

    def test_callbacks_credentials_e_progress(self):
        """Testa credenciais e progresso da classe interna ChamadasGit."""
        progresso_valores = []
        callbacks = self.gerenciador._obter_callbacks(lambda p: progresso_valores.append(p))

        # Teste de credentials com token
        cred = callbacks.credentials("url", "user", 0)
        self.assertIsInstance(cred, pygit2.UserPass)

        # Teste de credentials sem token deve levantar pygit2.Passthrough
        gerenciador_sem_token = GerenciadorSincronizacao(self.caminho_fake, token=None)
        callbacks_sem_token = gerenciador_sem_token._obter_callbacks()
        with self.assertRaises(pygit2.Passthrough):
            callbacks_sem_token.credentials("url", "user", 0)

        # Teste de transfer_progress
        stats = MagicMock()
        stats.total_objects = 100
        stats.received_objects = 50
        callbacks.transfer_progress(stats)
        self.assertEqual(progresso_valores, [50.0])

        # Teste transfer_progress com total_objects == 0
        stats.total_objects = 0
        callbacks.transfer_progress(stats)
        self.assertEqual(len(progresso_valores), 1)

    @patch("editor.core.sync.pygit2")
    def test_clonar_com_origin_master(self, mock_pygit2):
        """Verifica se o clone aceita origin/master quando origin/main não existir."""
        mock_repo = MagicMock()
        mock_repo.config = {}
        mock_pygit2.init_repository.return_value = mock_repo

        mock_remote = MagicMock()
        mock_repo.remotes.create.return_value = mock_remote

        mock_branch = MagicMock()
        mock_branch.branch_name = "origin/master"
        mock_branch.target = "fake_target"
        mock_repo.branches.remote.get.side_effect = lambda name: (
            mock_branch if name == "origin/master" else None
        )

        mock_local_branch = MagicMock()
        mock_repo.branches.local.create.return_value = mock_local_branch

        self.gerenciador.clonar("https://github.com/aresta-climb/aresta_db.git")
        mock_repo.checkout.assert_called_once_with(mock_local_branch)


if __name__ == "__main__":
    unittest.main()
