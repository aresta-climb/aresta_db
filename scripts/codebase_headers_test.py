# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
import re
from pathlib import Path

def test_todos_py_tem_spdx_e_copyright():
    """
    Garante que absolutamente todos os arquivos .py do repositório
    (ignorando diretórios gerados/caches) possuam as strings exatas de
    licenciamento SPDX e Copyright do Aresta Contributors.
    Arquivos na pasta 'aresta_api' DEVEM usar Apache-2.0.
    Os demais DEVEM usar GPL-3.0-or-later.
    """
    root = Path(__file__).resolve().parent.parent
    skip_dirs = {".git", "generated", "database", ".pytest_cache", "__pycache__", "venv", ".venv"}
    
    arquivos_sem_spdx = []
    arquivos_sem_copyright = []
    
    # Padrões estritos para o SPDX exigido
    spdx_gpl = re.compile(r"^#\s*SPDX-License-Identifier:\s*GPL-3\.0-or-later\s*$", re.MULTILINE)
    spdx_apache = re.compile(r"^#\s*SPDX-License-Identifier:\s*Apache-2\.0\s*$", re.MULTILINE)
    
    # Padrão flexível apenas para o ano
    copy_pattern = re.compile(r"^#\s*Copyright\s*\([Cc]\)\s*\d{4}\s*Aresta Contributors\s*$", re.MULTILINE)
    
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
        
        is_api = "aresta_api" in filepath.parts
        if is_api:
            if not spdx_apache.search(content):
                arquivos_sem_spdx.append(f"{filepath.relative_to(root)} (Faltou Apache-2.0)")
        else:
            if not spdx_gpl.search(content):
                arquivos_sem_spdx.append(f"{filepath.relative_to(root)} (Faltou GPL-3.0-or-later)")
            
        if not copy_pattern.search(content):
            arquivos_sem_copyright.append(str(filepath.relative_to(root)))
            
    assert count > 0, "Nenhum arquivo .py encontrado! Caminho base pode estar incorreto."
    assert not arquivos_sem_spdx, f"Arquivos .py com SPDX incorreto: {', '.join(arquivos_sem_spdx)}"
    assert not arquivos_sem_copyright, f"Arquivos .py sem Copyright exato: {', '.join(arquivos_sem_copyright)}"
