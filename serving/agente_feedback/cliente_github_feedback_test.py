# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes de comportamento e integração para `ClienteGithubFeedback` usando
micro-servidor HTTP local real para exercitar os endpoints REST do GitHub e download de anexos.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from serving.agente_feedback.cliente_github_feedback import (
    ClienteGithubFeedback,
    ErroComunicacaoGithub,
)


class _ManipuladorGithubLocal(BaseHTTPRequestHandler):
    rotas_get: dict[str, tuple[int, Any, str]] = {}
    rotas_post: dict[str, tuple[int, Any]] = {}
    requisicoes_post: list[tuple[str, dict[str, Any]]] = []

    def do_GET(self) -> None:
        status, conteudo, content_type = _ManipuladorGithubLocal.rotas_get.get(
            self.path, (404, {"message": "Not Found"}, "application/json")
        )
        corpo_bytes = (
            conteudo if isinstance(conteudo, bytes) else json.dumps(conteudo).encode("utf-8")
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(corpo_bytes)))
        self.end_headers()
        self.wfile.write(corpo_bytes)

    def do_POST(self) -> None:
        tamanho = int(self.headers.get("Content-Length", "0"))
        corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        _ManipuladorGithubLocal.requisicoes_post.append((self.path, corpo))
        status, payload = _ManipuladorGithubLocal.rotas_post.get(
            self.path, (201, {"number": 101, "html_url": "https://github.com/org/repo/pull/101"})
        )
        corpo_bytes = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo_bytes)))
        self.end_headers()
        self.wfile.write(corpo_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        pass


@pytest.fixture
def servidor_github_local() -> Any:
    _ManipuladorGithubLocal.rotas_get = {}
    _ManipuladorGithubLocal.rotas_post = {}
    _ManipuladorGithubLocal.requisicoes_post = []
    servidor = HTTPServer(("127.0.0.1", 0), _ManipuladorGithubLocal)
    porta = servidor.server_port
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{porta}", _ManipuladorGithubLocal
    servidor.shutdown()
    servidor.server_close()


def test_consulta_issue_pr_arquivos_cria_pr_comenta_e_baixa_anexo(
    servidor_github_local: Any,
) -> None:
    url_base, estado = servidor_github_local
    estado.rotas_get["/repos/aresta-climb/aresta_db/issues/10"] = (
        200,
        {
            "number": 10,
            "title": "[Croqui | br_mg_araxa] Feedback",
            "body": "Corpo da issue",
            "labels": [{"name": "feedback:croqui"}],
        },
        "application/json",
    )
    estado.rotas_get["/repos/aresta-climb/aresta_db/issues/20"] = (
        200,
        {
            "number": 20,
            "title": "PR existente",
            "body": "Corpo PR",
            "labels": [],
            "pull_request": {"url": f"{url_base}/repos/aresta-climb/aresta_db/pulls/20"},
        },
        "application/json",
    )
    estado.rotas_get["/repos/aresta-climb/aresta_db/pulls/20"] = (
        200,
        {"number": 20, "head": {"ref": "ai-fix/issue-10"}},
        "application/json",
    )
    estado.rotas_get["/repos/aresta-climb/aresta_db/pulls/20/files?per_page=100"] = (
        200,
        [{"filename": "database/br_mg_araxa/setor_a.md"}],
        "application/json",
    )
    estado.rotas_get[
        "/repos/aresta-climb/aresta_db/pulls?head=aresta-climb%3Aai-fix%2Fissue-10&state=open"
    ] = (
        200,
        [{"number": 20, "html_url": "https://github.com/aresta-climb/aresta_db/pull/20"}],
        "application/json",
    )
    estado.rotas_get[
        "/repos/aresta-climb/aresta_db/pulls?head=aresta-climb%3Abranch-vazia&state=open"
    ] = (200, [], "application/json")
    estado.rotas_get["/anexos/10/screenshot.webp"] = (200, b"bytes_webp", "image/webp")

    cliente = ClienteGithubFeedback(
        token="ghs_teste",
        repositorio="aresta-climb/aresta_db",
        url_base_api=url_base,
    )

    issue = cliente.obter_issue_ou_pr(10)
    assert issue.numero == 10
    assert issue.eh_pull_request is False
    assert issue.labels == ["feedback:croqui"]

    pr_info = cliente.obter_issue_ou_pr(20)
    assert pr_info.eh_pull_request is True
    assert pr_info.branch_head == "ai-fix/issue-10"

    assert cliente.obter_arquivos_modificados_pr(20) == ["database/br_mg_araxa/setor_a.md"]

    pr_encontrada = cliente.buscar_pr_aberta_por_branch("ai-fix/issue-10")
    assert pr_encontrada is not None
    assert pr_encontrada.numero == 20
    assert cliente.buscar_pr_aberta_por_branch("branch-vazia") is None

    nova_pr = cliente.criar_pull_request(
        branch_head="ai-fix/issue-11",
        titulo="fix: ajuste",
        corpo="Closes #11",
    )
    assert nova_pr.numero == 101

    cliente.publicar_comentario(10, "Comentário de teste")
    assert estado.requisicoes_post[-1] == (
        "/repos/aresta-climb/aresta_db/issues/10/comments",
        {"body": "Comentário de teste"},
    )

    anexo = cliente.baixar_imagem_anexo(f"{url_base}/anexos/10/screenshot.webp")
    assert anexo == (b"bytes_webp", "image/webp")
    assert cliente.baixar_imagem_anexo(f"{url_base}/anexos/404.webp") is None


def test_lanca_erro_comunicacao_github_quando_api_falha(servidor_github_local: Any) -> None:
    url_base, _ = servidor_github_local
    cliente = ClienteGithubFeedback(
        token="ghs_teste",
        repositorio="aresta-climb/aresta_db",
        url_base_api=url_base,
    )

    with pytest.raises(ErroComunicacaoGithub, match="404"):
        cliente.obter_issue_ou_pr(999)
