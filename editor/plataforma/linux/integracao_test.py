# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o adaptador Linux em editor.plataforma.linux.integracao.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from editor.plataforma.contrato import StatusAtualizacao
from editor.plataforma.linux.integracao import AdaptadorLinux


def test_adaptador_linux_configuracao_ambiente() -> None:
    """Valida a configuração inicial de ambiente no Linux definindo XKB_LOG_LEVEL=critical."""
    adaptador = AdaptadorLinux()

    # Caso 1: XKB_LOG_LEVEL ausente, deve definir como critical
    with patch.dict(os.environ, {}, clear=True):
        adaptador.configurar_ambiente_plataforma()
        assert os.environ.get("XKB_LOG_LEVEL") == "critical"

    # Caso 2: XKB_LOG_LEVEL já previamente definido, deve preservar (comportamento de setdefault)
    with patch.dict(os.environ, {"XKB_LOG_LEVEL": "debug"}, clear=True):
        adaptador.configurar_ambiente_plataforma()
        assert os.environ.get("XKB_LOG_LEVEL") == "debug"


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

    with patch(
        "PySide6.QtGui.QGuiApplication.setDesktopFileName", side_effect=RuntimeError("Erro Qt")
    ):
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
    with patch(
        "PySide6.QtWidgets.QApplication.activeWindow", side_effect=RuntimeError("Erro de janela")
    ):
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


def test_adaptador_linux_verificar_atualizacoes_disponivel_opcional() -> None:
    """Verifica detecção de nova versão opcional via version.json remoto."""
    adaptador = AdaptadorLinux()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"versao": "0.5.0", "obrigatoria": False}

    with patch("editor.core.version.VERSION", "0.4.9"):
        with patch("requests.get", return_value=mock_resp) as mock_get:
            res = adaptador.verificar_atualizacoes_disponiveis()
            assert res.status == StatusAtualizacao.ATUALIZACAO_DISPONIVEL
            assert res.versao_disponivel == "0.5.0"
            assert res.obrigatoria is False
            mock_get.assert_called_once_with(
                "https://serving.arestaclimb.com/flatpak/version.json", timeout=3
            )


def test_adaptador_linux_verificar_atualizacoes_obrigatoria() -> None:
    """Verifica detecção de nova versão mandatória via version.json remoto."""
    adaptador = AdaptadorLinux()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"versao": "1.0.0", "obrigatoria": True}

    with patch("editor.core.version.VERSION", "0.4.9"):
        with patch("requests.get", return_value=mock_resp):
            res = adaptador.verificar_atualizacoes_disponiveis()
            assert res.status == StatusAtualizacao.ATUALIZACAO_OBRIGATORIA
            assert res.versao_disponivel == "1.0.0"
            assert res.obrigatoria is True


def test_adaptador_linux_verificar_atualizacoes_mesma_versao() -> None:
    """Quando a versão local for igual à versão remota, não há atualização."""
    adaptador = AdaptadorLinux()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"versao": "0.4.9", "obrigatoria": True}

    with patch("editor.core.version.VERSION", "0.4.9"):
        with patch("requests.get", return_value=mock_resp):
            res = adaptador.verificar_atualizacoes_disponiveis()
            assert res.status == StatusAtualizacao.SEM_ATUALIZACAO


def test_adaptador_linux_verificar_atualizacoes_falha_de_rede() -> None:
    """Falha de rede na consulta retorna ERRO_CHECAGEM sem lançar exceção não tratada."""
    import requests

    adaptador = AdaptadorLinux()
    with patch("requests.get", side_effect=requests.RequestException("Timeout")):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.ERRO_CHECAGEM


def test_adaptador_linux_verificar_atualizacoes_status_http_invalido() -> None:
    """Resposta HTTP diferente de 200 retorna ERRO_CHECAGEM."""
    adaptador = AdaptadorLinux()
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("requests.get", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.ERRO_CHECAGEM


def test_adaptador_linux_verificar_atualizacoes_versao_vazia() -> None:
    """JSON retornado sem campo de versão válido resulta em ERRO_CHECAGEM."""
    adaptador = AdaptadorLinux()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"versao": "  "}

    with patch("requests.get", return_value=mock_resp):
        res = adaptador.verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.ERRO_CHECAGEM


def test_adaptador_linux_solicitar_instalacao_atualizacao() -> None:
    """No Linux, solicitar_instalacao_atualizacao retorna False por enquanto."""
    adaptador = AdaptadorLinux()
    assert adaptador.solicitar_instalacao_atualizacao(None) is False


def test_adaptador_linux_obter_nome_icone_preferencial() -> None:
    """Garante que o adaptador Linux retorna logo_app.png como ícone preferencial."""
    adaptador = AdaptadorLinux()
    assert adaptador.obter_nome_icone_preferencial() == "logo_app.png"


def test_adaptador_linux_configurar_cofre_credenciais_portal_disponivel_sucesso() -> None:
    """Valida que o PortalKeyring é configurado prioritariamente quando o portal está disponível."""
    from editor.plataforma.linux.portal_keyring import PortalKeyring

    adaptador = AdaptadorLinux()
    backend_inicial = MagicMock()
    with patch.object(PortalKeyring, "is_available", return_value=True):
        with patch.object(PortalKeyring, "get_master_key", return_value=b"1" * 32):
            with patch("keyring.get_keyring", return_value=backend_inicial):
                with patch("keyring.set_keyring") as mock_set:
                    assert adaptador.configurar_cofre_credenciais() is True
                    mock_set.assert_called_once()
                    instancia_registrada = mock_set.call_args[0][0]
                    assert isinstance(instancia_registrada, PortalKeyring)


def test_adaptador_linux_configurar_cofre_credenciais_portal_ja_configurado() -> None:
    """Valida que se o PortalKeyring já estiver ativo, não é reconfigurado desnecessariamente."""
    from editor.plataforma.linux.portal_keyring import PortalKeyring

    adaptador = AdaptadorLinux()
    portal_ativo = PortalKeyring(storage_path=Path("/fake/k.enc"))
    with patch.object(PortalKeyring, "is_available", return_value=True):
        with patch.object(portal_ativo, "get_master_key", return_value=b"1" * 32):
            with patch("keyring.get_keyring", return_value=portal_ativo):
                with patch("keyring.set_keyring") as mock_set:
                    assert adaptador.configurar_cofre_credenciais() is True
                    mock_set.assert_not_called()


def test_adaptador_linux_configurar_cofre_credenciais_portal_trancado_retorna_false() -> None:
    """Valida que quando o PortalKeyring estiver ativo mas o cofre trancado, retorna False."""
    from editor.plataforma.linux.portal_keyring import PortalKeyring

    adaptador = AdaptadorLinux()
    backend_inicial = MagicMock()
    with patch.object(PortalKeyring, "is_available", return_value=True):
        with patch.object(PortalKeyring, "get_master_key", side_effect=Exception("Keyring locked")):
            with patch("keyring.get_keyring", return_value=backend_inicial):
                with patch("keyring.set_keyring"):
                    assert adaptador.configurar_cofre_credenciais() is False


def test_adaptador_linux_configurar_cofre_credenciais_portal_erro_faz_fallback() -> None:
    """Valida que erro na checagem do PortalKeyring faz fallback gracioso para os outros backends."""
    from keyring.backends.fail import Keyring as FailKeyring

    adaptador = AdaptadorLinux()
    with patch(
        "editor.plataforma.linux.portal_keyring.PortalKeyring.is_available",
        side_effect=RuntimeError("Erro D-Bus"),
    ):
        with patch("keyring.get_keyring", return_value=FailKeyring()):
            with patch("keyring.backends.SecretService.Keyring") as mock_secret_service:
                with patch("keyring.set_keyring") as mock_set:
                    assert adaptador.configurar_cofre_credenciais() is True
                    mock_secret_service.assert_called_once()
                    mock_set.assert_called_once()


def test_adaptador_linux_configurar_cofre_credenciais_ja_valido() -> None:
    """Valida que backend válido já existente não é sobrescrito quando o portal está indisponível."""
    adaptador = AdaptadorLinux()
    backend_valido = MagicMock()
    with patch(
        "editor.plataforma.linux.portal_keyring.PortalKeyring.is_available", return_value=False
    ):
        with patch("keyring.get_keyring", return_value=backend_valido):
            with patch("keyring.set_keyring") as mock_set:
                assert adaptador.configurar_cofre_credenciais() is True
                mock_set.assert_not_called()


def test_adaptador_linux_configurar_cofre_credenciais_trata_excecao() -> None:
    """Valida tratamento seguro caso ocorra falha de importação do keyring."""
    adaptador = AdaptadorLinux()
    with patch.dict("sys.modules", {"keyring": None}):
        assert adaptador.configurar_cofre_credenciais() is False


def test_adaptador_linux_configurar_cofre_credenciais_get_keyring_lanca_excecao() -> None:
    """Valida tratamento seguro caso get_keyring lance exceção após checagem de portal."""
    adaptador = AdaptadorLinux()
    with patch(
        "editor.plataforma.linux.portal_keyring.PortalKeyring.is_available", return_value=False
    ):
        with patch(
            "keyring.get_keyring", side_effect=RuntimeError("Falha de introspecção do keyring")
        ):
            with patch("keyring.set_keyring") as mock_set:
                assert adaptador.configurar_cofre_credenciais() is False
                mock_set.assert_not_called()


def test_adaptador_linux_configurar_cofre_credenciais_secretservice_sucesso() -> None:
    """Valida configuração automática de SecretService quando o portal está indisponível."""
    from keyring.backends.fail import Keyring as FailKeyring

    adaptador = AdaptadorLinux()
    with patch(
        "editor.plataforma.linux.portal_keyring.PortalKeyring.is_available", return_value=False
    ):
        with patch("keyring.get_keyring", return_value=FailKeyring()):
            with patch("keyring.set_keyring") as mock_set:
                assert adaptador.configurar_cofre_credenciais() is True
                mock_set.assert_called_once()


def test_adaptador_linux_configurar_cofre_credenciais_secretservice_falha_tenta_kwallet() -> None:
    """Valida fallback para kwallet caso Portal e SecretService falhem."""
    from keyring.backends.fail import Keyring as FailKeyring

    adaptador = AdaptadorLinux()
    with patch(
        "editor.plataforma.linux.portal_keyring.PortalKeyring.is_available", return_value=False
    ):
        with patch("keyring.get_keyring", return_value=FailKeyring()):
            with patch(
                "keyring.backends.SecretService.Keyring",
                side_effect=Exception("SecretService ausente"),
            ):
                with patch("keyring.backends.kwallet.DBusKeyring", return_value=MagicMock()):
                    with patch("keyring.set_keyring") as mock_set:
                        assert adaptador.configurar_cofre_credenciais() is True
                        mock_set.assert_called_once()


def test_adaptador_linux_configurar_cofre_credenciais_ambos_falham() -> None:
    """Valida que falha em todos os backends no Linux é tratada silenciosamente."""
    from keyring.backends.fail import Keyring as FailKeyring

    adaptador = AdaptadorLinux()
    with patch(
        "editor.plataforma.linux.portal_keyring.PortalKeyring.is_available", return_value=False
    ):
        with patch("keyring.get_keyring", return_value=FailKeyring()):
            with patch("keyring.backends.SecretService.Keyring", side_effect=Exception("Falha 1")):
                with patch(
                    "keyring.backends.kwallet.DBusKeyring", side_effect=Exception("Falha 2")
                ):
                    with patch("keyring.set_keyring") as mock_set:
                        assert adaptador.configurar_cofre_credenciais() is False
                        mock_set.assert_not_called()


def test_adaptador_linux_normalizar_caminho_estendido() -> None:
    """Valida a resolução canônica de caminhos no Linux sem prefixo Win32."""
    adaptador = AdaptadorLinux()

    assert adaptador.normalizar_caminho_estendido("") == ""

    caminho = "/tmp/croqui/imagem.png"
    resultado = adaptador.normalizar_caminho_estendido(caminho)
    assert not resultado.startswith("\\\\?\\")
    assert resultado == str(Path(caminho).resolve())

    # Path object
    resultado_path = adaptador.normalizar_caminho_estendido(Path(caminho))
    assert resultado_path == str(Path(caminho).resolve())
