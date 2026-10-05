# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para o subpacote de integração Windows."""

import editor.plataforma.windows as pacote_windows


def test_subpacote_windows_carregamento() -> None:
    """Verifica que o subpacote Windows é importável."""
    assert pacote_windows is not None
