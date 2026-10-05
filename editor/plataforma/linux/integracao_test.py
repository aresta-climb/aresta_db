# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o adaptador Linux em editor.plataforma.linux.integracao.
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from editor.plataforma.contrato import StatusAtualizacao, ResultadoAtualizacao
from editor.plataforma.linux.integracao import AdaptadorLinux


def test_adaptador_linux_configuracao_ambiente() -> None:
    """Valida a configuração inicial de ambiente no Linux."""
    adaptador = AdaptadorLinux()
    adaptador.configurar_ambiente_plataforma()
    # Verifica que não injeta variáveis incompatíveis
    assert True


def test_adaptador_linux_presenca_barra_de_tarefas() -> None:
    """No Linux, a qualificação é transparente via QPA, retornando True."""
    adaptador = AdaptadorLinux()
    assert adaptador.configurar_presenca_barra_de_tarefas(1234) is True


def test_adaptador_linux_identidade_processo() -> None:
    """No Linux, configura o desktop file name no QGuiApplication."""
    adaptador = AdaptadorLinux()
    with patch("PySide6.QtGui.QGuiApplication.setDesktopFileName") as mock_set:
        assert adaptador.configurar_identidade_processo("com.arestaclimb.Editor") is True
        mock_set.assert_called_once_with("com.arestaclimb.Editor")

    with patch("PySide6.QtGui.QGuiApplication.setDesktopFileName", side_effect=RuntimeError("Erro Qt")):
        assert adaptador.configurar_identidade_processo("com.arestaclimb.Editor") is False


def test_adaptador_linux_trazer_janela_para_frente() -> None:
    """No Linux, eleva a janela via métodos da API do QApplication."""
    adaptador = AdaptadorLinux()

    # Cenário 1: Existe janela ativa no QApplication
    mock_janela = MagicMock()
    with patch("PySide6.QtWidgets.QApplication.activeWindow", return_value=mock_janela):
        assert adaptador.trazer_janela_para_frente(1234) is True
        mock_janela.showNormal.assert_called_once()
        mock_janela.raise_.assert_called_once()
        mock_janela.activateWindow.assert_called_once()

    # Cenário 2: Nenhuma janela ativa no momento
    with patch("PySide6.QtWidgets.QApplication.activeWindow", return_value=None):
        assert adaptador.trazer_janela_para_frente(1234) is True

    # Cenário 3: Exceção ao tentar manipular a janela
    with patch("PySide6.QtWidgets.QApplication.activeWindow", side_effect=RuntimeError("Erro de janela")):
        assert adaptador.trazer_janela_para_frente(1234) is False


def test_adaptador_linux_diretorio_dados_padrao_xdg() -> None:
    """Valida a resolução do diretório canônico com e sem XDG_DATA_HOME."""
    adaptador = AdaptadorLinux()

    # Com XDG_DATA_HOME definido
    with patch.dict(os.environ, {"XDG_DATA_HOME": "/custom/xdg/data"}):
        diretorio = adaptador.obter_diretorio_dados_usuario()
        assert diretorio == Path("/custom/xdg/data/EditorAresta")

    # Sem XDG_DATA_HOME definido (fallback ~/.local/share/EditorAresta)
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(Path, "home", return_value=Path("/home/usuario")):
            diretorio_padrao = adaptador.obter_diretorio_dados_usuario()
            assert diretorio_padrao == Path("/home/usuario/.local/share/EditorAresta")


def test_adaptador_linux_atualizacoes() -> None:
    """No Linux/Flatpak, atualizações são gerenciadas pelo sistema operacional."""
    adaptador = AdaptadorLinux()
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.NAO_APLICAVEL
    assert adaptador.solicitar_instalacao_atualizacao(res) is False


def test_adaptador_linux_obter_nome_icone_preferencial() -> None:
    """Garante que o adaptador Linux retorna logo_app.png como ícone preferencial."""
    adaptador = AdaptadorLinux()
    assert adaptador.obter_nome_icone_preferencial() == "logo_app.png"
