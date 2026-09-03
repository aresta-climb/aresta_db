# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
from typing import Optional, Callable, List
from PySide6.QtNetwork import QLocalSocket, QLocalServer
from PySide6.QtWidgets import QApplication

NOME_SERVIDOR_PADRAO = "ArestaEditorSingleInstanceServer"


def verificar_se_ja_em_execucao(
    nome_servidor: str = NOME_SERVIDOR_PADRAO,
    timeout_ms: int = 500
) -> bool:
    """
    Verifica se já existe uma instância do Aresta Editor em execução ativa e responsiva.
    Envia um ping para o servidor local. Se o servidor responder PONG, confirma que
    a instância está viva. Caso o servidor não responda (processo travado/zumbi),
    remove a trava órfã e retorna False permitindo a inicialização.
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

    # Servidor conectou mas não respondeu ao ping (instância zumbi/travada)
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
    callback_ativacao: Optional[Callable[[], None]] = None
) -> Optional[QLocalServer]:
    """
    Inicia o QLocalServer para garantir instância única e responder a pings
    de novas instâncias trazendo a janela existente para frente.
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
                s.write(b"PONG\n")
                s.flush()
            if callback_ativacao:
                callback_ativacao()
            else:
                janela = QApplication.activeWindow()
                if janela:
                    janela.showNormal()
                    janela.raise_()
                    janela.activateWindow()

        socket_cliente.readyRead.connect(_ao_ler)

    servidor.newConnection.connect(_ao_conectar)
    return servidor
