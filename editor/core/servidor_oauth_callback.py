# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

HTML_RESPOSTA_SUCESSO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Autenticação Concluída</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 50px; background: #f8f9fa; color: #212529; }
        .card { background: white; border-radius: 12px; padding: 40px; max-width: 480px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h1 { color: #28a745; font-size: 24px; margin-bottom: 12px; }
        p { font-size: 16px; line-height: 1.5; color: #495057; }
    </style>
</head>
<body>
    <div class="card">
        <h1>✅ Autenticação concluída!</h1>
        <p>Sua conta foi conectada com sucesso ao Aresta Editor.<br>Você já pode fechar esta aba e retornar ao aplicativo.</p>
    </div>
</body>
</html>
"""

HTML_CAPTURAR_FRAGMENTO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Conectando ao Aresta...</title>
    <script>
        window.onload = function() {
            var hash = window.location.hash.substring(1);
            var params = new URLSearchParams(hash);
            var access_token = params.get("access_token");
            var refresh_token = params.get("refresh_token");
            var provider_token = params.get("provider_token");

            if (access_token) {
                fetch("/tokens", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        access_token: access_token,
                        refresh_token: refresh_token,
                        provider_token: provider_token
                    })
                }).then(function(res) {
                    return res.text();
                }).then(function(html) {
                    document.open();
                    document.write(html);
                    document.close();
                }).catch(function(err) {
                    document.body.innerHTML = "<h3>Erro ao transferir credenciais para o editor.</h3>";
                });
            } else {
                document.body.innerHTML = "<h3>Nenhum token encontrado na resposta de autorização.</h3>";
            }
        };
    </script>
    <style>
        body { font-family: sans-serif; text-align: center; padding: 50px; }
    </style>
</head>
<body>
    <p>Conectando credenciais ao Aresta Editor... Aguarde um instante.</p>
</body>
</html>
"""


class ManipuladorRequisicaoOAuth(BaseHTTPRequestHandler):
    """Manipulador HTTP para as requisições de callback do OAuth."""

    def log_message(self, format, *args):
        # Log opcional no terminal para depuração
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Se vier erro na query (ex: autorização negada ou falha do provedor)
        if "error" in params or "error_description" in params:
            erro = params.get(
                "error_description", params.get("error", ["Erro na autorização"])
            )[0]
            from editor.core.registro_log import logger
            logger.warning(f"[OAuth Callback] Erro retornado pelo provedor: {erro}")
            self.server.servidor_oauth.definir_tokens({"erro": erro})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_erro = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Falha na Autenticação</title><style>body {{ font-family: sans-serif; text-align: center; padding: 50px; background: #fff5f5; color: #721c24; }} .card {{ background: white; border-radius: 12px; padding: 30px; max-width: 480px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #f5c6cb; }}</style></head><body><div class="card"><h2>⚠️ Falha na Autenticação</h2><p>{erro}</p><p>Você pode fechar esta aba e tentar novamente no Aresta Editor.</p></div></body></html>"""
            self.wfile.write(html_erro.encode("utf-8"))
            return

        # Se os tokens vierem diretamente por query params (ex: code exchange ou redirect customizado)
        if "access_token" in params:
            from editor.core.registro_log import logger
            logger.info("[OAuth Callback] Tokens de autenticação recebidos via query params.")
            tokens = {
                "access_token": params["access_token"][0],
                "refresh_token": params.get("refresh_token", [""])[0],
                "provider_token": params.get("provider_token", [None])[0],
            }
            self.server.servidor_oauth.definir_tokens(tokens)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_RESPOSTA_SUCESSO.encode("utf-8"))
            return

        # Caso contrário, serve a página que extrai o fragmento #access_token=... via JavaScript
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CAPTURAR_FRAGMENTO.encode("utf-8"))

    def do_POST(self):
        if self.path == "/tokens":
            tamanho = int(self.headers.get("Content-Length", 0))
            corpo = self.rfile.read(tamanho)
            try:
                dados = json.loads(corpo.decode("utf-8"))
                from editor.core.registro_log import logger
                logger.info("[OAuth Callback] Tokens de autenticação recebidos via POST /tokens.")
                self.server.servidor_oauth.definir_tokens(dados)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTML_RESPOSTA_SUCESSO.encode("utf-8"))
            except Exception as e:
                from editor.core.registro_log import logger
                logger.error(f"[OAuth Callback] Erro ao processar tokens recebidos via POST: {e}", exc_info=True)
                self.send_response(400)
                self.end_headers()


from PyQt6.QtCore import QObject, pyqtSignal


class ServidorCallbackOAuth(QObject):
    """
    Servidor HTTP efêmero local para receber os tokens do Supabase OAuth.
    """

    tokens_recebidos = pyqtSignal(dict)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._servidor_http: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._porta: int = 0
        self._evento_conclusao = threading.Event()
        self._tokens_recebidos: Optional[Dict[str, Any]] = None

    def iniciar_escuta(self) -> int:
        """Inicia o servidor em uma porta dinâmica livre alocada pelo SO."""
        self._servidor_http = HTTPServer(
            ("127.0.0.1", 0), ManipuladorRequisicaoOAuth
        )
        self._servidor_http.servidor_oauth = self
        self._porta = self._servidor_http.server_port

        self._thread = threading.Thread(
            target=self._servidor_http.serve_forever, daemon=True
        )
        self._thread.start()
        return self._porta

    def obter_url_redirecionamento(self) -> str:
        """Retorna a URL de callback a ser passada no redirect_to do OAuth."""
        return f"http://localhost:{self._porta}/callback"

    def definir_tokens(self, tokens: Dict[str, Any]) -> None:
        """Registra os tokens recebidos e sinaliza o evento de conclusão."""
        self._tokens_recebidos = tokens
        self._evento_conclusao.set()
        self.tokens_recebidos.emit(tokens)

    def aguardar_tokens(
        self, tempo_limite: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Bloqueia até que os tokens sejam recebidos ou ocorra timeout."""
        concluido = self._evento_conclusao.wait(timeout=tempo_limite)
        if concluido:
            return self._tokens_recebidos
        return None

    def encerrar(self) -> None:
        """Encerra o servidor e fecha a conexão do socket."""
        if self._servidor_http:
            try:
                self._servidor_http.shutdown()
                self._servidor_http.server_close()
            except Exception:
                pass
            self._servidor_http = None
