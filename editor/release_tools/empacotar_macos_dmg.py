# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para empacotamento, assinatura digital e notarização Apple do Editor Aresta no macOS (ARM64).
Monta a estrutura de bundle EditorAresta.app a partir do diretório onedir do PyInstaller
e gera a imagem de disco instalável .dmg para distribuição.
"""

import os
import shutil
import subprocess
from pathlib import Path

FEED_SPARKLE_PADRAO: str = "https://serving.arestaclimb.com/editor-macos/appcast.xml"
IDENTIFICADOR_BUNDLE_PADRAO: str = "com.arestaclimb.Editor"
NOME_EXECUTAVEL_PADRAO: str = "EditorAresta"
CHAVE_PUBLICA_SPARKLE_PADRAO: str = "BZ+UB+PvZmLAVAKiAoUtFUrrJSBECPFIc2dzvvlVruY="


def gerar_conteudo_info_plist(
    versao: str,
    identificador_bundle: str = IDENTIFICADOR_BUNDLE_PADRAO,
    nome_executavel: str = NOME_EXECUTAVEL_PADRAO,
    url_feed: str = FEED_SPARKLE_PADRAO,
    chave_publica_sparkle: str | None = CHAVE_PUBLICA_SPARKLE_PADRAO,
    atualizar_automaticamente: bool = True,
    intervalo_checagem_segundos: int = 3600,
) -> str:
    """
    Gera o conteúdo XML do Info.plist para o bundle macOS do Editor Aresta.
    """
    versao_limpa = versao.strip()
    tag_chave_publica = (
        f"    <key>SUPublicEDKey</key>\n    <string>{chave_publica_sparkle}</string>\n"
        if chave_publica_sparkle
        else ""
    )
    tag_atualizacao_automatica = (
        "    <key>SUAutomaticallyUpdate</key>\n    <true/>\n" if atualizar_automaticamente else ""
    )
    tag_intervalo = f"    <key>SUScheduledCheckInterval</key>\n    <integer>{intervalo_checagem_segundos}</integer>\n"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>pt-BR</string>
    <key>CFBundleDisplayName</key>
    <string>Editor Aresta</string>
    <key>CFBundleExecutable</key>
    <string>{nome_executavel}</string>
    <key>CFBundleIconFile</key>
    <string>logo.icns</string>
    <key>CFBundleIdentifier</key>
    <string>{identificador_bundle}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Editor Aresta</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{versao_limpa}</string>
    <key>CFBundleVersion</key>
    <string>{versao_limpa}</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>SUFeedURL</key>
    <string>{url_feed}</string>
    <key>SUEnableAutomaticChecks</key>
    <true/>
{tag_atualizacao_automatica}{tag_intervalo}{tag_chave_publica}</dict>
</plist>
"""


def criar_estrutura_bundle_macos(
    diretorio_origem_onedir: Path,
    diretorio_destino_app: Path,
    versao: str,
    caminho_icone_icns: Path | None = None,
    identificador_bundle: str = IDENTIFICADOR_BUNDLE_PADRAO,
    chave_publica_sparkle: str | None = CHAVE_PUBLICA_SPARKLE_PADRAO,
    caminho_sparkle_framework: Path | None = None,
) -> Path:
    """
    Monta a árvore de diretórios do bundle EditorAresta.app a partir da saída onedir.
    """
    diretorio_contents = diretorio_destino_app / "Contents"
    diretorio_macos = diretorio_contents / "MacOS"
    diretorio_resources = diretorio_contents / "Resources"

    if diretorio_destino_app.exists():
        shutil.rmtree(diretorio_destino_app)

    diretorio_macos.mkdir(parents=True, exist_ok=True)
    diretorio_resources.mkdir(parents=True, exist_ok=True)

    # Copia todo o conteúdo gerado pelo PyInstaller para Contents/MacOS
    for item in diretorio_origem_onedir.iterdir():
        destino_item = diretorio_macos / item.name
        if item.is_dir():
            shutil.copytree(item, destino_item)
        else:
            shutil.copy2(item, destino_item)

    # Copia o ícone .icns para Contents/Resources se fornecido
    if caminho_icone_icns and caminho_icone_icns.exists():
        shutil.copy2(caminho_icone_icns, diretorio_resources / "logo.icns")

    # Copia o Sparkle.framework para Contents/Frameworks se fornecido
    if caminho_sparkle_framework and caminho_sparkle_framework.exists():
        diretorio_frameworks = diretorio_contents / "Frameworks"
        diretorio_frameworks.mkdir(parents=True, exist_ok=True)
        destino_sparkle = diretorio_frameworks / "Sparkle.framework"
        shutil.copytree(caminho_sparkle_framework, destino_sparkle, symlinks=True)

    # Gera e grava o Info.plist
    conteudo_plist = gerar_conteudo_info_plist(
        versao=versao,
        identificador_bundle=identificador_bundle,
        chave_publica_sparkle=chave_publica_sparkle,
    )
    (diretorio_contents / "Info.plist").write_text(conteudo_plist, encoding="utf-8")

    return diretorio_destino_app


def assinar_bundle_macos(
    caminho_app: Path,
    identidade_assinatura: str,
    caminho_entitlements: Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    """
    Assina todos os binários, frameworks e o bundle principal com o Developer ID.
    Retorna a lista de comandos executados.
    """
    comandos_executados: list[str] = []

    # Localiza arquivos binários internos (.dylib, .so)
    arquivos_para_assinar = []
    for raiz, _, arquivos in os.walk(caminho_app):
        for arq in arquivos:
            if arq.endswith((".dylib", ".so")):
                arquivos_para_assinar.append(Path(raiz) / arq)

    cmd_base = [
        "codesign",
        "--force",
        "--options",
        "runtime",
        "--timestamp",
        "--sign",
        identidade_assinatura,
    ]

    for binario in arquivos_para_assinar:
        cmd = [*cmd_base, str(binario)]
        comandos_executados.append(" ".join(cmd))
        if not dry_run:
            subprocess.run(cmd, check=True)

    # Assina frameworks em Contents/Frameworks antes do bundle principal
    diretorio_frameworks = caminho_app / "Contents" / "Frameworks"
    if diretorio_frameworks.exists():
        for item in diretorio_frameworks.iterdir():
            if item.suffix == ".framework" or item.is_dir():
                cmd_fw = [*cmd_base, str(item)]
                comandos_executados.append(" ".join(cmd_fw))
                if not dry_run:
                    subprocess.run(cmd_fw, check=True)

    # Assina o bundle .app raiz
    cmd_app = cmd_base.copy()
    if caminho_entitlements and caminho_entitlements.exists():
        cmd_app.extend(["--entitlements", str(caminho_entitlements)])
    cmd_app.append(str(caminho_app))

    comandos_executados.append(" ".join(cmd_app))
    if not dry_run:
        subprocess.run(cmd_app, check=True)

    return comandos_executados


def gerar_dmg_macos(
    caminho_app: Path,
    caminho_saida_dmg: Path,
    nome_volume: str = "Editor Aresta",
    dry_run: bool = False,
) -> list[str]:
    """
    Gera a imagem de disco DMG utilizando hdiutil.
    """
    caminho_saida_dmg.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run and caminho_saida_dmg.exists():
        caminho_saida_dmg.unlink()

    cmd = [
        "hdiutil",
        "create",
        "-volname",
        nome_volume,
        "-srcfolder",
        str(caminho_app),
        "-ov",
        "-format",
        "UDZO",
        str(caminho_saida_dmg),
    ]

    comandos: list[str] = [" ".join(cmd)]
    if not dry_run:
        subprocess.run(cmd, check=True)

    return comandos


def notarizar_dmg_macos(
    caminho_dmg: Path,
    apple_id: str | None = None,
    app_password: str | None = None,
    team_id: str | None = None,
    profile: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    """
    Submete a imagem DMG para notarização Apple e grampeia o ticket (staple).
    """
    comandos: list[str] = []

    cmd_notary = ["xcrun", "notarytool", "submit", str(caminho_dmg), "--wait"]
    if profile:
        cmd_notary.extend(["--keychain-profile", profile])
    elif apple_id and app_password and team_id:
        cmd_notary.extend(
            [
                "--apple-id",
                apple_id,
                "--password",
                app_password,
                "--team-id",
                team_id,
            ]
        )

    comandos.append(" ".join(cmd_notary))
    if not dry_run:
        subprocess.run(cmd_notary, check=True)

    cmd_staple = ["xcrun", "stapler", "staple", str(caminho_dmg)]
    comandos.append(" ".join(cmd_staple))
    if not dry_run:
        subprocess.run(cmd_staple, check=True)

    return comandos


def empacotar_distribuicao_macos(
    diretorio_onedir: Path,
    diretorio_saida: Path,
    versao: str,
    identidade_assinatura: str | None = None,
    notarizar: bool = False,
    apple_id: str | None = None,
    app_password: str | None = None,
    team_id: str | None = None,
    profile: str | None = None,
    chave_publica_sparkle: str | None = CHAVE_PUBLICA_SPARKLE_PADRAO,
    caminho_sparkle_framework: Path | None = None,
    dry_run: bool = False,
) -> Path:
    """
    Fluxo orquestrado para gerar o bundle .app, assinar, gerar o DMG e opcionalmente notarizar.
    """
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    caminho_app = diretorio_saida / "EditorAresta.app"

    # 1. Monta o bundle .app
    criar_estrutura_bundle_macos(
        diretorio_origem_onedir=diretorio_onedir,
        diretorio_destino_app=caminho_app,
        versao=versao,
        chave_publica_sparkle=chave_publica_sparkle,
        caminho_sparkle_framework=caminho_sparkle_framework,
    )

    # 2. Assinatura com Developer ID (se informada)
    if identidade_assinatura:
        assinar_bundle_macos(
            caminho_app=caminho_app,
            identidade_assinatura=identidade_assinatura,
            dry_run=dry_run,
        )

    # 3. Geração do DMG
    caminho_dmg = diretorio_saida / f"EditorAresta-{versao}.dmg"
    gerar_dmg_macos(
        caminho_app=caminho_app,
        caminho_saida_dmg=caminho_dmg,
        dry_run=dry_run,
    )

    # 4. Notarização Apple (se solicitada)
    if notarizar:
        notarizar_dmg_macos(
            caminho_dmg=caminho_dmg,
            apple_id=apple_id,
            app_password=app_password,
            team_id=team_id,
            profile=profile,
            dry_run=dry_run,
        )

    return caminho_dmg
