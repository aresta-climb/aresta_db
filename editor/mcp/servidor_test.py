# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import asyncio
from pathlib import Path
from typing import Any

import httpx

from editor.mcp.despachante import DespachanteQt
from editor.mcp.servidor import ServidorMCP
from editor.mcp.sessao import ler_sessao_mcp


def _criar_servidor_teste(tmp_path: Path) -> ServidorMCP:
    despachante = DespachanteQt()
    servidor = ServidorMCP(despachante=despachante, diretorio_sessao=tmp_path)

    def somar(args: dict[str, Any]) -> dict[str, Any]:
        return {"soma": int(args["a"]) + int(args["b"])}

    def capturar_imagem(_args: dict[str, Any]) -> dict[str, Any]:
        return {
            "_mcp_content": [
                {"type": "image", "data": "iVBORw0KGgo=", "mimeType": "image/png"},
                {"type": "text", "text": '{"largura": 100}'},
            ]
        }

    def falhar(_args: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Parâmetro inválido no croqui")

    servidor.registrar_ferramenta(
        nome="aresta_somar",
        descricao="Soma dois inteiros.",
        esquema_entrada={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
        manipulador=somar,
    )
    servidor.registrar_ferramenta(
        nome="aresta_imagem",
        descricao="Retorna imagem multimodal.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=capturar_imagem,
    )
    servidor.registrar_ferramenta(
        nome="aresta_falhar",
        descricao="Simula erro de validação.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=falhar,
    )
    servidor.registrar_recurso(
        uri="aresta://croqui/resumo",
        nome="Resumo do Croqui",
        descricao="Dados básicos do croqui ativo.",
        leitor=lambda: {"nome": "Serra do Cipó", "picos": 2},
    )
    return servidor


def test_protocolo_jsonrpc_completo_via_post_mcp(qapp, tmp_path: Path):
    """Valida initialize, notificações, ping, tools/list, tools/call e resources via POST /mcp."""
    servidor = _criar_servidor_teste(tmp_path)

    async def _executar_fluxo() -> None:
        transporte = httpx.ASGITransport(app=servidor.app)
        async with httpx.AsyncClient(transport=transporte, base_url="http://127.0.0.1") as client:
            # 1. Payload inválido (não é JSON-RPC 2.0)
            resp_inv = await client.post("/mcp", json={"jsonrpc": "1.0", "id": 1, "method": "ping"})
            assert resp_inv.status_code == 200
            assert resp_inv.json()["error"]["code"] == -32600

            # 2. Initialize
            resp_init = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"},
                },
            )
            assert resp_init.status_code == 200
            dados_init = resp_init.json()["result"]
            assert dados_init["serverInfo"]["name"] == "editor-aresta"
            assert "tools" in dados_init["capabilities"]
            assert "aresta_obter_esquema_proto" in dados_init["instructions"]
            assert "aresta_listar_skills" in dados_init["instructions"]

            # 3. Notificação (sem id) -> 202 Accepted sem corpo JSON-RPC
            resp_notif = await client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
            assert resp_notif.status_code == 202

            # 4. Ping
            resp_ping = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "ping"}
            )
            assert resp_ping.json() == {"jsonrpc": "2.0", "id": 2, "result": {}}

            # 5. tools/list
            resp_tools = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
            )
            nomes_tools = [t["name"] for t in resp_tools.json()["result"]["tools"]]
            assert "aresta_somar" in nomes_tools
            assert "aresta_imagem" in nomes_tools

            # 6. tools/call com sucesso estruturado
            resp_call = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "aresta_somar", "arguments": {"a": 10, "b": 15}},
                },
            )
            res_call = resp_call.json()["result"]
            assert res_call["isError"] is False
            assert res_call["structuredContent"] == {"soma": 25}

            # 7. tools/call multimodal (_mcp_content)
            resp_img = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "aresta_imagem", "arguments": {}},
                },
            )
            res_img = resp_img.json()["result"]
            assert res_img["isError"] is False
            assert res_img["content"][0]["type"] == "image"
            assert res_img["content"][0]["mimeType"] == "image/png"

            # 8. tools/call com exceção de domínio -> retorna isError=True para o agente corrigir
            resp_err = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {"name": "aresta_falhar", "arguments": {}},
                },
            )
            res_err = resp_err.json()["result"]
            assert res_err["isError"] is True
            assert "Parâmetro inválido no croqui" in res_err["content"][0]["text"]

            # 9. tools/call de ferramenta inexistente -> erro JSON-RPC -32601
            resp_nao_existe = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {"name": "inexistente", "arguments": {}},
                },
            )
            assert resp_nao_existe.json()["error"]["code"] == -32601

            # 10. resources/list e resources/read
            resp_res_list = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 8, "method": "resources/list"}
            )
            recursos = resp_res_list.json()["result"]["resources"]
            assert len(recursos) == 1
            assert recursos[0]["uri"] == "aresta://croqui/resumo"

            resp_res_read = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "resources/read",
                    "params": {"uri": "aresta://croqui/resumo"},
                },
            )
            conteudo_lido = resp_res_read.json()["result"]["contents"][0]["text"]
            assert "Serra do Cipó" in conteudo_lido

            resp_res_invalido = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "resources/read",
                    "params": {"uri": "aresta://inexistente"},
                },
            )
            assert resp_res_invalido.json()["error"]["code"] == -32602

            # 11. Método desconhecido -> -32601
            resp_metodo_inv = await client.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 11, "method": "metodo/inexistente"}
            )
            assert resp_metodo_inv.json()["error"]["code"] == -32601

    asyncio.run(_executar_fluxo())


def test_transporte_sse_e_ciclo_vida_servidor_real(qapp, tmp_path: Path):
    """Inicia o servidor Uvicorn real em 127.0.0.1, valida SSE + /mcp/messages e encerramento limpo."""
    servidor = _criar_servidor_teste(tmp_path)
    sessao = servidor.iniciar()
    # Chamada idempotente quando já está rodando
    assert servidor.iniciar() == sessao
    assert servidor.esta_ativo is True
    assert ler_sessao_mcp(tmp_path) is not None

    try:
        with httpx.Client(timeout=5.0) as http:
            status = http.get(f"http://127.0.0.1:{servidor.porta}/mcp/status").json()
            assert status["ativo"] is True
            assert status["porta"] == servidor.porta

            # Abre stream SSE real e envia mensagem via POST /mcp/messages
            with http.stream("GET", sessao.url_sse) as stream:
                linhas_iter = stream.iter_lines()
                linha_evento = next(linhas_iter)
                linha_dados = next(linhas_iter)
                assert linha_evento == "event: endpoint"
                assert linha_dados.startswith("data: /mcp/messages?session_id=")
                endpoint_msg = linha_dados.removeprefix("data: ").strip()

                # Envia requisição JSON-RPC pelo endpoint de mensagens da sessão SSE
                url_post = f"http://127.0.0.1:{servidor.porta}{endpoint_msg}"
                resp_post = http.post(
                    url_post,
                    json={"jsonrpc": "2.0", "id": 42, "method": "ping"},
                )
                assert resp_post.status_code == 202

                # Envia notificação pelo endpoint de mensagens
                resp_notif = http.post(
                    url_post,
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                )
                assert resp_notif.status_code == 202

                # Lê resposta JSON-RPC entregue no canal SSE
                ev_msg = ""
                dados_msg = ""
                for linha in linhas_iter:
                    if linha.startswith("event: message"):
                        ev_msg = linha
                    elif linha.startswith("data: "):
                        dados_msg = linha.removeprefix("data: ").strip()
                        break
                assert ev_msg == "event: message"
                assert '"id": 42' in dados_msg or '"id":42' in dados_msg

                # POST /mcp/messages sem session_id ativa também retorna a resposta diretamente
                resp_sem_sessao = http.post(
                    f"http://127.0.0.1:{servidor.porta}/mcp/messages",
                    json={"jsonrpc": "2.0", "id": 99, "method": "ping"},
                )
                assert resp_sem_sessao.status_code == 200
                assert resp_sem_sessao.json()["id"] == 99

                # Parar o servidor enquanto o stream SSE está aberto deve encerrar o gerador limpo
                servidor.parar()
                restantes = [linha for linha in linhas_iter if linha]
                assert restantes == []
    finally:
        servidor.parar()

    assert servidor.esta_ativo is False
    assert ler_sessao_mcp(tmp_path) is None


def test_guarda_sem_croqui_aberto_e_roteamento_proxy_multi_janela(qapp, tmp_path: Path):
    """
    Valida:
    1. Guarda defensiva quando nenhum croqui está aberto (ferramentas com requer_croqui=True retornam erro,
       enquanto ferramentas globais com requer_croqui=False executam normalmente).
    2. Roteamento proxy transparente da porta primária para uma segunda instância do ServidorMCP
       por id_croqui, e erro de desambiguação quando id_croqui é omitido com >1 croquis abertos.
    """
    srv_primario = _criar_servidor_teste(tmp_path)
    srv_primario.registrar_ferramenta(
        nome="aresta_listar_croquis",
        descricao="Lista croquis.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=lambda _args: {"abertos": []},
        requer_croqui=False,
    )
    srv_primario.definir_croqui_ativo("", croqui_aberto=False)

    # 1. Sem croqui aberto: ferramenta de edição falha com guarda defensiva; global funciona
    resp_bloqueada = srv_primario.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "aresta_somar", "arguments": {"a": 1, "b": 2}},
        }
    )
    assert resp_bloqueada is not None
    assert resp_bloqueada["result"]["isError"] is True
    assert "Nenhum croqui está aberto" in resp_bloqueada["result"]["content"][0]["text"]

    resp_global = srv_primario.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "aresta_listar_croquis", "arguments": {}},
        }
    )
    assert resp_global is not None
    assert resp_global["result"]["isError"] is False

    # 2. Inicia dois servidores reais com croquis distintos ("croqui_a" e "croqui_b")
    srv_secundario = _criar_servidor_teste(tmp_path)
    srv_secundario.registrar_ferramenta(
        nome="aresta_identificar",
        descricao="Retorna id do servidor.",
        esquema_entrada={"type": "object", "properties": {"id_croqui": {"type": "string"}}},
        manipulador=lambda _args: {"janela": "secundaria_b"},
    )
    srv_primario.registrar_ferramenta(
        nome="aresta_identificar",
        descricao="Retorna id do servidor.",
        esquema_entrada={"type": "object", "properties": {"id_croqui": {"type": "string"}}},
        manipulador=lambda _args: {"janela": "primaria_a"},
    )

    srv_primario.iniciar()
    srv_secundario.iniciar()
    try:
        # Quando o primário está na Tela de Carregamento (sem croqui) e apenas o secundário tem "croqui_b" aberto,
        # chamadas sem id_croqui no primário são encaminhadas automaticamente para o único croqui aberto ("croqui_b")!
        srv_secundario.definir_croqui_ativo("croqui_b", "/db/b", croqui_aberto=True)
        resp_unico_remoto = srv_primario.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "aresta_identificar", "arguments": {}},
            }
        )
        assert resp_unico_remoto is not None
        assert resp_unico_remoto["result"]["structuredContent"] == {"janela": "secundaria_b"}

        # Agora o primário também abre "croqui_a" -> temos 2 croquis abertos ("croqui_a" e "croqui_b")
        srv_primario.definir_croqui_ativo("croqui_a", "/db/a", croqui_aberto=True)

        # Omitir id_croqui com 2 croquis abertos deve exigir desambiguação
        resp_ambiguo = srv_primario.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "aresta_identificar", "arguments": {}},
            }
        )
        assert resp_ambiguo is not None
        assert resp_ambiguo["result"]["isError"] is True
        assert "croqui_a" in resp_ambiguo["result"]["content"][0]["text"]
        assert "croqui_b" in resp_ambiguo["result"]["content"][0]["text"]

        # Informando id_croqui="croqui_a" -> executa no primário
        resp_a = srv_primario.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "aresta_identificar", "arguments": {"id_croqui": "croqui_a"}},
            }
        )
        assert resp_a is not None
        assert resp_a["result"]["structuredContent"] == {"janela": "primaria_a"}

        # Informando id_croqui="croqui_b" no primário -> faz proxy transparente para o secundário
        resp_b = srv_primario.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "aresta_identificar", "arguments": {"id_croqui": "croqui_b"}},
            }
        )
        assert resp_b is not None
        assert resp_b["result"]["structuredContent"] == {"janela": "secundaria_b"}

        # Informando id_croqui inexistente -> retorna erro listando os abertos
        resp_inex = srv_primario.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "aresta_identificar",
                    "arguments": {"id_croqui": "croqui_inexistente"},
                },
            }
        )
        assert resp_inex is not None
        assert resp_inex["result"]["isError"] is True
        assert "croqui_inexistente" in resp_inex["result"]["content"][0]["text"]
    finally:
        srv_secundario.parar()
        srv_primario.parar()


def test_servidor_mcp_iniciar_nao_dispara_about_to_quit_em_transicao_sem_janela_visivel(
    qapp, tmp_path: Path
):
    """
    Garante que ServidorMCP.iniciar() sobe a thread do Uvicorn sem chamar QCoreApplication.processEvents(),
    impedindo que uma transição de janela (onde a última janela visível acabou de fechar e a próxima
    ainda será exibida) dispare prematuramente o sinal aboutToQuit do QApplication.
    """
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog, QMainWindow

    eventos_quit: list[str] = []

    def _ao_sair() -> None:
        eventos_quit.append("aboutToQuit")

    qapp.aboutToQuit.connect(_ao_sair)
    servidor = _criar_servidor_teste(tmp_path)
    janela_destino = QMainWindow()

    try:
        dialogo_inicial = QDialog()
        dialogo_inicial.show()

        def _transicionar_janelas() -> None:
            dialogo_inicial.accept()
            # Neste ponto, 0 janelas estão visíveis e lastWindowClosed foi emitido;
            # ServidorMCP.iniciar() não deve processar a fila de eventos da GUI antes do show()
            servidor.iniciar()
            janela_destino.show()
            QTimer.singleShot(
                50,
                lambda: (
                    eventos_quit.append("janela_ainda_viva"),
                    qapp.exit(0),
                ),
            )

        QTimer.singleShot(20, _transicionar_janelas)
        qapp.exec()

        assert servidor.esta_ativo is True
        assert eventos_quit[0] == "janela_ainda_viva"
    finally:
        qapp.aboutToQuit.disconnect(_ao_sair)
        janela_destino.close()
        servidor.parar()


def test_ferramenta_com_executar_na_thread_qt_false_roda_fora_da_thread_principal(
    qapp, tmp_path: Path
):
    """
    Valida que ferramentas registradas com executar_na_thread_qt=False executam
    diretamente na thread HTTP do Uvicorn sem bloquear na fila do DespachanteQt.
    """
    import threading

    id_thread_principal = threading.get_ident()
    servidor = _criar_servidor_teste(tmp_path)

    def _manipulador_background(_args: dict[str, Any]) -> dict[str, Any]:
        return {
            "id_thread_execucao": threading.get_ident(),
            "fora_da_thread_qt": threading.get_ident() != id_thread_principal,
        }

    servidor.registrar_ferramenta(
        nome="aresta_background",
        descricao="Executa fora da thread do Qt.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_manipulador_background,
        executar_na_thread_qt=False,
    )

    sessao = servidor.iniciar()
    try:
        # Mesmo sem bombear o loop de eventos do Qt na thread principal (que travaria se passasse pelo DespachanteQt),
        # a chamada HTTP deve responder imediatamente na thread do Uvicorn!
        with httpx.Client(timeout=5.0) as http:
            resp = http.post(
                sessao.url_http,
                json={
                    "jsonrpc": "2.0",
                    "id": 77,
                    "method": "tools/call",
                    "params": {"name": "aresta_background", "arguments": {}},
                },
            )
            assert resp.status_code == 200
            dados = resp.json()["result"]["structuredContent"]
            assert dados["fora_da_thread_qt"] is True
            assert dados["id_thread_execucao"] != id_thread_principal
    finally:
        servidor.parar()


def test_servidor_mcp_inicia_e_responde_quando_stdout_e_stderr_sao_none(
    qapp, tmp_path: Path, monkeypatch
) -> None:
    """
    Regressão Issue #101 (ARESTA-EDITOR-1F): em executáveis GUI com console=False abertos pelo
    Menu Iniciar do Windows (MSIX), sys.stdout e sys.stderr são None, o que não pode derrubar o Uvicorn.
    """
    import sys

    servidor = _criar_servidor_teste(tmp_path)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    sessao = servidor.iniciar()
    try:
        with httpx.Client(timeout=5.0) as http:
            resp = http.post(
                sessao.url_http,
                json={"jsonrpc": "2.0", "id": 101, "method": "ping"},
            )
            assert resp.status_code == 200
            assert resp.json() == {"jsonrpc": "2.0", "id": 101, "result": {}}
    finally:
        servidor.parar()


def test_failover_automatico_porta_primaria_multiplas_janelas_e_poda_morte_abrupta(
    qapp, tmp_path: Path
) -> None:
    """
    Valida o ciclo completo de failover entre 3 instâncias reais de ServidorMCP:
    1. Janela 1 vincula a porta primária; Janelas 2 e 3 sobem em portas secundárias.
    2. Ao encerrar a Janela 1, exatamente uma das janelas sobreviventes readquire automaticamente
       a porta primária (mantendo também sua porta secundária viva como alias) e faz proxy para a outra.
    3. Se a outra janela secundária morrer abruptamente sem desregistrar sua sessão (simulando kill),
       chamadas na porta primária sem id_croqui podam a sessão zumbi e atendem o único croqui vivo,
       e chamadas explícitas para uma sessão recém-morta retornam isError=True sem IndexError.
    """
    import time

    from editor.mcp.sessao import (
        DadosSessaoMcp,
        alocar_porta_mcp,
        ler_sessao_mcp,
        registrar_sessao_multi_mcp,
    )

    porta_primaria = alocar_porta_mcp(porta_preferencial=38300)

    def _instanciar_janela(nome_janela: str, id_croqui: str) -> ServidorMCP:
        srv = ServidorMCP(
            despachante=DespachanteQt(),
            porta_preferencial=porta_primaria,
            diretorio_sessao=tmp_path,
            intervalo_vigia_primaria_s=0.03,
        )
        srv.definir_croqui_ativo(id_croqui, f"/db/{id_croqui}", croqui_aberto=True)
        srv.registrar_ferramenta(
            nome="aresta_quem_sou",
            descricao="Identifica a janela ativa.",
            esquema_entrada={"type": "object", "properties": {}},
            manipulador=lambda _args, n=nome_janela: {"janela": n},
            executar_na_thread_qt=False,
        )
        return srv

    srv_1 = _instanciar_janela("janela_1", "croqui_1")
    srv_2 = _instanciar_janela("janela_2", "croqui_2")
    srv_3 = _instanciar_janela("janela_3", "croqui_3")

    srv_1.iniciar()
    srv_2.iniciar()
    srv_3.iniciar()
    try:
        assert srv_1.porta == porta_primaria
        porta_sec_2 = srv_2.porta
        porta_sec_3 = srv_3.porta
        assert porta_sec_2 is not None and porta_sec_2 != porta_primaria
        assert porta_sec_3 is not None and porta_sec_3 != porta_primaria

        url_primaria = f"http://127.0.0.1:{porta_primaria}/mcp"

        # 1. Encerra a Janela 1 -> Janela 2 ou Janela 3 deve readquirir porta_primaria automaticamente
        srv_1.parar()

        prazo = time.monotonic() + 3.0
        while time.monotonic() < prazo:
            if srv_2.porta == porta_primaria or srv_3.porta == porta_primaria:
                break
            time.sleep(0.02)

        eleitos = [s for s in (srv_2, srv_3) if s.porta == porta_primaria]
        assert len(eleitos) == 1
        eleito = eleitos[0]
        outro = srv_3 if eleito is srv_2 else srv_2
        porta_alias_eleito = porta_sec_2 if eleito is srv_2 else porta_sec_3

        sessao_disco = ler_sessao_mcp(tmp_path)
        assert sessao_disco is not None
        assert sessao_disco.porta == porta_primaria

        with httpx.Client(timeout=5.0) as http:
            # Chamadas na porta primária alcançam tanto croqui_2 quanto croqui_3 (local + proxy HTTP fora da main thread)
            for req_id, id_alvo, janela_esp in (
                (10, "croqui_2", "janela_2"),
                (11, "croqui_3", "janela_3"),
            ):
                resp = http.post(
                    url_primaria,
                    json={
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "tools/call",
                        "params": {
                            "name": "aresta_quem_sou",
                            "arguments": {"id_croqui": id_alvo},
                        },
                    },
                )
                assert resp.status_code == 200
                assert resp.json()["result"]["structuredContent"] == {"janela": janela_esp}

            # A porta secundária original do eleito permanece aberta como alias
            resp_alias = http.post(
                f"http://127.0.0.1:{porta_alias_eleito}/mcp",
                json={"jsonrpc": "2.0", "id": 12, "method": "ping"},
            )
            assert resp_alias.status_code == 200

            # 2. Simula morte abrupta (kill) da outra janela secundária: para Uvicorn mas re-injeta sessão zumbi no JSON
            porta_morta = outro.porta
            id_morto = outro.id_croqui_ativo
            assert porta_morta is not None
            outro.parar()
            registrar_sessao_multi_mcp(
                DadosSessaoMcp(
                    porta=porta_morta,
                    pid=999999,
                    token="tok_zumbi",
                    id_croqui=id_morto,
                    caminho_database="/db/zumbi",
                ),
                diretorio_base=tmp_path,
            )

            # Sem id_croqui na porta primária -> poda a sessão zumbi automaticamente e responde pelo único vivo!
            resp_unico = http.post(
                url_primaria,
                json={
                    "jsonrpc": "2.0",
                    "id": 13,
                    "method": "tools/call",
                    "params": {"name": "aresta_quem_sou", "arguments": {}},
                },
            )
            assert resp_unico.status_code == 200
            assert resp_unico.json()["result"]["isError"] is False
            janela_esperada = "janela_2" if eleito is srv_2 else "janela_3"
            assert resp_unico.json()["result"]["structuredContent"] == {"janela": janela_esperada}

            # E se o proxy receber falha de conexão direta para uma porta inacessível, retorna erro estruturado sem IndexError
            erro_proxy = eleito._encaminhar_via_proxy(
                f"http://127.0.0.1:{porta_morta}/mcp",
                {"jsonrpc": "2.0", "id": 14, "method": "ping"},
                porta_destino=porta_morta,
            )
            assert erro_proxy["result"]["isError"] is True
    finally:
        srv_3.parar()
        srv_2.parar()
        srv_1.parar()

    import pytest

    arq_bloqueio = tmp_path / "arquivo_bloqueando_dir_sessao"
    arq_bloqueio.write_text("x", encoding="utf-8")
    srv_falha_gravacao = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=arq_bloqueio)
    with pytest.raises(OSError):
        srv_falha_gravacao.iniciar()
    srv_falha_gravacao.parar()
