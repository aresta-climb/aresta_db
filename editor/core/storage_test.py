# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from pathlib import Path

import pytest

from editor.core.storage import GerenciadorCaminhos, obter_diretorio_base_app


def test_obter_diretorio_base_app_prioriza_variavel_ambiente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    diretorio_isolado = tmp_path / "instalacao_isolada"
    monkeypatch.setenv("ARESTA_DIRETORIO_DADOS", str(diretorio_isolado))

    caminho = obter_diretorio_base_app()

    assert caminho == diretorio_isolado


def test_obter_diretorio_base_app_delega_para_plataforma_quando_sem_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ARESTA_DIRETORIO_DADOS", raising=False)

    caminho = obter_diretorio_base_app()

    assert isinstance(caminho, Path)
    assert str(caminho) != ""


def test_gerenciador_caminhos_com_diretorio_base_explicito_isola_todas_as_pastas(
    tmp_path: Path,
) -> None:
    base = tmp_path / "dados_editor"
    gerenciador = GerenciadorCaminhos(diretorio_base=base)

    assert gerenciador.obter_diretorio_base() == base
    assert gerenciador.obter_caminho_base_repo() == base / "aresta_db"
    assert gerenciador.obter_caminho_croquis_experimentais() == base / "croquis"
    assert gerenciador.obter_caminho_diarios_locais() == base / "diarios_locais"
    assert gerenciador.obter_caminho_lixeira() == base / ".trash_interna"


def test_gerenciador_caminhos_sem_argumento_respeita_variavel_ambiente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_env = tmp_path / "via_env"
    monkeypatch.setenv("ARESTA_DIRETORIO_DADOS", str(base_env))

    gerenciador = GerenciadorCaminhos()

    assert gerenciador.obter_diretorio_base() == base_env
    assert gerenciador.obter_caminho_base_repo() == base_env / "aresta_db"


def test_inicializar_diretorios_cria_estrutura_real_no_disco(tmp_path: Path) -> None:
    base = tmp_path / "instalacao_nova"
    gerenciador = GerenciadorCaminhos(diretorio_base=base)

    gerenciador.inicializar_diretorios()

    assert base.is_dir()
    assert (base / "aresta_db").is_dir()
    assert (base / "croquis").is_dir()
    assert (base / "diarios_locais").is_dir()
    assert (base / ".trash_interna").is_dir()


def test_obter_caminho_recurso_interno_modo_desenvolvimento(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.delenv("ARESTA_CANAL", raising=False)

    gerenciador = GerenciadorCaminhos()
    caminho = gerenciador.obter_caminho_recurso_interno("recursos/logo_splash.png")

    from editor.core import storage

    esperado = Path(storage.__file__).resolve().parent.parent / "recursos/logo_splash.png"
    assert caminho == esperado


def test_obter_caminho_recurso_interno_empacotado_pyinstaller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_MEI12345"), raising=False)
    monkeypatch.delenv("ARESTA_CANAL", raising=False)

    gerenciador = GerenciadorCaminhos()
    caminho = gerenciador.obter_caminho_recurso_interno("recursos/logo_splash.png")

    assert caminho == tmp_path / "_MEI12345" / "recursos/logo_splash.png"


def test_obter_caminho_recurso_interno_canal_beta_prioriza_recurso_existente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARESTA_CANAL", "beta")

    gerenciador = GerenciadorCaminhos()
    caminho = gerenciador.obter_caminho_recurso_interno("recursos/logo_app.png")

    assert "recursos_beta" in str(caminho).replace("\\", "/")
    assert caminho.name == "logo_app.png"


def test_obter_caminho_recurso_interno_canal_beta_faz_fallback_quando_ausente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setenv("ARESTA_CANAL", "beta")
    assert os.environ.get("ARESTA_CANAL") == "beta"

    gerenciador = GerenciadorCaminhos()
    caminho = gerenciador.obter_caminho_recurso_interno("recursos/arquivo_inexistente_beta.png")

    from editor.core import storage

    esperado = (
        Path(storage.__file__).resolve().parent.parent / "recursos/arquivo_inexistente_beta.png"
    )
    assert caminho == esperado

