# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from pathlib import Path
from scripts.validador_cabecalhos import (
    verificar_spdx_e_copyright_py,
    verificar_gpl_residual_py,
    verificar_odbl_e_copyright_database,
)


def test_todos_py_tem_spdx_e_copyright():
    """
    Garante que absolutamente todos os arquivos .py do repositório
    (ignorando diretórios gerados/caches) possuam as strings exatas de
    licenciamento SPDX (MPL-2.0) e Copyright do Aresta [Climb] Contributors.
    """
    root = Path(__file__).resolve().parent.parent
    erros = verificar_spdx_e_copyright_py(root)
    assert not erros, "\n".join(erros)


def test_nenhum_py_contem_gpl_residual():
    """
    Garante que nenhum arquivo .py ativo contenha menção residual à licença GPL.
    """
    root = Path(__file__).resolve().parent.parent
    erros = verificar_gpl_residual_py(root)
    assert not erros, "\n".join(erros)


def test_todos_database_arquivos_tem_odbl_e_copyright():
    """
    Garante que todos os arquivos de dados (.yaml) e documentos com frontmatter (.md)
    dentro do diretório 'database/' possuam o identificador SPDX de dados (ODbL-1.0)
    e o Copyright do Aresta [Climb] Contributors.
    """
    root = Path(__file__).resolve().parent.parent
    database_dir = root / "database"
    if not database_dir.exists() or not database_dir.is_dir():
        pytest.skip("Diretório database/ não encontrado na raiz (sparse checkout detectado).")

    erros = verificar_odbl_e_copyright_database(root)
    assert not erros, "\n".join(erros)

