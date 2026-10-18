# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.core.storage import GerenciadorCaminhos
from editor.core.workspace import (
    ExperimentalWorkspace,
    LocalRepoWorkspace,
    capturar_saida,
)


class CaminhosTemp(GerenciadorCaminhos):
    def __init__(self, base: Path) -> None:
        super().__init__()
        self._base = base

    def obter_diretorio_base(self) -> Path:
        return self._base


def _criar_croqui_valido(pasta_db: Path, croqui_id: str) -> None:
    pasta_db.mkdir(parents=True, exist_ok=True)
    pasta_img = pasta_db / "imagens"
    pasta_img.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (24, 24), color="blue").save(pasta_img / "capa.webp", "WEBP")
    (pasta_db / "croqui.yaml").write_text(
        f"id: {croqui_id}\n"
        f"nome: Croqui {croqui_id}\n"
        "publicar_croqui: true\n"
        "caminho_thumbnail: imagens/capa.webp\n"
        "ultima_migracao: 5\n"
        "picos:\n"
        "  - nome: Pico Principal\n"
        "    estado: MG\n",
        encoding="utf-8",
    )


def test_experimental_workspace_paths_e_commit_base(tmp_path: Path) -> None:
    raiz = tmp_path / "meu_croqui_exp"
    (raiz / "database").mkdir(parents=True)
    (raiz / "compilado").mkdir(parents=True)

    ws = ExperimentalWorkspace(raiz)
    assert ws.obter_caminho_database() == raiz / "database"
    assert ws.obter_caminho_compilado() == raiz / "compilado"
    assert ws.obter_pasta_servidor_celular() == raiz / "compilado"
    assert ws.can_publish_pr() is True
    assert ws.obter_tag_titulo() == ""
    assert ws.obter_diario() is not None
    assert ws.obter_commit_base_sha() == ""

    # Com metadados.json válido
    (raiz / "metadados.json").write_text(
        json.dumps({"commit_base_sha": "abc123def"}), encoding="utf-8"
    )
    assert ws.obter_commit_base_sha() == "abc123def"

    # Com metadados.json inválido
    (raiz / "metadados.json").write_text("{invalido", encoding="utf-8")
    assert ws.obter_commit_base_sha() == ""


def test_experimental_workspace_processar_renomeacao_e_compilacao(tmp_path: Path) -> None:
    storage = CaminhosTemp(tmp_path / "appdata")
    gerenciador = GerenciadorCroquiExperimental(storage)
    caminho_exp = gerenciador.criar_novo_croqui("Croqui Inicial", "Ouro Preto", "MG", "Autor Teste")
    id_inicial = caminho_exp.name

    ws = ExperimentalWorkspace(caminho_exp)
    diario = ws.obter_diario()
    assert diario is not None
    diario.gravar_comando_pendente({"classe": "CmdTeste"})
    assert diario.tem_alteracoes_pendentes()

    # Renomeia e compila
    (ws.obter_caminho_database() / "croqui.yaml").write_text(
        "id: croqui_renomeado\n"
        "nome: Croqui Renomeado\n"
        "ultima_migracao: 5\n"
        "picos:\n"
        "  - nome: Pico 1\n"
        "    estado: MG\n",
        encoding="utf-8",
    )
    novo_caminho, msgs, db_mod = ws.processar_renomeacao_e_compilacao(
        "croqui_renomeado", id_inicial, storage
    )
    assert novo_caminho == caminho_exp
    assert ws.caminho_raiz == caminho_exp
    assert isinstance(msgs, list)
    assert db_mod is True
    assert (novo_caminho / "compilado" / "compilado.binarypb").is_file()
    assert not ws.obter_diario().tem_alteracoes_pendentes()

    # Segunda compilação sem renomeação e já saneado -> db_mod False
    caminho2, msgs2, db_mod2 = ws.processar_renomeacao_e_compilacao(
        "croqui_renomeado", "croqui_renomeado", storage
    )
    assert caminho2 == novo_caminho
    assert isinstance(msgs2, list)
    assert db_mod2 is False


def test_experimental_workspace_compilacao_com_erro_retorna_mensagens(
    tmp_path: Path,
) -> None:
    storage = CaminhosTemp(tmp_path / "appdata")
    raiz = storage.obter_caminho_croquis_experimentais() / "croqui_quebrado"
    (raiz / "database").mkdir(parents=True)
    # croqui.yaml inválido (sem 'id')
    (raiz / "database" / "croqui.yaml").write_text("nome: Sem ID\n", encoding="utf-8")

    ws = ExperimentalWorkspace(raiz)
    ws.obter_diario().gravar_comando_pendente({"classe": "CmdErro"})

    caminho, msgs, db_mod = ws.processar_renomeacao_e_compilacao(
        "croqui_quebrado", "croqui_quebrado", storage
    )
    assert caminho == raiz
    assert db_mod is False
    assert any("Erro" in m for m in msgs)
    assert not ws.obter_diario().tem_alteracoes_pendentes()


def test_local_repo_workspace_paths_e_processar_em_memoria(tmp_path: Path) -> None:
    storage = CaminhosTemp(tmp_path / "appdata")
    aresta_db = tmp_path / "aresta_db"
    croqui_dir = aresta_db / "database" / "meu_croqui"
    _criar_croqui_valido(croqui_dir, "meu_croqui")

    ws = LocalRepoWorkspace(croqui_dir, storage=storage)
    assert ws.obter_caminho_database() == croqui_dir
    assert ws.obter_caminho_compilado() == aresta_db / "generated" / "meu_croqui"
    assert ws.obter_pasta_servidor_celular() == aresta_db / "generated"
    assert ws.can_publish_pr() is False
    assert ws.obter_tag_titulo() == "[Local Mode]"

    diario = ws.obter_diario()
    assert diario is not None
    assert diario.pasta_croqui == storage.obter_caminho_diarios_locais() / "meu_croqui"
    diario.gravar_comando_pendente({"classe": "CmdLocalTeste"})

    resultado, msgs, db_mod = ws.processar_renomeacao_e_compilacao(
        "meu_croqui", "meu_croqui", storage
    )
    assert resultado == croqui_dir
    assert isinstance(msgs, list)
    assert db_mod is True  # gerou UID inicial
    assert (aresta_db / "generated" / "meu_croqui" / "compilado.binarypb").is_file()
    # O relatório STATUS_CROQUIS.md deve ter sido gerado em memória na raiz do repo
    status_md = aresta_db / "STATUS_CROQUIS.md"
    assert status_md.is_file()
    assert "meu_croqui" in status_md.read_text(encoding="utf-8")

    # Diário consolidado sem criar diario_salvo.bin no modo local
    assert not diario.tem_alteracoes_pendentes()
    assert not diario.caminho_salvo.exists()


def test_local_repo_workspace_renomeacao_git_real_e_falha(tmp_path: Path) -> None:
    storage = CaminhosTemp(tmp_path / "appdata")
    aresta_db = tmp_path / "aresta_db"
    croqui_dir = aresta_db / "database" / "meu_croqui"
    _criar_croqui_valido(croqui_dir, "meu_croqui")

    ws_inexistente = LocalRepoWorkspace(aresta_db / "database" / "nao_existe", storage=storage)
    assert ws_inexistente.obter_commit_base_sha() == ""

    ws_sem_git = LocalRepoWorkspace(croqui_dir, storage=storage)
    assert ws_sem_git.obter_commit_base_sha() == ""

    # Sem repositório git inicializado, git mv deve falhar e lançar RuntimeError
    with pytest.raises(RuntimeError, match="Falha ao renomear"):
        ws_sem_git.processar_renomeacao_e_compilacao("novo_croqui", "meu_croqui", storage)
    assert ws_sem_git.caminho_raiz == croqui_dir

    # Inicializa repositório git real para testar git mv e obter_commit_base_sha
    subprocess.run(["git", "init"], cwd=str(aresta_db), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "teste@aresta.local"],
        cwd=str(aresta_db),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Teste"],
        cwd=str(aresta_db),
        check=True,
    )
    # Cria também pasta compilada para exercitar git mv do compilado
    comp_dir = aresta_db / "generated" / "meu_croqui"
    comp_dir.mkdir(parents=True)
    (comp_dir / "placeholder.txt").write_text("ok", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=str(aresta_db), check=True)
    subprocess.run(
        ["git", "commit", "-m", "Inicial"],
        cwd=str(aresta_db),
        check=True,
        capture_output=True,
    )

    ws = LocalRepoWorkspace(croqui_dir, storage=storage)
    sha = ws.obter_commit_base_sha()
    assert len(sha) == 40

    # Atualiza o id no croqui.yaml antes de renomear
    _criar_croqui_valido(croqui_dir, "novo_croqui")
    novo_caminho, _msgs, _db_mod = ws.processar_renomeacao_e_compilacao(
        "novo_croqui", "meu_croqui", storage
    )
    assert novo_caminho == aresta_db / "database" / "novo_croqui"
    assert ws.caminho_raiz == novo_caminho
    assert (aresta_db / "generated" / "novo_croqui" / "compilado.binarypb").is_file()


def test_local_repo_workspace_compilacao_com_erro_retorna_mensagens(
    tmp_path: Path,
) -> None:
    storage = CaminhosTemp(tmp_path / "appdata")
    aresta_db = tmp_path / "aresta_db"
    croqui_dir = aresta_db / "database" / "croqui_invalido"
    croqui_dir.mkdir(parents=True)
    (croqui_dir / "croqui.yaml").write_text("yaml: [invalido", encoding="utf-8")

    ws = LocalRepoWorkspace(croqui_dir, storage=storage)
    ws.obter_diario().gravar_comando_pendente({"classe": "CmdErro"})

    caminho, msgs, db_mod = ws.processar_renomeacao_e_compilacao(
        "croqui_invalido", "croqui_invalido", storage
    )
    assert caminho == croqui_dir
    assert db_mod is False
    assert any("Erro" in m for m in msgs)
    assert not ws.obter_diario().tem_alteracoes_pendentes()


def test_capturar_saida_e_filtragem_de_mensagens(tmp_path: Path) -> None:
    from editor.core.workspace import _filtrar_mensagens

    with capturar_saida() as out:
        print("Isso é um print normal.")
        print("[br_mg_ferros_ferros] Compilado com sucesso.")
        print("  Gerando thumbnail: imagens/capa.webp -> thumbnails/br.webp")
        print("Aviso: ID duplicado.")
        print("Erro ao tentar fazer algo.")
        print("  Warning: isso falhou feio")

    msgs = _filtrar_mensagens(out.getvalue())
    assert "Aviso: ID duplicado." in msgs
    assert "Erro ao tentar fazer algo." in msgs
    assert "  Warning: isso falhou feio" in msgs
    assert "Isso é um print normal." not in msgs
    assert "[br_mg_ferros_ferros] Compilado com sucesso." not in msgs
