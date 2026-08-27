# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

DSN_PADRAO = "https://a632ff22a93532930ea95f849b4a796b@o4511980548849664.ingest.us.sentry.io/4511980560515072"


def _obter_mapeamento_sanitizacao() -> list[tuple[str, str]]:
    """Gera lista ordenada de prefixos de caminhos locais e suas respectivas substituições anônimas."""
    mapeamentos = []
    
    # 1. APPDATA e LOCALAPPDATA
    appdata = os.environ.get("APPDATA")
    if appdata:
        mapeamentos.append((appdata, "%appdata%"))
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        mapeamentos.append((localappdata, "%localappdata%"))
        
    # 2. Diretório Home / UserProfile
    home = str(Path.home())
    if home:
        mapeamentos.append((home, "%userprofile%"))
        
    userprofile = os.environ.get("USERPROFILE")
    if userprofile and userprofile != home:
        mapeamentos.append((userprofile, "%userprofile%"))

    # 3. Diretório Temporário
    temp = os.environ.get("TEMP")
    if temp:
        mapeamentos.append((temp, "%temp%"))

    # Ordena pelos mais longos primeiro para substituição precisa
    mapeamentos.sort(key=lambda item: len(item[0]), reverse=True)
    return mapeamentos


def sanitizar_texto_caminhos(texto: str) -> str:
    """Substitui caminhos locais de usuários por variáveis de ambiente genéricas (%appdata%, %userprofile%, etc.)."""
    if not isinstance(texto, str) or not texto:
        return texto

    resultado = texto
    mapeamentos = _obter_mapeamento_sanitizacao()
    for caminho_original, substituto in mapeamentos:
        # Substitui versão com barras invertidas (\) e barras normais (/)
        caminho_barras_invertidas = caminho_original.replace("/", "\\")
        caminho_barras_normais = caminho_original.replace("\\", "/")
        
        # Regex case-insensitive escapando caracteres especiais
        padrao_inv = re.compile(re.escape(caminho_barras_invertidas), re.IGNORECASE)
        resultado = padrao_inv.sub(substituto, resultado)
        
        padrao_norm = re.compile(re.escape(caminho_barras_normais), re.IGNORECASE)
        resultado = padrao_norm.sub(substituto, resultado)

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


def sanitizar_evento_sentry(event: dict, hint: dict) -> dict:
    """Hook before_send do Sentry para sanitizar qualquer caminho local em eventos, stacktraces e breadcrumbs."""
    return _sanitizar_objeto_recursivo(event)


def inicializar_telemetria(dsn: str | None = None) -> bool:
    """
    Inicializa o Sentry SDK com telemetria silenciosa automática e sanitização de dados.
    Retorna True se inicializado com sucesso.
    """
    if not sentry_sdk:
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
        configurar_tratamento_excecoes_globais()
        return True
    except Exception:
        return False


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


def anexar_diario_escopo(diario) -> None:
    """Anexa os comandos recentes do diário (anonimizados) ao contexto do escopo Sentry."""
    if not sentry_sdk or not diario:
        return
    try:
        comandos_anon = diario.exportar_diario_anonimizado(limite_comandos=50)
        sentry_sdk.set_context("historico_comandos", {"comandos": comandos_anon})
    except Exception:
        pass


def configurar_tratamento_excecoes_globais() -> None:
    """Configura ganchos sys.excepthook e threading.excepthook para envio silencioso ao Sentry."""
    if not sentry_sdk:
        return

    hook_original_sys = sys.excepthook

    def _tratar_excecao_sys(exc_type, exc_value, exc_traceback):
        try:
            sentry_sdk.capture_exception((exc_type, exc_value, exc_traceback))
        except Exception:
            pass
        if hook_original_sys:
            hook_original_sys(exc_type, exc_value, exc_traceback)

    sys.excepthook = _tratar_excecao_sys

    if hasattr(threading, "excepthook"):
        hook_original_thread = threading.excepthook

        def _tratar_excecao_thread(args):
            try:
                sentry_sdk.capture_exception((args.exc_type, args.exc_value, args.exc_traceback))
            except Exception:
                pass
            if hook_original_thread:
                hook_original_thread(args)

        threading.excepthook = _tratar_excecao_thread
