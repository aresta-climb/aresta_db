# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from pathlib import Path
from editor.build import (
    executar_build,
    DIRETORIO_EDITOR,
    ARQUIVO_SPEC,
    obter_modulos_excluidos,
    filtrar_binarios_desnecessarios,
    filtrar_datas_desnecessarios,
    obter_argumentos_pyinstaller,
    executar_testes,
    main,
    LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB,
)


def test_obter_modulos_excluidos_contem_ia_ocr_pandas_e_qt_desnecessario():
    """Valida se a lista de exclusões contém bibliotecas de IA, OCR, Pandas e módulos dispensáveis do Qt."""
    excluidos = obter_modulos_excluidos()
    assert isinstance(excluidos, list)
    assert len(excluidos) > 0

    # Verifica bibliotecas de IA, OCR, PDF e Visão Computacional
    assert "paddleocr" in excluidos
    assert "paddlex" in excluidos
    assert "cv2" in excluidos
    assert "pymupdf" in excluidos
    assert "fitz" in excluidos
    assert "pypdfium2" in excluidos
    assert "scipy" in excluidos
    assert "tokenizers" in excluidos
    assert "grpc" in excluidos
    assert "modelscope" in excluidos

    # Verifica pacotes de dados transitivos não utilizados pelo editor
    assert "pandas" in excluidos
    assert "openpyxl" in excluidos
    assert "sqlalchemy" in excluidos
    assert "jinja2" in excluidos
    assert "fsspec" in excluidos
    assert "psutil" in excluidos
    assert "sqlite3" in excluidos

    # Verifica submódulos do PySide6 dispensáveis na aplicação QtWidgets
    assert "PySide6.QtQuick" in excluidos
    assert "PySide6.QtQml" in excluidos
    assert "PySide6.QtPdf" in excluidos
    assert "PySide6.QtOpenGL" in excluidos
    assert "PySide6.Qt3DCore" in excluidos
    assert "PySide6.QtWebEngineCore" in excluidos


def test_filtrar_binarios_desnecessarios_remove_opengl_software_qdirect2d_e_qml():
    """Valida se filtrar_binarios_desnecessarios remove opengl32sw, qdirect2d e DLLs de QML/Quick."""
    binarios_mock = [
        ("PySide6\\opengl32sw.dll", "C:\\fake\\opengl32sw.dll", "BINARY"),
        ("PySide6\\plugins\\platforms\\qdirect2d.dll", "C:\\fake\\qdirect2d.dll", "BINARY"),
        ("PySide6\\Qt6Core.dll", "C:\\fake\\Qt6Core.dll", "BINARY"),
        ("PySide6\\Qt6Widgets.dll", "C:\\fake\\Qt6Widgets.dll", "BINARY"),
        ("PySide6\\Qt6Quick.dll", "C:\\fake\\Qt6Quick.dll", "BINARY"),
        ("PySide6\\Qt6Qml.dll", "C:\\fake\\Qt6Qml.dll", "BINARY"),
        ("PySide6\\Qt6Pdf.dll", "C:\\fake\\Qt6Pdf.dll", "BINARY"),
        ("pygit2\\git2.dll", "C:\\fake\\git2.dll", "BINARY"),
    ]

    filtrados = filtrar_binarios_desnecessarios(binarios_mock)
    nomes_restantes = [b[0] for b in filtrados]

    # Verifica remoção de opengl32sw, qdirect2d e DLLs do QML/Quick/Pdf
    assert "PySide6\\opengl32sw.dll" not in nomes_restantes
    assert "PySide6\\plugins\\platforms\\qdirect2d.dll" not in nomes_restantes
    assert "PySide6\\Qt6Quick.dll" not in nomes_restantes
    assert "PySide6\\Qt6Qml.dll" not in nomes_restantes
    assert "PySide6\\Qt6Pdf.dll" not in nomes_restantes

    # Verifica manutenção de binários essenciais
    assert "PySide6\\Qt6Core.dll" in nomes_restantes
    assert "PySide6\\Qt6Widgets.dll" in nomes_restantes
    assert "pygit2\\git2.dll" in nomes_restantes


def test_filtrar_datas_desnecessarios_remove_fontes_nao_utilizadas():
    """Valida se filtrar_datas_desnecessarios remove fontes dispensáveis do QtAwesome e mantém as essenciais."""
    datas_mock = [
        ("C:\\fake\\qtawesome\\fonts\\phosphor-1.3.0.ttf", "qtawesome\\fonts\\phosphor-1.3.0.ttf", "DATA"),
        ("C:\\fake\\qtawesome\\fonts\\materialdesignicons6-webfont-6.9.96.ttf", "qtawesome\\fonts\\materialdesignicons6-webfont-6.9.96.ttf", "DATA"),
        ("C:\\fake\\qtawesome\\fonts\\fontawesome5-solid-webfont-5.15.4.ttf", "qtawesome\\fonts\\fontawesome5-solid-webfont-5.15.4.ttf", "DATA"),
        ("C:\\fake\\qtawesome\\fonts\\fontawesome5-brands-webfont-5.15.4.ttf", "qtawesome\\fonts\\fontawesome5-brands-webfont-5.15.4.ttf", "DATA"),
        ("C:\\fake\\editor\\recursos\\logo_app.png", "recursos\\logo_app.png", "DATA"),
    ]

    filtrados = filtrar_datas_desnecessarios(datas_mock)
    destinos_restantes = [d[1] for d in filtrados]

    # Verifica remoção de fontes não usadas no tema do editor
    assert "qtawesome\\fonts\\phosphor-1.3.0.ttf" not in destinos_restantes
    assert "qtawesome\\fonts\\materialdesignicons6-webfont-6.9.96.ttf" not in destinos_restantes

    # Verifica manutenção das fontes do FontAwesome 5 e dos recursos do app
    assert "qtawesome\\fonts\\fontawesome5-solid-webfont-5.15.4.ttf" in destinos_restantes
    assert "qtawesome\\fonts\\fontawesome5-brands-webfont-5.15.4.ttf" in destinos_restantes
    assert "recursos\\logo_app.png" in destinos_restantes


def test_obter_argumentos_pyinstaller_usa_arquivo_spec():
    """Valida se os argumentos para o PyInstaller apontam para o arquivo de especificação .spec."""
    args = obter_argumentos_pyinstaller()

    assert str(ARQUIVO_SPEC) in args
    assert "--clean" in args
    assert "--noconfirm" in args
    assert "--distpath" in args
    assert "--workpath" in args


def test_executar_build_executa_pyinstaller_com_spec():
    """Valida se executar_build gera o ícone e executa o PyInstaller apontando para o spec."""
    with patch("PyInstaller.__main__.run") as mock_run:
        with patch("PIL.Image.open") as mock_image_open:
            with patch("pathlib.Path.exists", return_value=True):
                mock_img = MagicMock()
                mock_img.mode = "RGBA"
                mock_img.width = 16
                mock_img.height = 16
                mock_img.resize.return_value = mock_img
                mock_image_open.return_value = mock_img
                executar_build(force_icon_generation=True)

            assert mock_img.resize.call_count == 6
            assert mock_img.save.call_count == 1

            argumentos_passados = mock_run.call_args[0][0]
            assert str(ARQUIVO_SPEC) in argumentos_passados
            assert "--clean" in argumentos_passados
            assert "--noconfirm" in argumentos_passados


def test_executar_build_falha_se_spec_nao_existe():
    """Valida se o build interrompe se o EditorAresta.spec sumir."""
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            executar_build()


def test_executar_build_pula_geracao_se_icone_existe():
    """Valida se pula a geração de imagem se o logo.ico já existir."""
    with patch("PyInstaller.__main__.run"):
        with patch("PIL.Image.open") as mock_image_open:
            with patch("pathlib.Path.exists", return_value=True):
                executar_build(force_icon_generation=False)

            mock_image_open.assert_not_called()


def test_executar_build_trata_excecao_na_geracao_de_icone():
    """Valida o tratamento gracioso caso a geração do ícone lance exceção."""
    with patch("PyInstaller.__main__.run"):
        with patch("pathlib.Path.exists", side_effect=lambda: True):
            # Simula erro ao abrir a imagem
            with patch("PIL.Image.open", side_effect=Exception("Erro de leitura")):
                # Não deve levantar exceção não tratada
                executar_build(force_icon_generation=True)


def test_executar_testes_sucesso():
    """Valida chamada do pytest retornando 0."""
    with patch("pytest.main", return_value=0):
        # Não deve lançar SystemExit com erro
        executar_testes()


def test_executar_testes_falha():
    """Valida chamada do pytest retornando código de erro."""
    with patch("pytest.main", return_value=1):
        with pytest.raises(SystemExit) as exc_info:
            executar_testes()
        assert exc_info.value.code == 1


def test_main_cli_dispatch():
    """Valida o despachante da linha de comando."""
    with patch("editor.build.executar_testes") as mock_testes:
        main(["test"])
        mock_testes.assert_called_once()

    with patch("editor.build.executar_build") as mock_build:
        main(["dist", "--force-icon-generation"])
        mock_build.assert_called_once_with(force_icon_generation=True)


def test_executar_modulo_como_script():
    """Valida execução do bloco __main__ quando executado como script."""
    import runpy
    with patch("sys.argv", ["build.py", "test"]):
        with patch("pytest.main", return_value=0):
            runpy.run_path(str(DIRETORIO_EDITOR / "build.py"), run_name="__main__")


def test_validacao_limite_tamanho_executavel_se_existir():
    """Valida que o executável gerado em dist/ não ultrapassa o limite máximo de tamanho."""
    caminho_exe = DIRETORIO_EDITOR / "dist" / "EditorAresta.exe"
    if caminho_exe.exists():
        tamanho_mb = caminho_exe.stat().st_size / (1024 * 1024)
        assert tamanho_mb <= LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB, (
            f"Executável EditorAresta.exe excedeu o limite máximo: {tamanho_mb:.2f}MB > {LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB}MB"
        )
