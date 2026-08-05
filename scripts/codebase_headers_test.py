import pytest
from pathlib import Path

def test_todos_py_tem_spdx_e_copyright():
    """
    Garante que absolutamente todos os arquivos .py do repositório
    (ignorando diretórios gerados/caches) possuam as strings de
    licenciamento SPDX e Copyright.
    """
    root = Path(__file__).resolve().parent.parent
    skip_dirs = {".git", "generated", "database", ".pytest_cache", "__pycache__", "venv", ".venv"}
    
    arquivos_sem_spdx = []
    arquivos_sem_copyright = []
    
    count = 0
    for filepath in root.rglob("*.py"):
        if any(part in skip_dirs for part in filepath.parts):
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
            
        count += 1
        if "SPDX-License-Identifier" not in content:
            arquivos_sem_spdx.append(str(filepath.relative_to(root)))
            
        if "Copyright" not in content:
            arquivos_sem_copyright.append(str(filepath.relative_to(root)))
            
    assert count > 0, "Nenhum arquivo .py encontrado! Caminho base pode estar incorreto."
    assert not arquivos_sem_spdx, f"Arquivos .py sem SPDX: {', '.join(arquivos_sem_spdx)}"
    assert not arquivos_sem_copyright, f"Arquivos .py sem Copyright: {', '.join(arquivos_sem_copyright)}"
