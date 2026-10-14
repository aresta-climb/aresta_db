# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para empacotamento, assinatura digital e notarização Apple do Editor Aresta no macOS (ARM64).
Monta a estrutura de bundle EditorAresta.app a partir do diretório onedir do PyInstaller
e gera a imagem de disco instalável .dmg para distribuição.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FEED_SPARKLE_PADRAO: str = "https://serving.arestaclimb.com/editor-macos/appcast.xml"
IDENTIFICADOR_BUNDLE_PADRAO: str = "com.arestaclimb.Editor"
NOME_EXECUTAVEL_PADRAO: str = "EditorAresta"
CHAVE_PUBLICA_SPARKLE_PADRAO: str = "BZ+UB+PvZmLAVAKiAoUtFUrrJSBECPFIc2dzvvlVruY="

ENTITLEMENTS_PADRAO_MACOS: str = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
"""


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

    # Copia todo o conteúdo gerado pelo PyInstaller preservando symlinks.
    # A pasta '_internal' contém dados, recursos e bibliotecas e deve residir em Contents/Resources/_internal
    # com um link simbólico relativo em Contents/MacOS/_internal, garantindo conformidade com as regras do
    # codesign da Apple (Contents/MacOS deve conter apenas o executável principal e symlinks).
    for item in diretorio_origem_onedir.iterdir():
        if item.name == "_internal":
            destino_internal = diretorio_resources / "_internal"
            shutil.copytree(item, destino_internal, symlinks=True)

            symlink_macos = diretorio_macos / "_internal"
            try:
                alvo_symlink = (
                    str(destino_internal.resolve()) if os.name == "nt" else "../Resources/_internal"
                )
                symlink_macos.symlink_to(alvo_symlink, target_is_directory=True)
            except OSError:
                pass
        else:
            destino_item = diretorio_macos / item.name
            if item.is_dir():
                shutil.copytree(item, destino_item, symlinks=True)
            else:
                shutil.copy2(item, destino_item, follow_symlinks=False)

    # Garante que a pasta 'migracoes' resida exclusivamente em Contents/Resources/migracoes
    migracoes_em_internal = diretorio_resources / "_internal" / "migracoes"
    migracoes_em_resources = diretorio_resources / "migracoes"
    if migracoes_em_internal.exists():
        shutil.move(str(migracoes_em_internal), str(migracoes_em_resources))

    if migracoes_em_resources.is_dir():
        precompilar_scripts_para_bytecode(migracoes_em_resources)

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


def precompilar_scripts_para_bytecode(diretorio: Path) -> list[Path]:
    """
    Pré-compila scripts Python (.py) de um diretório para bytecode (.pyc),
    mantendo os arquivos fontes originais intactos.
    Ignora arquivos de teste (*_test.py).
    Retorna a lista dos arquivos .pyc gerados com sucesso.
    """
    import py_compile

    arquivos_pyc: list[Path] = []
    if not diretorio.is_dir():
        return arquivos_pyc

    for arq_py in sorted(diretorio.glob("*.py")):
        if not arq_py.name.endswith("_test.py"):
            caminho_pyc = arq_py.with_suffix(".pyc")
            try:
                py_compile.compile(str(arq_py), cfile=str(caminho_pyc), doraise=True)
                arquivos_pyc.append(caminho_pyc)
            except (py_compile.PyCompileError, OSError):
                pass

    return arquivos_pyc


def sanitizar_bundle_para_codesign(
    caminho_app: Path,
    dry_run: bool = False,
) -> list[Path]:
    """
    Remove arquivos e pastas que causam falhas no utilitário codesign da Apple.
    No macOS, o codesign inspeciona qualquer diretório em Contents/MacOS/ tratando
    arquivos de script ou pastas com ponto como subcomponentes de código.
    Esta função:
    1. Garante que a pasta 'migracoes' resida em Contents/Resources/ e não em Contents/MacOS/.
    2. Expurga metadados pip (.dist-info, .egg-info), arquivos de testes e caches.
    3. Remove scripts Python (.py, .pyc) soltos residuais em Contents/MacOS/.
    4. Remove permissões de execução POSIX (+x) de arquivos comuns de dados.
    5. Limpa atributos estendidos (xattr -cr) no macOS.
    Retorna a lista de itens removidos ou alterados.
    """
    itens_removidos: list[Path] = []

    if not caminho_app.exists():
        return itens_removidos

    diretorio_macos = caminho_app / "Contents" / "MacOS"
    diretorio_resources = caminho_app / "Contents" / "Resources"

    # Se a pasta '_internal' em Contents/MacOS for uma pasta física (não symlink),
    # move para Contents/Resources/_internal e cria o symlink relativo.
    internal_macos = diretorio_macos / "_internal"
    internal_resources = diretorio_resources / "_internal"
    try:
        if internal_macos.is_dir() and not internal_macos.is_symlink():
            itens_removidos.append(internal_macos)
            if (internal_macos / "migracoes").is_dir():
                itens_removidos.append(internal_macos / "migracoes")
            if not dry_run:
                if internal_resources.exists():
                    shutil.rmtree(internal_resources, ignore_errors=True)
                diretorio_resources.mkdir(parents=True, exist_ok=True)
                shutil.move(str(internal_macos), str(internal_resources))
                try:
                    alvo_symlink = (
                        str(internal_resources.resolve())
                        if os.name == "nt"
                        else "../Resources/_internal"
                    )
                    internal_macos.symlink_to(alvo_symlink, target_is_directory=True)
                except OSError:
                    pass
    except OSError:
        pass

    if not dry_run and diretorio_resources.is_dir():
        migracoes_resources = diretorio_resources / "migracoes"
        migracoes_em_internal = internal_resources / "migracoes"
        if migracoes_em_internal.is_dir():
            if not migracoes_resources.is_dir():
                shutil.move(str(migracoes_em_internal), str(migracoes_resources))
            else:
                shutil.rmtree(migracoes_em_internal, ignore_errors=True)
        if migracoes_resources.is_dir():
            precompilar_scripts_para_bytecode(migracoes_resources)

    # 1. Varre o bundle de baixo para cima removendo diretórios e arquivos problemáticos
    for raiz, pastas, arquivos in os.walk(caminho_app, topdown=False):
        caminho_raiz = Path(raiz)
        esta_em_macos = caminho_raiz == diretorio_macos or (
            diretorio_macos in caminho_raiz.parents
            and not any(p.is_symlink() for p in [caminho_raiz, *caminho_raiz.parents])
        )

        # Remove arquivos .DS_Store, expurga testes e scripts residuais em Contents/MacOS
        for arq in arquivos:
            nome_baixo = arq.lower()
            p_arq = caminho_raiz / arq

            eh_ds_store = arq == ".DS_Store"
            eh_teste = (
                nome_baixo.endswith(("_test.py", "_test.pyc"))
                or nome_baixo.startswith("test_")
                or nome_baixo == "conftest.py"
            )
            eh_artefato_windows = nome_baixo.endswith((".ico", ".exe", ".bat", ".cmd"))

            if eh_ds_store or eh_teste or eh_artefato_windows:
                itens_removidos.append(p_arq)
                if not dry_run and p_arq.exists():
                    p_arq.unlink(missing_ok=True)
            elif esta_em_macos and (arq.endswith(".py") or arq.endswith(".pyc")):
                # Nenhum script Python solto (.py ou .pyc) pode residir em Contents/MacOS/,
                # pois o codesign da Apple trata qualquer arquivo em Contents/MacOS/ como
                # um code object que requer assinatura Mach-O válida.
                itens_removidos.append(p_arq)
                if not dry_run and p_arq.exists():
                    p_arq.unlink(missing_ok=True)
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


def inspecionar_itens_inesperados_macos(caminho_app: Path) -> list[Path]:
    """
    Inspeciona o diretório Contents/MacOS à procura de arquivos e diretórios físicos
    inesperados que possam violar as regras de codesign do macOS, imprimindo informações de depuração.
    Retorna a lista de itens inesperados encontrados.
    """
    diretorio_macos = caminho_app / "Contents" / "MacOS"
    if not diretorio_macos.exists():
        return []

    itens_inesperados: list[Path] = []
    print(f"[DEBUG macOS] Inspecionando estrutura de {diretorio_macos}:")

    # Verifica symlink _internal
    symlink_internal = diretorio_macos / "_internal"
    if symlink_internal.is_symlink():
        alvo = symlink_internal.readlink()
        print(f"  [DEBUG macOS - OK] _internal -> {alvo} (symlink)")

    for raiz, pastas, arquivos in os.walk(diretorio_macos, followlinks=False):
        caminho_raiz = Path(raiz)

        for pasta in pastas:
            p_pasta = caminho_raiz / pasta
            if not p_pasta.is_symlink():
                itens_inesperados.append(p_pasta)
                print(f"  [DEBUG macOS - PASTA INESPERADA] {p_pasta.relative_to(diretorio_macos)}")

        for arquivo in arquivos:
            p_arquivo = caminho_raiz / arquivo
            if caminho_raiz == diretorio_macos and arquivo == NOME_EXECUTAVEL_PADRAO:
                print(f"  [DEBUG macOS - OK] {arquivo} (executável principal)")
            else:
                itens_inesperados.append(p_arquivo)
                tamanho = p_arquivo.stat().st_size if p_arquivo.exists() else 0
                print(
                    f"  [DEBUG macOS - ARQUIVO INESPERADO] {p_arquivo.relative_to(diretorio_macos)} ({tamanho} bytes)"
                )

    if not itens_inesperados:
        print(
            "[DEBUG macOS] Nenhum arquivo ou pasta física inesperada encontrada em Contents/MacOS."
        )
    else:
        print(
            f"[DEBUG macOS] Total de {len(itens_inesperados)} itens inesperados em Contents/MacOS!"
        )

    return itens_inesperados


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

    # Imprime no log todos os arquivos na árvore de Contents/MacOS para depuração detalhada
    inspecionar_itens_inesperados_macos(caminho_app)

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
    caminho_entitlements_efetivo = caminho_entitlements
    if caminho_entitlements_efetivo is None or not caminho_entitlements_efetivo.exists():
        arquivo_entitlements_padrao = caminho_app / "Contents" / "Resources" / "entitlements.plist"
        if not dry_run:
            arquivo_entitlements_padrao.parent.mkdir(parents=True, exist_ok=True)
            arquivo_entitlements_padrao.write_text(ENTITLEMENTS_PADRAO_MACOS, encoding="utf-8")
        caminho_entitlements_efetivo = arquivo_entitlements_padrao

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
                if caminho_entitlements_efetivo and (
                    dry_run or caminho_entitlements_efetivo.exists()
                ):
                    cmd_bin.extend(["--entitlements", str(caminho_entitlements_efetivo)])
                cmd_bin.append(str(item))
                comandos_executados.append(" ".join(cmd_bin))
                if not dry_run:
                    subprocess.run(cmd_bin, check=True)

    # 4. Assina o bundle .app raiz
    cmd_app = cmd_base.copy()
    if caminho_entitlements_efetivo and (dry_run or caminho_entitlements_efetivo.exists()):
        cmd_app.extend(["--entitlements", str(caminho_entitlements_efetivo)])
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


def assinar_dmg_macos(
    caminho_dmg: Path,
    identidade_assinatura: str,
    dry_run: bool = False,
) -> list[str]:
    """
    Assina a imagem de disco DMG com o Developer ID Application e timestamp seguro.
    Obrigatório pela Apple antes da notarização e stapling.
    """
    cmd = [
        "codesign",
        "--force",
        "--timestamp",
        "--sign",
        identidade_assinatura,
        str(caminho_dmg),
    ]
    comandos = [" ".join(cmd)]
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
    Caso a submissão seja rejeitada ou não aprovada pela Apple, busca e imprime o log detalhado
    do notarytool no terminal para depuração imediata.
    """
    comandos: list[str] = []

    cmd_notary = [
        "xcrun",
        "notarytool",
        "submit",
        str(caminho_dmg),
        "--wait",
        "--output-format",
        "json",
    ]
    args_auth: list[str] = []
    if profile:
        args_auth.extend(["--keychain-profile", profile])
    elif apple_id and app_password and team_id:
        args_auth.extend(
            [
                "--apple-id",
                apple_id,
                "--password",
                app_password,
                "--team-id",
                team_id,
            ]
        )
    cmd_notary.extend(args_auth)

    comandos.append(" ".join(cmd_notary))
    if not dry_run:
        res = subprocess.run(cmd_notary, capture_output=True, text=True, check=False)
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()

        submissao_id: str | None = None
        status: str = "Unknown"

        try:
            dados = json.loads(stdout)
            submissao_id = dados.get("id")
            status = dados.get("status", "Unknown")
        except json.JSONDecodeError:
            print(
                f"[AVISO NOTARIZAÇÃO] Resposta do notarytool não foi JSON puro:\n{stdout}\n{stderr}"
            )
            match_id = re.search(r"id:\s*([a-f0-9\-]+)", stdout, re.IGNORECASE)
            if match_id:
                submissao_id = match_id.group(1)
            if "status: Accepted" in stdout:
                status = "Accepted"
            elif "status: Invalid" in stdout:
                status = "Invalid"

        if status != "Accepted":
            print(f"[ERRO NOTARIZAÇÃO APPLE] Status da submissão: {status} (ID: {submissao_id})")
            if submissao_id:
                cmd_log = ["xcrun", "notarytool", "log", submissao_id, *args_auth]
                print(
                    f"[LOG NOTARIZAÇÃO APPLE] Obtendo relatório detalhado da Apple: {' '.join(cmd_log)}"
                )
                res_log = subprocess.run(cmd_log, capture_output=True, text=True, check=False)
                print("[RELATÓRIO DE AUDITORIA APPLE]:")
                print(res_log.stdout)
                if res_log.stderr:
                    print(res_log.stderr)
            raise RuntimeError(
                f"A notarização Apple da imagem DMG falhou com status '{status}' (ID: {submissao_id}). "
                "Consulte o relatório de auditoria detalhado acima."
            )

        print(f"[OK NOTARIZAÇÃO APPLE] Submissão {submissao_id} aceita com sucesso pela Apple.")

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

    # 4. Assinatura do arquivo DMG com Developer ID
    if identidade_assinatura:
        assinar_dmg_macos(
            caminho_dmg=caminho_dmg,
            identidade_assinatura=identidade_assinatura,
            dry_run=dry_run,
        )

    # 5. Notarização Apple (se solicitada)
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
