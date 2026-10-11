# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o utilitário de linha de comando de bootstrap e publicação
do repositório Flatpak no Cloudflare R2 (editor.release_tools.publicar_flatpak_cli).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from editor.release_tools.publicar_flatpak_cli import (
    executar_bootstrap,
    executar_publicacao,
    main,
)


def test_executar_bootstrap_repositorio_remoto_existente(tmp_path: Path) -> None:
    """Quando o repositório remoto existe, deve configurar o remoto e puxar o commit anterior."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    with patch(
        "editor.release_tools.publicar_flatpak_cli.verificar_estado_repositorio_remoto",
        return_value=True,
    ), patch("subprocess.run") as mock_run:
        executar_bootstrap(repo_dir=diretorio_repo)

        assert mock_run.call_count == 2
        primeira_chamada = mock_run.call_args_list[0][0][0]
        segunda_chamada = mock_run.call_args_list[1][0][0]

        assert "remote" in primeira_chamada and "add" in primeira_chamada
        assert "pull" in segunda_chamada and "--mirror" in segunda_chamada


def test_executar_bootstrap_repositorio_remoto_novo(tmp_path: Path) -> None:
    """Quando o repositório remoto não existe (bootstrap), inicializa um repositório limpo."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    with patch(
        "editor.release_tools.publicar_flatpak_cli.verificar_estado_repositorio_remoto",
        return_value=False,
    ), patch("subprocess.run") as mock_run:
        executar_bootstrap(repo_dir=diretorio_repo)

        assert mock_run.call_count == 1
        chamada = mock_run.call_args_list[0][0][0]
        assert "init" in chamada and "--mode=archive-z2" in chamada


def test_executar_publicacao_sucesso(tmp_path: Path) -> None:
    """Executa o ciclo completo de sincronização, metadados e purga de cache com sucesso."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()
    diretorio_meta = tmp_path / "dist_flatpak_meta"

    mock_publicador = MagicMock()
    mock_publicador.zone_id = "fake_zone"
    mock_publicador.api_token = "fake_token"
    mock_publicador.sincronizar_diretorio_ostree.return_value = ["flatpak/repo/summary"]
    mock_publicador.publicar_metadados.return_value = {"version.json": diretorio_meta / "version.json"}
    mock_publicador.obter_urls_purga.return_value = ["https://serving.arestaclimb.com/flatpak/version.json"]

    executar_publicacao(
        versao="0.5.0",
        repo_dir=diretorio_repo,
        chave_gpg_base64="MOCK_GPG_BASE64",
        diretorio_meta=diretorio_meta,
        publicador=mock_publicador,
    )

    mock_publicador.sincronizar_diretorio_ostree.assert_called_once_with(diretorio_repo)
    mock_publicador.publicar_metadados.assert_called_once_with(
        versao="0.5.0",
        chave_gpg_base64="MOCK_GPG_BASE64",
        diretorio_saida=diretorio_meta,
        obrigatoria=True,
    )
    mock_publicador.purgar_cache.assert_called_once_with(
        ["https://serving.arestaclimb.com/flatpak/version.json"]
    )


def test_executar_publicacao_sem_chave_gpg_falha(tmp_path: Path) -> None:
    """Se a chave pública GPG estiver vazia, deve levantar ValueError impedindo publicação desprotegida."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    with pytest.raises(ValueError, match="chave pública GPG"):
        executar_publicacao(
            versao="0.5.0",
            repo_dir=diretorio_repo,
            chave_gpg_base64="",
            publicador=MagicMock(),
        )


def test_executar_publicacao_sem_credenciais_cloudflare(tmp_path: Path) -> None:
    """Quando credenciais da Cloudflare não estiverem configuradas, não chama purgar_cache."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    mock_publicador = MagicMock()
    mock_publicador.zone_id = None
    mock_publicador.api_token = None

    executar_publicacao(
        versao="0.5.0",
        repo_dir=diretorio_repo,
        chave_gpg_base64="MOCK_GPG_BASE64",
        publicador=mock_publicador,
    )

    mock_publicador.sincronizar_diretorio_ostree.assert_called_once()
    mock_publicador.publicar_metadados.assert_called_once()
    mock_publicador.purgar_cache.assert_not_called()


def test_main_cli_bootstrap(tmp_path: Path) -> None:
    """Testa invocação do comando 'bootstrap' via linha de comando."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    with patch("editor.release_tools.publicar_flatpak_cli.executar_bootstrap") as mock_boot:
        codigo = main(["bootstrap", "--repo-dir", str(diretorio_repo)])
        assert codigo == 0
        mock_boot.assert_called_once()


def test_main_cli_publicar(tmp_path: Path) -> None:
    """Testa invocação do comando 'publicar' via linha de comando."""
    diretorio_repo = tmp_path / "repo"
    diretorio_repo.mkdir()

    with patch("editor.release_tools.publicar_flatpak_cli.executar_publicacao") as mock_pub:
        codigo = main([
            "publicar",
            "--versao", "0.5.0",
            "--repo-dir", str(diretorio_repo),
            "--chave-gpg-b64", "MOCK_GPG",
        ])
        assert codigo == 0
        mock_pub.assert_called_once()


def test_main_cli_sem_subcomando() -> None:
    """Sem subcomando deve exibir ajuda e retornar código de erro."""
    codigo = main([])
    assert codigo != 0
