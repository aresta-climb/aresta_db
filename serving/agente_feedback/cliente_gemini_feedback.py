# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Cliente HTTP estruturado para o modelo multimodal Gemini Flash (Google AI Studio),
responsável por desambiguar arquivos `.md` a partir de índice compacto e gerar propostas
de alteração de croquis baseadas em texto, captura de tela e mapas com régua cartesiana.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from serving.agente_feedback.renderizador_regua_mapa import MapaAnotadoEmMemoria

URL_BASE_GEMINI_PADRAO = "https://generativelanguage.googleapis.com/v1beta/models"
MODELO_GEMINI_PROPOSTA_PADRAO = "gemini-3.8-flash"
MODELO_GEMINI_DESAMBIGUACAO_PADRAO = "gemini-3.5-flash-lite"


class ErroComunicacaoGemini(RuntimeError):
    """Exceção lançada quando a comunicação com a API do Gemini falha ou retorna resposta inválida."""


@dataclass(frozen=True)
class AlteracaoArquivoProposta:
    """Representa o conteúdo completo atualizado de um arquivo relativo dentro de `database/<croqui_id>/`."""

    arquivo_relativo: str
    conteudo_novo: str


@dataclass(frozen=True)
class RespostaPropostaGemini:
    """Resposta estruturada retornada pelo modelo de IA para um feedback de croqui."""

    acionavel: bool
    titulo_pr: str
    resumo_mudanca: str
    motivo_nao_acionavel: str
    alteracoes: list[AlteracaoArquivoProposta]


class InterfaceClienteGeminiFeedback(Protocol):
    """Protocolo para o cliente Gemini real e sua implementação Fake determinística."""

    def desambiguar_arquivos_croqui(
        self,
        indice_compacto: str,
        descricao_feedback: str,
        instrucao_extra: str = "",
        screenshot_bytes: bytes | None = None,
        screenshot_mime: str = "image/webp",
    ) -> list[str]: ...

    def gerar_proposta_alteracao(
        self,
        croqui_id: str,
        descricao_feedback: str,
        instrucao_extra: str,
        arquivos_atuais: dict[str, str],
        screenshot_bytes: bytes | None = None,
        screenshot_mime: str = "image/webp",
        mapas_anotados: list[MapaAnotadoEmMemoria] | None = None,
        erro_validacao_anterior: str = "",
    ) -> RespostaPropostaGemini: ...


_SCHEMA_DESAMBIGUACAO: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "arquivos_selecionados": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        }
    },
    "required": ["arquivos_selecionados"],
}

_SCHEMA_PROPOSTA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "acionavel": {"type": "BOOLEAN"},
        "titulo_pr": {"type": "STRING"},
        "resumo_mudanca": {"type": "STRING"},
        "motivo_nao_acionavel": {"type": "STRING"},
        "alteracoes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "arquivo_relativo": {"type": "STRING"},
                    "conteudo_novo": {"type": "STRING"},
                },
                "required": ["arquivo_relativo", "conteudo_novo"],
            },
        },
    },
    "required": [
        "acionavel",
        "titulo_pr",
        "resumo_mudanca",
        "motivo_nao_acionavel",
        "alteracoes",
    ],
}

_INSTRUCOES_SISTEMA_PROPOSTA = """Você é o assistente especialista de manutenção do banco de dados de escalada Aresta Climb (`aresta_db`).
Sua tarefa é analisar o feedback de um usuário (e eventuais instruções de um mantenedor via `/ai-fix`) e propor a edição exata nos arquivos `.md` ou `.yaml` do croqui.

Regras Inegociáveis de Formato:
1. Preserve TODOS os cabeçalhos `# SPDX-License-Identifier: ODbL-1.0` e `# Copyright (C) 2026 Aresta Climb Contributors`, bem como todos os `uid` existentes.
2. Enums de dificuldade válidos no Protobuf:
   - Vias: `PROJETO`, `BR_1`, `BR_2`, `BR_2SUP`, `BR_3`, `BR_3SUP`, `BR_4`, `BR_4SUP`, `BR_5`, `BR_5SUP`, `BR_6`, `BR_6SUP`, `BR_6SUP_BARRA_7A`, `BR_7A`, `BR_7A_BARRA_7B`, `BR_7B`, `BR_7B_BARRA_7C`, `BR_7C`, `BR_7C_BARRA_8A`, `BR_8A`, `BR_8B`, `BR_8C`, `BR_9A`, `BR_9B`, `BR_9C`, `BR_10A`, `BR_10B`, `BR_10C`, `BR_11A`, `BR_11B`, `BR_11C`.
   - Boulders: `PROJETO`, `V0`, `V1`, `V2`, `V3`, `V4`, `V5`, `V6`, `V7`, `V8`, `V9`, `V10`, `V11`, `V12`, `V13`, `V14`, `V15`, `V16`.
3. Se imagens de mapa do setor forem fornecidas, elas contêm uma RÉGUA CARTESIANA graduada em pixels (eixo X amarelo no topo/base de 0 a `largura_mapa`, eixo Y azul nas laterais de 0 a `altura_mapa`) e os `pontos_de_interesse` atuais desenhados em vermelho/amarelo. Use essa régua para localizar ou ajustar coordenadas `circulo: {x, y, raio}`.
4. Se o feedback exigir redesenhar linhas vetoriais complexas (`tracados`) ou for vago/impossível de determinar com segurança, retorne `acionavel: false` e explique em `motivo_nao_acionavel`.
"""


class ClienteGeminiFeedback:
    """Implementação real do cliente HTTP para a API Gemini do Google AI Studio."""

    def __init__(
        self,
        api_key: str,
        url_base: str = URL_BASE_GEMINI_PADRAO,
        modelo_proposta: str = MODELO_GEMINI_PROPOSTA_PADRAO,
        modelo_desambiguacao: str = MODELO_GEMINI_DESAMBIGUACAO_PADRAO,
        timeout_segundos: int = 90,
    ) -> None:
        self._api_key = api_key
        self._url_base = url_base.rstrip("/")
        self._modelo_proposta = modelo_proposta
        self._modelo_desambiguacao = modelo_desambiguacao
        self._timeout = timeout_segundos

    def _executar_chamada_json(
        self,
        modelo: str,
        partes: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self._url_base}/{modelo}:generateContent?key={self._api_key}"
        payload = {
            "contents": [{"role": "user", "parts": partes}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
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
        if not candidatos:
            raise ErroComunicacaoGemini("Resposta vazia ou malformada da API Gemini.")
        texto_json = candidatos[0]["content"]["parts"][0]["text"]
        return dict(json.loads(texto_json))

    def desambiguar_arquivos_croqui(
        self,
        indice_compacto: str,
        descricao_feedback: str,
        instrucao_extra: str = "",
        screenshot_bytes: bytes | None = None,
        screenshot_mime: str = "image/webp",
    ) -> list[str]:
        """Seleciona quais arquivos `.md` de `database/<croqui_id>/` devem ser inspecionados."""
        prompt = (
            "Com base no índice compacto do croqui abaixo e no feedback do usuário, "
            "retorne em `arquivos_selecionados` os nomes dos arquivos `.md` que precisam ser "
            "lidos/modificados (máximo de 3 arquivos).\n\n"
            f"### Índice Compacto do Croqui:\n{indice_compacto}\n\n"
            f"### Feedback do Usuário:\n{descricao_feedback}\n"
        )
        if instrucao_extra:
            prompt += f"\n### Instrução do Mantenedor (/ai-fix):\n{instrucao_extra}\n"

        partes: list[dict[str, Any]] = [{"text": prompt}]
        if screenshot_bytes:
            partes.append(
                {
                    "inlineData": {
                        "mimeType": screenshot_mime,
                        "data": base64.b64encode(screenshot_bytes).decode("ascii"),
                    }
                }
            )

        resposta = self._executar_chamada_json(
            self._modelo_desambiguacao, partes, _SCHEMA_DESAMBIGUACAO
        )
        return [str(a) for a in resposta.get("arquivos_selecionados", [])]

    def gerar_proposta_alteracao(
        self,
        croqui_id: str,
        descricao_feedback: str,
        instrucao_extra: str,
        arquivos_atuais: dict[str, str],
        screenshot_bytes: bytes | None = None,
        screenshot_mime: str = "image/webp",
        mapas_anotados: list[MapaAnotadoEmMemoria] | None = None,
        erro_validacao_anterior: str = "",
    ) -> RespostaPropostaGemini:
        """Gera a proposta estruturada de alteração nos arquivos `.md`/`.yaml` do croqui."""
        blocos_arquivos = "\n\n".join(
            f"=== ARQUIVO: {nome} ===\n{conteudo}\n=== FIM ARQUIVO: {nome} ==="
            for nome, conteudo in arquivos_atuais.items()
        )
        prompt = (
            f"{_INSTRUCOES_SISTEMA_PROPOSTA}\n\n"
            f"Croqui ID: {croqui_id}\n"
            f"### Feedback do Usuário:\n{descricao_feedback}\n"
        )
        if instrucao_extra:
            prompt += f"\n### Instrução do Mantenedor (/ai-fix):\n{instrucao_extra}\n"
        if erro_validacao_anterior:
            prompt += (
                "\n### ATENÇÃO — ERRO DE VALIDAÇÃO NA TENTATIVA ANTERIOR (CORRIJA):\n"
                f"{erro_validacao_anterior}\n"
            )
        prompt += f"\n### Arquivos Atuais:\n{blocos_arquivos}\n"

        partes: list[dict[str, Any]] = [{"text": prompt}]
        if screenshot_bytes:
            partes.append(
                {
                    "inlineData": {
                        "mimeType": screenshot_mime,
                        "data": base64.b64encode(screenshot_bytes).decode("ascii"),
                    }
                }
            )

        for mapa in mapas_anotados or []:
            partes.append(
                {
                    "text": (
                        f"Mapa do setor `{mapa.caminho_imagem_mapa}` com régua cartesiana "
                        f"(largura={mapa.largura_mapa}, altura={mapa.altura_mapa}):"
                    )
                }
            )
            partes.append(
                {
                    "inlineData": {
                        "mimeType": mapa.mime_type,
                        "data": base64.b64encode(mapa.dados_imagem).decode("ascii"),
                    }
                }
            )

        dados = self._executar_chamada_json(self._modelo_proposta, partes, _SCHEMA_PROPOSTA)
        alteracoes = [
            AlteracaoArquivoProposta(
                arquivo_relativo=str(item["arquivo_relativo"]),
                conteudo_novo=str(item["conteudo_novo"]),
            )
            for item in dados.get("alteracoes", [])
        ]
        return RespostaPropostaGemini(
            acionavel=bool(dados.get("acionavel", False)),
            titulo_pr=str(dados.get("titulo_pr", "")),
            resumo_mudanca=str(dados.get("resumo_mudanca", "")),
            motivo_nao_acionavel=str(dados.get("motivo_nao_acionavel", "")),
            alteracoes=alteracoes,
        )
