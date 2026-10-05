# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a integração nativa com o Windows em editor.plataforma.windows.integracao.
"""

import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from editor.plataforma.windows.integracao import (
    configurar_presenca_barra_de_tarefas,
    configurar_identidade_processo_windows,
    trazer_janela_para_frente,
    _esta_executando_em_pacote_msix,
    AdaptadorWindows,
    ESTILO_ESTENDIDO_APPWINDOW,
    ESTILO_MENU_SISTEMA,
)
from editor.plataforma.contrato import StatusAtualizacao, ResultadoAtualizacao


def test_configurar_presenca_barra_de_tarefas_no_op_fora_do_windows() -> None:
    """Garante que em plataformas não-Windows opere como no-op seguro retornando True."""
    with patch("sys.platform", "linux"):
        assert configurar_presenca_barra_de_tarefas(12345) is True


def test_configurar_presenca_barra_de_tarefas_sucesso_com_mocks() -> None:
    """Garante que os estilos WS_EX_APPWINDOW e WS_SYSMENU sejam aplicados no Windows via ctypes."""
    mock_user32 = MagicMock()
    mock_user32.GetWindowLongW.side_effect = lambda hwnd, indice: 0x0

    with patch("sys.platform", "win32"):
        with patch("editor.plataforma.windows.integracao._obter_user32", return_value=mock_user32):
            resultado = configurar_presenca_barra_de_tarefas(99999)
            assert resultado is True
            mock_user32.SetWindowLongW.assert_any_call(99999, -20, ESTILO_ESTENDIDO_APPWINDOW)
            mock_user32.SetWindowLongW.assert_any_call(99999, -16, ESTILO_MENU_SISTEMA)


def test_configurar_presenca_barra_de_tarefas_preserva_estilos_existentes() -> None:
    """Garante que bits de estilo pré-existentes sejam preservados usando bitwise OR."""
    mock_user32 = MagicMock()
    ex_existente = 0x00080000
    estilo_existente = 0x10000000

    def mock_get_long(hwnd: int, indice: int) -> int:
        if indice == -20:
            return ex_existente
        return estilo_existente

    mock_user32.GetWindowLongW.side_effect = mock_get_long

    with patch("sys.platform", "win32"):
        with patch("editor.plataforma.windows.integracao._obter_user32", return_value=mock_user32):
            resultado = configurar_presenca_barra_de_tarefas(123)
            assert resultado is True
            mock_user32.SetWindowLongW.assert_any_call(
                123, -20, ex_existente | ESTILO_ESTENDIDO_APPWINDOW
            )
            mock_user32.SetWindowLongW.assert_any_call(
                123, -16, estilo_existente | ESTILO_MENU_SISTEMA
            )


def test_configurar_presenca_barra_de_tarefas_trata_excecao() -> None:
    """Garante resiliência caso ocorra erro inesperado nas chamadas da API do Windows."""
    mock_user32 = MagicMock()
    mock_user32.GetWindowLongW.side_effect = RuntimeError("Falha de acesso Win32")

    with patch("sys.platform", "win32"):
        with patch("editor.plataforma.windows.integracao._obter_user32", return_value=mock_user32):
            assert configurar_presenca_barra_de_tarefas(123) is False


def test_configurar_identidade_processo_windows_fora_do_windows() -> None:
    """Garante que em plataformas não-Windows opere como no-op retornando True."""
    with patch("sys.platform", "linux"):
        assert configurar_identidade_processo_windows("aresta.editor.v1") is True


def test_configurar_identidade_processo_windows_em_pacote_msix() -> None:
    """Garante que não sobrescreva o AppUserModelID se já estiver executando dentro de pacote MSIX."""
    with patch("sys.platform", "win32"):
        with patch(
            "editor.plataforma.windows.integracao._esta_executando_em_pacote_msix",
            return_value=True,
        ):
            with patch("ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID") as mock_set:
                assert configurar_identidade_processo_windows("aresta.editor.v1") is True
                mock_set.assert_not_called()


def test_configurar_identidade_processo_windows_standalone_ou_python() -> None:
    """Garante que defina o AppUserModelID quando executando fora de pacote MSIX."""
    with patch("sys.platform", "win32"):
        with patch(
            "editor.plataforma.windows.integracao._esta_executando_em_pacote_msix",
            return_value=False,
        ):
            with patch(
                "ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID", return_value=0
            ) as mock_set:
                assert configurar_identidade_processo_windows("aresta.editor.v1") is True
                mock_set.assert_called_once_with("aresta.editor.v1")


def test_configurar_identidade_processo_windows_trata_excecao() -> None:
    """Garante que falhas na API do Windows sejam tratadas e retornem False."""
    with patch("sys.platform", "win32"):
        with patch(
            "editor.plataforma.windows.integracao._esta_executando_em_pacote_msix",
            side_effect=RuntimeError("Falha DLL"),
        ):
            assert configurar_identidade_processo_windows("aresta.editor.v1") is False


def test_esta_executando_em_pacote_msix_fora_do_windows() -> None:
    """Garante que a detecção de pacote MSIX retorne False fora do Windows."""
    with patch("sys.platform", "linux"):
        assert _esta_executando_em_pacote_msix() is False


def test_esta_executando_em_pacote_msix_trata_excecao() -> None:
    """Garante que falha em chamada ctypes no Windows retorne False com resiliência."""
    with patch("sys.platform", "win32"):
        with patch(
            "ctypes.windll.kernel32.GetCurrentPackageFamilyName",
            side_effect=RuntimeError("Falha DLL"),
        ):
            assert _esta_executando_em_pacote_msix() is False


def test_trazer_janela_para_frente_no_op_fora_do_windows() -> None:
    """Garante que fora do Windows seja um no-op seguro retornando True."""
    with patch("sys.platform", "linux"):
        assert trazer_janela_para_frente(12345) is True


def test_trazer_janela_para_frente_sucesso_com_mocks() -> None:
    """Garante que ShowWindow e SetForegroundWindow sejam invocados com o HWND."""
    mock_user32 = MagicMock()
    with patch("sys.platform", "win32"):
        with patch("editor.plataforma.windows.integracao._obter_user32", return_value=mock_user32):
            assert trazer_janela_para_frente(98765) is True
            mock_user32.ShowWindow.assert_called_once_with(98765, 9)
            mock_user32.SetForegroundWindow.assert_called_once_with(98765)


def test_trazer_janela_para_frente_trata_excecao() -> None:
    """Garante resiliência caso ocorra falha ao invocar APIs do Win32."""
    mock_user32 = MagicMock()
    mock_user32.ShowWindow.side_effect = RuntimeError("Falha ao restaurar")
    with patch("sys.platform", "win32"):
        with patch("editor.plataforma.windows.integracao._obter_user32", return_value=mock_user32):
            assert trazer_janela_para_frente(98765) is False


def test_adaptador_windows_metodos() -> None:
    """Valida as chamadas do AdaptadorWindows aos serviços subjacentes."""
    mock_loja = MagicMock()
    mock_loja.verificar_atualizacoes_disponiveis.return_value = ResultadoAtualizacao(
        status=StatusAtualizacao.SEM_ATUALIZACAO
    )
    mock_loja.solicitar_instalacao_atualizacao.return_value = True

    adaptador = AdaptadorWindows(servico_loja=mock_loja)

    # Teste configurar_ambiente_plataforma
    with patch.dict(os.environ, {}, clear=True):
        with patch("sys.platform", "win32"):
            adaptador.configurar_ambiente_plataforma()
            assert os.environ.get("QT_QPA_PLATFORM") == "windows:darkmode=0"

    with patch.dict(os.environ, {}, clear=True):
        with patch("sys.platform", "linux"):
            adaptador.configurar_ambiente_plataforma()
            assert "QT_QPA_PLATFORM" not in os.environ

    # Teste configurar_presenca_barra_de_tarefas
    with patch(
        "editor.plataforma.windows.integracao.configurar_presenca_barra_de_tarefas",
        return_value=True,
    ) as mock_cfg:
        assert adaptador.configurar_presenca_barra_de_tarefas(10) is True
        mock_cfg.assert_called_once_with(10)

    # Teste configurar_identidade_processo
    with patch(
        "editor.plataforma.windows.integracao.configurar_identidade_processo_windows",
        return_value=True,
    ) as mock_id:
        assert adaptador.configurar_identidade_processo("aresta.app") is True
        mock_id.assert_called_once_with("aresta.app")

    # Teste trazer_janela_para_frente
    with patch(
        "editor.plataforma.windows.integracao.trazer_janela_para_frente", return_value=True
    ) as mock_frente:
        assert adaptador.trazer_janela_para_frente(10) is True
        mock_frente.assert_called_once_with(10)

    # Teste obter_diretorio_dados_usuario
    diretorio = adaptador.obter_diretorio_dados_usuario()
    assert isinstance(diretorio, Path)

    # Teste fallback quando QStandardPaths retorna vazio
    with patch(
        "PySide6.QtCore.QStandardPaths.writableLocation", return_value=""
    ):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Teste\\AppData\\Roaming"}):
            dir_appdata = adaptador.obter_diretorio_dados_usuario()
            assert dir_appdata == Path("C:\\Users\\Teste\\AppData\\Roaming") / "EditorAresta"

        with patch.dict(os.environ, {"USERPROFILE": "C:\\Users\\Teste"}, clear=True):
            dir_sem_appdata = adaptador.obter_diretorio_dados_usuario()
            assert "EditorAresta" in str(dir_sem_appdata)

    # Teste delegacao para ServicoLoja
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.SEM_ATUALIZACAO
    mock_loja.verificar_atualizacoes_disponiveis.assert_called_once()

    assert adaptador.solicitar_instalacao_atualizacao(res) is True
    mock_loja.solicitar_instalacao_atualizacao.assert_called_once_with(res)


def test_obter_user32_execucao_real() -> None:
    """Valida a obtenção e configuração real de tipos da biblioteca user32 no Windows."""
    from editor.plataforma.windows.integracao import _obter_user32

    if sys.platform == "win32":
        u32 = _obter_user32()
        assert u32 is not None


def test_esta_executando_em_pacote_msix_execucao_real() -> None:
    """Valida a execução de _esta_executando_em_pacote_msix no Windows."""
    if sys.platform == "win32":
        resultado = _esta_executando_em_pacote_msix()
        assert isinstance(resultado, bool)


def test_adaptador_windows_obter_nome_icone_preferencial() -> None:
    """Garante que o adaptador Windows retorna logo.ico como ícone preferencial."""
    adaptador = AdaptadorWindows()
    assert adaptador.obter_nome_icone_preferencial() == "logo.ico"

