import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

import pygit2
from editor.core.worker import TarefaPublicacao, TarefaInicializacao

class TestWorker(unittest.TestCase):
    """Testes unitários para as tarefas de background do editor."""

    @patch("editor.core.worker.shutil")
    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_nova_pr(self, mock_sync_class, mock_pygit2, mock_github_class, mock_shutil):
        """Testa o fluxo de publicação de uma PR que não existia (nova PR)."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")

        dados_pr = {"titulo": "T", "descricao": "D"}
        
        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr=dados_pr,
            modo_atualizacao=False
        )
        
        # Mocks PyGit2
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        # Simulando git status com arquivo modificado
        mock_repo.status.return_value = {"arquivo.txt": pygit2.GIT_STATUS_WT_MODIFIED} if hasattr(pygit2, 'GIT_STATUS_WT_MODIFIED') else {"arquivo.txt": 256}
        
        # Mocking callbacks signal
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        mock_sync_class.return_value.fazer_fetch.assert_called_once()
        mock_repo.create_branch.assert_called_once()
        mock_repo.index.write_tree.assert_called_once()
        mock_repo.remotes["origin"].push.assert_called_once()
        
        mock_sync_class.return_value.criar_pull_request.assert_called_once()
        tarefa.sucesso.emit.assert_called_once()

    @patch("editor.core.worker.shutil")
    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_abortar_se_nao_ha_mudancas(self, mock_sync_class, mock_pygit2, mock_github_class, mock_shutil):
        """Deve abortar e emitir erro se o git status estiver vazio (sem modificações)."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")
        
        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr=None,
            modo_atualizacao=True
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        # Simulando git status SEM arquivo modificado
        mock_repo.status.return_value = {}
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        
        tarefa.run()
        
        # O commit não deve ser feito
        mock_repo.create_commit.assert_not_called()
        # O erro deve ser emitido com a mensagem apropriada
        tarefa.erro.emit.assert_called_once()
        self.assertIn("Nenhuma mudança", tarefa.erro.emit.call_args[0][0])

if __name__ == "__main__":
    unittest.main()
