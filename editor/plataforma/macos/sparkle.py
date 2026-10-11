# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Ponte de integração entre o Editor Aresta e o Sparkle Framework no macOS.
Permite o carregamento dinâmico e invocação do controlador de atualizações nativo
utilizando chamadas ao runtime Objective-C via ctypes de forma não-bloqueante.
"""

import ctypes
import sys
from pathlib import Path
from typing import Any


def _obter_runtime_objc() -> Any:
    """Retorna a biblioteca libobjc do sistema operacional macOS."""
    return ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")


def localizar_caminho_sparkle_framework() -> Path | None:
    """
    Localiza o diretório do Sparkle.framework dentro da estrutura de bundle macOS
    (Contents/Frameworks/Sparkle.framework) ou em diretórios do sistema.
    """
    # 1. Tenta a partir do executável em execução (bundle .app)
    caminho_exe = Path(sys.executable).resolve()
    candidato_bundle = caminho_exe.parent.parent / "Frameworks" / "Sparkle.framework"
    if candidato_bundle.exists():
        return candidato_bundle

    # 2. Tenta a partir do diretório do sistema
    candidato_sistema = Path("/Library/Frameworks/Sparkle.framework")
    if candidato_sistema.exists():
        return candidato_sistema

    return None


def carregar_biblioteca_sparkle(
    caminho_framework: Path | None = None,
) -> Any | None:
    """
    Carrega o binário dinâmico do Sparkle.framework utilizando ctypes.CDLL.
    Retorna a instância da biblioteca carregada ou None se indisponível.
    """
    if sys.platform != "darwin":
        return None

    caminho = caminho_framework or localizar_caminho_sparkle_framework()
    if not caminho or not caminho.exists():
        return None

    binario = caminho / "Versions" / "Current" / "Sparkle"
    if not binario.exists():
        binario = caminho / "Sparkle"

    try:
        return ctypes.CDLL(str(binario))
    except (OSError, Exception):
        return None


def obter_controlador_sparkle() -> Any | None:
    """
    Obtém ou instancia o controlador SPUStandardUpdaterController do Sparkle 2.
    Retorna o ponteiro para o objeto Objective-C ou None em caso de falha.
    """
    handle_lib = carregar_biblioteca_sparkle()
    if not handle_lib:
        return None

    try:
        objc = _obter_runtime_objc()
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

        cls = objc.objc_getClass(b"SPUStandardUpdaterController")
        if not cls:
            return None

        sel_shared = objc.sel_registerName(b"sharedUpdaterController")
        controlador = objc.objc_msgSend(cls, sel_shared)
        return controlador
    except Exception:
        return None


def solicitar_verificacao_sparkle(controlador: Any | None = None) -> bool:
    """
    Dispara a verificação imediata de novas versões através do Sparkle Framework,
    exibindo a interface gráfica nativa de diálogo e progresso do macOS.
    """
    instancia = controlador if controlador is not None else obter_controlador_sparkle()
    if not instancia:
        return False

    try:
        objc = _obter_runtime_objc()
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]

        sel_check = objc.sel_registerName(b"checkForUpdates:")
        objc.objc_msgSend(instancia, sel_check, None)
        return True
    except Exception:
        return False
