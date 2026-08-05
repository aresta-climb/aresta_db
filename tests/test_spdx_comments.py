import pytest
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.preparar_submissao_lib import garantir_comentarios_licenca

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "spdx_comments"

@pytest.fixture
def tmp_spdx_dir(tmp_path):
    shutil.copytree(FIXTURES_DIR, tmp_path, dirs_exist_ok=True)
    return tmp_path

def test_yaml_sem_spdx(tmp_spdx_dir):
    p = tmp_spdx_dir / "croqui_sem_spdx.yaml"
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[1].strip() == "# Copyright (C) 2026 ARESTA Contributors"
    assert "id: teste" in "".join(linhas)

def test_yaml_com_spdx(tmp_spdx_dir):
    p = tmp_spdx_dir / "croqui_com_spdx.yaml"
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert texto.count("SPDX-License-Identifier") == 1

def test_md_sem_spdx(tmp_spdx_dir):
    p = tmp_spdx_dir / "pico_sem_spdx.md"
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "---"
    assert linhas[1].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[2].strip() == "# Copyright (C) 2026 ARESTA Contributors"

def test_md_com_spdx(tmp_spdx_dir):
    p = tmp_spdx_dir / "pico_com_spdx.md"
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert texto.count("SPDX-License-Identifier") == 1

def test_md_sem_frontmatter(tmp_spdx_dir):
    p = tmp_spdx_dir / "pico_sem_frontmatter.md"
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert "SPDX-License-Identifier" not in texto
