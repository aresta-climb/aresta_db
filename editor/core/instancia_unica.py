# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import time
from typing import Optional, Callable, List
from PySide6.QtNetwork import QLocalSocket, QLocalServer
from PySide6.QtWidgets import QApplication

NOME_SERVIDOR_PADRAO = "ArestaEditorSingleInstanceServer"


def ativar_janela_existente() -> bool:
    """
    Localiza a janela ativa ou a primeira janela de nível superior visível e
    a restaura e traz para o primeiro plano.
    Retorna True se uma janela foi encontrada e ativada; False se nenhuma janela visível existir.
    """
    janela = QApplication.activeWindow()
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
        try:
            from editor.core.integracao_windows import trazer_janela_para_frente
            trazer_janela_para_frente(int(janela.winId()))
        except Exception:
            pass
        return True
    return False


def verificar_se_ja_em_execucao(
    nome_servidor: str = NOME_SERVIDOR_PADRAO,
    timeout_ms: int = 500
) -> bool:
    """
    Verifica se já existe uma instância do Aresta Editor em execução ativa e responsiva.
    Envia um ping para o servidor local. Se o servidor responder PONG, confirma que
    a instância está viva e com janela ativa. Caso o servidor não responda ou
    informe ausência de janelas (processo travado/zumbi/headless), remove a trava
    órfã e retorna False permitindo a inicialização.
    """
    socket = QLocalSocket()
    socket.connectToServer(nome_servidor)
    if not socket.waitForConnected(200):
        socket.close()
        return False

    # Envia ping com verificação de saúde
    socket.write(b"PING\n")
    socket.flush()
    if socket.waitForReadyRead(timeout_ms):
        resposta = bytes(socket.readAll().data())
        if b"PONG" in resposta:
            socket.close()
            return True

    # Servidor conectou mas não respondeu PONG (instância zumbi/travada ou sem janela visível)
    print(
        f"Aviso: Detectada trava de instância anterior não responsiva ('{nome_servidor}'). "
        "Limpando trava órfã...",
        file=sys.stderr
    )
    socket.abort()
    QLocalServer.removeServer(nome_servidor)
    return False


def iniciar_servidor_instancia_unica(
    nome_servidor: str = NOME_SERVIDOR_PADRAO,
    callback_ativacao: Optional[Callable[[], None]] = None,
    tempo_tolerancia_inicializacao_s: float = 5.0
) -> Optional[QLocalServer]:
    """
    Inicia o QLocalServer para garantir instância única e responder a pings
    de novas instâncias trazendo a janela existente para frente.

    Args:
        nome_servidor: Nome do servidor local IPC / named pipe.
        callback_ativacao: Callback customizado de ativação opcional.
        tempo_tolerancia_inicializacao_s: Tempo em segundos durante a inicialização
            no qual o processo pode responder PONG antes de sua janela estar visível.
    """
    QLocalServer.removeServer(nome_servidor)
    servidor = QLocalServer()
    if not servidor.listen(nome_servidor):
        print(
            f"Aviso: Não foi possível escutar no servidor local '{nome_servidor}': {servidor.errorString()}",
            file=sys.stderr
        )
        return None

    clientes_ativos: List[QLocalSocket] = []
    setattr(servidor, "_clientes_ativos", clientes_ativos)
    tempo_inicio = time.monotonic()

    def _ao_conectar() -> None:
        socket_cliente = servidor.nextPendingConnection()
        if not socket_cliente:
            return

        clientes_ativos.append(socket_cliente)

        def _ao_desconectar(s: QLocalSocket = socket_cliente) -> None:
            if s in clientes_ativos:
                clientes_ativos.remove(s)

        socket_cliente.disconnected.connect(_ao_desconectar)

        def _ao_ler(s: QLocalSocket = socket_cliente) -> None:
            dados = bytes(s.readAll().data())
            if b"PING" in dados:
                ativou = False
                if callback_ativacao:
                    callback_ativacao()
                    ativou = True
                else:
                    ativou = ativar_janela_existente()

                em_tolerancia = (time.monotonic() - tempo_inicio) < tempo_tolerancia_inicializacao_s
                if ativou or em_tolerancia:
                    s.write(b"PONG\n")
                else:
                    # Instância sem nenhuma janela visível fora da tolerância de inicialização
                    s.write(b"SEM_JANELA\n")
                    s.flush()
                    servidor.close()
                    app = QApplication.instance()
                    if app:
                        app.quit()
                    return
                s.flush()

        socket_cliente.readyRead.connect(_ao_ler)
        if socket_cliente.bytesAvailable() > 0:
            _ao_ler()

    servidor.newConnection.connect(_ao_conectar)
    return servidor

