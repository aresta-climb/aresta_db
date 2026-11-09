# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import keyring.backend

from editor.core.gerenciador_sessao import SessaoUsuario


class CofreChaveiroFake(keyring.backend.KeyringBackend):
    """
    Backend determinístico em memória para o módulo `keyring` (test-only).
    Isola completamente os testes do cofre real do sistema operacional e permite
    simular falhas determinísticas de leitura, escrita e remoção.
    """

    priority = 10

    def __init__(
        self,
        registros_iniciais: dict[tuple[str, str], str] | None = None,
        erro_leitura: Exception | None = None,
        erro_escrita: Exception | None = None,
        erro_delecao: Exception | None = None,
    ) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._registros: dict[tuple[str, str], str] = (
            dict(registros_iniciais) if registros_iniciais else {}
        )
        self.erro_leitura: Exception | None = erro_leitura
        self.erro_escrita: Exception | None = erro_escrita
        self.erro_delecao: Exception | None = erro_delecao

    def get_password(self, service: str, username: str) -> str | None:
        if self.erro_leitura is not None:
            raise self.erro_leitura
        return self._registros.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        if self.erro_escrita is not None:
            raise self.erro_escrita
        self._registros[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if self.erro_delecao is not None:
            raise self.erro_delecao
        self._registros.pop((service, username), None)

    def obter_registros(self) -> dict[tuple[str, str], str]:
        """Retorna uma cópia dos registros armazenados no cofre em memória."""
        return dict(self._registros)

    def limpar(self) -> None:
        """Remove todos os registros armazenados no cofre em memória."""
        self._registros.clear()


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
