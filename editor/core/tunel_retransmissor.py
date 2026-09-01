# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

"""Biblioteca modular para o cliente WebSocket de saída do túnel de retransmissão."""

import asyncio
import json
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
import websockets
from websockets.exceptions import ConnectionClosed

import urllib.request
import urllib.error

URL_RETRANSMISSOR_PADRAO = "wss://previa.arestaclimb.com/ws"
URL_HTTP_PREVIA_PADRAO = "https://previa.arestaclimb.com"


def solicitar_sessao_servidor(
    url_base: str,
    jwt_token: str,
    ip_local: Optional[str] = None,
    porta_local: Optional[int] = None,
    timeout_segundos: float = 10.0,
) -> Dict[str, Any]:
    """
    Solicita ao Cloudflare Worker (POST /sessoes) a criação de uma sessão autenticada.
    Retorna o dicionário contendo codigo, codigo_formatado, url_previa e ws_url.
    """
    if not jwt_token:
        raise ValueError("Token JWT obrigatório para autenticar no Cloudflare Worker.")

    url = f"{url_base.rstrip('/')}/sessoes"
    payload_dict: Dict[str, Any] = {}
    if ip_local:
        payload_dict["ipLocal"] = ip_local
    if porta_local:
        payload_dict["portaLocal"] = porta_local

    dados_bytes = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=dados_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jwt_token.strip()}",
            "User-Agent": "ArestaEditorDesktop/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout_segundos) as resposta:
        corpo = resposta.read().decode("utf-8")
        return json.loads(corpo)


class ClienteTunelRetransmissor:
    """Gerencia a conexão WebSocket de saída com o retransmissor na nuvem e o streaming de arquivos."""

    def __init__(
        self,
        codigo_sessao: str,
        pasta_compilado: Path,
        url_retransmissor_ws: Optional[str] = None,
        ip_local: Optional[str] = None,
        porta_local: Optional[int] = None,
    ):
        self.codigo_sessao = codigo_sessao
        self.pasta_compilado = Path(pasta_compilado).resolve()
        self.url_retransmissor_ws = (
            url_retransmissor_ws
            or f"{URL_RETRANSMISSOR_PADRAO}?sessao={codigo_sessao}"
        )
        self.ip_local = ip_local
        self.porta_local = porta_local
        self._rodando = False
        self._websocket = None
        self._evento_parada = asyncio.Event()

    async def executar(self) -> None:
        """Inicia e mantém o loop de conexão WebSocket com o retransmissor."""
        self._rodando = True
        self._evento_parada.clear()

        try:
            async with websockets.connect(self.url_retransmissor_ws) as ws:
                self._websocket = ws

                # 1. Envia mensagem inicial de registro com metadados de rede
                payload_registro: Dict[str, Any] = {
                    "tipo": "registro",
                    "dados": {
                        "codigo": self.codigo_sessao,
                        "ipLocal": self.ip_local,
                        "portaLocal": self.porta_local,
                        "urlLocal": (
                            f"http://{self.ip_local}:{self.porta_local}"
                            if self.ip_local and self.porta_local
                            else None
                        ),
                    },
                }
                await ws.send(json.dumps(payload_registro))

                # 2. Loop de escuta de mensagens
                while self._rodando:
                    tarefa_receber = asyncio.create_task(ws.recv())
                    tarefa_parada = asyncio.create_task(self._evento_parada.wait())

                    concluidas, pendentes = await asyncio.wait(
                        [tarefa_receber, tarefa_parada],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    for p in pendentes:
                        p.cancel()

                    if self._evento_parada.is_set():
                        break

                    if tarefa_receber in concluidas:
                        try:
                            mensagem = tarefa_receber.result()
                            dados = json.loads(mensagem)
                            await self._tratar_mensagem(dados, ws)
                        except Exception:
                            pass
        except (ConnectionClosed, asyncio.CancelledError, Exception):
            pass
        finally:
            self._rodando = False
            self._websocket = None

    async def emitir_recarregamento(self, setor_id: str) -> None:
        """Envia uma notificação push de recarregamento em tempo real para os clientes conectados."""
        if self._websocket and self._rodando:
            try:
                payload = {
                    "tipo": "evento",
                    "dados": {
                        "tipo": "recarregar",
                        "setor": setor_id,
                    },
                }
                await self._websocket.send(json.dumps(payload))
            except Exception:
                pass

    async def _tratar_mensagem(self, dados: Dict[str, Any], ws: Any) -> None:
        """Processa mensagens recebidas do retransmissor."""
        tipo = dados.get("tipo")

        if tipo == "requisicao_proxy":
            req = dados.get("dados", {})
            req_id = req.get("id")
            caminho = req.get("caminho", "").lstrip("/")

            resposta = self._ler_arquivo_proxy(req_id, caminho)
            await ws.send(
                json.dumps({
                    "tipo": "resposta_proxy",
                    "dados": resposta,
                })
            )
        elif tipo == "ping":
            await ws.send(json.dumps({"tipo": "pong"}))

    def _ler_arquivo_proxy(self, req_id: str, caminho_relativo: str) -> Dict[str, Any]:
        """Lê um arquivo da pasta compilada e formata a resposta base64 com isolamento total de diretório."""
        try:
            pasta_base = self.pasta_compilado.resolve()
            
            # Sanitiza caracteres nulos e barras iniciais para evitar escape de caminho absoluto
            caminho_limpo = str(caminho_relativo).replace("\x00", "").lstrip("/\\")
            caminho_alvo = (pasta_base / caminho_limpo).resolve()

            # Prevenção rigorosa contra Directory Traversal e Path Escaping
            if not caminho_alvo.is_relative_to(pasta_base):
                return {
                    "id": req_id,
                    "status": 403,
                    "cabecalhos": {"content-type": "application/json"},
                    "corpoBase64": base64.b64encode(
                        json.dumps({"erro": "Acesso negado: caminho fora do escopo permitido."}).encode()
                    ).decode(),
                }

            if not caminho_alvo.is_file():
                return {
                    "id": req_id,
                    "status": 404,
                    "cabecalhos": {"content-type": "application/json"},
                    "corpoBase64": base64.b64encode(
                        json.dumps({"erro": "Arquivo não encontrado"}).encode()
                    ).decode(),
                }

            conteudo_bytes = caminho_alvo.read_bytes()
            tipo_mime, _ = mimetypes.guess_type(str(caminho_alvo))
            if not tipo_mime:
                if caminho_alvo.suffix in (".binarypb", ".bin"):
                    tipo_mime = "application/octet-stream"
                else:
                    tipo_mime = "text/plain"

            return {
                "id": req_id,
                "status": 200,
                "cabecalhos": {
                    "content-type": tipo_mime,
                    "content-length": str(len(conteudo_bytes)),
                },
                "corpoBase64": base64.b64encode(conteudo_bytes).decode(),
            }
        except Exception as e:
            return {
                "id": req_id,
                "status": 500,
                "cabecalhos": {"content-type": "application/json"},
                "corpoBase64": base64.b64encode(
                    json.dumps({"erro": str(e)}).encode()
                ).decode(),
            }

    async def parar(self) -> None:
        """Solicita o encerramento gracioso do túnel."""
        self._rodando = False
        self._evento_parada.set()
        if self._websocket:
            try:
                await self._websocket.close(1000, "Editor desconectado")
            except Exception:
                pass
