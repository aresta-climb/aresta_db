# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket
import threading
import random
import mimetypes
import asyncio
from typing import Optional, Any
from pathlib import Path
from PySide6.QtCore import QObject, Signal

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from editor.core.codigo_sessao import obter_url_previa, DOMINIO_PREVIA_CANONICO
from editor.core.tunel_retransmissor import ClienteTunelRetransmissor, URL_HTTP_PREVIA_PADRAO

# Mapeamento customizado de extensões para garantir exibição correta no navegador (usado pelo StaticFiles nativamente)
mimetypes.add_type('text/plain', '.yaml')
mimetypes.add_type('text/plain', '.yml')
mimetypes.add_type('text/plain', '.md')
mimetypes.add_type('application/octet-stream', '.binarypb')


class ServidorCelular(QObject):
    """Gerencia um servidor HTTP local para conexão com o aplicativo móvel e túnel de retransmissão."""
    dispositivo_conectado = Signal()
    
    def __init__(
        self,
        pasta_compilado: Path | str,
        codigo_sessao: Optional[str] = None,
        url_retransmissor_ws: Optional[str] = None,
        jwt_token: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.pasta_compilado: Path = Path(pasta_compilado)
        self.codigo_sessao: Optional[str] = codigo_sessao
        self.url_retransmissor_ws: Optional[str] = url_retransmissor_ws
        self.url_previa_canonica: Optional[str] = None
        self.jwt_token: Optional[str] = jwt_token
        if not self.jwt_token:
            try:
                from editor.core.gerenciador_sessao import GerenciadorSessao
                sessao_usr = GerenciadorSessao().carregar_sessao()
                if sessao_usr and sessao_usr.jwt_supabase:
                    self.jwt_token = sessao_usr.jwt_supabase
            except Exception:
                pass
        self.porta: Optional[int] = None
        self.server: Any = None
        self._thread_servidor: Optional[threading.Thread] = None
        self._thread_tunel: Optional[threading.Thread] = None
        self._loop_tunel: Optional[asyncio.AbstractEventLoop] = None
        self.cliente_tunel: Optional[ClienteTunelRetransmissor] = None
        self._servindo: bool = False
        self.conectado: bool = False

    def solicitar_sessao_servidor(self, url_base: str = DOMINIO_PREVIA_CANONICO) -> bool:
        """Solicita ao Cloudflare Worker (POST /sessoes) a criação da sessão e armazena os dados oficiais."""
        if not self.jwt_token:
            return False

        from editor.core.tunel_retransmissor import solicitar_sessao_servidor as api_solicitar
        try:
            ip = self.obter_ip_local()
            porta = self.porta or 0
            dados = api_solicitar(url_base, self.jwt_token, ip_local=ip, porta_local=porta)
            if "codigo" in dados:
                self.codigo_sessao = dados["codigo"]
                self.url_previa_canonica = dados.get("url_previa")
                self.url_retransmissor_ws = dados.get("ws_url")
                return True
        except Exception:
            pass
        return False

    def obter_url_previa_canonica(self) -> str:
        """Retorna a URL pública canônica em previa.arestaclimb.com para o código desta sessão."""
        if self.url_previa_canonica:
            return self.url_previa_canonica
        if self.codigo_sessao:
            return obter_url_previa(self.codigo_sessao)
        if self.jwt_token and self.solicitar_sessao_servidor():
            if self.url_previa_canonica:
                return self.url_previa_canonica
        ip = self.obter_ip_local()
        porta = self.porta or 8000
        return f"http://{ip}:{porta}"

    def obter_porta_disponivel(self, inicio: int = 8000, fim: int = 9000, max_tentativas: int = 10) -> int:
        """Busca uma porta disponível no intervalo especificado."""
        for _ in range(max_tentativas):
            porta = random.randint(inicio, fim)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', porta)) != 0:
                    return porta
        return 0

    def obter_ip_local(self) -> str:
        """Retorna o endereço IP da máquina na rede local."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3.0)
        try:
            s.connect(('8.8.8.8', 80))
            ip = str(s.getsockname()[0])
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def gerar_qr_code(self, conteudo: str) -> bytes:
        """Gera um QR Code em memória e retorna o buffer de bytes da imagem PNG."""
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(conteudo)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, "PNG")
        return bytes(buffer.getvalue())

    def iniciar(self, conectar_tunel: bool = False) -> None:
        """Inicia o servidor HTTP ASGI e opcionalmente o túnel de retransmissão em threads separadas."""
        if self._servindo:
            return

        self._servindo = True
        
        def run_server() -> None:
            try:
                self.porta = self.obter_porta_disponivel()
                
                app = FastAPI(title="Servidor Celular Aresta", docs_url=None, redoc_url=None)
                
                @app.get("/handshake")
                def handshake() -> JSONResponse:
                    self.conectado = True
                    self.dispositivo_conectado.emit()
                    return JSONResponse(content={"status": "conectado"})

                @app.middleware("http")
                async def notify_connection(request: Request, call_next: Any) -> Any:
                    response = await call_next(request)
                    if response.status_code in (200, 206, 304) and request.url.path != "/favicon.ico":
                        self.conectado = True
                        self.dispositivo_conectado.emit()
                    return response

                app.mount("/", StaticFiles(directory=str(self.pasta_compilado)), name="static")

                config = uvicorn.Config(
                    app=app,
                    host="0.0.0.0",
                    port=self.porta,
                    log_level="warning",
                )
                self.server = uvicorn.Server(config)
                
                print(f"[INFO] Servidor Celular rodando em http://0.0.0.0:{self.porta}")
                self.server.run()
                print("[INFO] Loop ASGI do servidor celular encerrado com sucesso.")
            except Exception as e:
                import traceback
                print(f"[ERROR] Falha no servidor celular ASGI: {e}")
                traceback.print_exc()
            finally:
                self._servindo = False
                self.server = None
                print("[DEBUG] Thread do servidor celular finalizada.")

        self._thread_servidor = threading.Thread(target=run_server, daemon=True)
        self._thread_servidor.start()

        if conectar_tunel:
            self._iniciar_tunel()

    def _iniciar_tunel(self) -> None:
        """Inicia o cliente do túnel de retransmissão em background."""
        def run_tunel() -> None:
            self._loop_tunel = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop_tunel)

            ip_local = self.obter_ip_local()

            # Se possuir credenciais JWT e ainda não tiver URL oficial, requisita sessão ao servidor
            if self.jwt_token and not self.url_previa_canonica:
                self.solicitar_sessao_servidor()

            if not self.codigo_sessao:
                return

            self.cliente_tunel = ClienteTunelRetransmissor(
                codigo_sessao=self.codigo_sessao,
                pasta_compilado=self.pasta_compilado,
                url_retransmissor_ws=self.url_retransmissor_ws,
                ip_local=ip_local,
                porta_local=self.porta,
            )

            try:
                self._loop_tunel.run_until_complete(self.cliente_tunel.executar())
            except Exception:
                pass
            finally:
                if self._loop_tunel and not self._loop_tunel.is_closed():
                    self._loop_tunel.close()
                self._loop_tunel = None
                self.cliente_tunel = None

        self._thread_tunel = threading.Thread(target=run_tunel, daemon=True)
        self._thread_tunel.start()

    def emitir_recarregamento(self, setor_id: str) -> None:
        """Dispara evento de recarregamento em tempo real para os clientes conectados."""
        if self.cliente_tunel and self._loop_tunel and self._loop_tunel.is_running():
            asyncio.run_coroutine_threadsafe(
                self.cliente_tunel.emitir_recarregamento(setor_id),
                self._loop_tunel,
            )

    def parar(self) -> None:
        """Encerra o servidor HTTP e o túnel sem bloquear a UI."""
        if not self._servindo:
            return
            
        print("[DEBUG] Solicitando encerramento do servidor celular...")
        self._servindo = False
        self.conectado = False
        
        if self.server:
            print("[DEBUG] Setando should_exit = True no Uvicorn...")
            self.server.should_exit = True

        if self.cliente_tunel and self._loop_tunel and self._loop_tunel.is_running():
            asyncio.run_coroutine_threadsafe(
                self.cliente_tunel.parar(),
                self._loop_tunel,
            )
