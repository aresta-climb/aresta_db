# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a fachada pública da biblioteca editor.plataforma.
"""

from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
from editor.plataforma import (
    obter_adaptador_plataforma,
    configurar_ambiente_plataforma,
    configurar_presenca_barra_de_tarefas,
    configurar_identidade_processo,
    trazer_janela_para_frente,
    obter_diretorio_dados_usuario,
    verificar_atualizacoes_disponiveis,
    solicitar_instalacao_atualizacao,
    StatusAtualizacao,
    ResultadoAtualizacao,
)


def test_obter_adaptador_plataforma_despacho() -> None:
    """Valida que o adaptador correto é retornado dependendo de sys.platform."""
    with patch("sys.platform", "win32"):
        adaptador_win = obter_adaptador_plataforma()
        assert adaptador_win is not None

    with patch("sys.platform", "linux"):
        adaptador_linux = obter_adaptador_plataforma()
        assert adaptador_linux is not None

    with patch("sys.platform", "darwin"):
        adaptador_mac = obter_adaptador_plataforma()
        assert adaptador_mac is not None


def test_funcoes_conveniencia_fachada() -> None:
    """Garante que as funções públicas no topo do módulo delegam para o adaptador ativo."""
    mock_adaptador = MagicMock()
    mock_adaptador.configurar_presenca_barra_de_tarefas.return_value = True
    mock_adaptador.configurar_identidade_processo.return_value = True
    mock_adaptador.trazer_janela_para_frente.return_value = True
    mock_adaptador.obter_diretorio_dados_usuario.return_value = Path("/tmp/teste")
    mock_adaptador.verificar_atualizacoes_disponiveis.return_value = ResultadoAtualizacao(
        status=StatusAtualizacao.SEM_ATUALIZACAO
    )
    mock_adaptador.solicitar_instalacao_atualizacao.return_value = True

    with patch("editor.plataforma.obter_adaptador_plataforma", return_value=mock_adaptador):
        configurar_ambiente_plataforma()
        mock_adaptador.configurar_ambiente_plataforma.assert_called_once()

        assert configurar_presenca_barra_de_tarefas(42) is True
        mock_adaptador.configurar_presenca_barra_de_tarefas.assert_called_once_with(42)

        assert configurar_identidade_processo("aresta.app") is True
        mock_adaptador.configurar_identidade_processo.assert_called_once_with("aresta.app")

        assert trazer_janela_para_frente(42) is True
        mock_adaptador.trazer_janela_para_frente.assert_called_once_with(42)

        assert obter_diretorio_dados_usuario() == Path("/tmp/teste")
        mock_adaptador.obter_diretorio_dados_usuario.assert_called_once()

        res = verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO
        mock_adaptador.verificar_atualizacoes_disponiveis.assert_called_once()

        assert solicitar_instalacao_atualizacao(res) is True
        mock_adaptador.solicitar_instalacao_atualizacao.assert_called_once_with(res)

        mock_adaptador.obter_nome_icone_preferencial.return_value = "logo.png"
        from editor.plataforma import obter_nome_icone_preferencial, configurar_cofre_credenciais
        assert obter_nome_icone_preferencial() == "logo.png"
        mock_adaptador.obter_nome_icone_preferencial.assert_called_once()

        configurar_cofre_credenciais()
        mock_adaptador.configurar_cofre_credenciais.assert_called_once()

        mock_adaptador.normalizar_caminho_estendido.return_value = "\\\\?\\C:\\teste"
        from editor.plataforma import normalizar_caminho_estendido
        assert normalizar_caminho_estendido("C:\\teste") == "\\\\?\\C:\\teste"
        mock_adaptador.normalizar_caminho_estendido.assert_called_once_with("C:\\teste")


def test_adaptador_padrao_fallback_completo() -> None:
    """Garante que a implementação neutra de fallback atende a todos os métodos do protocolo."""
    from editor.plataforma import _AdaptadorPadraoFallback
    adaptador = _AdaptadorPadraoFallback()

    adaptador.configurar_ambiente_plataforma()
    assert adaptador.configurar_presenca_barra_de_tarefas(1) is True
    assert adaptador.configurar_identidade_processo("app") is True
    assert adaptador.trazer_janela_para_frente(1) is True
    assert isinstance(adaptador.obter_diretorio_dados_usuario(), Path)
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.NAO_APLICAVEL
    assert adaptador.solicitar_instalacao_atualizacao() is False
    assert adaptador.obter_nome_icone_preferencial() == "logo_app.png"
    adaptador.configurar_cofre_credenciais()
    assert adaptador.normalizar_caminho_estendido("") == ""
    assert isinstance(adaptador.normalizar_caminho_estendido("teste"), str)
