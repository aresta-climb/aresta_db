# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import re
import tomllib
from pathlib import Path

try:
    from editor.core import version
except ImportError:
    version = None

def test_version_exists():
    assert version is not None, "Módulo editor.core.version não encontrado."
    assert hasattr(version, "VERSION"), "O atributo VERSION não foi encontrado no módulo."

def test_version_is_string():
    assert isinstance(version.VERSION, str), "A constante VERSION deve ser uma string."

def test_version_is_semver_format():
    # Regex semver oficial simplificada
    semver_pattern = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    assert semver_pattern.match(version.VERSION) is not None, f"A versão {version.VERSION} não segue o formato SemVer válido."

def test_semver_pattern_suporta_sufixos():
    semver_pattern = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    assert semver_pattern.match("1.2.3-dev") is not None
    assert semver_pattern.match("1.2.3-rc.1") is not None

def test_version_alinhada_com_pyproject_toml():
    """Garante que a versão no editor/core/version.py está estritamente em sincronia com o pyproject.toml."""
    raiz = Path(__file__).resolve().parent.parent.parent
    caminho_toml = raiz / "pyproject.toml"
    assert caminho_toml.exists(), "pyproject.toml não encontrado na raiz do repositório."
    
    with open(caminho_toml, "rb") as f:
        dados = tomllib.load(f)
        
    versao_toml = dados.get("project", {}).get("version")
    assert version.VERSION == versao_toml, (
        f"Inconsistência de versão detectada: editor/core/version.py tem '{version.VERSION}' "
        f"mas pyproject.toml tem '{versao_toml}'."
    )
