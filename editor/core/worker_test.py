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
        
        # Configurando o PR retornado pelo mock
        mock_pr = MagicMock()
        mock_pr.html_url = "https://github.com/fake/pr/1"
        mock_sync_class.return_value.criar_pull_request.return_value = mock_pr

        # Mocking callbacks signal
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        mock_g = mock_github_class.return_value
        mock_sync_class.return_value.configurar_remotes.assert_called_once_with(mock_g)
        mock_sync_class.return_value.fazer_fetch.assert_called_once()
        mock_repo.create_branch.assert_called_once()
        self.assertEqual(mock_repo.index.write_tree.call_count, 2)
        mock_repo.remotes["origin"].push.assert_called_once()
        
        mock_sync_class.return_value.criar_pull_request.assert_called_once()
        tarefa.sucesso.emit.assert_called_once()
        
        # Validando os argumentos emitidos pelo signal
        args_emit = tarefa.sucesso.emit.call_args[0]
        self.assertEqual(len(args_emit), 3)
        self.assertEqual(args_emit[0], "https://github.com/fake/pr/1")
        # Os outros 2 argumentos são dinâmicos (nome da branch e owner do pr)

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
        
        # Simulando que a arvore não mudou (tree hash idêntico)
        mock_repo.index.write_tree.return_value = "mesmo_hash_123"
        mock_head_commit = MagicMock()
        mock_head_commit.tree_id = "mesmo_hash_123"
        mock_repo.head.peel.return_value = mock_head_commit
        tarefa.aviso = MagicMock()
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        
        tarefa.run()
        
        # O commit não deve ser feito
        mock_repo.create_commit.assert_not_called()
        # O erro (ou aviso) deve ser emitido com a mensagem apropriada
        tarefa.aviso.emit.assert_called_once()
        self.assertIn("Nenhuma alteração", tarefa.aviso.emit.call_args[0][0])

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_sincronizacao_arquivos_preserva_arquivos_iguais(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se a sincronização de arquivos não sobrescreve arquivos que não mudaram."""
        import tempfile
        import os
        import time
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            src = tmp_path / "src"
            dst = tmp_path / "dst"
            src.mkdir()
            dst.mkdir()
            
            # Criar arquivos no src
            file1_src = src / "file1.txt"
            file2_src = src / "file2.txt"
            file1_src.write_text("conteudo 1")
            file2_src.write_text("conteudo 2_novo")
            
            # Criar arquivos no dst (simulando estado anterior)
            file1_dst = dst / "file1.txt"
            file2_dst = dst / "file2.txt"
            file3_dst = dst / "file3_removido.txt"
            
            file1_dst.write_text("conteudo 1") # Igual
            file2_dst.write_text("conteudo 2_velho") # Diferente
            file3_dst.write_text("conteudo 3") # Removido
            
            # Guardar mtime do file1_dst para ver se ele NÃO foi alterado
            mtime_antes = file1_dst.stat().st_mtime
            
            # Garantir diferença de tempo
            time.sleep(0.1)
            
            storage_mock = MagicMock()
            storage_mock.obter_caminho_base_repo.return_value = tmp_path
            
            # Ajuste: o worker copiará para tmp_path / "database" / "teste"
            # Então vamos fazer o dst ser isso
            dst_real = tmp_path / "database" / "teste"
            dst_real.parent.mkdir(parents=True)
            dst.rename(dst_real)
            
            file1_dst = dst_real / "file1.txt"
            
            tarefa = TarefaPublicacao(
                token="fake", storage=storage_mock, 
                caminho_database_croqui=src, 
                id_croqui="teste", dados_pr={"titulo": "T", "descricao": "D"},
                modo_atualizacao=False
            )
            
            mock_repo = MagicMock()
            mock_pygit2.Repository.return_value = mock_repo
            mock_repo.status.return_value = {"file2.txt": 256}
            
            tarefa.sucesso = MagicMock()
            tarefa.erro = MagicMock()
            tarefa.progresso = MagicMock()
            tarefa.status = MagicMock()
            
            tarefa.run()
            
            # Asserts de sincronização
            self.assertTrue(file1_dst.exists())
            self.assertTrue((dst_real / "file2.txt").exists())
            self.assertFalse((dst_real / "file3_removido.txt").exists())
            
            self.assertEqual((dst_real / "file2.txt").read_text(), "conteudo 2_novo")
            
            # O mais importante: file1.txt não deve ter tido mtime modificado
            mtime_depois = file1_dst.stat().st_mtime
            self.assertEqual(mtime_antes, mtime_depois, "O arquivo não modificado foi reescrito!")

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_usa_id_original_como_destino(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se o id_original é usado como nome da pasta destino, se existir."""
        import tempfile
        import yaml
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            src = tmp_path / "src"
            src.mkdir()
            (src / "file.txt").write_text("teste")
            
            # Criar o croqui_experimental.yaml na raiz do workspace (parent do src)
            yaml_meta = tmp_path / "croqui_experimental.yaml"
            yaml_meta.write_text(yaml.dump({"id_original": "pasta_original"}))
            
            storage_mock = MagicMock()
            repo_base = tmp_path / "repo"
            storage_mock.obter_caminho_base_repo.return_value = repo_base
            
            tarefa = TarefaPublicacao(
                token="fake", storage=storage_mock, 
                caminho_database_croqui=src, 
                id_croqui="teste_novo_id", dados_pr={"titulo": "T", "descricao": "D"},
                modo_atualizacao=False
            )
            
            mock_repo = MagicMock()
            mock_pygit2.Repository.return_value = mock_repo
            mock_repo.status.return_value = {"file.txt": 256}
            
            tarefa.sucesso = MagicMock()
            tarefa.erro = MagicMock()
            tarefa.progresso = MagicMock()
            tarefa.status = MagicMock()
            
            tarefa.run()
            
            # O arquivo deve ter ido parar na "pasta_original" e não em "teste_novo_id"
            destino_esperado = repo_base / "database" / "pasta_original" / "file.txt"
            destino_errado = repo_base / "database" / "teste_novo_id" / "file.txt"
            
            self.assertTrue(destino_esperado.exists(), "O arquivo deveria ter sido copiado para a pasta com id_original")
            self.assertFalse(destino_errado.exists(), "O arquivo não deve ser copiado para a pasta com o ID novo")

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_nao_cria_commit_se_nao_houver_mudancas(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se o worker emite um aviso quando o tree gerado for idêntico ao da branch local."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            src = tmp_path / "src"
            src.mkdir()
            (src / "file.txt").write_text("teste")
            
            storage_mock = MagicMock()
            repo_base = tmp_path / "repo"
            storage_mock.obter_caminho_base_repo.return_value = repo_base
            
            tarefa = TarefaPublicacao(
                token="fake", storage=storage_mock, 
                caminho_database_croqui=src, 
                id_croqui="teste", dados_pr={"titulo": "T", "descricao": "D"},
                modo_atualizacao=True, pr_branch="minha_branch"
            )
            
            mock_repo = MagicMock()
            mock_pygit2.Repository.return_value = mock_repo
            
            # Simulamos que write_tree() retorna um hash idêntico ao da HEAD atual
            mock_repo.index.write_tree.return_value = "mesmo_hash_123"
            
            mock_head_commit = MagicMock()
            mock_head_commit.tree_id = "mesmo_hash_123"
            mock_repo.head.peel.return_value = mock_head_commit
            
            tarefa.aviso = MagicMock()
            tarefa.sucesso = MagicMock()
            tarefa.erro = MagicMock()
            tarefa.progresso = MagicMock()
            tarefa.status = MagicMock()
            
            tarefa.run()
            
            # Deve emitir aviso informando que não houve mudanças
            tarefa.aviso.emit.assert_called_once_with("Nenhuma alteração foi detectada no croqui. O Pull Request já está atualizado!")
            
            # E não deve criar um novo commit nem tentar push
            mock_repo.create_commit.assert_not_called()
            mock_repo.remotes["origin"].push.assert_not_called()

if __name__ == "__main__":
    unittest.main()
