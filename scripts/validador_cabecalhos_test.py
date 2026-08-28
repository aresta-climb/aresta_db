# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from scripts.validador_cabecalhos import (
    verificar_spdx_e_copyright_py,
    verificar_gpl_residual_py,
    verificar_odbl_e_copyright_database,
    validar_todos_cabecalhos_e_licencas,
)


def test_verificar_spdx_e_copyright_py_sucesso(tmp_path: Path):
    arquivo_ok = tmp_path / "modulo_ok.py"
    arquivo_ok.write_text(
        "# SPDX-License-Identifier: MPL-2.0\n# Copyright (C) 2026 Aresta Climb Contributors\n\ndef foo(): pass\n",
        encoding="utf-8",
    )
    erros = verificar_spdx_e_copyright_py(tmp_path)
    assert len(erros) == 0


def test_verificar_spdx_e_copyright_py_falhas(tmp_path: Path):
    arquivo_sem_spdx = tmp_path / "sem_spdx.py"
    arquivo_sem_spdx.write_text(
        "# Copyright (C) 2026 Aresta Climb Contributors\ndef foo(): pass\n",
        encoding="utf-8",
    )

    arquivo_sem_copy = tmp_path / "sem_copy.py"
    arquivo_sem_copy.write_text(
        "# SPDX-License-Identifier: MPL-2.0\ndef bar(): pass\n",
        encoding="utf-8",
    )

    erros = verificar_spdx_e_copyright_py(tmp_path)
    assert any("SPDX incorreto" in e for e in erros)
    assert any("sem Copyright" in e for e in erros)


def test_verificar_spdx_e_copyright_py_vazio(tmp_path: Path):
    erros = verificar_spdx_e_copyright_py(tmp_path)
    assert len(erros) == 1
    assert "Nenhum arquivo .py encontrado" in erros[0]


def test_verificar_gpl_residual_py_sucesso(tmp_path: Path):
    arquivo_ok = tmp_path / "codigo.py"
    arquivo_ok.write_text("# SPDX-License-Identifier: MPL-2.0\n", encoding="utf-8")
    erros = verificar_gpl_residual_py(tmp_path)
    assert len(erros) == 0


def test_verificar_gpl_residual_py_falha(tmp_path: Path):
    arquivo_gpl = tmp_path / "antigo.py"
    arquivo_gpl.write_text("# SPDX-License-Identifier: GPL-3.0\n", encoding="utf-8")
    erros = verificar_gpl_residual_py(tmp_path)
    assert len(erros) == 1
    assert "menção residual a GPL" in erros[0]


def test_verificar_odbl_e_copyright_database_sucesso(tmp_path: Path):
    db_dir = tmp_path / "database" / "pico_1"
    db_dir.mkdir(parents=True)

    yaml_file = db_dir / "dados.yaml"
    yaml_file.write_text(
        "# SPDX-License-Identifier: ODbL-1.0\n# Copyright (C) 2026 Aresta Climb Contributors\nchave: valor\n",
        encoding="utf-8",
    )

    md_file = db_dir / "info.md"
    md_file.write_text(
        "---\n# SPDX-License-Identifier: ODbL-1.0\n# Copyright (C) 2026 Aresta Climb Contributors\n---\n# Info",
        encoding="utf-8",
    )

    # Markdown sem frontmatter deve ser ignorado
    md_sem_front = db_dir / "notas.md"
    md_sem_front.write_text("# Apenas notas sem frontmatter", encoding="utf-8")

    erros = verificar_odbl_e_copyright_database(tmp_path)
    assert len(erros) == 0


def test_verificar_odbl_e_copyright_database_falhas(tmp_path: Path):
    db_dir = tmp_path / "database" / "pico_2"
    db_dir.mkdir(parents=True)

    yaml_sem_odbl = db_dir / "croqui.yaml"
    yaml_sem_odbl.write_text("# Copyright (C) 2026 Aresta Contributors\nchave: 1\n", encoding="utf-8")

    erros = verificar_odbl_e_copyright_database(tmp_path)
    assert any("sem ODbL-1.0" in e for e in erros)


def test_validar_todos_cabecalhos_e_licencas_integracao(tmp_path: Path):
    # Cria uma estrutura válida completa
    py_file = tmp_path / "script.py"
    py_file.write_text(
        "# SPDX-License-Identifier: MPL-2.0\n# Copyright (C) 2026 Aresta Climb Contributors\n",
        encoding="utf-8",
    )
    db_dir = tmp_path / "database" / "setor"
    db_dir.mkdir(parents=True)
    yaml_file = db_dir / "info.yaml"
    yaml_file.write_text(
        "# SPDX-License-Identifier: ODbL-1.0\n# Copyright (C) 2026 Aresta Climb Contributors\n",
        encoding="utf-8",
    )

    erros = validar_todos_cabecalhos_e_licencas(tmp_path)
    assert len(erros) == 0
