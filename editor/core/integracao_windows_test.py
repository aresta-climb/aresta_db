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


def test_configurar_identidade_processo_windows_fora_do_windows():
    """Garante que em plataformas não-Windows opere como no-op retornando True."""
    from editor.core.integracao_windows import configurar_identidade_processo_windows

    with patch("sys.platform", "linux"):
        resultado = configurar_identidade_processo_windows("aresta.editor.v1")
        assert resultado is True


def test_configurar_identidade_processo_windows_em_pacote_msix():
    """Garante que não sobrescreva o AppUserModelID se já estiver executando dentro de pacote MSIX."""
    from editor.core.integracao_windows import configurar_identidade_processo_windows

    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._esta_executando_em_pacote_msix", return_value=True):
            with patch("ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID") as mock_set_id:
                resultado = configurar_identidade_processo_windows("aresta.editor.v1")
                assert resultado is True
                mock_set_id.assert_not_called()


def test_configurar_identidade_processo_windows_standalone_ou_python():
    """Garante que defina o AppUserModelID quando executando fora de pacote MSIX."""
    from editor.core.integracao_windows import configurar_identidade_processo_windows

    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._esta_executando_em_pacote_msix", return_value=False):
            with patch("ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID", return_value=0) as mock_set_id:
                resultado = configurar_identidade_processo_windows("aresta.editor.v1")
                assert resultado is True
                mock_set_id.assert_called_once_with("aresta.editor.v1")


def test_configurar_identidade_processo_windows_trata_excecao():
    """Garante que falhas na API do Windows sejam tratadas e retornem False."""
    from editor.core.integracao_windows import configurar_identidade_processo_windows

    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._esta_executando_em_pacote_msix", side_effect=RuntimeError("Falha DLL")):
            resultado = configurar_identidade_processo_windows("aresta.editor.v1")
            assert resultado is False


def test_esta_executando_em_pacote_msix_fora_do_windows():
    """Garante que a detecção de pacote MSIX retorne False fora do Windows."""
    from editor.core.integracao_windows import _esta_executando_em_pacote_msix

    with patch("sys.platform", "linux"):
        assert _esta_executando_em_pacote_msix() is False


def test_esta_executando_em_pacote_msix_trata_excecao():
    """Garante que falha em chamada ctypes no Windows retorne False com resiliência."""
    from editor.core.integracao_windows import _esta_executando_em_pacote_msix

    with patch("sys.platform", "win32"):
        with patch("ctypes.windll.kernel32.GetCurrentPackageFamilyName", side_effect=RuntimeError("Falha DLL")):
            assert _esta_executando_em_pacote_msix() is False


@pytest.mark.skipif(sys.platform != "win32", reason="Requer Windows real para teste nativo de identidade")
def test_configurar_identidade_processo_windows_real():

    """Teste de integração real no Windows sem mock."""
    from editor.core.integracao_windows import configurar_identidade_processo_windows, _esta_executando_em_pacote_msix

    # No ambiente de desenvolvimento local, não estamos em pacote MSIX
    assert _esta_executando_em_pacote_msix() is False
    resultado = configurar_identidade_processo_windows("aresta.editor.v1")
    assert resultado is True


def test_trazer_janela_para_frente_no_op_fora_do_windows():
    """Garante que fora do Windows seja um no-op seguro retornando True."""
    from editor.core.integracao_windows import trazer_janela_para_frente

    with patch("sys.platform", "linux"):
        assert trazer_janela_para_frente(12345) is True


def test_trazer_janela_para_frente_sucesso_com_mocks():
    """Garante que ShowWindow (SW_RESTORE=9) e SetForegroundWindow sejam invocados com o HWND."""
    from editor.core.integracao_windows import trazer_janela_para_frente

    mock_user32 = MagicMock()
    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._obter_user32", return_value=mock_user32):
            resultado = trazer_janela_para_frente(98765)
            assert resultado is True
            mock_user32.ShowWindow.assert_called_once_with(98765, 9)
            mock_user32.SetForegroundWindow.assert_called_once_with(98765)


def test_trazer_janela_para_frente_trata_excecao():
    """Garante resiliência caso ocorra falha ao invocar APIs do Win32."""
    from editor.core.integracao_windows import trazer_janela_para_frente

    mock_user32 = MagicMock()
    mock_user32.ShowWindow.side_effect = RuntimeError("Falha ao restaurar")
    with patch("sys.platform", "win32"):
        with patch("editor.core.integracao_windows._obter_user32", return_value=mock_user32):
            resultado = trazer_janela_para_frente(98765)
            assert resultado is False


@pytest.mark.skipif(sys.platform != "win32", reason="Requer Windows real para teste nativo com HWND")
def test_trazer_janela_para_frente_janela_real_windows():
    """Teste de integração real no Windows trazendo janela Win32 para o primeiro plano."""
    from editor.core.integracao_windows import trazer_janela_para_frente
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = user32.CreateWindowExW(
        0, "STATIC", "JanelaTesteFrente", 0, 0, 0, 100, 100, 0, 0, 0, 0
    )
    assert hwnd != 0
    try:
        resultado = trazer_janela_para_frente(hwnd)
        assert resultado is True
    finally:
        user32.DestroyWindow(hwnd)




