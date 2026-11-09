# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import contextlib
import os
import re
import sys
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

sentry_sdk: Any
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

DSN_PADRAO = "https://a632ff22a93532930ea95f849b4a796b@o4511980548849664.ingest.us.sentry.io/4511980560515072"

_caminhos_extras_sanitizacao: list[tuple[str, str]] = []
_sessao_robo_caotico_ativa: bool = False


def registrar_caminho_repo_local(caminho_repo: Path | str) -> None:
    """
    Registra a raiz do repositório local para que qualquer caminho interno
    seja truncado e sanitizado como <aresta_db>\\... em logs e relatórios.
    """
    if not caminho_repo:
        return
    caminho_str = str(caminho_repo)
    if not (os.name != "nt" and re.match(r"^[a-zA-Z]:", caminho_str)):
        try:
            caminho_str = str(Path(caminho_repo).resolve())
        except Exception:
            pass
    if (caminho_str, "<aresta_db>") not in _caminhos_extras_sanitizacao:
        _caminhos_extras_sanitizacao.append((caminho_str, "<aresta_db>"))


def limpar_caminhos_extras_sanitizacao() -> None:
    """Limpa caminhos adicionais registrados para sanitização (útil em testes)."""
    global _caminhos_extras_sanitizacao
    _caminhos_extras_sanitizacao = []


def _obter_mapeamento_sanitizacao() -> list[tuple[str, str]]:
    """Gera lista ordenada de prefixos de caminhos locais e suas respectivas substituições anônimas."""
    mapeamentos: list[tuple[str, str]] = []

    # 1. Caminhos de repositórios locais registrados
    for caminho, substituto in _caminhos_extras_sanitizacao:
        mapeamentos.append((caminho, substituto))

    # 2. Diretório Base do Aplicativo (EditorAresta)
    try:
        from editor.core.storage import obter_diretorio_base_app

        dir_base = str(obter_diretorio_base_app())
        if dir_base:
            mapeamentos.append((dir_base, "%appdata%\\EditorAresta"))
    except Exception:
        pass

    # 3. APPDATA e LOCALAPPDATA
    appdata = os.environ.get("APPDATA")
    if appdata:
        mapeamentos.append((appdata, "%appdata%"))
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        mapeamentos.append((localappdata, "%localappdata%"))

    # 3. Diretório Home / UserProfile
    home = str(Path.home())
    if home:
        mapeamentos.append((home, "%userprofile%"))

    userprofile = os.environ.get("USERPROFILE")
    if userprofile and userprofile != home:
        mapeamentos.append((userprofile, "%userprofile%"))

    # 4. Diretório Temporário
    temp = os.environ.get("TEMP")
    if temp:
        mapeamentos.append((temp, "%temp%"))

    # Ordena pelos mais longos primeiro para substituição precisa
    mapeamentos.sort(key=lambda item: len(item[0]), reverse=True)
    return mapeamentos


def sanitizar_texto_caminhos(texto: str) -> str:
    """Substitui caminhos locais de usuários por variáveis de ambiente genéricas (%appdata%, %userprofile%, <aresta_db>, etc.)."""
    if not isinstance(texto, str) or not texto:
        return texto

    resultado = texto
    mapeamentos = _obter_mapeamento_sanitizacao()
    for caminho_original, substituto in mapeamentos:
        # Substitui versão com barras duplas escapadas (\\), barras invertidas (\) e barras normais (/)
        caminho_barras_invertidas = caminho_original.replace("/", "\\")
        caminho_barras_duplas = caminho_barras_invertidas.replace("\\", "\\\\")
        caminho_barras_normais = caminho_original.replace("\\", "/")

        substituto_barras_duplas = substituto.replace("\\", "\\\\")
        substituto_barras_normais = substituto.replace("\\", "/")

        # Helper com tipagem explícita para evitar erro de inferência em lambda
        def _fazer_subst(val_subst: str) -> Any:
            return lambda m: val_subst

        # Regex case-insensitive escapando caracteres especiais
        padrao_duplas = re.compile(re.escape(caminho_barras_duplas), re.IGNORECASE)
        resultado = padrao_duplas.sub(_fazer_subst(substituto_barras_duplas), resultado)

        padrao_inv = re.compile(re.escape(caminho_barras_invertidas), re.IGNORECASE)
        resultado = padrao_inv.sub(_fazer_subst(substituto), resultado)

        padrao_norm = re.compile(re.escape(caminho_barras_normais), re.IGNORECASE)
        resultado = padrao_norm.sub(_fazer_subst(substituto_barras_normais), resultado)

    return resultado


def _sanitizar_objeto_recursivo(obj: Any) -> Any:
    """Aplica sanitização de strings recursivamente em dicionários, listas e tuplas."""
    if isinstance(obj, str):
        return sanitizar_texto_caminhos(obj)
    if isinstance(obj, dict):
        return {k: _sanitizar_objeto_recursivo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitizar_objeto_recursivo(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitizar_objeto_recursivo(item) for item in obj)
    return obj


def sanitizar_evento_sentry(event: Any, hint: Any) -> Any:
    """Hook before_send do Sentry para sanitizar qualquer caminho local em eventos, stacktraces e breadcrumbs."""
    _ = hint
    return _sanitizar_objeto_recursivo(event)


def inicializar_telemetria(dsn: str | None = None) -> bool:
    """
    Inicializa o Sentry SDK com telemetria silenciosa automática e sanitização de dados.
    Retorna True se inicializado com sucesso.
    """
    if not sentry_sdk:
        return False

    if os.environ.get("ARESTA_DESATIVAR_TELEMETRIA") == "1":
        return False

    dsn_usado = dsn if dsn is not None else os.environ.get("SENTRY_DSN_EDITOR", DSN_PADRAO)
    if not dsn_usado:
        return False

    try:
        sentry_sdk.init(
            dsn=dsn_usado,
            send_default_pii=True,
            traces_sample_rate=1.0,
            profile_session_sample_rate=1.0,
            auto_enabling_integrations=False,
            before_send=sanitizar_evento_sentry,
        )
        if hasattr(sentry_sdk, "start_transaction"):
            try:
                with sentry_sdk.start_transaction(op="app.boot", name="InicializacaoEditor"):
                    pass
            except Exception:
                pass
        configurar_tratamento_excecoes_globais()
        return True
    except Exception:
        return False


def encerrar_telemetria(timeout: float = 2.0) -> None:
    """
    Encerra o cliente do Sentry e aguarda o término das threads de envio e monitoramento.
    """
    if not sentry_sdk:
        return
    try:
        obter_cliente = getattr(sentry_sdk, "get_client", None)
        if obter_cliente:
            cliente = obter_cliente()
            if cliente and hasattr(cliente, "close"):
                cliente.close(timeout=timeout)
    except Exception:
        pass


def registrar_contexto_croqui(id_croqui: str = "", commit_base_sha: str = "") -> None:
    """Registra tags no escopo do Sentry para rastrear o croqui em edição e a base git."""
    if not sentry_sdk:
        return
    try:
        if id_croqui:
            sentry_sdk.set_tag("id_croqui", id_croqui)
        if commit_base_sha:
            sentry_sdk.set_tag("commit_base_sha", commit_base_sha)
    except Exception:
        pass


_diario_ativo: Any = None


def anexar_diario_escopo(diario: Any) -> None:
    """Anexa os comandos recentes do diário (anonimizados) ao contexto do escopo Sentry."""
    global _diario_ativo
    _diario_ativo = diario
    if not sentry_sdk or not diario:
        return
    try:
        comandos_anon = diario.exportar_diario_anonimizado(limite_comandos=50)
        sentry_sdk.set_context("historico_comandos", {"comandos": comandos_anon})
    except Exception:
        pass


def _anexar_arquivos_diario_no_escopo(
    arquivos_extras: Sequence[Path | str] | None = None,
) -> None:
    """Anexa os arquivos .bin do diário e eventuais arquivos extras ao escopo no momento do envio do crash."""
    if not sentry_sdk or (not _diario_ativo and not arquivos_extras):
        return
    try:
        # Limpa anexos de todos os escopos do Sentry para garantir unicidade absoluta
        for obter_escopo in (
            getattr(sentry_sdk, "get_current_scope", None),
            getattr(sentry_sdk, "get_isolation_scope", None),
            getattr(sentry_sdk, "get_global_scope", None),
        ):
            if obter_escopo:
                try:
                    s = obter_escopo()
                    if s:
                        if hasattr(s, "clear_attachments"):
                            s.clear_attachments()
                        elif hasattr(s, "_attachments"):
                            s._attachments = []
                except Exception:
                    pass

        scope = (
            sentry_sdk.get_current_scope()
            if hasattr(sentry_sdk, "get_current_scope")
            else (
                getattr(getattr(sentry_sdk, "Hub", None), "current", None)
                and getattr(sentry_sdk.Hub.current, "scope", None)
            )
        )
        if scope and hasattr(scope, "add_attachment"):
            if (
                _diario_ativo
                and hasattr(_diario_ativo, "caminho_pendente")
                and _diario_ativo.caminho_pendente.exists()
                and _diario_ativo.caminho_pendente.stat().st_size > 0
            ):
                scope.add_attachment(
                    path=str(_diario_ativo.caminho_pendente), filename="diario_pendente.bin"
                )
            if (
                _diario_ativo
                and hasattr(_diario_ativo, "caminho_salvo")
                and _diario_ativo.caminho_salvo.exists()
                and _diario_ativo.caminho_salvo.stat().st_size > 0
            ):
                scope.add_attachment(
                    path=str(_diario_ativo.caminho_salvo), filename="diario_salvo.bin"
                )
            if arquivos_extras:
                for item_extra in arquivos_extras:
                    caminho_extra = Path(item_extra)
                    if caminho_extra.is_file():
                        scope.add_attachment(
                            path=str(caminho_extra),
                            filename=caminho_extra.name,
                            content_type="application/json",
                        )
    except Exception:
        pass


def registrar_breadcrumb_comando(cmd: Any) -> None:
    """Registra uma ação / comando do usuário como breadcrumb cronológico no Sentry."""
    if not sentry_sdk or not hasattr(sentry_sdk, "add_breadcrumb"):
        return
    try:
        classe = type(cmd).__name__
        campo = getattr(cmd, "campo_nome", "")
        caminho = getattr(cmd, "context_path", "") or getattr(cmd, "caminho_msg", "")
        msg = f"{classe}: {campo}" if campo else classe
        sentry_sdk.add_breadcrumb(
            category="historico",
            message=msg,
            level="info",
            data={"classe": classe, "campo": campo, "caminho": caminho},
        )
    except Exception:
        pass


def configurar_tratamento_excecoes_globais() -> None:
    """Configura ganchos sys.excepthook e threading.excepthook para envio silencioso ao Sentry."""
    if not sentry_sdk:
        return

    hook_original_sys = sys.excepthook

    def _tratar_excecao_sys(
        exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any
    ) -> None:
        try:
            _anexar_arquivos_diario_no_escopo()
            sentry_sdk.capture_exception((exc_type, exc_value, exc_traceback))
            if hasattr(sentry_sdk, "flush"):
                sentry_sdk.flush(timeout=5.0)
        except Exception:
            pass
        if hook_original_sys is not None:
            hook_original_sys(exc_type, exc_value, exc_traceback)

    sys.excepthook = _tratar_excecao_sys

    if hasattr(threading, "excepthook"):
        hook_original_thread = threading.excepthook

        def _tratar_excecao_thread(args: Any) -> None:
            try:
                _anexar_arquivos_diario_no_escopo()
                sentry_sdk.capture_exception((args.exc_type, args.exc_value, args.exc_traceback))
                if hasattr(sentry_sdk, "flush"):
                    sentry_sdk.flush(timeout=5.0)
            except Exception:
                pass
            if hook_original_thread is not None:
                hook_original_thread(args)

        threading.excepthook = _tratar_excecao_thread


def registrar_breadcrumb_submissao(
    mensagem: str,
    categoria: str = "submissao_pr",
    dados: Any = None,
    nivel: str = "info",
) -> None:
    """Registra uma etapa de submissão como breadcrumb cronológico no Sentry."""
    if not sentry_sdk or not hasattr(sentry_sdk, "add_breadcrumb"):
        return
    try:
        dados_sanitizados = _sanitizar_objeto_recursivo(dados) if dados else {}
        sentry_sdk.add_breadcrumb(
            category=categoria,
            message=sanitizar_texto_caminhos(mensagem),
            level=nivel,
            data=dados_sanitizados,
        )
    except Exception:
        pass


def capturar_falha_submissao(
    erro: Exception,
    id_croqui: str = "",
    etapa: str = "",
    categoria: str = "inesperado",
    contexto_extra: Any = None,
) -> Any:
    """
    Captura e despacha uma falha de submissão de Pull Request para o Sentry com severidade,
    tags taxonômicas, diário de comandos anexado e contexto operacional sanitizado.
    Retorna o event_id do Sentry se enviado com sucesso, ou None.
    """
    if not sentry_sdk:
        return None

    try:
        # Mapeamento taxonômico de severidade
        mapa_severidade = {
            "git_proxy": "fatal",
            "github_api": "fatal",
            "git_local": "fatal",
            "inesperado": "fatal",
            "autenticacao": "error",
            "rede": "warning",
        }
        severidade = mapa_severidade.get(categoria, "fatal")

        # Configura tags no escopo
        if hasattr(sentry_sdk, "set_tag"):
            sentry_sdk.set_tag("tipo_evento", "falha_publicacao_pr")
            sentry_sdk.set_tag("categoria_erro", categoria)
            sentry_sdk.set_tag("nivel_severidade", severidade)
            if id_croqui:
                sentry_sdk.set_tag("id_croqui", id_croqui)
            if etapa:
                sentry_sdk.set_tag("etapa_falha", etapa)

        # Contexto operacional detalhado sanitizado
        if contexto_extra and hasattr(sentry_sdk, "set_context"):
            contexto_sanitizado = _sanitizar_objeto_recursivo(contexto_extra)
            sentry_sdk.set_context("detalhes_submissao", contexto_sanitizado)

        # Anexa os binários de diário recente se disponíveis
        _anexar_arquivos_diario_no_escopo()

        # Dispara captura de exceção
        event_id = None
        if hasattr(sentry_sdk, "capture_exception"):
            event_id = sentry_sdk.capture_exception(erro)
            if hasattr(sentry_sdk, "flush"):
                sentry_sdk.flush(timeout=5.0)

        return event_id
    except Exception:
        return None


def capturar_excecao(
    erro: BaseException,
    id_croqui: str = "",
    etapa: str = "",
    contexto_extra: Any = None,
    contextos_extras: dict[str, Any] | None = None,
    nivel_severidade: str | None = None,
    tags_extras: dict[str, str] | None = None,
    arquivos_anexos: Sequence[Path | str] | None = None,
) -> Any:
    """
    Captura qualquer exceção (incluindo falhas de salvamento e compilação),
    registra tags, anexa o diário local sanitizado e envia silenciosamente ao Sentry com flush imediato.
    Retorna o event_id se enviado com sucesso, ou None.
    """
    if not sentry_sdk:
        return None

    try:
        if hasattr(sentry_sdk, "set_tag"):
            sentry_sdk.set_tag("tipo_evento", "excecao_editor")
            if id_croqui:
                sentry_sdk.set_tag("id_croqui", id_croqui)
            if etapa:
                sentry_sdk.set_tag("etapa_falha", etapa)
            if nivel_severidade:
                sentry_sdk.set_tag("nivel_severidade", nivel_severidade)
            if tags_extras:
                for chave_tag, valor_tag in tags_extras.items():
                    sentry_sdk.set_tag(chave_tag, valor_tag)

        if nivel_severidade and hasattr(sentry_sdk, "set_level"):
            sentry_sdk.set_level(nivel_severidade)

        if contexto_extra and hasattr(sentry_sdk, "set_context"):
            contexto_sanitizado = _sanitizar_objeto_recursivo(contexto_extra)
            sentry_sdk.set_context("detalhes_erro", contexto_sanitizado)

        if contextos_extras and hasattr(sentry_sdk, "set_context"):
            for nome_ctx, dados_ctx in contextos_extras.items():
                sentry_sdk.set_context(nome_ctx, _sanitizar_objeto_recursivo(dados_ctx))

        _anexar_arquivos_diario_no_escopo(arquivos_extras=arquivos_anexos)

        event_id = None
        if hasattr(sentry_sdk, "capture_exception"):
            event_id = sentry_sdk.capture_exception(erro)
            if hasattr(sentry_sdk, "flush"):
                sentry_sdk.flush(timeout=5.0)

        return event_id
    except Exception:
        return None


@contextlib.contextmanager
def ativar_sessao_sentry_robo_caotico(dsn: str | None = None) -> Iterator[None]:
    """
    Mantém o Sentry continuamente ativo e liberado do início ao fim de uma campanha
    do Robô Caótico, permitindo que erros, breadcrumbs de comandos, logs e diário
    sejam enviados e acumulados em tempo real durante toda a execução.
    """
    global _sessao_robo_caotico_ativa
    desativar_anterior = os.environ.pop("ARESTA_DESATIVAR_TELEMETRIA", None)
    hook_sys_anterior = sys.excepthook
    hook_thread_anterior = getattr(threading, "excepthook", None)
    sessao_anterior = _sessao_robo_caotico_ativa
    _sessao_robo_caotico_ativa = True
    inicializado = inicializar_telemetria(dsn=dsn)
    try:
        yield
    finally:
        if inicializado:
            encerrar_telemetria(timeout=2.0)
        _sessao_robo_caotico_ativa = sessao_anterior
        sys.excepthook = hook_sys_anterior
        if hook_thread_anterior is not None:
            threading.excepthook = hook_thread_anterior
        if desativar_anterior is not None:
            os.environ["ARESTA_DESATIVAR_TELEMETRIA"] = desativar_anterior


@contextlib.contextmanager
def escopo_isolado_semente_sentry(
    seed: int,
    dataset: str = "",
    escopo: str = "",
) -> Iterator[None]:
    """
    Abre um escopo isolado do Sentry para uma semente individual do Robô Caótico,
    garantindo que breadcrumbs, tags e anexos iniciem limpos a cada semente.
    """
    gerenciador = (
        sentry_sdk.isolation_scope()
        if sentry_sdk and hasattr(sentry_sdk, "isolation_scope")
        else contextlib.nullcontext()
    )
    with gerenciador as escopo_iso:
        try:
            for escopo_alvo in (
                escopo_iso,
                sentry_sdk.get_current_scope()
                if sentry_sdk and hasattr(sentry_sdk, "get_current_scope")
                else None,
                sentry_sdk.get_isolation_scope()
                if sentry_sdk and hasattr(sentry_sdk, "get_isolation_scope")
                else None,
            ):
                if escopo_alvo is not None:
                    if hasattr(escopo_alvo, "clear_breadcrumbs"):
                        escopo_alvo.clear_breadcrumbs()
                    if hasattr(escopo_alvo, "clear_attachments"):
                        escopo_alvo.clear_attachments()
            if sentry_sdk and hasattr(sentry_sdk, "set_tag"):
                sentry_sdk.set_tag("seed_caos", str(seed))
                if dataset:
                    sentry_sdk.set_tag("dataset_caos", dataset)
                if escopo:
                    sentry_sdk.set_tag("escopo_caos", escopo)
        except Exception:
            pass
        yield


@contextlib.contextmanager
def escopo_silencioso_ddmin_sentry() -> Iterator[None]:
    """
    Isola as reexecuções de minimização (ddmin) em um escopo descartável do Sentry,
    preservando intactos os breadcrumbs e o diário acumulados na semente original que falhou.
    """
    diario_semente_original = _diario_ativo
    gerenciador = (
        sentry_sdk.isolation_scope()
        if sentry_sdk and hasattr(sentry_sdk, "isolation_scope")
        else contextlib.nullcontext()
    )
    try:
        with gerenciador:
            yield
    finally:
        anexar_diario_escopo(diario_semente_original)


def capturar_crash_robo_caotico(
    erro: BaseException,
    receita_robo_caotico: dict[str, Any],
    id_croqui: str = "",
    etapa: str = "robo_caotico",
    caminho_arquivo_json: Path | str | None = None,
) -> Any:
    """
    Captura uma falha inédita encontrada pelo Robô Caótico e envia ao Sentry com
    nível 'fatal', tag 'origem_crash=robo_caotico', contexto estruturado 'receita_robo_caotico'
    sanitizado, breadcrumbs acumulados da semente e o arquivo '.json' da receita anexado.
    """
    anexos = [caminho_arquivo_json] if caminho_arquivo_json else None
    gerenciador = (
        contextlib.nullcontext()
        if _sessao_robo_caotico_ativa
        else ativar_sessao_sentry_robo_caotico()
    )
    with gerenciador:
        return capturar_excecao(
            erro=erro,
            id_croqui=id_croqui,
            etapa=etapa,
            contextos_extras={"receita_robo_caotico": receita_robo_caotico},
            nivel_severidade="fatal",
            tags_extras={"origem_crash": "robo_caotico"},
            arquivos_anexos=anexos,
        )
