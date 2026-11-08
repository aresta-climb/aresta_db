# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from editor.core.cliente_auth_supabase import ErroAutenticacaoSupabase
from editor.core.cliente_auth_supabase_fake import ClienteAuthSupabaseFake


def test_fluxo_completo_otp_perfil_e_renovacao_em_memoria() -> None:
    fake = ClienteAuthSupabaseFake(codigo_otp_padrao="654321")

    url_oauth = fake.obter_url_autorizacao_github("http://127.0.0.1:54321/callback")
    assert "provider=github" in url_oauth
    assert "http://127.0.0.1:54321/callback" in url_oauth

    assert fake.solicitar_codigo_otp("escalador@arestaclimb.com") is True

    dados_sessao = fake.verificar_codigo_otp("escalador@arestaclimb.com", "654321")
    jwt = dados_sessao["access_token"]
    refresh = dados_sessao["refresh_token"]
    assert dados_sessao["user"]["email"] == "escalador@arestaclimb.com"

    assert fake.atualizar_nome_autor(jwt, "Escalador Teste") is True
    usuario = fake.obter_usuario_atual(jwt)
    assert usuario["user_metadata"]["nome_completo"] == "Escalador Teste"

    renovado = fake.renovar_sessao(refresh)
    novo_jwt = renovado["access_token"]
    assert novo_jwt != jwt
    usuario_apos_renovar = fake.obter_usuario_atual(novo_jwt)
    assert usuario_apos_renovar["email"] == "escalador@arestaclimb.com"


def test_rejeita_otp_invalido_jwt_desconhecido_e_refresh_invalido() -> None:
    fake = ClienteAuthSupabaseFake(codigo_otp_padrao="123456")
    fake.solicitar_codigo_otp("autor@arestaclimb.com")

    with pytest.raises(ErroAutenticacaoSupabase) as exc_otp:
        fake.verificar_codigo_otp("autor@arestaclimb.com", "000000")
    assert exc_otp.value.codigo_status == 400

    with pytest.raises(ErroAutenticacaoSupabase) as exc_usr:
        fake.obter_usuario_atual("jwt_inexistente")
    assert exc_usr.value.codigo_status == 401

    with pytest.raises(ErroAutenticacaoSupabase) as exc_nome:
        fake.atualizar_nome_autor("jwt_inexistente", "Nome")
    assert exc_nome.value.codigo_status == 401

    with pytest.raises(ErroAutenticacaoSupabase) as exc_ref:
        fake.renovar_sessao("refresh_inexistente")
    assert exc_ref.value.codigo_status == 400


def test_simulacao_deterministica_de_falha_proxima_chamada() -> None:
    fake = ClienteAuthSupabaseFake()
    fake.configurar_falha_proxima_chamada("token has expired or is invalid", codigo_status=403)

    with pytest.raises(ErroAutenticacaoSupabase) as exc:
        fake.solicitar_codigo_otp("autor@arestaclimb.com")
    assert exc.value.codigo_status == 403
    assert "expirou ou é inválido" in str(exc.value)

    # A chamada seguinte volta a funcionar normalmente
    assert fake.solicitar_codigo_otp("autor@arestaclimb.com") is True
