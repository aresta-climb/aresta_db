# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import contextlib
import os
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from editor.plataforma import trazer_janela_para_frente

NOME_SERVIDOR_PADRAO = "ArestaEditorSingleInstanceServer"
PREFIXO_SERVIDOR_CROQUI = "ArestaEditorCroqui_"


def obter_nome_servidor_croqui(id_croqui: str) -> str:
    """
    Retorna o nome do servidor local IPC escopado para um croqui específico (`ArestaEditorCroqui_<id>`).
    Retorna `NOME_SERVIDOR_PADRAO` caso o identificador seja vazio.
    """
    id_limpo = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in id_croqui.strip())
    return f"{PREFIXO_SERVIDOR_CROQUI}{id_limpo}" if id_limpo else NOME_SERVIDOR_PADRAO


def ativar_janela_existente(janela_alvo: Any = None) -> bool:
    """
    Localiza a janela informada, a janela ativa ou a primeira janela de nível superior visível e
    a restaura e traz para o primeiro plano.
    Retorna True se uma janela foi encontrada e ativada; False se nenhuma janela visível existir.
    """
    janela = janela_alvo or QApplication.activeWindow()
    if not janela:
        for widget in QApplication.topLevelWidgets():
            if widget.isWindow() and widget.isVisible():
                janela = widget
                break

    if janela:
        if janela.isMinimized():
            janela.showNormal()
        janela.raise_()
        janela.activateWindow()
        trazer_janela_para_frente(int(janela.winId()))
        return True
    return False


def verificar_se_ja_em_execucao(
    nome_servidor: str = NOME_SERVIDOR_PADRAO, timeout_ms: int = 500
) -> bool:
    """
    Verifica se já existe uma instância do Aresta Editor escutando em `nome_servidor` ativa e responsiva.
    Envia um ping para o servidor local. Se o servidor responder PONG, confirma que
    a instância está viva e elevou a janela correspondente. Caso o servidor não responda,
    remove a trava órfã e retorna False.
    """
    app = QApplication.instance()
    socket = QLocalSocket()
    socket.connectToServer(nome_servidor)
    inicio_con = time.monotonic()
    while socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
        if app is not None:
            app.processEvents()
        socket.waitForConnected(20)
        if (
            socket.state() != QLocalSocket.LocalSocketState.ConnectedState
            and (time.monotonic() - inicio_con) * 1000 >= 200
        ):
            socket.close()
            return False

    socket.write(b"PING\n")
    socket.flush()
    inicio_leitura = time.monotonic()
    while (time.monotonic() - inicio_leitura) * 1000 < timeout_ms:
        if app is not None:
            app.processEvents()
        if socket.bytesAvailable() > 0 or socket.waitForReadyRead(20):
            resposta = bytes(socket.readAll().data())
            if b"PONG" in resposta:
                socket.close()
                return True
            if b"SEM_JANELA" in resposta:
                break

    print(
        f"Aviso: Detectada trava de instância anterior não responsiva ('{nome_servidor}'). "
        "Limpando trava órfã...",
        file=sys.stderr,
    )
    socket.abort()
    QLocalServer.removeServer(nome_servidor)
    return False


def iniciar_servidor_instancia_unica(
    nome_servidor: str = NOME_SERVIDOR_PADRAO,
    callback_ativacao: Callable[[], None] | None = None,
    tempo_tolerancia_inicializacao_s: float = 5.0,
) -> QLocalServer | None:
    """
    Inicia o QLocalServer para garantir instância única para `nome_servidor` e responder a pings
    de novas instâncias trazendo a janela existente para frente.
    """
    QLocalServer.removeServer(nome_servidor)
    servidor = QLocalServer()
    if not servidor.listen(nome_servidor):
        print(
            f"Aviso: Não foi possível escutar no servidor local '{nome_servidor}': {servidor.errorString()}",
            file=sys.stderr,
        )
        return None

    clientes_ativos: list[QLocalSocket] = []
    setattr(servidor, "_clientes_ativos", clientes_ativos)
    tempo_inicio = time.monotonic()

    def _ao_conectar() -> None:
        socket_cliente = servidor.nextPendingConnection()
        clientes_ativos.append(socket_cliente)

        def _ao_desconectar(s: QLocalSocket = socket_cliente) -> None:
            if s in clientes_ativos:
                clientes_ativos.remove(s)

        socket_cliente.disconnected.connect(_ao_desconectar)

        def _ao_ler(s: QLocalSocket = socket_cliente) -> None:
            dados = bytes(s.readAll().data())
            if b"PING" in dados:
                if callback_ativacao:
                    callback_ativacao()
                    ativou = True
                else:
                    ativou = ativar_janela_existente()

                em_tolerancia = (time.monotonic() - tempo_inicio) < tempo_tolerancia_inicializacao_s
                if ativou or em_tolerancia:
                    s.write(b"PONG\n")
                else:
                    s.write(b"SEM_JANELA\n")
                    s.flush()
                    servidor.close()
                    return
                s.flush()

        socket_cliente.readyRead.connect(_ao_ler)

    servidor.newConnection.connect(_ao_conectar)
    return servidor


def verificar_croqui_ja_aberto(id_croqui: str, timeout_ms: int = 500) -> bool:
    """
    Verifica se o croqui `id_croqui` já está aberto em alguma janela do Editor.
    Se estiver, a janela correspondente é automaticamente elevada para o primeiro plano.
    """
    return verificar_se_ja_em_execucao(obter_nome_servidor_croqui(id_croqui), timeout_ms=timeout_ms)


def iniciar_trava_croqui(
    id_croqui: str,
    callback_ativacao: Callable[[], None] | None = None,
    tempo_tolerancia_inicializacao_s: float = 5.0,
) -> QLocalServer | None:
    """
    Inicia o servidor de trava local para o croqui `id_croqui`.
    """
    return iniciar_servidor_instancia_unica(
        obter_nome_servidor_croqui(id_croqui),
        callback_ativacao=callback_ativacao,
        tempo_tolerancia_inicializacao_s=tempo_tolerancia_inicializacao_s,
    )


@contextlib.contextmanager
def trava_arquivo_operacao(
    caminho_lock: Path, timeout_s: float = 10.0, idade_maxima_orfao_s: float = 120.0
) -> Iterator[None]:
    """
    Gerenciador de contexto que garante exclusão mútua via arquivo de lock atômico (`O_CREAT | O_EXCL`),
    útil para proteger operações Git compartilhadas entre múltiplas janelas do Editor.
    """
    caminho_lock.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.monotonic()
    fd: int | None = None

    while True:
        try:
            fd = os.open(str(caminho_lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
            os.close(fd)
            fd = None
            break
        except FileExistsError:
            if caminho_lock.exists():
                idade = time.time() - caminho_lock.stat().st_mtime
                if idade > idade_maxima_orfao_s:
                    caminho_lock.unlink(missing_ok=True)
                    continue
            if (time.monotonic() - inicio) >= timeout_s:
                raise TimeoutError(
                    f"Não foi possível adquirir trava em '{caminho_lock}' após {timeout_s}s."
                )
            time.sleep(0.01)

    try:
        yield
    finally:
        caminho_lock.unlink(missing_ok=True)
