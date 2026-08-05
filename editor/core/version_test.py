# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import re
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
