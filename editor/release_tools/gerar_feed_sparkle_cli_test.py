# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a CLI de geração do feed Sparkle (appcast.xml) macOS.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from editor.release_tools.gerar_feed_sparkle_cli import main


def test_gerar_feed_sparkle_cli_multi_arquitetura_sucesso(tmp_path: Path) -> None:
    """Valida geração do appcast.xml a partir de diretório contendo artefatos arm64 e intel."""
    dist_dir = tmp_path / "dist_macos"
    dist_dir.mkdir()
    dmg_arm = dist_dir / "EditorAresta-0.5.14-arm64.dmg"
    dmg_arm.write_bytes(b"ARM64_DMG_CONTENT")
    dmg_intel = dist_dir / "EditorAresta-0.5.14-intel.dmg"
    dmg_intel.write_bytes(b"INTEL_DMG_CONTENT")

    saida_xml = dist_dir / "appcast.xml"

    codigo = main(
        [
            "--versao",
            "0.5.14",
            "--diretorio-dist",
            str(dist_dir),
        ]
    )

    assert codigo == 0
    assert saida_xml.exists()
    conteudo = saida_xml.read_text(encoding="utf-8")
    assert "EditorAresta-0.5.14-arm64.dmg" in conteudo
    assert "EditorAresta-0.5.14-intel.dmg" in conteudo
    assert "<sparkle:hardwareRequirements>arm64</sparkle:hardwareRequirements>" in conteudo
    assert "<sparkle:hardwareRequirements>x86_64</sparkle:hardwareRequirements>" in conteudo


def test_gerar_feed_sparkle_cli_com_chave_privada_e_forcar_atualizacao(
    tmp_path: Path,
) -> None:
    """Valida assinatura com chave privada informada e inclusão de criticalUpdate."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "EditorAresta-1.0.0-arm64.dmg").write_bytes(b"ARM_DATA")

    saida_xml = tmp_path / "custom_feed.xml"

    with patch(
        "editor.release_tools.gerar_feed_sparkle_cli.assinar_arquivo_ed25519",
        return_value="CHAVE_ASSINADA_TESTE",
    ) as mock_assinar:
        codigo = main(
            [
                "--versao",
                "1.0.0",
                "--diretorio-dist",
                str(dist_dir),
                "--saida",
                str(saida_xml),
                "--chave-privada",
                "CHAVE_PRIVADA_MOCK",
                "--forcar-atualizacao",
            ]
        )

        assert codigo == 0
        mock_assinar.assert_called_once()
        conteudo = saida_xml.read_text(encoding="utf-8")
        assert 'sparkle:edSignature="CHAVE_ASSINADA_TESTE"' in conteudo
        assert "<sparkle:criticalUpdate" in conteudo


def test_gerar_feed_sparkle_cli_com_variaveis_de_ambiente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida consumo de variáveis de ambiente para chave e flag de atualização."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "EditorAresta-1.0.0-intel.dmg").write_bytes(b"INTEL_DATA")

    monkeypatch.setenv("SPARKLE_ED25519_PRIVATE_KEY", "CHAVE_ENV")
    monkeypatch.setenv("FORCAR_ATUALIZACAO", "false")

    with patch(
        "editor.release_tools.gerar_feed_sparkle_cli.assinar_arquivo_ed25519",
        return_value="SIG_ENV",
    ):
        codigo = main(
            [
                "--versao",
                "1.0.0",
                "--diretorio-dist",
                str(dist_dir),
            ]
        )

        assert codigo == 0
        xml = (dist_dir / "appcast.xml").read_text(encoding="utf-8")
        assert "SIG_ENV" in xml
        assert "<sparkle:criticalUpdate" not in xml


def test_gerar_feed_sparkle_cli_fallback_dmg_legado(tmp_path: Path) -> None:
    """Valida geração quando apenas o arquivo DMG legado sem sufixo de arquitetura existe."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "EditorAresta-1.0.0.dmg").write_bytes(b"LEGADO_DATA")

    codigo = main(
        [
            "--versao",
            "1.0.0",
            "--diretorio-dist",
            str(dist_dir),
        ]
    )

    assert codigo == 0
    xml = (dist_dir / "appcast.xml").read_text(encoding="utf-8")
    assert "EditorAresta-1.0.0.dmg" in xml
    assert "<sparkle:hardwareRequirements>" not in xml


def test_gerar_feed_sparkle_cli_argumentos_caminhos_explicitos(tmp_path: Path) -> None:
    """Valida fornecimento explícito dos caminhos para os arquivos .dmg."""
    dmg_arm = tmp_path / "custom_arm.dmg"
    dmg_arm.write_bytes(b"ARM")
    dmg_intel = tmp_path / "custom_intel.dmg"
    dmg_intel.write_bytes(b"INTEL")
    saida = tmp_path / "feed.xml"

    codigo = main(
        [
            "--versao",
            "2.0.0",
            "--dmg-arm64",
            str(dmg_arm),
            "--dmg-intel",
            str(dmg_intel),
            "--saida",
            str(saida),
        ]
    )

    assert codigo == 0
    assert saida.exists()
    conteudo = saida.read_text(encoding="utf-8")
    assert "custom_arm.dmg" in conteudo
    assert "custom_intel.dmg" in conteudo


def test_gerar_feed_sparkle_cli_sem_nenhum_dmg_lanca_erro(tmp_path: Path) -> None:
    """Valida erro quando nenhum artefato DMG correspondente é localizado."""
    vazio = tmp_path / "vazio"
    vazio.mkdir()

    with pytest.raises(FileNotFoundError, match="Nenhum arquivo DMG encontrado"):
        main(
            [
                "--versao",
                "1.0.0",
                "--diretorio-dist",
                str(vazio),
            ]
        )


def test_gerar_feed_sparkle_cli_execucao_modulo_principal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida execução direta do script via runpy (__main__)."""
    import runpy
    import sys

    dist_dir = tmp_path / "dist_macos"
    dist_dir.mkdir()
    (dist_dir / "EditorAresta-0.5.14-arm64.dmg").write_bytes(b"ARM_DATA")

    caminho_script = Path(__file__).parent / "gerar_feed_sparkle_cli.py"
    raiz_repo = str(caminho_script.resolve().parent.parent.parent)

    monkeypatch.setattr(
        "sys.argv",
        [
            "gerar_feed_sparkle_cli.py",
            "--versao",
            "0.5.14",
            "--diretorio-dist",
            str(dist_dir),
        ],
    )

    # Simula raiz ausente no sys.path inicial
    monkeypatch.setattr(
        sys,
        "path",
        [p for p in sys.path if p != raiz_repo],
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(caminho_script), run_name="__main__")

    assert exc_info.value.code == 0
    assert (dist_dir / "appcast.xml").exists()
