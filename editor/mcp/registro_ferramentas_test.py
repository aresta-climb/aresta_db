# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.core.historico import GerenciadorHistorico
from editor.core.workspace import HeadlessWorkspace
from editor.mcp.despachante import DespachanteQt
from editor.mcp.registro_ferramentas import registrar_catalogo_ferramentas_croqui
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def test_registrar_catalogo_ferramentas_croqui_unificado_sem_widgets(qapp, tmp_path: Path) -> None:
    """Garante que o registrador unificado expõe todo o catálogo MCP em modo headless e orienta quando capturar_canvas é chamado sem widget."""
    pasta_db = tmp_path / "database" / "br_mg_teste"
    pasta_db.mkdir(parents=True)

    croqui = croqui_pb2.Croqui(uid="uid_croqui_reg", id="br_mg_teste", nome="Croqui Teste")
    pico = croqui.picos.add(nome="Pico 1")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    setor.uid = "uid_setor_reg1"
    setor.nome = "Setor Central"

    model = CroquiModel(croqui)
    historico = GerenciadorHistorico()
    controller = CroquiController(model, historico)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)

    with HeadlessWorkspace(pasta_db) as ws:
        mapas_ctrl = registrar_catalogo_ferramentas_croqui(
            servidor=servidor,
            croqui_model=model,
            croqui_controller=controller,
            historico=historico,
            workspace=ws,
        )
        assert mapas_ctrl is not None

        resp_lista = servidor.processar_mensagem_jsonrpc(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert resp_lista is not None
        nomes = {t["name"] for t in resp_lista["result"]["tools"]}
        ferramentas_esperadas = {
            "aresta_alterar_campo",
            "aresta_alterar_em_lote",
            "aresta_adicionar_repeated",
            "aresta_remover_repeated",
            "aresta_mover_repeated",
            "aresta_migrar_escalada",
            "aresta_migrar_setor",
            "aresta_obter_arvore",
            "aresta_listar_escaladas",
            "aresta_renderizar_mapa",
            "aresta_obter_esquema_proto",
            "aresta_listar_skills",
            "aresta_ler_skill",
            "aresta_compilar",
            "aresta_salvar",
            "aresta_status_workspace",
            "aresta_listar_betas_nao_scorados",
            "aresta_pontuar_betas",
            "aresta_adicionar_betas_revisao",
            "aresta_remover_betas",
        }
        assert ferramentas_esperadas.issubset(nomes)

        # Sem provedor de widget (modo headless), aresta_capturar_canvas retorna erro orientativo
        resp_canvas = servidor.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "aresta_capturar_canvas",
                    "arguments": {"alvo_viewport": "mapa"},
                },
            }
        )
        assert resp_canvas is not None
        res_canvas = resp_canvas["result"]
        assert res_canvas["isError"] is True
        texto_erro = res_canvas["content"][0]["text"]
        assert "aresta_renderizar_mapa" in texto_erro
        assert "aresta_obter_arvore" in texto_erro


def test_registrar_catalogo_ferramentas_croqui_sem_workspace(qapp, tmp_path: Path) -> None:
    """Verifica registro limpo mesmo quando workspace=None."""
    croqui = croqui_pb2.Croqui(uid="uid_croqui_sw", id="sem_ws", nome="Sem WS")
    model = CroquiModel(croqui)
    historico = GerenciadorHistorico()
    controller = CroquiController(model, historico)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)

    registrar_catalogo_ferramentas_croqui(
        servidor=servidor,
        croqui_model=model,
        croqui_controller=controller,
        historico=historico,
        workspace=None,
    )
    assert "aresta_alterar_campo" in servidor.ferramentas
