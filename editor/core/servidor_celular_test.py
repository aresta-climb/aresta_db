# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning:websockets.*", "ignore::DeprecationWarning:uvicorn.*"
)
import asyncio
import json
import socket
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
import websockets

from editor.core.servidor_celular import ServidorCelular


def test_deve_encontrar_porta_livre_automaticamente(tmp_path):
    servidor = ServidorCelular(tmp_path)
    porta = servidor.obter_porta_disponivel()

    assert porta >= 1024
    assert porta <= 65535

    # Verifica se a porta está realmente livre
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        resultado = s.connect_ex(("127.0.0.1", porta))
        assert resultado != 0, f"Porta {porta} deveria estar livre"


def esperar_porta(servidor, timeout=5.0):
    """Aguarda o servidor estar pronto e aceitando conexões na porta em background."""
    inicio = time.time()
    while (time.time() - inicio) < timeout:
        if servidor.porta is not None:
            try:
                with socket.create_connection(("127.0.0.1", servidor.porta), timeout=0.1):
                    return
            except OSError:
                pass
        time.sleep(0.05)
    pytest.fail("Timeout esperando o servidor iniciar e aceitar conexões")


def test_deve_iniciar_servidor_http_e_servir_arquivos(tmp_path):
    # Cria um arquivo de teste na pasta compilada
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()
    arquivo_teste = pasta_compilado / "index.json"
    arquivo_teste.write_text('{"status": "ok"}', encoding="utf-8")
    arquivo_db = pasta_compilado / "catalogo.db"
    arquivo_db.write_bytes(b"SQLite format 3\x00dados")

    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)

    url = f"http://127.0.0.1:{servidor.porta}/index.json"
    resposta = requests.get(url)

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}

    resposta_db = requests.get(f"http://127.0.0.1:{servidor.porta}/catalogo.db")
    assert resposta_db.status_code == 200
    assert resposta_db.content == b"SQLite format 3\x00dados"
    assert "application/octet-stream" in resposta_db.headers.get("content-type", "")

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
    servidor = ServidorCelular(Path())
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
    servidor = ServidorCelular(Path())
    with patch("socket.socket") as mock_socket_cls:
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("192.168.1.105", 12345)
        mock_socket_cls.return_value = mock_sock
        ip = servidor.obter_ip_local()
        assert ip == "192.168.1.105"


def test_deve_obter_ip_local_fallback_offline():
    servidor = ServidorCelular(Path())
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

            assert (
                servidor.obter_url_previa_canonica() == "https://previa.arestaclimb.com/k9x2-p83a"
            )

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

    with patch(
        "editor.core.tunel_retransmissor.solicitar_sessao_servidor",
        return_value={
            "codigo": "x7m4n2q1",
            "codigo_formatado": "x7m4-n2q1",
            "url_previa": "https://previa.arestaclimb.com/x7m4-n2q1",
            "ws_url": "wss://previa.arestaclimb.com/ws?sessao=x7m4n2q1&token=jwt_valido_mock",
        },
    ):
        sucesso = servidor.solicitar_sessao_servidor()
        assert sucesso is True
        assert servidor.codigo_sessao == "x7m4n2q1"
        assert servidor.obter_url_previa_canonica() == "https://previa.arestaclimb.com/x7m4-n2q1"
        assert (
            servidor.url_retransmissor_ws
            == "wss://previa.arestaclimb.com/ws?sessao=x7m4n2q1&token=jwt_valido_mock"
        )


def test_deve_recuperar_jwt_automaticamente_do_gerenciador_sessao(tmp_path):
    """Quando jwt_token for None, deve buscar automaticamente no GerenciadorSessao."""
    import base64
    import time

    from editor.core.gerenciador_sessao import GerenciadorSessao, SessaoUsuario

    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    agora = int(time.time())
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": agora + 3600}).encode()).decode().rstrip("=")
    )
    jwt_valido = f"{header}.{payload}.sig"

    gerenciador = GerenciadorSessao()
    gerenciador.salvar_sessao(
        SessaoUsuario(
            email="autor@arestaclimb.com",
            nome_completo="Autor Teste",
            jwt_supabase=jwt_valido,
            token_atualizacao="refresh_123",
        )
    )

    servidor = ServidorCelular(pasta_compilado=pasta_compilado)
    assert servidor.jwt_token == jwt_valido


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

    with patch(
        "editor.core.servidor_celular.ClienteTunelRetransmissor", side_effect=MockClienteTunel
    ):
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


def test_deve_servir_arquivos_compactos_mesmo_com_prefixo_croqui_id(tmp_path):
    """Garante que rotas com prefixo do croqui_id encontram arquivos na raiz de compilado quando compactado."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    # Estrutura compacta (sem subpasta br_mg_itambe)
    (pasta_compilado / "compilado.binarypb").write_bytes(b"dados_pb")
    pasta_imagens = pasta_compilado / "imagens"
    pasta_imagens.mkdir()
    (pasta_imagens / "parede.webp").write_bytes(b"imagem_bytes")

    servidor = ServidorCelular(pasta_compilado)
    servidor.iniciar()
    esperar_porta(servidor)

    try:
        # 1. Requisição com prefixo do ID do croqui (como o celular pode solicitar)
        url_pb = f"http://127.0.0.1:{servidor.porta}/br_mg_itambe/compilado.binarypb"
        resp_pb = requests.get(url_pb)
        assert resp_pb.status_code == 200
        assert resp_pb.content == b"dados_pb"

        # 2. Requisição de imagem com prefixo
        url_img = f"http://127.0.0.1:{servidor.porta}/br_mg_itambe/imagens/parede.webp"
        resp_img = requests.get(url_img)
        assert resp_img.status_code == 200
        assert resp_img.content == b"imagem_bytes"

        # 3. Requisição direta à raiz
        url_direta = f"http://127.0.0.1:{servidor.porta}/compilado.binarypb"
        resp_direta = requests.get(url_direta)
        assert resp_direta.status_code == 200
        assert resp_direta.content == b"dados_pb"

        # 4. Mesmo se a subpasta <id_croqui>/ existir vazia durante recompilação/compactação,
        # deve fazer fallback para a raiz de compilado/
        (pasta_compilado / "br_mg_itambe").mkdir(exist_ok=True)
        resp_pb_sub = requests.get(url_pb)
        assert resp_pb_sub.status_code == 200
        assert resp_pb_sub.content == b"dados_pb"

        resp_img_sub = requests.get(url_img)
        assert resp_img_sub.status_code == 200
        assert resp_img_sub.content == b"imagem_bytes"
    finally:
        servidor.parar()
        if servidor._thread_servidor and servidor._thread_servidor.is_alive():
            servidor._thread_servidor.join(timeout=3.0)


def test_obter_url_previa_canonica_lanca_erro_quando_sem_sessao_e_sem_jwt(tmp_path):
    """Fail-Fast: deve lançar RuntimeError quando não houver sessão ativa nem JWT para criar uma."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    servidor = ServidorCelular(pasta_compilado=pasta_compilado)
    assert servidor.jwt_token is None

    with pytest.raises(RuntimeError, match="sessão de prévia"):
        servidor.obter_url_previa_canonica()


def test_obter_url_previa_canonica_solicita_sessao_sob_demanda(tmp_path):
    """Quando ainda não há código mas há JWT válido, obter_url_previa_canonica solicita sessão ao servidor."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    servidor = ServidorCelular(pasta_compilado=pasta_compilado, jwt_token="jwt_sob_demanda")

    with patch(
        "editor.core.tunel_retransmissor.solicitar_sessao_servidor",
        return_value={
            "codigo": "m2n4p6q8",
            "url_previa": "https://previa.arestaclimb.com/m2n4-p6q8",
            "ws_url": "wss://previa.arestaclimb.com/ws?sessao=m2n4p6q8",
        },
    ) as mock_api:
        url = servidor.obter_url_previa_canonica()
        assert url == "https://previa.arestaclimb.com/m2n4-p6q8"
        assert mock_api.call_count == 1

        # Chamada subsequente a solicitar_sessao_servidor deve ser idempotente (já possui sessão)
        assert servidor.solicitar_sessao_servidor() is True
        assert mock_api.call_count == 1


def test_solicitar_sessao_servidor_retorna_false_quando_api_falha(tmp_path):
    """Quando a API do Cloudflare Relay lança exceção, solicitar_sessao_servidor retorna False."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    servidor = ServidorCelular(pasta_compilado=pasta_compilado, jwt_token="jwt_teste")

    with patch(
        "editor.core.tunel_retransmissor.solicitar_sessao_servidor",
        side_effect=RuntimeError("Falha de conexão com Cloudflare"),
    ):
        assert servidor.solicitar_sessao_servidor() is False
        with pytest.raises(RuntimeError, match="sessão de prévia"):
            servidor.obter_url_previa_canonica()


def test_obter_porta_disponivel_retorna_zero_quando_intervalo_ocupado(tmp_path):
    """Quando todas as portas do intervalo estão ocupadas, obter_porta_disponivel retorna 0."""
    servidor = ServidorCelular(tmp_path)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_ocupado:
        sock_ocupado.bind(("127.0.0.1", 0))
        sock_ocupado.listen(5)
        porta_ocupada = sock_ocupado.getsockname()[1]

        porta_obtida = servidor.obter_porta_disponivel(
            inicio=porta_ocupada, fim=porta_ocupada, max_tentativas=1
        )
        assert porta_obtida == 0


def test_iniciar_parar_idempotentes_e_notificacao_remota(tmp_path, qtbot):
    """Garante idempotência de iniciar/parar, aviso de recarregamento sem túnel e sinal remoto."""
    pasta_compilado = tmp_path / "compilado"
    pasta_compilado.mkdir()

    servidor = ServidorCelular(pasta_compilado=pasta_compilado)
    # Parar antes de iniciar não deve falhar
    servidor.parar()
    # Emitir recarregamento sem túnel ativo não deve falhar
    servidor.emitir_recarregamento("setor_inativo")

    # Notificação remota deve emitir dispositivo_conectado apenas na primeira vez
    with qtbot.waitSignal(servidor.dispositivo_conectado, timeout=1000):
        servidor._ao_notificar_conexao_remota()
    assert servidor.conectado is True
    servidor._ao_notificar_conexao_remota()

    servidor.iniciar()
    esperar_porta(servidor)
    try:
        # Chamar iniciar novamente enquanto já está servindo deve retornar imediatamente
        thread_original = servidor._thread_servidor
        servidor.iniciar()
        assert servidor._thread_servidor is thread_original
    finally:
        servidor.parar()
        if servidor._thread_servidor and servidor._thread_servidor.is_alive():
            servidor._thread_servidor.join(timeout=3.0)
