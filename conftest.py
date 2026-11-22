# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import ctypes
import os
import sys
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Suprime avisos de depreciação internos de tipos SWIG de extensões C++ compiladas em Python 3.13
warnings.filterwarnings("ignore", category=DeprecationWarning, message=r"builtin type SwigPy.*")
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=r"builtin type swigvarlink.*"
)

# Garante saída padrão em UTF-8 no Windows (evita UnicodeEncodeError com cp1252 quando captura=-s)
for _stream in (sys.stdout, sys.stderr):
    getattr(_stream, "reconfigure", lambda **_kw: None)(encoding="utf-8", errors="replace")

# Garante plataforma gráfica headless (offscreen) antes de qualquer importação de PySide6 ou plugins do pytest
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Disponibiliza stub de ctypes.windll em plataformas não-Windows para testes unitários
if not hasattr(ctypes, "windll"):
    setattr(ctypes, "windll", MagicMock())


def limpar_janelas_qt_ativas() -> None:
    """Fecha todas as janelas ativas da QApplication, limpa quitNow residual e drena eventos."""
    try:
        from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setQuitOnLastWindowClosed(False)
            for w in app.topLevelWidgets():
                if hasattr(w, "_forcar_fechamento"):
                    setattr(w, "_forcar_fechamento", True)
            app.closeAllWindows()
            QCoreApplication.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
            app.processEvents()
            if type(app) is QApplication:
                sonda = QEventLoop()
                QTimer.singleShot(0, sonda.quit)
                if sonda.exec() == -1:
                    QTimer.singleShot(0, app.quit)
                    app.exec()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _isolar_ambiente_sessao_e_dados(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    """
    Isola o cofre de credenciais (keyring) em memória e redireciona ARESTA_DIRETORIO_DADOS
    para um diretório temporário descartável em cada teste, impedindo vazamento para o SO.
    """
    import keyring

    from editor.core.gerenciador_sessao_fake import CofreChaveiroFake

    backend_anterior = keyring.get_keyring()
    cofre_isolado = CofreChaveiroFake()
    keyring.set_keyring(cofre_isolado)
    diretorio_dados = tmp_path / "aresta_dados_isolados"
    monkeypatch.setenv("ARESTA_DIRETORIO_DADOS", str(diretorio_dados))
    sys_path_anterior = list(sys.path)
    cwd_anterior = Path.cwd()
    try:
        yield cofre_isolado
    finally:
        keyring.set_keyring(backend_anterior)
        sys.path[:] = sys_path_anterior
        if cwd_anterior.is_dir():
            os.chdir(cwd_anterior)


@pytest.fixture(autouse=True)
def _limpar_janelas_qt_apos_teste() -> Any:
    """Garante que qualquer janela do Qt aberta pelo teste seja fechada e os eventos drenados."""
    yield
    limpar_janelas_qt_ativas()


def pytest_configure(config: Any) -> None:
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["ARESTA_DESATIVAR_TELEMETRIA"] = "1"

    import keyring

    from editor.core.gerenciador_sessao_fake import CofreChaveiroFake
    from tests.bloqueador_rede import bloquear_acesso_externo

    keyring.set_keyring(CofreChaveiroFake())
    bloquear_acesso_externo()


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    if hasattr(session, "config"):
        session.config._aresta_exitstatus = exitstatus

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
        from PySide6.QtCore import QThreadPool

        limpar_janelas_qt_ativas()

        pool = QThreadPool.globalInstance()
        if pool is not None:
            pool.waitForDone(1000)
    except Exception:
        pass


def pytest_unconfigure(config: Any) -> None:
    """
    No ambiente de CI ou sob a flag ARESTA_FAST_EXIT, encerra o processo de forma atômica
    no nível de kernel (TerminateProcess no Windows / os._exit). Isso evita que o descarregamento
    de DLLs C++ (pyside6.abi3.dll) no DLL_PROCESS_DETACH do Windows dispare Access Violation (0xC0000005).
    Em execuções locais sem xdist, destrói ordenadamente widgets órfãos e a QApplication após todos os
    plugins (pytest-qt, pytest-cov) concluírem seus relatórios.
    """
    if os.environ.get("CI") or os.environ.get("ARESTA_FAST_EXIT"):
        try:
            import faulthandler

            faulthandler.disable()
        except Exception:
            pass

        sys.stdout.flush()
        sys.stderr.flush()
        status_armazenado = getattr(config, "_aresta_exitstatus", None)
        if status_armazenado is None:
            # Se _aresta_exitstatus não foi definido, pytest_sessionfinish não executou
            # (provavelmente devido a erro interno ou exceção durante pytest_configure).
            # Jamais mascarar o erro retornando 0; repassar ExitCode.INTERNAL_ERROR (3).
            status = 3
        else:
            status = int(status_armazenado)

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

    if not os.environ.get("PYTEST_XDIST_WORKER") and isinstance(
        getattr(config, "_aresta_exitstatus", None), int
    ):
        try:
            import gc

            import shiboken6
            from PySide6.QtCore import QCoreApplication, QEvent
            from PySide6.QtWidgets import QApplication

            limpar_janelas_qt_ativas()
            gc.collect()
            app = QApplication.instance()
            if isinstance(app, QApplication):
                for widget_restante in list(app.topLevelWidgets()):
                    if shiboken6.isValid(widget_restante):
                        shiboken6.delete(widget_restante)
                QCoreApplication.sendPostedEvents(None, int(QEvent.Type.DeferredDelete))
                app.processEvents()
                gc.collect()
                shiboken6.delete(app)
        except Exception:
            pass
