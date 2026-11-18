# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import argparse
import hashlib
import importlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

_raiz_repositorio = str(Path(__file__).resolve().parents[1])
if _raiz_repositorio not in sys.path:  # pragma: no cover
    sys.path.insert(0, _raiz_repositorio)

from editor.executor_build_fake import ExecutorBuildProtocolo

# Caminhos padrão do pacote do editor
DIRETORIO_EDITOR = Path(__file__).parent.resolve()
ARQUIVO_MAIN = DIRETORIO_EDITOR / "main.py"
ARQUIVO_SPEC = DIRETORIO_EDITOR / "EditorAresta.spec"
DIRETORIO_DIST = DIRETORIO_EDITOR / "dist"
DIRETORIO_DIST_ONEDIR = DIRETORIO_DIST / "EditorAresta"
DIRETORIO_FLATPAK = DIRETORIO_EDITOR / "flatpak"
ARQUIVO_MANIFESTO_FLATPAK = DIRETORIO_FLATPAK / "com.arestaclimb.Editor.yaml"
LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB = 95.0


class ExecutorBuildPadrao:
    """Implementação real de produção para invocação de processos externos de build e teste."""

    def qual_executavel(self, nome: str) -> str | None:
        return shutil.which(nome)

    def executar_comando(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        capturar_saida: bool = False,
        verificar: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=capturar_saida,
            text=True,
            check=verificar,
        )

    def executar_pyinstaller(self, argumentos: list[str]) -> None:
        getattr(importlib.import_module("PyInstaller.__main__"), "run")(argumentos)

    def executar_pytest(self, argumentos: list[str]) -> int:
        return int(pytest.main(argumentos))


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


# Binários pesados de fallback gráfico do Qt que não são necessários no Windows/macOS moderno
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


def obter_modulos_excluidos() -> list[str]:
    """
    Retorna a lista de módulos pesados de IA, OCR, visão computacional, pacotes de dados
    e submódulos dispensáveis do PySide6 que NÃO pertencem ao grupo 'editor' e não devem
    ser empacotados no executável do editor.
    Nota: 'pymupdf' e 'lxml' pertencem ao grupo 'editor' e NÃO devem ser excluídos.
    """
    return [
        # Bibliotecas pesadas de IA, OCR e Visão Computacional fora do grupo editor
        "paddleocr",
        "paddlex",
        "cv2",
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
    plataforma: str | None = None,
) -> list[Any]:
    """
    Filtra a lista de arquivos de dados do PyInstaller, removendo:
    - cabeçalhos C/C++ de build-time do PyMuPDF (mupdf-devel);
    - famílias de fontes do QtAwesome não utilizadas pelo tema do editor;
    - metadados de pacotes (.dist-info e .egg-info) que violam codesign no macOS;
    - arquivos de teste (*_test.py, test_*, conftest.py, tests/) e bibliotecas test-only (*_fake.py).
    """
    plat = plataforma or sys.platform
    resultado = []
    for item in datas:
        origem = item[0] if isinstance(item, (tuple, list)) and len(item) > 0 else ""
        destino = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else ""
        alvo = f"{origem} {destino}".lower()
        if "mupdf-devel" in alvo:
            continue
        if ".dist-info" in alvo or ".egg-info" in alvo:
            continue
        if (
            "_test.py" in alvo
            or "_fake.py" in alvo
            or "test_" in alvo
            or "conftest.py" in alvo
            or "/tests/" in alvo
            or "\\tests\\" in alvo
        ):
            continue
        if plat == "darwin" and (
            origem.lower().endswith(".ico") or destino.lower().endswith(".ico")
        ):
            continue
        resultado.append(item)
    return resultado


def obter_argumentos_pyinstaller(
    caminho_spec: Path | None = None,
    diretorio_editor: Path | None = None,
) -> list[str]:
    """
    Monta e retorna a lista de argumentos de linha de comando para o PyInstaller
    apontando para o arquivo de especificação .spec.
    """
    dir_ed = diretorio_editor or DIRETORIO_EDITOR
    arquivo_alvo = caminho_spec or (dir_ed / "EditorAresta.spec")
    return [
        str(arquivo_alvo),
        "--clean",
        "--noconfirm",
        "--distpath",
        str(dir_ed / "dist"),
        "--workpath",
        str(dir_ed / "build"),
    ]


def obter_caminho_icone_alvo(
    eh_beta: bool,
    plataforma: str | None = None,
    diretorio_editor: Path | None = None,
) -> tuple[Path | None, Path]:
    """
    Retorna a tupla contendo o caminho do arquivo de ícone alvo (.ico no Windows, .icns no macOS ou None no Linux)
    e o caminho da imagem .png de origem correspondentes ao canal de compilação.
    """
    plat = plataforma or sys.platform
    dir_ed = diretorio_editor or DIRETORIO_EDITOR
    if plat == "darwin":
        extensao_icone = ".icns"
    elif plat.startswith("win"):
        extensao_icone = ".ico"
    else:
        caminho_png_linux = (
            dir_ed / "recursos_beta" / "logo_app.png"
            if eh_beta
            else dir_ed / "recursos" / "logo_app.png"
        )
        return (None, caminho_png_linux)

    nome_icone = f"logo{extensao_icone}"
    if eh_beta:
        return (
            dir_ed / "recursos_beta" / nome_icone,
            dir_ed / "recursos_beta" / "logo_app.png",
        )
    return (
        dir_ed / nome_icone,
        dir_ed / "recursos" / "logo_app.png",
    )


def _salvar_icone_multirresolucao(
    caminho_saida: Path,
    caminho_png: Path,
    formato: str,
    tamanhos: list[int],
    force_generation: bool,
) -> None:
    if not force_generation and caminho_saida.exists():
        print(f"Ícone existente encontrado em {caminho_saida}. Pulando geração.")
        return

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(str(caminho_png)) as img_aberta:
        img_rgba = img_aberta.convert("RGBA") if img_aberta.mode != "RGBA" else img_aberta.copy()

    imagens_pil = [img_rgba.resize((tam, tam), Image.Resampling.LANCZOS) for tam in tamanhos]
    imagens_pil[-1].save(
        str(caminho_saida),
        format=formato,
        sizes=[(img.width, img.height) for img in imagens_pil],
    )
    print(f"Ícone ({formato}) configurado: {caminho_saida}")


def gerar_arquivo_icone(
    caminho_icone: Path,
    caminho_png: Path | None = None,
    force_generation: bool = False,
) -> None:
    """Gera o arquivo .ico multi-resolução a partir do logo_app.png caso necessário."""
    origem_png = caminho_png or (DIRETORIO_EDITOR / "recursos" / "logo_app.png")
    _salvar_icone_multirresolucao(
        caminho_icone,
        origem_png,
        formato="ICO",
        tamanhos=[16, 32, 48, 64, 128, 256],
        force_generation=force_generation,
    )


def gerar_arquivo_icone_icns(
    caminho_icns: Path,
    caminho_png: Path | None = None,
    force_generation: bool = False,
) -> None:
    """Gera o arquivo .icns a partir do logo_app.png caso necessário para empacotamento no macOS."""
    origem_png = caminho_png or (DIRETORIO_EDITOR / "recursos" / "logo_app.png")
    _salvar_icone_multirresolucao(
        caminho_icns,
        origem_png,
        formato="ICNS",
        tamanhos=[16, 32, 64, 128, 256, 512],
        force_generation=force_generation,
    )


# Pacotes com extensões nativas (C/Rust) que devem usar binary wheels pré-compilados
PACOTES_PREFERIR_WHEELS = (
    "brotli",
    "cffi",
    "charset-normalizer",
    "cryptography",
    "ddgs",
    "lxml",
    "pillow",
    "pillow-heif",
    "primp",
    "protobuf",
    "pydantic-core",
    "pygit2",
    "pymupdf",
    "pyyaml",
    "websockets",
    "zstandard",
)

# Dependências que não devem ser empacotadas no Flatpak oficial
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
    executor: ExecutorBuildProtocolo | None = None,
) -> Path:
    """
    Gera efemeramente o manifesto de fontes de dependências Python (pypi-dependencies.json)
    a partir do lockfile (uv.lock) via 'uv export' e 'flatpak_pip_generator'.
    """
    exec_proc = executor or ExecutorBuildPadrao()
    raiz = raiz_projeto or DIRETORIO_EDITOR.parent
    arquivo_lock = raiz / "uv.lock"
    if not arquivo_lock.exists():
        raise FileNotFoundError(f"Arquivo uv.lock não encontrado em {arquivo_lock}")

    destino = caminho_saida or (DIRETORIO_FLATPAK / "pypi-dependencies.json")
    destino.parent.mkdir(parents=True, exist_ok=True)

    executavel_uv = exec_proc.qual_executavel("uv") or "uv"
    resultado_export = exec_proc.executar_comando(
        [
            executavel_uv,
            "export",
            "--frozen",
            "--only-group",
            "editor",
            "--no-dev",
            "--no-hashes",
        ],
        cwd=raiz,
        capturar_saida=True,
        verificar=True,
    )

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
    executavel_flatpak = exec_proc.qual_executavel("flatpak")
    if executavel_flatpak:
        for runtime_candidato in ("org.kde.Sdk//6.11", "org.kde.Platform//6.11"):
            resultado_info = exec_proc.executar_comando(
                [executavel_flatpak, "info", runtime_candidato],
                capturar_saida=True,
            )
            if resultado_info.returncode == 0:
                pacotes = ",".join(PACOTES_PREFERIR_WHEELS)
                argumentos_extras = [
                    f"--runtime={runtime_candidato}",
                    f"--prefer-wheels={pacotes}",
                ]
                break

    try:
        caminho_sem_ext = destino.parent / destino.stem
        comando_generator = [
            executavel_uv,
            "run",
            "--group",
            "editor_deploy",
            "python",
            "-m",
            "flatpak_pip_generator",
            f"--requirements-file={caminho_tmp_req}",
            f"--output={caminho_sem_ext}",
        ]
        comando_generator.extend(argumentos_extras)
        exec_proc.executar_comando(
            comando_generator,
            cwd=raiz,
            verificar=True,
        )
    finally:
        caminho_tmp_req.unlink(missing_ok=True)

    if not destino.exists():
        raise FileNotFoundError(f"Falha ao gerar o manifesto de dependências em {destino}")

    return destino


def orquestrar_build_flatpak(
    caminho_manifesto: Path | None = None,
    diretorio_dist: Path | None = None,
    versao: str | None = None,
    raiz_projeto: Path | None = None,
    executor: ExecutorBuildProtocolo | None = None,
) -> Path:
    """
    Orquestra a compilação do pacote oficial Flatpak no Linux utilizando flatpak-builder.
    Gera um bundle offline (.flatpak) no diretório de distribuição.
    """
    exec_proc = executor or ExecutorBuildPadrao()
    raiz = raiz_projeto or DIRETORIO_EDITOR.parent
    manifesto = caminho_manifesto or (raiz / "editor" / "flatpak" / "com.arestaclimb.Editor.yaml")
    if not manifesto.exists():
        raise FileNotFoundError(f"Manifesto Flatpak não encontrado: {manifesto}")

    executavel_builder = exec_proc.qual_executavel("flatpak-builder")
    if not executavel_builder:
        raise RuntimeError(
            "flatpak-builder não encontrado no PATH. Instale o flatpak-builder em sua distribuição Linux "
            "(ex: sudo pacman -S flatpak-builder ou sudo apt install flatpak-builder) para gerar o pacote oficial."
        )

    dist_dir = diretorio_dist or (raiz / "editor" / "dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    diretorio_build = dist_dir / "flatpak-build"
    diretorio_repo = dist_dir / "flatpak-repo"
    versao_app = versao or obter_versao_projeto(raiz / "pyproject.toml")
    bundle_saida = dist_dir / f"EditorAresta-{versao_app}.flatpak"

    caminho_deps = manifesto.parent / "pypi-dependencies.json"
    arquivo_lock = raiz / "uv.lock"
    deve_gerar_deps = not caminho_deps.exists() or (
        arquivo_lock.exists() and arquivo_lock.stat().st_mtime > caminho_deps.stat().st_mtime
    )

    if deve_gerar_deps:
        gerar_manifesto_dependencias_flatpak(
            caminho_saida=caminho_deps, raiz_projeto=raiz, executor=exec_proc
        )

    bundle_saida.unlink(missing_ok=True)

    print(f"Compilando Flatpak a partir de {manifesto}...")
    exec_proc.executar_comando(
        [
            executavel_builder,
            "--force-clean",
            "--user",
            "--install-deps-from=flathub",
            "--repo=" + str(diretorio_repo),
            str(diretorio_build),
            str(manifesto),
        ],
        verificar=True,
    )

    executavel_flatpak = exec_proc.qual_executavel("flatpak") or "flatpak"
    exec_proc.executar_comando(
        [
            executavel_flatpak,
            "build-bundle",
            str(diretorio_repo),
            str(bundle_saida),
            "com.arestaclimb.Editor",
        ],
        verificar=True,
    )

    print(f"Bundle Flatpak gerado com sucesso: {bundle_saida}")
    return bundle_saida


def executar_build(
    force_icon_generation: bool = False,
    *,
    plataforma: str | None = None,
    canal: str | None = None,
    diretorio_editor: Path | None = None,
    executor: ExecutorBuildProtocolo | None = None,
) -> None:
    """
    Executa o empacotamento do editor para a plataforma informada (ou atual).
    No Linux, delega integralmente ao flatpak-builder gerando um bundle Flatpak oficial.
    No Windows e macOS, utiliza PyInstaller para gerar o pacote de distribuição onedir.
    """
    exec_proc = executor or ExecutorBuildPadrao()
    plat = plataforma or sys.platform
    dir_ed = diretorio_editor or DIRETORIO_EDITOR
    raiz = dir_ed.parent

    if plat.startswith("linux"):
        print("Ambiente Linux: delegando empacotamento oficial para o ecossistema Flatpak...")
        orquestrar_build_flatpak(
            caminho_manifesto=dir_ed / "flatpak" / "com.arestaclimb.Editor.yaml",
            diretorio_dist=dir_ed / "dist",
            raiz_projeto=raiz,
            executor=exec_proc,
        )
        return

    arquivo_spec = dir_ed / "EditorAresta.spec"
    if not arquivo_spec.exists():
        raise FileNotFoundError(f"Arquivo de especificação não encontrado: {arquivo_spec}")

    canal_efetivo = (canal if canal is not None else os.environ.get("ARESTA_CANAL", "")).strip()
    eh_beta = canal_efetivo.lower() == "beta"
    caminho_icone, caminho_png = obter_caminho_icone_alvo(
        eh_beta=eh_beta, plataforma=plat, diretorio_editor=dir_ed
    )
    assert caminho_icone is not None
    if plat == "darwin":
        gerar_arquivo_icone_icns(
            caminho_icone, caminho_png=caminho_png, force_generation=force_icon_generation
        )
        if not eh_beta:
            gerar_arquivo_icone_icns(
                dir_ed / "recursos" / "logo.icns",
                caminho_png=caminho_png,
                force_generation=force_icon_generation,
            )
    else:
        gerar_arquivo_icone(
            caminho_icone, caminho_png=caminho_png, force_generation=force_icon_generation
        )
        if not eh_beta:
            gerar_arquivo_icone(
                dir_ed / "recursos" / "logo.ico",
                caminho_png=caminho_png,
                force_generation=force_icon_generation,
            )

    argumentos = obter_argumentos_pyinstaller(caminho_spec=arquivo_spec, diretorio_editor=dir_ed)
    exec_proc.executar_pyinstaller(argumentos)
    print("Build concluído com sucesso!")


def executar_testes(
    *,
    diretorio_editor: Path | None = None,
    executor: ExecutorBuildProtocolo | None = None,
) -> None:
    """
    Executa a checagem estática com Ruff (lint e formatação) e todos os testes do editor com pytest.
    """
    exec_proc = executor or ExecutorBuildPadrao()
    dir_ed = diretorio_editor or DIRETORIO_EDITOR

    print("\n[1/3] Executando checagem estática com Ruff (lint)...")
    res_lint = exec_proc.executar_comando([sys.executable, "-m", "ruff", "check", str(dir_ed)])
    if res_lint.returncode != 0:
        print("\nFalha na checagem estática do Ruff!")
        sys.exit(res_lint.returncode)

    print("\n[2/3] Executando checagem de formatação com Ruff...")
    res_fmt = exec_proc.executar_comando(
        [sys.executable, "-m", "ruff", "format", "--check", str(dir_ed)]
    )
    if res_fmt.returncode != 0:
        print("\nFalha na formatação do Ruff!")
        sys.exit(res_fmt.returncode)

    print(f"\n[3/3] Executando testes unitários do editor em {dir_ed}...")
    resultado = exec_proc.executar_pytest([str(dir_ed), "-v"])
    if resultado != 0:
        print(f"Alguns testes falharam (código de saída: {resultado})")
        sys.exit(resultado)

    print("Todos os testes passaram!")


def gerar_tarball_codigo_fonte(
    diretorio_saida: Path | None = None,
    versao: str | None = None,
    raiz_projeto: Path | None = None,
) -> tuple[Path, str]:
    """
    Gera um tarball comprimido (.tar.gz) contendo estritamente os arquivos de código-fonte
    necessários para compilação do Editor Aresta, excluindo database/, pastas de build, testes e fakes.
    """
    raiz = raiz_projeto or DIRETORIO_EDITOR.parent
    versao_app = versao or obter_versao_projeto(raiz / "pyproject.toml")
    dist_dir = diretorio_saida or (raiz / "editor" / "dist")
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
            "_fake.py",
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
    return caminho_tarball, hasher.hexdigest()


def main(
    argv: list[str] | None = None,
    *,
    plataforma: str | None = None,
    diretorio_editor: Path | None = None,
    raiz_projeto: Path | None = None,
    executor: ExecutorBuildProtocolo | None = None,
) -> None:
    """Ponto de entrada de linha de comando para o utilitário de build e testes."""
    parser = argparse.ArgumentParser(description="Script de build e testes do Editor Aresta")
    parser.add_argument(
        "modo",
        choices=["test", "dist", "flatpak-deps", "source-tarball"],
        help="Modo de operação: 'test', 'dist', 'flatpak-deps' ou 'source-tarball'",
    )
    parser.add_argument(
        "--force-icon-generation",
        action="store_true",
        help="Força a geração do arquivo de ícone mesmo se ele já existir",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Caminho de saída para o manifesto pypi-dependencies.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Diretório de saída para o tarball de código-fonte",
    )
    parser.add_argument(
        "--versao",
        type=str,
        default=None,
        help="Versão para o tarball de código-fonte",
    )

    args = parser.parse_args(argv)

    if args.modo == "test":
        executar_testes(diretorio_editor=diretorio_editor, executor=executor)
    elif args.modo == "dist":
        executar_build(
            force_icon_generation=args.force_icon_generation,
            plataforma=plataforma,
            diretorio_editor=diretorio_editor,
            executor=executor,
        )
    elif args.modo == "flatpak-deps":
        gerar_manifesto_dependencias_flatpak(
            caminho_saida=args.output,
            raiz_projeto=raiz_projeto,
            executor=executor,
        )
    else:
        tarball, sha256_hash = gerar_tarball_codigo_fonte(
            diretorio_saida=args.output_dir,
            versao=args.versao,
            raiz_projeto=raiz_projeto,
        )
        print(f"Tarball de código-fonte gerado em: {tarball}")
        print(f"SHA-256: {sha256_hash}")


if __name__ == "__main__":  # pragma: no cover
    main()
