# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import tempfile
import pytest
from editor.release_tools.bump_version import bump_version_file, SemVerError

def test_bump_version_sucesso():
    # Cria um arquivo temporário simulando version.py
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as f:
        f.write('# Comentário inicial\nVERSION = "1.0.0"\n# Fim\n')
        temp_path = f.name
        
    try:
        bump_version_file(temp_path, "1.2.3")
        
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        assert 'VERSION = "1.2.3"' in content
        assert '# Comentário inicial' in content
        assert '# Fim' in content
    finally:
        os.remove(temp_path)

def test_bump_version_nova_versao_com_dev():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as f:
        f.write('VERSION = "1.2.3"\n')
        temp_path = f.name
        
    try:
        bump_version_file(temp_path, "1.3.0-dev")
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'VERSION = "1.3.0-dev"' in content
    finally:
        os.remove(temp_path)

def test_bump_version_formato_semver_invalido():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as f:
        f.write('VERSION = "1.2.3"\n')
        temp_path = f.name
        
    try:
        with pytest.raises(SemVerError):
            bump_version_file(temp_path, "versao-errada")
    finally:
        os.remove(temp_path)

def test_bump_version_arquivo_sem_versao():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as f:
        f.write('ALGUM_OUTRO_ATRIBUTO = "1.2.3"\n')
        temp_path = f.name
        
    try:
        with pytest.raises(ValueError, match="Padrão VERSION = .* não encontrado no arquivo"):
            bump_version_file(temp_path, "1.2.3")
    finally:
        os.remove(temp_path)
