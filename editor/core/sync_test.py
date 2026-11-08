# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from types import SimpleNamespace

import pygit2
import pytest

from editor.core.sync import (
    ErroSincronizacaoGit,
    GerenciadorSincronizacao,
    _tratar_erro_git,
)


def _criar_commit_em_repo_local(
    repo: pygit2.Repository,
    arquivo_rel: str,
    conteudo: str,
    nome_branch: str = "main",
) -> str:
    caminho_arq = Path(repo.workdir) / arquivo_rel
    caminho_arq.parent.mkdir(parents=True, exist_ok=True)
    caminho_arq.write_text(conteudo, encoding="utf-8")

    repo.index.add(arquivo_rel)
    repo.index.write()
    tree = repo.index.write_tree()
    autor = pygit2.Signature("Autor Teste", "autor@arestaclimb.com")
    ref_nome = f"refs/heads/{nome_branch}"
    try:
        ref_existente = repo.lookup_reference(ref_nome)
        pais = [ref_existente.target]
    except KeyError:
        pais = []
    commit_oid = repo.create_commit(ref_nome, autor, autor, f"Commit {arquivo_rel}", tree, pais)
    repo.set_head(ref_nome)
    return str(commit_oid)


def test_obter_url_clone_padrao_personalizado_e_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deve retornar a URL oficial por padrão, permitindo repositório customizado ou override por env/arg."""
    monkeypatch.delenv("ARESTA_GIT_UPSTREAM_URL", raising=False)
    gerenciador = GerenciadorSincronizacao(tmp_path / "repo")
    assert gerenciador.obter_url_clone() == "https://github.com/aresta-climb/aresta_db.git"
    assert (
        gerenciador.obter_url_clone("outro-org/outro_repo")
        == "https://github.com/outro-org/outro_repo.git"
    )

    remoto_env = str(tmp_path / "remoto_env.git")
    monkeypatch.setenv("ARESTA_GIT_UPSTREAM_URL", remoto_env)
    assert gerenciador.obter_url_clone() == remoto_env

    remoto_explicito = str(tmp_path / "remoto_explicito.git")
    gerenciador_exp = GerenciadorSincronizacao(
        tmp_path / "clone_exp", url_upstream=remoto_explicito
    )
    assert gerenciador_exp.obter_url_clone() == remoto_explicito


def test_configurar_remotes_mantem_apenas_origin_e_remove_upstream_e_proxy_legados(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deve garantir apenas o remote origin e remover quaisquer remotes upstream e proxy existentes."""
    monkeypatch.delenv("ARESTA_GIT_UPSTREAM_URL", raising=False)
    caminho_repo = tmp_path / "repo_local"
    repo = pygit2.init_repository(str(caminho_repo), False)
    sha_inicial = _criar_commit_em_repo_local(repo, "README.md", "v1\n")

    gerenciador = GerenciadorSincronizacao(caminho_repo)
    gerenciador.configurar_remotes()

    repo_reaberto = pygit2.Repository(str(caminho_repo))
    nomes_remotes = [r.name for r in repo_reaberto.remotes]
    assert nomes_remotes == ["origin"]
    assert repo_reaberto.remotes["origin"].url == "https://github.com/aresta-climb/aresta_db.git"

    # Simula estado legado com remote upstream congelado, proxy efêmero e origin com URL antiga
    repo_reaberto.remotes.set_url("origin", "https://github.com/antigo/aresta_db.git")
    repo_reaberto.remotes.create("upstream", "https://github.com/aresta-climb/aresta_db.git")
    repo_reaberto.remotes.create("proxy", "https://proxy.arestaclimb.com.br")
    repo_reaberto.create_reference(
        "refs/remotes/upstream/main", pygit2.Oid(hex=sha_inicial), force=True
    )

    nova_url = "https://github.com/aresta-climb/novo_aresta_db.git"
    gerenciador.configurar_remotes(url_upstream=nova_url)

    repo_limpo = pygit2.Repository(str(caminho_repo))
    assert [r.name for r in repo_limpo.remotes] == ["origin"]
    assert repo_limpo.remotes["origin"].url == nova_url
    assert "refs/remotes/upstream/main" not in repo_limpo.references


def test_fazer_fetch_e_checkout_usam_exclusivamente_origin_main(
    tmp_path: Path,
) -> None:
    """Deve atualizar origin/main no fetch e fazer checkout ignorando qualquer ref upstream/main obsoleta."""
    caminho_remoto = tmp_path / "remoto_oficial.git"
    repo_remoto = pygit2.init_repository(str(caminho_remoto), False)
    sha_v1 = _criar_commit_em_repo_local(
        repo_remoto, "database/croqui_teste/croqui.yaml", "id: croqui_teste\nnome: V1\n"
    )

    caminho_clone = tmp_path / "aresta_db_local"
    sync = GerenciadorSincronizacao(caminho_clone, url_upstream=str(caminho_remoto))
    sync.clonar(str(caminho_remoto))

    # Injeta uma referência legada upstream/main apontando para V1 enquanto o remoto avança para V2
    repo_local = pygit2.Repository(str(caminho_clone))
    repo_local.create_reference("refs/remotes/upstream/main", pygit2.Oid(hex=sha_v1), force=True)

    sha_v2 = _criar_commit_em_repo_local(
        repo_remoto, "database/croqui_teste/croqui.yaml", "id: croqui_teste\nnome: V2\n"
    )
    assert sha_v1 != sha_v2

    sync.configurar_remotes()
    sync.fazer_fetch()
    sync.fazer_checkout_main_upstream()

    conteudo_atualizado = (caminho_clone / "database/croqui_teste/croqui.yaml").read_text(
        encoding="utf-8"
    )
    assert "nome: V2" in conteudo_atualizado
    repo_verificado = pygit2.Repository(str(caminho_clone))
    assert str(repo_verificado.head.target) == sha_v2


def test_fazer_checkout_main_upstream_cria_branch_local_quando_ausente_e_ignora_sem_remoto(
    tmp_path: Path,
) -> None:
    """Deve criar a branch local main a partir de origin/main quando ausente, ou não fazer nada sem origin/main."""
    caminho_vazio = tmp_path / "repo_vazio"
    pygit2.init_repository(str(caminho_vazio), False)
    sync_vazio = GerenciadorSincronizacao(caminho_vazio)
    sync_vazio.fazer_checkout_main_upstream()

    caminho_repo = tmp_path / "repo_sem_main_local"
    repo = pygit2.init_repository(str(caminho_repo), False)
    sha = _criar_commit_em_repo_local(repo, "arquivo.txt", "conteudo\n", nome_branch="outra")
    repo.create_reference("refs/remotes/origin/main", pygit2.Oid(hex=sha), force=True)
    assert "main" not in repo.branches.local

    sync = GerenciadorSincronizacao(caminho_repo)
    sync.fazer_checkout_main_upstream()

    repo_apos = pygit2.Repository(str(caminho_repo))
    assert "main" in repo_apos.branches.local
    assert str(repo_apos.branches.local["main"].target) == sha
    assert repo_apos.config.get_bool("core.autocrlf") is False


def test_clonar_suporta_branch_master_e_falha_em_repositorio_vazio_ou_url_invalida(
    tmp_path: Path,
) -> None:
    """Deve aceitar origin/master quando origin/main não existir, e levantar erros adequados em falhas."""
    caminho_remoto_master = tmp_path / "remoto_master.git"
    repo_master = pygit2.init_repository(str(caminho_remoto_master), False)
    _criar_commit_em_repo_local(repo_master, "README.md", "ramo master\n", nome_branch="master")

    caminho_clone_master = tmp_path / "clone_master"
    sync_master = GerenciadorSincronizacao(caminho_clone_master)
    sync_master.clonar(str(caminho_remoto_master))
    assert (caminho_clone_master / "README.md").read_text(encoding="utf-8") == "ramo master\n"

    caminho_remoto_vazio = tmp_path / "remoto_vazio.git"
    pygit2.init_repository(str(caminho_remoto_vazio), True)
    sync_vazio = GerenciadorSincronizacao(tmp_path / "clone_vazio")
    with pytest.raises(RuntimeError, match="Não foi possível encontrar a branch main ou master"):
        sync_vazio.clonar(str(caminho_remoto_vazio))

    sync_http_invalido = GerenciadorSincronizacao(tmp_path / "clone_http_invalido")
    with pytest.raises(ErroSincronizacaoGit):
        sync_http_invalido.clonar("http://127.0.0.1:1/repo_inexistente.git")


def test_fazer_fetch_traduz_giterror_e_tratar_erro_git_no_error(tmp_path: Path) -> None:
    """Deve traduzir falhas de fetch em ErroSincronizacaoGit e mapear 'no error' para mensagem amigável."""
    caminho_repo = tmp_path / "repo_fetch_falho"
    repo = pygit2.init_repository(str(caminho_repo), False)
    repo.remotes.create("origin", str(tmp_path / "nao_existe.git"))

    sync = GerenciadorSincronizacao(caminho_repo)
    with pytest.raises(ErroSincronizacaoGit, match="Erro no Git ao sincronizar"):
        sync.fazer_fetch()

    erro_opaco = _tratar_erro_git(pygit2.GitError("no error"))
    assert "tempo limite" in str(erro_opaco).lower()


def test_reset_hard_restaura_arvore_de_trabalho(tmp_path: Path) -> None:
    """Deve restaurar alterações locais para o commit atual de HEAD ao executar reset_hard."""
    caminho_repo = tmp_path / "repo_reset"
    repo = pygit2.init_repository(str(caminho_repo), False)
    _criar_commit_em_repo_local(repo, "dados.txt", "original\n")

    arquivo = caminho_repo / "dados.txt"
    arquivo.write_text("modificado\n", encoding="utf-8")
    assert arquivo.read_text(encoding="utf-8") == "modificado\n"

    sync = GerenciadorSincronizacao(caminho_repo)
    sync.reset_hard()
    assert arquivo.read_text(encoding="utf-8") == "original\n"


def test_callbacks_credenciais_e_progresso(tmp_path: Path) -> None:
    """Deve fornecer credenciais UserPass quando houver token, Passthrough sem token e reportar progresso."""
    progresso_valores: list[float] = []
    gerenciador_com_token = GerenciadorSincronizacao(tmp_path / "repo", token="token-secreto")
    callbacks = gerenciador_com_token._obter_callbacks(lambda p: progresso_valores.append(p))

    cred = callbacks.credentials("https://github.com", "git", 0)
    assert isinstance(cred, pygit2.UserPass)

    gerenciador_sem_token = GerenciadorSincronizacao(tmp_path / "repo", token=None)
    callbacks_sem_token = gerenciador_sem_token._obter_callbacks()
    with pytest.raises(pygit2.Passthrough):
        callbacks_sem_token.credentials("https://github.com", "git", 0)

    callbacks.transfer_progress(SimpleNamespace(total_objects=100, received_objects=50))
    assert progresso_valores == [50.0]

    callbacks.transfer_progress(SimpleNamespace(total_objects=0, received_objects=0))
    assert len(progresso_valores) == 1
