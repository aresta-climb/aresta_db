# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import json
from pathlib import Path

from PySide6.QtWidgets import QLabel, QWidget

from aresta_api.proto.generated import croqui_pb2
from editor.mcp.despachante import DespachanteQt
from editor.mcp.ferramentas_visao import registrar_ferramentas_visao
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def _criar_ambiente_visao(tmp_path: Path):
    croqui = croqui_pb2.Croqui(uid="uid_croqui_vis", nome="Croqui Visual")
    pico = croqui.picos.add(nome="Pico do Sol")
    sg = pico.setores_ou_grupos.add()
    grupo = sg.grupo.conteudo
    grupo.uid = "uid_grupo_vis1"
    grupo.nome = "Grupo Leste"
    setor = grupo.setores.add().conteudo
    setor.uid = "uid_setor_vis1"
    setor.nome = "Setor Cristais"
    esc = setor.escaladas.add(uid="uid_via_vis001")
    esc.via_esportiva.nome = "Aresta Dourada"

    model = CroquiModel(croqui)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)

    widget_mapa = QLabel("Mapa Renderizado")
    widget_mapa.resize(240, 120)
    widget_foto = QLabel("Foto Renderizada")
    widget_foto.resize(320, 200)
    widget_dados = QWidget()
    widget_dados.resize(400, 300)

    widgets = {
        "janela": widget_dados,
        "dados": widget_dados,
        "mapa": widget_mapa,
        "foto": widget_foto,
    }

    registrar_ferramentas_visao(
        servidor=servidor,
        model=model,
        provedor_widget_alvo=lambda nome: widgets.get(nome),
        provedor_selecao_atual=lambda: {
            "uid": "uid_via_vis001",
            "caminho_selecionado": "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.escaladas.0",
            "aba_ativa": "mapa",
        },
    )
    return model, servidor, widgets


def test_aresta_capturar_canvas_retorna_png_base64_para_viewports(qapp, tmp_path: Path):
    """Verifica a captura de imagem PNG Base64 dos viewports de mapa, foto e dados."""
    _, servidor, _ = _criar_ambiente_visao(tmp_path)

    for nome_vp, larg_esperada, alt_esperada in [
        ("mapa", 240, 120),
        ("foto", 320, 200),
        ("dados", 400, 300),
    ]:
        resp = servidor.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "aresta_capturar_canvas",
                    "arguments": {"alvo_viewport": nome_vp},
                },
            }
        )
        assert resp is not None
        res = resp["result"]
        assert res["isError"] is False
        bloco_img = res["content"][0]
        bloco_txt = res["content"][1]
        assert bloco_img["type"] == "image"
        assert bloco_img["mimeType"] == "image/png"
        bytes_png = base64.b64decode(bloco_img["data"])
        assert bytes_png.startswith(b"\x89PNG\r\n\x1a\n")

        meta = json.loads(bloco_txt["text"])
        assert meta["viewport"] == nome_vp
        assert meta["largura"] == larg_esperada
        assert meta["altura"] == alt_esperada

    # Viewport indisponível deve retornar isError=True
    resp_invalido = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "aresta_capturar_canvas",
                "arguments": {"alvo_viewport": "inexistente"},
            },
        }
    )
    assert resp_invalido is not None
    assert resp_invalido["result"]["isError"] is True


def test_aresta_obter_arvore_e_selecao_atual_com_uids_e_caminhos_formatados(qapp, tmp_path: Path):
    """Verifica aresta_obter_arvore, recurso MCP e aresta_obter_selecao_atual enriquecido com caminho formatado."""
    model, servidor, _ = _criar_ambiente_visao(tmp_path)

    # 1. Árvore completa e subárvore por UID
    resp_arv = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "aresta_obter_arvore", "arguments": {}},
        }
    )
    assert resp_arv is not None
    dados_arv = resp_arv["result"]["structuredContent"]
    assert dados_arv["dados"]["nome"] == "Croqui Visual"
    caminhos_fmt = {item["uid"]: item["caminho_formatado"] for item in dados_arv["indice_uids"]}
    assert caminhos_fmt["uid_via_vis001"] == "Grupo Leste > Setor Cristais > Aresta Dourada"

    resp_sub = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "aresta_obter_arvore", "arguments": {"alvo": "uid_setor_vis1"}},
        }
    )
    assert resp_sub is not None
    dados_sub = resp_sub["result"]["structuredContent"]
    assert dados_sub["dados"]["nome"] == "Setor Cristais"

    # 2. Seleção atual enriquecida pelo IndiceUidsModel
    resp_sel = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "aresta_obter_selecao_atual", "arguments": {}},
        }
    )
    assert resp_sel is not None
    sel = resp_sel["result"]["structuredContent"]
    assert sel["uid"] == "uid_via_vis001"
    assert sel["aba_ativa"] == "mapa"
    assert sel["caminho_formatado"] == "Grupo Leste > Setor Cristais > Aresta Dourada"

    # 3. Sem provedor de seleção customizado deve retornar valores padrão vazios
    servidor_padrao = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_visao(servidor=servidor_padrao, model=model)
    resp_sel_vazia = servidor_padrao.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "aresta_obter_selecao_atual", "arguments": {}},
        }
    )
    assert resp_sel_vazia is not None
    assert resp_sel_vazia["result"]["structuredContent"] == {
        "uid": "",
        "caminho_selecionado": "",
        "aba_ativa": "",
        "caminho_formatado": "",
    }
