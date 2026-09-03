# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

"""Biblioteca modular para o cliente WebSocket de saída do túnel de retransmissão."""

import asyncio
import json
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, Callable, cast
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
        return cast(Dict[str, Any], json.loads(corpo))


class ClienteTunelRetransmissor:
    """Gerencia a conexão WebSocket de saída com o retransmissor na nuvem e o streaming de arquivos."""

    def __init__(
        self,
        codigo_sessao: str,
        pasta_compilado: Path,
        url_retransmissor_ws: Optional[str] = None,
        ip_local: Optional[str] = None,
        porta_local: Optional[int] = None,
        ao_conectar_dispositivo: Optional[Callable[[], None]] = None,
        jwt_token: Optional[str] = None,
        obter_jwt_atualizado: Optional[Callable[[], Optional[str]]] = None,
    ) -> None:
        self.codigo_sessao = codigo_sessao
        self.pasta_compilado = Path(pasta_compilado).resolve()
        self._url_retransmissor_ws_configurada = url_retransmissor_ws
        self.ip_local = ip_local
        self.porta_local = porta_local
        self.ao_conectar_dispositivo = ao_conectar_dispositivo
        self.jwt_token = jwt_token
        self.obter_jwt_atualizado = obter_jwt_atualizado
        self._rodando = False
        self._websocket: Optional[Any] = None
        self._evento_parada = asyncio.Event()

    def _obter_url_conexao(self) -> str:
        """Gera a URL de conexão WebSocket incluindo o código e o token JWT atualizado quando disponível."""
        if self._url_retransmissor_ws_configurada:
            url = self._url_retransmissor_ws_configurada
        else:
            url = f"{URL_RETRANSMISSOR_PADRAO}?sessao={self.codigo_sessao}"

        token_atual: Optional[str] = None
        if self.obter_jwt_atualizado:
            try:
                token_atual = self.obter_jwt_atualizado()
            except Exception:
                pass
        if not token_atual and self.jwt_token:
            token_atual = self.jwt_token

        if token_atual and "token=" not in url:
            separador = "&" if "?" in url else "?"
            url = f"{url}{separador}token={token_atual.strip()}"

        return url

    @property
    def url_retransmissor_ws(self) -> str:
        return self._obter_url_conexao()

    @url_retransmissor_ws.setter
    def url_retransmissor_ws(self, valor: Optional[str]) -> None:
        self._url_retransmissor_ws_configurada = valor

    async def _loop_heartbeat(self, ws: Any, intervalo: float) -> None:
        """Envia pings periódicos de heartbeat em segundo plano sem interromper a escuta de mensagens."""
        while not self._evento_parada.is_set():
            try:
                await asyncio.sleep(intervalo)
                if self._evento_parada.is_set():
                    break
                await ws.send(json.dumps({"tipo": "ping"}))
            except asyncio.CancelledError:
                break
            except Exception:
                break

    async def executar(self, intervalo_heartbeat: float = 30.0) -> None:
        """Inicia e mantém o loop de conexão WebSocket com o retransmissor e reconexão automática."""
        self._rodando = True
        self._evento_parada.clear()
        tentativas_falhas = 0

        while not self._evento_parada.is_set():
            try:
                url_ws = self._obter_url_conexao()
                async with websockets.connect(
                    url_ws,
                    ping_interval=intervalo_heartbeat,
                    ping_timeout=intervalo_heartbeat,
                    close_timeout=5,
                ) as ws:
                    self._websocket = ws
                    tentativas_falhas = 0

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

                    # 2. Inicia corrotina dedicada de heartbeat em segundo plano
                    tarefa_heartbeat = asyncio.create_task(
                        self._loop_heartbeat(ws, intervalo_heartbeat)
                    )

                    try:
                        # 3. Loop de escuta de mensagens contínuo
                        while not self._evento_parada.is_set():
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
                                erro = tarefa_receber.exception()
                                if erro is not None:
                                    break
                                mensagem = tarefa_receber.result()
                                try:
                                    dados = json.loads(mensagem)
                                    await self._tratar_mensagem(dados, ws)
                                except Exception:
                                    pass
                    finally:
                        tarefa_heartbeat.cancel()
                        try:
                            await tarefa_heartbeat
                        except (asyncio.CancelledError, Exception):
                            pass
            except (ConnectionClosed, asyncio.CancelledError, Exception):
                if self._evento_parada.is_set():
                    break
                tentativas_falhas += 1
                tempo_espera = min(5.0, 0.2 * (2 ** min(tentativas_falhas, 4)))
                await asyncio.sleep(tempo_espera)
            finally:
                self._websocket = None

        self._rodando = False

    async def emitir_recarregamento(self, setor_id: str) -> None:
        """Envia uma notificação push de recarregamento em tempo real para os clientes conectados."""
        print(f"⚡ [TunelRetransmissor] emitir_recarregamento('{setor_id}') | ws={self._websocket is not None}, rodando={self._rodando}")
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
                print(f"⚡ [TunelRetransmissor] ✅ Push de recarga enviado para o Cloudflare com sucesso: {payload}")
            except Exception as e:
                print(f"🛑 [TunelRetransmissor] Falha ao enviar payload de recarga: {e}")
        else:
            print(f"⚠️ [TunelRetransmissor] WebSocket não conectado ou túnel inativo (ws={self._websocket}, rodando={self._rodando})")

    async def _tratar_mensagem(self, dados: Dict[str, Any], ws: Any) -> None:
        """Processa mensagens recebidas do retransmissor."""
        tipo = dados.get("tipo")

        if tipo == "requisicao_proxy":
            if self.ao_conectar_dispositivo:
                try:
                    self.ao_conectar_dispositivo()
                except Exception:
                    pass

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
