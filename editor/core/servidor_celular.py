import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from PyQt6.QtCore import QObject, pyqtSignal
import random
from pathlib import Path
import hashlib

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP que trata cada requisição em uma thread separada.
    Isso evita que uma conexão lenta de celular trave o servidor ou o shutdown.
    """
    daemon_threads = True

class ManipuladorHandshake(SimpleHTTPRequestHandler):
    """Manipulador que emite um sinal quando uma requisição é recebida."""
    
    # Habilita HTTP/1.1 para suportar Keep-Alive nativamente
    protocol_version = "HTTP/1.1"

    # Mapeamento customizado de extensões para garantir exibição correta no navegador
    extensions_map = SimpleHTTPRequestHandler.extensions_map.copy()
    extensions_map.update({
        '.yaml': 'text/plain; charset=utf-8',
        '.yml': 'text/plain; charset=utf-8',
        '.md': 'text/plain; charset=utf-8',
        '.binarypb': 'application/octet-stream',
    })

    def __init__(self, *args, servidor_obj=None, **kwargs):
        self.servidor_obj = servidor_obj
        self.current_etag = None
        super().__init__(*args, **kwargs)

    def _calcular_sha256(self, caminho_arquivo):
        """Calcula o SHA-256 de um arquivo lendo em chunks para economizar RAM."""
        sha256 = hashlib.sha256()
        try:
            with open(caminho_arquivo, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return f'"{sha256.hexdigest()}"'
        except Exception:
            return None

    def end_headers(self):
        """Sobrescreve o end_headers para injetar o ETag se existir."""
        if hasattr(self, 'current_etag') and self.current_etag:
            self.send_header('ETag', self.current_etag)
        super().end_headers()

    def do_GET(self):
        # Traduz o caminho da URL para o caminho do sistema de arquivos
        caminho_fisico = Path(self.translate_path(self.path))
        eh_arquivo_real = caminho_fisico.is_file()
        eh_handshake = self.path == "/handshake"

        # Lógica de ETag e HTTP 304 para arquivos
        if eh_arquivo_real:
            etag = self._calcular_sha256(caminho_fisico)
            if etag:
                self.current_etag = etag
                if_none_match = self.headers.get('If-None-Match')
                if if_none_match == etag:
                    self.send_response(304)
                    self.end_headers()
                    return

        # Emite o sinal se o recurso existir ou for o handshake
        # Nota: diretórios agora também são válidos para listagem
        recurso_existe = eh_arquivo_real or caminho_fisico.is_dir()
        
        if self.servidor_obj and (recurso_existe or eh_handshake):
            if self.path != "/favicon.ico":
                print(f"[INFO] Requisição válida em {self.path}. Dispositivo conectado.")
                self.servidor_obj.conectado = True
                self.servidor_obj.dispositivo_conectado.emit()

        if eh_handshake:
            conteudo = b'{"status": "conectado"}'
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)
            return

        return super().do_GET()

class ServidorCelular(QObject):
    """Gerencia um servidor HTTP local para conexão com o aplicativo móvel."""
    dispositivo_conectado = pyqtSignal()
    
    def __init__(self, pasta_compilado, parent=None):
        super().__init__(parent)
        self.pasta_compilado = Path(pasta_compilado)
        self.porta = None
        self.httpd = None
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
        # Se falhar as tentativas, deixa o SO escolher uma porta (porta 0)
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
        """Inicia o servidor HTTP em uma thread separada."""
        if self._servindo:
            return

        self._servindo = True
        
        def run_server():
            try:
                # Obtém a porta dentro da thread
                self.porta = self.obter_porta_disponivel()
                
                def handler_factory(*args, **kwargs):
                    return ManipuladorHandshake(*args, servidor_obj=self, directory=str(self.pasta_compilado), **kwargs)

                self.httpd = ThreadedHTTPServer(('0.0.0.0', self.porta), handler_factory)
                # Garante que a porta final seja a do servidor (caso o SO tenha escolhido uma diferente)
                self.porta = self.httpd.server_port
                print(f"[INFO] Servidor Celular rodando em http://0.0.0.0:{self.porta}")
                self.httpd.serve_forever()
                print("[INFO] Loop serve_forever() do servidor celular encerrado com sucesso.")
            except Exception as e:
                import traceback
                print(f"[ERROR] Falha no servidor celular: {e}")
                traceback.print_exc()
            finally:
                self._servindo = False
                print("[DEBUG] Thread do servidor celular finalizada.")

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

    def parar(self):
        """Encerra o servidor HTTP sem bloquear a UI."""
        if not self._servindo:
            return
            
        print("[DEBUG] Solicitando encerramento do servidor celular...")
        self._servindo = False
        self.conectado = False
        
        # Copia referências para a thread de shutdown
        httpd_para_fechar = self.httpd
        
        def shutdown_process():
            try:
                if httpd_para_fechar:
                    print("[DEBUG] Chamando httpd.shutdown()...")
                    # shutdown() acorda o loop serve_forever e o encerra
                    httpd_para_fechar.shutdown()
                    print("[DEBUG] httpd.shutdown() retornou. Fechando socket...")
                    httpd_para_fechar.server_close()
                    print("[INFO] Socket do servidor celular liberado.")
            except Exception as e:
                print(f"[WARN] Erro ao encerrar HTTPd em background: {e}")

        # Executa o shutdown em uma thread separada para evitar QUALQUER travamento na UI
        threading.Thread(target=shutdown_process, daemon=True).start()
            
        self.httpd = None
        self.thread = None
        print("[INFO] Sinal de encerramento enviado para o servidor celular.")
