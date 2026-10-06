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

            # 6 tamanhos redimensionados para editor/logo.ico e 6 para editor/recursos/logo.ico
            assert mock_img.resize.call_count == 12
            assert mock_img.save.call_count == 2

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


def test_obter_caminho_icone_alvo_producao():
    """Garante que a resolução de ícone no canal de produção aponte para recursos padrão."""
    from editor.build import obter_caminho_icone_alvo

    ico, png = obter_caminho_icone_alvo(eh_beta=False)
    assert ico == DIRETORIO_EDITOR / "logo.ico"
    assert png == DIRETORIO_EDITOR / "recursos" / "logo_app.png"


def test_obter_caminho_icone_alvo_beta():
    """Garante que a resolução de ícone no canal Beta aponte para recursos_beta."""
    from editor.build import obter_caminho_icone_alvo

    ico, png = obter_caminho_icone_alvo(eh_beta=True)
    assert ico == DIRETORIO_EDITOR / "recursos_beta" / "logo.ico"
    assert png == DIRETORIO_EDITOR / "recursos_beta" / "logo_app.png"


def test_executar_build_canal_beta():
    """Valida se executar_build em canal beta aciona o caminho correto de ícone beta."""
    with patch.dict(os.environ, {"ARESTA_CANAL": "beta"}):
        with patch("PyInstaller.__main__.run"):
            with patch("editor.build.gerar_arquivo_icone") as mock_gerar_ico:
                with patch("pathlib.Path.exists", return_value=True):
                    executar_build()
                    mock_gerar_ico.assert_called_once_with(
                        DIRETORIO_EDITOR / "recursos_beta" / "logo.ico",
                        caminho_png=DIRETORIO_EDITOR / "recursos_beta" / "logo_app.png",
                        force_generation=False,
                    )


def test_spec_configura_modo_onedir_com_collect_e_sem_upx():
    """Valida se EditorAresta.spec está configurado no modo onedir com COLLECT e upx=False."""
    conteudo_spec = ARQUIVO_SPEC.read_text(encoding="utf-8")
    assert "COLLECT(" in conteudo_spec, "EditorAresta.spec deve definir bloco COLLECT para distribuição onedir"
    assert "upx=False" in conteudo_spec, "EditorAresta.spec deve desativar UPX em tempo de execução"
    assert "upx=True" not in conteudo_spec, "EditorAresta.spec não deve conter upx=True"
    assert "exclude_binaries=True" in conteudo_spec, "EXE deve conter exclude_binaries=True para modo onedir"


def test_obter_diretorio_distribuicao_onedir():
    """Valida o diretório de destino da distribuição onedir."""
    from editor.build import obter_diretorio_distribuicao_onedir, DIRETORIO_DIST_ONEDIR
    diretorio = obter_diretorio_distribuicao_onedir()
    assert diretorio == DIRETORIO_EDITOR / "dist" / "EditorAresta"
    assert DIRETORIO_DIST_ONEDIR == DIRETORIO_EDITOR / "dist" / "EditorAresta"


def test_filtrar_binarios_desnecessarios_unix_so_e_dylib():
    """Valida se filtrar_binarios_desnecessarios remove .so e .dylib de QML/Quick/Pdf."""
    binarios_mock = [
        ("PySide6/libQt6Quick.so.6", "/fake/libQt6Quick.so.6", "BINARY"),
        ("PySide6/libQt6Qml.so.6", "/fake/libQt6Qml.so.6", "BINARY"),
        ("PySide6/libQt6Pdf.dylib", "/fake/libQt6Pdf.dylib", "BINARY"),
        ("PySide6/libQt6Quick.dylib", "/fake/libQt6Quick.dylib", "BINARY"),
        ("PySide6/libQt6Core.so.6", "/fake/libQt6Core.so.6", "BINARY"),
        ("PySide6/libQt6Widgets.dylib", "/fake/libQt6Widgets.dylib", "BINARY"),
        ("pygit2/_pygit2.so", "/fake/_pygit2.so", "BINARY"),
    ]

    filtrados = filtrar_binarios_desnecessarios(binarios_mock)
    nomes_restantes = [b[0] for b in filtrados]

    assert "PySide6/libQt6Quick.so.6" not in nomes_restantes
    assert "PySide6/libQt6Qml.so.6" not in nomes_restantes
    assert "PySide6/libQt6Pdf.dylib" not in nomes_restantes
    assert "PySide6/libQt6Quick.dylib" not in nomes_restantes

    assert "PySide6/libQt6Core.so.6" in nomes_restantes
    assert "PySide6/libQt6Widgets.dylib" in nomes_restantes
    assert "pygit2/_pygit2.so" in nomes_restantes




def test_gerar_arquivo_icone_icns_sucesso():
    """Valida se gerar_arquivo_icone_icns converte PNG para ICNS multi-resolução."""
    from editor.build import gerar_arquivo_icone_icns

    with patch("PIL.Image.open") as mock_open:
        mock_img = MagicMock()
        mock_img.mode = "RGBA"
        mock_img.width = 16
        mock_img.height = 16
        mock_img.resize.return_value = mock_img
        mock_open.return_value = mock_img

        caminho_icns = DIRETORIO_EDITOR / "logo.icns"
        with patch.object(Path, "exists", return_value=False):
            gerar_arquivo_icone_icns(caminho_icns, force_generation=True)

        assert mock_img.resize.call_count == 6
        mock_img.save.assert_called_once()
        args, kwargs = mock_img.save.call_args
        assert kwargs.get("format") == "ICNS"


def test_gerar_arquivo_icone_icns_pula_se_existir():
    """Valida se pula a geração de .icns se ele já existir e force_generation for False."""
    from editor.build import gerar_arquivo_icone_icns

    with patch("PIL.Image.open") as mock_open:
        with patch.object(Path, "exists", return_value=True):
            gerar_arquivo_icone_icns(DIRETORIO_EDITOR / "logo.icns", force_generation=False)
        mock_open.assert_not_called()


def test_gerar_arquivo_icone_icns_trata_excecao():
    """Valida tratamento seguro contra falhas na geração de .icns."""
    from editor.build import gerar_arquivo_icone_icns

    with patch("PIL.Image.open", side_effect=Exception("Falha PIL")):
        with patch.object(Path, "exists", return_value=False):
            gerar_arquivo_icone_icns(DIRETORIO_EDITOR / "logo.icns", force_generation=True)


def test_obter_caminho_icone_alvo_macos():
    """Garante que a resolução de ícone no macOS retorne .icns."""
    from editor.build import obter_caminho_icone_alvo

    with patch("sys.platform", "darwin"):
        icns, png = obter_caminho_icone_alvo(eh_beta=False)
        assert icns == DIRETORIO_EDITOR / "logo.icns"
        assert png == DIRETORIO_EDITOR / "recursos" / "logo_app.png"

        icns_beta, png_beta = obter_caminho_icone_alvo(eh_beta=True)
        assert icns_beta == DIRETORIO_EDITOR / "recursos_beta" / "logo.icns"
        assert png_beta == DIRETORIO_EDITOR / "recursos_beta" / "logo_app.png"


def test_executar_build_macos():
    """Valida a execução de build no macOS acionando gerar_arquivo_icone_icns."""
    with patch("sys.platform", "darwin"):
        with patch("PyInstaller.__main__.run"):
            with patch("editor.build.gerar_arquivo_icone_icns") as mock_icns:
                with patch("pathlib.Path.exists", return_value=True):
                    executar_build()
                    mock_icns.assert_called()


def test_obter_caminho_icone_alvo_linux():
    """Garante que a resolução de ícone no Linux retorne None para arquivo de ícone e aponte para PNG."""
    from editor.build import obter_caminho_icone_alvo

    with patch("sys.platform", "linux"):
        icone, png = obter_caminho_icone_alvo(eh_beta=False)
        assert icone is None
        assert png == DIRETORIO_EDITOR / "recursos" / "logo_app.png"

        icone_beta, png_beta = obter_caminho_icone_alvo(eh_beta=True)
        assert icone_beta is None
        assert png_beta == DIRETORIO_EDITOR / "recursos_beta" / "logo_app.png"


def test_orquestrar_build_flatpak_manifesto_inexistente_lanca_erro():
    """Garante que orquestrar_build_flatpak lance FileNotFoundError se o manifesto não existir."""
    from editor.build import orquestrar_build_flatpak
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError, match="Manifesto Flatpak não encontrado"):
            orquestrar_build_flatpak()


def test_orquestrar_build_flatpak_sem_ferramenta_lanca_erro():
    """Garante que orquestrar_build_flatpak lance RuntimeError claro caso flatpak-builder não esteja no PATH."""
    from editor.build import orquestrar_build_flatpak
    with patch("pathlib.Path.exists", return_value=True):
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="flatpak-builder não encontrado no PATH"):
                orquestrar_build_flatpak()


def test_orquestrar_build_flatpak_executa_comandos():
    """Valida se orquestrar_build_flatpak executa o build e a exportação do bundle com sucesso."""
    from editor.build import orquestrar_build_flatpak
    with patch("shutil.which", return_value="/usr/bin/flatpak-builder"):
        with patch("subprocess.run") as mock_subproc:
            with patch("pathlib.Path.exists", return_value=True):
                bundle_gerado = orquestrar_build_flatpak()
                assert mock_subproc.call_count >= 1
                cmd = mock_subproc.call_args_list[0][0][0]
                assert "flatpak-builder" in cmd[0]
                assert "com.arestaclimb.Editor.yaml" in str(cmd)
                assert bundle_gerado.name.endswith(".flatpak")


def test_executar_build_linux_delega_para_flatpak():
    """Valida que executar_build no Linux invoca orquestrar_build_flatpak e não executa o PyInstaller."""
    with patch("sys.platform", "linux"):
        with patch("editor.build.orquestrar_build_flatpak") as mock_flatpak:
            with patch("PyInstaller.__main__.run") as mock_pyinstaller:
                executar_build()
                mock_flatpak.assert_called_once()
                mock_pyinstaller.assert_not_called()


def test_spec_trata_icones_por_plataforma():
    """Valida se o EditorAresta.spec possui tratamento específico para darwin, win e linux."""
    conteudo_spec = ARQUIVO_SPEC.read_text(encoding="utf-8")
    assert 'sys.platform == "darwin"' in conteudo_spec
    assert 'sys.platform.startswith("win")' in conteudo_spec
    assert "icone_pyinstaller = None" in conteudo_spec
    assert "icon=icone_pyinstaller" in conteudo_spec


def test_obter_versao_projeto_sucesso():
    """Valida se obter_versao_projeto lê a versão correta do pyproject.toml."""
    from editor.build import obter_versao_projeto
    versao = obter_versao_projeto()
    assert isinstance(versao, str)
    assert len(versao) > 0


def test_obter_versao_projeto_arquivo_inexistente():
    """Valida se FileNotFoundError é levantado se o arquivo pyproject.toml não existir."""
    from editor.build import obter_versao_projeto
    caminho_fake = Path("caminho/falso/para/pyproject.toml")
    with pytest.raises(FileNotFoundError, match="Arquivo pyproject.toml não encontrado"):
        obter_versao_projeto(caminho_fake)


def test_obter_versao_projeto_campo_invalido(tmp_path):
    """Valida se ValueError é levantado caso o campo project.version seja ausente ou inválido."""
    from editor.build import obter_versao_projeto
    toml_invalido = tmp_path / "pyproject.toml"
    toml_invalido.write_text("[project]\nname = 'aresta'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Campo 'project.version' não encontrado"):
        obter_versao_projeto(toml_invalido)


def test_gerar_manifesto_dependencias_flatpak_lock_inexistente(tmp_path):
    """Garante que FileNotFoundError é lançado se uv.lock não for encontrado."""
    from editor.build import gerar_manifesto_dependencias_flatpak
    with pytest.raises(FileNotFoundError, match="Arquivo uv.lock não encontrado"):
        gerar_manifesto_dependencias_flatpak(raiz_projeto=tmp_path)


def test_gerar_manifesto_dependencias_flatpak_sucesso(tmp_path):
    """Valida o fluxo completo de exportação e filtragem de dependências Flatpak."""
    from editor.build import gerar_manifesto_dependencias_flatpak
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("# lock", encoding="utf-8")
    destino = tmp_path / "pypi-dependencies.json"

    export_mock_stdout = "\n".join([
        "# comentário inicial",
        "",
        "pyside6-essentials==6.8.0",
        "shiboken6==6.8.0",
        "pyinstaller==6.10.0",
        "requests==2.32.3",
        "qtawesome==1.3.1",
    ])

    def mock_subprocess(cmd, *args, **kwargs):
        res = MagicMock()
        if "export" in cmd:
            res.stdout = export_mock_stdout
            return res
        if "flatpak_pip_generator" in cmd:
            # Simula a criação do arquivo de saída
            destino.write_text("{}", encoding="utf-8")
            return res
        return res

    with patch("subprocess.run", side_effect=mock_subprocess):
        caminho_gerado = gerar_manifesto_dependencias_flatpak(
            caminho_saida=destino,
            raiz_projeto=tmp_path,
        )
        assert caminho_gerado == destino
        assert destino.exists()


def test_gerar_manifesto_dependencias_flatpak_falha_geracao_arquivo(tmp_path):
    """Garante que FileNotFoundError é lançado se flatpak_pip_generator não gerar o arquivo."""
    from editor.build import gerar_manifesto_dependencias_flatpak
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("# lock", encoding="utf-8")
    destino = tmp_path / "pypi-dependencies.json"

    with patch("subprocess.run", return_value=MagicMock(stdout="requests==2.32.3\n")):
        with pytest.raises(FileNotFoundError, match="Falha ao gerar o manifesto de dependências"):
            gerar_manifesto_dependencias_flatpak(caminho_saida=destino, raiz_projeto=tmp_path)


def test_orquestrar_build_flatpak_gera_deps_efemeras_e_limpa():
    """Valida se dependências Flatpak são geradas efemeramente e removidas ao término."""
    from editor.build import orquestrar_build_flatpak
    with patch("shutil.which", return_value="/usr/bin/flatpak-builder"):
        with patch("subprocess.run"):
            deps_criado = False

            def mock_gerar(caminho_saida=None, raiz_projeto=None):
                nonlocal deps_criado
                deps_criado = True
                return caminho_saida

            with patch("editor.build.gerar_manifesto_dependencias_flatpak", side_effect=mock_gerar) as mock_gerar_deps:
                def mock_exists(self):
                    if "com.arestaclimb.Editor.yaml" in str(self):
                        return True
                    if "pypi-dependencies.json" in str(self):
                        return deps_criado
                    return True

                with patch.object(Path, "exists", autospec=True, side_effect=mock_exists):
                    with patch.object(Path, "unlink") as mock_unlink:
                        bundle = orquestrar_build_flatpak()
                        mock_gerar_deps.assert_called_once()
                        mock_unlink.assert_called_once()
                        assert bundle.name.endswith(".flatpak")


def test_main_cli_dispatch_flatpak_deps():
    """Valida o despachante CLI para o modo flatpak-deps."""
    with patch("editor.build.gerar_manifesto_dependencias_flatpak") as mock_gerar:
        main(["flatpak-deps", "--output", "custom.json"])
        mock_gerar.assert_called_once_with(caminho_saida=Path("custom.json"))




