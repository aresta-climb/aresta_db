# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import os
import pytest

def pytest_configure(config):
    """
    Configura o ambiente de testes.
    Define o Qt para rodar em modo 'offscreen' (headless) por padrão,
    evitando que janelas fiquem abrindo e fechando durante os testes.
    """
    # Se você quiser ver as janelas para debug, rode com: $env:QT_QPA_PLATFORM='windows'
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
