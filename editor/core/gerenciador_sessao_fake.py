# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from editor.core.gerenciador_sessao import SessaoUsuario


class GerenciadorSessaoFake:
    """
    Dublê determinístico em memória para GerenciadorSessao (test-only).
    Não acessa o keyring nem o cofre de credenciais do sistema operacional.
    """

    def __init__(
        self,
        sessao_inicial: SessaoUsuario | None = None,
        cofre_ativo: bool = True,
    ) -> None:
        self._sessao: SessaoUsuario | None = sessao_inicial
        self._cofre_ativo: bool = cofre_ativo

    def inicializar_cofre(self) -> bool:
        """Retorna a disponibilidade configurada para o cofre em memória."""
        return self._cofre_ativo

    def cofre_disponivel(self) -> bool:
        """Retorna se o cofre simulado está disponível."""
        return self._cofre_ativo

    def salvar_sessao(self, sessao: SessaoUsuario) -> None:
        """Armazena uma cópia da sessão do usuário em memória."""
        self._sessao = SessaoUsuario.de_dicionario(sessao.para_dicionario())

    def obter_sessao(self) -> SessaoUsuario | None:
        """Recupera a sessão atualmente armazenada em memória."""
        if self._sessao is None:
            return None
        return SessaoUsuario.de_dicionario(self._sessao.para_dicionario())

    def carregar_sessao(self) -> SessaoUsuario | None:
        """Alias de compatibilidade para obter_sessao."""
        return self.obter_sessao()

    def recuperar_token(self, auto_renovar: bool = True) -> str | None:
        """Recupera o token JWT da sessão em memória."""
        _ = auto_renovar
        if self._sessao is None or not self._sessao.jwt_supabase:
            return None
        return self._sessao.jwt_supabase

    def limpar_sessao(self) -> None:
        """Remove a sessão da memória."""
        self._sessao = None
