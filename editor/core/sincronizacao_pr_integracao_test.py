# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pygit2
from pathlib import Path
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QMessageBox

from editor.core.workspace import ExperimentalWorkspace
from editor.core.worker import TarefaSalvamento, TarefaSincronizacaoPR
from editor.controllers.publish_controller import PublishController
from editor.core.servico_submissao import (
    ServicoSubmissao,
    StatusSincronizacao,
)


def inicializar_repo_git(caminho: Path) -> pygit2.Repository:
    """Inicializa um repositório git local válido para o teste de integração."""
    repo = pygit2.init_repository(str(caminho), False)
    repo.config["user.name"] = "Integracao Teste"
    repo.config["user.email"] = "integracao@aresta.local"

    readme = caminho / "README.md"
    readme.write_text("# Aresta DB\n", encoding="utf-8")
    repo.index.add_all()
    repo.index.write()
    tree = repo.index.write_tree()

    autor = pygit2.Signature("Integracao Teste", "integracao@aresta.local")
    commit = repo.create_commit("HEAD", autor, autor, "Commit inicial", tree, [])
    repo.create_reference("refs/remotes/upstream/main", commit)
    return repo


class TestIntegracaoSincronizacaoPR:
    """
    Teste de integração fim-a-fim cobrindo:
    1. Salvamento resiliente com compilação reportando erro
    2. Validação de publicação com confirmação do usuário
    3. Sincronização remota e merge automático de atualizações
    4. Resolução de conflito atômica com commit de duplo parentesco no Git
    """

    def test_ciclo_completo_salvamento_publicacao_e_sincronizacao(self, tmp_path):
        repo_dir = tmp_path / "repo_base"
        repo = inicializar_repo_git(repo_dir)
        commit_base = repo.lookup_reference("refs/remotes/upstream/main").peel()

        dir_experimental = tmp_path / "croqui_exp"
        dir_experimental.mkdir()
        caminho_db_croqui = dir_experimental / "database" / "falésia_sul"
        caminho_db_croqui.mkdir(parents=True)

        # -------------------------------------------------------------
        # 1. Salvamento Resiliente: grava YAML mesmo com compilação falhando
        # -------------------------------------------------------------
        mock_ws = MagicMock(spec=ExperimentalWorkspace)
        mock_ws.processar_renomeacao_e_compilacao.return_value = (
            caminho_db_croqui,
            ["[ERRO] Campo obrigatório ausente"],
            False,
        )

        dados_croqui = {"id": "falésia_sul", "nome": "Falésia Sul"}
        tarefa_salvar = TarefaSalvamento(
            workspace=mock_ws,
            storage=None,
            caminho_db=caminho_db_croqui,
            croqui_data=dados_croqui,
            novo_id="falésia_sul",
            id_atual="falésia_sul",
            undo_index=1,
        )
        mock_sucesso_salvar = MagicMock()
        mock_erro_salvar = MagicMock()
        tarefa_salvar.sucesso.connect(mock_sucesso_salvar)
        tarefa_salvar.erro.connect(mock_erro_salvar)

        tarefa_salvar.run()

        # Verifica que o arquivo físico foi gravado no disco
        yaml_salvo = caminho_db_croqui / "croqui.yaml"
        assert yaml_salvo.is_file()
        assert "Falésia Sul" in yaml_salvo.read_text(encoding="utf-8")
        # Verifica que sucesso foi emitido contendo a lista de erros de compilação
        mock_sucesso_salvar.assert_called_once()
        mock_erro_salvar.assert_not_called()
        erros_retornados = mock_sucesso_salvar.call_args[0][1]
        assert len(erros_retornados) == 1
        assert "[ERRO]" in erros_retornados[0]

        # -------------------------------------------------------------
        # 2. Publicação com Confirmação para Croqui com Erro
        # -------------------------------------------------------------
        mock_auth = MagicMock()
        mock_historico = MagicMock()
        mock_historico.obter_pilha().isClean.return_value = True
        mock_storage = MagicMock()
        mock_storage.obter_caminho_base_repo.return_value = repo_dir

        controller_pub = PublishController(
            workspace=mock_ws,
            auth=mock_auth,
            historico=mock_historico,
            storage=mock_storage,
        )
        controller_pub.croqui_data = dados_croqui

        with patch("editor.controllers.publish_controller.QMessageBox") as mock_mb, \
             patch.object(controller_pub, "_prosseguir_publicacao") as mock_prosseguir:
            mock_mb.StandardButton = QMessageBox.StandardButton
            # Usuário confirma o envio mesmo com erro
            mock_mb.question.return_value = QMessageBox.StandardButton.Yes

            controller_pub.iniciar_publicacao()

            mock_mb.question.assert_called_once()
            assert "possui erros de compilação" in mock_mb.question.call_args[0][2]
            mock_prosseguir.assert_called_once()

        # -------------------------------------------------------------
        # 3. Sincronização Remota Bidirecional (Fast-Forward e Merge Limpo)
        # -------------------------------------------------------------
        repo.remotes.create("origin", "https://github.com/exemplo/repo.git")
        nome_branch = "edicao-falesia_sul-integracao"
        branch_local = repo.create_branch(nome_branch, commit_base)
        repo.checkout(branch_local)

        # Simula commit na branch remota adicionando foto.png
        dir_repo_croqui = repo_dir / "database" / "falésia_sul"
        dir_repo_croqui.mkdir(parents=True, exist_ok=True)
        (dir_repo_croqui / "foto.png").write_bytes(b"BYTES_FOTO_REMOTA")
        repo.index.add_all()
        repo.index.write()
        tree_rem = repo.index.write_tree()
        autor_remoto = pygit2.Signature("Colaborador Remoto", "remoto@aresta.local")
        commit_remoto_oid = repo.create_commit(
            f"refs/remotes/origin/{nome_branch}",
            autor_remoto,
            autor_remoto,
            "Adiciona foto remota",
            tree_rem,
            [commit_base.id],
        )

        servico_submissao = ServicoSubmissao(caminho_repo_base=repo_dir)

        # Dispara tarefa de sincronização
        tarefa_sinc = TarefaSincronizacaoPR(
            servico_submissao=servico_submissao,
            id_croqui="falésia_sul",
            nome_branch=nome_branch,
            caminho_database_croqui=caminho_db_croqui,
        )
        mock_sucesso_sinc = MagicMock()
        tarefa_sinc.sucesso.connect(mock_sucesso_sinc)

        with patch.object(pygit2.Remote, "fetch"):
            tarefa_sinc.run()

        mock_sucesso_sinc.assert_called_once()
        res_sinc = mock_sucesso_sinc.call_args[0][0]
        assert res_sinc.status == StatusSincronizacao.MESCLADO
        # Arquivo novo veio do remoto para a pasta de trabalho
        assert (caminho_db_croqui / "foto.png").is_file()
        assert (caminho_db_croqui / "foto.png").read_bytes() == b"BYTES_FOTO_REMOTA"

        # -------------------------------------------------------------
        # 4. Resolução de Conflito Preservando Histórico Git (Duplo Parentesco)
        # -------------------------------------------------------------
        # Local altera o croqui.yaml com uma descrição local
        (dir_repo_croqui / "croqui.yaml").write_text("nome: Falésia Local\n", encoding="utf-8")
        repo.index.add_all()
        repo.index.write()
        t_loc = repo.index.write_tree()
        autor_local = pygit2.Signature("Autor Local", "local@aresta.local")
        c_loc_oid = repo.create_commit(
            f"refs/heads/{nome_branch}",
            autor_local,
            autor_local,
            "Edicao local conflitante",
            t_loc,
            [commit_remoto_oid],
        )

        # Remoto altera o mesmo croqui.yaml com descrição remota
        (dir_repo_croqui / "croqui.yaml").write_text("nome: Falésia Remota\n", encoding="utf-8")
        repo.index.add_all()
        repo.index.write()
        t_rem_conflito = repo.index.write_tree()
        c_rem_conflito_oid = repo.create_commit(
            f"refs/remotes/origin/{nome_branch}",
            autor_remoto,
            autor_remoto,
            "Edicao remota conflitante",
            t_rem_conflito,
            [commit_remoto_oid],
        )

        repo.checkout(branch_local, strategy=pygit2.enums.CheckoutStrategy.FORCE)
        (caminho_db_croqui / "croqui.yaml").write_text("nome: Falésia Local\n", encoding="utf-8")

        # Tenta sincronizar -> Deve acusar CONFLITO sem alterar arquivos locais
        with patch.object(pygit2.Remote, "fetch"):
            res_conflito = servico_submissao.sincronizar_pr_remota(
                id_croqui="falésia_sul",
                nome_branch=nome_branch,
                caminho_database_croqui=caminho_db_croqui,
            )

        assert res_conflito.status == StatusSincronizacao.CONFLITO
        assert (caminho_db_croqui / "croqui.yaml").read_text(encoding="utf-8") == "nome: Falésia Local\n"

        # Resolve conflito a favor da versão local mantendo o histórico de ambos
        res_resolucao = servico_submissao.resolver_conflito_pr(
            id_croqui="falésia_sul",
            nome_branch=nome_branch,
            caminho_database_croqui=caminho_db_croqui,
            manter_local=True,
        )

        assert res_resolucao.status == StatusSincronizacao.MESCLADO
        commit_merge_final = repo.lookup_reference(f"refs/heads/{nome_branch}").peel(pygit2.Commit)
        # O commit de merge DEVE conter exatamente 2 pais no Git
        assert len(commit_merge_final.parent_ids) == 2
        assert commit_merge_final.parent_ids[0] == c_loc_oid
        assert commit_merge_final.parent_ids[1] == c_rem_conflito_oid
        # O conteúdo final deve ser o local
        assert (caminho_db_croqui / "croqui.yaml").read_text(encoding="utf-8") == "nome: Falésia Local\n"
