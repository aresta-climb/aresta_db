# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a CLI de publicação do canal macOS no Cloudflare R2.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from editor.release_tools.publicar_macos_cli import main


def test_publicar_macos_cli_argumentos_padrao(tmp_path: Path) -> None:
    """Valida execução com argumentos padrão deduzidos a partir do diretório dist."""
    dist_dir = tmp_path / "dist_macos"
    dist_dir.mkdir()
    dmg = dist_dir / "EditorAresta-0.5.13.dmg"
    dmg.write_bytes(b"DMG")
    appcast = dist_dir / "appcast.xml"
    appcast.write_text("<xml/>", encoding="utf-8")

    with patch("editor.release_tools.publicar_macos_cli.PublicadorR2MacOS") as mock_pub_cls:
        instancia = MagicMock()
        mock_pub_cls.return_value = instancia

        codigo = main(
            [
                "--versao",
                "0.5.13",
                "--diretorio-dist",
                str(dist_dir),
            ]
        )

        assert codigo == 0
        instancia.publicar_e_purgar.assert_called_once_with(
            versao="0.5.13",
            caminho_dmg=dmg,
            caminho_appcast=appcast,
        )


def test_publicar_macos_cli_caminhos_explicitados(tmp_path: Path) -> None:
    """Valida execução com caminhos explícitos para DMG e appcast."""
    dmg = tmp_path / "custom.dmg"
    dmg.write_bytes(b"DMG")
    appcast = tmp_path / "custom.xml"
    appcast.write_text("<xml/>", encoding="utf-8")

    with patch("editor.release_tools.publicar_macos_cli.PublicadorR2MacOS") as mock_pub_cls:
        instancia = MagicMock()
        mock_pub_cls.return_value = instancia

        codigo = main(
            [
                "--versao",
                "0.5.13",
                "--dmg",
                str(dmg),
                "--appcast",
                str(appcast),
            ]
        )

        assert codigo == 0
        instancia.publicar_e_purgar.assert_called_once_with(
            versao="0.5.13",
            caminho_dmg=dmg,
            caminho_appcast=appcast,
        )


def test_publicar_macos_cli_sem_versao() -> None:
    """Valida erro quando --versao não é informada."""
    with pytest.raises(SystemExit):
        main([])


def test_publicar_macos_cli_execucao_modulo_principal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida execução direta do script via python -m ou runpy como __main__."""
    import runpy
    import sys

    caminho_script = Path(__file__).parent / "publicar_macos_cli.py"
    raiz_repo = str(caminho_script.resolve().parent.parent.parent)

    monkeypatch.setattr(
        "sys.argv",
        ["publicar_macos_cli.py", "--versao", "0.5.13"],
    )

    # Simula situação onde a raiz do repo não está presente inicialmente no sys.path
    monkeypatch.setattr(
        sys,
        "path",
        [p for p in sys.path if p != raiz_repo],
    )

    with patch("editor.release_tools.publicador_r2_macos.PublicadorR2MacOS") as mock_pub_cls:
        instancia = MagicMock()
        mock_pub_cls.return_value = instancia

        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(caminho_script), run_name="__main__")

        assert exc_info.value.code == 0
        instancia.publicar_e_purgar.assert_called_once()
