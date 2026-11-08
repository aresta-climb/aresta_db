# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes de comportamento e integração para `ClienteGeminiFeedback` utilizando
um micro-servidor HTTP local real para validar a comunicação multimodal e o JSON Schema.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from serving.agente_feedback.cliente_gemini_feedback import (
    ClienteGeminiFeedback,
    ErroComunicacaoGemini,
)
from serving.agente_feedback.renderizador_regua_mapa import MapaAnotadoEmMemoria


class _ManipuladorGeminiLocal(BaseHTTPRequestHandler):
    respostas_programadas: list[tuple[int, dict[str, Any]]] = []
    requisicoes_recebidas: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        tamanho = int(self.headers.get("Content-Length", "0"))
        corpo = self.rfile.read(tamanho).decode("utf-8")
        _ManipuladorGeminiLocal.requisicoes_recebidas.append(
            {
                "caminho": self.path,
                "corpo": json.loads(corpo),
            }
        )
        status, payload = _ManipuladorGeminiLocal.respostas_programadas.pop(0)
        corpo_resp = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo_resp)))
        self.end_headers()
        self.wfile.write(corpo_resp)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def servidor_gemini_local() -> Any:
    _ManipuladorGeminiLocal.respostas_programadas = []
    _ManipuladorGeminiLocal.requisicoes_recebidas = []
    servidor = HTTPServer(("127.0.0.1", 0), _ManipuladorGeminiLocal)
    porta = servidor.server_port
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{porta}", _ManipuladorGeminiLocal
    servidor.shutdown()
    servidor.server_close()


def test_desambigua_arquivos_enviando_indice_e_screenshot_ao_servidor(
    servidor_gemini_local: Any,
) -> None:
    url_base, estado = servidor_gemini_local
    estado.respostas_programadas.append(
        (
            200,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {"arquivos_selecionados": ["setor_bem_vindo.md"]}
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )
    )

    cliente = ClienteGeminiFeedback(
        api_key="chave-teste",
        url_base=url_base,
        modelo="gemini-2.5-flash",
    )
    arquivos = cliente.desambiguar_arquivos_croqui(
        indice_compacto="- setor_bem_vindo.md | Setor: Setor Bem-vindo",
        descricao_feedback="A via 03 na imagem é 7b",
        instrucao_extra="Verifique o mapa",
        screenshot_bytes=b"\x89PNG\r\n",
        screenshot_mime="image/png",
    )

    assert arquivos == ["setor_bem_vindo.md"]
    assert len(estado.requisicoes_recebidas) == 1
    req = estado.requisicoes_recebidas[0]
    assert "gemini-2.5-flash:generateContent?key=chave-teste" in req["caminho"]
    partes = req["corpo"]["contents"][0]["parts"]
    assert len(partes) == 2
    assert partes[1]["inlineData"]["mimeType"] == "image/png"


def test_gera_proposta_de_alteracao_multimodal_com_mapas_anotados_e_erro_anterior(
    servidor_gemini_local: Any,
) -> None:
    url_base, estado = servidor_gemini_local
    resposta_json = {
        "acionavel": True,
        "titulo_pr": "fix(br_mg_araxa): ajusta grau da via Excalibur para 7b",
        "resumo_mudanca": "Alterado campo dificuldade de BR_7C para BR_7B.",
        "motivo_nao_acionavel": "",
        "alteracoes": [
            {
                "arquivo_relativo": "setor_bem_vindo.md",
                "conteudo_novo": "---\nnome: Setor Bem-vindo\n---\n",
            }
        ],
    }
    estado.respostas_programadas.append(
        (
            200,
            {"candidates": [{"content": {"parts": [{"text": json.dumps(resposta_json)}]}}]},
        )
    )

    cliente = ClienteGeminiFeedback(api_key="chave-teste", url_base=url_base)
    proposta = cliente.gerar_proposta_alteracao(
        croqui_id="br_mg_araxa",
        descricao_feedback="O grau da Excalibur é 7b",
        instrucao_extra="Confirmo o ajuste",
        arquivos_atuais={"setor_bem_vindo.md": "---\nnome: Setor Bem-vindo\n---\n"},
        screenshot_bytes=b"bytes_screenshot",
        screenshot_mime="image/webp",
        mapas_anotados=[
            MapaAnotadoEmMemoria(
                caminho_imagem_mapa="imagens/setor_p1.webp",
                largura_mapa=1152,
                altura_mapa=1270,
                dados_imagem=b"bytes_mapa_regua",
            )
        ],
        erro_validacao_anterior="Erro de schema na tentativa anterior",
    )

    assert proposta.acionavel is True
    assert proposta.titulo_pr == "fix(br_mg_araxa): ajusta grau da via Excalibur para 7b"
    assert len(proposta.alteracoes) == 1
    assert proposta.alteracoes[0].arquivo_relativo == "setor_bem_vindo.md"

    partes_enviadas = estado.requisicoes_recebidas[0]["corpo"]["contents"][0]["parts"]
    # Texto principal + screenshot + texto descritivo do mapa + imagem do mapa com régua = 4 partes
    assert len(partes_enviadas) == 4
    assert "Erro de schema na tentativa anterior" in partes_enviadas[0]["text"]


def test_lanca_erro_comunicacao_quando_api_retorna_http_erro_ou_json_invalido(
    servidor_gemini_local: Any,
) -> None:
    url_base, estado = servidor_gemini_local
    estado.respostas_programadas.append((429, {"error": {"message": "Quota exceeded"}}))
    estado.respostas_programadas.append((200, {"candidates": []}))

    cliente = ClienteGeminiFeedback(api_key="chave-teste", url_base=url_base)

    with pytest.raises(ErroComunicacaoGemini, match="429"):
        cliente.desambiguar_arquivos_croqui("indice", "desc")

    with pytest.raises(ErroComunicacaoGemini, match="Resposta vazia ou malformada"):
        cliente.gerar_proposta_alteracao(
            croqui_id="br_mg_araxa",
            descricao_feedback="desc",
            instrucao_extra="",
            arquivos_atuais={"setor.md": "conteudo"},
        )
