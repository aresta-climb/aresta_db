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
    if hasattr(session, "config"):
        setattr(session.config, "_aresta_exitstatus", exitstatus)

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

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QThreadPool

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.closeAllWindows()
            app.processEvents()

        pool = QThreadPool.globalInstance()
        if pool is not None:
            pool.waitForDone(1000)

        if isinstance(app, QApplication):
            try:
                import shiboken6

                shiboken6.delete(app)
            except Exception:
                pass
    except Exception:
        pass


def pytest_unconfigure(config: Any) -> None:
    """
    No ambiente de CI ou sob a flag ARESTA_FAST_EXIT, encerra o processo via os._exit
    após a impressão de todos os resultados pelo pytest. Isso evita que o descarregamento
    de DLLs C++ do PySide6/Qt no Py_FinalizeEx do Windows dispare Access Violation (0xC0000005).
    """
    if os.environ.get("CI") or os.environ.get("ARESTA_FAST_EXIT"):
        import sys

        try:
            import faulthandler

            faulthandler.disable()
        except Exception:
            pass

        sys.stdout.flush()
        sys.stderr.flush()
        status = int(getattr(config, "_aresta_exitstatus", 0))
        os._exit(status)

