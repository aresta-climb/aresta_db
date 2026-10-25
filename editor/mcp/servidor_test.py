# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import asyncio
from pathlib import Path
from typing import Any

import httpx

from editor.mcp.despachante import DespachanteQt
from editor.mcp.servidor import ServidorMCP
from editor.mcp.sessao import ler_sessao_mcp


def _criar_servidor_teste(tmp_path: Path) -> ServidorMCP:
    despachante = DespachanteQt()
    servidor = ServidorMCP(despachante=despachante, diretorio_sessao=tmp_path)

    def somar(args: dict[str, Any]) -> dict[str, Any]:
        return {"soma": int(args["a"]) + int(args["b"])}

    def capturar_imagem(_args: dict[str, Any]) -> dict[str, Any]:
        return {
            "_mcp_content": [
                {"type": "image", "data": "iVBORw0KGgo=", "mimeType": "image/png"},
                {"type": "text", "text": '{"largura": 100}'},
            ]
        }

    def falhar(_args: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Parâmetro inválido no croqui")

    servidor.registrar_ferramenta(
        nome="aresta_somar",
        descricao="Soma dois inteiros.",
        esquema_entrada={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
        manipulador=somar,
    )
    servidor.registrar_ferramenta(
        nome="aresta_imagem",
        descricao="Retorna imagem multimodal.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=capturar_imagem,
    )
    servidor.registrar_ferramenta(
        nome="aresta_falhar",
        descricao="Simula erro de validação.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=falhar,
    )
    servidor.registrar_recurso(
        uri="aresta://croqui/resumo",
        nome="Resumo do Croqui",
        descricao="Dados básicos do croqui ativo.",
        leitor=lambda: {"nome": "Serra do Cipó", "picos": 2},
    )
    return servidor


def test_protocolo_jsonrpc_completo_via_post_mcp(qapp, tmp_path: Path):
    """Valida initialize, notificações, ping, tools/list, tools/call e resources via POST /mcp."""
    servidor = _criar_servidor_teste(tmp_path)

    async def _executar_fluxo() -> None:
        transporte = httpx.ASGITransport(app=servidor.app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://127.0.0.1") as client:
            # 1. Payload inválido (não é JSON-RPC 2.0)
            resp_inv = await client.post("/mcp", json={"jsonrpc": "1.0", "id": 1, "method": "ping"})
            assert resp_inv.status_code == 200
            assert resp_inv.json()["error"]["code"] == -32600

            # 2. Initialize
            resp_init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                },
            )
            assert resp_init.status_code == 200
            dados_init = resp_init.json()["result"]
            assert dados_init["serverInfo"]["name"] == "editor-aresta"
            assert "tools" in dados_init["capabilities"]

            # 3. Notificação (sem id) -> 202 Accepted sem corpo JSON-RPC
            resp_notif = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
            assert resp_notif.status_code == 202

            # 4. Ping
            resp_ping = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "ping"}
            )
            assert resp_ping.json() == {"jsonrpc": "2.0", "id": 2, "result": {}}

            # 5. tools/list
            resp_tools = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
            )
            nomes_tools = [t["name"] for t in resp_tools.json()["result"]["tools"]]
            assert "aresta_somar" in nomes_tools
            assert "aresta_imagem" in nomes_tools

            # 6. tools/call com sucesso estruturado
            resp_call = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "aresta_somar", "arguments": {"a": 10, "b": 15}},
                },
            )
            res_call = resp_call.json()["result"]
            assert res_call["isError"] is False
            assert res_call["structuredContent"] == {"soma": 25}

            # 7. tools/call multimodal (_mcp_content)
            resp_img = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "aresta_imagem", "arguments": {}},
                },
            )
            res_img = resp_img.json()["result"]
            assert res_img["isError"] is False
            assert res_img["content"][0]["type"] == "image"
            assert res_img["content"][0]["mimeType"] == "image/png"

            # 8. tools/call com exceção de domínio -> retorna isError=True para o agente corrigir
            resp_err = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {"name": "aresta_falhar", "arguments": {}},
                },
            )
            res_err = resp_err.json()["result"]
            assert res_err["isError"] is True
            assert "Parâmetro inválido no croqui" in res_err["content"][0]["text"]

            # 9. tools/call de ferramenta inexistente -> erro JSON-RPC -32601
            resp_nao_existe = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {"name": "inexistente", "arguments": {}},
                },
            )
            assert resp_nao_existe.json()["error"]["code"] == -32601

            # 10. resources/list e resources/read
            resp_res_list = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 8, "method": "resources/list"}
            )
            recursos = resp_res_list.json()["result"]["resources"]
            assert len(recursos) == 1
            assert recursos[0]["uri"] == "aresta://croqui/resumo"

            resp_res_read = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "resources/read",
                    "params": {"uri": "aresta://croqui/resumo"},
                },
            )
            conteudo_lido = resp_res_read.json()["result"]["contents"][0]["text"]
            assert "Serra do Cipó" in conteudo_lido

            resp_res_invalido = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "resources/read",
                    "params": {"uri": "aresta://inexistente"},
                },
            )
            assert resp_res_invalido.json()["error"]["code"] == -32602

            # 11. Método desconhecido -> -32601
            resp_metodo_inv = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 11, "method": "metodo/inexistente"}
            )
            assert resp_metodo_inv.json()["error"]["code"] == -32601

    asyncio.run(_executar_fluxo())


def test_transporte_sse_e_ciclo_vida_servidor_real(qapp, tmp_path: Path):
    """Inicia o servidor Uvicorn real em 127.0.0.1, valida SSE + /mcp/messages e encerramento limpo."""
    servidor = _criar_servidor_teste(tmp_path)
    sessao = servidor.iniciar()
    # Chamada idempotente quando já está rodando
    assert servidor.iniciar() == sessao
    assert servidor.esta_ativo is True
    assert ler_sessao_mcp(tmp_path) is not None

    try:
        with httpx.Client(timeout=5.0) as http:
            status = http.get(f"http://127.0.0.1:{servidor.porta}/mcp/status").json()
            assert status["ativo"] is True
            assert status["porta"] == servidor.porta

            # Abre stream SSE real e envia mensagem via POST /mcp/messages
            with http.stream("GET", sessao.url_sse) as stream:
                linhas_iter = stream.iter_lines()
                linha_evento = next(linhas_iter)
                linha_dados = next(linhas_iter)
                assert linha_evento == "event: endpoint"
                assert linha_dados.startswith("data: /mcp/messages?session_id=")
                endpoint_msg = linha_dados.removeprefix("data: ").strip()

                # Envia requisição JSON-RPC pelo endpoint de mensagens da sessão SSE
                url_post = f"http://127.0.0.1:{servidor.porta}{endpoint_msg}"
                resp_post = http.post(
                    url_post,
                    json={"jsonrpc": "2.0", "id": 42, "method": "ping"},
                )
                assert resp_post.status_code == 202

                # Envia notificação pelo endpoint de mensagens
                resp_notif = http.post(
                    url_post,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                )
                assert resp_notif.status_code == 202

                # Lê resposta JSON-RPC entregue no canal SSE
                ev_msg = ""
                dados_msg = ""
                for linha in linhas_iter:
                    if linha.startswith("event: message"):
                        ev_msg = linha
                    elif linha.startswith("data: "):
                        dados_msg = linha.removeprefix("data: ").strip()
                        break
                assert ev_msg == "event: message"
                assert '"id": 42' in dados_msg or '"id":42' in dados_msg

                # POST /mcp/messages sem session_id ativa também retorna a resposta diretamente
                resp_sem_sessao = http.post(
                    f"http://127.0.0.1:{servidor.porta}/mcp/messages",
                    json={"jsonrpc": "2.0", "id": 99, "method": "ping"},
                )
                assert resp_sem_sessao.status_code == 200
                assert resp_sem_sessao.json()["id"] == 99

                # Parar o servidor enquanto o stream SSE está aberto deve encerrar o gerador limpo
                servidor.parar()
                restantes = [linha for linha in linhas_iter if linha]
                assert restantes == []
    finally:
        servidor.parar()

    assert servidor.esta_ativo is False
    assert ler_sessao_mcp(tmp_path) is None
