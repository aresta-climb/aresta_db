import pytest
from editor.core.servidor_celular import ServidorCelular
from pathlib import Path
import socket
import requests
import time

def test_deve_encontrar_porta_livre_automaticamente(tmp_path):
    servidor = ServidorCelular(tmp_path)
    porta = servidor.obter_porta_disponivel()
    
    assert porta >= 1024
    assert porta <= 65535
    
    # Verifica se a porta está realmente livre
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        resultado = s.connect_ex(('127.0.0.1', porta))
        assert resultado != 0, f"Porta {porta} deveria estar livre"

def esperar_porta(servidor, timeout=5.0):
    """Aguarda o servidor descobrir uma porta livre em background."""
    inicio = time.time()
    while servidor.porta is None and (time.time() - inicio) < timeout:
        time.sleep(0.1)
    if servidor.porta is None:
        pytest.fail("Timeout esperando porta do servidor")

def test_deve_iniciar_servidor_http_e_servir_arquivos(tmp_path):
    # Cria um arquivo de teste na pasta compilada
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    arquivo_teste = pasta_compilado / "index.json"
    arquivo_teste.write_text('{"status": "ok"}', encoding="utf-8")
    
    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)
    
    url = f"http://127.0.0.1:{servidor.porta}/index.json"
    resposta = requests.get(url)
    
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
    
    servidor.parar()

def test_deve_emitir_sinal_quando_receber_conexao(tmp_path, qtbot):
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    
    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)
    
    with qtbot.waitSignal(servidor.dispositivo_conectado, timeout=2000):
        # Agora qualquer GET deve emitir sinal, não só /handshake
        # Mas o arquivo DEVE existir para ser considerado uma conexão válida
        arquivo_teste = pasta_compilado / "index.json"
        arquivo_teste.write_text('{"status": "ok"}', encoding="utf-8")
        
        url = f"http://127.0.0.1:{servidor.porta}/index.json"
        requests.get(url)
    
    servidor.parar()

def test_deve_mostrar_listagem_de_diretorio(tmp_path):
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    
    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)
    
    # Tenta acessar a raiz (diretório)
    url = f"http://127.0.0.1:{servidor.porta}/"
    resposta = requests.get(url)
    
    # Deve retornar 200 (pois a listagem de diretório foi habilitada para debug)
    assert resposta.status_code == 200
    
    servidor.parar()

def test_deve_gerar_qr_code_em_memoria(qapp):
    servidor = ServidorCelular(Path("."))
    conteudo = "http://192.168.1.10:8080"
    buffer = servidor.gerar_qr_code(conteudo)
    
    assert isinstance(buffer, bytes)
    assert len(buffer) > 100 # Deve ter algum conteúdo de imagem
    
    # Verifica se o PyQt6 consegue carregar
    from PyQt6.QtGui import QPixmap
    pixmap = QPixmap()
    sucesso = pixmap.loadFromData(buffer)
    assert sucesso is True
    assert not pixmap.isNull()

def test_deve_obter_ip_local():
    servidor = ServidorCelular(Path("."))
    ip = servidor.obter_ip_local()
    
    assert ip is not None
    assert "." in ip
    # Verifica se não é o localhost 127.0.0.1 (queremos o IP da rede Wi-Fi/LAN)
    assert ip != "127.0.0.1"
