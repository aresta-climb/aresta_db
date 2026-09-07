# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from pathlib import Path
from unittest.mock import patch

from editor.core.configuracao_canal import (
    obter_configuracao_canal,
    ConfiguracaoCanal,
    CANAL_PRODUCAO,
    CANAL_BETA,
)


def test_configuracao_canal_producao_explicito() -> None:
    """Valida as propriedades do canal de produção quando fornecido explicitamente."""
    config = obter_configuracao_canal(CANAL_PRODUCAO)
    assert config.eh_beta is False
    assert config.nome_canal == CANAL_PRODUCAO
    assert config.nome_aplicativo == "Editor Aresta"
    assert config.app_user_model_id == "aresta.editor.v1"
    assert config.subdiretorio_recursos == "recursos"
    assert config.titulo_janela() == "Editor Aresta"
    assert config.titulo_janela("1.0.0") == "Editor Aresta v1.0.0"


def test_configuracao_canal_beta_explicito() -> None:
    """Valida as propriedades do canal Beta quando fornecido explicitamente."""
    config = obter_configuracao_canal(CANAL_BETA)
    assert config.eh_beta is True
    assert config.nome_canal == CANAL_BETA
    assert config.nome_aplicativo == "Editor Aresta (Beta)"
    assert config.app_user_model_id == "aresta.editor.beta"
    assert config.subdiretorio_recursos == "recursos_beta"
    assert config.titulo_janela() == "Editor Aresta (Beta)"
    assert config.titulo_janela("1.2.3") == "Editor Aresta (Beta) v1.2.3"


def test_configuracao_canal_variavel_ambiente_beta() -> None:
    """Valida a resolução do canal Beta a partir da variável de ambiente ARESTA_CANAL."""
    with patch.dict(os.environ, {"ARESTA_CANAL": "BETA"}):
        config = obter_configuracao_canal()
        assert config.eh_beta is True
        assert config.nome_canal == CANAL_BETA
        assert config.nome_aplicativo == "Editor Aresta (Beta)"


def test_configuracao_canal_variavel_ambiente_ausente_ou_invalida() -> None:
    """Garante fallback seguro para produção caso a variável esteja ausente, vazia ou com valor desconhecido."""
    with patch.dict(os.environ, {}, clear=True):
        if "ARESTA_CANAL" in os.environ:
            del os.environ["ARESTA_CANAL"]
        config = obter_configuracao_canal()
        assert config.eh_beta is False
        assert config.nome_canal == CANAL_PRODUCAO

    with patch.dict(os.environ, {"ARESTA_CANAL": "desconhecido"}):
        config = obter_configuracao_canal()
        assert config.eh_beta is False
        assert config.nome_canal == CANAL_PRODUCAO


def test_configuracao_canal_obter_caminho_recurso(tmp_path: Path) -> None:
    """Testa a resolução de caminhos de recursos gráficos com suporte a diretório base."""
    dir_editor = tmp_path / "editor"
    dir_recursos_padrao = dir_editor / "recursos"
    dir_recursos_beta = dir_editor / "recursos_beta"

    dir_recursos_padrao.mkdir(parents=True)
    dir_recursos_beta.mkdir(parents=True)

    logo_padrao = dir_recursos_padrao / "logo_splash.png"
    logo_padrao.write_bytes(b"logo_laranja")

    logo_beta = dir_recursos_beta / "logo_splash.png"
    logo_beta.write_bytes(b"logo_azul")

    # Canal Beta encontra o recurso em recursos_beta
    config_beta = ConfiguracaoCanal(CANAL_BETA, diretorio_base=dir_editor)
    caminho_beta = config_beta.obter_caminho_recurso("logo_splash.png")
    assert caminho_beta == logo_beta

    # Se um recurso não existir em recursos_beta, faz fallback seguro para recursos padrão
    outro_recurso_padrao = dir_recursos_padrao / "outro.png"
    outro_recurso_padrao.write_bytes(b"outro")

    caminho_fallback = config_beta.obter_caminho_recurso("outro.png")
    assert caminho_fallback == outro_recurso_padrao

    # Canal Produção busca direto em recursos padrão
    config_prod = ConfiguracaoCanal(CANAL_PRODUCAO, diretorio_base=dir_editor)
    caminho_prod = config_prod.obter_caminho_recurso("logo_splash.png")
    assert caminho_prod == logo_padrao

    # Recurso inexistente retorna o caminho do canal
    caminho_inexistente = config_beta.obter_caminho_recurso("arquivo_inexistente.png")
    assert caminho_inexistente == dir_recursos_beta / "arquivo_inexistente.png"
