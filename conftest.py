# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any
import os
import sys

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
    No ambiente de CI ou sob a flag ARESTA_FAST_EXIT, encerra o processo de forma atômica
    no nível de kernel (TerminateProcess no Windows / os._exit). Isso evita que o descarregamento
    de DLLs C++ (pyside6.abi3.dll) no DLL_PROCESS_DETACH do Windows dispare Access Violation (0xC0000005).
    """
    if os.environ.get("CI") or os.environ.get("ARESTA_FAST_EXIT"):
        try:
            import faulthandler

            faulthandler.disable()
        except Exception:
            pass

        sys.stdout.flush()
        sys.stderr.flush()
        status = int(getattr(config, "_aresta_exitstatus", 0))

        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                kernel32.GetCurrentProcess.restype = ctypes.c_void_p
                kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                kernel32.TerminateProcess.restype = ctypes.c_bool
                kernel32.TerminateProcess(kernel32.GetCurrentProcess(), status)
            except Exception:
                pass

        os._exit(status)

