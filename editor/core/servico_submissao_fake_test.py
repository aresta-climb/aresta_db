# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest

from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.servico_submissao import ErroSubmissao, StatusSincronizacao
from editor.core.servico_submissao_fake import ServicoSubmissaoFake


def _criar_sessao() -> SessaoUsuario:
    return SessaoUsuario(
        email="caos@arestaclimb.com",
        nome_completo="Robô Caótico",
        jwt_supabase="jwt_123",
        token_atualizacao="refresh_123",
    )


def test_diff_real_e_submissao_com_e_sem_alteracoes(tmp_path: Path) -> None:
    repo_base = tmp_path / "aresta_db"
    pasta_base_croqui = repo_base / "database" / "bau"
    pasta_base_croqui.mkdir(parents=True)
    (pasta_base_croqui / "croqui.yaml").write_text(
        "id: bau\nnome: Pedra do Baú\n", encoding="utf-8"
    )

    pasta_trabalho = tmp_path / "experimental" / "database"
    pasta_trabalho.mkdir(parents=True)
    (pasta_trabalho / "croqui.yaml").write_text("id: bau\nnome: Pedra do Baú\n", encoding="utf-8")

    fake = ServicoSubmissaoFake(caminho_repo_base=repo_base)

    # Sem alterações em relação ao repositório base
    assert fake.obter_arquivos_modificados(pasta_trabalho, "bau") == []
    res_sem = fake.submeter_sugestao(
        caminho_database_croqui=pasta_trabalho,
        id_croqui="bau",
        titulo="Sem mudanças",
        descricao="Teste",
        sessao=_criar_sessao(),
    )
    assert res_sem.sem_alteracoes is True

    # Modifica o arquivo de trabalho e adiciona novo arquivo
    (pasta_trabalho / "croqui.yaml").write_text(
        "id: bau\nnome: Pedra do Baú Editada\n", encoding="utf-8"
    )
    (pasta_trabalho / "setor_novo.md").write_text("---\nnome: Setor Novo\n---\n", encoding="utf-8")

    modificados = fake.obter_arquivos_modificados(pasta_trabalho, "bau")
    assert modificados == ["croqui.yaml", "setor_novo.md"]

    progresso_recebido: list[tuple[int, str]] = []
    res_pr = fake.submeter_sugestao(
        caminho_database_croqui=pasta_trabalho,
        id_croqui="bau",
        titulo="Adiciona Setor Novo",
        descricao="Descrição da PR",
        sessao=_criar_sessao(),
        callback_progresso=lambda pct, msg: progresso_recebido.append((pct, msg)),
    )
    assert res_pr.sucesso is True
    assert res_pr.sem_alteracoes is False
    assert res_pr.pr_number == 1
    assert res_pr.pr_url == "http://127.0.0.1/pull/1"
    assert res_pr.nome_branch == "edicao-bau-0001"
    assert len(progresso_recebido) == 2

    # Após submeter, o repositório base local foi espelhado, logo não há mais diff pendente
    assert fake.obter_arquivos_modificados(pasta_trabalho, "bau") == []


def test_sincronizacao_pr_remota_estados_e_resolucao_de_conflito(tmp_path: Path) -> None:
    fake = ServicoSubmissaoFake(caminho_repo_base=tmp_path / "aresta_db")
    pasta_db = tmp_path / "trabalho"
    pasta_db.mkdir(parents=True)

    # Padrão: ATUALIZADO
    res_atualizado = fake.sincronizar_pr_remota(
        id_croqui="bau",
        nome_branch="edicao-bau-0001",
        caminho_database_croqui=pasta_db,
    )
    assert res_atualizado.status == StatusSincronizacao.ATUALIZADO

    # Configura MESCLADO
    fake.configurar_proxima_sincronizacao(StatusSincronizacao.MESCLADO)
    res_mesclado = fake.sincronizar_pr_remota(
        id_croqui="bau",
        nome_branch="edicao-bau-0001",
        caminho_database_croqui=pasta_db,
    )
    assert res_mesclado.status == StatusSincronizacao.MESCLADO

    # Configura CONFLITO
    fake.configurar_proxima_sincronizacao(
        StatusSincronizacao.CONFLITO,
        arquivos_conflito=["database/bau/croqui.yaml"],
    )
    res_conflito = fake.sincronizar_pr_remota(
        id_croqui="bau",
        nome_branch="edicao-bau-0001",
        caminho_database_croqui=pasta_db,
    )
    assert res_conflito.status == StatusSincronizacao.CONFLITO
    assert res_conflito.arquivos_conflito == ["database/bau/croqui.yaml"]

    # Resolve conflito
    res_resolvido = fake.resolver_conflito_pr(
        id_croqui="bau",
        nome_branch="edicao-bau-0001",
        caminho_database_croqui=pasta_db,
        manter_local=True,
    )
    assert res_resolvido.status == StatusSincronizacao.MESCLADO
    assert fake.conflitos_resolvidos == [("bau", "edicao-bau-0001", True)]


def test_simulacao_de_falha_em_submissao_e_sincronizacao(tmp_path: Path) -> None:
    fake = ServicoSubmissaoFake(caminho_repo_base=tmp_path / "aresta_db")
    pasta_db = tmp_path / "trabalho"
    pasta_db.mkdir(parents=True)

    fake.configurar_falha_proxima_chamada("Erro simulado no Git Proxy")
    with pytest.raises(ErroSubmissao, match="Erro simulado no Git Proxy"):
        fake.submeter_sugestao(
            caminho_database_croqui=pasta_db,
            id_croqui="bau",
            titulo="T",
            descricao="D",
            sessao=_criar_sessao(),
        )

    fake.configurar_falha_proxima_chamada("Falha de sincronização remota")
    with pytest.raises(ErroSubmissao, match="Falha de sincronização remota"):
        fake.sincronizar_pr_remota(
            id_croqui="bau",
            nome_branch="edicao-bau-0001",
            caminho_database_croqui=pasta_db,
        )
