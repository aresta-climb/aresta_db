# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Cliente HTTP para interação com a API REST do GitHub no fluxo de resolução de feedbacks,
incluindo leitura de Issues/PRs, listagem de arquivos de PR, criação/busca de PRs,
publicação de comentários e download de imagens de captura de tela.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

URL_BASE_GITHUB_API_PADRAO = "https://api.github.com"


class ErroComunicacaoGithub(RuntimeError):
    """Exceção lançada quando uma chamada à API REST do GitHub falha."""


@dataclass(frozen=True)
class DadosIssueOuPr:
    """Metadados de uma Issue ou Pull Request retornados pela API do GitHub."""

    numero: int
    titulo: str
    corpo: str
    labels: list[str]
    eh_pull_request: bool
    branch_head: str | None


@dataclass(frozen=True)
class DadosPullRequestAberta:
    """Representa uma Pull Request aberta associada a uma branch de correção."""

    numero: int
    url_html: str
    branch_head: str


class InterfaceClienteGithubFeedback(Protocol):
    """Protocolo compartilhado entre `ClienteGithubFeedback` e `ClienteGithubFeedbackFake`."""

    def obter_issue_ou_pr(self, numero: int) -> DadosIssueOuPr: ...

    def obter_arquivos_modificados_pr(self, numero_pr: int) -> list[str]: ...

    def buscar_pr_aberta_por_branch(self, branch_head: str) -> DadosPullRequestAberta | None: ...

    def criar_pull_request(
        self,
        branch_head: str,
        titulo: str,
        corpo: str,
        branch_base: str = "main",
    ) -> DadosPullRequestAberta: ...

    def publicar_comentario(self, numero_issue_ou_pr: int, corpo_comentario: str) -> None: ...

    def baixar_imagem_anexo(self, url: str) -> tuple[bytes, str] | None: ...


class ClienteGithubFeedback:
    """Implementação real do cliente HTTP para a API v3 REST do GitHub."""

    def __init__(
        self,
        token: str,
        repositorio: str = "aresta-climb/aresta_db",
        url_base_api: str = URL_BASE_GITHUB_API_PADRAO,
        timeout_segundos: int = 30,
    ) -> None:
        self._token = token
        self._repositorio = repositorio
        self._dono = repositorio.split("/")[0]
        self._url_base_api = url_base_api.rstrip("/")
        self._timeout = timeout_segundos

    def _requisitar_json(
        self,
        metodo: str,
        caminho: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._url_base_api}{caminho}"
        dados_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
        cabecalhos = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Aresta-AI-Feedback-Solver",
        }
        if dados_bytes is not None:
            cabecalhos["Content-Type"] = "application/json"

        req = urllib.request.Request(url=url, data=dados_bytes, headers=cabecalhos, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", errors="replace")
            raise ErroComunicacaoGithub(
                f"Erro HTTP {e.code} no GitHub ({caminho}): {detalhe}"
            ) from e

    def obter_issue_ou_pr(self, numero: int) -> DadosIssueOuPr:
        """Busca os metadados de uma Issue ou PR pelo seu número."""
        dados = self._requisitar_json("GET", f"/repos/{self._repositorio}/issues/{numero}")
        labels = [str(item["name"]) for item in dados.get("labels", []) if isinstance(item, dict)]
        eh_pr = "pull_request" in dados
        branch_head: str | None = None
        if eh_pr:
            dados_pr = self._requisitar_json("GET", f"/repos/{self._repositorio}/pulls/{numero}")
            branch_head = str(dados_pr["head"]["ref"])

        return DadosIssueOuPr(
            numero=int(dados["number"]),
            titulo=str(dados.get("title") or ""),
            corpo=str(dados.get("body") or ""),
            labels=labels,
            eh_pull_request=eh_pr,
            branch_head=branch_head,
        )

    def obter_arquivos_modificados_pr(self, numero_pr: int) -> list[str]:
        """Lista os caminhos dos arquivos modificados em uma Pull Request."""
        itens = self._requisitar_json(
            "GET",
            f"/repos/{self._repositorio}/pulls/{numero_pr}/files?per_page=100",
        )
        return [str(arq["filename"]) for arq in itens]

    def buscar_pr_aberta_por_branch(self, branch_head: str) -> DadosPullRequestAberta | None:
        """Retorna a Pull Request aberta para `branch_head` se já existir."""
        head_query = urllib.parse.quote(f"{self._dono}:{branch_head}", safe="")
        itens = self._requisitar_json(
            "GET",
            f"/repos/{self._repositorio}/pulls?head={head_query}&state=open",
        )
        if not itens:
            return None
        primeiro = itens[0]
        return DadosPullRequestAberta(
            numero=int(primeiro["number"]),
            url_html=str(primeiro["html_url"]),
            branch_head=branch_head,
        )

    def criar_pull_request(
        self,
        branch_head: str,
        titulo: str,
        corpo: str,
        branch_base: str = "main",
    ) -> DadosPullRequestAberta:
        """Abre uma nova Pull Request de `branch_head` para `branch_base`."""
        resposta = self._requisitar_json(
            "POST",
            f"/repos/{self._repositorio}/pulls",
            payload={
                "title": titulo,
                "head": branch_head,
                "base": branch_base,
                "body": corpo,
            },
        )
        return DadosPullRequestAberta(
            numero=int(resposta["number"]),
            url_html=str(resposta["html_url"]),
            branch_head=branch_head,
        )

    def publicar_comentario(self, numero_issue_ou_pr: int, corpo_comentario: str) -> None:
        """Adiciona um comentário em uma Issue ou Pull Request."""
        self._requisitar_json(
            "POST",
            f"/repos/{self._repositorio}/issues/{numero_issue_ou_pr}/comments",
            payload={"body": corpo_comentario},
        )

    def baixar_imagem_anexo(self, url: str) -> tuple[bytes, str] | None:
        """Baixa os bytes e o MIME type da captura de tela da Issue; retorna None se falhar."""
        req = urllib.request.Request(url=url, headers={"User-Agent": "Aresta-AI-Feedback-Solver"})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                mime = resp.headers.get_content_type()
                return resp.read(), mime
        except urllib.error.URLError:
            return None
