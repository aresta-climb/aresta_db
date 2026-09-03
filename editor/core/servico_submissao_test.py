# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import pygit2
import requests
import responses
from pathlib import Path
from unittest.mock import patch, MagicMock

from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.servico_submissao import (
    ServicoSubmissao,
    ResultadoSubmissao,
    ErroSubmissao,
    gerar_nome_branch,
)


def inicializar_repo_local(caminho: Path) -> pygit2.Repository:
    """Cria um repositório git local válido para testes."""
    repo = pygit2.init_repository(str(caminho), False)
    repo.config["user.name"] = "Autor Teste"
    repo.config["user.email"] = "autor@aresta.local"

    readme = caminho / "README.md"
    readme.write_text("# Aresta DB\n", encoding="utf-8")
    index = repo.index
    index.add_all()
    index.write()
    tree = index.write_tree()

    autor = pygit2.Signature("Autor Teste", "autor@aresta.local")
    commit = repo.create_commit("HEAD", autor, autor, "Commit inicial", tree, [])
    repo.create_reference("refs/remotes/upstream/main", commit)
    return repo


class TesteServicoSubmissaoUnitario:
    """Testes unitários da biblioteca ServicoSubmissao (Princípios II, III e IV)."""

    def teste_gerar_nome_branch(self):
        nome = gerar_nome_branch("bauzinho")
        assert nome.startswith("edicao-bauzinho-")
        partes = nome.split("-")
        assert len(partes) == 3
        assert len(partes[2]) == 8
        # Deve conter apenas caracteres hexadecimais no sufixo
        int(partes[2], 16)

    def teste_sincronizar_arquivos_croqui_escopo_estrito(self, tmp_path):
        origem = tmp_path / "origem" / "database" / "setor_norte"
        origem.mkdir(parents=True)
        (origem / "croqui.yaml").write_text("nome: Norte\n", encoding="utf-8")
        (origem / "foto.png").write_bytes(b"PNG_BYTES")

        destino_repo = tmp_path / "repo"
        destino_repo.mkdir(parents=True)

        servico = ServicoSubmissao(caminho_repo_base=destino_repo)
        destino_final = servico.sincronizar_arquivos_croqui(origem, destino_repo, "setor_norte")

        assert destino_final == destino_repo / "database" / "setor_norte"
        assert (destino_final / "croqui.yaml").is_file()
        assert (destino_final / "foto.png").is_file()

        # Testa remoção de arquivo na sincronização
        (origem / "foto.png").unlink()
        servico.sincronizar_arquivos_croqui(origem, destino_repo, "setor_norte")
        assert not (destino_final / "foto.png").exists()

    def teste_criar_commit_sugestao_com_assinatura_e_mensagem(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)

        servico = ServicoSubmissao(caminho_repo_base=repo_dir)
        nome_branch = "edicao-setor_norte-abcdef12"
        commit_base = repo.lookup_reference("refs/remotes/upstream/main").peel()
        branch = repo.create_branch(nome_branch, commit_base)
        repo.checkout(branch)

        # Adiciona modificação
        arquivo = repo_dir / "database" / "setor_norte" / "croqui.yaml"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text("nome: Novo Setor Norte\n", encoding="utf-8")

        sessao = SessaoUsuario(
            email="mariana@escalada.com",
            nome_completo="Mariana Conquistadora",
            jwt_supabase="jwt_fake",
            token_atualizacao="refresh_fake",
        )

        commit = servico.criar_commit_sugestao(
            repo=repo,
            nome_branch=nome_branch,
            id_croqui="setor_norte",
            titulo="Nova via adicionada",
            descricao="Linha de 6b aberta em julho",
            sessao=sessao,
        )

        assert commit is not None
        assert commit.author.name == "Mariana Conquistadora"
        assert commit.author.email == "mariana@escalada.com"
        assert "edicao(setor_norte): Nova via adicionada" in commit.message
        assert "Linha de 6b aberta em julho" in commit.message
        assert "Signed-off-by: Mariana Conquistadora <mariana@escalada.com>" in commit.message

    def teste_criar_commit_sugestao_sem_alteracoes_retorna_none(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)

        servico = ServicoSubmissao(caminho_repo_base=repo_dir)
        nome_branch = "sugestao-setor_norte-abcdef12"
        commit_base = repo.lookup_reference("refs/remotes/upstream/main").peel()
        branch = repo.create_branch(nome_branch, commit_base)
        repo.checkout(branch)

        sessao = SessaoUsuario(
            email="mariana@escalada.com",
            nome_completo="Mariana Conquistadora",
            jwt_supabase="jwt_fake",
            token_atualizacao="refresh_fake",
        )

        commit = servico.criar_commit_sugestao(
            repo=repo,
            nome_branch=nome_branch,
            id_croqui="setor_norte",
            titulo="Sem mudanças",
            descricao="Nada mudou",
            sessao=sessao,
        )
        assert commit is None

    @responses.activate
    def teste_solicitar_abertura_pr_sucesso(self, tmp_path):
        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            json={
                "sucesso": True,
                "pr_number": 99,
                "pr_url": "https://github.com/aresta-climb/aresta_db/pull/99",
                "branch": "sugestao-itacolomi-11223344",
            },
            status=200,
        )

        servico = ServicoSubmissao(
            caminho_repo_base=tmp_path,
            url_supabase=url_supabase,
            chave_publica="chave-teste",
        )

        resultado = servico.solicitar_abertura_pr(
            jwt="jwt.token.valido",
            branch="sugestao-itacolomi-11223344",
            titulo="Adição do Pico do Itacolomi",
            descricao="Todas as vias tradicionais",
        )

        assert resultado["pr_number"] == 99
        assert resultado["pr_url"] == "https://github.com/aresta-climb/aresta_db/pull/99"

        chamada = responses.calls[0]
        assert "Bearer jwt.token.valido" in chamada.request.headers["Authorization"]
        assert chamada.request.headers["apikey"] == "chave-teste"

    @responses.activate
    def teste_solicitar_abertura_pr_com_token_usuario_github(self, tmp_path):
        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            json={
                "numero_pr": 100,
                "url_pr": "https://github.com/aresta-climb/aresta_db/pull/100",
            },
            status=200,
        )

        servico = ServicoSubmissao(
            caminho_repo_base=tmp_path,
            url_supabase=url_supabase,
            chave_publica="chave-teste",
        )

        resultado = servico.solicitar_abertura_pr(
            jwt="jwt.token.valido",
            branch="edicao-bau-123",
            titulo="Título",
            descricao="Desc",
            token_usuario_github="gho_token_usuario_123",
        )

        assert resultado["pr_number"] == 100
        import json
        corpo = json.loads(responses.calls[0].request.body)
        assert corpo["token_usuario_github"] == "gho_token_usuario_123"

    @responses.activate
    def teste_solicitar_abertura_pr_erro_servidor_lanca_excecao(self, tmp_path):
        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            json={"erro": "Arquivos fora do escopo database/ detectados."},
            status=400,
        )

        servico = ServicoSubmissao(
            caminho_repo_base=tmp_path,
            url_supabase=url_supabase,
        )

        with pytest.raises(ErroSubmissao) as info:
            servico.solicitar_abertura_pr(
                jwt="jwt.token.valido",
                branch="edicao-itacolomi-11223344",
                titulo="Inválido",
                descricao="Teste",
            )

        assert "Arquivos fora do escopo" in str(info.value)

    @responses.activate
    def teste_solicitar_abertura_pr_erro_servidor_texto_puro(self, tmp_path):
        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            body="Erro interno de infraestrutura",
            status=500,
        )

        servico = ServicoSubmissao(caminho_repo_base=tmp_path, url_supabase=url_supabase)
        with pytest.raises(ErroSubmissao, match="Erro interno de infraestrutura"):
            servico.solicitar_abertura_pr("jwt", "edicao-1", "T", "D")

    @responses.activate
    def teste_solicitar_abertura_pr_resposta_sucesso_nao_json(self, tmp_path):
        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            body="Nao e json",
            status=200,
        )

        servico = ServicoSubmissao(caminho_repo_base=tmp_path, url_supabase=url_supabase)
        with pytest.raises(ErroSubmissao, match="Resposta inválida do servidor"):
            servico.solicitar_abertura_pr("jwt", "edicao-1", "T", "D")

    def teste_solicitar_abertura_pr_erro_conexao(self, tmp_path):
        servico = ServicoSubmissao(caminho_repo_base=tmp_path, url_supabase="https://teste.supabase.co")
        with patch("requests.post", side_effect=requests.ConnectionError("Sem conexao")):
            with pytest.raises(ErroSubmissao, match="Falha na comunicação com o servidor"):
                servico.solicitar_abertura_pr("jwt", "edicao-1", "T", "D")

    def teste_fazer_push_proxy_configura_callbacks_corretamente(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)

        servico = ServicoSubmissao(
            caminho_repo_base=repo_dir,
            url_supabase="https://teste.supabase.co",
        )

        mock_remote = MagicMock()
        def mock_getitem(nome):
            raise KeyError("proxy")

        with patch.object(repo.remotes, "create", return_value=mock_remote) as mock_create:
            with patch.object(repo.remotes, "__getitem__", side_effect=mock_getitem):
                with patch.object(servico, "_obter_callbacks_push") as mock_callbacks:
                    mock_callbacks.return_value = MagicMock()
                    servico.fazer_push_proxy(
                        repo=repo,
                        nome_branch="sugestao-teste-123",
                        jwt="jwt_teste",
                    )

                    mock_create.assert_called_once_with(
                        "proxy", "https://teste.supabase.co/functions/v1/git-proxy"
                    )
                    mock_remote.push.assert_called_once()

    def teste_fazer_push_proxy_quando_remote_ja_existe(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        repo.remotes.create("proxy", "https://url_antiga.com")
        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")

        with patch("pygit2.Remote.push") as mock_push:
            servico.fazer_push_proxy(repo=repo, nome_branch="sugestao-teste-123", jwt="jwt_teste")
            assert repo.remotes["proxy"].url == "https://teste.supabase.co/functions/v1/git-proxy"
            mock_push.assert_called_once()

    def teste_executar_push_git_chama_fazer_push_proxy(self, tmp_path):
        servico = ServicoSubmissao(caminho_repo_base=tmp_path)
        with patch.object(servico, "fazer_push_proxy") as mock_push:
            servico._executar_push_git("branch", "jwt", MagicMock())
            mock_push.assert_called_once()

    def teste_callbacks_push_credentials_e_progress(self, tmp_path):
        servico = ServicoSubmissao(caminho_repo_base=tmp_path)
        progresso_chamado = []
        cb = servico._obter_callbacks_push("jwt_123", callback_progresso=lambda p: progresso_chamado.append(p))

        # Até 3 tentativas retorna UserPass
        assert isinstance(cb.credentials("https://proxy", "bearer", 0), pygit2.UserPass)
        assert isinstance(cb.credentials("https://proxy", "bearer", 0), pygit2.UserPass)
        assert isinstance(cb.credentials("https://proxy", "bearer", 0), pygit2.UserPass)
        # Na 4ª tentativa retorna None para evitar loop
        assert cb.credentials("https://proxy", "bearer", 0) is None

        stats = MagicMock()
        stats.total_objects = 10
        stats.received_objects = 5
        cb.transfer_progress(stats)
        assert progresso_chamado == [50.0]

        # Testa stats com 0 objetos (não divide por zero)
        stats.total_objects = 0
        cb.transfer_progress(stats)
        assert len(progresso_chamado) == 1

    def teste_fazer_push_proxy_erro_autenticacao(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        with patch("pygit2.Remote.push", side_effect=Exception("too many redirects or authentication replays")):
            with pytest.raises(ErroSubmissao, match="Falha na autenticação com o Git Proxy"):
                servico.fazer_push_proxy(repo=repo, nome_branch="sugestao-1", jwt="jwt_invalido")

    def teste_fazer_push_proxy_erro_interface_credencial(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        with patch("pygit2.Remote.push", side_effect=TypeError("credential does not implement interface")):
            with pytest.raises(ErroSubmissao, match="Falha na autenticação com o Git Proxy"):
                servico.fazer_push_proxy(repo=repo, nome_branch="sugestao-1", jwt="jwt_invalido")

    def teste_fazer_push_proxy_erro_generico(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        with patch("pygit2.Remote.push", side_effect=Exception("Connection reset by peer")):
            with pytest.raises(ErroSubmissao, match="Falha ao enviar proposta de mudança"):
                servico.fazer_push_proxy(repo=repo, nome_branch="sugestao-1", jwt="jwt_valido")

    def teste_inicializacao_padrao_com_gerenciador_caminhos(self, tmp_path):
        with patch("editor.core.servico_submissao.GerenciadorCaminhos") as mock_gc:
            mock_gc.return_value.obter_caminho_base_repo.return_value = tmp_path
            servico = ServicoSubmissao()
            assert servico.caminho_repo_base == tmp_path

    def teste_sincronizar_arquivos_com_subdiretorios_e_remocoes(self, tmp_path):
        origem = tmp_path / "origem" / "database" / "setor_sul"
        origem.mkdir(parents=True)
        sub_origem = origem / "fotos"
        sub_origem.mkdir()
        (sub_origem / "foto_antiga.jpg").write_text("foto antiga")

        destino_repo = tmp_path / "repo"
        destino_repo.mkdir(parents=True)
        destino_croqui = destino_repo / "database" / "setor_sul"
        destino_sub = destino_croqui / "antiga_pasta"
        destino_sub.mkdir(parents=True)
        (destino_sub / "lixo.txt").write_text("lixo")

        servico = ServicoSubmissao(caminho_repo_base=destino_repo)
        servico.sincronizar_arquivos_croqui(origem, destino_repo, "setor_sul")

        assert (destino_croqui / "fotos" / "foto_antiga.jpg").is_file()
        assert not (destino_croqui / "antiga_pasta").exists()

    @responses.activate
    def teste_solicitar_abertura_pr_resposta_nao_json(self, tmp_path):
        url_supabase = "https://teste.supabase.co"
        responses.add(
            responses.POST,
            f"{url_supabase}/functions/v1/create-pr",
            body="502 Bad Gateway - Timeout",
            status=502,
        )

        servico = ServicoSubmissao(caminho_repo_base=tmp_path, url_supabase=url_supabase)
        with pytest.raises(ErroSubmissao) as info:
            servico.solicitar_abertura_pr("jwt", "branch", "titulo", "desc")
        assert "502 Bad Gateway" in str(info.value)

    def teste_submeter_sugestao_sem_alteracoes(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)

        croqui_dir = tmp_path / "croqui" / "database" / "bau"
        croqui_dir.mkdir(parents=True)
        # Cria arquivos idênticos aos que já estariam sincronizados
        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")

        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_123",
            token_atualizacao="ref_123",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "123"}):
            resultado = servico.submeter_sugestao(
                caminho_database_croqui=croqui_dir,
                id_croqui="bau",
                titulo="Sem mudanças",
                descricao="desc",
                sessao=sessao,
            )

            assert resultado.sucesso is True
            assert resultado.sem_alteracoes is True
            assert "Nenhuma alteração" in resultado.mensagem

    def teste_submeter_sugestao_com_renovacao_jwt_sucesso(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)

        croqui_dir = tmp_path / "croqui" / "database" / "bau"
        croqui_dir.mkdir(parents=True)
        (croqui_dir / "croqui.yaml").write_text("nome: Bau Novo\n", encoding="utf-8")

        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")

        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_expirado",
            token_atualizacao="ref_valido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", side_effect=Exception("Expirado")):
            with patch.object(
                servico.cliente_auth,
                "renovar_sessao",
                return_value={"access_token": "jwt_renovado", "refresh_token": "ref_novo"},
            ) as mock_renovar:
                with patch.object(servico, "_executar_push_git") as mock_push:
                    with patch.object(
                        servico, "solicitar_abertura_pr", return_value={"pr_number": 5, "pr_url": "url_pr"}
                    ):
                        progresso = []
                        resultado = servico.submeter_sugestao(
                            caminho_database_croqui=croqui_dir,
                            id_croqui="bau",
                            titulo="Titulo",
                            descricao="Desc",
                            sessao=sessao,
                            callback_progresso=lambda pct, msg: progresso.append((pct, msg)),
                        )

                        mock_renovar.assert_called_once_with("ref_valido")
                        assert sessao.jwt_supabase == "jwt_renovado"
                        assert sessao.token_atualizacao == "ref_novo"
                        assert resultado.sucesso is True
                        assert resultado.pr_number == 5
                        assert len(progresso) > 0

    def teste_submeter_sugestao_com_renovacao_jwt_falha(self, tmp_path):
        repo_dir = tmp_path / "repo"
        inicializar_repo_local(repo_dir)
        croqui_dir = tmp_path / "croqui" / "database" / "bau"
        croqui_dir.mkdir(parents=True)

        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")
        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_invalido",
            token_atualizacao="ref_invalido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", side_effect=Exception("Expirado")):
            with patch.object(servico.cliente_auth, "renovar_sessao", side_effect=Exception("Refresh revogado")):
                with pytest.raises(ErroSubmissao) as info:
                    servico.submeter_sugestao(
                        caminho_database_croqui=croqui_dir,
                        id_croqui="bau",
                        titulo="Titulo",
                        descricao="Desc",
                        sessao=sessao,
                    )
                assert "Sessão expirada" in str(info.value)

    def teste_submeter_sugestao_com_branch_existente_local_e_remota(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)

        # Cria branch local existente
        ref_upstream = repo.lookup_reference("refs/remotes/upstream/main")
        repo.create_branch("sugestao-bau-existente1", ref_upstream.peel())

        croqui_dir = tmp_path / "croqui" / "database" / "bau"
        croqui_dir.mkdir(parents=True)
        (croqui_dir / "croqui.yaml").write_text("nome: Bau Atualizado\n", encoding="utf-8")

        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")
        sessao = SessaoUsuario(
            email="autor@teste.com",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_123",
            token_atualizacao="ref_123",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "123"}):
            with patch.object(servico, "_executar_push_git"):
                with patch.object(
                    servico, "solicitar_abertura_pr", return_value={"pr_number": 7, "pr_url": "url_pr"}
                ):
                    # 1. Branch já existe localmente
                    res1 = servico.submeter_sugestao(
                        caminho_database_croqui=croqui_dir,
                        id_croqui="bau",
                        titulo="Titulo",
                        descricao="Desc",
                        sessao=sessao,
                        branch_existente="sugestao-bau-existente1",
                    )
                    assert res1.nome_branch == "sugestao-bau-existente1"

                    # 2. Branch não existe localmente ainda
                    (croqui_dir / "croqui.yaml").write_text("nome: Bau 2\n", encoding="utf-8")
                    res2 = servico.submeter_sugestao(
                        caminho_database_croqui=croqui_dir,
                        id_croqui="bau",
                        titulo="Titulo 2",
                        descricao="Desc 2",
                        sessao=sessao,
                        branch_existente="sugestao-bau-nova1",
                    )
                    assert res2.nome_branch == "sugestao-bau-nova1"

    def teste_submeter_sugestao_com_apenas_remote_origin(self, tmp_path):
        """Testa submissão quando o repositório possui apenas remote origin/main e não upstream/main."""
        repo_dir = tmp_path / "repo_origin"
        repo = pygit2.init_repository(str(repo_dir), False)
        repo.config["user.name"] = "Autor"
        repo.config["user.email"] = "autor@aresta.local"
        (repo_dir / "README.md").write_text("# Origin Only")
        repo.index.add_all()
        repo.index.write()
        commit = repo.create_commit("HEAD", pygit2.Signature("A", "a@a.com"), pygit2.Signature("A", "a@a.com"), "init", repo.index.write_tree(), [])
        repo.create_reference("refs/remotes/origin/main", commit)

        croqui_dir = tmp_path / "croqui" / "database" / "setor"
        croqui_dir.mkdir(parents=True)
        (croqui_dir / "croqui.yaml").write_text("nome: Novo Setor\n")

        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")
        sessao = SessaoUsuario("a@a.com", "Autor", "jwt_fake", "ref_fake")

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "1"}):
            with patch.object(servico, "_executar_push_git"):
                with patch.object(servico, "solicitar_abertura_pr", return_value={"pr_number": 1, "pr_url": "url"}):
                    res = servico.submeter_sugestao(
                        caminho_database_croqui=croqui_dir,
                        id_croqui="setor",
                        titulo="Titulo",
                        descricao="Desc",
                        sessao=sessao,
                    )
                    assert res.sucesso is True
                    assert res.nome_branch.startswith("edicao-setor-")

    def teste_submeter_sugestao_com_apenas_head_local(self, tmp_path):
        """Testa submissão quando não há remotes configurados, usando HEAD local como base."""
        repo_dir = tmp_path / "repo_head"
        repo = pygit2.init_repository(str(repo_dir), False)
        repo.config["user.name"] = "Autor"
        repo.config["user.email"] = "autor@aresta.local"
        (repo_dir / "README.md").write_text("# Local Only")
        repo.index.add_all()
        repo.index.write()
        repo.create_commit("HEAD", pygit2.Signature("A", "a@a.com"), pygit2.Signature("A", "a@a.com"), "init", repo.index.write_tree(), [])

        croqui_dir = tmp_path / "croqui_head" / "database" / "setor"
        croqui_dir.mkdir(parents=True)
        (croqui_dir / "croqui.yaml").write_text("nome: Setor Local\n")

        servico = ServicoSubmissao(caminho_repo_base=repo_dir, url_supabase="https://teste.supabase.co")
        sessao = SessaoUsuario("a@a.com", "Autor", "jwt_fake", "ref_fake")

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "1"}):
            with patch.object(servico, "_executar_push_git"):
                with patch.object(servico, "solicitar_abertura_pr", return_value={"pr_number": 2, "pr_url": "url2"}):
                    res = servico.submeter_sugestao(
                        caminho_database_croqui=croqui_dir,
                        id_croqui="setor",
                        titulo="Titulo Local",
                        descricao="Desc Local",
                        sessao=sessao,
                    )
                    assert res.sucesso is True

    def teste_obter_commit_base_repo_vazio_lanca_erro(self, tmp_path):
        """Testa erro ao tentar obter commit base de repositório vazio."""
        repo_dir = tmp_path / "repo_vazio"
        pygit2.init_repository(str(repo_dir), False)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)
        repo = pygit2.Repository(str(repo_dir))
        with pytest.raises(ErroSubmissao, match="Não foi possível determinar o commit base"):
            servico._obter_commit_base(repo)

    def teste_obter_commit_base_erro_ao_peel_head(self, tmp_path):
        """Testa fallback de erro quando repo.head.peel() lança exceção."""
        servico = ServicoSubmissao(caminho_repo_base=tmp_path)
        mock_repo = MagicMock()
        mock_repo.lookup_reference.side_effect = KeyError("ref")
        mock_repo.is_empty = False
        mock_repo.head_is_unborn = False
        mock_repo.head.peel.side_effect = RuntimeError("Peel error")

        with pytest.raises(ErroSubmissao, match="Não foi possível determinar o commit base"):
            servico._obter_commit_base(mock_repo)


    def teste_obter_arquivos_modificados_apenas_retorna_arquivos_alterados_adicionados_ou_removidos(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        base_croqui_dir = repo_dir / "database" / "meu_croqui"
        base_croqui_dir.mkdir(parents=True)
        (base_croqui_dir / "croqui.yaml").write_text("nome: Bau v1\n", encoding="utf-8")
        img_base = base_croqui_dir / "imagens"
        img_base.mkdir()
        (img_base / "foto1.jpg").write_bytes(b"FOTO1_ORIGINAL")
        (img_base / "foto_para_deletar.jpg").write_bytes(b"DELETAR")

        croqui_trabalho = tmp_path / "trabalho" / "database" / "meu_croqui"
        croqui_trabalho.mkdir(parents=True)
        # Modificado: croqui.yaml
        (croqui_trabalho / "croqui.yaml").write_text("nome: Bau v2 (Alterado)\n", encoding="utf-8")
        img_trabalho = croqui_trabalho / "imagens"
        img_trabalho.mkdir()
        # Inalterado: foto1.jpg
        (img_trabalho / "foto1.jpg").write_bytes(b"FOTO1_ORIGINAL")
        # Adicionado: foto_nova.jpg
        (img_trabalho / "foto_nova.jpg").write_bytes(b"FOTO_NOVA")
        # Removido: foto_para_deletar.jpg (não existe na pasta de trabalho)

        servico = ServicoSubmissao(caminho_repo_base=repo_dir)
        modificados = servico.obter_arquivos_modificados(croqui_trabalho, "meu_croqui")

        # Deve conter apenas o modificado, o novo e o removido
        assert "croqui.yaml" in modificados
        assert "imagens/foto_nova.jpg" in modificados
        assert "imagens/foto_para_deletar.jpg" in modificados
        # O arquivo inalterado NÃO deve estar presente
        assert "imagens/foto1.jpg" not in modificados
        assert len(modificados) == 3

    def teste_obter_arquivos_modificados_novo_croqui(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        croqui_trabalho = tmp_path / "trabalho" / "database" / "novo_setor"
        croqui_trabalho.mkdir(parents=True)
        (croqui_trabalho / "croqui.yaml").write_text("nome: Novo\n", encoding="utf-8")
        (croqui_trabalho / "mapa.png").write_bytes(b"MAPA")

        servico = ServicoSubmissao(caminho_repo_base=repo_dir)
        modificados = servico.obter_arquivos_modificados(croqui_trabalho, "novo_setor")

        assert sorted(modificados) == ["croqui.yaml", "mapa.png"]

    def teste_obter_arquivos_modificados_sem_alteracoes(self, tmp_path):
        repo_dir = tmp_path / "repo"
        base_croqui = repo_dir / "database" / "croqui_identico"
        base_croqui.mkdir(parents=True)
        (base_croqui / "croqui.yaml").write_text("nome: Igual\n", encoding="utf-8")

        croqui_trabalho = tmp_path / "trabalho"
        croqui_trabalho.mkdir()
        (croqui_trabalho / "croqui.yaml").write_text("nome: Igual\n", encoding="utf-8")

        servico = ServicoSubmissao(caminho_repo_base=repo_dir)
        modificados = servico.obter_arquivos_modificados(croqui_trabalho, "croqui_identico")
        assert modificados == []

    def teste_obter_arquivos_modificados_diretorio_invalido(self, tmp_path):
        servico = ServicoSubmissao(caminho_repo_base=tmp_path)
        assert servico.obter_arquivos_modificados(Path("/diretorio/inexistente"), "id") == []


class TesteTelemetriaSubmissaoIntegracao:
    """Testes de integração para captura e reporte de falhas no ServicoSubmissao (Princípios IV e V)."""

    @patch("editor.core.servico_submissao.capturar_falha_submissao")
    @patch("editor.core.servico_submissao.registrar_breadcrumb_submissao")
    def teste_falha_push_proxy_dispara_telemetria_git_proxy(
        self, mock_breadcrumb, mock_capturar, tmp_path
    ):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        caminho_db = tmp_path / "database" / "croqui_teste"
        caminho_db.mkdir(parents=True)
        (caminho_db / "croqui.yaml").write_text("nome: Croqui Teste\n", encoding="utf-8")

        sessao = SessaoUsuario(
            email="autor@aresta.local",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_valido",
            token_atualizacao="refresh_valido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "u1"}), \
             patch("pygit2.Remote.push", side_effect=Exception("HTTP 500 Internal Server Error no Proxy")):
            with pytest.raises(ErroSubmissao) as excinfo:
                servico.submeter_sugestao(
                    caminho_database_croqui=caminho_db,
                    id_croqui="croqui_teste",
                    titulo="Adicionando nova via",
                    descricao="Detalhes",
                    sessao=sessao,
                )
            assert "Proxy" in str(excinfo.value)
            mock_capturar.assert_called_once()
            args, kwargs = mock_capturar.call_args
            assert kwargs.get("id_croqui") == "croqui_teste" or args[1] == "croqui_teste"
            assert kwargs.get("categoria") == "git_proxy" or (len(args) > 3 and args[3] == "git_proxy")
            assert mock_breadcrumb.called

    @patch("editor.core.servico_submissao.capturar_falha_submissao")
    @patch("editor.core.servico_submissao.registrar_breadcrumb_submissao")
    def teste_falha_edge_function_create_pr_dispara_telemetria_github_api(
        self, mock_breadcrumb, mock_capturar, tmp_path
    ):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        caminho_db = tmp_path / "database" / "croqui_teste"
        caminho_db.mkdir(parents=True)
        (caminho_db / "croqui.yaml").write_text("nome: Croqui Teste\n", encoding="utf-8")

        sessao = SessaoUsuario(
            email="autor@aresta.local",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_valido",
            token_atualizacao="refresh_valido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "u1"}), \
             patch.object(servico, "_executar_push_git"), \
             patch("requests.post", side_effect=Exception("Edge Function create-pr falhou")):
            with pytest.raises(ErroSubmissao):
                servico.submeter_sugestao(
                    caminho_database_croqui=caminho_db,
                    id_croqui="croqui_teste",
                    titulo="Adicionando via",
                    descricao="Desc",
                    sessao=sessao,
                )
            mock_capturar.assert_called_once()
            args, kwargs = mock_capturar.call_args
            categoria = kwargs.get("categoria") or (args[3] if len(args) > 3 else None)
            assert categoria == "github_api"
            assert kwargs.get("id_croqui") == "croqui_teste" or args[1] == "croqui_teste"

    @patch("editor.core.servico_submissao.capturar_falha_submissao")
    def teste_falha_commit_sugestao_dispara_telemetria_git_local(
        self, mock_capturar, tmp_path
    ):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        caminho_db = tmp_path / "database" / "croqui_teste"
        caminho_db.mkdir(parents=True)
        (caminho_db / "croqui.yaml").write_text("nome: Croqui Teste\n", encoding="utf-8")

        sessao = SessaoUsuario(
            email="autor@aresta.local",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_valido",
            token_atualizacao="refresh_valido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "u1"}), \
             patch.object(servico, "criar_commit_sugestao", side_effect=RuntimeError("Index lock error")):
            with pytest.raises(ErroSubmissao) as excinfo:
                servico.submeter_sugestao(
                    caminho_database_croqui=caminho_db,
                    id_croqui="croqui_teste",
                    titulo="Titulo",
                    descricao="Desc",
                    sessao=sessao,
                )
            assert "commit assinado" in str(excinfo.value)
            mock_capturar.assert_called_once()
            kwargs = mock_capturar.call_args[1]
            assert kwargs["categoria"] == "git_local"
            assert kwargs["etapa"] == "commit_local"
            assert kwargs["id_croqui"] == "croqui_teste"

    @patch("editor.core.servico_submissao.capturar_falha_submissao")
    def teste_fazer_push_proxy_falha_autenticacao(self, mock_capturar, tmp_path):
        servico = ServicoSubmissao(caminho_repo_base=tmp_path)
        repo_mock = MagicMock()
        remote_mock = MagicMock()
        repo_mock.remotes.__getitem__.return_value = remote_mock
        remote_mock.push.side_effect = Exception("credential does not implement authentication")

        with pytest.raises(ErroSubmissao) as excinfo:
            servico.fazer_push_proxy(
                repo=repo_mock,
                nome_branch="edicao-croqui_xyz-abcdef12",
                jwt="jwt_invalido",
            )
        assert "Falha na autenticação" in str(excinfo.value)
        mock_capturar.assert_called_once()
        kwargs = mock_capturar.call_args[1]
        assert kwargs["categoria"] == "autenticacao"
        assert kwargs["id_croqui"] == "croqui_xyz"




    @patch("editor.core.servico_submissao.capturar_falha_submissao")
    def teste_falha_renovacao_sessao_dispara_telemetria_autenticacao(
        self, mock_capturar, tmp_path
    ):
        repo_dir = tmp_path / "repo"
        repo = inicializar_repo_local(repo_dir)
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        caminho_db = tmp_path / "database" / "croqui_teste"
        caminho_db.mkdir(parents=True)
        (caminho_db / "croqui.yaml").write_text("nome: Croqui Teste\n", encoding="utf-8")

        sessao = SessaoUsuario(
            email="autor@aresta.local",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_expirado",
            token_atualizacao="refresh_invalido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", side_effect=Exception("Token inválido")), \
             patch.object(servico.cliente_auth, "renovar_sessao", side_effect=Exception("Refresh token revogado")):
            with pytest.raises(ErroSubmissao) as excinfo:
                servico.submeter_sugestao(
                    caminho_database_croqui=caminho_db,
                    id_croqui="croqui_teste",
                    titulo="Titulo",
                    descricao="Desc",
                    sessao=sessao,
                )
            assert "Sessão expirada" in str(excinfo.value)
            mock_capturar.assert_called_once()
            args, kwargs = mock_capturar.call_args
            categoria = kwargs.get("categoria") or (args[3] if len(args) > 3 else None)
            assert categoria == "autenticacao"

    @patch("editor.core.servico_submissao.capturar_falha_submissao")
    def teste_falha_git_local_dispara_telemetria_git_local(
        self, mock_capturar, tmp_path
    ):
        repo_dir = tmp_path / "repo"
        servico = ServicoSubmissao(caminho_repo_base=repo_dir)

        caminho_db = tmp_path / "database" / "croqui_teste"
        caminho_db.mkdir(parents=True)
        (caminho_db / "croqui.yaml").write_text("nome: Croqui Teste\n", encoding="utf-8")

        sessao = SessaoUsuario(
            email="autor@aresta.local",
            nome_completo="Autor Teste",
            jwt_supabase="jwt_valido",
            token_atualizacao="refresh_valido",
        )

        with patch.object(servico.cliente_auth, "obter_usuario_atual", return_value={"id": "u1"}), \
             patch("pygit2.Repository", side_effect=pygit2.GitError("Falha ao abrir repositório local")):
            with pytest.raises((ErroSubmissao, pygit2.GitError)):
                servico.submeter_sugestao(
                    caminho_database_croqui=caminho_db,
                    id_croqui="croqui_teste",
                    titulo="Titulo",
                    descricao="Desc",
                    sessao=sessao,
                )
            mock_capturar.assert_called_once()
            args, kwargs = mock_capturar.call_args
            categoria = kwargs.get("categoria") or (args[3] if len(args) > 3 else None)
            assert categoria == "git_local"



