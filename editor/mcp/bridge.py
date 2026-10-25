# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

import httpx

from editor.mcp.sessao import descobrir_url_mcp_ativa


def _escrever_jsonrpc(saida: TextIO, pacote: dict[str, Any]) -> None:
    saida.write(json.dumps(pacote, ensure_ascii=False) + "\n")
    saida.flush()


def executar_ponte_stdio(
    entrada: TextIO | None = None,
    saida: TextIO | None = None,
    diretorio_sessao: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 30.0,
) -> int:
    """
    Executa o loop de ponte MCP sobre `stdio`, lendo pacotes JSON-RPC 2.0 linha a linha
    de `entrada` (`sys.stdin`), encaminhando-os via HTTP local para a instância ativa
    do Editor Aresta descoberta em `mcp_sessao.json` e gravando as respostas em `saida` (`sys.stdout`).
    """
    fluxo_in = entrada if entrada is not None else sys.stdin
    fluxo_out = saida if saida is not None else sys.stdout

    with httpx.Client(timeout=timeout) as http:
        for linha_bruta in fluxo_in:
            linha = linha_bruta.strip()
            if not linha:
                continue

            try:
                mensagem = json.loads(linha)
            except ValueError:
                _escrever_jsonrpc(
                    fluxo_out,
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Erro de sintaxe JSON na entrada stdio.",
                        },
                    },
                )
                continue

            url_http, token = descobrir_url_mcp_ativa(diretorio_base=diretorio_sessao, env=env)
            cabecalhos = {"X-Aresta-Mcp-Token": token} if token else {}

            try:
                resposta = http.post(url_http, json=mensagem, headers=cabecalhos)
                if resposta.status_code == 202 or not resposta.content:
                    continue
                _escrever_jsonrpc(fluxo_out, resposta.json())
            except httpx.HTTPError as exc:
                req_id = mensagem.get("id") if isinstance(mensagem, dict) else None
                if req_id is not None:
                    _escrever_jsonrpc(
                        fluxo_out,
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32000,
                                "message": (
                                    f"Não foi possível conectar ao Editor Aresta em {url_http}. "
                                    f"Verifique se o editor está aberto ({exc})."
                                ),
                            },
                        },
                    )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(executar_ponte_stdio())
