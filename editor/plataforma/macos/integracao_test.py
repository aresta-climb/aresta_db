# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o adaptador macOS em editor.plataforma.macos.integracao.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from editor.plataforma.contrato import StatusAtualizacao
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
    with patch(
        "PySide6.QtGui.QGuiApplication.setDesktopFileName", side_effect=RuntimeError("Erro macOS")
    ):
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
    with patch(
        "PySide6.QtWidgets.QApplication.activeWindow", side_effect=RuntimeError("Erro de janela")
    ):
        assert adaptador.trazer_janela_para_frente(1234) is False


def test_adaptador_macos_diretorio_dados_usuario() -> None:
    """Valida a resolução canônica do diretório de dados ~/Library/Application Support/EditorAresta."""
    adaptador = AdaptadorMacOS()

    # Cenário 1: QStandardPaths retorna caminho
    with patch(
        "PySide6.QtCore.QStandardPaths.writableLocation",
        return_value="/Users/usuario/Library/Application Support/EditorAresta",
    ):
        caminho = adaptador.obter_diretorio_dados_usuario()
        assert caminho == Path("/Users/usuario/Library/Application Support/EditorAresta")

    # Cenário 2: QStandardPaths retorna vazio, fallback para home
    with patch("PySide6.QtCore.QStandardPaths.writableLocation", return_value=""):
        with patch.object(Path, "home", return_value=Path("/Users/usuario")):
            caminho_padrao = adaptador.obter_diretorio_dados_usuario()
            assert caminho_padrao == Path("/Users/usuario/Library/Application Support/EditorAresta")


def test_adaptador_macos_verificar_atualizacoes_obrigatoria() -> None:
    """Detecta atualização crítica remota retornando ATUALIZACAO_OBRIGATORIA."""
    xml_feed = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <item>
      <sparkle:criticalUpdate />
      <enclosure url="https://serving.arestaclimb.com/editor-macos/EditorAresta-1.0.0.dmg"
                 sparkle:version="1.0.0" />
    </item>
  </channel>
</rss>
"""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = xml_feed
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.ATUALIZACAO_OBRIGATORIA
        assert res.versao_disponivel == "1.0.0"


def test_adaptador_macos_verificar_atualizacoes_disponivel_sem_critical() -> None:
    """Detecta atualização normal remota sem criticalUpdate retornando ATUALIZACAO_DISPONIVEL."""
    xml_feed = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <item>
      <enclosure url="https://serving.arestaclimb.com/editor-macos/EditorAresta-1.0.0.dmg"
                 sparkle:version="1.0.0" />
    </item>
  </channel>
</rss>
"""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = xml_feed
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.ATUALIZACAO_DISPONIVEL
        assert res.versao_disponivel == "1.0.0"


def test_adaptador_macos_verificar_atualizacoes_sem_atualizacao() -> None:
    """Quando a versão remota for menor ou igual à local, retorna SEM_ATUALIZACAO."""
    xml_feed = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
  <channel>
    <item>
      <enclosure url="https://serving.arestaclimb.com/editor-macos/EditorAresta-0.4.0.dmg"
                 sparkle:version="0.4.0" />
    </item>
  </channel>
</rss>
"""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = xml_feed
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_verificar_atualizacoes_falha_rede() -> None:
    """Trata erros de conexão retornando SEM_ATUALIZACAO defensivamente."""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    with patch("urllib.request.urlopen", side_effect=OSError("Sem internet")):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_verificar_atualizacoes_xml_invalido() -> None:
    """Trata respostas XML corrompidas retornando SEM_ATUALIZACAO."""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<invalido>"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_verificar_atualizacoes_xml_sem_canal() -> None:
    """Trata XML sem elemento channel retornando SEM_ATUALIZACAO."""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<rss></rss>"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_verificar_atualizacoes_xml_sem_item() -> None:
    """Trata XML sem elemento item retornando SEM_ATUALIZACAO."""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<rss><channel></channel></rss>"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_verificar_atualizacoes_xml_sem_enclosure() -> None:
    """Trata XML sem elemento enclosure retornando SEM_ATUALIZACAO."""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<rss><channel><item></item></channel></rss>"
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_verificar_atualizacoes_xml_enclosure_sem_versao() -> None:
    """Trata XML com enclosure sem chave de versão retornando SEM_ATUALIZACAO."""
    adaptador = AdaptadorMacOS(versao_atual="0.4.0")
    mock_resp = MagicMock()
    mock_resp.read.return_value = (
        b'<rss><channel><item><enclosure url="teste.dmg" /></item></channel></rss>'
    )
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_macos_solicitar_instalacao_atualizacao() -> None:
    """Valida o repasse da solicitação para o módulo de integração Sparkle."""
    adaptador = AdaptadorMacOS()

    with patch("editor.plataforma.macos.sparkle.solicitar_verificacao_sparkle", return_value=True):
        assert adaptador.solicitar_instalacao_atualizacao() is True

    with patch("editor.plataforma.macos.sparkle.solicitar_verificacao_sparkle", return_value=False):
        assert adaptador.solicitar_instalacao_atualizacao() is False

    with patch(
        "editor.plataforma.macos.sparkle.solicitar_verificacao_sparkle",
        side_effect=Exception("Erro"),
    ):
        assert adaptador.solicitar_instalacao_atualizacao() is False


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
            assert adaptador.configurar_cofre_credenciais() is True
            mock_set.assert_not_called()

    # Cenário 2: Erro ao consultar backend
    with patch("keyring.get_keyring", side_effect=Exception("Erro")):
        with patch("keyring.set_keyring") as mock_set:
            assert adaptador.configurar_cofre_credenciais() is False
            mock_set.assert_not_called()

    # Cenário 3: Configuração com sucesso
    with patch("keyring.get_keyring", return_value=FailKeyring()):  # type: ignore[no-untyped-call]
        with patch("keyring.backends.macOS.Keyring", return_value=MagicMock()):
            with patch("keyring.set_keyring") as mock_set:
                assert adaptador.configurar_cofre_credenciais() is True
                mock_set.assert_called_once()

    # Cenário 4: Falha ao instanciar backend
    with patch("keyring.get_keyring", return_value=FailKeyring()):  # type: ignore[no-untyped-call]
        with patch("keyring.backends.macOS.Keyring", side_effect=Exception("Keychain erro")):
            with patch("keyring.set_keyring") as mock_set:
                assert adaptador.configurar_cofre_credenciais() is False
                mock_set.assert_not_called()

    # Cenário 5: Falha ao importar keyring
    with patch.dict("sys.modules", {"keyring": None}):
        assert adaptador.configurar_cofre_credenciais() is False


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
