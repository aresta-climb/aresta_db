# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o adaptador macOS em editor.plataforma.macos.integracao.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
from editor.plataforma.contrato import StatusAtualizacao, ResultadoAtualizacao
from editor.plataforma.macos.integracao import AdaptadorMacOS


def test_adaptador_macos_configuracao_ambiente() -> None:
    """Valida a configuração inicial de ambiente no macOS."""
    adaptador = AdaptadorMacOS()
    adaptador.configurar_ambiente_plataforma()
    assert True


def test_adaptador_macos_presenca_barra_de_tarefas() -> None:
    """No macOS, a presença na Dock e alternador é gerenciada nativamente."""
    adaptador = AdaptadorMacOS()
    assert adaptador.configurar_presenca_barra_de_tarefas(1234) is True


def test_adaptador_macos_identidade_processo() -> None:
    """Valida a configuração de identidade do processo no macOS."""
    adaptador = AdaptadorMacOS()
    assert adaptador.configurar_identidade_processo("com.arestaclimb.Editor") is True

    # Teste de cenário de erro defensivo
    with patch("PySide6.QtGui.QGuiApplication.setDesktopFileName", side_effect=RuntimeError("Erro macOS")):
        assert adaptador.configurar_identidade_processo("com.arestaclimb.Editor") is False


def test_adaptador_macos_trazer_janela_para_frente() -> None:
    """No macOS, eleva a janela via APIs padrão do Qt."""
    adaptador = AdaptadorMacOS()

    # Cenário 1: Janela ativa presente
    mock_janela = MagicMock()
    with patch("PySide6.QtWidgets.QApplication.activeWindow", return_value=mock_janela):
        assert adaptador.trazer_janela_para_frente(1234) is True
        mock_janela.showNormal.assert_called_once()
        mock_janela.raise_.assert_called_once()
        mock_janela.activateWindow.assert_called_once()

    # Cenário 2: Sem janela ativa
    with patch("PySide6.QtWidgets.QApplication.activeWindow", return_value=None):
        assert adaptador.trazer_janela_para_frente(1234) is True

    # Cenário 3: Exceção durante elevação
    with patch("PySide6.QtWidgets.QApplication.activeWindow", side_effect=RuntimeError("Erro de janela")):
        assert adaptador.trazer_janela_para_frente(1234) is False


def test_adaptador_macos_diretorio_dados_usuario() -> None:
    """Valida a resolução canônica do diretório de dados ~/Library/Application Support/EditorAresta."""
    adaptador = AdaptadorMacOS()

    # Cenário 1: QStandardPaths retorna caminho
    with patch("PySide6.QtCore.QStandardPaths.writableLocation", return_value="/Users/usuario/Library/Application Support/EditorAresta"):
        caminho = adaptador.obter_diretorio_dados_usuario()
        assert caminho == Path("/Users/usuario/Library/Application Support/EditorAresta")

    # Cenário 2: QStandardPaths retorna vazio, fallback para home
    with patch("PySide6.QtCore.QStandardPaths.writableLocation", return_value=""):
        with patch.object(Path, "home", return_value=Path("/Users/usuario")):
            caminho_padrao = adaptador.obter_diretorio_dados_usuario()
            assert caminho_padrao == Path("/Users/usuario/Library/Application Support/EditorAresta")


def test_adaptador_macos_atualizacoes() -> None:
    """Valida a checagem e instalação de atualizações no macOS."""
    adaptador = AdaptadorMacOS()
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.SEM_ATUALIZACAO
    assert adaptador.solicitar_instalacao_atualizacao(res) is False


def test_adaptador_macos_obter_nome_icone_preferencial() -> None:
    """Garante que o adaptador macOS retorna logo.icns como ícone preferencial."""
    adaptador = AdaptadorMacOS()
    assert adaptador.obter_nome_icone_preferencial() == "logo.icns"


def test_adaptador_macos_configurar_cofre_credenciais() -> None:
    """Valida a configuração do cofre de credenciais no macOS (sucesso, já válido e falha)."""
    from keyring.backends.fail import Keyring as FailKeyring

    adaptador = AdaptadorMacOS()

    # Cenário 1: Já válido
    with patch("keyring.get_keyring", return_value=MagicMock()):
        with patch("keyring.set_keyring") as mock_set:
            adaptador.configurar_cofre_credenciais()
            mock_set.assert_not_called()

    # Cenário 2: Erro ao consultar backend
    with patch("keyring.get_keyring", side_effect=Exception("Erro")):
        with patch("keyring.set_keyring") as mock_set:
            adaptador.configurar_cofre_credenciais()
            mock_set.assert_not_called()

    # Cenário 3: Configuração com sucesso
    with patch("keyring.get_keyring", return_value=FailKeyring()):
        with patch("keyring.backends.macOS.Keyring", return_value=MagicMock()):
            with patch("keyring.set_keyring") as mock_set:
                adaptador.configurar_cofre_credenciais()
                mock_set.assert_called_once()

    # Cenário 4: Falha ao instanciar backend
    with patch("keyring.get_keyring", return_value=FailKeyring()):
        with patch("keyring.backends.macOS.Keyring", side_effect=Exception("Keychain erro")):
            with patch("keyring.set_keyring") as mock_set:
                adaptador.configurar_cofre_credenciais()
                mock_set.assert_not_called()


def test_adaptador_macos_normalizar_caminho_estendido() -> None:
    """Valida a resolução canônica de caminhos no macOS sem prefixo Win32."""
    adaptador = AdaptadorMacOS()

    assert adaptador.normalizar_caminho_estendido("") == ""

    caminho = "/tmp/croqui/imagem.png"
    resultado = adaptador.normalizar_caminho_estendido(caminho)
    assert not resultado.startswith("\\\\?\\")
    assert resultado == str(Path(caminho).resolve())

    # Path object
    resultado_path = adaptador.normalizar_caminho_estendido(Path(caminho))
    assert resultado_path == str(Path(caminho).resolve())
