# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Aresta Contributors

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from aresta_api.proto.generated import beta_pb2

def gerar_prompt_avaliacao(
    nome_escalada: str,
    grau: str,
    setor: str,
    pico: str,
    candidatos: List[Dict[str, Any]]
) -> str:
    """
    Gera o prompt estruturado em português para o modelo LLM avaliar relevância
    e extrair o resumo de movimentos dos vídeos/posts candidatos.
    """
    prompt = f"""Você é um especialista em escalada em rocha brasileiro.
Sua missão é avaliar postagens e vídeos coletados na internet para verificar se eles correspondem
à escalada descrita abaixo, e extrair o resumo do beta (movimento chave/crux) caso exista.

Escalada Alvo:
- Nome da Via/Boulder: {nome_escalada}
- Grau: {grau or 'Não informado'}
- Setor: {setor or 'Não informado'}
- Pico/Região: {pico or 'Não informado'}

Candidatos encontrados na busca:
{json.dumps(candidatos, indent=2, ensure_ascii=False)}

Para cada candidato, avalie:
1. "score": Inteiro de 0 a 100 indicando a certeza de que a mídia mostra a via alvo.
2. "justificativa": Explicação sucinta em português do porquê desta nota.
3. "resumo_crux": Resumo claro em português dos movimentos chave, agarras ou sequência descrita (ou string vazia se não houver).

Responda OBRIGATORIAMENTE em formato JSON puro (uma lista de objetos com "url", "score", "justificativa", "resumo_crux"):
```json
[
  {{
    "url": "...",
    "score": 95,
    "justificativa": "...",
    "resumo_crux": "..."
  }}
]
```
"""
    return prompt


def parsear_resposta_llm(conteudo_resposta: str) -> List[Dict[str, Any]]:
    """
    Extrai e decodifica a lista JSON retornada pelo modelo LLM.
    """
    texto = conteudo_resposta.strip()
    match = re.search(r"```json\s*(.*?)\s*```", texto, re.DOTALL)
    if match:
        texto = match.group(1)

    try:
        dados = json.loads(texto)
        if isinstance(dados, list):
            return dados
        if isinstance(dados, dict) and "candidatos" in dados:
            return dados["candidatos"]
    except Exception:
        # Fallback de busca por array
        match_arr = re.search(r"\[\s*\{.*\}\s*\]", texto, re.DOTALL)
        if match_arr:
            try:
                return json.loads(match_arr.group(0))
            except Exception:
                pass
    return []


def avaliar_candidatos(
    nome_escalada: str,
    grau: str,
    setor: str,
    pico: str,
    midias: List[beta_pb2.MidiaBeta],
    client_llm: Optional[Any] = None
) -> List[beta_pb2.MidiaBeta]:
    """
    Avalia em lote os candidatos de uma via usando o client LLM fornecido,
    populando os metadados semânticos em cada MidiaBeta.
    """
    if not midias:
        return []

    candidatos_payload = [
        {
            "url": m.url,
            "titulo": m.titulo,
            "match_multiplas_fontes": m.match_multiplas_fontes,
            "match_nome_no_snippet": m.match_nome_no_snippet
        }
        for m in midias
    ]

    prompt = gerar_prompt_avaliacao(nome_escalada, grau, setor, pico, candidatos_payload)

    if client_llm and hasattr(client_llm, "gerar_texto"):
        resposta_texto = client_llm.gerar_texto(prompt)
        avaliacoes = parsear_resposta_llm(resposta_texto)
        mapa_avaliacoes = {a.get("url"): a for a in avaliacoes if "url" in a}

        for m in midias:
            if m.url in mapa_avaliacoes:
                dados_av = mapa_avaliacoes[m.url]
                m.meta.llm_confidence_score = int(dados_av.get("score", 0))
                m.meta.llm_reasoning = dados_av.get("justificativa", "")
                m.meta.resumo_do_movimento = dados_av.get("resumo_crux", "")

    return midias


def salvar_betas_pendentes(
    id_croqui: str,
    candidatos_por_escalada: List[beta_pb2.CandidatosBetaPorEscalada],
    caminho_arquivo: Path | str
) -> None:
    """
    Serializa a mensagem raiz BetasPendentes em formato protobuf binário (.binarypb).
    """
    msg = beta_pb2.BetasPendentes()
    msg.id_croqui = id_croqui
    msg.candidatos_por_escalada.extend(candidatos_por_escalada)

    path = Path(caminho_arquivo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(msg.SerializeToString())


def carregar_betas_pendentes(caminho_arquivo: Path | str) -> beta_pb2.BetasPendentes:
    """
    Desserializa o arquivo intermediário betas_pendentes.binarypb.
    """
    path = Path(caminho_arquivo)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    msg = beta_pb2.BetasPendentes()
    with open(path, "rb") as f:
        msg.ParseFromString(f.read())
    return msg
