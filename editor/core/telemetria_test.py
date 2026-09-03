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
    configurar_tratamento_excecoes_globais,
    registrar_caminho_repo_local,
    limpar_caminhos_extras_sanitizacao
)


def test_sanitizar_texto_caminhos():
    user_dir = str(Path.home())
    appdata_dir = os.environ.get("APPDATA", user_dir)
    
    texto_com_caminho = f"Erro no arquivo {appdata_dir}\\aresta\\croqui.yaml linha 42"
    sanitizado = sanitizar_texto_caminhos(texto_com_caminho)
    
    assert appdata_dir not in sanitizado
    assert "%appdata%" in sanitizado or "%userprofile%" in sanitizado


def test_sanitizar_caminho_repo_local():
    limpar_caminhos_extras_sanitizacao()
    repo_ficticio = r"D:\Projetos\EmpresaX\aresta_db"
    registrar_caminho_repo_local(repo_ficticio)

    texto = r"Carregando database em D:\Projetos\EmpresaX\aresta_db\database\croqui_mg\croqui.yaml"
    sanitizado = sanitizar_texto_caminhos(texto)

    assert "D:\\Projetos\\EmpresaX" not in sanitizado
    assert r"<aresta_db>\database\croqui_mg\croqui.yaml" in sanitizado
    limpar_caminhos_extras_sanitizacao()


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
    sucesso = inicializar_telemetria()
    assert sucesso is True
    mock_sentry.init.assert_called_once()
    
    # Verifica que chamou com before_send=sanitizar_evento_sentry
    kwargs = mock_sentry.init.call_args[1]
    assert kwargs["before_send"] == sanitizar_evento_sentry


@patch("editor.core.telemetria.sentry_sdk")
def test_registrar_contexto_croqui(mock_sentry):
    registrar_contexto_croqui(id_croqui="croqui_123", commit_base_sha="abc12345")
    mock_sentry.set_tag.assert_any_call("id_croqui", "croqui_123")
    mock_sentry.set_tag.assert_any_call("commit_base_sha", "abc12345")


@patch("editor.core.telemetria.sentry_sdk")
def test_anexar_diario_escopo(mock_sentry, tmp_path):
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
def test_anexar_arquivos_diario_no_momento_do_crash(mock_sentry, tmp_path):
    from editor.core.telemetria import _anexar_arquivos_diario_no_escopo
    mock_diario = MagicMock()
    p_pend = tmp_path / "diario_pendente.bin"
    p_pend.write_bytes(b"bytes_pendente")
    p_salv = tmp_path / "diario_salvo.bin"
    p_salv.write_bytes(b"bytes_salvo")
    mock_diario.caminho_pendente = p_pend
    mock_diario.caminho_salvo = p_salv

    mock_scope = MagicMock()
    mock_sentry.get_current_scope.return_value = mock_scope

    anexar_diario_escopo(mock_diario)
    _anexar_arquivos_diario_no_escopo()

    assert mock_scope.add_attachment.call_count == 2
    chamadas_anexos = [c[1]["filename"] for c in mock_scope.add_attachment.call_args_list]
    assert "diario_pendente.bin" in chamadas_anexos
    assert "diario_salvo.bin" in chamadas_anexos


@patch("editor.core.telemetria.sentry_sdk")
def test_registrar_breadcrumb_comando(mock_sentry):
    from editor.core.telemetria import registrar_breadcrumb_comando
    mock_cmd = MagicMock()
    mock_cmd.campo_nome = "nome"
    mock_cmd.context_path = "picos.0"
    type(mock_cmd).__name__ = "CmdAlterarPrimitivo"

    registrar_breadcrumb_comando(mock_cmd)

    mock_sentry.add_breadcrumb.assert_called_once()
    kwargs = mock_sentry.add_breadcrumb.call_args[1]
    assert kwargs["category"] == "historico"
    assert kwargs["data"]["campo"] == "nome"


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
        mock_sentry.flush.assert_called_once_with(timeout=5.0)
        mock_orig.assert_called_once()
    finally:
        sys.excepthook = original_excepthook


@patch("editor.core.telemetria.sentry_sdk")
def test_excecao_global_anexa_diario_e_envia_ao_sentry(mock_sentry, tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.core.historico import GerenciadorHistorico
    from editor.core.diario import GerenciadorDiario
    from editor.controllers.croqui_controller import CroquiController
    from editor.core.telemetria import configurar_tratamento_excecoes_globais

    croqui_proto = croqui_pb2.Croqui(id="teste_e2e_sentry", nome="Croqui Original")
    model = CroquiModel(croqui_proto)
    diario = GerenciadorDiario(tmp_path)
    historico = GerenciadorHistorico()
    historico.definir_gerenciador_diario(diario)
    controller = CroquiController(model, historico)

    mock_scope = MagicMock()
    mock_sentry.get_current_scope.return_value = mock_scope

    # Ação 1: Altera o nome
    controller.alterar_primitivo(croqui_proto, "nome", "Croqui Original", "Nome Alterado")

    # Ação 2: Adiciona crédito
    controller.adicionar_repeated(croqui_proto, "creditos", 0, "Autor Teste")

    # Verifica que o escopo do Sentry foi atualizado com o histórico de comandos
    assert mock_sentry.set_context.called
    ult_chamada = mock_sentry.set_context.call_args[0]
    assert ult_chamada[0] == "historico_comandos"
    comandos = ult_chamada[1]["comandos"]
    assert len(comandos) == 2

    # Simula ocorrência de exceção não tratada capturada pelo sys.excepthook
    mock_orig = MagicMock()
    original_excepthook = sys.excepthook
    sys.excepthook = mock_orig
    try:
        configurar_tratamento_excecoes_globais()
        exc = RuntimeError("Falha inesperada no editor")
        sys.excepthook(RuntimeError, exc, None)

        mock_sentry.capture_exception.assert_called()
        mock_sentry.flush.assert_called_with(timeout=5.0)
        assert mock_scope.add_attachment.called
    finally:
        sys.excepthook = original_excepthook


@patch("editor.core.telemetria.sentry_sdk")
def test_capturar_falha_submissao_git_proxy_fatal(mock_sentry, tmp_path):
    from editor.core.telemetria import capturar_falha_submissao, anexar_diario_escopo

    mock_diario = MagicMock()
    mock_diario.caminho_pendente = tmp_path / "pend.bin"
    mock_diario.caminho_pendente.write_bytes(b"123")
    mock_diario.caminho_salvo = tmp_path / "salv.bin"
    mock_diario.caminho_salvo.write_bytes(b"456")
    anexar_diario_escopo(mock_diario)

    mock_scope = MagicMock()
    mock_sentry.get_current_scope.return_value = mock_scope
    mock_sentry.capture_exception.return_value = "evento_123"

    erro = RuntimeError("Erro 500 no git proxy")
    user_home = str(Path.home())
    contexto = {
        "url": f"https://proxy.local/{user_home}/repo",
        "codigo_status_http": 500,
    }

    event_id = capturar_falha_submissao(
        erro=erro,
        id_croqui="setor_norte",
        etapa="push_proxy",
        categoria="git_proxy",
        contexto_extra=contexto,
    )

    assert event_id == "evento_123"
    mock_sentry.set_tag.assert_any_call("id_croqui", "setor_norte")
    mock_sentry.set_tag.assert_any_call("etapa_falha", "push_proxy")
    mock_sentry.set_tag.assert_any_call("categoria_erro", "git_proxy")
    mock_sentry.set_tag.assert_any_call("tipo_evento", "falha_publicacao_pr")
    mock_sentry.set_tag.assert_any_call("nivel_severidade", "fatal")

    mock_sentry.capture_exception.assert_called_once_with(erro)
    mock_sentry.set_context.assert_called()
    nome_ctx, dados_ctx = mock_sentry.set_context.call_args[0]
    assert nome_ctx == "detalhes_submissao"
    assert user_home not in str(dados_ctx["url"])


@patch("editor.core.telemetria.sentry_sdk")
def test_capturar_falha_submissao_autenticacao_e_rede(mock_sentry):
    from editor.core.telemetria import capturar_falha_submissao

    mock_sentry.capture_exception.return_value = "ev_auth"

    capturar_falha_submissao(
        erro=Exception("Sessão revogada"),
        id_croqui="bau",
        etapa="verificacao_auth",
        categoria="autenticacao",
    )
    mock_sentry.set_tag.assert_any_call("nivel_severidade", "error")

    capturar_falha_submissao(
        erro=Exception("DNS Timeout"),
        id_croqui="bau",
        etapa="conexao",
        categoria="rede",
    )
    mock_sentry.set_tag.assert_any_call("nivel_severidade", "warning")


def test_capturar_falha_submissao_sem_sentry():
    import editor.core.telemetria as telemetria_mod
    original_sentry = telemetria_mod.sentry_sdk
    try:
        telemetria_mod.sentry_sdk = None
        resultado = telemetria_mod.capturar_falha_submissao(
            erro=Exception("Erro"),
            id_croqui="bau",
            etapa="push",
            categoria="inesperado",
        )
        assert resultado is None
    finally:
        telemetria_mod.sentry_sdk = original_sentry


@patch("editor.core.telemetria.sentry_sdk")
def test_capturar_falha_submissao_resiliente_a_erros_internos(mock_sentry):
    from editor.core.telemetria import capturar_falha_submissao
    mock_sentry.set_tag.side_effect = RuntimeError("Falha no Sentry SDK")

    resultado = capturar_falha_submissao(
        erro=Exception("Erro original"),
        id_croqui="bau",
        etapa="push",
        categoria="git_proxy",
    )
    assert resultado is None


@patch("editor.core.telemetria.sentry_sdk")
def test_registrar_breadcrumb_submissao(mock_sentry):
    from editor.core.telemetria import registrar_breadcrumb_submissao
    user_home = str(Path.home())
    dados = {"caminho": f"{user_home}/db/croqui.yaml", "porcentagem": 40}

    registrar_breadcrumb_submissao(
        mensagem="Sincronizando arquivos",
        categoria="submissao_pr",
        dados=dados,
    )

    mock_sentry.add_breadcrumb.assert_called_once()
    kwargs = mock_sentry.add_breadcrumb.call_args[1]
    assert kwargs["category"] == "submissao_pr"
    assert kwargs["message"] == "Sincronizando arquivos"
    assert user_home not in str(kwargs["data"]["caminho"])

