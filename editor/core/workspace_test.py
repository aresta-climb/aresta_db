# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

from editor.core.workspace import (
    ExperimentalWorkspace,
    LocalRepoWorkspace,
)

@pytest.fixture
def tmp_paths(tmp_path):
    # Simula a estrutura aresta_db/database/meu_croqui
    aresta_db = tmp_path / "aresta_db"
    aresta_db.mkdir()
    
    scripts = aresta_db / "scripts"
    scripts.mkdir()
    (scripts / "medir_saude_croquis.py").touch()
    
    db_dir = aresta_db / "database"
    db_dir.mkdir()
    
    raiz = db_dir / "meu_croqui"
    raiz.mkdir()
    
    # Para o ExperimentalWorkspace (que usa a raiz diretamente)
    (raiz / "database").mkdir()
    (raiz / "compilado").mkdir()
    
    return raiz

def test_experimental_workspace_paths(tmp_paths):
    ws = ExperimentalWorkspace(tmp_paths)
    
    assert ws.obter_caminho_database() == tmp_paths / "database"
    assert ws.obter_caminho_compilado() == tmp_paths / "compilado"
    assert ws.obter_pasta_servidor_celular() == tmp_paths / "compilado"
    assert ws.can_publish_pr() is True
    assert ws.obter_tag_titulo() == ""

@patch("editor.core.workspace.GerenciadorCroquiExperimental")
def test_experimental_workspace_processar(mock_gerenciador_cls, tmp_paths):
    mock_gerenciador = MagicMock()
    mock_gerenciador_cls.return_value = mock_gerenciador
    
    # Mock para renomear
    novo_caminho = tmp_paths.parent / "novo_croqui"
    mock_gerenciador.renomear_pasta_croqui.return_value = novo_caminho
    
    ws = ExperimentalWorkspace(tmp_paths)
    mock_storage = MagicMock()
    
    # Testa quando ID muda
    resultado, msgs = ws.processar_renomeacao_e_compilacao("novo_id", "id_atual", mock_storage)
    
    mock_gerenciador_cls.assert_called_once_with(mock_storage)
    mock_gerenciador.renomear_pasta_croqui.assert_called_once_with(tmp_paths, "novo_id")
    mock_gerenciador.compilar_croqui.assert_called_once_with(novo_caminho)
    assert resultado == novo_caminho
    assert ws.caminho_raiz == novo_caminho
    assert isinstance(msgs, list)
    
    # Testa quando ID não muda
    mock_gerenciador.reset_mock()
    resultado2, msgs2 = ws.processar_renomeacao_e_compilacao("novo_id", "novo_id", mock_storage)
    mock_gerenciador.renomear_pasta_croqui.assert_not_called()
    mock_gerenciador.compilar_croqui.assert_called_once_with(novo_caminho)
    assert resultado2 == novo_caminho
    assert isinstance(msgs2, list)

def test_local_repo_workspace_paths(tmp_paths):
    # tmp_paths simula aresta_db/database/meu_croqui
    ws = LocalRepoWorkspace(tmp_paths)
    
    assert ws.obter_caminho_database() == tmp_paths
    assert ws.obter_caminho_compilado() == tmp_paths.parent.parent / "generated" / tmp_paths.name
    assert ws.obter_pasta_servidor_celular() == tmp_paths.parent.parent / "generated"
    assert ws.can_publish_pr() is False
    assert ws.obter_tag_titulo() == "[Local Mode]"

@patch("editor.core.workspace.deploy")
@patch("editor.core.workspace.subprocess.run")
def test_local_repo_workspace_processar(mock_run, mock_deploy, tmp_paths):
    ws = LocalRepoWorkspace(tmp_paths)
    mock_storage = MagicMock()
    
    # Testa quando ID não muda
    resultado, msgs = ws.processar_renomeacao_e_compilacao("meu_croqui", "meu_croqui", mock_storage)
    
    # O health check deve ter sido chamado via subprocess
    mock_run.assert_called_once()
    chamada = mock_run.call_args[0][0]
    assert "medir_saude_croquis.py" in str(chamada[1])
    
    mock_deploy.assert_called_once()
    
    # Verifica argumentos do deploy
    args = mock_deploy.call_args[1]
    assert args["output_dir"] == ws.obter_caminho_compilado().parent
    assert args["target_paths"] == [ws.obter_caminho_database()]
    assert args["is_producao"] is False
    
    assert resultado == tmp_paths
    assert isinstance(msgs, list)
    
@patch("editor.core.workspace.deploy")
@patch("editor.core.workspace.subprocess.run")
def test_local_repo_workspace_processar_com_renomeacao(mock_run, mock_deploy, tmp_paths):
    ws = LocalRepoWorkspace(tmp_paths)
    mock_storage = MagicMock()
    
    caminho_compilado = ws.obter_caminho_compilado()
    caminho_compilado.parent.mkdir(parents=True, exist_ok=True)
    caminho_compilado.mkdir()
    
    # Testa quando ID muda
    resultado, msgs = ws.processar_renomeacao_e_compilacao("novo_croqui", "meu_croqui", mock_storage)
    
    novo_caminho = tmp_paths.parent / "novo_croqui"
    assert resultado == novo_caminho
    assert ws.caminho_raiz == novo_caminho
    
    # Verifica chamadas ao git mv e ao medir saude
    assert mock_run.call_count == 3
    chamada1 = mock_run.call_args_list[0][0][0]
    assert chamada1[:3] == ["git", "mv", str(tmp_paths)]
    assert chamada1[3] == str(novo_caminho)
    
    chamada2 = mock_run.call_args_list[1][0][0]
    assert chamada2[:3] == ["git", "mv", str(caminho_compilado)]
    assert chamada2[3] == str(caminho_compilado.parent / "novo_croqui")

    chamada3 = mock_run.call_args_list[2][0][0]
    assert "medir_saude_croquis.py" in str(chamada3[1])
    
    mock_deploy.assert_called_once()

@patch("editor.core.workspace.deploy")
@patch("editor.core.workspace.subprocess.run")
def test_local_repo_workspace_processar_falha_renomeacao(mock_run, mock_deploy, tmp_paths):
    ws = LocalRepoWorkspace(tmp_paths)
    mock_storage = MagicMock()
    
    mock_run.side_effect = subprocess.CalledProcessError(1, "git")
    
    with pytest.raises(RuntimeError) as exc_info:
        ws.processar_renomeacao_e_compilacao("novo_croqui", "meu_croqui", mock_storage)
        
    assert "Falha ao renomear" in str(exc_info.value)
    assert ws.caminho_raiz == tmp_paths  # Estado não deve ter sido alterado
    mock_deploy.assert_not_called()

def test_captura_mensagens(tmp_paths):
    # Testa se captura prints de avisos
    import sys
    
    ws = ExperimentalWorkspace(tmp_paths)
    mock_storage = MagicMock()
    
    with patch("editor.core.workspace.GerenciadorCroquiExperimental") as mock_cls:
        mock_gerenciador = mock_cls.return_value
        
        def fake_compilar(*args, **kwargs):
            print("Isso é um print normal.")
            print("Aviso: ID duplicado.")
            print("Erro ao tentar fazer algo.")
            print("  Warning: isso falhou feio")
            print("tudo certo!")
            
        mock_gerenciador.compilar_croqui.side_effect = fake_compilar
        
        _, msgs = ws.processar_renomeacao_e_compilacao("id", "id", mock_storage)
        
        assert "Aviso: ID duplicado." in msgs
        assert "Erro ao tentar fazer algo." in msgs
        assert "  Warning: isso falhou feio" in msgs
        assert "Isso é um print normal." not in msgs
        assert "tudo certo!" not in msgs

def test_experimental_workspace_diario_consolidacao(tmp_paths):
    ws = ExperimentalWorkspace(tmp_paths)
    diario = ws.obter_diario()
    assert diario is not None
    
    # Grava alteração pendente
    diario.gravar_comando_pendente({"classe": "CmdTeste"})
    assert diario.tem_alteracoes_pendentes()
    
    mock_storage = MagicMock()
    with patch("editor.core.workspace.GerenciadorCroquiExperimental") as mock_cls:
        mock_gerenciador = mock_cls.return_value
        mock_gerenciador.compilar_croqui.return_value = None
        
        ws.processar_renomeacao_e_compilacao("id", "id", mock_storage)
        
    # Deve ter consolidado o diário
    assert not diario.tem_alteracoes_pendentes()
    assert len(diario.ler_diario_salvo()) == 1


def test_local_repo_workspace_diario_consolidacao(tmp_path):
    repo_dir = tmp_path / "repo"
    croqui_dir = repo_dir / "database" / "croqui_teste"
    croqui_dir.mkdir(parents=True)

    mock_storage = MagicMock()
    pasta_diarios = tmp_path / "appdata" / "diarios_locais"
    mock_storage.obter_caminho_diarios_locais.return_value = pasta_diarios

    ws = LocalRepoWorkspace(croqui_dir, storage=mock_storage)
    diario = ws.obter_diario()
    assert diario is not None
    # Diário deve estar fora da pasta do croqui
    assert diario.pasta_croqui == pasta_diarios / "croqui_teste"
    assert not (croqui_dir / "diario_pendente.bin").exists()

    diario.gravar_comando_pendente({"classe": "CmdLocalTeste"})
    assert diario.tem_alteracoes_pendentes()

    with patch("editor.core.workspace.deploy") as mock_deploy:
        ws.processar_renomeacao_e_compilacao("croqui_teste", "croqui_teste", mock_storage)

    # Pendente deve ter sido esvaziado
    assert not diario.tem_alteracoes_pendentes()
    # Em modo local, diario_salvo.bin NÃO é criado
    assert len(diario.ler_diario_salvo()) == 0
    assert not diario.caminho_salvo.exists()
    assert not (croqui_dir / "diario_salvo.bin").exists()
