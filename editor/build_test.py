# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import ast
import builtins
import importlib
import importlib.util
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from editor.build import (
    ARQUIVO_MANIFESTO_FLATPAK,
    ARQUIVO_SPEC,
    DIRETORIO_DIST_ONEDIR,
    DIRETORIO_EDITOR,
    DIRETORIO_FLATPAK,
    LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB,
    PACOTES_DISPENSAVEIS_FLATPAK,
    PACOTES_PREFERIR_WHEELS,
    ExecutorBuildPadrao,
    executar_build,
    executar_testes,
    filtrar_binarios_desnecessarios,
    filtrar_datas_desnecessarios,
    gerar_arquivo_icone,
    gerar_arquivo_icone_icns,
    gerar_manifesto_dependencias_flatpak,
    main,
    obter_argumentos_pyinstaller,
    obter_caminho_icone_alvo,
    obter_diretorio_distribuicao_onedir,
    obter_modulos_excluidos,
    obter_versao_projeto,
    orquestrar_build_flatpak,
)
from editor.executor_build_fake import ExecutorBuildFake


def _criar_png_rgba(caminho: Path, tamanho: tuple[int, int] = (64, 64)) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", tamanho, (34, 139, 34, 255))
    img.save(str(caminho), format="PNG")
    return caminho


def test_obter_modulos_excluidos_preserva_dependencias_do_editor_e_exclui_ia_pesada() -> None:
    """
    Valida que bibliotecas pesadas fora do grupo editor permanecem excluídas, enquanto
    pymupdf/fitz e lxml (usados pelo editor em runtime) NÃO constam na lista de exclusão.
    """
    excluidos = obter_modulos_excluidos()
    assert "paddleocr" in excluidos
    assert "paddlex" in excluidos
    assert "cv2" in excluidos
    assert "scipy" in excluidos
    assert "torch" in excluidos
    assert "PySide6.QtQuick" in excluidos
    assert "PySide6.QtWebEngineCore" in excluidos

    assert "pymupdf" not in excluidos
    assert "fitz" not in excluidos
    assert "lxml" not in excluidos
    assert "sqlite3" not in excluidos


def test_nenhum_pacote_do_grupo_editor_uv_lock_esta_em_modulos_excluidos() -> None:
    """
    Garante invariante estrutural: nenhum pacote instalado no grupo 'editor' do uv.lock
    pode ser excluído pelo empacotamento PyInstaller em obter_modulos_excluidos().
    """
    raiz = DIRETORIO_EDITOR.parent
    res = subprocess.run(
        ["uv", "export", "--frozen", "--only-group", "editor", "--no-dev", "--no-hashes"],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        check=True,
    )
    pacotes_editor: set[str] = set()
    for linha in res.stdout.splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#"):
            continue
        nome_pkg = limpa.split("==")[0].split(">=")[0].split("<=")[0].split(";")[0].strip().lower()
        pacotes_editor.add(nome_pkg)
        pacotes_editor.add(nome_pkg.replace("-", "_"))

    excluidos = obter_modulos_excluidos()
    conflitos = [
        exc
        for exc in excluidos
        if exc.lower() in pacotes_editor or exc.lower().replace("_", "-") in pacotes_editor
    ]
    assert conflitos == [], (
        f"Conflito fatal de empacotamento: pacotes do grupo 'editor' estão em obter_modulos_excluidos(): {conflitos}"
    )


def test_todos_os_modulos_de_producao_importam_sem_violar_modulos_excluidos() -> None:
    """
    Simula o bloqueio do PyInstaller em runtime E varre o fecho transitivo AST (incluindo
    imports lazy dentro de funções em scripts.*, aresta_api.* e serving.*): nenhum módulo
    alcançável a partir de editor/, coleta_de_betas/ ou migracoes/ pode importar obter_modulos_excluidos().
    """
    raiz = DIRETORIO_EDITOR.parent
    excluidos = set(obter_modulos_excluidos())
    import_original = builtins.__import__

    def _import_com_bloqueio(name: str, *args: object, **kwargs: object) -> object:
        for exc in excluidos:
            if name == exc or name.startswith(f"{exc}."):
                raise ModuleNotFoundError(
                    f"Módulo '{name}' bloqueado por obter_modulos_excluidos ({exc})"
                )
        return import_original(name, *args, **kwargs)  # type: ignore[arg-type]

    pastas_ignoradas = {"caos", "release_tools", "dist", "build", "__pycache__", ".venv"}
    falhas: list[str] = []
    fila_ast: list[Path] = []
    visitados_ast: set[Path] = set()

    builtins.__import__ = _import_com_bloqueio  # type: ignore[assignment]
    try:
        for base in ("editor", "coleta_de_betas", "migracoes"):
            pasta_base = raiz / base
            for arq in sorted(pasta_base.rglob("*.py")):
                if (
                    any(p in pastas_ignoradas for p in arq.parts)
                    or arq.name.endswith("_test.py")
                    or arq.name.endswith("_fake.py")
                    or arq.name == "build.py"
                ):
                    continue
                fila_ast.append(arq.resolve())
                if base == "migracoes":
                    spec = importlib.util.spec_from_file_location(arq.stem, arq)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        try:
                            spec.loader.exec_module(mod)
                        except Exception as err:
                            falhas.append(f"{arq.relative_to(raiz)}: {err!r}")
                else:
                    partes_rel = arq.relative_to(raiz).with_suffix("").parts
                    nome_mod = ".".join(partes_rel)
                    try:
                        importlib.import_module(nome_mod)
                    except Exception as err:
                        falhas.append(f"{nome_mod}: {err!r}")
    finally:
        builtins.__import__ = import_original

    # Varredura do fecho transitivo AST (captura inclusive imports lazy e stdlib já em sys.modules, ex: sqlite3)
    prefixos_internos = ("editor.", "coleta_de_betas.", "scripts.", "serving.")
    while fila_ast:
        arq_atual = fila_ast.pop()
        if arq_atual in visitados_ast or not arq_atual.is_file():
            continue
        visitados_ast.add(arq_atual)
        arvore = ast.parse(arq_atual.read_text(encoding="utf-8"), filename=str(arq_atual))
        for node in ast.walk(arvore):
            modulos_ref: list[str] = []
            if isinstance(node, ast.Import):
                modulos_ref = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modulos_ref = [node.module]
            for m_ref in modulos_ref:
                for exc in excluidos:
                    if m_ref == exc or m_ref.startswith(f"{exc}."):
                        falhas.append(
                            f"{arq_atual.relative_to(raiz)}:{node.lineno} importa '{m_ref}' (excluído por '{exc}')"
                        )
                if m_ref.startswith(prefixos_internos):
                    candidato = (raiz / Path(*m_ref.split("."))).with_suffix(".py").resolve()
                    if candidato.is_file() and candidato not in visitados_ast:
                        fila_ast.append(candidato)

    assert falhas == [], "Falhas de importação sob obter_modulos_excluidos():\n" + "\n".join(falhas)


def test_spec_possui_hiddenimports_e_pacotes_coletados_validos() -> None:
    """
    Analisa estaticamente o EditorAresta.spec garantindo que nenhum hiddenimport ou pacote
    em pacotes_para_coletar referencie módulos deletados/inexistentes, e que pymupdf e ddgs sejam coletados.
    """
    conteudo_spec = ARQUIVO_SPEC.read_text(encoding="utf-8")
    arvore = ast.parse(conteudo_spec, filename=str(ARQUIVO_SPEC))

    hidden_literais: list[str] = []
    pacotes_coletados: list[str] = []

    for node in ast.walk(arvore):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.List):
                    valores = [
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
                    if target.id == "hiddenimports":
                        hidden_literais.extend(valores)
                    elif target.id == "pacotes_para_coletar":
                        pacotes_coletados.extend(valores)

    assert len(hidden_literais) > 0
    for mod_nome in hidden_literais:
        assert importlib.util.find_spec(mod_nome) is not None, (
            f"O módulo '{mod_nome}' listado em hiddenimports de EditorAresta.spec não existe!"
        )

    assert "pymupdf" in pacotes_coletados
    assert "ddgs" in pacotes_coletados
    for pkg in pacotes_coletados:
        assert importlib.util.find_spec(pkg) is not None, (
            f"O pacote '{pkg}' em pacotes_para_coletar de EditorAresta.spec não está instalado!"
        )


def test_filtrar_binarios_desnecessarios_windows_e_unix() -> None:
    """Valida filtragem de binários gráficos dispensáveis preservando bibliotecas essenciais e pymupdf."""
    binarios = [
        ("PySide6\\opengl32sw.dll", "C:\\fake\\opengl32sw.dll", "BINARY"),
        ("PySide6\\plugins\\platforms\\qdirect2d.dll", "C:\\fake\\qdirect2d.dll", "BINARY"),
        ("PySide6/libQt6Quick.so.6", "/fake/libQt6Quick.so.6", "BINARY"),
        ("PySide6/libQt6Qml.dylib", "/fake/libQt6Qml.dylib", "BINARY"),
        ("PySide6/libQt6Pdf.dylib", "/fake/libQt6Pdf.dylib", "BINARY"),
        ("PySide6\\Qt6Core.dll", "C:\\fake\\Qt6Core.dll", "BINARY"),
        ("PySide6\\Qt6Widgets.dll", "C:\\fake\\Qt6Widgets.dll", "BINARY"),
        ("pymupdf\\mupdfcpp64.dll", "C:\\fake\\mupdfcpp64.dll", "BINARY"),
        ("pygit2\\git2.dll", "C:\\fake\\git2.dll", "BINARY"),
    ]
    nomes = [b[0] for b in filtrar_binarios_desnecessarios(binarios)]
    assert "PySide6\\opengl32sw.dll" not in nomes
    assert "PySide6\\plugins\\platforms\\qdirect2d.dll" not in nomes
    assert "PySide6/libQt6Quick.so.6" not in nomes
    assert "PySide6/libQt6Qml.dylib" not in nomes
    assert "PySide6/libQt6Pdf.dylib" not in nomes

    assert "PySide6\\Qt6Core.dll" in nomes
    assert "PySide6\\Qt6Widgets.dll" in nomes
    assert "pymupdf\\mupdfcpp64.dll" in nomes
    assert "pygit2\\git2.dll" in nomes


def test_filtrar_datas_desnecessarios_poda_mupdf_devel_fontes_metadados_testes_e_fakes() -> None:
    """Valida remoção de mupdf-devel, fontes extras, dist-info, testes/fakes e .ico no darwin."""
    datas = [
        (
            "C:\\venv\\pymupdf\\mupdf-devel\\include\\mupdf\\fitz.h",
            "pymupdf\\mupdf-devel\\include\\mupdf",
            "DATA",
        ),
        ("C:\\venv\\pymupdf\\utils.py", "pymupdf", "DATA"),
        ("C:\\venv\\qtawesome\\fonts\\phosphor.ttf", "qtawesome\\fonts\\phosphor.ttf", "DATA"),
        (
            "C:\\venv\\qtawesome\\fonts\\fontawesome5-solid-webfont-5.15.4.ttf",
            "qtawesome\\fonts\\fontawesome5-solid-webfont-5.15.4.ttf",
            "DATA",
        ),
        ("C:\\venv\\websockets-17.2.dist-info\\METADATA", "websockets-17.2.dist-info", "DATA"),
        ("C:\\venv\\pkg.egg-info\\PKG-INFO", "pkg.egg-info", "DATA"),
        ("C:\\repo\\migracoes\\0005_mig_test.py", "migracoes\\0005_mig_test.py", "DATA"),
        ("C:\\repo\\editor\\executor_build_fake.py", "editor\\executor_build_fake.py", "DATA"),
        ("C:\\repo\\tests\\conftest.py", "tests\\conftest.py", "DATA"),
        ("C:\\repo\\tests\\test_algo.py", "tests\\test_algo.py", "DATA"),
        ("C:\\repo\\migracoes\\0005_mig.py", "migracoes\\0005_mig.py", "DATA"),
        ("C:\\repo\\editor\\logo.ico", "editor\\logo.ico", "DATA"),
        ("C:\\repo\\editor\\recursos\\logo_app.png", "recursos\\logo_app.png", "DATA"),
    ]

    destinos_win = [d[1] for d in filtrar_datas_desnecessarios(datas, plataforma="win32")]
    assert "pymupdf\\mupdf-devel\\include\\mupdf" not in destinos_win
    assert "pymupdf" in destinos_win
    assert "qtawesome\\fonts\\phosphor.ttf" not in destinos_win
    assert "qtawesome\\fonts\\fontawesome5-solid-webfont-5.15.4.ttf" in destinos_win
    assert "websockets-17.2.dist-info" not in destinos_win
    assert "pkg.egg-info" not in destinos_win
    assert "migracoes\\0005_mig_test.py" not in destinos_win
    assert "editor\\executor_build_fake.py" not in destinos_win
    assert "tests\\conftest.py" not in destinos_win
    assert "tests\\test_algo.py" not in destinos_win
    assert "migracoes\\0005_mig.py" in destinos_win
    assert "editor\\logo.ico" in destinos_win

    destinos_mac = [d[1] for d in filtrar_datas_desnecessarios(datas, plataforma="darwin")]
    assert "editor\\logo.ico" not in destinos_mac
    assert "recursos\\logo_app.png" in destinos_mac


def test_geracao_real_de_icones_ico_e_icns_em_disco(tmp_path: Path) -> None:
    """Valida criação real de arquivos .ico e .icns multi-resolução com PIL em tmp_path."""
    png_rgb = tmp_path / "origem_rgb.png"
    Image.new("RGB", (64, 64), (10, 20, 30)).save(str(png_rgb), format="PNG")

    caminho_ico = tmp_path / "saida" / "logo.ico"
    gerar_arquivo_icone(caminho_ico, caminho_png=png_rgb, force_generation=True)
    assert caminho_ico.is_file() and caminho_ico.stat().st_size > 0
    mtime_ico = caminho_ico.stat().st_mtime_ns
    gerar_arquivo_icone(caminho_ico, caminho_png=png_rgb, force_generation=False)
    assert caminho_ico.stat().st_mtime_ns == mtime_ico

    caminho_icns = tmp_path / "saida" / "logo.icns"
    gerar_arquivo_icone_icns(caminho_icns, caminho_png=png_rgb, force_generation=True)
    assert caminho_icns.is_file() and caminho_icns.stat().st_size > 0
    mtime_icns = caminho_icns.stat().st_mtime_ns
    gerar_arquivo_icone_icns(caminho_icns, caminho_png=png_rgb, force_generation=False)
    assert caminho_icns.stat().st_mtime_ns == mtime_icns


def test_obter_caminho_icone_alvo_todas_plataformas_e_canais(tmp_path: Path) -> None:
    """Valida resolução de caminho de ícone para win32, darwin e linux nos canais produção e beta."""
    ico_win, png_win = obter_caminho_icone_alvo(
        eh_beta=False, plataforma="win32", diretorio_editor=tmp_path
    )
    assert ico_win == tmp_path / "logo.ico"
    assert png_win == tmp_path / "recursos" / "logo_app.png"

    ico_win_beta, png_win_beta = obter_caminho_icone_alvo(
        eh_beta=True, plataforma="win32", diretorio_editor=tmp_path
    )
    assert ico_win_beta == tmp_path / "recursos_beta" / "logo.ico"
    assert png_win_beta == tmp_path / "recursos_beta" / "logo_app.png"

    icns_mac, _ = obter_caminho_icone_alvo(
        eh_beta=False, plataforma="darwin", diretorio_editor=tmp_path
    )
    assert icns_mac == tmp_path / "logo.icns"

    icns_linux, png_linux = obter_caminho_icone_alvo(
        eh_beta=False, plataforma="linux", diretorio_editor=tmp_path
    )
    assert icns_linux is None
    assert png_linux == tmp_path / "recursos" / "logo_app.png"

    icns_linux_beta, png_linux_beta = obter_caminho_icone_alvo(
        eh_beta=True, plataforma="linux", diretorio_editor=tmp_path
    )
    assert icns_linux_beta is None
    assert png_linux_beta == tmp_path / "recursos_beta" / "logo_app.png"


def test_obter_argumentos_pyinstaller_e_diretorio_onedir(tmp_path: Path) -> None:
    """Valida construção de argumentos do PyInstaller e caminho de distribuição onedir."""
    assert obter_diretorio_distribuicao_onedir() == DIRETORIO_DIST_ONEDIR
    spec_tmp = tmp_path / "EditorAresta.spec"
    args = obter_argumentos_pyinstaller(caminho_spec=spec_tmp, diretorio_editor=tmp_path)
    assert str(spec_tmp) in args
    assert "--clean" in args
    assert "--noconfirm" in args
    assert str(tmp_path / "dist") in args
    assert str(tmp_path / "build") in args


def test_executar_build_windows_macos_linux_e_erros(tmp_path: Path) -> None:
    """Valida orquestração de executar_build nas 3 plataformas usando diretório temporário real e ExecutorBuildFake."""
    dir_editor = tmp_path / "editor"
    spec_file = dir_editor / "EditorAresta.spec"
    _criar_png_rgba(dir_editor / "recursos" / "logo_app.png")
    _criar_png_rgba(dir_editor / "recursos_beta" / "logo_app.png")

    # 1. Falha se o spec não existir em Windows/macOS
    fake = ExecutorBuildFake()
    with pytest.raises(FileNotFoundError, match="Arquivo de especificação não encontrado"):
        executar_build(plataforma="win32", diretorio_editor=dir_editor, executor=fake)

    spec_file.write_text("# spec", encoding="utf-8")

    # 2. Windows produção: gera logo.ico e recursos/logo.ico e chama PyInstaller
    executar_build(
        force_icon_generation=True,
        plataforma="win32",
        canal="producao",
        diretorio_editor=dir_editor,
        executor=fake,
    )
    assert (dir_editor / "logo.ico").is_file()
    assert (dir_editor / "recursos" / "logo.ico").is_file()
    assert len(fake.chamadas_pyinstaller) == 1
    assert str(spec_file) in fake.chamadas_pyinstaller[0]

    # 3. Windows beta: gera recursos_beta/logo.ico
    executar_build(
        force_icon_generation=True,
        plataforma="win32",
        canal="beta",
        diretorio_editor=dir_editor,
        executor=fake,
    )
    assert (dir_editor / "recursos_beta" / "logo.ico").is_file()

    # 4. macOS produção e beta: gera .icns
    executar_build(
        force_icon_generation=True,
        plataforma="darwin",
        canal="producao",
        diretorio_editor=dir_editor,
        executor=fake,
    )
    assert (dir_editor / "logo.icns").is_file()
    assert (dir_editor / "recursos" / "logo.icns").is_file()

    executar_build(
        force_icon_generation=True,
        plataforma="darwin",
        canal="beta",
        diretorio_editor=dir_editor,
        executor=fake,
    )
    assert (dir_editor / "recursos_beta" / "logo.icns").is_file()

    # 5. Erro claro se PyInstaller não estiver instalado
    fake_sem_pyi = ExecutorBuildFake(pyinstaller_disponivel=False)
    with pytest.raises(RuntimeError, match="PyInstaller não está disponível"):
        executar_build(plataforma="win32", diretorio_editor=dir_editor, executor=fake_sem_pyi)

    # 6. Linux delega ao Flatpak sem chamar PyInstaller
    raiz = tmp_path
    (raiz / "pyproject.toml").write_text('[project]\nversion = "0.6.3"\n', encoding="utf-8")
    (raiz / "uv.lock").write_text("# lock\n", encoding="utf-8")
    manifesto_fp = dir_editor / "flatpak" / "com.arestaclimb.Editor.yaml"
    manifesto_fp.parent.mkdir(parents=True, exist_ok=True)
    manifesto_fp.write_text("app-id: com.arestaclimb.Editor\n", encoding="utf-8")
    deps_fp = dir_editor / "flatpak" / "pypi-dependencies.json"
    deps_fp.write_text("{}", encoding="utf-8")

    fake_linux = ExecutorBuildFake()
    executar_build(plataforma="linux", diretorio_editor=dir_editor, executor=fake_linux)
    assert fake_linux.chamadas_pyinstaller == []
    assert any("flatpak-builder" in cmd[0] for cmd in fake_linux.comandos_executados)


def test_orquestrar_build_flatpak_e_gerar_manifesto_dependencias(tmp_path: Path) -> None:
    """Valida geração de pypi-dependencies.json e orquestração completa do Flatpak com arquivos reais em tmp_path."""
    raiz = tmp_path / "projeto"
    dir_editor = raiz / "editor"
    dir_flatpak = dir_editor / "flatpak"
    dir_flatpak.mkdir(parents=True)
    (raiz / "pyproject.toml").write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")

    # Erro sem uv.lock
    with pytest.raises(FileNotFoundError, match="Arquivo uv.lock não encontrado"):
        gerar_manifesto_dependencias_flatpak(
            caminho_saida=dir_flatpak / "pypi-dependencies.json",
            raiz_projeto=raiz,
            executor=ExecutorBuildFake(),
        )

    (raiz / "uv.lock").write_text("# lock\n", encoding="utf-8")
    destino_deps = dir_flatpak / "pypi-dependencies.json"

    saida_export = "\n".join(
        [
            "# exportado",
            "",
            "pyside6-essentials==6.8.0",
            "pyinstaller==6.10.0",
            "grpcio==1.84.0",
            "pymupdf==1.25.0",
            "lxml==5.3.0",
            "requests==2.32.3",
        ]
    )

    def manipulador_sucesso(
        cmd: list[str], cwd: Path | None, capturar: bool, verificar: bool
    ) -> subprocess.CompletedProcess[str]:
        if "export" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=saida_export)
        if "info" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok")
        if "flatpak_pip_generator" in cmd:
            req_arg = [a for a in cmd if a.startswith("--requirements-file=")][0]
            conteudo_req = Path(req_arg.split("=", 1)[1]).read_text(encoding="utf-8")
            assert "pymupdf==1.25.0" in conteudo_req
            assert "lxml==5.3.0" in conteudo_req
            assert "pyside6" not in conteudo_req
            assert "pyinstaller" not in conteudo_req
            assert any(a.startswith("--runtime=") for a in cmd)
            assert any(a.startswith("--prefer-wheels=") for a in cmd)
            destino_deps.write_text('{"name": "pypi"}', encoding="utf-8")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")
        if "build-bundle" in cmd:
            Path(cmd[3]).write_text("bundle", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="")

    fake_ok = ExecutorBuildFake(manipulador_comando=manipulador_sucesso)

    # Erro se manifesto não existir
    with pytest.raises(FileNotFoundError, match="Manifesto Flatpak não encontrado"):
        orquestrar_build_flatpak(
            caminho_manifesto=dir_flatpak / "inexistente.yaml",
            diretorio_dist=dir_editor / "dist",
            versao="1.0.0",
            raiz_projeto=raiz,
            executor=fake_ok,
        )

    manifesto = dir_flatpak / "com.arestaclimb.Editor.yaml"
    manifesto.write_text("app-id: com.arestaclimb.Editor\n", encoding="utf-8")

    # Erro se flatpak-builder ausente
    fake_sem_builder = ExecutorBuildFake(executaveis={"flatpak-builder": None})
    with pytest.raises(RuntimeError, match="flatpak-builder não encontrado"):
        orquestrar_build_flatpak(
            caminho_manifesto=manifesto,
            diretorio_dist=dir_editor / "dist",
            versao="1.0.0",
            raiz_projeto=raiz,
            executor=fake_sem_builder,
        )

    # Sucesso gerando pypi-dependencies.json e substituindo bundle pré-existente
    dist_dir = dir_editor / "dist"
    dist_dir.mkdir(parents=True)
    bundle_antigo = dist_dir / "EditorAresta-1.0.0.flatpak"
    bundle_antigo.write_text("antigo", encoding="utf-8")

    bundle = orquestrar_build_flatpak(
        caminho_manifesto=manifesto,
        diretorio_dist=dist_dir,
        versao="1.0.0",
        raiz_projeto=raiz,
        executor=fake_ok,
    )
    assert bundle == bundle_antigo
    assert bundle.read_text(encoding="utf-8") == "bundle"
    assert destino_deps.is_file()

    # Falha se o gerador não escrever o arquivo de saída
    destino_ausente = dir_flatpak / "nao_criado.json"
    fake_nao_gera = ExecutorBuildFake(executaveis={"uv": "/bin/uv", "flatpak": None})
    fake_nao_gera.enfileirar_resposta_comando(returncode=0, stdout="requests==2.32.3\n")
    fake_nao_gera.enfileirar_resposta_comando(returncode=0, stdout="")
    with pytest.raises(FileNotFoundError, match="Falha ao gerar o manifesto de dependências"):
        gerar_manifesto_dependencias_flatpak(
            caminho_saida=destino_ausente,
            raiz_projeto=raiz,
            executor=fake_nao_gera,
        )


def test_obter_versao_projeto_e_erros(tmp_path: Path) -> None:
    """Valida leitura da versão do pyproject.toml real e erros de arquivo/campo inválido."""
    assert len(obter_versao_projeto()) > 0

    with pytest.raises(FileNotFoundError, match="Arquivo pyproject.toml não encontrado"):
        obter_versao_projeto(tmp_path / "ausente.toml")

    toml_sem_versao = tmp_path / "pyproject.toml"
    toml_sem_versao.write_text("[project]\nname = 'aresta'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Campo 'project.version' não encontrado"):
        obter_versao_projeto(toml_sem_versao)


def test_executar_testes_fluxos_lint_format_e_pytest(tmp_path: Path) -> None:
    """Valida bloqueio rápido em falha de ruff check, ruff format, falha de pytest e sucesso."""
    # 1. Sucesso completo
    fake_ok = ExecutorBuildFake(codigo_pytest=0)
    executar_testes(diretorio_editor=tmp_path, executor=fake_ok)
    assert len(fake_ok.comandos_executados) == 2
    assert len(fake_ok.chamadas_pytest) == 1

    # 2. Falha no ruff check
    fake_lint = ExecutorBuildFake()
    fake_lint.enfileirar_resposta_comando(returncode=1)
    with pytest.raises(SystemExit) as exc_lint:
        executar_testes(diretorio_editor=tmp_path, executor=fake_lint)
    assert exc_lint.value.code == 1
    assert fake_lint.chamadas_pytest == []

    # 3. Falha no ruff format
    fake_fmt = ExecutorBuildFake()
    fake_fmt.enfileirar_resposta_comando(returncode=0)
    fake_fmt.enfileirar_resposta_comando(returncode=2)
    with pytest.raises(SystemExit) as exc_fmt:
        executar_testes(diretorio_editor=tmp_path, executor=fake_fmt)
    assert exc_fmt.value.code == 2
    assert fake_fmt.chamadas_pytest == []

    # 4. Falha no pytest
    fake_pt = ExecutorBuildFake(codigo_pytest=4)
    with pytest.raises(SystemExit) as exc_pt:
        executar_testes(diretorio_editor=tmp_path, executor=fake_pt)
    assert exc_pt.value.code == 4


def test_gerar_tarball_codigo_fonte_e_cli_main(tmp_path: Path) -> None:
    """Valida geração real de tarball de código-fonte excluindo database/testes/fakes e despacho CLI de main()."""
    raiz = tmp_path / "repo"
    raiz.mkdir()
    (raiz / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
    (raiz / "uv.lock").write_text("lock", encoding="utf-8")
    (raiz / "database").mkdir()
    (raiz / "database" / "pesado.bin").write_text("dados", encoding="utf-8")
    (raiz / "editor").mkdir()
    (raiz / "editor" / "main.py").write_text("print('ok')", encoding="utf-8")
    (raiz / "editor" / "main_test.py").write_text("def test(): pass", encoding="utf-8")
    (raiz / "editor" / "executor_build_fake.py").write_text("# fake", encoding="utf-8")
    (raiz / "editor" / "dist").mkdir()
    (raiz / "editor" / "dist" / "bin").write_text("bin", encoding="utf-8")
    for sub in ("aresta_api", "scripts", "coleta_de_betas", "migracoes", "serving"):
        (raiz / sub).mkdir()
        (raiz / sub / "mod.py").write_text("# ok", encoding="utf-8")

    fake_cli = ExecutorBuildFake()

    # Modo source-tarball via main()
    saida_tar = tmp_path / "tarballs"
    main(
        ["source-tarball", "--output-dir", str(saida_tar), "--versao", "1.2.3"],
        raiz_projeto=raiz,
        executor=fake_cli,
    )
    tarball = saida_tar / "EditorAresta-1.2.3-source.tar.gz"
    assert tarball.is_file()
    with tarfile.open(tarball, "r:gz") as tar:
        nomes = [n.replace("\\", "/") for n in tar.getnames()]
        assert "editor/main.py" in nomes
        assert not any("database" in n for n in nomes)
        assert not any("_test.py" in n for n in nomes)
        assert not any("_fake.py" in n for n in nomes)

    # Modo test via main()
    main(["test"], diretorio_editor=raiz / "editor", executor=fake_cli)
    assert len(fake_cli.chamadas_pytest) == 1

    # Modo dist via main()
    _criar_png_rgba(raiz / "editor" / "recursos" / "logo_app.png")
    (raiz / "editor" / "EditorAresta.spec").write_text("# spec", encoding="utf-8")
    main(
        ["dist", "--force-icon-generation"],
        plataforma="win32",
        diretorio_editor=raiz / "editor",
        executor=fake_cli,
    )
    assert len(fake_cli.chamadas_pyinstaller) == 1

    # Modo flatpak-deps via main()
    saida_json = tmp_path / "pypi-deps.json"

    def criar_json(
        cmd: list[str], cwd: Path | None, capturar: bool, verificar: bool
    ) -> subprocess.CompletedProcess[str]:
        if "flatpak_pip_generator" in cmd:
            saida_json.write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="requests==2.32.3\n")

    fake_deps = ExecutorBuildFake(manipulador_comando=criar_json)
    main(
        ["flatpak-deps", "--output", str(saida_json)],
        raiz_projeto=raiz,
        executor=fake_deps,
    )
    assert saida_json.is_file()

    # Cobertura real de ExecutorBuildPadrao em operações seguras e leves
    padrao = ExecutorBuildPadrao()
    assert padrao.qual_executavel("python") is not None or padrao.qual_executavel("uv") is not None
    res_cmd = padrao.executar_comando(["uv", "--version"], capturar_saida=True, verificar=True)
    assert res_cmd.returncode == 0
    assert (
        padrao.executar_pytest(
            ["-o", "addopts=", str(DIRETORIO_EDITOR / "executor_build_fake_test.py")]
        )
        == 0
    )
    if importlib.util.find_spec("PyInstaller") is not None:
        with pytest.raises(SystemExit) as exc_pyi:
            padrao.executar_pyinstaller(["--version"])
        assert exc_pyi.value.code == 0
    else:
        with pytest.raises(ModuleNotFoundError):
            padrao.executar_pyinstaller(["--version"])


def test_manifesto_flatpak_poda_mupdf_devel_e_constantes_otimizadas() -> None:
    """Valida manifesto Flatpak, metainfo XML, poda de mupdf-devel e constantes de wheels nativos."""
    assert "grpcio" in PACOTES_DISPENSAVEIS_FLATPAK
    assert "pyinstaller" in PACOTES_DISPENSAVEIS_FLATPAK
    for pacote_nativo in (
        "brotli",
        "charset-normalizer",
        "ddgs",
        "lxml",
        "primp",
        "pymupdf",
        "zstandard",
    ):
        assert pacote_nativo in PACOTES_PREFERIR_WHEELS

    manifesto_texto = ARQUIVO_MANIFESTO_FLATPAK.read_text(encoding="utf-8")
    assert "mupdf-devel" in manifesto_texto

    caminho_metainfo = DIRETORIO_FLATPAK / "com.arestaclimb.Editor.metainfo.xml"
    raiz = ET.parse(caminho_metainfo).getroot()
    assert raiz.tag == "component"
    assert LIMITE_MAXIMO_TAMANHO_EXECUTAVEL_MB > 0
