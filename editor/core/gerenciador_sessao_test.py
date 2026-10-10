# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

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

    def teste_recuperar_token(self, tmp_path):
        gerenciador = GerenciadorSessao(usar_memoria=True)
        assert gerenciador.recuperar_token() is None

        sessao = SessaoUsuario(
            email="teste@arestaclimb.com",
            nome_completo="Usuario Teste",
            jwt_supabase="jwt.supabase.123",
            token_atualizacao="refresh.123",
        )
        gerenciador.salvar_sessao(sessao)
        assert gerenciador.recuperar_token(auto_renovar=False) == "jwt.supabase.123"
        assert gerenciador.carregar_sessao().email == "teste@arestaclimb.com"

    def teste_token_jwt_expirado(self):
        import time
        import base64
        import json
        from editor.core.gerenciador_sessao import token_jwt_expirado

        agora = int(time.time())

        def criar_jwt(exp):
            header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
            payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
            return f"{header}.{payload}.signature"

        jwt_expirado = criar_jwt(agora - 100)
        jwt_valido = criar_jwt(agora + 3600)

        assert token_jwt_expirado(jwt_expirado) is True
        assert token_jwt_expirado(jwt_valido) is False
        assert token_jwt_expirado("invalido") is True

    def teste_recuperar_token_com_auto_renovacao(self):
        import time
        import base64
        import json
        from unittest.mock import patch, MagicMock

        agora = int(time.time())
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload_expirado = base64.urlsafe_b64encode(json.dumps({"exp": agora - 500}).encode()).decode().rstrip("=")
        jwt_expirado = f"{header}.{payload_expirado}.sig"

        gerenciador = GerenciadorSessao(usar_memoria=True)
        sessao = SessaoUsuario(
            email="expirado@arestaclimb.com",
            nome_completo="Usuario Expirado",
            jwt_supabase=jwt_expirado,
            token_atualizacao="refresh.token.valido",
        )
        gerenciador.salvar_sessao(sessao)

        with patch("editor.core.cliente_auth_supabase.ClienteAuthSupabase.renovar_sessao", return_value={
            "access_token": "jwt_novo_renovado_456",
            "refresh_token": "refresh_novo_789",
        }):
            token_obtido = gerenciador.recuperar_token(auto_renovar=True)
            assert token_obtido == "jwt_novo_renovado_456"

            sessao_atualizada = gerenciador.obter_sessao()
            assert sessao_atualizada.jwt_supabase == "jwt_novo_renovado_456"
            assert sessao_atualizada.token_atualizacao == "refresh_novo_789"

    def teste_chave_corrompida_ou_invalida_no_keyring_gera_nova(self, tmp_path):
        """Valida que uma chave corrompida no Keyring força a regeneração segura."""
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        cofre = {("editor_aresta", "chave_criptografia_sessao"): "chave_invalida_curta"}

        with patch("keyring.get_password", side_effect=lambda s, u: cofre.get((s, u))):
            with patch("keyring.set_password", side_effect=lambda s, u, p: cofre.update({(s, u): p})):
                chave = gerenciador._obter_ou_criar_chave_criptografia()
                assert len(chave) == 32
                assert cofre[("editor_aresta", "chave_criptografia_sessao")] != "chave_invalida_curta"

    def teste_keyring_get_password_lanca_excecao_recupera_chave_ou_cria_nova(self, tmp_path):
        """Valida que exceção ao ler do Keyring é tratada gerando nova chave e registrando no Keyring."""
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        with patch("keyring.get_password", side_effect=Exception("Falha D-Bus temporária")):
            with patch("keyring.set_password") as mock_set:
                chave = gerenciador._obter_ou_criar_chave_criptografia()
                assert len(chave) == 32
                mock_set.assert_called_once()

    def teste_obter_sessao_com_excecao_no_keyring_limpa_sessao(self, tmp_path):
        """Valida que erro de leitura do Keyring ao carregar sessão limpa dados locais e retorna None."""
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        caminho_arquivo.write_bytes(b"dados_cifrados_minimos_com_tamanho_suficiente_1234567890")
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        with patch("keyring.get_password", side_effect=Exception("Chaveiro inacessível")):
            assert gerenciador.obter_sessao() is None
            assert not caminho_arquivo.exists()

    def teste_obter_sessao_com_chave_comprimento_invalido_limpa_sessao(self, tmp_path):
        """Valida que chave no Keyring com comprimento inválido limpa a sessão e retorna None."""
        import base64
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        caminho_arquivo.write_bytes(b"dados_cifrados_minimos_com_tamanho_suficiente_1234567890")
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        chave_curta_b64 = base64.b64encode(b"chave_invalida").decode("ascii")
        with patch("keyring.get_password", return_value=chave_curta_b64):
            assert gerenciador.obter_sessao() is None
            assert not caminho_arquivo.exists()

    def teste_sessao_em_memoria_json_invalido_retorna_none(self):
        """Valida que payload corrompido em memória retorna None graciosamente."""
        gerenciador = GerenciadorSessao(usar_memoria=True)
        gerenciador._sessao_memoria = "{json_invalido"
        assert gerenciador.obter_sessao() is None

    def teste_arquivo_menor_que_tamanho_minimo_limpa_sessao(self, tmp_path):
        """Valida que arquivo com menos de 28 bytes limpa a sessão."""
        import base64
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        caminho_arquivo.write_bytes(b"muito_pequeno")
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        chave_falsa_b64 = base64.b64encode(b"0" * 32).decode("ascii")
        with patch("keyring.get_password", return_value=chave_falsa_b64):
            assert gerenciador.obter_sessao() is None
            assert not caminho_arquivo.exists()

    def teste_renovar_sessao_excecao_retorna_jwt_antigo(self):
        """Valida que exceção na renovação não quebra a recuperação do token existente."""
        jwt_expirado = "header.payload.sig"

        gerenciador = GerenciadorSessao(usar_memoria=True)
        sessao = SessaoUsuario(
            email="teste@arestaclimb.com",
            nome_completo="Nome",
            jwt_supabase=jwt_expirado,
            token_atualizacao="refresh.token",
        )
        gerenciador.salvar_sessao(sessao)

        with patch("editor.core.gerenciador_sessao.token_jwt_expirado", return_value=True):
            with patch("editor.core.cliente_auth_supabase.ClienteAuthSupabase.renovar_sessao", side_effect=Exception("Rede indisponível")):
                assert gerenciador.recuperar_token(auto_renovar=True) == jwt_expirado

    def teste_limpar_sessao_trata_excecoes_de_unlink_e_keyring(self, tmp_path):
        """Valida que limpar_sessao trata graciosamente exceções ao deletar chaves e arquivos."""
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        caminho_arquivo.write_bytes(b"dados")

        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        with patch("keyring.delete_password", side_effect=Exception("Keyring erro")):
            with patch.object(Path, "unlink", side_effect=OSError("Arquivo em uso")):
                # Não deve estourar erro
                gerenciador.limpar_sessao()

    def teste_token_jwt_expirado_trata_excecoes_inesperadas(self):
        """Valida que token_jwt_expirado trata qualquer erro de decodificação retornando True."""
        from editor.core.gerenciador_sessao import token_jwt_expirado

        with patch("base64.urlsafe_b64decode", side_effect=ValueError("Decodificação falhou")):
            assert token_jwt_expirado("a.b.c") is True

    def teste_token_jwt_sem_campo_exp_retorna_false(self):
        """Valida que token JWT sem campo exp não é considerado expirado."""
        import base64
        import json
        from editor.core.gerenciador_sessao import token_jwt_expirado

        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "12345"}).encode()).decode().rstrip("=")
        jwt_sem_exp = f"{header}.{payload}.signature"
        assert token_jwt_expirado(jwt_sem_exp) is False

    def teste_obter_ou_criar_chave_criptografia_reutiliza_existente(self, tmp_path):
        """Valida que chave persistida existente no Keyring é reaproveitada na segunda chamada."""
        import base64
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )

        chave_b64 = base64.b64encode(b"1" * 32).decode("ascii")
        with patch("keyring.get_password", return_value=chave_b64):
            with patch("keyring.set_password") as mock_set:
                chave = gerenciador._obter_ou_criar_chave_criptografia()
                assert chave == b"1" * 32
                mock_set.assert_not_called()

    def teste_gerenciador_sessao_init_puro_sem_acesso_a_cofre(self):
        """Valida que instanciar GerenciadorSessao não acessa o cofre de credenciais."""
        with patch("editor.core.gerenciador_sessao.configurar_cofre_credenciais") as mock_conf:
            gerenciador = GerenciadorSessao(usar_memoria=False)
            mock_conf.assert_not_called()
            assert gerenciador._cofre_disponivel is None

    def teste_salvar_sessao_falha_chaveiro_mantem_em_memoria_sem_crash(self, tmp_path):
        """Valida que falha de escrita no chaveiro mantém a sessão em memória sem crashar."""
        caminho_arquivo = tmp_path / ".sessao_auth.enc"
        gerenciador = GerenciadorSessao(
            usar_memoria=False, caminho_arquivo_sessao=caminho_arquivo
        )
        sessao = SessaoUsuario(
            email="resiliente@arestaclimb.com",
            nome_completo="Usuario Resiliente",
            jwt_supabase="jwt.resiliente.123",
            token_atualizacao="refresh.resiliente.123",
            token_github="gho_resiliente",
        )

        with patch.object(gerenciador, "_obter_ou_criar_chave_criptografia", side_effect=Exception("Keyring offline")):
            gerenciador.salvar_sessao(sessao)
            assert gerenciador._sessao_memoria is not None
            assert not caminho_arquivo.exists()

            sessao_recuperada = gerenciador.obter_sessao()
            assert sessao_recuperada is not None
            assert sessao_recuperada.email == "resiliente@arestaclimb.com"

    def teste_inicializar_cofre_sucesso_e_cache_em_cofre_disponivel(self):
        """Valida inicializar_cofre com sucesso e que cofre_disponivel usa o valor em memória."""
        with patch("editor.core.gerenciador_sessao.configurar_cofre_credenciais", return_value=True) as mock_conf:
            gerenciador = GerenciadorSessao(usar_memoria=False)
            assert gerenciador.inicializar_cofre() is True
            assert mock_conf.call_count == 1

            # Chamadas subsequentes a cofre_disponivel não devem redisparar configurar_cofre_credenciais
            assert gerenciador.cofre_disponivel() is True
            assert mock_conf.call_count == 1

    def teste_inicializar_cofre_falha_e_cache_em_cofre_disponivel(self):
        """Valida inicializar_cofre com falha e que cofre_disponivel preserva False em memória."""
        with patch("editor.core.gerenciador_sessao.configurar_cofre_credenciais", return_value=False) as mock_conf:
            gerenciador = GerenciadorSessao(usar_memoria=False)
            assert gerenciador.inicializar_cofre() is False
            assert mock_conf.call_count == 1

            assert gerenciador.cofre_disponivel() is False
            assert mock_conf.call_count == 1

    def teste_inicializar_cofre_quando_usar_memoria(self):
        """Valida que inicializar_cofre retorna True diretamente quando usar_memoria=True."""
        gerenciador = GerenciadorSessao(usar_memoria=True)
        with patch("editor.core.gerenciador_sessao.configurar_cofre_credenciais") as mock_conf:
            assert gerenciador.inicializar_cofre() is True
            assert gerenciador.cofre_disponivel() is True
            mock_conf.assert_not_called()

    def teste_cofre_disponivel_lazy_quando_nao_inicializado_previamente(self):
        """Valida que cofre_disponivel dispara inicializar_cofre se ainda não foi executado."""
        with patch("editor.core.gerenciador_sessao.configurar_cofre_credenciais", return_value=True) as mock_conf:
            gerenciador = GerenciadorSessao(usar_memoria=False)
            assert gerenciador._cofre_disponivel is None
            assert gerenciador.cofre_disponivel() is True
            assert mock_conf.call_count == 1
            assert gerenciador._cofre_disponivel is True

    def teste_token_jwt_expirado_com_padding_necessario(self):
        """Valida que token JWT cujo payload exige padding base64 é processado corretamente."""
        import base64
        import json
        from editor.core.gerenciador_sessao import token_jwt_expirado
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload_raw = json.dumps({"exp": 9999999999}).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_raw).decode().rstrip("=")
        assert len(payload_b64) % 4 != 0
        jwt = f"{header}.{payload_b64}.sig"
        assert token_jwt_expirado(jwt) is False

    def teste_token_jwt_expirado_com_padding_multiplo_de_quatro(self):
        """Valida que token JWT cujo payload já é múltiplo de 4 não executa ajuste de padding."""
        import base64
        import json
        from editor.core.gerenciador_sessao import token_jwt_expirado
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload_raw = json.dumps({"exp": 9999999999, "extra": "x"}).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_raw).decode().rstrip("=")
        assert len(payload_b64) % 4 == 0
        jwt = f"{header}.{payload_b64}.sig"
        assert token_jwt_expirado(jwt) is False

    def teste_obter_ou_criar_chave_com_base64_valido_mas_tamanho_diferente_de_32(self, tmp_path):
        """Valida que chave no Keyring em base64 válido mas com comprimento != 32 gera nova chave."""
        import base64
        gerenciador = GerenciadorSessao(usar_memoria=False, caminho_arquivo_sessao=tmp_path / "k.enc")
        chave_16_b64 = base64.b64encode(b"apenas_16_bytes!").decode("ascii")
        with patch("keyring.get_password", return_value=chave_16_b64):
            with patch("keyring.set_password") as mock_set:
                chave = gerenciador._obter_ou_criar_chave_criptografia()
                assert len(chave) == 32
                mock_set.assert_called_once()

    def teste_recuperar_token_expirado_sem_token_atualizacao(self):
        """Valida que token expirado sem token de atualização retorna o jwt atual sem tentar renovar."""
        jwt_exp = "header.payload.sig"
        gerenciador = GerenciadorSessao(usar_memoria=True)
        sessao = SessaoUsuario(
            email="teste@arestaclimb.com",
            nome_completo="Nome",
            jwt_supabase=jwt_exp,
            token_atualizacao="",
        )
        gerenciador.salvar_sessao(sessao)

        with patch("editor.core.gerenciador_sessao.token_jwt_expirado", return_value=True):
            with patch("editor.core.cliente_auth_supabase.ClienteAuthSupabase.renovar_sessao") as mock_renovar:
                token = gerenciador.recuperar_token(auto_renovar=True)
                assert token == jwt_exp
                mock_renovar.assert_not_called()

    def teste_obter_ou_criar_chave_quando_chave_b64_eh_none(self, tmp_path):
        """Valida que quando get_password retorna None, uma nova chave é gerada."""
        gerenciador = GerenciadorSessao(usar_memoria=False, caminho_arquivo_sessao=tmp_path / "k.enc")
        with patch("keyring.get_password", return_value=None):
            with patch("keyring.set_password") as mock_set:
                chave = gerenciador._obter_ou_criar_chave_criptografia()
                assert len(chave) == 32
                mock_set.assert_called_once()

    def teste_recuperar_token_jwt_valido_nao_expirado(self):
        """Valida que recuperar_token com JWT ainda válido não tenta renovar."""
        import time
        import base64
        import json
        agora = int(time.time())
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps({"exp": agora + 3600}).encode()).decode().rstrip("=")
        jwt_valido = f"{header}.{payload}.sig"

        gerenciador = GerenciadorSessao(usar_memoria=True)
        sessao = SessaoUsuario(
            email="valido@arestaclimb.com",
            nome_completo="Valido",
            jwt_supabase=jwt_valido,
            token_atualizacao="refresh.valido",
        )
        gerenciador.salvar_sessao(sessao)
        assert gerenciador.recuperar_token(auto_renovar=True) == jwt_valido

    def teste_recuperar_token_renovacao_sem_access_token_retorna_jwt_atual(self):
        """Valida que se renovar_sessao não retornar access_token, mantém o jwt atual."""
        jwt_exp = "header.payload.sig"
        gerenciador = GerenciadorSessao(usar_memoria=True)
        sessao = SessaoUsuario(
            email="teste@arestaclimb.com",
            nome_completo="Nome",
            jwt_supabase=jwt_exp,
            token_atualizacao="refresh.valido",
        )
        gerenciador.salvar_sessao(sessao)

        with patch("editor.core.gerenciador_sessao.token_jwt_expirado", return_value=True):
            with patch("editor.core.cliente_auth_supabase.ClienteAuthSupabase.renovar_sessao", return_value={"outra_coisa": 123}):
                assert gerenciador.recuperar_token(auto_renovar=True) == jwt_exp

    def teste_limpar_sessao_quando_arquivo_nao_existe(self, tmp_path):
        """Valida limpar_sessao quando o arquivo físico não existe no disco."""
        caminho_inexistente = tmp_path / "nao_existe.enc"
        gerenciador = GerenciadorSessao(usar_memoria=False, caminho_arquivo_sessao=caminho_inexistente)
        with patch("keyring.delete_password"):
            gerenciador.limpar_sessao()
            assert not caminho_inexistente.exists()




