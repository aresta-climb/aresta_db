# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning:websockets.*",
    "ignore::DeprecationWarning:uvicorn.*"
)
from editor.core.servidor_celular import ServidorCelular
from pathlib import Path
import socket
import requests
import time
import asyncio
import websockets
import json
from unittest.mock import patch, MagicMock

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
    if servidor._thread_servidor and servidor._thread_servidor.is_alive():
        servidor._thread_servidor.join(timeout=3.0)


def test_deve_emitir_sinal_quando_receber_conexao(tmp_path, qtbot):
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    
    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)
    
    with qtbot.waitSignal(servidor.dispositivo_conectado, timeout=2000):
        arquivo_teste = pasta_compilado / "index.json"
        arquivo_teste.write_text('{"status": "ok"}', encoding="utf-8")
        
        url = f"http://127.0.0.1:{servidor.porta}/index.json"
        requests.get(url)
    
    servidor.parar()
    if servidor._thread_servidor and servidor._thread_servidor.is_alive():
        servidor._thread_servidor.join(timeout=3.0)


def test_deve_gerar_qr_code_em_memoria(qapp):
    servidor = ServidorCelular(Path("."))
    conteudo = "http://192.168.1.10:8080"
    buffer = servidor.gerar_qr_code(conteudo)
    
    assert isinstance(buffer, bytes)
    try:
        from PySide6.QtGui import QPixmap
    except ImportError:
        from PyQt6.QtGui import QPixmap
    pixmap = QPixmap()
    sucesso = pixmap.loadFromData(buffer)
    assert sucesso is True
    assert not pixmap.isNull()

def test_deve_obter_ip_local():
    servidor = ServidorCelular(Path("."))
    with patch("socket.socket") as mock_socket_cls:
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.105", 12345)
        mock_socket_cls.return_value = mock_sock
        ip = servidor.obter_ip_local()
        assert ip == "192.168.1.105"


def test_deve_obter_ip_local_fallback_offline():
    servidor = ServidorCelular(Path("."))
    with patch("socket.socket") as mock_socket_cls:
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("Rede inalcançável")
        mock_socket_cls.return_value = mock_sock
        ip = servidor.obter_ip_local()
        assert ip == "127.0.0.1"

def test_deve_suportar_http1_1_e_keep_alive(tmp_path):
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    
    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)
    
    url = f"http://127.0.0.1:{servidor.porta}/handshake"
    
    with requests.Session() as s:
        resposta = s.get(url)
        assert resposta.status_code == 200
        assert resposta.json() == {"status": "conectado"}
        
        assert "Content-Length" in resposta.headers
        assert int(resposta.headers["Content-Length"]) > 0
        
        resposta_2 = s.get(url)
        assert resposta_2.status_code == 200
    
    servidor.parar()
    if servidor._thread_servidor and servidor._thread_servidor.is_alive():
        servidor._thread_servidor.join(timeout=3.0)


def test_deve_retornar_304_se_etag_sha256_bater(tmp_path):
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    arquivo_teste = pasta_compilado / "dados.bin"
    conteudo = b"dados super pesados do croqui"
    arquivo_teste.write_bytes(conteudo)
    
    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)
    
    url = f"http://127.0.0.1:{servidor.porta}/dados.bin"
    
    with requests.Session() as s:
        resp1 = s.get(url)
        assert resp1.status_code == 200
        assert "ETag" in resp1.headers
        
        etag = resp1.headers["ETag"]
        
        resp2 = s.get(url, headers={"If-None-Match": etag})
        assert resp2.status_code == 304
        assert not resp2.content
        assert resp2.headers.get("ETag") == etag
        
        resp3 = s.get(url, headers={"If-None-Match": '"fake-hash"'})
        assert resp3.status_code == 200
        
    servidor.parar()
    if servidor._thread_servidor and servidor._thread_servidor.is_alive():
        servidor._thread_servidor.join(timeout=3.0)


def test_deve_construir_url_previa_canonica_e_conectar_tunel(tmp_path):
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    mensagens_recebidas = []

    async def mock_ws_server(websocket):
        try:
            async for msg in websocket:
                mensagens_recebidas.append(json.loads(msg))
        except websockets.exceptions.ConnectionClosed:
            pass

    async def run_test():
        async with websockets.serve(mock_ws_server, "127.0.0.1", 0) as server:
            porta_ws = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta_ws}/ws?sessao=k9x2p83a"

            servidor = ServidorCelular(
                pasta_compilado=pasta_compilado,
                codigo_sessao="k9x2p83a",
                url_retransmissor_ws=url_ws,
            )

            assert servidor.obter_url_previa_canonica() == "https://previa.arestaclimb.com/k9x2-p83a"

            servidor.iniciar()
            esperar_porta(servidor)

            for _ in range(40):
                if any(m.get("tipo") == "registro" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            servidor.emitir_recarregamento("br_mg_ferros_setor1")

            for _ in range(40):
                if any(m.get("tipo") == "evento" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            servidor.parar()

            assert any(m.get("tipo") == "registro" for m in mensagens_recebidas)
            msg_evento = next(m for m in mensagens_recebidas if m.get("tipo") == "evento")
            assert msg_evento["dados"]["setor"] == "br_mg_ferros_setor1"

    asyncio.run(run_test())


def test_deve_solicitar_sessao_ao_servidor_remoto(tmp_path):
    """ServidorCelular deve atualizar codigo_sessao e url_previa com o retorno da API."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    servidor = ServidorCelular(
        pasta_compilado=pasta_compilado,
        jwt_token="jwt_valido_mock",
    )

    with patch("editor.core.tunel_retransmissor.solicitar_sessao_servidor", return_value={
        "codigo": "x7m4n2q1",
        "codigo_formatado": "x7m4-n2q1",
        "url_previa": "https://previa.arestaclimb.com/x7m4-n2q1",
        "ws_url": "wss://previa.arestaclimb.com/ws?sessao=x7m4n2q1&token=jwt_valido_mock",
    }):
        sucesso = servidor.solicitar_sessao_servidor()
        assert sucesso is True
        assert servidor.codigo_sessao == "x7m4n2q1"
        assert servidor.obter_url_previa_canonica() == "https://previa.arestaclimb.com/x7m4-n2q1"
        assert servidor.url_retransmissor_ws == "wss://previa.arestaclimb.com/ws?sessao=x7m4n2q1&token=jwt_valido_mock"


def test_deve_recuperar_jwt_automaticamente_do_gerenciador_sessao(tmp_path):
    """Quando jwt_token for None, deve buscar automaticamente no GerenciadorSessao."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    with patch("editor.core.gerenciador_sessao.GerenciadorSessao.recuperar_token", return_value="jwt_auto_recuperado"):
        servidor = ServidorCelular(pasta_compilado=pasta_compilado)
        assert servidor.jwt_token == "jwt_auto_recuperado"


def test_servidor_celular_inicia_tunel_com_jwt_e_callback(tmp_path):
    """Verifica se o túnel retransmissor recebe jwt_token e obter_jwt_atualizado ao iniciar."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    instancias_criadas = []

    class MockClienteTunel:
        def __init__(self, **kwargs):
            instancias_criadas.append(kwargs)
        async def executar(self):
            pass
        async def parar(self):
            pass

    with patch("editor.core.servidor_celular.ClienteTunelRetransmissor", side_effect=MockClienteTunel):
        servidor = ServidorCelular(
            pasta_compilado=pasta_compilado,
            codigo_sessao="tstjwt12",
            url_retransmissor_ws="ws://127.0.0.1:8080/ws?sessao=tstjwt12",
            jwt_token="jwt_passado_teste",
        )
        servidor.iniciar()
        esperar_porta(servidor)

        # Aguarda thread do túnel iniciar
        for _ in range(30):
            if len(instancias_criadas) > 0:
                break
            time.sleep(0.05)

        servidor.parar()

        assert len(instancias_criadas) == 1
        assert instancias_criadas[0]["jwt_token"] == "jwt_passado_teste"
        assert callable(instancias_criadas[0]["obter_jwt_atualizado"])

