# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os

from scripts.gerar_croqui_experimental import empacotar_databases_para_croqui, _criar_croqui_experimental_yaml

def test_criar_croqui_experimental_yaml(tmp_path: Path):
    yaml_path = tmp_path / "croqui_experimental.yaml"
    _criar_croqui_experimental_yaml("teste_id", yaml_path)
    
    assert yaml_path.exists()
    
    import yaml
    with open(yaml_path, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
        
    assert dados["id_original"] == "teste_id"
    assert dados["autor"] == "Aresta CLI"
    assert "timestamp_criacao" in dados
    assert "Z" in dados["timestamp_criacao"]

@patch("scripts.gerar_croqui_experimental.deploy")
@patch("scripts.gerar_croqui_experimental.empacotar_croqui")
@patch("scripts.gerar_croqui_experimental.pygit2")
def test_empacotar_database_sucesso(mock_pygit2, mock_empacotar, mock_deploy, tmp_path: Path):
    """
    Testa o fluxo principal com mocks, garantindo 100% coverage das condicionais.
    """
    # Setup
    db_path = tmp_path / "database" / "pico_sucesso"
    db_path.mkdir(parents=True)
    
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    
    # Mock do empacotar_croqui para criar um arquivo dummy no destino
    def fake_empacotar(origem, destino):
        Path(destino).write_text("dummy zip", encoding="utf-8")
    mock_empacotar.side_effect = fake_empacotar
    
    # Execução
    arquivo_zip = empacotar_databases_para_croqui([db_path], out_dir)
    
    # Verificações
    assert arquivo_zip.exists()
    assert arquivo_zip.suffix == ".croqui"
    assert arquivo_zip.name.endswith("_modificados.croqui")
    
    # O deploy deve ser chamado com a pasta database copiada
    mock_deploy.assert_called_once()
    args, kwargs = mock_deploy.call_args
    assert "output_dir" in kwargs
    assert kwargs["output_dir"].name == "compilado"
    assert "target_paths" in kwargs
    
    # O git init deve ter sido chamado
    mock_pygit2.init_repository.assert_called_once()
    
def test_empacotar_database_falha_nao_existe(tmp_path: Path):
    """
    Testa comportamento se a pasta de origem não existir.
    """
    db_path = tmp_path / "nao_existe"
    out_dir = tmp_path / "saida"
    
    with pytest.raises(FileNotFoundError):
        empacotar_databases_para_croqui([db_path], out_dir)
