# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import re
from pathlib import Path

def test_todos_py_tem_spdx_e_copyright():
    """
    Garante que absolutamente todos os arquivos .py do repositório
    (ignorando diretórios gerados/caches) possuam as strings exatas de
    licenciamento SPDX (MPL-2.0) e Copyright do Aresta [Climb] Contributors.
    """
    root = Path(__file__).resolve().parent.parent
    skip_dirs = {".git", "generated", "database", ".pytest_cache", "__pycache__", "venv", ".venv"}
    
    arquivos_sem_spdx = []
    arquivos_sem_copyright = []
    
    # Padrão estrito para o SPDX exigido (MPL-2.0)
    spdx_mpl = re.compile(r"^#\s*SPDX-License-Identifier:\s*MPL-2\.0\s*$", re.MULTILINE)
    
    # Aceita tanto 'Aresta Climb Contributors' quanto 'Aresta Contributors'
    copy_pattern = re.compile(r"^#\s*(SPDX-FileCopyrightText:\s*)?Copyright\s*\([Cc]\)\s*\d{4}\s*Aresta\s+(Climb\s+)?Contributors\s*$", re.MULTILINE)
    
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
        
        if not spdx_mpl.search(content):
            arquivos_sem_spdx.append(f"{filepath.relative_to(root)} (Faltou MPL-2.0)")
            
        if not copy_pattern.search(content):
            arquivos_sem_copyright.append(str(filepath.relative_to(root)))
            
    assert count > 0, "Nenhum arquivo .py encontrado! Caminho base pode estar incorreto."
    assert not arquivos_sem_spdx, f"Arquivos .py com SPDX incorreto: {', '.join(arquivos_sem_spdx)}"
    assert not arquivos_sem_copyright, f"Arquivos .py sem Copyright exato: {', '.join(arquivos_sem_copyright)}"

def test_nenhum_py_contem_gpl_residual():
    """
    Garante que nenhum arquivo .py ativo contenha menção residual à licença GPL.
    """
    root = Path(__file__).resolve().parent.parent
    skip_dirs = {".git", "generated", "database", ".pytest_cache", "__pycache__", "venv", ".venv", "openspec"}
    
    arquivos_com_gpl = []
    for filepath in root.rglob("*.py"):
        if any(part in skip_dirs for part in filepath.parts):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if filepath == Path(__file__).resolve():
            continue
        if "GPL-3.0" in content or "GPLv3" in content:
            arquivos_com_gpl.append(str(filepath.relative_to(root)))
            
    assert not arquivos_com_gpl, f"Arquivos com menção residual a GPL: {', '.join(arquivos_com_gpl)}"

def test_todos_database_arquivos_tem_odbl_e_copyright():
    """
    Garante que todos os arquivos de dados (.yaml) e documentos com frontmatter (.md)
    dentro do diretório 'database/' possuam o identificador SPDX de dados (ODbL-1.0)
    e o Copyright do Aresta [Climb] Contributors.
    """
    root = Path(__file__).resolve().parent.parent
    database_dir = root / "database"
    
    arquivos_sem_odbl = []
    arquivos_sem_copyright = []
    
    spdx_odbl = re.compile(r"^#\s*SPDX-License-Identifier:\s*ODbL-1\.0\s*$", re.MULTILINE)
    copy_pattern = re.compile(r"^#\s*(SPDX-FileCopyrightText:\s*)?Copyright\s*\([Cc]\)\s*\d{4}\s*Aresta\s+(Climb\s+)?Contributors\s*$", re.MULTILINE)
    
    count = 0
    for filepath in database_dir.rglob("*"):
        if filepath.is_dir():
            continue
        if filepath.suffix not in {".yaml", ".md"}:
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
            
        if filepath.suffix == ".md" and not content.startswith("---"):
            continue
            
        count += 1
        
        if not spdx_odbl.search(content):
            arquivos_sem_odbl.append(str(filepath.relative_to(root)))
            
        if not copy_pattern.search(content):
            arquivos_sem_copyright.append(str(filepath.relative_to(root)))
            
    assert count > 0, "Nenhum arquivo de database encontrado!"
    assert not arquivos_sem_odbl, f"Arquivos na database sem ODbL-1.0: {len(arquivos_sem_odbl)} arquivos (ex: {', '.join(arquivos_sem_odbl[:5])})"
    assert not arquivos_sem_copyright, f"Arquivos na database sem Copyright correto: {len(arquivos_sem_copyright)} arquivos (ex: {', '.join(arquivos_sem_copyright[:5])})"



