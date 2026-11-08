# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca test-only de Fake determinístico em memória para `ClienteGithubFeedback`.
"""

from __future__ import annotations

from serving.agente_feedback.cliente_github_feedback import (
    DadosIssueOuPr,
    DadosPullRequestAberta,
    ErroComunicacaoGithub,
)


class ClienteGithubFeedbackFake:
    """Fake determinístico em memória que cumpre `InterfaceClienteGithubFeedback`."""

    def __init__(self, erro_simulado: str | None = None) -> None:
        self._erro_simulado = erro_simulado
        self._issues_prs: dict[int, DadosIssueOuPr] = {}
        self._arquivos_pr: dict[int, list[str]] = {}
        self._prs_por_branch: dict[str, DadosPullRequestAberta] = {}
        self._anexos: dict[str, tuple[bytes, str]] = {}
        self._proximo_numero_pr = 100
        self.comentarios_publicados: list[tuple[int, str]] = []

    def registrar_issue_ou_pr(self, dados: DadosIssueOuPr) -> None:
        """Registra uma Issue ou PR em memória para consulta nos testes."""
        self._issues_prs[dados.numero] = dados

    def registrar_arquivos_pr(self, numero_pr: int, arquivos: list[str]) -> None:
        """Registra a lista de arquivos modificados por uma PR específica."""
        self._arquivos_pr[numero_pr] = list(arquivos)

    def registrar_anexo(self, url: str, dados: bytes, mime_type: str = "image/webp") -> None:
        """Registra uma imagem de captura de tela em memória."""
        self._anexos[url] = (dados, mime_type)

    def obter_issue_ou_pr(self, numero: int) -> DadosIssueOuPr:
        """Retorna a Issue/PR registrada ou lança `ErroComunicacaoGithub`."""
        if self._erro_simulado:
            raise ErroComunicacaoGithub(self._erro_simulado)
        return self._issues_prs[numero]

    def obter_arquivos_modificados_pr(self, numero_pr: int) -> list[str]:
        """Retorna a lista de arquivos modificados registrada para `numero_pr`."""
        return list(self._arquivos_pr.get(numero_pr, []))

    def buscar_pr_aberta_por_branch(self, branch_head: str) -> DadosPullRequestAberta | None:
        """Busca PR aberta em memória pela `branch_head`."""
        return self._prs_por_branch.get(branch_head)

    def criar_pull_request(
        self,
        branch_head: str,
        titulo: str,
        corpo: str,
        branch_base: str = "main",
    ) -> DadosPullRequestAberta:
        """Cria e armazena uma Pull Request em memória."""
        if self._erro_simulado:
            raise ErroComunicacaoGithub(self._erro_simulado)
        numero = self._proximo_numero_pr
        self._proximo_numero_pr += 1
        pr = DadosPullRequestAberta(
            numero=numero,
            url_html=f"https://github.com/aresta-climb/aresta_db/pull/{numero}",
            branch_head=branch_head,
        )
        self._prs_por_branch[branch_head] = pr
        return pr

    def publicar_comentario(self, numero_issue_ou_pr: int, corpo_comentario: str) -> None:
        """Registra o comentário publicado na Issue ou Pull Request."""
        self.comentarios_publicados.append((numero_issue_ou_pr, corpo_comentario))

    def baixar_imagem_anexo(self, url: str) -> tuple[bytes, str] | None:
        """Retorna os bytes e MIME type registrados para `url` ou `None`."""
        return self._anexos.get(url)
