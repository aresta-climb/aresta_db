# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para o subpacote de integração macOS."""

import editor.plataforma.macos as pacote_macos


def test_subpacote_macos_carregamento() -> None:
    """Verifica que o subpacote macOS é importável."""
    assert pacote_macos is not None
