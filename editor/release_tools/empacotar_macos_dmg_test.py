# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a ferramenta de empacotamento, assinatura e notarização macOS (DMG).
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from editor.release_tools.empacotar_macos_dmg import (
    gerar_conteudo_info_plist,
    criar_estrutura_bundle_macos,
    assinar_bundle_macos,
    gerar_dmg_macos,
    notarizar_dmg_macos,
    empacotar_distribuicao_macos,
)


def test_gerar_conteudo_info_plist() -> None:
    """Valida as chaves obrigatórias no Info.plist para macOS e Sparkle."""
    plist = gerar_conteudo_info_plist(
        versao="0.4.0",
        identificador_bundle="com.arestaclimb.Editor",
        nome_executavel="EditorAresta",
    )

    assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in plist
    assert "<key>CFBundleExecutable</key>" in plist
    assert "<string>EditorAresta</string>" in plist
    assert "<key>CFBundleIdentifier</key>" in plist
    assert "<string>com.arestaclimb.Editor</string>" in plist
    assert "<key>CFBundleShortVersionString</key>" in plist
    assert "<string>0.4.0</string>" in plist
    assert "<key>SUFeedURL</key>" in plist
    assert "https://serving.arestaclimb.com/editor-macos/appcast.xml" in plist
    assert "<key>SUPublicEDKey</key>" in plist
    assert "<string>BZ+UB+PvZmLAVAKiAoUtFUrrJSBECPFIc2dzvvlVruY=</string>" in plist


def test_gerar_conteudo_info_plist_sem_chave_publica_sparkle() -> None:
    """Valida a omissão da SUPublicEDKey quando explicitamente desabilitada com None."""
    plist = gerar_conteudo_info_plist(
        versao="0.4.0",
        chave_publica_sparkle=None,
    )
    assert "<key>SUPublicEDKey</key>" not in plist


def test_gerar_conteudo_info_plist_com_chave_publica_sparkle() -> None:
    """Valida a inclusão da SUPublicEDKey customizada quando informada."""
    plist = gerar_conteudo_info_plist(
        versao="0.4.0",
        chave_publica_sparkle="CHAVE_PUBLICA_ED25519_BASE64",
    )
    assert "<key>SUPublicEDKey</key>" in plist
    assert "<string>CHAVE_PUBLICA_ED25519_BASE64</string>" in plist


def test_criar_estrutura_bundle_macos(tmp_path: Path) -> None:
    """Valida a montagem do bundle .app com Info.plist, binários e ícone."""
    dir_onedir = tmp_path / "EditorAresta_onedir"
    dir_onedir.mkdir()
    (dir_onedir / "EditorAresta").write_bytes(b"binario_executavel")
    (dir_onedir / "arquivo_dados.txt").write_text("dados", encoding="utf-8")

    caminho_icns = tmp_path / "logo.icns"
    caminho_icns.write_bytes(b"icns_bytes")

    dir_saida_app = tmp_path / "EditorAresta.app"

    app_criado = criar_estrutura_bundle_macos(
        diretorio_origem_onedir=dir_onedir,
        diretorio_destino_app=dir_saida_app,
        versao="0.4.0",
        caminho_icone_icns=caminho_icns,
    )

    assert app_criado.exists()
    assert (app_criado / "Contents" / "Info.plist").exists()
    assert (app_criado / "Contents" / "MacOS" / "EditorAresta").exists()
    assert (app_criado / "Contents" / "Resources" / "logo.icns").exists()


def test_assinar_bundle_macos_dry_run(tmp_path: Path) -> None:
    """Garante que em dry-run os comandos codesign sejam gerados sem invocar o SO."""
    dir_app = tmp_path / "EditorAresta.app"
    dir_app.mkdir(parents=True)
    (dir_app / "Contents").mkdir()
    (dir_app / "Contents" / "MacOS").mkdir()
    (dir_app / "Contents" / "MacOS" / "EditorAresta").write_bytes(b"bin")

    comandos = assinar_bundle_macos(
        caminho_app=dir_app,
        identidade_assinatura="Developer ID Application: Aresta Climb (ABC123XYZ)",
        dry_run=True,
    )

    assert len(comandos) > 0
    assert any("codesign" in cmd and "Developer ID Application" in cmd for cmd in comandos)


def test_assinar_bundle_macos_execucao_real(tmp_path: Path) -> None:
    """Valida a invocação de subprocess.run durante assinatura quando dry_run é False."""
    dir_app = tmp_path / "EditorAresta.app"
    dir_app.mkdir(parents=True)
    (dir_app / "Contents").mkdir()
    (dir_app / "Contents" / "MacOS").mkdir()
    (dir_app / "Contents" / "MacOS" / "EditorAresta").write_bytes(b"bin")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = assinar_bundle_macos(
            caminho_app=dir_app,
            identidade_assinatura="Developer ID",
            dry_run=False,
        )
        assert mock_run.call_count >= 1
        assert len(comandos) >= 1


def test_gerar_dmg_macos_dry_run(tmp_path: Path) -> None:
    """Valida a geração do comando hdiutil em dry-run."""
    dir_app = tmp_path / "EditorAresta.app"
    dir_app.mkdir()
    dmg_saida = tmp_path / "EditorAresta.dmg"

    comandos = gerar_dmg_macos(
        caminho_app=dir_app,
        caminho_saida_dmg=dmg_saida,
        nome_volume="Editor Aresta",
        dry_run=True,
    )

    assert len(comandos) == 1
    assert "hdiutil create" in comandos[0]
    assert "EditorAresta.dmg" in comandos[0]


def test_gerar_dmg_macos_execucao_real(tmp_path: Path) -> None:
    """Valida a execução de subprocess.run para geração do DMG."""
    dir_app = tmp_path / "EditorAresta.app"
    dir_app.mkdir()
    dmg_saida = tmp_path / "EditorAresta.dmg"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = gerar_dmg_macos(
            caminho_app=dir_app,
            caminho_saida_dmg=dmg_saida,
            dry_run=False,
        )
        assert mock_run.call_count == 1
        assert len(comandos) == 1


def test_notarizar_dmg_macos_dry_run(tmp_path: Path) -> None:
    """Valida os comandos de notarização (notarytool e stapler) em dry-run."""
    dmg = tmp_path / "EditorAresta.dmg"
    dmg.write_bytes(b"dmg")

    # Cenário com profile
    comandos_profile = notarizar_dmg_macos(
        caminho_dmg=dmg,
        profile="AC_NOTARY_PROFILE",
        dry_run=True,
    )
    assert any("notarytool submit" in c for c in comandos_profile)
    assert any("stapler staple" in c for c in comandos_profile)

    # Cenário com credenciais explícitas
    comandos_creds = notarizar_dmg_macos(
        caminho_dmg=dmg,
        apple_id="autor@aresta.com",
        app_password="senha-app-especifica",
        team_id="TEAM123",
        dry_run=True,
    )
    assert any("apple-id" in c for c in comandos_creds)


def test_notarizar_dmg_macos_execucao_real(tmp_path: Path) -> None:
    """Valida a execução de subprocess.run na notarização."""
    dmg = tmp_path / "EditorAresta.dmg"
    dmg.write_bytes(b"dmg")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = notarizar_dmg_macos(
            caminho_dmg=dmg,
            profile="AC_PROFILE",
            dry_run=False,
        )
        assert mock_run.call_count == 2
        assert len(comandos) == 2


def test_empacotar_distribuicao_macos_fluxo_completo(tmp_path: Path) -> None:
    """Valida o fluxo coordenado de empacotamento completo em dry-run."""
    dir_onedir = tmp_path / "onedir"
    dir_onedir.mkdir()
    (dir_onedir / "EditorAresta").write_bytes(b"bin")

    pasta_saida = tmp_path / "dist_macos"

    dmg_gerado = empacotar_distribuicao_macos(
        diretorio_onedir=dir_onedir,
        diretorio_saida=pasta_saida,
        versao="0.4.0",
        identidade_assinatura="Developer ID",
        notarizar=True,
        profile="MEU_PERFIL",
        dry_run=True,
    )

    assert dmg_gerado == pasta_saida / "EditorAresta-0.4.0.dmg"


def test_criar_estrutura_bundle_macos_sobrescreve_destino_e_copia_subpastas(tmp_path: Path) -> None:
    """Valida que diretório .app pré-existente é limpo e subpastas são copiadas."""
    dir_onedir = tmp_path / "onedir"
    dir_onedir.mkdir()
    (dir_onedir / "EditorAresta").write_bytes(b"bin")
    subpasta = dir_onedir / "recursos"
    subpasta.mkdir()
    (subpasta / "item.png").write_bytes(b"png")

    dir_app = tmp_path / "EditorAresta.app"
    dir_app.mkdir()
    (dir_app / "lixo.txt").write_bytes(b"lixo")

    criar_estrutura_bundle_macos(
        diretorio_origem_onedir=dir_onedir,
        diretorio_destino_app=dir_app,
        versao="0.4.0",
    )

    assert not (dir_app / "lixo.txt").exists()
    assert (dir_app / "Contents" / "MacOS" / "recursos" / "item.png").exists()


def test_assinar_bundle_macos_com_dylib_e_entitlements(tmp_path: Path) -> None:
    """Valida assinatura recursiva de .dylib e uso de entitlements."""
    dir_app = tmp_path / "EditorAresta.app"
    macos_dir = dir_app / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)
    (macos_dir / "libteste.dylib").write_bytes(b"dylib")
    (macos_dir / "libextra.so").write_bytes(b"so")

    entitlements = tmp_path / "entitlements.plist"
    entitlements.write_text("<plist></plist>", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = assinar_bundle_macos(
            caminho_app=dir_app,
            identidade_assinatura="Dev ID",
            caminho_entitlements=entitlements,
            dry_run=False,
        )
        assert any("--entitlements" in c for c in comandos)
        assert any("libteste.dylib" in c for c in comandos)
        assert any("libextra.so" in c for c in comandos)


def test_gerar_dmg_macos_remove_dmg_pre_existente(tmp_path: Path) -> None:
    """Valida remoção de DMG existente antes da nova geração."""
    dir_app = tmp_path / "EditorAresta.app"
    dir_app.mkdir()
    dmg_saida = tmp_path / "EditorAresta.dmg"
    dmg_saida.write_bytes(b"antigo")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        gerar_dmg_macos(
            caminho_app=dir_app,
            caminho_saida_dmg=dmg_saida,
            dry_run=False,
        )
        assert not dmg_saida.exists()


def test_criar_estrutura_bundle_macos_com_sparkle_framework(tmp_path: Path) -> None:
    """Valida a cópia do Sparkle.framework para Contents/Frameworks."""
    dir_onedir = tmp_path / "EditorAresta_onedir"
    dir_onedir.mkdir()
    (dir_onedir / "EditorAresta").write_bytes(b"bin")

    sparkle_dir = tmp_path / "Sparkle.framework"
    sparkle_dir.mkdir()
    (sparkle_dir / "Sparkle").write_bytes(b"sparkle_binary")

    dir_saida_app = tmp_path / "EditorAresta.app"

    criar_estrutura_bundle_macos(
        diretorio_origem_onedir=dir_onedir,
        diretorio_destino_app=dir_saida_app,
        versao="0.4.0",
        caminho_sparkle_framework=sparkle_dir,
    )

    frameworks_dir = dir_saida_app / "Contents" / "Frameworks" / "Sparkle.framework"
    assert frameworks_dir.exists()
    assert (frameworks_dir / "Sparkle").exists()

    # Chama novamente com destino já existente para cobrir a remoção prévia
    criar_estrutura_bundle_macos(
        diretorio_origem_onedir=dir_onedir,
        diretorio_destino_app=dir_saida_app,
        versao="0.4.0",
        caminho_sparkle_framework=sparkle_dir,
    )
    assert frameworks_dir.exists()


def test_assinar_bundle_macos_com_sparkle_framework(tmp_path: Path) -> None:
    """Valida assinatura explícita do Sparkle.framework antes do bundle principal."""
    dir_app = tmp_path / "EditorAresta.app"
    frameworks_dir = dir_app / "Contents" / "Frameworks" / "Sparkle.framework"
    frameworks_dir.mkdir(parents=True)
    (frameworks_dir / "Autoupdate").write_bytes(b"autoupdate_bin")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = assinar_bundle_macos(
            caminho_app=dir_app,
            identidade_assinatura="Dev ID",
            dry_run=False,
        )
        assert any("Sparkle.framework" in c for c in comandos)


