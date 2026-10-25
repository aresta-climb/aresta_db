# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
import json
import threading
import time
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from editor.mcp.bridge import executar_ponte_stdio
from editor.mcp.despachante import DespachanteQt
from editor.mcp.servidor import ServidorMCP


def test_ponte_stdio_encaminha_mensagens_para_servidor_real_via_mcp_sessao(qapp, tmp_path: Path):
    """Deve descobrir a porta pelo mcp_sessao.json e encaminhar mensagens JSON-RPC bidirecionalmente."""
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    servidor.registrar_ferramenta(
        nome="aresta_eco",
        descricao="Retorna o texto recebido.",
        esquema_entrada={"type": "object", "properties": {"msg": {"type": "string"}}},
        manipulador=lambda args: {"eco": args.get("msg", "")},
    )
    servidor.iniciar()

    try:
        linhas_entrada = [
            "",
            "{json_invalido}",
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "aresta_eco", "arguments": {"msg": "Olá MCP"}},
                }
            ),
        ]
        entrada = io.StringIO("\n".join(linhas_entrada) + "\n")
        saida = io.StringIO()
        codigo_box: list[int] = []
        concluido = threading.Event()

        def rodar_ponte() -> None:
            codigo_box.append(
                executar_ponte_stdio(
                    entrada=entrada,
                    saida=saida,
                    diretorio_sessao=tmp_path,
                    env={},
                )
            )
            concluido.set()

        t = threading.Thread(target=rodar_ponte, daemon=True)
        t.start()

        prazo = time.monotonic() + 5.0
        while not concluido.is_set() and time.monotonic() < prazo:
            QCoreApplication.processEvents()
            time.sleep(0.005)

        t.join(timeout=1.0)
        assert codigo_box == [0]

        respostas = [json.loads(linha) for linha in saida.getvalue().splitlines() if linha.strip()]
        # 3 respostas: erro de parse (-32700), initialize (id=1) e tools/call (id=2). Notificação não gera saída.
        assert len(respostas) == 3
        assert respostas[0]["error"]["code"] == -32700
        assert respostas[1]["id"] == 1
        assert respostas[1]["result"]["serverInfo"]["name"] == "editor-aresta"
        assert respostas[2]["id"] == 2
        assert respostas[2]["result"]["structuredContent"] == {"eco": "Olá MCP"}
    finally:
        servidor.parar()


def test_ponte_stdio_retorna_erro_jsonrpc_quando_editor_offline(tmp_path: Path):
    """Se o servidor MCP do editor estiver offline, deve devolver erro JSON-RPC -32000 para requisições com id."""
    entrada = io.StringIO(
        "\n".join(
            [
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"}),
            ]
        )
        + "\n"
    )
    saida = io.StringIO()

    codigo = executar_ponte_stdio(
        entrada=entrada,
        saida=saida,
        diretorio_sessao=tmp_path,
        env={"ARESTA_MCP_PORTA": "65431"},
    )
    assert codigo == 0

    respostas = [json.loads(linha) for linha in saida.getvalue().splitlines() if linha.strip()]
    assert len(respostas) == 1
    assert respostas[0]["id"] == 99
    assert respostas[0]["error"]["code"] == -32000
    assert "Não foi possível conectar ao Editor Aresta" in respostas[0]["error"]["message"]
