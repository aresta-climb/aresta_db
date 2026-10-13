# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a ferramenta de empacotamento, assinatura e notarização macOS (DMG).
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from editor.release_tools.empacotar_macos_dmg import (
    assinar_bundle_macos,
    criar_estrutura_bundle_macos,
    eh_binario_mach_o,
    empacotar_distribuicao_macos,
    gerar_conteudo_info_plist,
    gerar_dmg_macos,
    notarizar_dmg_macos,
    precompilar_scripts_para_bytecode,
    sanitizar_bundle_para_codesign,
)


def test_gerar_conteudo_info_plist() -> None:
    """Valida as chaves obrigatórias no Info.plist para macOS e Sparkle."""
    plist = gerar_conteudo_info_plist(
        versao="0.4.0",
        identificador_bundle="com.arestaclimb.Editor",
        nome_executavel="EditorAresta",
    )

    assert '<?xml version="1.0" encoding="UTF-8"?>' in plist
    assert "<key>CFBundleExecutable</key>" in plist
    assert "<string>EditorAresta</string>" in plist
    assert "<key>CFBundleIdentifier</key>" in plist
    assert "<string>com.arestaclimb.Editor</string>" in plist
    assert "<key>CFBundleShortVersionString</key>" in plist
    assert "<string>0.4.0</string>" in plist
    assert "<key>SUFeedURL</key>" in plist
    assert "https://serving.arestaclimb.com/editor-macos/appcast.xml" in plist
    assert "<key>SUEnableAutomaticChecks</key>" in plist
    assert "<key>SUAutomaticallyUpdate</key>" in plist
    assert "<key>SUScheduledCheckInterval</key>" in plist
    assert "<integer>3600</integer>" in plist
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


def test_gerar_conteudo_info_plist_sem_atualizacao_automatica() -> None:
    """Valida a omissão de SUAutomaticallyUpdate quando atualizar_automaticamente=False."""
    plist = gerar_conteudo_info_plist(
        versao="0.4.0",
        atualizar_automaticamente=False,
        intervalo_checagem_segundos=7200,
    )
    assert "<key>SUAutomaticallyUpdate</key>" not in plist
    assert "<key>SUScheduledCheckInterval</key>" in plist
    assert "<integer>7200</integer>" in plist


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
    (macos_dir / "EditorAresta").write_bytes(b"bin")
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


def test_sanitizar_bundle_para_codesign_remove_dist_info_egg_info_e_pycache(tmp_path: Path) -> None:
    """Valida se a sanitização do bundle expurga pastas com ponto (.dist-info, .egg-info) e arquivos residuais."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    internal_dir = macos_dir / "_internal"
    internal_dir.mkdir(parents=True)

    # Cria arquivo executável legítimo
    (macos_dir / "EditorAresta").write_bytes(b"bin")

    # Cria pastas de metadados do pip que causam erro no codesign
    dist_info = internal_dir / "websockets-17.2.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("info", encoding="utf-8")

    egg_info = internal_dir / "modulo.egg-info"
    egg_info.mkdir()
    (egg_info / "PKG-INFO").write_text("info", encoding="utf-8")

    pycache = internal_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "cache.pyc").write_bytes(b"pyc")

    ds_store = macos_dir / ".DS_Store"
    ds_store.write_bytes(b"ds_store")

    removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)

    assert not dist_info.exists()
    assert not egg_info.exists()
    assert not pycache.exists()
    assert not ds_store.exists()
    assert (macos_dir / "EditorAresta").exists()
    assert len(removidos) >= 4


def test_sanitizar_bundle_para_codesign_dry_run_nao_deleta_arquivos(tmp_path: Path) -> None:
    """Valida que em modo dry_run a sanitização identifica os itens sem removê-los do disco."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)

    dist_info = macos_dir / "pacote-1.0.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("info", encoding="utf-8")

    removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=True)

    assert dist_info.exists()
    assert any("pacote-1.0.0.dist-info" in str(r) for r in removidos)


def test_sanitizar_bundle_para_codesign_executa_xattr_no_darwin(tmp_path: Path) -> None:
    """Valida chamada ao utilitário xattr -cr no macOS."""
    app_dir = tmp_path / "EditorAresta.app"
    app_dir.mkdir()

    with patch("sys.platform", "darwin"), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        sanitizar_bundle_para_codesign(app_dir, dry_run=False)
        assert mock_run.call_count == 1
        assert "xattr" in mock_run.call_args[0][0]


def test_sanitizar_bundle_para_codesign_ignora_ausencia_xattr(tmp_path: Path) -> None:
    """Valida tolerância graciosa caso o utilitário xattr não exista no ambiente."""
    app_dir = tmp_path / "EditorAresta.app"
    app_dir.mkdir()

    with (
        patch("sys.platform", "darwin"),
        patch("subprocess.run", side_effect=FileNotFoundError("xattr missing")),
    ):
        removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)
        assert isinstance(removidos, list)


def test_criar_estrutura_bundle_macos_sanitiza_subcomponentes_automaticamente(
    tmp_path: Path,
) -> None:
    """Valida que criar_estrutura_bundle_macos elimina metadados .dist-info ao montar o bundle."""
    dir_onedir = tmp_path / "onedir"
    dir_onedir.mkdir()
    (dir_onedir / "EditorAresta").write_bytes(b"bin")

    # Simula pasta .dist-info vinda do PyInstaller onedir
    internal_onedir = dir_onedir / "_internal"
    internal_onedir.mkdir()
    dist_info = internal_onedir / "websockets-17.2.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("info", encoding="utf-8")

    dir_app = tmp_path / "EditorAresta.app"

    criar_estrutura_bundle_macos(
        diretorio_origem_onedir=dir_onedir,
        diretorio_destino_app=dir_app,
        versao="0.4.0",
    )

    app_dist_info = dir_app / "Contents" / "MacOS" / "_internal" / "websockets-17.2.dist-info"
    assert not app_dist_info.exists()
    assert (dir_app / "Contents" / "MacOS" / "EditorAresta").exists()


def test_sanitizar_bundle_para_codesign_caminho_inexistente_retorna_vazio(tmp_path: Path) -> None:
    """Valida retorno de lista vazia ao sanitizar caminho inexistente."""
    caminho_inexistente = tmp_path / "NaoExiste.app"
    assert sanitizar_bundle_para_codesign(caminho_inexistente) == []


def test_sanitizar_bundle_para_codesign_remove_arquivos_de_teste_e_pasta_tests(
    tmp_path: Path,
) -> None:
    """Valida que arquivos de teste (*_test.py, conftest.py) e pastas tests são expurgados do bundle."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    resources_dir = app_dir / "Contents" / "Resources"
    internal_dir = macos_dir / "_internal"
    migracoes_dir = internal_dir / "migracoes"
    tests_dir = internal_dir / "tests"
    migracoes_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    arquivo_prod = migracoes_dir / "0005_migrar_uids_e_rotulos.py"
    arquivo_prod.write_text("print('migracao')", encoding="utf-8")

    arquivo_teste = migracoes_dir / "0005_migrar_uids_e_rotulos_test.py"
    arquivo_teste.write_text("def test_migracao(): pass", encoding="utf-8")

    conftest = internal_dir / "conftest.py"
    conftest.write_text("# conftest", encoding="utf-8")

    teste_dummy = tests_dir / "test_modulo.py"
    teste_dummy.write_text("def test(): pass", encoding="utf-8")

    removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)

    # A pasta migracoes deve ser movida para Contents/Resources/migracoes com seus arquivos .py de produção
    assert not migracoes_dir.exists()
    assert (resources_dir / "migracoes" / "0005_migrar_uids_e_rotulos.py").exists()
    assert not (resources_dir / "migracoes" / "0005_migrar_uids_e_rotulos_test.py").exists()
    assert not arquivo_teste.exists()
    assert not conftest.exists()
    assert not tests_dir.exists()
    assert any("0005_migrar_uids_e_rotulos_test.py" in str(r) for r in removidos)
    assert any("conftest.py" in str(r) for r in removidos)


def test_sanitizar_bundle_para_codesign_remove_permissao_execucao_de_arquivos_comuns(
    tmp_path: Path,
) -> None:
    """Valida que arquivos não-binários perdem o bit executável (+x) para prevenir erro 'code object is not signed at all'."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    internal_dir = macos_dir / "_internal"
    internal_dir.mkdir(parents=True)

    arquivo_txt = internal_dir / "dados.txt"
    arquivo_txt.write_text("dados", encoding="utf-8")

    executavel_principal = macos_dir / "EditorAresta"
    executavel_principal.write_bytes(b"binario_mach_o")

    # Mocka st_mode com bit executável ativo (0o755) em arquivos comuns para cobrir o branch de remoção do bit
    stat_real = Path.stat
    mock_stat = MagicMock(st_mode=0o100755)

    def mock_stat_fn(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self.name == "dados.txt":
            return mock_stat
        return stat_real(self, *args, **kwargs)

    with (
        patch.object(Path, "stat", mock_stat_fn),
        patch.object(Path, "chmod") as mock_chmod,
    ):
        sanitizar_bundle_para_codesign(app_dir, dry_run=False)
        assert mock_chmod.call_count >= 1

    # Cobre também a captura defensiva de OSError no chmod
    with (
        patch.object(Path, "stat", mock_stat_fn),
        patch.object(Path, "chmod", side_effect=OSError("Permissao negada")),
    ):
        sanitizar_bundle_para_codesign(app_dir, dry_run=False)


def test_assinar_bundle_macos_assina_executavel_principal_antes_do_bundle(tmp_path: Path) -> None:
    """Valida que o executável principal em Contents/MacOS é assinado individualmente antes do bundle raiz."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)
    (macos_dir / "EditorAresta").write_bytes(b"binario_executavel")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = assinar_bundle_macos(
            caminho_app=app_dir,
            identidade_assinatura="Developer ID",
            dry_run=False,
        )

        # Deve haver comando para o executável principal e outro para o .app raiz
        cmd_executavel = next((c for c in comandos if c.endswith("EditorAresta")), None)
        cmd_app = next((c for c in comandos if c.endswith("EditorAresta.app")), None)

        assert cmd_executavel is not None, (
            "Executável principal Contents/MacOS/EditorAresta deve ser assinado."
        )
        assert cmd_app is not None, "Bundle EditorAresta.app raiz deve ser assinado."

        idx_executavel = comandos.index(cmd_executavel)
        idx_app = comandos.index(cmd_app)
        assert idx_executavel < idx_app, (
            "O executável principal deve ser assinado ANTES do bundle pai."
        )


def test_eh_binario_mach_o(tmp_path: Path) -> None:
    """Valida identificação de binários Mach-O por assinatura magic bytes de 4 bytes."""
    arq_macho_64 = tmp_path / "bin_macho_64"
    arq_macho_64.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 20)

    arq_macho_fat = tmp_path / "bin_macho_fat"
    arq_macho_fat.write_bytes(b"\xca\xfe\xba\xbe" + b"\x00" * 20)

    arq_texto = tmp_path / "script.py"
    arq_texto.write_text("print(1)", encoding="utf-8")

    arq_curto = tmp_path / "curto"
    arq_curto.write_bytes(b"\x01\x02")

    pasta = tmp_path / "subpasta"
    pasta.mkdir()

    assert eh_binario_mach_o(arq_macho_64) is True
    assert eh_binario_mach_o(arq_macho_fat) is True
    assert eh_binario_mach_o(arq_texto) is False
    assert eh_binario_mach_o(arq_curto) is False
    assert eh_binario_mach_o(pasta) is False
    assert eh_binario_mach_o(tmp_path / "inexistente") is False


def test_sanitizar_bundle_para_codesign_move_migracoes_e_preserva_fontes_py(
    tmp_path: Path,
) -> None:
    """Valida que a pasta migracoes é movida de Contents/MacOS/_internal para Contents/Resources preservando os arquivos .py."""
    app_dir = tmp_path / "EditorAresta.app"
    migracoes_macos = app_dir / "Contents" / "MacOS" / "_internal" / "migracoes"
    migracoes_macos.mkdir(parents=True)

    script_migracao = migracoes_macos / "0003_migrar_mapas_gerais.py"
    script_migracao.write_text("MIGRATION_ID = 3\ndef migrar(c): pass\n", encoding="utf-8")

    removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)

    assert not migracoes_macos.exists(), "migracoes não pode ficar em Contents/MacOS/_internal"
    destino_resources = (
        app_dir / "Contents" / "Resources" / "migracoes" / "0003_migrar_mapas_gerais.py"
    )
    destino_resources_pyc = (
        app_dir / "Contents" / "Resources" / "migracoes" / "0003_migrar_mapas_gerais.pyc"
    )
    assert destino_resources.exists(), (
        "O script .py original deve ser preservado em Contents/Resources/migracoes"
    )
    assert destino_resources_pyc.exists(), (
        "O bytecode .pyc deve ser gerado e preservado ao lado do fonte .py"
    )
    assert "MIGRATION_ID = 3" in destino_resources.read_text(encoding="utf-8")
    assert any("migracoes" in str(r) for r in removidos)


def test_precompilar_scripts_para_bytecode_sucesso(tmp_path: Path) -> None:
    """Valida que scripts .py são compilados para .pyc preservando os fontes e ignorando testes."""
    pasta = tmp_path / "scripts"
    pasta.mkdir()

    script_prod = pasta / "0001_migracao.py"
    script_prod.write_text("def migrar(): pass\n", encoding="utf-8")

    script_teste = pasta / "0001_migracao_test.py"
    script_teste.write_text("def test_migrar(): pass\n", encoding="utf-8")

    compilados = precompilar_scripts_para_bytecode(pasta)

    assert (pasta / "0001_migracao.py").exists()
    assert (pasta / "0001_migracao.pyc").exists()
    assert not (pasta / "0001_migracao_test.pyc").exists()
    assert (pasta / "0001_migracao.pyc") in compilados


def test_precompilar_scripts_para_bytecode_diretorio_inexistente(tmp_path: Path) -> None:
    """Valida retorno de lista vazia para diretório inexistente."""
    pasta_inexistente = tmp_path / "inexistente"
    assert precompilar_scripts_para_bytecode(pasta_inexistente) == []


def test_precompilar_scripts_para_bytecode_trata_erros(tmp_path: Path) -> None:
    """Valida tratamento resiliente para PyCompileError ou OSError."""
    import py_compile

    pasta = tmp_path / "scripts"
    pasta.mkdir()
    script = pasta / "erro.py"
    script.write_text("codigo", encoding="utf-8")

    with patch(
        "py_compile.compile",
        side_effect=py_compile.PyCompileError(SyntaxError, SyntaxError("Erro"), "erro.py"),
    ):
        assert precompilar_scripts_para_bytecode(pasta) == []

    with patch("py_compile.compile", side_effect=OSError("Permissao negada")):
        assert precompilar_scripts_para_bytecode(pasta) == []


def test_sanitizar_bundle_para_codesign_remove_scripts_soltos_em_contents_macos(
    tmp_path: Path,
) -> None:
    """Valida que scripts .py e .pyc residuais soltos em Contents/MacOS são removidos para não quebrar o codesign."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)

    script_solto = macos_dir / "script_residual.py"
    script_solto.write_text("print(1)", encoding="utf-8")
    pyc_solto = macos_dir / "bytecode_residual.pyc"
    pyc_solto.write_bytes(b"pyc")

    removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)

    assert not script_solto.exists()
    assert not pyc_solto.exists()
    assert any("script_residual.py" in str(r) for r in removidos)
    assert any("bytecode_residual.pyc" in str(r) for r in removidos)


def test_sanitizar_bundle_para_codesign_remove_arquivos_ico_e_artefatos_windows(
    tmp_path: Path,
) -> None:
    """Valida que arquivos .ico, .exe, .bat e .cmd do ecossistema Windows são removidos do bundle macOS."""
    app_dir = tmp_path / "EditorAresta.app"
    internal_dir = app_dir / "Contents" / "MacOS" / "_internal"
    recursos_dir = internal_dir / "recursos"
    recursos_dir.mkdir(parents=True)

    ico_raiz = internal_dir / "logo.ico"
    ico_raiz.write_bytes(b"\x00\x00\x01\x00")
    ico_recursos = recursos_dir / "logo.ico"
    ico_recursos.write_bytes(b"\x00\x00\x01\x00")
    bat_arquivo = internal_dir / "script.bat"
    bat_arquivo.write_text("@echo off", encoding="utf-8")
    png_recursos = recursos_dir / "logo_app.png"
    png_recursos.write_bytes(b"\x89PNG")

    removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)

    assert not ico_raiz.exists()
    assert not ico_recursos.exists()
    assert not bat_arquivo.exists()
    assert png_recursos.exists()
    assert any("logo.ico" in str(r) for r in removidos)
    assert any("script.bat" in str(r) for r in removidos)


def test_criar_estrutura_bundle_macos_move_migracoes_para_contents_resources(
    tmp_path: Path,
) -> None:
    """Valida que criar_estrutura_bundle_macos posiciona a pasta migracoes em Contents/Resources."""
    dir_onedir = tmp_path / "EditorAresta_onedir"
    dir_onedir.mkdir()
    (dir_onedir / "EditorAresta").write_bytes(b"binario")
    migracoes_onedir = dir_onedir / "_internal" / "migracoes"
    migracoes_onedir.mkdir(parents=True)
    (migracoes_onedir / "0001_migrar.py").write_text("print('m')", encoding="utf-8")

    dir_app = tmp_path / "EditorAresta.app"

    criar_estrutura_bundle_macos(
        diretorio_origem_onedir=dir_onedir,
        diretorio_destino_app=dir_app,
        versao="0.4.0",
    )

    assert not (dir_app / "Contents" / "MacOS" / "_internal" / "migracoes").exists()
    assert (dir_app / "Contents" / "Resources" / "migracoes" / "0001_migrar.py").exists()
    assert (dir_app / "Contents" / "Resources" / "migracoes" / "0001_migrar.pyc").exists()


def test_sanitizar_bundle_para_codesign_movimentacao_migracoes_trata_oserror(
    tmp_path: Path,
) -> None:
    """Valida tratamento defensivo de falha de IO ao mover a pasta migracoes."""
    app_dir = tmp_path / "EditorAresta.app"
    migracoes_macos = app_dir / "Contents" / "MacOS" / "_internal" / "migracoes"
    migracoes_macos.mkdir(parents=True)

    with patch("shutil.move", side_effect=OSError("Falha de IO")):
        removidos = sanitizar_bundle_para_codesign(app_dir, dry_run=False)
        assert isinstance(removidos, list)


def test_assinar_bundle_macos_detecta_binario_macho_por_magic_bytes(tmp_path: Path) -> None:
    """Valida que binários Mach-O sem extensão .dylib/.so dentro de _internal são assinados."""
    app_dir = tmp_path / "EditorAresta.app"
    internal_bin_dir = app_dir / "Contents" / "MacOS" / "_internal" / "bin"
    internal_bin_dir.mkdir(parents=True)

    bin_auxiliar = internal_bin_dir / "python_helper"
    bin_auxiliar.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 30)

    executavel_principal = app_dir / "Contents" / "MacOS" / "EditorAresta"
    executavel_principal.write_bytes(b"binario_executavel")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        comandos = assinar_bundle_macos(
            caminho_app=app_dir,
            identidade_assinatura="Developer ID",
            dry_run=False,
        )

        assert any("python_helper" in cmd for cmd in comandos), (
            "Binário Mach-O auxiliar deve ser assinado"
        )


def test_eh_binario_mach_o_captura_oserror(tmp_path: Path) -> None:
    """Valida que falha de IO ao ler cabeçalho retorna False."""
    arquivo = tmp_path / "arquivo_com_erro"
    arquivo.write_bytes(b"1234")

    with patch("builtins.open", side_effect=OSError("Erro de permissao")):
        assert eh_binario_mach_o(arquivo) is False


def test_assinar_bundle_macos_ignora_symlinks(tmp_path: Path) -> None:
    """Valida que links simbólicos não são adicionados na lista de binários a assinar."""
    app_dir = tmp_path / "EditorAresta.app"
    internal_bin_dir = app_dir / "Contents" / "MacOS" / "_internal"
    internal_bin_dir.mkdir(parents=True)

    arquivo_dylib = internal_bin_dir / "libreal.dylib"
    arquivo_dylib.write_bytes(b"real")

    symlink_dylib = internal_bin_dir / "liblink.dylib"
    symlink_dylib.write_bytes(b"link")

    def mock_is_symlink(self: Path) -> bool:
        return self.name == "liblink.dylib"

    with patch.object(Path, "is_symlink", mock_is_symlink):
        comandos = assinar_bundle_macos(
            caminho_app=app_dir, identidade_assinatura="Dev", dry_run=True
        )

    assert any("libreal.dylib" in c for c in comandos)
    assert not any("liblink.dylib" in c for c in comandos)


def test_assinar_bundle_macos_assina_frameworks_aninhados_como_bundle_e_nao_binarios_internos(
    tmp_path: Path,
) -> None:
    """Valida que frameworks aninhados (ex: PySide6/Qt/lib/QtGui.framework) são assinados no nível do diretório e não seus binários internos soltos."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True)
    (macos_dir / "EditorAresta").write_bytes(b"binario_executavel")

    frameworks_dir = app_dir / "Contents" / "Frameworks" / "Sparkle.framework"
    frameworks_dir.mkdir(parents=True)
    (frameworks_dir / "Sparkle").write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 20)

    qt_framework_dir = macos_dir / "_internal" / "PySide6" / "Qt" / "lib" / "QtGui.framework"
    versoes_a_dir = qt_framework_dir / "Versions" / "A"
    versoes_a_dir.mkdir(parents=True)
    binario_qtgui = versoes_a_dir / "QtGui"
    binario_qtgui.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 20)

    comandos = assinar_bundle_macos(
        caminho_app=app_dir,
        identidade_assinatura="Developer ID",
        dry_run=True,
    )

    # 1. Os binários internos de QtGui.framework não devem ser assinados isoladamente
    assert not any(str(binario_qtgui) in cmd for cmd in comandos), (
        "Binários internos de um .framework não devem ser assinados como arquivos isolados"
    )

    # 2. O diretório QtGui.framework e Sparkle.framework devem ser assinados como frameworks
    cmd_qtgui_fw = next((cmd for cmd in comandos if cmd.endswith(str(qt_framework_dir))), None)
    cmd_sparkle_fw = next((cmd for cmd in comandos if cmd.endswith(str(frameworks_dir))), None)

    assert cmd_qtgui_fw is not None, "QtGui.framework deve ser assinado como bundle"
    assert cmd_sparkle_fw is not None, "Sparkle.framework deve ser assinado como bundle"

    # 3. Framework mais aninhado (QtGui.framework em _internal/PySide6/Qt/lib) deve ser assinado antes do executável principal e bundle raiz
    idx_qtgui = comandos.index(cmd_qtgui_fw)
    cmd_app = next(cmd for cmd in comandos if cmd.endswith(str(app_dir)))
    assert idx_qtgui < comandos.index(cmd_app)


def test_sanitizar_bundle_para_codesign_preserva_executavel_de_binario_macho_e_arquivos_em_framework(
    tmp_path: Path,
) -> None:
    """Valida que binários Mach-O e arquivos dentro de diretórios .framework não perdem a permissão de execução."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    internal_dir = macos_dir / "_internal"
    internal_dir.mkdir(parents=True)

    # Binário Mach-O sem extensão .dylib/.so
    bin_macho = internal_dir / "executavel_auxiliar"
    bin_macho.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 20)

    # Arquivo dentro de um .framework
    framework_dir = internal_dir / "Meu.framework"
    framework_dir.mkdir()
    bin_fw = framework_dir / "Meu"
    bin_fw.write_bytes(b"\xcf\xfa\xed\xfe" + b"\x00" * 20)

    # Arquivo de texto comum (este sim deve perder o bit executável se tiver)
    arquivo_txt = internal_dir / "readme.txt"
    arquivo_txt.write_text("texto", encoding="utf-8")

    chmod_chamados: list[Path] = []

    def mock_chmod(self: Path, modo: int) -> None:
        chmod_chamados.append(self)

    stat_real = Path.stat
    mock_stat = MagicMock(st_mode=0o100755)

    def mock_stat_fn(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self.name in ("readme.txt", "executavel_auxiliar", "Meu"):
            return mock_stat
        return stat_real(self, *args, **kwargs)

    with (
        patch.object(Path, "stat", mock_stat_fn),
        patch.object(Path, "chmod", mock_chmod),
    ):
        sanitizar_bundle_para_codesign(app_dir, dry_run=False)

    # Apenas o arquivo comum de texto deve acionar chmod (não binários Mach-O nem dentro de .framework)
    assert bin_macho not in chmod_chamados
    assert bin_fw not in chmod_chamados
    assert arquivo_txt in chmod_chamados


def test_criar_estrutura_bundle_macos_preserva_symlinks(tmp_path: Path) -> None:
    """Valida que a cópia de diretórios onedir usa symlinks=True para preservar links simbólicos de frameworks."""
    dir_onedir = tmp_path / "EditorAresta_onedir"
    dir_onedir.mkdir()
    subpasta = dir_onedir / "subpasta"
    subpasta.mkdir()
    (subpasta / "item.txt").write_text("item", encoding="utf-8")
    dir_saida_app = tmp_path / "EditorAresta.app"

    with patch("shutil.copytree") as mock_copytree:
        criar_estrutura_bundle_macos(
            diretorio_origem_onedir=dir_onedir,
            diretorio_destino_app=dir_saida_app,
            versao="0.4.0",
        )
        assert mock_copytree.call_count >= 1
        for call in mock_copytree.call_args_list:
            assert call.kwargs.get("symlinks") is True
