# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais e de integração para `ClienteGeminiFeedback` com Function Calling,
validando conversão de schemas MCP (`parametersJsonSchema`), turnos paralelos de 1 rodada,
respostas multimodais de `aresta_renderizar_mapa` e tratamento de falhas HTTP/payload.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from serving.agente_feedback.cliente_gemini_feedback import (
    NOME_FERRAMENTA_FINALIZAR,
    ChamadaFerramentaAgente,
    ClienteGeminiFeedback,
    ErroComunicacaoGemini,
    ResultadoFerramentaExecutada,
    construir_declaracoes_ferramentas_gemini,
    montar_turno_inicial_usuario,
    montar_turno_respostas_ferramentas,
)


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


def test_constroi_declaracoes_filtrando_ferramentas_gui_e_id_croqui_e_incluindo_finalizar() -> None:
    ferramentas_mcp = [
        {
            "name": "aresta_alterar_campo",
            "description": "Altera campo",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "alvo": {"type": "string"},
                    "valor": {},
                    "id_croqui": {"type": "string"},
                },
                "required": ["alvo"],
            },
        },
        {
            "name": "aresta_capturar_canvas",
            "description": "Captura janela",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "aresta_salvar",
            "description": "Salva no disco",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]

    declaracoes = construir_declaracoes_ferramentas_gemini(ferramentas_mcp)
    nomes = [d["name"] for d in declaracoes]
    assert nomes == ["aresta_alterar_campo", NOME_FERRAMENTA_FINALIZAR]
    props_alt = declaracoes[0]["parametersJsonSchema"]["properties"]
    assert "alvo" in props_alt
    assert "id_croqui" not in props_alt


def test_executa_turno_function_calling_preservando_thought_signature_e_imagens_inline(
    servidor_gemini_local: Any,
) -> None:
    url_base, estado = servidor_gemini_local
    conteudo_modelo_t1 = {
        "role": "model",
        "parts": [
            {
                "thought": True,
                "text": "Vou renderizar o mapa primeiro.",
                "thoughtSignature": "sig_123",
            },
            {
                "functionCall": {
                    "name": "aresta_renderizar_mapa",
                    "args": {"alvo": "uid_setor_01"},
                }
            },
        ],
    }
    conteudo_modelo_t2 = {
        "role": "model",
        "parts": [
            {
                "functionCall": {
                    "name": "aresta_alterar_campo",
                    "args": {"alvo": "uid_poi_01", "campo": "circulo.x", "valor": 120},
                }
            },
            {
                "functionCall": {
                    "name": NOME_FERRAMENTA_FINALIZAR,
                    "args": {
                        "acao": "abrir_pr",
                        "titulo_pr": "fix(croqui): ajusta POI",
                        "resumo_mudanca": "Move POI para x=120.",
                    },
                }
            },
        ],
    }
    estado.respostas_programadas.append(
        (
            200,
            {
                "candidates": [{"content": conteudo_modelo_t1}],
                "usageMetadata": {
                    "promptTokenCount": 1200,
                    "candidatesTokenCount": 45,
                    "thoughtsTokenCount": 80,
                    "totalTokenCount": 1325,
                },
            },
        )
    )
    estado.respostas_programadas.append(
        (
            200,
            {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {"text": "Ajustando coordenada do POI."},
                                *conteudo_modelo_t2["parts"],
                            ],
                        }
                    }
                ]
            },
        )
    )

    cliente = ClienteGeminiFeedback(api_key="chave-teste", url_base=url_base)
    declaracoes = construir_declaracoes_ferramentas_gemini([])

    historico = [
        montar_turno_inicial_usuario(
            prompt_texto="Prompt Warm-Start",
            screenshot_bytes=b"\x89PNG\r\n",
            screenshot_mime="image/png",
        )
    ]
    resp_t1 = cliente.executar_turno_agente(historico, declaracoes)
    assert resp_t1.chamadas == [
        ChamadaFerramentaAgente("aresta_renderizar_mapa", {"alvo": "uid_setor_01"})
    ]
    assert resp_t1.conteudo_modelo_bruto == conteudo_modelo_t1
    assert resp_t1.textos_modelo == ["[pensamento] Vou renderizar o mapa primeiro."]
    assert resp_t1.metadados_uso["totalTokenCount"] == 1325

    historico.append(resp_t1.conteudo_modelo_bruto)
    historico.append(
        montar_turno_respostas_ferramentas(
            [
                ResultadoFerramentaExecutada(
                    nome="aresta_renderizar_mapa",
                    resposta_json={"textos": ["Mapa renderizado"]},
                    imagens_inline=[("image/png", "aW1nX2I2NA==")],
                )
            ],
            aviso_orcamento="Último turno disponível.",
        )
    )

    resp_t2 = cliente.executar_turno_agente(historico, declaracoes)
    assert len(resp_t2.chamadas) == 2
    assert resp_t2.chamadas[1].nome == NOME_FERRAMENTA_FINALIZAR
    assert resp_t2.textos_modelo == ["Ajustando coordenada do POI."]
    assert resp_t2.metadados_uso == {}

    req_t2 = estado.requisicoes_recebidas[1]["corpo"]
    assert req_t2["toolConfig"]["functionCallingConfig"]["mode"] == "ANY"
    assert req_t2["contents"][1]["parts"][0]["thoughtSignature"] == "sig_123"
    partes_user_t2 = req_t2["contents"][2]["parts"]
    assert partes_user_t2[0]["functionResponse"]["name"] == "aresta_renderizar_mapa"
    assert partes_user_t2[1]["inlineData"]["data"] == "aW1nX2I2NA=="
    assert partes_user_t2[2]["text"] == "Último turno disponível."


def test_lanca_erro_comunicacao_para_falha_http_resposta_vazia_ou_sem_function_call(
    servidor_gemini_local: Any,
) -> None:
    url_base, estado = servidor_gemini_local
    estado.respostas_programadas.append((429, {"error": {"message": "Quota exceeded"}}))
    estado.respostas_programadas.append((200, {"candidates": []}))
    estado.respostas_programadas.append(
        (200, {"candidates": [{"content": {"role": "model", "parts": [{"text": "Sem tool"}]}}]})
    )

    cliente = ClienteGeminiFeedback(api_key="chave-teste", url_base=url_base)
    historico = [montar_turno_inicial_usuario("Prompt sem screenshot")]
    decls = construir_declaracoes_ferramentas_gemini([])

    with pytest.raises(ErroComunicacaoGemini, match="429"):
        cliente.executar_turno_agente(historico, decls)

    with pytest.raises(ErroComunicacaoGemini, match="vazia ou malformada"):
        cliente.executar_turno_agente(historico, decls)

    with pytest.raises(ErroComunicacaoGemini, match="nenhuma chamada de ferramenta"):
        cliente.executar_turno_agente(historico, decls)
