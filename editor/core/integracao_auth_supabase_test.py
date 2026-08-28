# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import responses
from unittest.mock import patch

from editor.core.cliente_auth_supabase import ClienteAuthSupabase
from editor.core.gerenciador_sessao import GerenciadorSessao, SessaoUsuario
from editor.core.servidor_oauth_callback import ServidorCallbackOAuth


@pytest.fixture
def url_supabase():
    return "https://teste-aresta.supabase.co"


@pytest.fixture
def chave_publica():
    return "chave-publica-teste"


@pytest.fixture
def cliente_auth(url_supabase, chave_publica):
    return ClienteAuthSupabase(url_supabase=url_supabase, chave_publica=chave_publica)


@pytest.fixture
def gerenciador_sessao():
    return GerenciadorSessao(usar_memoria=True)


class TesteIntegracaoAuthSupabase:
    """
    Testes de integração de fronteira (Princípio V) validando o ciclo completo
    de autenticação e persistência de sessão.
    """

    @responses.activate
    def teste_fluxo_integrado_email_otp_com_definicao_de_nome(
        self, cliente_auth, gerenciador_sessao, url_supabase
    ):
        email_teste = "escalador@arestaclimb.com"
        codigo_otp = "123456"
        jwt_mock = "jwt.supabase.teste"
        refresh_mock = "refresh.token.teste"

        # 1. Mock do envio de OTP
        responses.add(
            responses.POST,
            f"{url_supabase}/auth/v1/otp",
            json={"message": "OTP enviado"},
            status=200,
        )

        sucesso_envio = cliente_auth.solicitar_codigo_otp(email_teste)
        assert sucesso_envio is True

        # 2. Mock da verificação do OTP (sem nome cadastrado inicialmente)
        responses.add(
            responses.POST,
            f"{url_supabase}/auth/v1/verify",
            json={
                "access_token": jwt_mock,
                "refresh_token": refresh_mock,
                "user": {
                    "id": "usuario-uuid-1",
                    "email": email_teste,
                    "user_metadata": {},
                },
            },
            status=200,
        )

        dados_sessao = cliente_auth.verificar_codigo_otp(email_teste, codigo_otp)
        assert dados_sessao["access_token"] == jwt_mock
        assert dados_sessao["user"]["email"] == email_teste
        assert "nome_completo" not in dados_sessao["user"].get("user_metadata", {})

        # 3. Mock da atualização do nome do autor
        nome_completo_autor = "Renato Utsch"
        responses.add(
            responses.PUT,
            f"{url_supabase}/auth/v1/user",
            json={
                "id": "usuario-uuid-1",
                "email": email_teste,
                "user_metadata": {"nome_completo": nome_completo_autor},
            },
            status=200,
        )

        sucesso_nome = cliente_auth.atualizar_nome_autor(
            jwt=jwt_mock, nome_completo=nome_completo_autor
        )
        assert sucesso_nome is True

        # 4. Persistência na Sessão Unificada
        sessao = SessaoUsuario(
            email=email_teste,
            nome_completo=nome_completo_autor,
            jwt_supabase=jwt_mock,
            token_atualizacao=refresh_mock,
            token_github=None,
        )
        gerenciador_sessao.salvar_sessao(sessao)

        sessao_recuperada = gerenciador_sessao.obter_sessao()
        assert sessao_recuperada is not None
        assert sessao_recuperada.email == email_teste
        assert sessao_recuperada.nome_completo == nome_completo_autor
        assert sessao_recuperada.jwt_supabase == jwt_mock
        assert sessao_recuperada.eh_mantenedor is False

    @responses.activate
    def teste_fluxo_integrado_login_github_com_preenchimento_automatico_nome(
        self, cliente_auth, gerenciador_sessao, url_supabase
    ):
        email_teste = "mantenedor@arestaclimb.com"
        jwt_mock = "jwt.supabase.github"
        refresh_mock = "refresh.github"
        token_git_mock = "gho_token_mantenedor"
        nome_publico_github = "Mantenedor Aresta"

        # 1. Simulação do retorno do callback OAuth do GitHub com metadados
        dados_usuario_github = {
            "id": "usuario-github-uuid",
            "email": email_teste,
            "user_metadata": {
                "full_name": nome_publico_github,
                "user_name": "mantenedor_aresta",
            },
        }

        # Mock da chamada de obter usuário
        responses.add(
            responses.GET,
            f"{url_supabase}/auth/v1/user",
            json=dados_usuario_github,
            status=200,
        )

        usuario_obtido = cliente_auth.obter_usuario_atual(jwt_mock)
        assert usuario_obtido["email"] == email_teste
        assert usuario_obtido["user_metadata"]["full_name"] == nome_publico_github

        # 2. Salvar sessão identificando privilégio de mantenedor
        sessao_git = SessaoUsuario(
            email=email_teste,
            nome_completo=nome_publico_github,
            jwt_supabase=jwt_mock,
            token_atualizacao=refresh_mock,
            token_github=token_git_mock,
        )
        gerenciador_sessao.salvar_sessao(sessao_git)

        sessao_recuperada = gerenciador_sessao.obter_sessao()
        assert sessao_recuperada is not None
        assert sessao_recuperada.eh_mantenedor is True
        assert sessao_recuperada.token_github == token_git_mock

    @responses.activate
    def teste_fluxo_integrado_renovacao_de_sessao_expirada(
        self, cliente_auth, gerenciador_sessao, url_supabase
    ):
        refresh_antigo = "refresh.antigo"
        jwt_novo = "jwt.renovado.novo"
        refresh_novo = "refresh.novo"

        responses.add(
            responses.POST,
            f"{url_supabase}/auth/v1/token?grant_type=refresh_token",
            json={
                "access_token": jwt_novo,
                "refresh_token": refresh_novo,
                "expires_in": 3600,
            },
            status=200,
        )

        novos_dados = cliente_auth.renovar_sessao(refresh_antigo)
        assert novos_dados["access_token"] == jwt_novo
        assert novos_dados["refresh_token"] == refresh_novo
