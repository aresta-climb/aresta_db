# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

import asyncio
import json
import base64
import pytest
from pathlib import Path
import websockets
from unittest.mock import patch, MagicMock
from editor.core.tunel_retransmissor import ClienteTunelRetransmissor


@pytest.fixture
def pasta_temporaria(tmp_path):
    """Cria uma pasta com arquivos de teste compilados."""
    arquivo_indice = tmp_path / "indice.binarypb"
    arquivo_indice.write_bytes(b"\x08\x01\x12\x04test")

    arquivo_imagem = tmp_path / "foto.webp"
    arquivo_imagem.write_bytes(b"fake_webp_bytes")

    arquivo_custom = tmp_path / "custom.desconhecido"
    arquivo_custom.write_bytes(b"dados_desconhecidos")

    subpasta = tmp_path / "setores"
    subpasta.mkdir()
    arquivo_setor = subpasta / "br_mg_ferros.binarypb"
    arquivo_setor.write_bytes(b"conteudo_do_setor")

    return tmp_path


def test_deve_registrar_sessao_e_responder_requisicoes_de_arquivo(pasta_temporaria):
    """O cliente do túnel deve conectar ao retransmissor, anunciar IP/porta e responder proxy de arquivos."""
    async def run():
        mensagens_recebidas = []
        
        async def servidor_mock_handler(websocket):
            try:
                async for mensagem in websocket:
                    dados = json.loads(mensagem)
                    mensagens_recebidas.append(dados)
                    
                    if dados.get("tipo") == "registro":
                        # Envia confirmação e logo em seguida solicita um arquivo
                        await websocket.send(json.dumps({
                            "tipo": "confirmacao_registro",
                            "status": "ok"
                        }))
                        await websocket.send(json.dumps({
                            "tipo": "requisicao_proxy",
                            "dados": {
                                "id": "req-1",
                                "metodo": "GET",
                                "caminho": "/indice.binarypb",
                                "cabecalhos": {}
                            }
                        }))
                        # Solicita arquivo com extensão genérica
                        await websocket.send(json.dumps({
                            "tipo": "requisicao_proxy",
                            "dados": {
                                "id": "req-custom",
                                "metodo": "GET",
                                "caminho": "/custom.desconhecido",
                                "cabecalhos": {}
                            }
                        }))
                        # Envia ping
                        await websocket.send(json.dumps({
                            "tipo": "ping"
                        }))
            except websockets.exceptions.ConnectionClosed:
                pass

        async with websockets.serve(servidor_mock_handler, "127.0.0.1", 0) as server:
            porta = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta}/ws?sessao=k9x2p83a"

            cliente = ClienteTunelRetransmissor(
                codigo_sessao="k9x2p83a",
                pasta_compilado=pasta_temporaria,
                url_retransmissor_ws=url_ws,
                ip_local="192.168.1.50",
                porta_local=8421,
            )

            tarefa_cliente = asyncio.create_task(cliente.executar())
            
            # Aguarda a resposta do proxy e do pong chegarem ao servidor mock
            for _ in range(40):
                if any(m.get("tipo") == "pong" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            await cliente.parar()
            await tarefa_cliente

            # 1. Verifica mensagem de registro
            msg_registro = next(m for m in mensagens_recebidas if m.get("tipo") == "registro")
            assert msg_registro["dados"]["ipLocal"] == "192.168.1.50"
            assert msg_registro["dados"]["portaLocal"] == 8421
            assert msg_registro["dados"]["urlLocal"] == "http://192.168.1.50:8421"

            # 2. Verifica resposta do arquivo proxy
            msg_resposta = next(m for m in mensagens_recebidas if m.get("tipo") == "resposta_proxy" and m["dados"]["id"] == "req-1")
            assert msg_resposta["dados"]["status"] == 200
            corpo = base64.b64decode(msg_resposta["dados"]["corpoBase64"])
            assert corpo == b"\x08\x01\x12\x04test"

            # 3. Verifica resposta do arquivo com mime fallback
            msg_custom = next(m for m in mensagens_recebidas if m.get("tipo") == "resposta_proxy" and m["dados"]["id"] == "req-custom")
            assert msg_custom["dados"]["status"] == 200
            assert msg_custom["dados"]["cabecalhos"]["content-type"] == "text/plain"

            # 4. Verifica resposta de pong
            assert any(m.get("tipo") == "pong" for m in mensagens_recebidas)

    asyncio.run(run())


def test_deve_retornar_404_para_arquivo_inexistente(pasta_temporaria):
    """O cliente do túnel deve responder 404 caso o arquivo solicitado não exista."""
    async def run():
        mensagens_recebidas = []

        async def servidor_mock_handler(websocket):
            try:
                async for mensagem in websocket:
                    dados = json.loads(mensagem)
                    mensagens_recebidas.append(dados)
                    if dados.get("tipo") == "registro":
                        await websocket.send(json.dumps({
                            "tipo": "requisicao_proxy",
                            "dados": {
                                "id": "req-404",
                                "metodo": "GET",
                                "caminho": "/nao_existe.json",
                                "cabecalhos": {}
                            }
                        }))
            except websockets.exceptions.ConnectionClosed:
                pass

        async with websockets.serve(servidor_mock_handler, "127.0.0.1", 0) as server:
            porta = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta}/ws?sessao=k9x2p83a"

            cliente = ClienteTunelRetransmissor(
                codigo_sessao="k9x2p83a",
                pasta_compilado=pasta_temporaria,
                url_retransmissor_ws=url_ws,
            )

            tarefa_cliente = asyncio.create_task(cliente.executar())

            for _ in range(40):
                if any(m.get("tipo") == "resposta_proxy" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            await cliente.parar()
            await tarefa_cliente

            msg_resposta = next(m for m in mensagens_recebidas if m.get("tipo") == "resposta_proxy")
            assert msg_resposta["dados"]["id"] == "req-404"
            assert msg_resposta["dados"]["status"] == 404

    asyncio.run(run())


def test_deve_bloquear_path_traversal(pasta_temporaria):
    """O cliente do túnel deve bloquear tentativas de acessar caminhos fora da pasta compilada."""
    async def run():
        mensagens_recebidas = []

        async def servidor_mock_handler(websocket):
            try:
                async for mensagem in websocket:
                    dados = json.loads(mensagem)
                    mensagens_recebidas.append(dados)
                    if dados.get("tipo") == "registro":
                        await websocket.send(json.dumps({
                            "tipo": "requisicao_proxy",
                            "dados": {
                                "id": "req-traversal",
                                "metodo": "GET",
                                "caminho": "/../../../etc/passwd",
                                "cabecalhos": {}
                            }
                        }))
            except websockets.exceptions.ConnectionClosed:
                pass

        async with websockets.serve(servidor_mock_handler, "127.0.0.1", 0) as server:
            porta = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta}/ws?sessao=k9x2p83a"

            cliente = ClienteTunelRetransmissor(
                codigo_sessao="k9x2p83a",
                pasta_compilado=pasta_temporaria,
                url_retransmissor_ws=url_ws,
            )

            tarefa_cliente = asyncio.create_task(cliente.executar())

            for _ in range(40):
                if any(m.get("tipo") == "resposta_proxy" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            await cliente.parar()
            await tarefa_cliente

            msg_resposta = next(m for m in mensagens_recebidas if m.get("tipo") == "resposta_proxy")
            assert msg_resposta["dados"]["status"] in (403, 404)

    asyncio.run(run())


def test_deve_emitir_evento_de_recarregamento(pasta_temporaria):
    """O cliente do túnel deve ser capaz de emitir eventos de recarregamento (Live Reload)."""
    async def run():
        mensagens_recebidas = []

        async def servidor_mock_handler(websocket):
            try:
                async for mensagem in websocket:
                    dados = json.loads(mensagem)
                    mensagens_recebidas.append(dados)
            except websockets.exceptions.ConnectionClosed:
                pass

        async with websockets.serve(servidor_mock_handler, "127.0.0.1", 0) as server:
            porta = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta}/ws?sessao=k9x2p83a"

            cliente = ClienteTunelRetransmissor(
                codigo_sessao="k9x2p83a",
                pasta_compilado=pasta_temporaria,
                url_retransmissor_ws=url_ws,
            )

            # Teste emitir antes de conectar não deve quebrar
            await cliente.emitir_recarregamento("teste_offline")

            tarefa_cliente = asyncio.create_task(cliente.executar())

            for _ in range(40):
                if any(m.get("tipo") == "registro" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            await cliente.emitir_recarregamento("br_mg_ferros_setor1")

            for _ in range(40):
                if any(m.get("tipo") == "evento" for m in mensagens_recebidas):
                    break
                await asyncio.sleep(0.05)

            await cliente.parar()
            await tarefa_cliente

            msg_evento = next(m for m in mensagens_recebidas if m.get("tipo") == "evento")
            assert msg_evento["dados"]["tipo"] == "recarregar"
            assert msg_evento["dados"]["setor"] == "br_mg_ferros_setor1"

    asyncio.run(run())


def test_deve_tratar_erro_ao_ler_arquivo_proxy(pasta_temporaria):
    """Retorna status 500 caso ocorra erro inesperado de I/O."""
    cliente = ClienteTunelRetransmissor(
        codigo_sessao="k9x2p83a",
        pasta_compilado=pasta_temporaria,
    )
    with patch.object(Path, "resolve", side_effect=Exception("Erro simulado de I/O")):
        res = cliente._ler_arquivo_proxy("req-erro", "indice.binarypb")
        assert res["status"] == 500
        assert "Erro simulado" in base64.b64decode(res["corpoBase64"]).decode()


def test_deve_solicitar_sessao_ao_servidor_com_sucesso():
    """Deve enviar POST /sessoes com JWT e retornar o dicionário de sessão."""
    from editor.core.tunel_retransmissor import solicitar_sessao_servidor
    from unittest.mock import MagicMock
    import urllib.request
    from io import BytesIO

    resposta_mock = MagicMock()
    resposta_mock.read.return_value = json.dumps({
        "codigo": "k9x2p83a",
        "codigo_formatado": "k9x2-p83a",
        "url_previa": "https://previa.arestaclimb.com/k9x2-p83a",
        "ws_url": "wss://previa.arestaclimb.com/ws?sessao=k9x2p83a&token=fake_jwt",
    }).encode("utf-8")
    resposta_mock.__enter__.return_value = resposta_mock

    with patch.object(urllib.request, "urlopen", return_value=resposta_mock) as mock_urlopen:
        resultado = solicitar_sessao_servidor(
            url_base="https://previa.arestaclimb.com",
            jwt_token="fake_jwt_123",
            ip_local="192.168.1.10",
            porta_local=8888,
        )

        assert resultado["codigo"] == "k9x2p83a"
        assert resultado["codigo_formatado"] == "k9x2-p83a"
        assert resultado["url_previa"] == "https://previa.arestaclimb.com/k9x2-p83a"
        assert "ws_url" in resultado
        mock_urlopen.assert_called_once()


def test_deve_lancar_erro_ao_solicitar_sessao_sem_jwt():
    """Deve lançar ValueError caso jwt_token esteja vazio."""
    from editor.core.tunel_retransmissor import solicitar_sessao_servidor
    with pytest.raises(ValueError, match="Token JWT obrigatório"):
        solicitar_sessao_servidor("https://previa.arestaclimb.com", "")


def test_deve_rejeitar_tentativas_de_directory_traversal(pasta_temporaria):
    """Garante que qualquer tentativa de leitura fora da pasta compilada seja bloqueada com status 403."""
    # Cria arquivo secreto fora da pasta compilada
    pasta_fora = pasta_temporaria.parent / "pasta_secreta_fora"
    pasta_fora.mkdir(exist_ok=True)
    arquivo_secreto = pasta_fora / "segredo.txt"
    arquivo_secreto.write_text("DADOS_CONFIDENCIAIS_NAO_ACESSIVEIS")

    cliente = ClienteTunelRetransmissor(
        codigo_sessao="k9x2p83a",
        pasta_compilado=pasta_temporaria,
    )

    # 1. Tentativa de traversal relativo com ../
    res_relativo = cliente._ler_arquivo_proxy("req-1", "../pasta_secreta_fora/segredo.txt")
    assert res_relativo["status"] == 403
    assert "Acesso negado" in base64.b64decode(res_relativo["corpoBase64"]).decode()

    # 2. Tentativa com múltiplas subidas de diretório
    res_profundo = cliente._ler_arquivo_proxy("req-2", "../../../../../Windows/win.ini")
    assert res_profundo["status"] == 403

    # 3. Tentativa com caminho absoluto do sistema
    caminho_abs = str(arquivo_secreto.resolve())
    res_abs = cliente._ler_arquivo_proxy("req-3", caminho_abs)
    assert res_abs["status"] == 403

    # 4. Leitura autorizada de subpasta permitida deve funcionar normalmente com 200
    res_legitimo = cliente._ler_arquivo_proxy("req-4", "setores/br_mg_ferros.binarypb")
    assert res_legitimo["status"] == 200
    assert base64.b64decode(res_legitimo["corpoBase64"]) == b"conteudo_do_setor"


def test_cliente_tunel_reconecta_automaticamente_apos_queda(pasta_temporaria):
    """Cliente do túnel deve restabelecer conexão automaticamente quando o servidor fecha a conexão."""
    async def run():
        conexoes = 0

        async def servidor_mock_handler(websocket):
            nonlocal conexoes
            conexoes += 1
            if conexoes == 1:
                # Na primeira conexão, fecha abruptamente logo após o registro
                await websocket.recv()
                await websocket.close(1001, "Reinicio de servidor")
            else:
                # Na segunda conexão, processa normalmente
                async for mensagem in websocket:
                    dados = json.loads(mensagem)
                    if dados.get("tipo") == "registro":
                        await websocket.send(json.dumps({"tipo": "pong"}))

        async with websockets.serve(servidor_mock_handler, "127.0.0.1", 0) as server:
            porta = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta}/ws?sessao=recon123"

            cliente = ClienteTunelRetransmissor(
                codigo_sessao="recon123",
                pasta_compilado=pasta_temporaria,
                url_retransmissor_ws=url_ws,
            )

            tarefa = asyncio.create_task(cliente.executar(intervalo_heartbeat=0.1))

            for _ in range(50):
                if conexoes >= 2:
                    break
                await asyncio.sleep(0.05)

            await cliente.parar()
            await tarefa
            assert conexoes >= 2

    asyncio.run(run())


def test_cliente_tunel_envia_ping_keepalive_quando_ocioso(pasta_temporaria):
    """Cliente do túnel deve enviar ping de heartbeat quando o canal permanece ocioso."""
    async def run():
        pings_recebidos = 0

        async def servidor_mock_handler(websocket):
            nonlocal pings_recebidos
            async for mensagem in websocket:
                dados = json.loads(mensagem)
                if dados.get("tipo") == "ping":
                    pings_recebidos += 1
                    await websocket.send(json.dumps({"tipo": "pong"}))

        async with websockets.serve(servidor_mock_handler, "127.0.0.1", 0) as server:
            porta = server.sockets[0].getsockname()[1]
            url_ws = f"ws://127.0.0.1:{porta}/ws?sessao=ping123"

            cliente = ClienteTunelRetransmissor(
                codigo_sessao="ping123",
                pasta_compilado=pasta_temporaria,
                url_retransmissor_ws=url_ws,
            )

            tarefa = asyncio.create_task(cliente.executar(intervalo_heartbeat=0.08))

            for _ in range(40):
                if pings_recebidos >= 2:
                    break
                await asyncio.sleep(0.05)

            await cliente.parar()
            await tarefa
            assert pings_recebidos >= 1

    asyncio.run(run())

