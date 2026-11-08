# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.gerenciador_sessao_fake import GerenciadorSessaoFake


def test_gerenciador_sessao_fake_ciclo_completo_em_memoria() -> None:
    gerenciador = GerenciadorSessaoFake(cofre_ativo=True)

    assert gerenciador.inicializar_cofre() is True
    assert gerenciador.cofre_disponivel() is True
    assert gerenciador.obter_sessao() is None
    assert gerenciador.carregar_sessao() is None
    assert gerenciador.recuperar_token() is None

    sessao = SessaoUsuario(
        email="caos@arestaclimb.com",
        nome_completo="Robô Caótico",
        jwt_supabase="jwt_teste_123",
        token_atualizacao="refresh_teste_123",
        token_github="gh_token_123",
    )
    gerenciador.salvar_sessao(sessao)

    recuperada = gerenciador.obter_sessao()
    assert recuperada is not None
    assert recuperada.email == "caos@arestaclimb.com"
    assert recuperada.nome_completo == "Robô Caótico"
    assert gerenciador.carregar_sessao() == recuperada
    assert gerenciador.recuperar_token() == "jwt_teste_123"

    gerenciador.limpar_sessao()
    assert gerenciador.obter_sessao() is None
    assert gerenciador.recuperar_token() is None


def test_gerenciador_sessao_fake_com_sessao_inicial_e_cofre_indisponivel() -> None:
    sessao_inicial = SessaoUsuario(
        email="inicial@arestaclimb.com",
        nome_completo="Autor Inicial",
        jwt_supabase="jwt_ini",
        token_atualizacao="ref_ini",
    )
    gerenciador = GerenciadorSessaoFake(sessao_inicial=sessao_inicial, cofre_ativo=False)

    assert gerenciador.inicializar_cofre() is False
    assert gerenciador.cofre_disponivel() is False
    assert gerenciador.recuperar_token() == "jwt_ini"
