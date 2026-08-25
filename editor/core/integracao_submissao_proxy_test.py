# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
import pygit2
import responses
from pathlib import Path
from unittest.mock import patch, MagicMock

from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.servico_submissao import ServicoSubmissao, ResultadoSubmissao


def criar_repositorio_base_teste(caminho: Path) -> pygit2.Repository:
    """Inicializa um repositório git com commit inicial na branch main para testes."""
    repo = pygit2.init_repository(str(caminho), False)
    repo.config["user.name"] = "Sistema Aresta"
    repo.config["user.email"] = "sistema@aresta.local"

    # Cria arquivo base inicial
    arquivo_readme = caminho / "README.md"
    arquivo_readme.write_text("# Repositório Aresta DB\n", encoding="utf-8")

    index = repo.index
    index.add_all()
    index.write()
    tree = index.write_tree()

    autor = pygit2.Signature("Sistema Aresta", "sistema@aresta.local")
    commit = repo.create_commit("HEAD", autor, autor, "Commit inicial oficial", tree, [])

    # Cria referência explícita para upstream/main
    repo.create_reference("refs/remotes/upstream/main", commit)
    return repo


@pytest.fixture
def ambiente_submissao(tmp_path):
    caminho_repo = tmp_path / "aresta_db"
    caminho_repo.mkdir(parents=True)
    repo = criar_repositorio_base_teste(caminho_repo)

    caminho_croqui = tmp_path / "croqui_experimental" / "database" / "pedra_do_bau"
    caminho_croqui.mkdir(parents=True)

    arquivo_croqui = caminho_croqui / "croqui.yaml"
    arquivo_croqui.write_text("id: pedra_do_bau\nnome: Pedra do Baú\n", encoding="utf-8")

    arquivo_imagem = caminho_croqui / "foto1.jpg"
    arquivo_imagem.write_bytes(b"\xFF\xD8\xFF\xE0_TESTE_IMAGEM")

    sessao = SessaoUsuario(
        email="colaborador@arestaclimb.com",
        nome_completo="Carlos Escalador",
        jwt_supabase="jwt.valido.mock",
        token_atualizacao="refresh.valido.mock",
        token_github=None,
    )

    return {
        "repo": repo,
        "caminho_repo": caminho_repo,
        "caminho_croqui": caminho_croqui,
        "sessao": sessao,
    }


class TesteIntegracaoSubmissaoProxy:
    """Valida o contrato de fronteira fim-a-fim da submissão através do Git Proxy (Princípio V)."""

    @responses.activate
    def teste_fluxo_submissao_fim_a_fim_sucesso(self, ambiente_submissao):
        caminho_repo = ambiente_submissao["caminho_repo"]
        caminho_croqui = ambiente_submissao["caminho_croqui"]
        sessao = ambiente_submissao["sessao"]
        repo = ambiente_submissao["repo"]

        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.GET,
            f"{url_supabase}/auth/v1/user",
            json={
                "id": "user-123",
                "email": "colaborador@arestaclimb.com",
                "user_metadata": {"nome_completo": "Carlos Escalador"},
            },
            status=200,
        )
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            json={
                "sucesso": True,
                "pr_number": 42,
                "pr_url": "https://github.com/aresta-climb/aresta_db/pull/42",
                "branch": "edicao-pedra_do_bau-12345678",
            },
            status=200,
        )

        servico = ServicoSubmissao(
            caminho_repo_base=caminho_repo,
            url_supabase=url_supabase,
            chave_publica="chave-publica-teste",
        )

        with patch.object(servico, "_executar_push_git") as mock_push:
            resultado = servico.submeter_sugestao(
                caminho_database_croqui=caminho_croqui,
                id_croqui="pedra_do_bau",
                titulo="Adição de novas vias no Baú",
                descricao="Vias conquistadas no setor sul",
                sessao=sessao,
            )

            assert isinstance(resultado, ResultadoSubmissao)
            assert resultado.sucesso is True
            assert resultado.pr_number == 42
            assert resultado.pr_url == "https://github.com/aresta-climb/aresta_db/pull/42"
            assert resultado.nome_branch.startswith("edicao-pedra_do_bau-")

            # Valida que o commit foi assinado com a SessaoUsuario
            head_commit = repo.head.peel()
            assert head_commit.author.name == "Carlos Escalador"
            assert head_commit.author.email == "colaborador@arestaclimb.com"
            assert "edicao(pedra_do_bau): Adição de novas vias no Baú" in head_commit.message
            assert "Signed-off-by: Carlos Escalador <colaborador@arestaclimb.com>" in head_commit.message

            # Valida que o push foi invocado com a branch e o JWT
            mock_push.assert_called_once()
            args_push = mock_push.call_args[0]
            assert args_push[0] == resultado.nome_branch
            assert args_push[1] == "jwt.valido.mock"

    @responses.activate
    def teste_fluxo_submissao_com_token_github_usuario(self, ambiente_submissao):
        """Verifica a propagação do token_github do usuário até a chamada de abertura do PR."""
        caminho_repo = ambiente_submissao["caminho_repo"]
        caminho_croqui = ambiente_submissao["caminho_croqui"]
        sessao = ambiente_submissao["sessao"]
        sessao.token_github = "gho_token_usuario_oauth_123"

        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.GET,
            f"{url_supabase}/auth/v1/user",
            json={
                "id": "user-123",
                "email": "colaborador@arestaclimb.com",
                "user_metadata": {"nome_completo": "Carlos Escalador"},
            },
            status=200,
        )
        
        chamadas_create_pr = []
        def callback_create_pr(request):
            import json
            payload = json.loads(request.body)
            chamadas_create_pr.append(payload)
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps({
                    "sucesso": True,
                    "pr_number": 88,
                    "pr_url": "https://github.com/aresta-climb/aresta_db/pull/88",
                    "branch": payload.get("branch"),
                }),
            )

        responses.add_callback(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            callback=callback_create_pr,
        )

        servico = ServicoSubmissao(
            caminho_repo_base=caminho_repo,
            url_supabase=url_supabase,
            chave_publica="chave-publica-teste",
        )

        with patch.object(servico, "_executar_push_git"):
            resultado = servico.submeter_sugestao(
                caminho_database_croqui=caminho_croqui,
                id_croqui="pedra_do_bau",
                titulo="Adição de vias",
                descricao="Descrição",
                sessao=sessao,
            )

            assert resultado.sucesso is True
            assert len(chamadas_create_pr) == 1
            assert chamadas_create_pr[0].get("token_usuario_github") == "gho_token_usuario_oauth_123"
