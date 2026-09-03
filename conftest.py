# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any
import os

def pytest_configure(config: Any) -> None:
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["ARESTA_DESATIVAR_TELEMETRIA"] = "1"

    from tests.bloqueador_rede import bloquear_acesso_externo

    bloquear_acesso_externo()


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    try:
        from tests.bloqueador_rede import restaurar_acesso_rede

        restaurar_acesso_rede()
    except Exception:
        pass

    try:
        from editor.core.telemetria import encerrar_telemetria

        encerrar_telemetria(timeout=1.0)
    except Exception:
        pass

