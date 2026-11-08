# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Callable
from pathlib import Path
from typing import Any

from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.servico_submissao import (
    ErroSubmissao,
    ResultadoSincronizacao,
    ResultadoSubmissao,
    ServicoSubmissao,
    StatusSincronizacao,
)


class ServicoSubmissaoFake(ServicoSubmissao):
    """
    Dublê determinístico em memória/disco temporário para ServicoSubmissao (test-only).
    Utiliza o cálculo real de diff de arquivos sobre caminho_repo_base em tmp_path,
    mas simula o push Git Proxy, a abertura de PR e a sincronização remota sem rede.
    """

    def __init__(self, caminho_repo_base: Path) -> None:
        super().__init__(caminho_repo_base=caminho_repo_base)
        self._contador_prs: int = 0
        self._falha_pendente: str | None = None
        self.proximo_status_sincronizacao: StatusSincronizacao = StatusSincronizacao.ATUALIZADO
        self.proximos_arquivos_conflito: list[str] = []
        self.submissoes_registradas: list[dict[str, Any]] = []
        self.conflitos_resolvidos: list[tuple[str, str, bool]] = []

    def configurar_falha_proxima_chamada(self, mensagem: str) -> None:
        """Agenda uma exceção ErroSubmissao para a próxima operação de submissão ou sincronização."""
        self._falha_pendente = mensagem

    def configurar_proxima_sincronizacao(
        self,
        status: StatusSincronizacao,
        arquivos_conflito: list[str] | None = None,
    ) -> None:
        """Define o resultado determinístico que será retornado em sincronizar_pr_remota."""
        self.proximo_status_sincronizacao = status
        self.proximos_arquivos_conflito = list(arquivos_conflito or [])

    def _consumir_falha_se_houver(self) -> None:
        if self._falha_pendente is not None:
            msg = self._falha_pendente
            self._falha_pendente = None
            raise ErroSubmissao(msg)

    def submeter_sugestao(
        self,
        caminho_database_croqui: Path,
        id_croqui: str,
        titulo: str,
        descricao: str,
        sessao: SessaoUsuario,
        branch_existente: str | None = None,
        callback_progresso: Callable[[int, str], None] | None = None,
    ) -> ResultadoSubmissao:
        """Executa submissão local determinística verificando diff real no disco."""
        self._consumir_falha_se_houver()
        if callback_progresso is not None:
            callback_progresso(50, "Verificando arquivos modificados...")

        modificados = self.obter_arquivos_modificados(caminho_database_croqui, id_croqui)
        if not modificados:
            return ResultadoSubmissao(
                sucesso=True,
                nome_branch=branch_existente or f"edicao-{id_croqui}-0000",
                mensagem="Nenhuma alteração foi detectada no croqui.",
                sem_alteracoes=True,
            )

        self.sincronizar_arquivos_croqui(
            caminho_database_croqui, self.caminho_repo_base, id_croqui
        )
        self._contador_prs += 1
        nome_branch = branch_existente or f"edicao-{id_croqui}-{self._contador_prs:04d}"
        self.submissoes_registradas.append(
            {
                "id_croqui": id_croqui,
                "titulo": titulo,
                "descricao": descricao,
                "autor": sessao.nome_completo,
                "branch": nome_branch,
                "arquivos": modificados,
            }
        )
        if callback_progresso is not None:
            callback_progresso(100, "Proposta de mudança enviada com sucesso!")

        return ResultadoSubmissao(
            sucesso=True,
            pr_number=self._contador_prs,
            pr_url=f"http://127.0.0.1/pull/{self._contador_prs}",
            nome_branch=nome_branch,
            mensagem="Proposta de mudança publicada com sucesso!",
        )

    def sincronizar_pr_remota(
        self,
        id_croqui: str,
        nome_branch: str,
        caminho_database_croqui: Path,
        nome_remote: str = "origin",
        sessao: SessaoUsuario | None = None,
        callbacks: Any = None,
    ) -> ResultadoSincronizacao:
        """Retorna o resultado determinístico configurado para sincronização de PR."""
        _ = (id_croqui, nome_branch, caminho_database_croqui, nome_remote, sessao, callbacks)
        self._consumir_falha_se_houver()
        status = self.proximo_status_sincronizacao
        conflitos = list(self.proximos_arquivos_conflito)
        return ResultadoSincronizacao(
            status=status,
            mensagem=f"Sincronização simulada ({status.value}).",
            arquivos_conflito=conflitos,
            commit_merge="sha_sync_fake",
        )

    def resolver_conflito_pr(
        self,
        id_croqui: str,
        nome_branch: str,
        caminho_database_croqui: Path,
        manter_local: bool,
        nome_remote: str = "origin",
        sessao: SessaoUsuario | None = None,
    ) -> ResultadoSincronizacao:
        """Registra a decisão de conflito em memória e retorna status MESCLADO."""
        _ = (caminho_database_croqui, nome_remote, sessao)
        self.conflitos_resolvidos.append((id_croqui, nome_branch, manter_local))
        return ResultadoSincronizacao(
            status=StatusSincronizacao.MESCLADO,
            mensagem="Conflito resolvido com sucesso.",
            commit_merge="sha_conflito_resolvido_fake",
        )
