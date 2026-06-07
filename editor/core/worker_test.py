import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from editor.core.worker import TarefaPublicacao

@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.obter_caminho_base_repo.return_value = Path("/fake/base_repo")
    return storage

def test_tarefa_publicacao_inicializacao():
    token = "fake_token"
    storage = MagicMock()
    caminho_database = Path("/fake/croqui/database")
    id_croqui = "meu_croqui"
    dados_pr = {"titulo": "PR", "descricao": "Desc"}
    
    tarefa = TarefaPublicacao(token, storage, caminho_database, id_croqui, dados_pr)
    
    assert tarefa.token == token
    assert tarefa.storage == storage
    assert tarefa.caminho_database_croqui == caminho_database
    assert tarefa.id_croqui == id_croqui
    assert tarefa.dados_pr == dados_pr

@patch("editor.core.worker.pygit2.Repository")
@patch("editor.core.worker.github.Github")
@patch("editor.core.worker.shutil.copytree")
@patch("editor.core.worker.shutil.rmtree")
@patch("editor.core.worker.GerenciadorSincronizacao")
def test_tarefa_publicacao_fluxo_sucesso(mock_sync_class, mock_rmtree, mock_copytree, mock_github, mock_repo_class, mock_storage):
    # Setup Mocks
    mock_sync = mock_sync_class.return_value
    mock_g = mock_github.return_value
    mock_repo = mock_repo_class.return_value
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/pr/1"
    mock_sync.criar_pull_request.return_value = mock_pr
    
    # Mock user details for commit signature
    mock_user = mock_g.get_user.return_value
    mock_user.name = "Teste"
    mock_user.email = "teste@aresta.local"
    
    tarefa = TarefaPublicacao(
        token="token", 
        storage=mock_storage, 
        caminho_database_croqui=Path("/fake/database"),
        id_croqui="test_id",
        dados_pr={"titulo": "T", "descricao": "D"}
    )
    
    # Spy signals
    success_url = []
    tarefa.sucesso.connect(lambda url: success_url.append(url))
    
    # Run the worker logic (direct call to run for unit testing)
    tarefa.run()
    
    # Verificações
    mock_sync.sincronizar.assert_called_once()
    mock_repo.create_branch.assert_called()
    mock_copytree.assert_called()
    mock_repo.create_commit.assert_called()
    mock_sync.criar_pull_request.assert_called_once()
    
    assert len(success_url) == 1
    assert success_url[0] == "https://github.com/pr/1"

@patch("editor.core.worker.GerenciadorSincronizacao")
def test_tarefa_publicacao_erro_emite_sinal(mock_sync_class, mock_storage):
    mock_sync = mock_sync_class.return_value
    mock_sync.sincronizar.side_effect = Exception("Erro Fatal")
    
    tarefa = TarefaPublicacao(
        token="token", 
        storage=mock_storage, 
        caminho_database_croqui=Path("/fake/database"),
        id_croqui="test_id",
        dados_pr={"titulo": "T", "descricao": "D"}
    )
    
    errors = []
    tarefa.erro.connect(lambda msg: errors.append(msg))
    
    tarefa.run()
    
    assert len(errors) == 1
    assert "Erro Fatal" in errors[0]

@patch("editor.core.worker.pygit2.Repository")
@patch("editor.core.worker.github.Github")
@patch("editor.core.worker.shutil.copytree")
@patch("editor.core.worker.shutil.rmtree")
@patch("editor.core.worker.GerenciadorSincronizacao")
def test_tarefa_publicacao_remove_id_original(mock_sync_class, mock_rmtree, mock_copytree, mock_github, mock_repo_class, mock_storage, tmp_path):
    # Setup Mocks
    mock_sync = mock_sync_class.return_value
    mock_g = mock_github.return_value
    mock_repo = mock_repo_class.return_value
    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/pr/1"
    mock_sync.criar_pull_request.return_value = mock_pr
    
    mock_user = mock_g.get_user.return_value
    mock_user.name = "Teste"
    mock_user.email = "teste@aresta.local"
    
    # Criar mock do index para verificar se removeu do git
    mock_index = mock_repo.index
    
    # Setup de diretórios temporários para simular a leitura do yaml
    caminho_db = tmp_path / "database"
    caminho_db.mkdir()
    
    # Simula o arquivo croqui_experimental.yaml no nível acima da database
    import yaml
    with open(tmp_path / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"id_original": "old_id"}, f)
        
    # Precisamos criar a pasta de destino antigo para simular que existe e será deletada
    pasta_repo_base = mock_storage.obter_caminho_base_repo.return_value
    pasta_destino_antigo = pasta_repo_base / "database" / "old_id"
    # Faz o mock do exists() da pasta_destino_antigo retornar True (nós usamos o magic mock no base_repo)
    # Como obter_caminho_base_repo retorna um Path que nós vamos manipular no teste, 
    # é melhor mocar a propriedade exists() apenas nesse path.
    # Usaremos patch no Path.exists
    
    tarefa = TarefaPublicacao(
        token="token", 
        storage=mock_storage, 
        caminho_database_croqui=caminho_db,
        id_croqui="new_id",
        dados_pr={"titulo": "T", "descricao": "D"}
    )
    
    with patch("editor.core.worker.Path.exists", return_value=True):
        tarefa.run()
    
    # Deve ter chamado rmtree para a pasta do old_id
    mock_rmtree.assert_any_call(pasta_destino_antigo)
    
    # Deve ter chamado git rm
    mock_index.remove_all.assert_any_call(["database/old_id"])
    
    # O copytree deve ter copiado o novo id
    mock_copytree.assert_called()
