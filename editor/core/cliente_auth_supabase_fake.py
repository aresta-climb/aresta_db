# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any

from editor.core.cliente_auth_supabase import ErroAutenticacaoSupabase


class ClienteAuthSupabaseFake:
    """
    Dublê determinístico em memória para ClienteAuthSupabase (test-only).
    Simula OTP, verificação de token, atualização de perfil e renovação de sessão sem rede.
    """

    def __init__(
        self,
        codigo_otp_padrao: str = "123456",
        nome_autor_inicial: str = "",
    ) -> None:
        self.codigo_otp_padrao: str = codigo_otp_padrao
        self.nome_autor_inicial: str = nome_autor_inicial
        self.codigos_otp_por_email: dict[str, str] = {}
        self.usuarios_por_jwt: dict[str, dict[str, Any]] = {}
        self.jwt_por_refresh: dict[str, str] = {}
        self._contador_tokens: int = 0
        self._falha_pendente: tuple[str, int] | None = None

    def configurar_falha_proxima_chamada(
        self, mensagem: str = "Falha simulada no Supabase", codigo_status: int = 500
    ) -> None:
        """Agenda uma falha determinística para a próxima chamada de API."""
        self._falha_pendente = (mensagem, codigo_status)

    def _consumir_falha_se_houver(self) -> None:
        if self._falha_pendente is not None:
            mensagem, codigo = self._falha_pendente
            self._falha_pendente = None
            raise ErroAutenticacaoSupabase(mensagem, codigo_status=codigo)

    def obter_url_autorizacao_github(self, url_redirecionamento: str) -> str:
        """Retorna uma URL local simulada para autorização OAuth GitHub."""
        return (
            "http://127.0.0.1/auth/v1/authorize?"
            f"provider=github&scopes=read:user,user:email,public_repo&redirect_to={url_redirecionamento}"
        )

    def solicitar_codigo_otp(self, email: str) -> bool:
        """Registra o envio de um código OTP determinístico para o e-mail."""
        self._consumir_falha_se_houver()
        email_limpo = email.strip()
        self.codigos_otp_por_email[email_limpo] = self.codigo_otp_padrao
        return True

    def verificar_codigo_otp(self, email: str, token: str) -> dict[str, Any]:
        """Valida o código OTP de 6 dígitos e gera sessão determinística em memória."""
        self._consumir_falha_se_houver()
        email_limpo = email.strip()
        token_limpo = token.strip()
        esperado = self.codigos_otp_por_email.get(email_limpo, self.codigo_otp_padrao)
        if token_limpo != esperado:
            raise ErroAutenticacaoSupabase("token has expired or is invalid", codigo_status=400)

        self._contador_tokens += 1
        jwt = f"jwt_fake_{self._contador_tokens}"
        refresh = f"refresh_fake_{self._contador_tokens}"
        usuario = {
            "email": email_limpo,
            "user_metadata": {"nome_completo": self.nome_autor_inicial},
        }
        self.usuarios_por_jwt[jwt] = usuario
        self.jwt_por_refresh[refresh] = jwt
        return {
            "access_token": jwt,
            "refresh_token": refresh,
            "user": usuario,
        }

    def atualizar_nome_autor(self, jwt: str, nome_completo: str) -> bool:
        """Atualiza o nome completo do autor nos metadados em memória."""
        self._consumir_falha_se_houver()
        usuario = self.usuarios_por_jwt.get(jwt)
        if usuario is None:
            raise ErroAutenticacaoSupabase("invalid login credentials", codigo_status=401)
        usuario.setdefault("user_metadata", {})["nome_completo"] = nome_completo.strip()
        return True

    def renovar_sessao(self, token_atualizacao: str) -> dict[str, Any]:
        """Emite novo par de tokens para um refresh_token válido."""
        self._consumir_falha_se_houver()
        jwt_antigo = self.jwt_por_refresh.get(token_atualizacao.strip())
        if jwt_antigo is None or jwt_antigo not in self.usuarios_por_jwt:
            raise ErroAutenticacaoSupabase("token has expired or is invalid", codigo_status=400)

        usuario = self.usuarios_por_jwt[jwt_antigo]
        self._contador_tokens += 1
        novo_jwt = f"jwt_fake_{self._contador_tokens}"
        novo_refresh = f"refresh_fake_{self._contador_tokens}"
        self.usuarios_por_jwt[novo_jwt] = usuario
        self.jwt_por_refresh[novo_refresh] = novo_jwt
        return {
            "access_token": novo_jwt,
            "refresh_token": novo_refresh,
            "user": usuario,
        }

    def obter_usuario_atual(self, jwt: str) -> dict[str, Any]:
        """Retorna os dados do usuário associado ao JWT em memória."""
        self._consumir_falha_se_houver()
        usuario = self.usuarios_por_jwt.get(jwt)
        if usuario is None:
            raise ErroAutenticacaoSupabase("invalid login credentials", codigo_status=401)
        return usuario
