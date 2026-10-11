# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any

try:
    import PyInstaller.__main__  # type: ignore[import-untyped]  # noqa: F401
except ImportError:
    pass


import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest

# Caminhos
DIRETORIO_EDITOR = Path(__file__).parent.resolve()
ARQUIVO_MAIN = DIRETORIO_EDITOR / "main.py"
ARQUIVO_SPEC = DIRETORIO_EDITOR / "EditorAresta.spec"
DIRETORIO_DIST = DIRETORIO_EDITOR / "dist"
DIRETORIO_DIST_ONEDIR = DIRETORIO_DIST / "EditorAresta"
DIRETORIO_FLATPAK = DIRETORIO_EDITOR / "flatpak"
ARQUIVO_MANIFESTO_FLATPAK = DIRETORIO_FLATPAK / "com.arestaclimb.Editor.yaml"
LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB = 95.0


def obter_versao_projeto(caminho_pyproject: Path | None = None) -> str:
    """
    Retorna a versão do projeto lendo diretamente o arquivo pyproject.toml na raiz do repositório.
    """
    arquivo_toml = caminho_pyproject or (DIRETORIO_EDITOR.parent / "pyproject.toml")
    if not arquivo_toml.exists():
        raise FileNotFoundError(f"Arquivo pyproject.toml não encontrado em: {arquivo_toml}")

    with open(arquivo_toml, "rb") as f:
        dados = tomllib.load(f)

    versao = dados.get("project", {}).get("version")
    if not versao or not isinstance(versao, str):
        raise ValueError(f"Campo 'project.version' não encontrado ou inválido em {arquivo_toml}")

    return versao


def obter_diretorio_distribuicao_onedir() -> Path:
    """Retorna o diretório onde os binários onedir são gerados pelo PyInstaller."""
    return DIRETORIO_DIST_ONEDIR


# Binários pesados de fallback gráfico do Qt que não são necessários no Windows moderno
BINARIOS_DISPENSAVEIS = {
    "opengl32sw.dll",
    "qdirect2d.dll",
    "Qt6Quick.dll",
    "Qt6Qml.dll",
    "Qt6Pdf.dll",
    "Qt6ShaderTools.dll",
    "Qt6Quick3DRuntimeRender.dll",
    "Qt63DRender.dll",
    "Qt6Designer.dll",
}

NOMES_BASE_BINARIOS_DISPENSAVEIS = (
    "opengl32sw",
    "qdirect2d",
    "qt6quick",
    "qt6qml",
    "qt6pdf",
    "qt6shadertools",
    "qt6quick3druntimerender",
    "qt63drender",
    "qt6designer",
)


# Famílias de fontes de ícones do QtAwesome que não são utilizadas pelo tema do editor
FONTES_DISPENSAVEIS = (
    "materialdesignicons",
    "phosphor",
    "remixicon",
    "codicon",
    "elusiveicons",
)


def obter_modulos_excluidos() -> list[str]:
    """
    Retorna a lista de módulos pesados de IA, OCR, PDF, visão computacional, pacotes de dados
    e submódulos dispensáveis do PySide6 que não devem ser empacotados no executável do editor.
    """
    return [
        # Bibliotecas pesadas de IA, OCR, PDF e Visão Computacional (grupo pdf/scripts)
        "paddleocr",
        "paddlex",
        "cv2",
        "pymupdf",
        "fitz",
        "pypdfium2",
        "scipy",
        "numpy",
        "tokenizers",
        "grpc",
        "grpcio",
        "hf_xet",
        "modelscope",
        "langchain",
        "langchain_community",
        "torch",
        "tiktoken",
        "lxml",
        "openai",
        "duckduckgo_search",
        "boto3",
        "botocore",
        "google.generativeai",
        "google.ai",
        # Pacotes de dados/auxiliares não utilizados pelo editor
        "pandas",
        "openpyxl",
        "sqlalchemy",
        "jinja2",
        "fsspec",
        "psutil",
        "sqlite3",
        # Submódulos dispensáveis do PySide6 (não utilizados pelo Editor QtWidgets)
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtNetworkAuth",
        "PySide6.QtDesigner",
        "PySide6.QtSpatialAudio",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
        "PySide6.QtHttpServer",
        "PySide6.QtLocation",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSerialBus",
        "PySide6.QtStateMachine",
        "PySide6.QtTextToSpeech",
        "PySide6.QtUiTools",
        "PySide6.QtXml",
        "PySide6.QtGraphs",
        "PySide6.QtGraphsWidgets",
        "PySide6.QtDataVisualization",
        "PySide6.QtCharts",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtAxContainer",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
    ]


def filtrar_binarios_desnecessarios(
    binarios: list[Any],
) -> list[Any]:
    """
    Filtra a lista de binários do PyInstaller, removendo DLLs de fallback de hardware
    e submódulos gráficos do Qt sabidamente dispensáveis para Windows e macOS.
    """
    resultado = []
    for item in binarios:
        nome_binario = item[0] if isinstance(item, (tuple, list)) and len(item) > 0 else ""
        nome_binario_lower = nome_binario.lower()

        eh_dispensavel = any(
            dispensavel.lower() in nome_binario_lower for dispensavel in BINARIOS_DISPENSAVEIS
        ) or any(nome_base in nome_binario_lower for nome_base in NOMES_BASE_BINARIOS_DISPENSAVEIS)
        if not eh_dispensavel:
            resultado.append(item)
    return resultado


def filtrar_datas_desnecessarios(
    datas: list[Any],
) -> list[Any]:
    """
    Filtra a lista de arquivos de dados do PyInstaller, removendo famílias de fontes
    do QtAwesome não utilizadas pelo tema de ícones do editor.
    """
    resultado = []
    for item in datas:
        origem = item[0] if isinstance(item, (tuple, list)) and len(item) > 0 else ""
        destino = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else ""
        alvo = f"{origem} {destino}".lower()
        if not any(fonte in alvo for fonte in FONTES_DISPENSAVEIS):
            resultado.append(item)
    return resultado


def obter_argumentos_pyinstaller(caminho_spec: Path | None = None) -> list[str]:
    """
    Monta e retorna a lista de argumentos de linha de comando para o PyInstaller
    apontando para o arquivo de especificação .spec.
    """
    arquivo_alvo = caminho_spec or ARQUIVO_SPEC
    argumentos: list[str] = [
        str(arquivo_alvo),
        "--clean",
        "--noconfirm",
        "--distpath",
        str(DIRETORIO_EDITOR / "dist"),
        "--workpath",
        str(DIRETORIO_EDITOR / "build"),
    ]
    return argumentos


def obter_caminho_icone_alvo(eh_beta: bool) -> tuple[Path | None, Path]:
    """
    Retorna a tupla contendo o caminho do arquivo de ícone alvo (.ico no Windows, .icns no macOS ou None no Linux)
    e o caminho da imagem .png de origem correspondentes ao canal de compilação.
    """
    extensao_icone: str = ""
    if sys.platform == "darwin":
        extensao_icone = ".icns"
    elif sys.platform.startswith("win"):
        extensao_icone = ".ico"
    else:
        # No Linux (binários ELF), o executável não usa arquivo de ícone embutido; o asset principal é o PNG
        caminho_png_linux = (
            DIRETORIO_EDITOR / "recursos_beta" / "logo_app.png"
            if eh_beta
            else DIRETORIO_EDITOR / "recursos" / "logo_app.png"
        )
        return (None, caminho_png_linux)

    nome_icone = f"logo{extensao_icone}"
    if eh_beta:
        return (
            DIRETORIO_EDITOR / "recursos_beta" / nome_icone,
            DIRETORIO_EDITOR / "recursos_beta" / "logo_app.png",
        )
    return (
        DIRETORIO_EDITOR / nome_icone,
        DIRETORIO_EDITOR / "recursos" / "logo_app.png",
    )


def gerar_arquivo_icone(
    caminho_icone: Path,
    caminho_png: Path | None = None,
    force_generation: bool = False,
) -> None:
    """
    Gera o arquivo .ico multi-resolução a partir do logo_app.png caso necessário.
    """
    if not force_generation and caminho_icone.exists():
        print(f"Ícone existente encontrado em {caminho_icone}. Pulando geração.")
        return

    try:
        from PIL import Image

        origem_png = caminho_png or (DIRETORIO_EDITOR / "recursos" / "logo_app.png")
        tamanhos = [16, 32, 48, 64, 128, 256]
        imagens_pil = []
        img_aberta = Image.open(str(origem_png))
        img_rgba = img_aberta.convert("RGBA") if img_aberta.mode != "RGBA" else img_aberta

        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        for tam in tamanhos:
            img_resized = img_rgba.resize((tam, tam), resample_filter)
            imagens_pil.append(img_resized)

        imagens_pil[-1].save(
            str(caminho_icone),
            format="ICO",
            sizes=[(img.width, img.height) for img in imagens_pil],
        )
        print(f"Ícone multi-resolução (16-256px) configurado: {caminho_icone}")
    except Exception as e:
        print(f"Aviso: Não foi possível gerar o arquivo .ico (usando padrão): {e}")


def gerar_arquivo_icone_icns(
    caminho_icns: Path,
    caminho_png: Path | None = None,
    force_generation: bool = False,
) -> None:
    """
    Gera o arquivo .icns a partir do logo_app.png caso necessário para empacotamento no macOS.
    """
    if not force_generation and caminho_icns.exists():
        print(f"Ícone .icns existente encontrado em {caminho_icns}. Pulando geração.")
        return

    try:
        from PIL import Image

        origem_png = caminho_png or (DIRETORIO_EDITOR / "recursos" / "logo_app.png")
        tamanhos = [16, 32, 64, 128, 256, 512]
        imagens_pil = []
        img_aberta = Image.open(str(origem_png))
        img_rgba = img_aberta.convert("RGBA") if img_aberta.mode != "RGBA" else img_aberta

        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        for tam in tamanhos:
            img_resized = img_rgba.resize((tam, tam), resample_filter)
            imagens_pil.append(img_resized)

        imagens_pil[-1].save(
            str(caminho_icns),
            format="ICNS",
            sizes=[(img.width, img.height) for img in imagens_pil],
        )
        print(f"Ícone .icns configurado: {caminho_icns}")
    except Exception as e:
        print(f"Aviso: Não foi possível gerar o arquivo .icns (usando padrão): {e}")


# Pacotes com extensões nativas (C/Rust) que devem usar binary wheels pré-compilados
PACOTES_PREFERIR_WHEELS = (
    "cryptography",
    "cffi",
    "pygit2",
    "pillow",
    "pillow-heif",
    "pydantic-core",
    "pyyaml",
    "ruamel-yaml",
    "ruamel.yaml.clib",
    "protobuf",
    "websockets",
)

# Dependências que não devem ser empacotadas no Flatpak oficial
# (fornecidas pelo runtime io.qt.PySide.BaseApp, ferramentas de compilação ou empacotamento Windows)
PACOTES_DISPENSAVEIS_FLATPAK = (
    "pyside6",
    "shiboken6",
    "pyinstaller",
    "pyinstaller-hooks-contrib",
    "altgraph",
    "macholib",
    "pefile",
    "pywin32-ctypes",
    "grpcio",
    "grpcio-tools",
    "mypy-protobuf",
    "types-protobuf",
)


def gerar_manifesto_dependencias_flatpak(
    caminho_saida: Path | None = None,
    raiz_projeto: Path | None = None,
) -> Path:
    """
    Gera efemeramente o manifesto de fontes de dependências Python (pypi-dependencies.json)
    a partir do lockfile (uv.lock) via 'uv export' e 'flatpak_pip_generator'.
    """
    raiz = raiz_projeto or DIRETORIO_EDITOR.parent
    arquivo_lock = raiz / "uv.lock"
    if not arquivo_lock.exists():
        raise FileNotFoundError(f"Arquivo uv.lock não encontrado em {arquivo_lock}")

    destino = caminho_saida or (DIRETORIO_FLATPAK / "pypi-dependencies.json")
    destino.parent.mkdir(parents=True, exist_ok=True)

    executavel_uv = shutil.which("uv") or "uv"
    resultado_export = subprocess.run(
        [
            executavel_uv,
            "export",
            "--frozen",
            "--only-group",
            "editor",
            "--no-dev",
            "--no-hashes",
        ],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        check=True,
    )

    # Filtra dependências dispensáveis no Linux Flatpak
    linhas_filtradas: list[str] = []
    for linha in resultado_export.stdout.splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa or linha_limpa.startswith("#"):
            continue
        nome_pkg = linha_limpa.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
        if any(disp in nome_pkg for disp in PACOTES_DISPENSAVEIS_FLATPAK):
            continue
        linhas_filtradas.append(linha_limpa)

    with tempfile.NamedTemporaryFile(
        "w", suffix="-requirements.txt", delete=False, encoding="utf-8"
    ) as tmp_req:
        tmp_req.write("\n".join(linhas_filtradas) + "\n")
        caminho_tmp_req = Path(tmp_req.name)

    argumentos_extras: list[str] = []
    executavel_flatpak = shutil.which("flatpak")
    if executavel_flatpak:
        for runtime_candidato in ("org.kde.Sdk//6.11", "org.kde.Platform//6.11"):
            resultado_info = subprocess.run(
                [executavel_flatpak, "info", runtime_candidato],
                capture_output=True,
            )
            if resultado_info.returncode == 0:
                pacotes = ",".join(PACOTES_PREFERIR_WHEELS)
                argumentos_extras = [
                    f"--runtime={runtime_candidato}",
                    f"--prefer-wheels={pacotes}",
                ]
                break

    try:
        nome_base_saida = destino.stem
        diretorio_saida = destino.parent
        caminho_sem_ext = diretorio_saida / nome_base_saida
        comando_generator = [
            executavel_uv,
            "run",
            "--group",
            "editor_deploy_flatpak",
            "python",
            "-m",
            "flatpak_pip_generator",
            f"--requirements-file={caminho_tmp_req}",
            f"--output={caminho_sem_ext}",
        ]
        comando_generator.extend(argumentos_extras)
        subprocess.run(
            comando_generator,
            cwd=str(raiz),
            check=True,
        )
    finally:
        if caminho_tmp_req.exists():
            caminho_tmp_req.unlink()

    if not destino.exists():
        raise FileNotFoundError(f"Falha ao gerar o manifesto de dependências em {destino}")

    return destino


def orquestrar_build_flatpak(
    caminho_manifesto: Path | None = None,
    diretorio_dist: Path | None = None,
    versao: str | None = None,
) -> Path:
    """
    Orquestra a compilação do pacote oficial Flatpak no Linux utilizando flatpak-builder.
    Gera um bundle offline (.flatpak) no diretório de distribuição.
    """
    manifesto = caminho_manifesto or ARQUIVO_MANIFESTO_FLATPAK
    if not manifesto.exists():
        raise FileNotFoundError(f"Manifesto Flatpak não encontrado: {manifesto}")

    executavel_builder = shutil.which("flatpak-builder")
    if not executavel_builder:
        raise RuntimeError(
            "flatpak-builder não encontrado no PATH. Instale o flatpak-builder em sua distribuição Linux "
            "(ex: sudo pacman -S flatpak-builder ou sudo apt install flatpak-builder) para gerar o pacote oficial."
        )

    dist_dir = diretorio_dist or DIRETORIO_DIST
    dist_dir.mkdir(parents=True, exist_ok=True)

    diretorio_build = dist_dir / "flatpak-build"
    diretorio_repo = dist_dir / "flatpak-repo"
    versao_app = versao or obter_versao_projeto()
    bundle_saida = dist_dir / f"EditorAresta-{versao_app}.flatpak"

    caminho_deps = manifesto.parent / "pypi-dependencies.json"
    arquivo_lock = DIRETORIO_EDITOR.parent / "uv.lock"
    deve_gerar_deps = not caminho_deps.exists()
    if not deve_gerar_deps and arquivo_lock.exists():
        try:
            deve_gerar_deps = arquivo_lock.stat().st_mtime > caminho_deps.stat().st_mtime
        except OSError:
            deve_gerar_deps = True

    if deve_gerar_deps:
        gerar_manifesto_dependencias_flatpak(caminho_saida=caminho_deps)

    if bundle_saida.exists():
        bundle_saida.unlink(missing_ok=True)

    print(f"Compilando Flatpak a partir de {manifesto}...")
    subprocess.run(
        [
            executavel_builder,
            "--force-clean",
            "--user",
            "--install-deps-from=flathub",
            "--repo=" + str(diretorio_repo),
            str(diretorio_build),
            str(manifesto),
        ],
        check=True,
    )

    executavel_flatpak = shutil.which("flatpak") or "flatpak"
    subprocess.run(
        [
            executavel_flatpak,
            "build-bundle",
            str(diretorio_repo),
            str(bundle_saida),
            "com.arestaclimb.Editor",
        ],
        check=True,
    )

    print(f"Bundle Flatpak gerado com sucesso: {bundle_saida}")
    return bundle_saida


def executar_build(force_icon_generation: bool = False) -> None:
    """
    Executa o empacotamento do editor para a plataforma atual.
    No Linux, delega integralmente ao flatpak-builder gerando um bundle Flatpak oficial.
    No Windows e macOS, utiliza PyInstaller para gerar o pacote de distribuição.
    """
    if sys.platform.startswith("linux"):
        print("Ambiente Linux: delegando empacotamento oficial para o ecossistema Flatpak...")
        orquestrar_build_flatpak()
        return

    if not ARQUIVO_SPEC.exists():
        raise FileNotFoundError(f"Arquivo de especificação não encontrado: {ARQUIVO_SPEC}")

    eh_beta = os.environ.get("ARESTA_CANAL", "").strip().lower() == "beta"
    caminho_icone, caminho_png = obter_caminho_icone_alvo(eh_beta)
    if sys.platform == "darwin":
        if caminho_icone:
            gerar_arquivo_icone_icns(
                caminho_icone, caminho_png=caminho_png, force_generation=force_icon_generation
            )
        if not eh_beta:
            caminho_icns_recursos = DIRETORIO_EDITOR / "recursos" / "logo.icns"
            gerar_arquivo_icone_icns(
                caminho_icns_recursos,
                caminho_png=caminho_png,
                force_generation=force_icon_generation,
            )
    elif sys.platform.startswith("win"):
        if caminho_icone:
            gerar_arquivo_icone(
                caminho_icone, caminho_png=caminho_png, force_generation=force_icon_generation
            )
        if not eh_beta:
            # Garante cópia espelhada em editor/recursos/logo.ico para empacotamento no bundle
            caminho_icone_recursos = DIRETORIO_EDITOR / "recursos" / "logo.ico"
            gerar_arquivo_icone(
                caminho_icone_recursos,
                caminho_png=caminho_png,
                force_generation=force_icon_generation,
            )

    argumentos = obter_argumentos_pyinstaller(caminho_spec=ARQUIVO_SPEC)

    mod_pyinstaller: Any = sys.modules.get("PyInstaller.__main__")
    if mod_pyinstaller is None:
        try:
            import PyInstaller.__main__

            mod_pyinstaller = PyInstaller.__main__
        except ImportError:
            raise RuntimeError(
                "PyInstaller não está disponível neste ambiente. Ele é necessário para empacotamento em Windows e macOS."
            )
    assert mod_pyinstaller is not None
    mod_pyinstaller.run(argumentos)

    print("Build concluído com sucesso!")


def executar_testes() -> None:
    """
    Executa a checagem estática com Ruff (lint e formatação) e todos os testes do editor com pytest.
    """
    print("\n[1/3] Executando checagem estática com Ruff (lint)...")
    res_lint = subprocess.run([sys.executable, "-m", "ruff", "check", str(DIRETORIO_EDITOR)])
    if res_lint.returncode != 0:
        print("\nFalha na checagem estática do Ruff!")
        print("Dica: Execute 'uv run ruff check --fix' para corrigir problemas automaticamente.")
        sys.exit(res_lint.returncode)

    print("\n[2/3] Executando checagem de formatação com Ruff...")
    res_fmt = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", str(DIRETORIO_EDITOR)]
    )
    if res_fmt.returncode != 0:
        print("\nFalha na formatação do Ruff!")
        print("Dica: Execute 'uv run ruff format' para formatar o código.")
        sys.exit(res_fmt.returncode)

    print(f"\n[3/3] Executando testes unitários do editor em {DIRETORIO_EDITOR}...")
    resultado = pytest.main([str(DIRETORIO_EDITOR), "-v"])

    if resultado == 0:
        print("Todos os testes passaram!")
    else:
        print(f"Alguns testes falharam (código de saída: {resultado})")

    if resultado != 0:
        sys.exit(resultado)


def gerar_tarball_codigo_fonte(
    diretorio_saida: Path | None = None,
    versao: str | None = None,
    raiz_projeto: Path | None = None,
) -> tuple[Path, str]:
    """
    Gera um tarball comprimido (.tar.gz) contendo estritamente os arquivos de código-fonte
    necessários para compilação do Editor Aresta (editor, aresta_api, uv.lock, pyproject.toml),
    excluindo o banco de dados pesado (database/), pastas de build e testes.
    Retorna uma tupla com o caminho do arquivo gerado e seu hash SHA-256.
    """
    import hashlib
    import tarfile

    raiz = raiz_projeto or DIRETORIO_EDITOR.parent
    versao_app = versao or obter_versao_projeto(raiz / "pyproject.toml")
    dist_dir = diretorio_saida or DIRETORIO_DIST
    dist_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = f"EditorAresta-{versao_app}-source.tar.gz"
    caminho_tarball = dist_dir / nome_arquivo

    itens_incluir = [
        "editor",
        "aresta_api",
        "scripts",
        "coleta_de_betas",
        "migracoes",
        "serving",
        "uv.lock",
        "pyproject.toml",
    ]

    def filtro_exclusao(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        caminho_str = tarinfo.name.replace("\\", "/")
        exclusoes = (
            "/__pycache__",
            "__pycache__",
            "/dist",
            "/build",
            "/.flatpak-builder",
            ".flatpak-builder",
            "pypi-dependencies.json",
            "_test.py",
            "conftest.py",
            ".pyc",
        )
        if any(exc in caminho_str for exc in exclusoes):
            return None
        return tarinfo

    with tarfile.open(caminho_tarball, "w:gz") as tar:
        for item in itens_incluir:
            origem = raiz / item
            if origem.exists():
                tar.add(str(origem), arcname=item, filter=filtro_exclusao)

    hasher = hashlib.sha256()
    with open(caminho_tarball, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    hash_sha256 = hasher.hexdigest()

    return caminho_tarball, hash_sha256


def main(argv: list[str] | None = None) -> None:
    """
    Ponto de entrada de linha de comando para o utilitário de build e testes.
    """
    parser = argparse.ArgumentParser(description="Script de build e testes do Editor Aresta")
    parser.add_argument(
        "modo",
        choices=["test", "dist", "flatpak-deps", "source-tarball"],
        help="Modo de operação: 'test' para rodar testes, 'dist' para compilar, 'flatpak-deps' para pypi-dependencies.json, 'source-tarball' para release archive",
    )

    parser.add_argument(
        "--force-icon-generation",
        action="store_true",
        help="Força a geração do arquivo .ico mesmo se ele já existir",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Caminho de saída para o manifesto pypi-dependencies.json (usado com flatpak-deps)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Diretório de saída para o tarball de código-fonte (usado com source-tarball)",
    )

    parser.add_argument(
        "--versao",
        type=str,
        default=None,
        help="Versão para o tarball de código-fonte (usado com source-tarball)",
    )

    args = parser.parse_args(argv)

    if args.modo == "test":
        executar_testes()
    elif args.modo == "dist":
        executar_build(force_icon_generation=args.force_icon_generation)
    elif args.modo == "flatpak-deps":
        gerar_manifesto_dependencias_flatpak(caminho_saida=args.output)
    elif args.modo == "source-tarball":
        tarball, sha256_hash = gerar_tarball_codigo_fonte(
            diretorio_saida=args.output_dir,
            versao=args.versao,
        )
        print(f"Tarball de código-fonte gerado em: {tarball}")
        print(f"SHA-256: {sha256_hash}")


if __name__ == "__main__":
    main()
