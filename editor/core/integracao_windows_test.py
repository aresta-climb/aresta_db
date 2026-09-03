# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import pytest
from unittest.mock import MagicMock, patch

from editor.core.integracao_windows import (
    configurar_presenca_barra_de_tarefas,
    ESTILO_ESTENDIDO_APPWINDOW,
    ESTILO_MENU_SISTEMA,
)


def test_configurar_presenca_barra_de_tarefas_no_op_fora_do_windows():
    """Garante que em plataformas não-Windows a função opere como no-op seguro retornando True."""
    with patch("sys.platform", "linux"):
        resultado = configurar_presenca_barra_de_tarefas(12345)
        assert resultado is True


def test_configurar_presenca_barra_de_tarefas_sucesso_com_mocks():
    """Garante que os estilos WS_EX_APPWINDOW e WS_SYSMENU sejam aplicados no Windows via ctypes."""
    mock_user32 = MagicMock()
    mock_user32.GetWindowLongW.side_effect = lambda hwnd, indice: 0x0

    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._obter_user32", return_value=mock_user32):
            resultado = configurar_presenca_barra_de_tarefas(99999)

            assert resultado is True
            mock_user32.SetWindowLongW.assert_any_call(
                99999, -20, ESTILO_ESTENDIDO_APPWINDOW
            )
            mock_user32.SetWindowLongW.assert_any_call(
                99999, -16, ESTILO_MENU_SISTEMA
            )


def test_configurar_presenca_barra_de_tarefas_preserva_estilos_existentes():
    """Garante que bits de estilo pré-existentes sejam preservados usando bitwise OR."""
    mock_user32 = MagicMock()
    estilo_existente = 0x10000000  # WS_VISIBLE
    ex_existente = 0x00080000      # WS_EX_LAYERED
    
    def mock_get_long(hwnd, indice):
        if indice == -20:
            return ex_existente
        return estilo_existente

    mock_user32.GetWindowLongW.side_effect = mock_get_long

    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._obter_user32", return_value=mock_user32):
            resultado = configurar_presenca_barra_de_tarefas(123)

            assert resultado is True
            mock_user32.SetWindowLongW.assert_any_call(
                123, -20, ex_existente | ESTILO_ESTENDIDO_APPWINDOW
            )
            mock_user32.SetWindowLongW.assert_any_call(
                123, -16, estilo_existente | ESTILO_MENU_SISTEMA
            )


def test_configurar_presenca_barra_de_tarefas_trata_excecao():
    """Garante resiliência caso ocorra erro inesperado nas chamadas da API do Windows."""
    mock_user32 = MagicMock()
    mock_user32.GetWindowLongW.side_effect = RuntimeError("Falha de acesso Win32")

    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._obter_user32", return_value=mock_user32):
            resultado = configurar_presenca_barra_de_tarefas(123)
            assert resultado is False



@pytest.mark.skipif(sys.platform != "win32", reason="Requer Windows real para teste nativo com HWND")
def test_configurar_presenca_barra_de_tarefas_janela_real_windows():
    """Teste de integração nativo com HWND real no Windows."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    # Cria uma janela Win32 nativa real para teste (independente do driver offscreen do Qt)
    hwnd = user32.CreateWindowExW(
        0, "STATIC", "JanelaTeste", 0, 0, 0, 100, 100, 0, 0, 0, 0
    )
    assert hwnd != 0
    try:
        resultado = configurar_presenca_barra_de_tarefas(hwnd)
        assert resultado is True

        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = wintypes.LONG

        exstyle = user32.GetWindowLongW(hwnd, -20)
        style = user32.GetWindowLongW(hwnd, -16)

        assert bool(exstyle & ESTILO_ESTENDIDO_APPWINDOW) is True
        assert bool(style & ESTILO_MENU_SISTEMA) is True
    finally:
        user32.DestroyWindow(hwnd)


