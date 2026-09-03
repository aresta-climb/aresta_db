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

