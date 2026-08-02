import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from serving.pr_db_validator import validar_pull_request

@patch("serving.pr_db_validator.empacotar_databases_para_croqui")
def test_validar_pull_request_sucesso(mock_empacotar, tmp_path: Path):
    """
    Testa se o validador retorna sucesso quando todas as pastas compilam corretamente.
    """
    pastas = ["database/pico_1", "database/pico_2"]
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    
    # Simula sucesso retornando um Path qualquer
    mock_empacotar.return_value = tmp_path / "teste.croqui"
    
    erros = validar_pull_request(pastas, str(out_dir))
    
    assert len(erros) == 0
    assert mock_empacotar.call_count == 1
    args, _ = mock_empacotar.call_args
    assert len(args[0]) == 2
    assert args[0][0].name == "pico_1"
    assert args[0][1].name == "pico_2"

@patch("serving.pr_db_validator.empacotar_databases_para_croqui")
def test_validar_pull_request_com_falha(mock_empacotar, tmp_path: Path):
    """
    Testa se o validador captura a falha quando ocorre erro no empacotamento.
    """
    pastas = ["database/pico_ruim"]
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    
    mock_empacotar.side_effect = Exception("Erro simulado no pico_ruim")
    
    erros = validar_pull_request(pastas, str(out_dir))
    
    assert len(erros) == 1
    assert "Erro simulado no pico_ruim" in erros[0]
    assert mock_empacotar.call_count == 1
