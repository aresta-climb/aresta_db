# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any
import os
import pytest

def pytest_configure(config: Any) -> None:

    """
    Configura o ambiente de testes.
    Define o Qt para rodar em modo 'offscreen' (headless) por padrão,
    evitando que janelas fiquem abrindo e fechando durante os testes.
    """
    # Se você quiser ver as janelas para debug, rode com: $env:QT_QPA_PLATFORM='windows'
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

