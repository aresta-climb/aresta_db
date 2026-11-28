# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Cliente HTTP multimodal com Function Calling (`parametersJsonSchema`) para o modelo
Gemini Flash (Google AI Studio), acoplado às ferramentas MCP do Editor Aresta.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

URL_BASE_GEMINI_PADRAO = "https://generativelanguage.googleapis.com/v1beta/models"
MODELO_GEMINI_AGENTE_PADRAO = "gemini-3.8-flash"
NOME_FERRAMENTA_FINALIZAR = "finalizar_resolucao"

FERRAMENTAS_MCP_EXCLUIDAS_FEEDBACK: frozenset[str] = frozenset(
    {
        "aresta_listar_croquis",
        "aresta_abrir_croqui_existente",
        "aresta_importar_croqui_oficial",
        "aresta_criar_novo_croqui",
        "aresta_particionar_pdf_croqui",
        "aresta_focar_elemento",
        "aresta_capturar_canvas",
        "aresta_obter_selecao_atual",
        "aresta_coletar_betas",
        "aresta_listar_betas_nao_scorados",
        "aresta_salvar",
        "aresta_compilar",
    }
)

DECLARACAO_FINALIZAR_RESOLUCAO: dict[str, Any] = {
    "name": NOME_FERRAMENTA_FINALIZAR,
    "description": (
        "Finaliza o atendimento do feedback. Emita acao='abrir_pr' (em paralelo às ferramentas "
        "de edição no mesmo turno quando os UIDs já forem conhecidos, ou após turnos de "
        "inspeção/criação) para validar, salvar e abrir a Pull Request; ou acao='nao_acionavel' "
        "para desistir com diagnóstico claro quando o relato for vago, subjetivo ou exigir "
        "edição manual no Editor Desktop."
    ),
    "parametersJsonSchema": {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["abrir_pr", "nao_acionavel"],
                "description": "'abrir_pr' para concluir a correção ou 'nao_acionavel' para desistir.",
            },
            "titulo_pr": {
                "type": "string",
                "description": "Título curto da PR (ex: 'fix(id_croqui): resumo'), quando acao='abrir_pr'.",
            },
            "resumo_mudanca": {
                "type": "string",
                "description": "Resumo claro das edições realizadas para o corpo da PR.",
            },
            "motivo": {
                "type": "string",
                "description": "Motivo detalhado caso acao='nao_acionavel'.",
            },
        },
        "required": ["acao"],
    },
}

_INSTRUCAO_SISTEMA_AGENTE = (
    "Você é o agente autônomo especialista de curadoria do banco de dados Aresta Climb (aresta_db), "
    "operando diretamente sobre o Editor Aresta em modo Headless via ferramentas MCP. "
    "Use sempre os UIDs reais das entidades, preserve UIDs existentes ao migrar escaladas "
    "(aresta_migrar_escalada) e finalize sempre chamando finalizar_resolucao."
)


class ErroComunicacaoGemini(RuntimeError):
    """Exceção lançada quando a comunicação com a API do Gemini falha ou retorna resposta inválida."""


@dataclass(frozen=True)
class ChamadaFerramentaAgente:
    """Representa uma invocação `functionCall` emitida pelo modelo em um turno."""

    nome: str
    argumentos: dict[str, Any]


@dataclass(frozen=True)
class RespostaTurnoGemini:
    """Resultado de um turno de inferência contendo chamadas, textos/raciocínio, uso de tokens e bloco bruto `model`."""

    chamadas: list[ChamadaFerramentaAgente]
    conteudo_modelo_bruto: dict[str, Any]
    textos_modelo: list[str] = field(default_factory=list)
    metadados_uso: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoFerramentaExecutada:
    """Resultado da execução local de uma ferramenta MCP (incluindo blocos visuais opcionais)."""

    nome: str
    resposta_json: dict[str, Any]
    imagens_inline: list[tuple[str, str]] = field(default_factory=list)


class InterfaceClienteGeminiFeedback(Protocol):
    """Protocolo compartilhado entre `ClienteGeminiFeedback` e `ClienteGeminiFeedbackFake`."""

    def executar_turno_agente(
        self,
        historico_contents: list[dict[str, Any]],
        declaracoes_ferramentas: list[dict[str, Any]],
    ) -> RespostaTurnoGemini: ...


def construir_declaracoes_ferramentas_gemini(
    ferramentas_mcp: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Converte o catálogo `tools/list` do `ServidorMCP` para `functionDeclarations` da API
    Gemini (`parametersJsonSchema`), omitindo ferramentas exclusivas de GUI/gestão global
    e o parâmetro `id_croqui` redundante na sessão single-croqui, e anexando `finalizar_resolucao`.
    """
    declaracoes: list[dict[str, Any]] = []
    for item in ferramentas_mcp:
        nome = str(item.get("name", ""))
        if not nome or nome in FERRAMENTAS_MCP_EXCLUIDAS_FEEDBACK:
            continue
        esquema_orig = dict(item.get("inputSchema") or {"type": "object", "properties": {}})
        props_orig = dict(esquema_orig.get("properties") or {})
        props_orig.pop("id_croqui", None)
        esquema_limpo = dict(esquema_orig)
        esquema_limpo["properties"] = props_orig
        declaracoes.append(
            {
                "name": nome,
                "description": str(item.get("description", "")),
                "parametersJsonSchema": esquema_limpo,
            }
        )
    declaracoes.append(DECLARACAO_FINALIZAR_RESOLUCAO)
    return declaracoes


def montar_turno_inicial_usuario(
    prompt_texto: str,
    screenshot_bytes: bytes | None = None,
    screenshot_mime: str = "image/webp",
) -> dict[str, Any]:
    """Constrói a mensagem inicial `role='user'` com o pacote Warm-Start e screenshot opcional."""
    partes: list[dict[str, Any]] = [{"text": prompt_texto}]
    if screenshot_bytes:
        partes.append(
            {
                "inlineData": {
                    "mimeType": screenshot_mime,
                    "data": base64.b64encode(screenshot_bytes).decode("ascii"),
                }
            }
        )
    return {"role": "user", "parts": partes}


def montar_turno_respostas_ferramentas(
    resultados: list[ResultadoFerramentaExecutada],
    aviso_orcamento: str = "",
) -> dict[str, Any]:
    """
    Constrói a mensagem de retorno `role='user'` contendo os `functionResponse`s executados
    no turno anterior, eventuais imagens PNG Base64 geradas por `aresta_renderizar_mapa`
    e aviso opcional de orçamento de turnos.
    """
    partes: list[dict[str, Any]] = []
    for res in resultados:
        partes.append(
            {
                "functionResponse": {
                    "name": res.nome,
                    "response": res.resposta_json,
                }
            }
        )
        for mime_type, dados_b64 in res.imagens_inline:
            partes.append(
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": dados_b64,
                    }
                }
            )
    if aviso_orcamento:
        partes.append({"text": aviso_orcamento})
    return {"role": "user", "parts": partes}


class ClienteGeminiFeedback:
    """Implementação real do cliente HTTP para Function Calling na API Gemini do Google AI Studio."""

    def __init__(
        self,
        api_key: str,
        url_base: str = URL_BASE_GEMINI_PADRAO,
        modelo: str = MODELO_GEMINI_AGENTE_PADRAO,
        timeout_segundos: int = 90,
    ) -> None:
        self._api_key = api_key
        self._url_base = url_base.rstrip("/")
        self._modelo = modelo
        self._timeout = timeout_segundos

    def executar_turno_agente(
        self,
        historico_contents: list[dict[str, Any]],
        declaracoes_ferramentas: list[dict[str, Any]],
    ) -> RespostaTurnoGemini:
        """Executa um turno do agente no Gemini com modo `ANY` (chamada de ferramenta garantida)."""
        url = f"{self._url_base}/{self._modelo}:generateContent?key={self._api_key}"
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": _INSTRUCAO_SISTEMA_AGENTE}]},
            "contents": historico_contents,
            "tools": [{"functionDeclarations": declaracoes_ferramentas}],
            "toolConfig": {"functionCallingConfig": {"mode": "ANY"}},
            "generationConfig": {"temperature": 0.1},
        }
        corpo_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=corpo_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                dados_brutos = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", errors="replace")
            raise ErroComunicacaoGemini(f"Erro HTTP {e.code} na API Gemini: {detalhe}") from e

        candidatos = dados_brutos.get("candidates") or []
        if not candidatos or "content" not in candidatos[0]:
            raise ErroComunicacaoGemini("Resposta vazia ou malformada da API Gemini.")

        conteudo_modelo: dict[str, Any] = dict(candidatos[0]["content"])
        partes_modelo = conteudo_modelo.get("parts") or []
        chamadas: list[ChamadaFerramentaAgente] = []
        textos_modelo: list[str] = []
        for parte in partes_modelo:
            texto_parte = str(parte.get("text") or "").strip()
            if texto_parte:
                prefixo = "[pensamento] " if parte.get("thought") else ""
                textos_modelo.append(f"{prefixo}{texto_parte}")
            fc = parte.get("functionCall")
            if isinstance(fc, dict) and fc.get("name"):
                chamadas.append(
                    ChamadaFerramentaAgente(
                        nome=str(fc["name"]),
                        argumentos=dict(fc.get("args") or {}),
                    )
                )

        if not chamadas:
            raise ErroComunicacaoGemini(
                "O modelo não retornou nenhuma chamada de ferramenta no turno."
            )

        uso_bruto = dados_brutos.get("usageMetadata") or {}
        metadados_uso = {str(k): int(v) for k, v in uso_bruto.items() if isinstance(v, int)}

        return RespostaTurnoGemini(
            chamadas=chamadas,
            conteudo_modelo_bruto=conteudo_modelo,
            textos_modelo=textos_modelo,
            metadados_uso=metadados_uso,
        )
