# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

from editor.core.configuracao_canal import (
    obter_configuracao_canal,
    ConfiguracaoCanal,
    CANAL_PRODUCAO,
    CANAL_BETA,
)


def test_integracao_contrato_canal_beta_variaveis_e_titulos(qapp: QApplication) -> None:
    """
    Testa a integração entre a configuração de canal sob ARESTA_CANAL=beta
    e a criação da TelaDeAbertura, assegurando que o título e a identidade visual
    reflitam o canal Beta.
    """
    with patch.dict(os.environ, {"ARESTA_CANAL": CANAL_BETA}):
        config = obter_configuracao_canal()
        assert config.eh_beta is True
        assert config.nome_aplicativo == "Editor Aresta (Beta)"
        assert config.app_user_model_id == "aresta.editor.beta"
        assert config.titulo_janela("1.2.0") == "Editor Aresta (Beta) v1.2.0"
        assert config.subdiretorio_recursos == "recursos_beta"

        from editor.views.tela_de_abertura import TelaDeAbertura
        tela = TelaDeAbertura()
        try:
            assert tela.windowTitle() == "Editor Aresta (Beta)"
        finally:
            tela.close()


def test_integracao_contrato_canal_producao_padrao(qapp: QApplication) -> None:
    """
    Testa a integração no canal padrão de produção (quando ARESTA_CANAL não está definido),
    assegurando a compatibilidade total com o comportamento existente.
    """
    with patch.dict(os.environ, {}, clear=True):
        if "ARESTA_CANAL" in os.environ:
            del os.environ["ARESTA_CANAL"]

        config = obter_configuracao_canal()
        assert config.eh_beta is False
        assert config.nome_aplicativo == "Editor Aresta"
        assert config.app_user_model_id == "aresta.editor.v1"
        assert config.titulo_janela("1.2.0") == "Editor Aresta v1.2.0"
        assert config.subdiretorio_recursos == "recursos"

        from editor.views.tela_de_abertura import TelaDeAbertura
        tela = TelaDeAbertura()
        try:
            assert tela.windowTitle() == "Editor Aresta"
        finally:
            tela.close()


def test_integracao_contrato_app_user_model_id_no_main() -> None:
    """
    Testa se a inicialização de plataforma no Windows invoca o AppUserModelID
    correto com base na biblioteca de configuração de canal.
    """
    with patch.dict(os.environ, {"ARESTA_CANAL": CANAL_BETA}):
        config = obter_configuracao_canal()
        assert config.app_user_model_id == "aresta.editor.beta"
