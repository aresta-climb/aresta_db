# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from serving.pr_db_validator import validar_pull_request, validar_cabecalhos_e_licencas

@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
@patch("serving.pr_db_validator.empacotar_databases_para_croqui")
def test_validar_pull_request_sucesso(mock_empacotar, mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador retorna sucesso quando todas as pastas compilam corretamente e os cabeçalhos estão válidos.
    """
    mock_cabecalhos.return_value = []
    pastas = ["database/pico_1", "database/pico_2"]
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    
    # Simula sucesso retornando um Path qualquer
    mock_empacotar.return_value = tmp_path / "teste.croqui"
    
    erros = validar_pull_request(pastas, str(out_dir))
    
    assert len(erros) == 0
    assert mock_cabecalhos.call_count == 1
    assert mock_empacotar.call_count == 1
    args, _ = mock_empacotar.call_args
    assert len(args[0]) == 2
    assert args[0][0].name == "pico_1"
    assert args[0][1].name == "pico_2"

@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
@patch("serving.pr_db_validator.empacotar_databases_para_croqui")
def test_validar_pull_request_com_falha_compilacao(mock_empacotar, mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador captura a falha quando ocorre erro no empacotamento.
    """
    mock_cabecalhos.return_value = []
    pastas = ["database/pico_ruim"]
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    
    mock_empacotar.side_effect = Exception("Erro simulado no pico_ruim")
    
    erros = validar_pull_request(pastas, str(out_dir))
    
    assert len(erros) == 1
    assert "Erro simulado no pico_ruim" in erros[0]
    assert mock_empacotar.call_count == 1

@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
@patch("serving.pr_db_validator.empacotar_databases_para_croqui")
def test_validar_pull_request_com_falha_cabecalhos(mock_empacotar, mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador reporta erros quando a validação de cabeçalhos falha.
    """
    mock_cabecalhos.return_value = ["Erro no cabeçalho SPDX de arquivo X"]
    pastas = ["database/pico_1"]
    out_dir = tmp_path / "saida"
    out_dir.mkdir()
    mock_empacotar.return_value = tmp_path / "teste.croqui"
    
    erros = validar_pull_request(pastas, str(out_dir))
    
    assert len(erros) == 1
    assert "Erro no cabeçalho SPDX de arquivo X" in erros[0]

@patch("subprocess.run")
def test_validar_cabecalhos_e_licencas_sucesso(mock_run):
    """
    Testa execução com sucesso de validar_cabecalhos_e_licencas.
    """
    mock_run.return_value = MagicMock(returncode=0, stdout="4 passed", stderr="")
    erros = validar_cabecalhos_e_licencas()
    assert len(erros) == 0
    assert mock_run.call_count == 1

@patch("subprocess.run")
def test_validar_cabecalhos_e_licencas_falha(mock_run):
    """
    Testa execução com falha de validar_cabecalhos_e_licencas.
    """
    mock_run.return_value = MagicMock(returncode=1, stdout="1 failed", stderr="error detail")
    erros = validar_cabecalhos_e_licencas()
    assert len(erros) == 1
    assert "Falha na validação de cabeçalhos" in erros[0]

