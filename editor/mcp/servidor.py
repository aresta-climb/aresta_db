# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import asyncio
import json
import secrets
import threading
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from PySide6.QtCore import QCoreApplication

from editor.mcp.despachante import DespachanteQt
from editor.mcp.sessao import (
    DadosSessaoMcp,
    gravar_sessao_mcp,
    remover_sessao_mcp,
    vincular_socket_mcp,
)


@dataclass
class DefinicaoFerramentaMcp:
    """Metadados e função manipuladora de uma ferramenta exposta via MCP."""

    nome: str
    descricao: str
    esquema_entrada: dict[str, Any]
    manipulador: Callable[[dict[str, Any]], Any]


@dataclass
class DefinicaoRecursoMcp:
    """Metadados e função leitora de um recurso estático/dinâmico exposto via MCP."""

    uri: str
    nome: str
    descricao: str
    mime_type: str
    leitor: Callable[[], str | dict[str, Any]]


class ServidorMCP:
    """
    Servidor MCP (Model Context Protocol) JSON-RPC 2.0 sobre HTTP e SSE local (`127.0.0.1`).
    Encaminha todas as execuções de ferramentas e leituras de recursos pelo `DespachanteQt`.
    """

    def __init__(
        self,
        despachante: DespachanteQt | None = None,
        porta_preferencial: int | None = None,
        diretorio_sessao: Path | None = None,
        versao_servidor: str = "1.0.0",
    ) -> None:
        self.despachante: DespachanteQt = despachante or DespachanteQt()
        self.porta_preferencial: int | None = porta_preferencial
        self.diretorio_sessao: Path | None = diretorio_sessao
        self.versao_servidor: str = versao_servidor
        self.ferramentas: dict[str, DefinicaoFerramentaMcp] = {}
        self.recursos: dict[str, DefinicaoRecursoMcp] = {}
        self.sessao: DadosSessaoMcp | None = None
        self._filas_sse: dict[
            str, tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, Any] | None]]
        ] = {}
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self.app: FastAPI = self._criar_app()

    @property
    def porta(self) -> int | None:
        """Retorna a porta TCP ativa do servidor MCP ou `None` se parado."""
        return self.sessao.porta if self.sessao is not None else None

    @property
    def esta_ativo(self) -> bool:
        """Indica se o servidor Uvicorn em segundo plano está em execução."""
        return bool(
            self._server is not None and self._thread is not None and self._thread.is_alive()
        )

    def registrar_ferramenta(
        self,
        nome: str,
        descricao: str,
        esquema_entrada: dict[str, Any],
        manipulador: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Registra uma ferramenta no catálogo MCP do servidor."""
        self.ferramentas[nome] = DefinicaoFerramentaMcp(
            nome=nome,
            descricao=descricao,
            esquema_entrada=esquema_entrada,
            manipulador=manipulador,
        )

    def registrar_recurso(
        self,
        uri: str,
        nome: str,
        descricao: str,
        leitor: Callable[[], str | dict[str, Any]],
        mime_type: str = "application/json",
    ) -> None:
        """Registra um recurso consultável no catálogo MCP do servidor."""
        self.recursos[uri] = DefinicaoRecursoMcp(
            uri=uri,
            nome=nome,
            descricao=descricao,
            mime_type=mime_type,
            leitor=leitor,
        )

    def processar_mensagem_jsonrpc(self, mensagem: dict[str, Any]) -> dict[str, Any] | None:
        """
        Processa uma mensagem JSON-RPC 2.0 do protocolo MCP e retorna o dicionário de resposta
        (ou `None` caso se trate de uma notificação sem `id`).
        """
        if not isinstance(mensagem, dict) or mensagem.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": mensagem.get("id") if isinstance(mensagem, dict) else None,
                "error": {
                    "code": -32600,
                    "message": "Requisição JSON-RPC 2.0 inválida.",
                },
            }

        req_id = mensagem.get("id")
        metodo = str(mensagem.get("method", ""))
        params = mensagem.get("params") or {}

        if req_id is None:
            return None

        if metodo == "initialize":
            versao_proto = params.get("protocolVersion", "2024-11-05")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": versao_proto,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {
                        "name": "editor-aresta",
                        "version": self.versao_servidor,
                    },
                },
            }

        if metodo == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if metodo == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": f.nome,
                            "description": f.descricao,
                            "inputSchema": f.esquema_entrada,
                        }
                        for f in self.ferramentas.values()
                    ]
                },
            }

        if metodo == "tools/call":
            nome_ferramenta = str(params.get("name", ""))
            argumentos = params.get("arguments") or {}
            ferramenta = self.ferramentas.get(nome_ferramenta)
            if ferramenta is None:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Ferramenta MCP desconhecida: '{nome_ferramenta}'.",
                    },
                }

            try:
                resultado = self.despachante.executar(ferramenta.manipulador, argumentos)
            except Exception as exc:
                texto_erro = json.dumps(
                    {"erro": str(exc), "tipo": type(exc).__name__}, ensure_ascii=False
                )
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": texto_erro}],
                    },
                }

            if isinstance(resultado, dict) and "_mcp_content" in resultado:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "isError": False,
                        "content": resultado["_mcp_content"],
                    },
                }

            texto_json = json.dumps(resultado, ensure_ascii=False)
            resposta_call: dict[str, Any] = {
                "isError": False,
                "content": [{"type": "text", "text": texto_json}],
            }
            if isinstance(resultado, dict):
                resposta_call["structuredContent"] = resultado
            return {"jsonrpc": "2.0", "id": req_id, "result": resposta_call}

        if metodo == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": [
                        {
                            "uri": r.uri,
                            "name": r.nome,
                            "description": r.descricao,
                            "mimeType": r.mime_type,
                        }
                        for r in self.recursos.values()
                    ]
                },
            }

        if metodo == "resources/read":
            uri = str(params.get("uri", ""))
            recurso = self.recursos.get(uri)
            if recurso is None:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": f"Recurso MCP não encontrado: '{uri}'.",
                    },
                }
            conteudo = self.despachante.executar(recurso.leitor)
            texto_recurso = (
                json.dumps(conteudo, ensure_ascii=False)
                if isinstance(conteudo, dict)
                else str(conteudo)
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": recurso.uri,
                            "mimeType": recurso.mime_type,
                            "text": texto_recurso,
                        }
                    ]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Método JSON-RPC desconhecido: '{metodo}'.",
            },
        }

    def _criar_app(self) -> FastAPI:
        app = FastAPI(title="Aresta Editor MCP", docs_url=None, redoc_url=None)

        @app.get("/mcp/status")
        async def status_mcp() -> JSONResponse:
            return JSONResponse(
                content={
                    "ativo": True,
                    "porta": self.porta,
                    "servidor": "editor-aresta",
                    "versao": self.versao_servidor,
                }
            )

        @app.post("/mcp")
        async def post_mcp(request: Request) -> Response:
            payload = await request.json()
            resposta = self.processar_mensagem_jsonrpc(payload)
            if resposta is None:
                return Response(status_code=202)
            return JSONResponse(content=resposta, status_code=200)

        @app.get("/mcp")
        @app.get("/mcp/sse")
        async def get_sse() -> StreamingResponse:
            session_id = secrets.token_hex(8)
            loop = asyncio.get_running_loop()
            fila: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
            self._filas_sse[session_id] = (loop, fila)

            async def gerador_eventos() -> AsyncIterator[str]:
                try:
                    yield f"event: endpoint\ndata: /mcp/messages?session_id={session_id}\n\n"
                    while True:
                        item = await fila.get()
                        if item is None:
                            break
                        dados = json.dumps(item, ensure_ascii=False)
                        yield f"event: message\ndata: {dados}\n\n"
                finally:
                    self._filas_sse.pop(session_id, None)

            return StreamingResponse(gerador_eventos(), media_type="text/event-stream")

        @app.post("/mcp/messages")
        async def post_messages(request: Request) -> Response:
            session_id = request.query_params.get("session_id", "")
            payload = await request.json()
            resposta = self.processar_mensagem_jsonrpc(payload)
            if resposta is None:
                return Response(status_code=202)
            entrada_sse = self._filas_sse.get(session_id)
            if entrada_sse is not None:
                loop_sse, fila_sse = entrada_sse
                loop_sse.call_soon_threadsafe(fila_sse.put_nowait, resposta)
                return JSONResponse(content=resposta, status_code=202)
            return JSONResponse(content=resposta, status_code=200)

        return app

    def iniciar(self, aguardar_pronto: bool = True, timeout: float = 5.0) -> DadosSessaoMcp:
        """Inicia o servidor Uvicorn em segundo plano vinculado a `127.0.0.1` e grava `mcp_sessao.json`."""
        if self.esta_ativo and self.sessao is not None:
            return self.sessao

        sock, porta = vincular_socket_mcp(porta_preferencial=self.porta_preferencial)
        self.sessao = gravar_sessao_mcp(porta=porta, diretorio_base=self.diretorio_sessao)

        config = uvicorn.Config(
            app=self.app,
            host="127.0.0.1",
            port=porta,
            log_level="error",
            ws="none",
        )
        self._server = uvicorn.Server(config)

        def _rodar() -> None:
            try:
                if self._server is not None:
                    self._server.run(sockets=[sock])
            finally:
                sock.close()

        self._thread = threading.Thread(target=_rodar, daemon=True)
        self._thread.start()

        if aguardar_pronto:
            prazo = time.monotonic() + timeout
            while not self._server.started and time.monotonic() < prazo:
                QCoreApplication.processEvents()
                time.sleep(0.01)

        return self.sessao

    def parar(self) -> None:
        """Encerra o servidor Uvicorn em segundo plano, fecha streams SSE e remove `mcp_sessao.json`."""
        for loop_sse, fila_sse in list(self._filas_sse.values()):
            loop_sse.call_soon_threadsafe(fila_sse.put_nowait, None)
        self._filas_sse.clear()

        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        self._server = None
        self._thread = None
        self.sessao = None
        remover_sessao_mcp(self.diretorio_sessao)
