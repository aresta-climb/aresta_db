# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from editor.release_tools.calculate_next_dev import calculate_next_dev

def test_calculate_next_dev_versao_simples():
    assert calculate_next_dev("1.2.3") == "1.2.4-dev"

def test_calculate_next_dev_patch_zero():
    assert calculate_next_dev("2.0.0") == "2.0.1-dev"

def test_calculate_next_dev_com_sufixo_dev_existente():
    assert calculate_next_dev("1.2.3-dev") == "1.2.4-dev"

def test_calculate_next_dev_com_sufixo_beta():
    assert calculate_next_dev("1.2.3-beta.1") == "1.2.4-dev"

def test_calculate_next_dev_falha_poucas_partes():
    with pytest.raises(ValueError, match="não possui formato Major.Minor.Patch na base"):
        calculate_next_dev("1.2")

def test_calculate_next_dev_falha_muitas_partes():
    with pytest.raises(ValueError, match="não possui formato Major.Minor.Patch na base"):
        calculate_next_dev("1.2.3.4")

def test_calculate_next_dev_falha_patch_invalido():
    with pytest.raises(ValueError, match="não começa com números"):
        calculate_next_dev("1.2.dev")
