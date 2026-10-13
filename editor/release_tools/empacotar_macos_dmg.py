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
import sys
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

    # Copia todo o conteúdo gerado pelo PyInstaller para Contents/MacOS preservando symlinks
    for item in diretorio_origem_onedir.iterdir():
        destino_item = diretorio_macos / item.name
        if item.is_dir():
            shutil.copytree(item, destino_item, symlinks=True)
        else:
            shutil.copy2(item, destino_item, follow_symlinks=False)

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

    # Sanitiza o bundle expurgando metadados pip (.dist-info, .egg-info) e caches
    sanitizar_bundle_para_codesign(diretorio_destino_app)

    return diretorio_destino_app


ASSINATURAS_MAGIC_MACH_O: tuple[bytes, ...] = (
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit big-endian
    b"\xce\xfa\xed\xfe",  # Mach-O 32-bit little-endian
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit big-endian
    b"\xcf\xfa\xed\xfe",  # Mach-O 64-bit little-endian (ARM64 / x86_64)
    b"\xca\xfe\xba\xbe",  # Mach-O Universal Binary / Fat binary
    b"\xbe\xba\xfe\xca",  # Mach-O Universal Binary inverso
)


def eh_binario_mach_o(caminho: Path) -> bool:
    """
    Verifica se um arquivo é um executável ou biblioteca Mach-O através de seus magic bytes iniciais.
    """
    try:
        if not caminho.is_file() or caminho.is_symlink():
            return False
        with open(caminho, "rb") as f:
            cabecalho = f.read(4)
        return len(cabecalho) == 4 and cabecalho in ASSINATURAS_MAGIC_MACH_O
    except OSError:
        return False


def sanitizar_bundle_para_codesign(
    caminho_app: Path,
    dry_run: bool = False,
) -> list[Path]:
    """
    Remove arquivos e pastas que causam falhas no utilitário codesign da Apple.
    No macOS, o codesign inspeciona qualquer diretório em Contents/MacOS/ tratando
    arquivos de script ou pastas com ponto como subcomponentes de código.
    Scripts Python (.py) soltos são considerados subcomponentes de código não assinados
    ('code object is not signed at all').
    Esta função:
    1. Pré-compila scripts .py de produção para bytecode .pyc e remove os fontes .py originais.
    2. Expurga metadados pip (.dist-info, .egg-info), arquivos de testes e caches.
    3. Remove permissões de execução POSIX (+x) de arquivos comuns de dados.
    4. Limpa atributos estendidos (xattr -cr) no macOS.
    Retorna a lista de itens removidos ou alterados.
    """
    import py_compile

    itens_removidos: list[Path] = []

    if not caminho_app.exists():
        return itens_removidos

    # 1. Varre o bundle de baixo para cima removendo diretórios e arquivos problemáticos
    for raiz, pastas, arquivos in os.walk(caminho_app, topdown=False):
        caminho_raiz = Path(raiz)

        # Remove arquivos .DS_Store, compila scripts .py para .pyc e expurga testes
        for arq in arquivos:
            nome_baixo = arq.lower()
            p_arq = caminho_raiz / arq

            eh_ds_store = arq == ".DS_Store"
            eh_teste = (
                nome_baixo.endswith(("_test.py", "_test.pyc"))
                or nome_baixo.startswith("test_")
                or nome_baixo == "conftest.py"
            )

            if eh_ds_store or eh_teste:
                itens_removidos.append(p_arq)
                if not dry_run and p_arq.exists():
                    p_arq.unlink(missing_ok=True)
            elif arq.endswith(".py"):
                # Arquivo de script Python de produção (ex: migracoes/*.py):
                # Compila para bytecode .pyc e remove o fonte .py para evitar o erro
                # 'code object is not signed at all' no codesign da Apple
                itens_removidos.append(p_arq)
                if not dry_run and p_arq.exists():
                    caminho_pyc = p_arq.with_suffix(".pyc")
                    try:
                        py_compile.compile(str(p_arq), cfile=str(caminho_pyc), doraise=True)
                        p_arq.unlink(missing_ok=True)
                    except (py_compile.PyCompileError, OSError):
                        pass
            elif (
                not dry_run
                and not arq.endswith((".dylib", ".so"))
                and not eh_binario_mach_o(p_arq)
                and not any(
                    p.name.endswith(".framework") for p in [caminho_raiz, *caminho_raiz.parents]
                )
            ):
                # Se for arquivo comum, remove o bit executável POSIX para evitar que o macOS trate como code object
                if p_arq.parent.name != "MacOS" or p_arq.name != NOME_EXECUTAVEL_PADRAO:
                    try:
                        modo_atual = p_arq.stat().st_mode
                        if modo_atual & 0o111:
                            p_arq.chmod(modo_atual & ~0o111)
                    except OSError:
                        pass

        # Remove pastas de metadados, caches e pastas de teste
        for pasta in pastas:
            eh_pasta_problema = (
                pasta.endswith((".dist-info", ".egg-info"))
                or pasta == "__pycache__"
                or pasta == "tests"
            )
            if eh_pasta_problema:
                p_pasta = caminho_raiz / pasta
                itens_removidos.append(p_pasta)
                if not dry_run and p_pasta.exists():
                    shutil.rmtree(p_pasta, ignore_errors=True)

    # 2. Limpa atributos estendidos no macOS (quarantine, FinderInfo, etc.)
    if not dry_run and sys.platform == "darwin":
        try:
            subprocess.run(["xattr", "-cr", str(caminho_app)], check=False, capture_output=True)
        except FileNotFoundError:
            pass

    return itens_removidos


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
    # Garante que o bundle esteja limpo de subcomponentes inválidos antes do codesign
    sanitizar_bundle_para_codesign(caminho_app, dry_run=dry_run)

    comandos_executados: list[str] = []

    cmd_base = [
        "codesign",
        "--force",
        "--options",
        "runtime",
        "--timestamp",
        "--sign",
        identidade_assinatura,
    ]

    diretorio_macos = caminho_app / "Contents" / "MacOS"

    # 1. Localiza arquivos binários internos soltos (.dylib, .so ou binários Mach-O auxiliares)
    # Binários que residem dentro de um .framework NÃO devem ser assinados como arquivos isolados,
    # pois o codesign da Apple exige que o .framework seja assinado como um bundle único.
    arquivos_para_assinar: list[Path] = []
    for raiz, _, arquivos in os.walk(caminho_app):
        caminho_raiz = Path(raiz)
        if any(p.name.endswith(".framework") for p in [caminho_raiz, *caminho_raiz.parents]):
            continue
        for arq in arquivos:
            p_arq = caminho_raiz / arq
            if p_arq.is_symlink():
                continue
            # Assina extensões binárias ou arquivos Mach-O que não sejam o executável principal em Contents/MacOS
            if arq.endswith((".dylib", ".so")) or (
                eh_binario_mach_o(p_arq)
                and (caminho_raiz != diretorio_macos or arq != NOME_EXECUTAVEL_PADRAO)
            ):
                arquivos_para_assinar.append(p_arq)

    for binario in sorted(arquivos_para_assinar):
        cmd = [*cmd_base, str(binario)]
        comandos_executados.append(" ".join(cmd))
        if not dry_run:
            subprocess.run(cmd, check=True)

    # 2. Localiza e assina todos os frameworks (.framework) recursivamente em ordem inside-out
    # Localiza qualquer diretório terminado em .framework (ex: Contents/Frameworks/Sparkle.framework,
    # Contents/MacOS/_internal/PySide6/Qt/lib/QtCore.framework, QtGui.framework, etc.).
    # Ordena por profundidade decrescente para que frameworks aninhados mais internos sejam assinados primeiro.
    frameworks_para_assinar: list[Path] = []
    for raiz, pastas, _ in os.walk(caminho_app):
        caminho_raiz = Path(raiz)
        for pasta in pastas:
            if pasta.endswith(".framework"):
                p_fw = caminho_raiz / pasta
                if not p_fw.is_symlink():
                    frameworks_para_assinar.append(p_fw)

    frameworks_para_assinar.sort(key=lambda p: (len(p.parts), str(p)), reverse=True)

    for framework in frameworks_para_assinar:
        cmd_fw = [*cmd_base, str(framework)]
        comandos_executados.append(" ".join(cmd_fw))
        if not dry_run:
            subprocess.run(cmd_fw, check=True)

    # 3. Assina executáveis binários principais em Contents/MacOS antes do bundle
    diretorio_macos = caminho_app / "Contents" / "MacOS"
    if diretorio_macos.exists():
        for item in sorted(diretorio_macos.iterdir()):
            if item.is_file() and item.suffix.lower() not in (
                ".dylib",
                ".so",
                ".plist",
                ".txt",
                ".json",
                ".xml",
            ):
                cmd_bin = cmd_base.copy()
                if caminho_entitlements and caminho_entitlements.exists():
                    cmd_bin.extend(["--entitlements", str(caminho_entitlements)])
                cmd_bin.append(str(item))
                comandos_executados.append(" ".join(cmd_bin))
                if not dry_run:
                    subprocess.run(cmd_bin, check=True)

    # 4. Assina o bundle .app raiz
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
