# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from editor.core.telemetria import (
    anexar_diario_escopo,
    configurar_tratamento_excecoes_globais,
    inicializar_telemetria,
    limpar_caminhos_extras_sanitizacao,
    registrar_caminho_repo_local,
    registrar_contexto_croqui,
    sanitizar_evento_sentry,
    sanitizar_texto_caminhos,
)


def test_sanitizar_texto_caminhos():
    user_dir = str(Path.home())
    appdata_dir = os.environ.get("APPDATA", user_dir)

    texto_com_caminho = f"Erro no arquivo {appdata_dir}\\aresta\\croqui.yaml linha 42"
    sanitizado = sanitizar_texto_caminhos(texto_com_caminho)

    assert appdata_dir not in sanitizado
    assert "%appdata%" in sanitizado or "%userprofile%" in sanitizado


def test_sanitizar_texto_caminhos_barras_duplas_escapadas():
    user_dir = str(Path.home())
    localappdata_dir = os.environ.get("LOCALAPPDATA", user_dir)
    appdata_dir = os.environ.get("APPDATA", user_dir)

    # Simula repr() de tuplas de erro como em exceções shutil.Error
    localappdata_escapado = localappdata_dir.replace("\\", "\\\\")
    appdata_escapado = appdata_dir.replace("\\", "\\\\")

    texto_repr = (
        f"[('{localappdata_escapado}\\\\Packages\\\\App\\\\imagem.webp', "
        f"'{appdata_escapado}\\\\Editor Aresta\\\\croquis\\\\compilado\\\\imagem.webp')]"
    )

    sanitizado = sanitizar_texto_caminhos(texto_repr)

    assert localappdata_escapado not in sanitizado
    assert appdata_escapado not in sanitizado
    assert "%localappdata%" in sanitizado or "%userprofile%" in sanitizado
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
                    "stacktrace": {"frames": [{"filename": f"{user_dir}\\Devel\\aresta\\main.py"}]},
                }
            ]
        },
        "breadcrumbs": {"values": [{"message": f"Abrindo {user_dir}\\croqui"}]},
    }

    evento_limpo = sanitizar_evento_sentry(evento, hint={})

    assert user_dir not in evento_limpo["message"]
    assert user_dir not in evento_limpo["exception"]["values"][0]["value"]
    assert (
        user_dir
        not in evento_limpo["exception"]["values"][0]["stacktrace"]["frames"][0]["filename"]
    )
    assert user_dir not in evento_limpo["breadcrumbs"]["values"][0]["message"]


@patch.dict(os.environ, {"ARESTA_DESATIVAR_TELEMETRIA": "0"})
@patch("editor.core.telemetria.sentry_sdk")
def test_inicializar_telemetria(mock_sentry):
    sucesso = inicializar_telemetria()
    assert sucesso is True
    mock_sentry.init.assert_called_once()

    # Verifica que chamou com before_send=sanitizar_evento_sentry e auto_enabling_integrations=False
    kwargs = mock_sentry.init.call_args[1]
    assert kwargs["before_send"] == sanitizar_evento_sentry
    assert kwargs["auto_enabling_integrations"] is False


@patch.dict(os.environ, {"ARESTA_DESATIVAR_TELEMETRIA": "1"})
@patch("editor.core.telemetria.sentry_sdk")
def test_inicializar_telemetria_desativada_por_variavel_ambiente(mock_sentry):
    sucesso = inicializar_telemetria()
    assert sucesso is False
    mock_sentry.init.assert_not_called()


@patch("editor.core.telemetria.sentry_sdk")
def test_encerrar_telemetria(mock_sentry):
    mock_cliente = MagicMock()
    mock_sentry.get_client.return_value = mock_cliente

    from editor.core.telemetria import encerrar_telemetria

    encerrar_telemetria(timeout=1.5)

    mock_sentry.get_client.assert_called_once()
    mock_cliente.close.assert_called_once_with(timeout=1.5)


@patch("editor.core.telemetria.sentry_sdk")
def test_registrar_contexto_croqui(mock_sentry):
    registrar_contexto_croqui(id_croqui="croqui_123", commit_base_sha="abc12345")
    mock_sentry.set_tag.assert_any_call("id_croqui", "croqui_123")
    mock_sentry.set_tag.assert_any_call("commit_base_sha", "abc12345")


@patch("editor.core.telemetria.sentry_sdk")
def test_anexar_diario_escopo(mock_sentry, tmp_path):
    mock_diario = MagicMock()
    mock_diario.exportar_diario_anonimizado.return_value = [
        {"classe": "CmdAlterarCampo", "campo": "nome"}
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
    type(mock_cmd).__name__ = "CmdAlterarCampo"

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
        except ValueError:
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
    from editor.controllers.croqui_controller import CroquiController
    from editor.core.diario import GerenciadorDiario
    from editor.core.historico import GerenciadorHistorico
    from editor.core.telemetria import configurar_tratamento_excecoes_globais
    from editor.models.croqui_model import CroquiModel

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
    from editor.core.telemetria import anexar_diario_escopo, capturar_falha_submissao

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


@patch("editor.core.telemetria.sentry_sdk")
def test_capturar_excecao_envia_tags_e_flush(mock_sentry):
    from editor.core.telemetria import capturar_excecao

    mock_sentry.capture_exception.return_value = "evento_crash_123"
    erro = ValueError("Erro de validação Protobuf")

    ev_id = capturar_excecao(
        erro=erro,
        id_croqui="ouroboulder",
        etapa="tarefa_salvamento",
        contexto_extra={"caminho": str(Path.home())},
    )

    assert ev_id == "evento_crash_123"
    mock_sentry.set_tag.assert_any_call("id_croqui", "ouroboulder")
    mock_sentry.set_tag.assert_any_call("etapa_falha", "tarefa_salvamento")
    mock_sentry.capture_exception.assert_called_once_with(erro)
    mock_sentry.flush.assert_called_once()

    # Verifica sanitização do contexto extra
    mock_sentry.set_context.assert_called()
    nome_ctx, dados_ctx = mock_sentry.set_context.call_args[0]
    assert nome_ctx == "detalhes_erro"
    assert str(Path.home()) not in str(dados_ctx["caminho"])


def test_capturar_excecao_sem_sentry():
    import editor.core.telemetria as telemetria_mod

    original_sentry = telemetria_mod.sentry_sdk
    try:
        telemetria_mod.sentry_sdk = None
        assert telemetria_mod.capturar_excecao(ValueError("teste")) is None
        assert (
            telemetria_mod.capturar_crash_robo_caotico(
                ValueError("teste"), {"seed": 42, "dataset": "toxico"}
            )
            is None
        )
    finally:
        telemetria_mod.sentry_sdk = original_sentry


class _EscopoSentryEspiao:
    def __init__(self) -> None:
        self.anexos: list[dict[str, str | None]] = []

    def clear_attachments(self) -> None:
        self.anexos.clear()

    def add_attachment(
        self,
        path: str | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.anexos.append({"path": path, "filename": filename, "content_type": content_type})


class _ClienteSentryEspiao:
    def __init__(self) -> None:
        self.fechado: bool = False
        self.ultimo_timeout: float | None = None

    def close(self, timeout: float = 2.0) -> None:
        self.fechado = True
        self.ultimo_timeout = timeout


class _SentryEspiao:
    def __init__(self) -> None:
        self.inicializado: bool = False
        self.tags: dict[str, str] = {}
        self.contextos: dict[str, dict] = {}
        self.nivel: str | None = None
        self.excecoes_capturadas: list[BaseException] = []
        self.flushes: list[float] = []
        self.escopo = _EscopoSentryEspiao()
        self.cliente = _ClienteSentryEspiao()

    def init(self, **kwargs: object) -> None:
        _ = kwargs
        self.inicializado = True

    def get_current_scope(self) -> _EscopoSentryEspiao:
        return self.escopo

    def get_client(self) -> _ClienteSentryEspiao:
        return self.cliente

    def set_tag(self, chave: str, valor: str) -> None:
        self.tags[chave] = valor

    def set_context(self, nome: str, dados: dict) -> None:
        self.contextos[nome] = dados

    def set_level(self, nivel: str) -> None:
        self.nivel = nivel

    def capture_exception(self, erro: BaseException) -> str:
        self.excecoes_capturadas.append(erro)
        return "ev_robo_999"

    def flush(self, timeout: float = 2.0) -> None:
        self.flushes.append(timeout)


def test_capturar_crash_robo_caotico_anexa_receita_json_e_reabilita_telemetria(
    tmp_path: Path,
) -> None:
    import editor.core.telemetria as telemetria_mod
    import tests.bloqueador_rede as mod_rede
    from editor.core.telemetria import anexar_diario_escopo, capturar_crash_robo_caotico

    espiao = _SentryEspiao()
    original_sentry = telemetria_mod.sentry_sdk
    anexar_diario_escopo(None)
    mod_rede.bloquear_acesso_externo()
    os.environ["ARESTA_DESATIVAR_TELEMETRIA"] = "1"
    try:
        telemetria_mod.sentry_sdk = espiao
        caminho_sensivel = f"{Path.home()}\\croquis\\toxico.yaml"
        receita = {
            "seed": 4242,
            "dataset": "toxico",
            "passos_minimos": [{"acao": "digitar_fuzz", "valor_texto": caminho_sensivel}],
            "passos_originais": [{"acao": "digitar_fuzz", "valor_texto": caminho_sensivel}],
        }
        arquivo_json = tmp_path / "crash_seed_4242_runtimeerror.json"
        arquivo_json.write_text('{"seed": 4242}\n', encoding="utf-8")
        erro = RuntimeError("Crash descoberto pelo Robô Caótico")

        event_id = capturar_crash_robo_caotico(
            erro=erro,
            receita_robo_caotico=receita,
            id_croqui="croqui_toxico",
            caminho_arquivo_json=arquivo_json,
        )

        assert event_id == "ev_robo_999"
        assert espiao.inicializado is True
        assert espiao.cliente.fechado is True
        assert espiao.nivel == "fatal"
        assert espiao.tags["nivel_severidade"] == "fatal"
        assert espiao.tags["origem_crash"] == "robo_caotico"
        assert espiao.tags["id_croqui"] == "croqui_toxico"
        assert espiao.tags["etapa_falha"] == "robo_caotico"
        assert "receita_robo_caotico" in espiao.contextos
        ctx_receita = espiao.contextos["receita_robo_caotico"]
        assert ctx_receita["seed"] == 4242
        assert ctx_receita["dataset"] == "toxico"
        assert str(Path.home()) not in ctx_receita["passos_minimos"][0]["valor_texto"]
        assert espiao.excecoes_capturadas == [erro]
        assert espiao.flushes == [5.0]
        assert espiao.escopo.anexos == [
            {
                "path": str(arquivo_json),
                "filename": "crash_seed_4242_runtimeerror.json",
                "content_type": "application/json",
            }
        ]
        assert os.environ.get("ARESTA_DESATIVAR_TELEMETRIA") == "1"
        assert mod_rede._bloqueio_ativo is True
    finally:
        telemetria_mod.sentry_sdk = original_sentry


def test_sessao_continua_robo_caotico_preserva_breadcrumbs_isola_ddmin_e_anexa_json(
    tmp_path: Path,
) -> None:
    from editor.core.telemetria import (
        anexar_diario_escopo,
        ativar_sessao_sentry_robo_caotico,
        capturar_crash_robo_caotico,
        capturar_excecao,
        escopo_isolado_semente_sentry,
        escopo_silencioso_ddmin_sentry,
        registrar_breadcrumb_comando,
        sanitizar_evento_sentry,
    )

    eventos_enviados: list[tuple[dict, dict]] = []

    class _CmdFalso:
        def __init__(self, campo: str, caminho: str) -> None:
            self.campo_nome = campo
            self.context_path = caminho

    class _DiarioFalso:
        def __init__(self, pasta: Path, etiqueta: str) -> None:
            self.etiqueta = etiqueta
            self.caminho_pendente = pasta / f"pend_{etiqueta}.bin"
            self.caminho_pendente.write_bytes(b"dados_diario")
            self.caminho_salvo = pasta / f"salv_{etiqueta}.bin"

        def exportar_diario_anonimizado(self, limite_comandos: int = 50) -> list[dict[str, str]]:
            _ = limite_comandos
            return [{"etiqueta": self.etiqueta}]

    os.environ["ARESTA_DESATIVAR_TELEMETRIA"] = "1"
    with ativar_sessao_sentry_robo_caotico(dsn="https://public@example.com/1"):
        import sentry_sdk as sdk_real

        cliente = sdk_real.get_client()
        opcoes = cliente.options

        def _interceptar_before_send(event: dict, hint: dict) -> None:
            limpo = sanitizar_evento_sentry(event, hint)
            if limpo is not None:
                eventos_enviados.append((limpo, hint))
            return None

        opcoes["before_send"] = _interceptar_before_send

        with escopo_isolado_semente_sentry(seed=777, dataset="toxico", escopo="completo"):
            diario_original = _DiarioFalso(tmp_path, "semente_777")
            anexar_diario_escopo(diario_original)
            registrar_breadcrumb_comando(_CmdFalso("nome", "croqui"))
            registrar_breadcrumb_comando(_CmdFalso("altura", "picos.0"))

            # Chamada intermediária de capturar_excecao também é enviada ao Sentry em tempo real (Sentry liberado o tempo todo)
            capturar_excecao(RuntimeError("Erro intermediário em tempo real"))
            assert len(eventos_enviados) == 1

            # Replays do ddmin não devem poluir os breadcrumbs nem substituir o diário da semente original
            with escopo_silencioso_ddmin_sentry():
                diario_ddmin = _DiarioFalso(tmp_path, "ddmin_temporario")
                anexar_diario_escopo(diario_ddmin)
                registrar_breadcrumb_comando(_CmdFalso("lixo_ddmin", "setores.99"))

            arquivo_json = tmp_path / "crash_seed_777_oserror.json"
            arquivo_json.write_text('{"seed": 777}\n', encoding="utf-8")

            try:
                raise OSError(22, "Invalid argument")
            except OSError as erro_real:
                capturar_crash_robo_caotico(
                    erro=erro_real,
                    receita_robo_caotico={"seed": 777, "dataset": "toxico"},
                    id_croqui="br_sp_caos_toxico",
                    caminho_arquivo_json=arquivo_json,
                )

    assert len(eventos_enviados) == 2
    evento, hint = eventos_enviados[-1]
    mensagens_breadcrumbs = [b["message"] for b in evento["breadcrumbs"]["values"]]
    assert "_CmdFalso: nome" in mensagens_breadcrumbs
    assert "_CmdFalso: altura" in mensagens_breadcrumbs
    assert "_CmdFalso: lixo_ddmin" not in mensagens_breadcrumbs

    frames = evento["exception"]["values"][0]["stacktrace"]["frames"]
    assert len(frames) >= 1

    nomes_anexos = [a.filename for a in hint.get("attachments", [])]
    assert "crash_seed_777_oserror.json" in nomes_anexos
    assert "diario_pendente.bin" in nomes_anexos
    assert evento["contexts"]["historico_comandos"]["comandos"] == [{"etiqueta": "semente_777"}]
