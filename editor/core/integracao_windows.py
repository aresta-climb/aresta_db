# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração de janelas com o subsistema Win32 da Shell do Windows.
Fornece recursos para qualificação de janelas sem bordas (frameless) na barra de tarefas.
"""

import sys
from typing import Any

# Constantes da API Win32 para manipulação de estilos de janela
INDICE_ESTILO_ESTENDIDO: int = -20  # GWL_EXSTYLE
INDICE_ESTILO_PADRAO: int = -16     # GWL_STYLE

ESTILO_ESTENDIDO_APPWINDOW: int = 0x00040000  # WS_EX_APPWINDOW
ESTILO_MENU_SISTEMA: int = 0x00080000         # WS_SYSMENU


def _obter_user32() -> Any:

    """Retorna a biblioteca user32 do Win32 configurada com os tipos de chamada."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG
    return user32


def configurar_presenca_barra_de_tarefas(identificador_janela: int) -> bool:
    """
    Configura os estilos estendidos de janela no Windows para assegurar que janelas
    sem moldura (frameless) sejam exibidas com ícone na barra de tarefas e no alternador
    de janelas (Alt+Tab).

    Args:
        identificador_janela: O handle Win32 nativo da janela (HWND).

    Returns:
        True se os estilos foram aplicados com sucesso (ou em caso de plataforma não-Windows),
        False caso ocorra uma falha na chamada à API do sistema operacional.
    """
    if sys.platform != "win32":
        return True

    try:
        user32 = _obter_user32()


        # Lê os estilos atuais da janela
        estilo_estendido_atual: int = int(
            user32.GetWindowLongW(identificador_janela, INDICE_ESTILO_ESTENDIDO)
        )
        estilo_padrao_atual: int = int(
            user32.GetWindowLongW(identificador_janela, INDICE_ESTILO_PADRAO)
        )

        # Adiciona WS_EX_APPWINDOW para forçar aparição na barra de tarefas
        user32.SetWindowLongW(
            identificador_janela,
            INDICE_ESTILO_ESTENDIDO,
            estilo_estendido_atual | ESTILO_ESTENDIDO_APPWINDOW,
        )

        # Adiciona WS_SYSMENU para habilitar menu de contexto na barra de tarefas
        user32.SetWindowLongW(
            identificador_janela,
            INDICE_ESTILO_PADRAO,
            estilo_padrao_atual | ESTILO_MENU_SISTEMA,
        )

        return True
    except Exception:
        return False


def _esta_executando_em_pacote_msix() -> bool:
    """
    Verifica se o processo atual está sendo executado dentro de um pacote MSIX com identidade própria.
    No Windows, pacotes MSIX gerenciam seu próprio AppUserModelID via manifesto (PackageFamilyName!AppId).
    """
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        comprimento = wintypes.UINT(0)
        resultado = kernel32.GetCurrentPackageFamilyName(ctypes.byref(comprimento), None)
        # Código 0 indica ERROR_SUCCESS, significando que o processo possui identidade de pacote MSIX
        return bool(resultado == 0)
    except Exception:
        return False


def configurar_identidade_processo_windows(app_user_model_id: str) -> bool:
    """
    Configura explicitamente o AppUserModelID para processos standalone ou em desenvolvimento local.
    Caso a aplicação esteja rodando dentro de um pacote MSIX, a identidade nativa do pacote é
    preservada para assegurar a correspondência correta com os ícones e atalhos do Windows Shell.

    Args:
        app_user_model_id: Identificador único da aplicação no formato 'empresa.produto.versao'.

    Returns:
        True em caso de sucesso ou se estiver fora do Windows / sob pacote MSIX. False em caso de erro.
    """
    if sys.platform != "win32":
        return True

    try:
        if _esta_executando_em_pacote_msix():
            return True

        import ctypes

        resultado_hresult = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_user_model_id)
        return bool(resultado_hresult == 0)
    except Exception:
        return False


