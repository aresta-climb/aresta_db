# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import responses
from editor.core.cliente_auth_supabase import ClienteAuthSupabase, ErroAutenticacaoSupabase


@pytest.fixture
def cliente():
    return ClienteAuthSupabase(
        url_supabase="https://teste.supabase.co", chave_publica="chave-publica-teste"
    )


class TesteClienteAuthSupabase:
    """Testes unitários para o cliente REST do Supabase Auth."""

    @responses.activate
    def teste_solicitar_codigo_otp_sucesso(self, cliente):
        responses.add(
            responses.POST,
            "https://teste.supabase.co/auth/v1/otp",
            json={"message": "OTP enviado com sucesso"},
            status=200,
        )

        resultado = cliente.solicitar_codigo_otp("escalador@arestaclimb.com")
        assert resultado is True

        chamada = responses.calls[0]
        assert "apikey" in chamada.request.headers
        assert chamada.request.headers["apikey"] == "chave-publica-teste"
        assert chamada.request.headers["Authorization"] == "Bearer chave-publica-teste"
        assert b'"email": "escalador@arestaclimb.com"' in chamada.request.body
        assert b'"create_user": true' in chamada.request.body

    def teste_instanciacao_padrao_possui_url_e_chave_publica_definidas(self):
        cliente_padrao = ClienteAuthSupabase()
        assert "supabase.co" in cliente_padrao.url_supabase
        assert len(cliente_padrao.chave_publica) > 20

    @responses.activate
    def teste_solicitar_codigo_otp_falha_lanca_excecao(self, cliente):
        responses.add(
            responses.POST,
            "https://teste.supabase.co/auth/v1/otp",
            json={"msg": "Email rate limit exceeded"},
            status=429,
        )

        with pytest.raises(ErroAutenticacaoSupabase) as info_erro:
            cliente.solicitar_codigo_otp("escalador@arestaclimb.com")

        assert "Limite de envio de e-mails" in str(info_erro.value)

    @responses.activate
    def teste_verificar_codigo_otp_sucesso(self, cliente):
        responses.add(
            responses.POST,
            "https://teste.supabase.co/auth/v1/verify",
            json={
                "access_token": "jwt-token-123",
                "refresh_token": "refresh-token-456",
                "user": {
                    "id": "uuid-123",
                    "email": "escalador@arestaclimb.com",
                    "user_metadata": {"nome_completo": "Renato Utsch"},
                },
            },
            status=200,
        )

        resultado = cliente.verificar_codigo_otp("escalador@arestaclimb.com", "123456")
        assert resultado["access_token"] == "jwt-token-123"
        assert resultado["refresh_token"] == "refresh-token-456"
        assert resultado["user"]["email"] == "escalador@arestaclimb.com"

    @responses.activate
    def teste_verificar_codigo_otp_invalido_lanca_excecao(self, cliente):
        responses.add(
            responses.POST,
            "https://teste.supabase.co/auth/v1/verify",
            json={"msg": "Token has expired or is invalid"},
            status=400,
        )

        with pytest.raises(ErroAutenticacaoSupabase) as info_erro:
            cliente.verificar_codigo_otp("escalador@arestaclimb.com", "000000")

        assert "código de acesso expirou ou é inválido" in str(info_erro.value)

    @responses.activate
    def teste_atualizar_nome_autor_sucesso(self, cliente):
        responses.add(
            responses.PUT,
            "https://teste.supabase.co/auth/v1/user",
            json={
                "id": "uuid-123",
                "user_metadata": {"nome_completo": "Novo Nome"},
            },
            status=200,
        )

        resultado = cliente.atualizar_nome_autor("jwt-token-123", "Novo Nome")
        assert resultado is True

        chamada = responses.calls[0]
        assert chamada.request.headers["Authorization"] == "Bearer jwt-token-123"
        assert b'"nome_completo": "Novo Nome"' in chamada.request.body

    @responses.activate
    def teste_atualizar_nome_autor_falha_lanca_excecao(self, cliente):
        responses.add(
            responses.PUT,
            "https://teste.supabase.co/auth/v1/user",
            json={"msg": "JWT expired"},
            status=401,
        )

        with pytest.raises(ErroAutenticacaoSupabase):
            cliente.atualizar_nome_autor("jwt-expirado", "Novo Nome")

    @responses.activate
    def teste_renovar_sessao_sucesso(self, cliente):
        responses.add(
            responses.POST,
            "https://teste.supabase.co/auth/v1/token?grant_type=refresh_token",
            json={
                "access_token": "novo-jwt",
                "refresh_token": "novo-refresh",
            },
            status=200,
        )

        resultado = cliente.renovar_sessao("refresh-antigo")
        assert resultado["access_token"] == "novo-jwt"
        assert resultado["refresh_token"] == "novo-refresh"

    @responses.activate
    def teste_obter_usuario_atual_sucesso(self, cliente):
        responses.add(
            responses.GET,
            "https://teste.supabase.co/auth/v1/user",
            json={
                "id": "uuid-123",
                "email": "autor@arestaclimb.com",
                "user_metadata": {"full_name": "Nome GitHub"},
            },
            status=200,
        )

        usuario = cliente.obter_usuario_atual("jwt-valido")
        assert usuario["email"] == "autor@arestaclimb.com"
        assert usuario["user_metadata"]["full_name"] == "Nome GitHub"

    @pytest.mark.parametrize(
        "msg_original,msg_esperada",
        [
            (
                "For security purposes, you can only request this after 21 seconds.",
                "Por motivos de segurança, você só pode solicitar um novo código após 21 segundos.",
            ),
            (
                "For security purposes, you can only request this after 1 second.",
                "Por motivos de segurança, você só pode solicitar um novo código após 1 segundo.",
            ),
            (
                "For security purposes, you can only request this once every 60 seconds.",
                "Por motivos de segurança, você só pode solicitar um novo código a cada 60 segundos.",
            ),
            (
                "Token has expired or is invalid",
                "O código de acesso expirou ou é inválido.",
            ),
            (
                "Email rate limit exceeded",
                "Limite de envio de e-mails atingido. Tente novamente mais tarde.",
            ),
            (
                "Invalid login credentials",
                "Credenciais de login inválidas.",
            ),
            (
                "Unsupported provider: provider is not enabled",
                "Provedor de autenticação não está habilitado no servidor.",
            ),
            (
                "Error getting user profile from external provider",
                "Não foi possível obter o perfil e e-mail da sua conta externa (GitHub).",
            ),
        ],
    )
    def teste_traduzir_mensagem_erro_supabase(self, msg_original, msg_esperada):
        from editor.core.cliente_auth_supabase import traduzir_mensagem_erro_supabase

        assert traduzir_mensagem_erro_supabase(msg_original) == msg_esperada

    def teste_cliente_com_url_vazia_usa_fallback_padrao(self):
        cliente = ClienteAuthSupabase(url_supabase="")
        assert cliente.url_supabase == "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"

    def teste_cliente_com_url_sem_esquema_ou_espacos_usa_fallback_padrao(self):
        cliente1 = ClienteAuthSupabase(url_supabase="   ")
        assert cliente1.url_supabase == "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"
        cliente2 = ClienteAuthSupabase(url_supabase="invalido_sem_http")
        assert cliente2.url_supabase == "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"

    def teste_cliente_com_env_vazias_usa_fallback_padrao(self, monkeypatch):
        monkeypatch.setenv("ARESTA_SUPABASE_URL", "")
        monkeypatch.setenv("ARESTA_SUPABASE_PUBLISHABLE_KEY", "")
        cliente = ClienteAuthSupabase()
        assert cliente.url_supabase == "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"
        assert "sb_publishable_" in cliente.chave_publica

    @responses.activate
    def teste_solicitar_codigo_otp_com_url_vazia_usa_url_absoluta_valida(self):
        responses.add(
            responses.POST,
            "https://yzkhiaoqtxvvcyyuwmqg.supabase.co/auth/v1/otp",
            json={"message": "ok"},
            status=200,
        )
        cliente = ClienteAuthSupabase(url_supabase="")
        resultado = cliente.solicitar_codigo_otp("renatoutsch@gmail.com")
        assert resultado is True
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == "https://yzkhiaoqtxvvcyyuwmqg.supabase.co/auth/v1/otp"

    def teste_obter_url_autorizacao_github(self, cliente):
        url = cliente.obter_url_autorizacao_github("http://localhost:55887/callback")
        assert url == (
            "https://teste.supabase.co/auth/v1/authorize?"
            "provider=github&scopes=read:user,user:email,public_repo&redirect_to=http://localhost:55887/callback"
        )
