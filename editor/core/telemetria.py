# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

sentry_sdk: Any
try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

DSN_PADRAO = "https://a632ff22a93532930ea95f849b4a796b@o4511980548849664.ingest.us.sentry.io/4511980560515072"

_caminhos_extras_sanitizacao: list[tuple[str, str]] = []


def registrar_caminho_repo_local(caminho_repo: Path | str) -> None:
    """
    Registra a raiz do repositório local para que qualquer caminho interno
    seja truncado e sanitizado como <aresta_db>\\... em logs e relatórios.
    """
    if not caminho_repo:
        return
    caminho_str = str(Path(caminho_repo).resolve())
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
        # Substitui versão com barras invertidas (\) e barras normais (/)
        caminho_barras_invertidas = caminho_original.replace("/", "\\")
        caminho_barras_normais = caminho_original.replace("\\", "/")
        
        # Helper com tipagem explícita para evitar erro de inferência em lambda
        def _fazer_subst(val_subst: str) -> Any:
            return lambda m: val_subst

        # Regex case-insensitive escapando caracteres especiais
        padrao_inv = re.compile(re.escape(caminho_barras_invertidas), re.IGNORECASE)
        resultado = padrao_inv.sub(_fazer_subst(substituto), resultado)
        
        padrao_norm = re.compile(re.escape(caminho_barras_normais), re.IGNORECASE)
        resultado = padrao_norm.sub(_fazer_subst(substituto), resultado)

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

    dsn_usado = dsn or DSN_PADRAO
    if not dsn_usado:
        return False

    try:
        sentry_sdk.init(
            dsn=dsn_usado,
            send_default_pii=True,
            traces_sample_rate=1.0,
            profile_session_sample_rate=1.0,
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


def _anexar_arquivos_diario_no_escopo() -> None:
    """Anexa os arquivos .bin do diário ao escopo apenas no momento do envio do crash."""
    if not sentry_sdk or not _diario_ativo:
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

        scope = sentry_sdk.get_current_scope() if hasattr(sentry_sdk, "get_current_scope") else (
            getattr(getattr(sentry_sdk, "Hub", None), "current", None) and getattr(sentry_sdk.Hub.current, "scope", None)
        )
        if scope and hasattr(scope, "add_attachment"):
            if hasattr(_diario_ativo, "caminho_pendente") and _diario_ativo.caminho_pendente.exists() and _diario_ativo.caminho_pendente.stat().st_size > 0:
                scope.add_attachment(path=str(_diario_ativo.caminho_pendente), filename="diario_pendente.bin")
            if hasattr(_diario_ativo, "caminho_salvo") and _diario_ativo.caminho_salvo.exists() and _diario_ativo.caminho_salvo.stat().st_size > 0:
                scope.add_attachment(path=str(_diario_ativo.caminho_salvo), filename="diario_salvo.bin")
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
            data={"classe": classe, "campo": campo, "caminho": caminho}
        )
    except Exception:
        pass


def configurar_tratamento_excecoes_globais() -> None:
    """Configura ganchos sys.excepthook e threading.excepthook para envio silencioso ao Sentry."""
    if not sentry_sdk:
        return

    hook_original_sys = sys.excepthook

    def _tratar_excecao_sys(exc_type: type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
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

        if contexto_extra and hasattr(sentry_sdk, "set_context"):
            contexto_sanitizado = _sanitizar_objeto_recursivo(contexto_extra)
            sentry_sdk.set_context("detalhes_erro", contexto_sanitizado)

        _anexar_arquivos_diario_no_escopo()

        event_id = None
        if hasattr(sentry_sdk, "capture_exception"):
            event_id = sentry_sdk.capture_exception(erro)
            if hasattr(sentry_sdk, "flush"):
                sentry_sdk.flush(timeout=5.0)

        return event_id
    except Exception:
        return None




