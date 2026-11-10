# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import random
from pathlib import Path

import pygit2

from editor.caos.fabrica_dataset_caos import (
    DICT_ENTRADAS_FUZZ,
    FabricaDatasetCaos,
    gerar_texto_fuzz,
)
from editor.core.sync import GerenciadorSincronizacao
from editor.core.workspace import ExperimentalWorkspace


def test_criar_croqui_normal_e_toxico_carregam_no_workspace_e_compilam(
    tmp_path: Path,
) -> None:
    for variante in ("normal", "toxico"):
        pasta_exp = tmp_path / f"exp_{variante}"
        pasta_db = pasta_exp / "database"
        if variante == "normal":
            proto = FabricaDatasetCaos.criar_croqui_normal(pasta_db)
        else:
            proto = FabricaDatasetCaos.criar_croqui_toxico(pasta_db)

        assert proto.id != ""
        assert (pasta_db / "croqui.yaml").is_file()
        assert (pasta_db / "curadoria_betas.yaml").is_file()
        assert any((pasta_db / "imagens").glob("*.png"))

        ws = ExperimentalWorkspace(pasta_exp)
        assert ws.obter_id_croqui_atual() == proto.id


def test_inicializar_ambiente_instalacao_caos_cria_git_upstream_clonavel(
    tmp_path: Path,
) -> None:
    ambiente_normal = FabricaDatasetCaos.inicializar_ambiente_instalacao_caos(
        tmp_path / "inst_normal", dataset="normal"
    )
    assert ambiente_normal.id_croqui_experimental == "br_mg_ouro_preto_normal"
    assert (ambiente_normal.caminho_croqui_experimental / "database" / "croqui.yaml").is_file()

    ambiente = FabricaDatasetCaos.inicializar_ambiente_instalacao_caos(
        tmp_path / "inst_toxico", dataset="toxico"
    )

    assert ambiente.diretorio_dados.is_dir()
    assert Path(ambiente.url_git_upstream).is_dir()
    assert (ambiente.caminho_croqui_experimental / "database" / "croqui.yaml").is_file()

    # Deve ser possível clonar e dar fetch do repositório upstream local 100% offline
    destino_clone = ambiente.storage.obter_caminho_base_repo()
    sync = GerenciadorSincronizacao(destino_clone, url_upstream=ambiente.url_git_upstream)
    sync.clonar(sync.obter_url_clone())
    assert (destino_clone / "database" / "br_mg_ouro_preto_normal" / "croqui.yaml").is_file()
    assert (destino_clone / "database" / "br_sp_caos_toxico" / "croqui.yaml").is_file()

    repo_clonado = pygit2.Repository(str(destino_clone))
    assert not repo_clonado.is_empty


def test_gerador_texto_fuzz_deterministico_por_seed() -> None:
    assert len(DICT_ENTRADAS_FUZZ) >= 10
    rng_a = random.Random(12345)
    rng_b = random.Random(12345)

    sequencia_a = [gerar_texto_fuzz(rng_a) for _ in range(15)]
    sequencia_b = [gerar_texto_fuzz(rng_b) for _ in range(15)]
    assert sequencia_a == sequencia_b
