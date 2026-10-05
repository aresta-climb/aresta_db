# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para o subpacote de integração Linux."""

import editor.plataforma.linux as pacote_linux


def test_subpacote_linux_carregamento() -> None:
    """Verifica que o subpacote Linux é importável."""
    assert pacote_linux is not None
