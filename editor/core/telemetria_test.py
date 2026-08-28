# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from editor.core.telemetria import (
    sanitizar_texto_caminhos,
    sanitizar_evento_sentry,
    inicializar_telemetria,
    registrar_contexto_croqui,
    anexar_diario_escopo,
    configurar_tratamento_excecoes_globais
)


def test_sanitizar_texto_caminhos():
    user_dir = str(Path.home())
    appdata_dir = os.environ.get("APPDATA", user_dir)
    
    texto_com_caminho = f"Erro no arquivo {appdata_dir}\\aresta\\croqui.yaml linha 42"
    sanitizado = sanitizar_texto_caminhos(texto_com_caminho)
    
    assert appdata_dir not in sanitizado
    assert "%appdata%" in sanitizado or "%userprofile%" in sanitizado


def test_sanitizar_evento_sentry():
    user_dir = str(Path.home())
    evento = {
        "message": f"Falha ao carregar {user_dir}\\aresta\\db",
        "exception": {
            "values": [
                {
                    "value": f"Arquivo não encontrado: {user_dir}\\aresta\\arquivo.png",
                    "stacktrace": {
                        "frames": [
                            {"filename": f"{user_dir}\\Devel\\aresta\\main.py"}
                        ]
                    }
                }
            ]
        },
        "breadcrumbs": {
            "values": [
                {"message": f"Abrindo {user_dir}\\croqui"}
            ]
        }
    }
    
    evento_limpo = sanitizar_evento_sentry(evento, hint={})
    
    assert user_dir not in evento_limpo["message"]
    assert user_dir not in evento_limpo["exception"]["values"][0]["value"]
    assert user_dir not in evento_limpo["exception"]["values"][0]["stacktrace"]["frames"][0]["filename"]
    assert user_dir not in evento_limpo["breadcrumbs"]["values"][0]["message"]


@patch("editor.core.telemetria.sentry_sdk")
def test_inicializar_telemetria(mock_sentry):
    inicializar_telemetria(dsn="https://chave@sentry.io/123")
    
    mock_sentry.init.assert_called_once()
    args, kwargs = mock_sentry.init.call_args
    assert kwargs["dsn"] == "https://chave@sentry.io/123"
    assert kwargs["send_default_pii"] is True
    assert kwargs["traces_sample_rate"] == 1.0
    assert kwargs["profile_session_sample_rate"] == 1.0
    assert callable(kwargs["before_send"])


@patch("editor.core.telemetria.sentry_sdk")
def test_registrar_contexto_croqui(mock_sentry):
    registrar_contexto_croqui(id_croqui="savassinha", commit_base_sha="abc12345")
    
    mock_sentry.set_tag.assert_any_call("id_croqui", "savassinha")
    mock_sentry.set_tag.assert_any_call("commit_base_sha", "abc12345")


@patch("editor.core.telemetria.sentry_sdk")
def test_anexar_diario_escopo(mock_sentry):
    mock_diario = MagicMock()
    mock_diario.exportar_diario_anonimizado.return_value = [
        {"classe": "CmdAlterarPrimitivo", "campo": "nome"}
    ]
    
    anexar_diario_escopo(mock_diario)
    
    mock_sentry.set_context.assert_called_once()
    nome_contexto, dados = mock_sentry.set_context.call_args[0]
    assert nome_contexto == "historico_comandos"
    assert len(dados["comandos"]) == 1


@patch("editor.core.telemetria.sentry_sdk")
def test_configurar_tratamento_excecoes_globais(mock_sentry):
    mock_orig = MagicMock()
    original_excepthook = sys.excepthook
    sys.excepthook = mock_orig
    try:
        configurar_tratamento_excecoes_globais()
        assert sys.excepthook != mock_orig
        
        # Simula chamada do sys.excepthook com dados de erro
        try:
            raise ValueError("Erro teste global")
        except ValueError as e:
            exc_info = sys.exc_info()
            sys.excepthook(*exc_info)
            
        mock_sentry.capture_exception.assert_called_once()
        mock_orig.assert_called_once()
    finally:
        sys.excepthook = original_excepthook
