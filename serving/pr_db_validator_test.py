# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from serving.pr_db_validator import (
    validar_pull_request,
    validar_cabecalhos_e_licencas,
    main,
)


@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
@patch("serving.pr_db_validator.deploy")
def test_validar_pull_request_sucesso(mock_deploy, mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador retorna sucesso quando todas as pastas compilam corretamente e os cabeçalhos estão válidos.
    """
    mock_cabecalhos.return_value = []
    
    pasta_1 = tmp_path / "pico_1"
    pasta_1.mkdir()
    pasta_2 = tmp_path / "pico_2"
    pasta_2.mkdir()
    
    pastas = [str(pasta_1), str(pasta_2)]
    
    erros = validar_pull_request(pastas)
    
    assert len(erros) == 0
    assert mock_cabecalhos.call_count == 1
    assert mock_deploy.call_count == 1
    _, kwargs = mock_deploy.call_args
    assert len(kwargs["target_paths"]) == 2
    assert kwargs["is_producao"] is False


@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
@patch("serving.pr_db_validator.deploy")
def test_validar_pull_request_com_falha_compilacao(mock_deploy, mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador captura a falha quando ocorre erro na compilação via deploy(...).
    """
    mock_cabecalhos.return_value = []
    pasta_ruim = tmp_path / "pico_ruim"
    pasta_ruim.mkdir()
    pastas = [str(pasta_ruim)]
    
    mock_deploy.side_effect = RuntimeError("Erro simulado no pico_ruim")
    
    erros = validar_pull_request(pastas)
    
    assert len(erros) == 1
    assert "Erro simulado no pico_ruim" in erros[0]
    assert mock_deploy.call_count == 1


@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
def test_validar_pull_request_com_falha_cabecalhos(mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador reporta erros quando a validação de cabeçalhos falha.
    """
    mock_cabecalhos.return_value = ["Erro no cabeçalho SPDX de arquivo X"]
    pasta_1 = tmp_path / "pico_1"
    pasta_1.mkdir()
    pastas = [str(pasta_1)]
    
    erros = validar_pull_request(pastas)
    
    assert len(erros) == 1
    assert "Erro no cabeçalho SPDX de arquivo X" in erros[0]


def test_validar_pull_request_pasta_inexistente(tmp_path: Path):
    """
    Testa se o validador identifica pasta inexistente sem tentar compilar.
    """
    with patch("serving.pr_db_validator.validar_cabecalhos_e_licencas", return_value=[]):
        pasta_fantasma = tmp_path / "nao_existe"
        erros = validar_pull_request([str(pasta_fantasma)])
        assert len(erros) == 1
        assert "Pasta não encontrada ou inválida" in erros[0]


def test_validar_pull_request_vazio():
    """
    Testa comportamento quando nenhuma pasta é fornecida.
    """
    with patch("serving.pr_db_validator.validar_cabecalhos_e_licencas", return_value=[]):
        erros = validar_pull_request([])
        assert erros == []


@patch("serving.pr_db_validator.validar_cabecalhos_e_licencas")
@patch("serving.pr_db_validator.deploy")
def test_validar_pull_request_com_diretorio_saida(mock_deploy, mock_cabecalhos, tmp_path: Path):
    """
    Testa se o validador aceita um diretório de saída explícito.
    """
    mock_cabecalhos.return_value = []
    pasta = tmp_path / "pico_1"
    pasta.mkdir()
    saida = tmp_path / "saida_custom"
    
    erros = validar_pull_request([str(pasta)], diretorio_saida=str(saida))
    
    assert len(erros) == 0
    assert mock_deploy.call_count == 1
    assert saida.exists()


@patch("serving.pr_db_validator.validar_todos_cabecalhos_e_licencas")
def test_validar_cabecalhos_e_licencas_sucesso(mock_validador):
    """
    Testa execução com sucesso de validar_cabecalhos_e_licencas.
    """
    mock_validador.return_value = []
    erros = validar_cabecalhos_e_licencas()
    assert len(erros) == 0
    assert mock_validador.call_count == 1


@patch("serving.pr_db_validator.validar_todos_cabecalhos_e_licencas")
def test_validar_cabecalhos_e_licencas_falha(mock_validador):
    """
    Testa execução com falha de validar_cabecalhos_e_licencas.
    """
    mock_validador.return_value = ["Arquivo X sem cabeçalho SPDX"]
    erros = validar_cabecalhos_e_licencas()
    assert len(erros) == 1
    assert "Arquivo X sem cabeçalho SPDX" in erros[0]


@patch("serving.pr_db_validator.validar_pull_request")
def test_main_sucesso(mock_validador):
    """
    Testa fluxo de execução CLI quando não ocorrem erros.
    """
    mock_validador.return_value = []
    with patch("sys.argv", ["pr_db_validator.py", "--pastas", "database/pico"]):
        codigo = main()
        assert codigo == 0
        mock_validador.assert_called_once_with(["database/pico"], None)


@patch("serving.pr_db_validator.validar_pull_request")
def test_main_erro(mock_validador):
    """
    Testa fluxo de execução CLI quando ocorrem erros de validação.
    """
    mock_validador.return_value = ["Falha na validação"]
    with patch("sys.argv", ["pr_db_validator.py", "--pastas", "database/pico", "--saida", "/tmp/out"]):
        codigo = main()
        assert codigo == 1
        mock_validador.assert_called_once_with(["database/pico"], "/tmp/out")

