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

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_nova_pr_owner_sem_fork(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se o pr_owner é aresta-climb quando não houver fork."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")

        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr={"titulo": "T", "descricao": "D"},
            modo_atualizacao=False
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        # Simula repo da org aresta-climb
        mock_repo.remotes = {"origin": MagicMock(url="https://github.com/aresta-climb/aresta_db.git")}
        mock_repo.status.return_value = {"arquivo.txt": 256}
        
        mock_g = mock_github_class.return_value
        mock_g.get_user.return_value.login = "usuario_aleatorio"
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        args_emit = tarefa.sucesso.emit.call_args[0]
        self.assertEqual(args_emit[2], "aresta-climb")

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_nova_pr_owner_com_fork(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se o pr_owner é o user login quando houver fork."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")

        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr={"titulo": "T", "descricao": "D"},
            modo_atualizacao=False
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        
        # Simula repo de um fork
        mock_repo.remotes = {"origin": MagicMock(url="https://github.com/usuario_aleatorio/aresta_db.git")}
        mock_repo.status.return_value = {"arquivo.txt": 256}
        
        mock_g = mock_github_class.return_value
        mock_g.get_user.return_value.login = "usuario_aleatorio"
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        args_emit = tarefa.sucesso.emit.call_args[0]
        self.assertEqual(args_emit[2], "usuario_aleatorio")

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_nova_branch_timestamp_completo(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se a nova branch gerada tem formato YYYYMMDD_HHMMSS."""
        import re
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        
        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=Path("/fake/repo/database/teste"), 
            id_croqui="meucroqui", dados_pr={"titulo": "T", "descricao": "D"},
            modo_atualizacao=False
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_repo.remotes = {"origin": MagicMock(url="https://github.com/a/b.git")}
        mock_repo.status.return_value = {"arquivo.txt": 256}
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        args_emit = tarefa.sucesso.emit.call_args[0]
        nome_branch = args_emit[1]
        # edicao_meucroqui_YYYYMMDD_HHMMSS -> tamanho e regex
        self.assertTrue(re.match(r"^edicao_meucroqui_\d{8}_\d{6}$", nome_branch), f"Nome da branch inválido: {nome_branch}")

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
            mock_repo.branches.local = {"minha_branch": MagicMock()}
            
            mock_repo.index.conflicts = None
            mock_commit_base = MagicMock()
            mock_branch_remote = MagicMock()
            mock_branch_remote.peel.return_value = mock_commit_base
            mock_repo.branches.remote = {"upstream/main": mock_branch_remote, "origin/minha_branch": MagicMock()}
            
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
            tarefa.aviso.emit.assert_called_once_with("Nenhuma alteração foi detectada no croqui.\nO Pull Request já está atualizado!")
            
            # E não deve criar um novo commit nem tentar push
            mock_repo.create_commit.assert_not_called()
            mock_repo.remotes["origin"].push.assert_not_called()

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_modo_atualizacao_faz_merge_da_main_limpo(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se em modo de atualização a tarefa faz merge da main local sem conflitos e cria o commit."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")
        
        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr=None,
            modo_atualizacao=True, pr_branch="minha_branch"
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_repo.branches.local = {"minha_branch": MagicMock()}
        
        mock_repo.index.conflicts = None
        
        mock_commit_base = MagicMock()
        mock_commit_base.id = "commit_main_id"
        
        mock_branch_remote = MagicMock()
        mock_branch_remote.peel.return_value = mock_commit_base
        mock_repo.branches.remote = {"upstream/main": mock_branch_remote, "origin/minha_branch": MagicMock()}
        
        mock_repo.index.write_tree.return_value = "novo_hash_123"
        mock_head_commit = MagicMock()
        mock_head_commit.tree_id = "velho_hash_123"
        mock_head_commit.id = "head_commit_id"
        mock_repo.head.peel.return_value = mock_head_commit
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        mock_repo.merge.assert_called_once_with("commit_main_id")
        self.assertEqual(mock_repo.create_commit.call_count, 2)
        args = mock_repo.create_commit.call_args_list[0][0]
        self.assertEqual(args[5], ["head_commit_id", "commit_main_id"])
        mock_repo.state_cleanup.assert_called_once()

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_modo_atualizacao_aborta_com_conflitos(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se a tarefa aborta a atualização quando há conflitos com a main."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")
        
        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr=None,
            modo_atualizacao=True, pr_branch="minha_branch"
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_repo.branches.local = {"minha_branch": MagicMock()}
        
        # Simula conflito
        mock_repo.index.conflicts = ["conflito1"]
        
        mock_commit_base = MagicMock()
        mock_commit_base.id = "commit_main_id"
        mock_branch_remote = MagicMock()
        mock_branch_remote.peel.return_value = mock_commit_base
        mock_repo.branches.remote = {"upstream/main": mock_branch_remote, "origin/minha_branch": MagicMock()}
        
        mock_head_target = MagicMock()
        mock_repo.head.target = mock_head_target
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        mock_repo.merge.assert_called_once_with("commit_main_id")
        mock_repo.reset.assert_called_once_with(mock_head_target, mock_pygit2.GIT_RESET_HARD)
        mock_repo.state_cleanup.assert_called_once()
        
        tarefa.erro.emit.assert_called_once()
        self.assertIn("conflitos com a branch main", tarefa.erro.emit.call_args[0][0])

    @patch("editor.core.worker.github.Github")
    @patch("editor.core.worker.pygit2")
    @patch("editor.core.worker.GerenciadorSincronizacao")
    def test_tarefa_publicacao_modo_atualizacao_faz_merge_mas_sem_alteracoes_no_croqui(self, mock_sync_class, mock_pygit2, mock_github_class):
        """Testa se o worker faz o push do merge da main mesmo que o croqui em si não tenha alterações."""
        storage_mock = MagicMock()
        storage_mock.obter_caminho_base_repo.return_value = Path("/fake/repo")
        caminho_database = Path("/fake/repo/database/teste")
        
        tarefa = TarefaPublicacao(
            token="fake", storage=storage_mock, 
            caminho_database_croqui=caminho_database, 
            id_croqui="teste", dados_pr=None,
            modo_atualizacao=True, pr_branch="minha_branch"
        )
        
        mock_repo = MagicMock()
        mock_pygit2.Repository.return_value = mock_repo
        mock_repo.branches.local = {"minha_branch": MagicMock()}
        
        mock_repo.index.conflicts = None
        
        mock_commit_base = MagicMock()
        mock_commit_base.id = "commit_main_id"
        mock_branch_remote = MagicMock()
        mock_branch_remote.peel.return_value = mock_commit_base
        mock_repo.branches.remote = {"upstream/main": mock_branch_remote, "origin/minha_branch": MagicMock()}
        
        # Simular que a tree NÃO mudou na checagem final (passo 4), 
        # mas que o merge criou um commit (tree inicial difere da origin).
        # Para simplificar o mock e não precisar lidar com chamadas múltiplas 
        # retornando coisas diferentes no mock_repo.index.write_tree, 
        # vamos usar o call_count ou side_effect.
        def write_tree_side_effect():
            # A primeira chamada é logo após o merge. Vamos simular que o merge gerou um novo hash
            # A segunda chamada é depois de add_all do croqui. Simulamos que hash NÃO muda.
            write_tree_side_effect.calls += 1
            if write_tree_side_effect.calls == 1:
                return "hash_do_merge_123"
            return "hash_do_merge_123"
        write_tree_side_effect.calls = 0
        mock_repo.index.write_tree.side_effect = write_tree_side_effect
        
        mock_head_commit = MagicMock()
        mock_head_commit.tree_id = "velho_hash_123" # Diferente do hash_do_merge_123, então cria commit de merge
        mock_head_commit.id = "head_commit_id"
        
        # E a segunda chamada de repo.head.peel() será a checagem do passo 4. 
        # O head peel precisa retornar o mesmo tree_id que o write_tree() retornou agora.
        def head_peel_side_effect():
            head_peel_side_effect.calls += 1
            m = MagicMock()
            if head_peel_side_effect.calls == 1:
                m.tree_id = "velho_hash_123"
                m.id = "head_commit_id"
            else:
                m.tree_id = "hash_do_merge_123" # head_commit foi atualizado pelo merge
                m.id = "novo_merge_commit_id"
            return m
        head_peel_side_effect.calls = 0
        mock_repo.head.peel.side_effect = head_peel_side_effect
        
        tarefa.sucesso = MagicMock()
        tarefa.erro = MagicMock()
        tarefa.aviso = MagicMock()
        tarefa.progresso = MagicMock()
        tarefa.status = MagicMock()
        
        tarefa.run()
        
        mock_repo.merge.assert_called_once_with("commit_main_id")
        # Deve ter chamado create_commit APENAS UMA VEZ (para o merge), e não duas (para o croqui)
        self.assertEqual(mock_repo.create_commit.call_count, 1)
        # E deve ter tentado fazer o push, ao invés de abortar no aviso
        mock_repo.remotes["origin"].push.assert_called_once()
        tarefa.sucesso.emit.assert_called_once()
        tarefa.aviso.emit.assert_not_called()

if __name__ == "__main__":
    unittest.main()
