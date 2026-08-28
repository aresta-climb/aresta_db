# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import socket
import threading
import random
import mimetypes
from pathlib import Path
from PySide6.QtCore import QObject, Signal

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Mapeamento customizado de extensões para garantir exibição correta no navegador (usado pelo StaticFiles nativamente)
mimetypes.add_type('text/plain', '.yaml')
mimetypes.add_type('text/plain', '.yml')
mimetypes.add_type('text/plain', '.md')
mimetypes.add_type('application/octet-stream', '.binarypb')

class ServidorCelular(QObject):
    """Gerencia um servidor HTTP local para conexão com o aplicativo móvel usando FastAPI/Uvicorn."""
    dispositivo_conectado = Signal()
    
    def __init__(self, pasta_compilado, parent=None):
        super().__init__(parent)
        self.pasta_compilado = Path(pasta_compilado)
        self.porta = None
        self.server = None
        self.thread = None
        self._servindo = False
        self.conectado = False

    def obter_porta_disponivel(self, inicio=8000, fim=9000, max_tentativas=10):
        """Busca uma porta disponível no intervalo especificado."""
        for _ in range(max_tentativas):
            porta = random.randint(inicio, fim)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', porta)) != 0:
                    return porta
        return 0

    def obter_ip_local(self):
        """Retorna o endereço IP da máquina na rede local."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3.0) # Timeout mais confortável, rodando em background
        try:
            # Não precisa conectar de verdade, apenas para o SO escolher a interface
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def gerar_qr_code(self, conteudo):
        """Gera um QR Code em memória e retorna o buffer de bytes da imagem PNG."""
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2, # Mais compacto
        )
        qr.add_data(conteudo)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def iniciar(self):
        """Inicia o servidor HTTP ASGI em uma thread separada."""
        if self._servindo:
            return

        self._servindo = True
        
        def run_server():
            try:
                # Obtém a porta dentro da thread
                self.porta = self.obter_porta_disponivel()
                
                app = FastAPI(title="Servidor Celular Aresta", docs_url=None, redoc_url=None)
                
                @app.get("/handshake")
                def handshake():
                    self.conectado = True
                    self.dispositivo_conectado.emit()
                    return JSONResponse(content={"status": "conectado"})

                @app.middleware("http")
                async def notify_connection(request: Request, call_next):
                    response = await call_next(request)
                    # Notificar via sinal qt sempre que um recurso for acessado com sucesso
                    if response.status_code in (200, 206, 304) and request.url.path != "/favicon.ico":
                        self.conectado = True
                        self.dispositivo_conectado.emit()
                    return response

                # Monta a pasta de arquivos compilados, gerenciando ETags e 304 nativamente
                app.mount("/", StaticFiles(directory=str(self.pasta_compilado)), name="static")

                config = uvicorn.Config(
                    app=app,
                    host="0.0.0.0",
                    port=self.porta,
                    log_level="warning", # Para não poluir o terminal, igual ao http.server
                )
                self.server = uvicorn.Server(config)
                
                from editor.core.registro_log import logger
                logger.info(f"Servidor Celular rodando em http://0.0.0.0:{self.porta}")
                # run() é bloqueante e vai rodar o asyncio event loop desta thread
                self.server.run()
                logger.info("Loop ASGI do servidor celular encerrado com sucesso.")
            except Exception as e:
                from editor.core.registro_log import logger
                logger.error(f"Falha no servidor celular ASGI: {e}", exc_info=True)
            finally:
                self._servindo = False
                self.server = None
                from editor.core.registro_log import logger
                logger.debug("Thread do servidor celular finalizada.")

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

    def parar(self):
        """Encerra o servidor HTTP sem bloquear a UI e sem usar threads extras."""
        if not self._servindo:
            return
            
        from editor.core.registro_log import logger
        logger.debug("Solicitando encerramento do servidor celular...")
        self._servindo = False
        self.conectado = False
        
        if self.server:
            logger.debug("Setando should_exit = True no Uvicorn...")
            self.server.should_exit = True
            logger.info("Sinal de encerramento nativo enviado para o servidor celular.")
