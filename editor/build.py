# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, List, Tuple, Any
import PyInstaller.__main__  # type: ignore[import-untyped]
import os
import sys
import argparse
import pytest
from pathlib import Path


# Caminhos
DIRETORIO_EDITOR = Path(__file__).parent.resolve()
ARQUIVO_MAIN = DIRETORIO_EDITOR / "main.py"
ARQUIVO_SPEC = DIRETORIO_EDITOR / "EditorAresta.spec"
LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB = 95.0

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

# Famílias de fontes de ícones do QtAwesome que não são utilizadas pelo tema do editor
FONTES_DISPENSAVEIS = (
    "materialdesignicons",
    "phosphor",
    "remixicon",
    "codicon",
    "elusiveicons",
)


def obter_modulos_excluidos() -> List[str]:
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
    binarios: List[Any],
) -> List[Any]:
    """
    Filtra a lista de binários do PyInstaller, removendo DLLs de fallback de hardware
    e módulos do Qt sabidamente dispensáveis para reduzir o tamanho final do executável.
    """
    resultado = []
    for item in binarios:
        nome_binario = item[0] if isinstance(item, (tuple, list)) and len(item) > 0 else ""
        if not any(dispensavel.lower() in nome_binario.lower() for dispensavel in BINARIOS_DISPENSAVEIS):
            resultado.append(item)
    return resultado


def filtrar_datas_desnecessarios(
    datas: List[Any],
) -> List[Any]:
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


def obter_argumentos_pyinstaller(caminho_spec: Optional[Path] = None) -> List[str]:
    """
    Monta e retorna a lista de argumentos de linha de comando para o PyInstaller
    apontando para o arquivo de especificação .spec.
    """
    arquivo_alvo = caminho_spec or ARQUIVO_SPEC
    argumentos: List[str] = [
        str(arquivo_alvo),
        "--clean",
        "--noconfirm",
        "--distpath", str(DIRETORIO_EDITOR / "dist"),
        "--workpath", str(DIRETORIO_EDITOR / "build"),
    ]
    return argumentos


def gerar_arquivo_icone(caminho_icone: Path, force_generation: bool = False) -> None:
    """
    Gera o arquivo .ico multi-resolução a partir do logo_app.png caso necessário.
    """
    if not force_generation and caminho_icone.exists():
        print(f"Ícone existente encontrado em {caminho_icone}. Pulando geração.")
        return

    try:
        from PIL import Image

        caminho_png = DIRETORIO_EDITOR / "recursos" / "logo_app.png"
        tamanhos = [16, 32, 48, 64, 128, 256]
        imagens_pil = []
        img_aberta = Image.open(str(caminho_png))
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


def executar_build(force_icon_generation: bool = False) -> None:
    """
    Executa o empacotamento otimizado do editor utilizando PyInstaller a partir do arquivo .spec.
    Gera um executável standalone enxuto na pasta dist/.
    """
    if not ARQUIVO_SPEC.exists():
        raise FileNotFoundError(f"Arquivo de especificação não encontrado: {ARQUIVO_SPEC}")

    caminho_icone = DIRETORIO_EDITOR / "logo.ico"
    gerar_arquivo_icone(caminho_icone, force_generation=force_icon_generation)

    argumentos = obter_argumentos_pyinstaller(caminho_spec=ARQUIVO_SPEC)

    print(f"Iniciando build do Editor Aresta a partir de {ARQUIVO_SPEC}...")
    PyInstaller.__main__.run(argumentos)
    print("Build concluído com sucesso!")


def executar_testes() -> None:
    """
    Executa todos os testes do editor utilizando pytest.
    """
    print(f"Executando testes em {DIRETORIO_EDITOR}...")
    resultado = pytest.main([str(DIRETORIO_EDITOR), "-v"])

    if resultado == 0:
        print("Todos os testes passaram!")
    else:
        print(f"Alguns testes falharam (código de saída: {resultado})")

    if resultado != 0:
        sys.exit(resultado)


def main(argv: Optional[List[str]] = None) -> None:
    """
    Ponto de entrada de linha de comando para o utilitário de build e testes.
    """
    parser = argparse.ArgumentParser(description="Script de build e testes do Editor Aresta")
    parser.add_argument(
        "modo",
        choices=["test", "dist"],
        help="Modo de operação: 'test' para rodar testes, 'dist' para compilar o executável",
    )

    parser.add_argument(
        "--force-icon-generation",
        action="store_true",
        help="Força a geração do arquivo .ico mesmo se ele já existir",
    )

    args = parser.parse_args(argv)

    if args.modo == "test":
        executar_testes()
    elif args.modo == "dist":
        executar_build(force_icon_generation=args.force_icon_generation)


if __name__ == "__main__":
    main()
