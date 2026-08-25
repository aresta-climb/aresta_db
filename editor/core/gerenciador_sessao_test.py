# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from unittest.mock import patch, MagicMock

from editor.core.gerenciador_sessao import SessaoUsuario, GerenciadorSessao


class TesteSessaoUsuario:
    """Testes para o modelo de dados da sessão unificada."""

    def teste_criacao_sessao_e_propriedades(self):
        sessao = SessaoUsuario(
            email="autor@arestaclimb.com",
            nome_completo="Carlos Escalador",
            jwt_supabase="jwt.token.123",
            token_atualizacao="refresh.token.456",
            token_github=None,
        )

        assert sessao.email == "autor@arestaclimb.com"
        assert sessao.nome_completo == "Carlos Escalador"
        assert sessao.jwt_supabase == "jwt.token.123"
        assert sessao.token_atualizacao == "refresh.token.456"
        assert sessao.token_github is None
        assert sessao.eh_mantenedor is False

    def teste_propriedade_eh_mantenedor_com_token_github(self):
        sessao = SessaoUsuario(
            email="mantenedor@arestaclimb.com",
            nome_completo="Ana Mantenedora",
            jwt_supabase="jwt.token.123",
            token_atualizacao="refresh.token.456",
            token_github="gho_token_123",
        )

        assert sessao.eh_mantenedor is True

    def teste_serializacao_para_dicionario_e_reconstrucao(self):
        sessao_original = SessaoUsuario(
            email="autor@arestaclimb.com",
            nome_completo="Carlos Escalador",
            jwt_supabase="jwt.token.123",
            token_atualizacao="refresh.token.456",
            token_github="gho_teste",
        )

        dicionario = sessao_original.para_dicionario()
        assert isinstance(dicionario, dict)
        assert dicionario["email"] == "autor@arestaclimb.com"

        sessao_reconstruida = SessaoUsuario.de_dicionario(dicionario)
        assert sessao_reconstruida.email == sessao_original.email
        assert sessao_reconstruida.nome_completo == sessao_original.nome_completo
        assert sessao_reconstruida.jwt_supabase == sessao_original.jwt_supabase
        assert sessao_reconstruida.token_atualizacao == sessao_original.token_atualizacao
        assert sessao_reconstruida.token_github == sessao_original.token_github


class TesteGerenciadorSessao:
    """Testes para persistência de sessão com AES-256-GCM e Envelope Encryption."""

    def teste_salvar_obter_e_limpar_sessao_em_memoria(self):
        gerenciador = GerenciadorSessao(usar_memoria=True)
        assert gerenciador.obter_sessao() is None

        sessao = SessaoUsuario(
            email="teste@arestaclimb.com",
            nome_completo="Nome Teste",
            jwt_supabase="jwt.teste",
            token_atualizacao="refresh.teste",
        )

        gerenciador.salvar_sessao(sessao)
        sessao_recuperada = gerenciador.obter_sessao()
        assert sessao_recuperada is not None
        assert sessao_recuperada.email == "teste@arestaclimb.com"

        gerenciador.limpar_sessao()
        assert gerenciador.obter_sessao() is None

    def teste_salvar_e_obter_sessao_aes256gcm_sucesso(self, tmp_path):
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        sessao = SessaoUsuario(
            email="escalador@arestaclimb.com",
            nome_completo="João da Silva",
            jwt_supabase="jwt.supabase.payload",
            token_atualizacao="refresh.token.123",
            token_github="gho_github_token",
        )

        cofre_falso = {}

        def mock_set_password(service, user, password):
            cofre_falso[(service, user)] = password

        def mock_get_password(service, user):
            return cofre_falso.get((service, user))

        def mock_delete_password(service, user):
            cofre_falso.pop((service, user), None)

        with patch("keyring.set_password", side_effect=mock_set_password):
            with patch("keyring.get_password", side_effect=mock_get_password):
                with patch("keyring.delete_password", side_effect=mock_delete_password):
                    gerenciador.salvar_sessao(sessao)

                    # Verifica que o arquivo foi gravado criptografado no disco
                    assert caminho_arquivo.exists()
                    dados_gravados = caminho_arquivo.read_bytes()
                    # Não deve conter texto plano
                    assert b"escalador@arestaclimb.com" not in dados_gravados
                    assert "João da Silva".encode("utf-8") not in dados_gravados

                    # Verifica que a chave de 256 bits foi armazenada no keyring
                    assert ("editor_aresta", "chave_criptografia_sessao") in cofre_falso
                    chave_b64 = cofre_falso[("editor_aresta", "chave_criptografia_sessao")]
                    assert len(chave_b64) == 44  # 32 bytes em Base64

                    # Recupera e decifra com sucesso
                    sessao_recuperada = gerenciador.obter_sessao()
                    assert sessao_recuperada is not None
                    assert sessao_recuperada.email == "escalador@arestaclimb.com"
                    assert sessao_recuperada.nome_completo == "João da Silva"
                    assert sessao_recuperada.jwt_supabase == "jwt.supabase.payload"
                    assert sessao_recuperada.token_github == "gho_github_token"

                    # Limpa a sessão
                    gerenciador.limpar_sessao()
                    assert not caminho_arquivo.exists()
                    assert ("editor_aresta", "chave_criptografia_sessao") not in cofre_falso
                    assert gerenciador.obter_sessao() is None

    def teste_sessao_com_payload_longo_jwt_e_tokens(self, tmp_path):
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        jwt_gigante = "jwt." + ("a" * 2048)
        sessao = SessaoUsuario(
            email="longo@arestaclimb.com",
            nome_completo="Usuario Token Longo",
            jwt_supabase=jwt_gigante,
            token_atualizacao="refresh_token_gigante_" + ("b" * 256),
            token_github="gho_token_longo_" + ("c" * 256),
        )

        cofre_falso = {}

        with patch("keyring.set_password", side_effect=lambda s, u, p: cofre_falso.update({(s, u): p})):
            with patch("keyring.get_password", side_effect=lambda s, u: cofre_falso.get((s, u))):
                gerenciador.salvar_sessao(sessao)
                sessao_recuperada = gerenciador.obter_sessao()

                assert sessao_recuperada is not None
                assert sessao_recuperada.jwt_supabase == jwt_gigante
                assert sessao_recuperada.token_github == sessao.token_github

    def teste_arquivo_adulterado_falha_na_autenticacao_gcm_e_limpa_sessao(self, tmp_path):
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        sessao = SessaoUsuario(
            email="vitima@arestaclimb.com",
            nome_completo="Usuario Alvo",
            jwt_supabase="jwt.valido",
            token_atualizacao="refresh.valido",
        )

        cofre_falso = {}

        with patch("keyring.set_password", side_effect=lambda s, u, p: cofre_falso.update({(s, u): p})):
            with patch("keyring.get_password", side_effect=lambda s, u: cofre_falso.get((s, u))):
                with patch("keyring.delete_password", side_effect=lambda s, u: cofre_falso.pop((s, u), None)):
                    gerenciador.salvar_sessao(sessao)
                    assert caminho_arquivo.exists()

                    # Adultera 1 byte do arquivo cifrado (ataque de integridade)
                    dados = bytearray(caminho_arquivo.read_bytes())
                    dados[-1] ^= 0xFF
                    caminho_arquivo.write_bytes(bytes(dados))

                    # AES-GCM deve rejeitar a adulteração, limpar a sessão e retornar None
                    sessao_recuperada = gerenciador.obter_sessao()
                    assert sessao_recuperada is None
                    assert not caminho_arquivo.exists()

    def teste_chave_perdida_no_keyring_limpa_arquivo_e_retorna_none(self, tmp_path):
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        sessao = SessaoUsuario(
            email="teste@arestaclimb.com",
            nome_completo="Usuario Teste",
            jwt_supabase="jwt.valido",
            token_atualizacao="refresh.valido",
        )

        cofre_falso = {}

        with patch("keyring.set_password", side_effect=lambda s, u, p: cofre_falso.update({(s, u): p})):
            with patch("keyring.get_password", side_effect=lambda s, u: cofre_falso.get((s, u))):
                with patch("keyring.delete_password", side_effect=lambda s, u: cofre_falso.pop((s, u), None)):
                    gerenciador.salvar_sessao(sessao)
                    assert caminho_arquivo.exists()

                    # Simula perda da chave no keyring
                    cofre_falso.clear()

                    sessao_recuperada = gerenciador.obter_sessao()
                    assert sessao_recuperada is None
                    assert not caminho_arquivo.exists()
