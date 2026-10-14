# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import tempfile
from pathlib import Path

import pytest

from editor.release_tools.bump_version import (
    SemVerError,
    bump_version_file,
    bump_version_lockfile,
    bump_version_metainfo,
    main,
    sincronizar_versoes,
)


def test_bump_version_sucesso():
    # Cria um arquivo temporário simulando version.py
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as f:
        f.write('# Comentário inicial\nVERSION = "1.0.0"\n# Fim\n')
        temp_path = f.name

    try:
        bump_version_file(temp_path, "1.2.3")

        with open(temp_path, encoding="utf-8") as f:
            content = f.read()

        assert 'VERSION = "1.2.3"' in content
        assert "# Comentário inicial" in content
        assert "# Fim" in content
    finally:
        os.remove(temp_path)


def test_bump_version_toml_sucesso():
    # Cria um arquivo temporário simulando pyproject.toml
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".toml", encoding="utf-8"
    ) as f:
        f.write('[project]\nname = "aresta-db"\nversion = "1.0.0"\ndescription = "Teste"\n')
        temp_path = f.name

    try:
        bump_version_file(temp_path, "1.2.3")

        with open(temp_path, encoding="utf-8") as f:
            content = f.read()

        assert 'version = "1.2.3"' in content
        assert "[project]" in content
    finally:
        os.remove(temp_path)


def test_bump_version_nova_versao_com_dev():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as f:
        f.write('VERSION = "1.2.3"\n')
        temp_path = f.name

    try:
        bump_version_file(temp_path, "1.3.0-dev")
        with open(temp_path, encoding="utf-8") as f:
            content = f.read()
        assert 'VERSION = "1.3.0-dev"' in content
    finally:
        os.remove(temp_path)


def test_bump_version_formato_semver_invalido():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as f:
        f.write('VERSION = "1.2.3"\n')
        temp_path = f.name

    try:
        with pytest.raises(SemVerError):
            bump_version_file(temp_path, "versao-errada")
    finally:
        os.remove(temp_path)


def test_bump_version_arquivo_sem_versao():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as f:
        f.write('ALGUM_OUTRO_ATRIBUTO = "1.2.3"\n')
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Padrão VERSION = .* não encontrado"):
            bump_version_file(temp_path, "1.2.3")
    finally:
        os.remove(temp_path)


def test_sincronizar_versoes(tmp_path):
    # Cria estrutura simulada
    pasta_editor_core = tmp_path / "editor" / "core"
    pasta_editor_core.mkdir(parents=True)
    arquivo_version_py = pasta_editor_core / "version.py"
    arquivo_pyproject = tmp_path / "pyproject.toml"

    arquivo_version_py.write_text('VERSION = "1.0.0"\n', encoding="utf-8")
    arquivo_pyproject.write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")

    atualizados = sincronizar_versoes("1.1.0", raiz=tmp_path)
    assert len(atualizados) == 2

    assert 'VERSION = "1.1.0"' in arquivo_version_py.read_text(encoding="utf-8")
    assert 'version = "1.1.0"' in arquivo_pyproject.read_text(encoding="utf-8")


def test_bump_version_com_type_annotation_str():
    # Simula version.py com anotação de tipo VERSION: str = "0.0.7-dev"
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as f:
        f.write('# Comentário\nVERSION: str = "0.0.7-dev"\n')
        temp_path = f.name

    try:
        bump_version_file(temp_path, "0.2.1-dev")
        with open(temp_path, encoding="utf-8") as f:
            content = f.read()
        assert 'VERSION: str = "0.2.1-dev"' in content
        assert "# Comentário" in content
    finally:
        os.remove(temp_path)


def test_bump_version_com_type_annotation_complexa():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".py", encoding="utf-8") as f:
        f.write('VERSION: Final[str] = "1.0.0"\n')
        temp_path = f.name

    try:
        bump_version_file(temp_path, "1.1.0")
        with open(temp_path, encoding="utf-8") as f:
            content = f.read()
        assert 'VERSION: Final[str] = "1.1.0"' in content
    finally:
        os.remove(temp_path)


def test_bump_version_lockfile_sucesso(tmp_path):
    arquivo_lock = tmp_path / "uv.lock"
    conteudo_inicial = (
        "[[package]]\n"
        'name = "outra-lib"\n'
        'version = "1.0.0"\n\n'
        "[[package]]\n"
        'name = "aresta-db"\n'
        'version = "1.0.0"\n'
        'source = { virtual = "." }\n\n'
        "[[package]]\n"
        'name = "mais-uma"\n'
        'version = "2.0.0"\n'
    )
    arquivo_lock.write_text(conteudo_inicial, encoding="utf-8")

    bump_version_lockfile(arquivo_lock, "1.2.3")

    conteudo_final = arquivo_lock.read_text(encoding="utf-8")
    assert 'version = "1.2.3"' in conteudo_final
    assert 'name = "outra-lib"\nversion = "1.0.0"' in conteudo_final
    assert 'name = "mais-uma"\nversion = "2.0.0"' in conteudo_final


def test_bump_version_lockfile_pacote_inexistente(tmp_path):
    arquivo_lock = tmp_path / "uv.lock"
    arquivo_lock.write_text(
        '[[package]]\nname = "outra-lib"\nversion = "1.0.0"\n', encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Pacote 'aresta-db' não encontrado"):
        bump_version_lockfile(arquivo_lock, "1.2.3")


def test_bump_version_lockfile_versao_menor_ou_igual(tmp_path):
    arquivo_lock = tmp_path / "uv.lock"
    arquivo_lock.write_text(
        '[[package]]\nname = "aresta-db"\nversion = "1.5.0"\n', encoding="utf-8"
    )

    with pytest.raises(SemVerError):
        bump_version_lockfile(arquivo_lock, "1.4.0")


def test_sincronizar_versoes_com_uv_lock(tmp_path):
    pasta_editor_core = tmp_path / "editor" / "core"
    pasta_editor_core.mkdir(parents=True)
    arquivo_version_py = pasta_editor_core / "version.py"
    arquivo_pyproject = tmp_path / "pyproject.toml"
    arquivo_uv_lock = tmp_path / "uv.lock"

    arquivo_version_py.write_text('VERSION = "1.0.0"\n', encoding="utf-8")
    arquivo_pyproject.write_text(
        '[project]\nname = "aresta-db"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    arquivo_uv_lock.write_text(
        '[[package]]\nname = "aresta-db"\nversion = "1.0.0"\n', encoding="utf-8"
    )

    atualizados = sincronizar_versoes("1.1.0", raiz=tmp_path)
    assert len(atualizados) == 3
    assert arquivo_uv_lock in atualizados

    assert 'VERSION = "1.1.0"' in arquivo_version_py.read_text(encoding="utf-8")
    assert 'version = "1.1.0"' in arquivo_pyproject.read_text(encoding="utf-8")
    assert 'version = "1.1.0"' in arquivo_uv_lock.read_text(encoding="utf-8")


def test_bump_version_lockfile_versao_antes_do_nome(tmp_path):
    arquivo_lock = tmp_path / "uv.lock"
    conteudo_inicial = (
        '[[package]]\nversion = "1.0.0"\nname = "aresta-db"\nsource = { virtual = "." }\n'
    )
    arquivo_lock.write_text(conteudo_inicial, encoding="utf-8")

    bump_version_lockfile(arquivo_lock, "1.2.3")

    conteudo_final = arquivo_lock.read_text(encoding="utf-8")
    assert 'version = "1.2.3"' in conteudo_final
    assert 'name = "aresta-db"' in conteudo_final


def test_bump_version_lockfile_versao_antes_do_nome_menor_ou_igual(tmp_path):
    arquivo_lock = tmp_path / "uv.lock"
    conteudo_inicial = (
        '[[package]]\nversion = "1.5.0"\nname = "aresta-db"\nsource = { virtual = "." }\n'
    )
    arquivo_lock.write_text(conteudo_inicial, encoding="utf-8")

    with pytest.raises(SemVerError):
        bump_version_lockfile(arquivo_lock, "1.4.0")


def test_main_cli_com_um_argumento(tmp_path, monkeypatch):
    pasta_core = tmp_path / "editor" / "core"
    pasta_core.mkdir(parents=True)
    arquivo_version = pasta_core / "version.py"
    arquivo_version.write_text('VERSION = "1.0.0"\n', encoding="utf-8")

    from editor.release_tools import bump_version

    monkeypatch.setattr(bump_version, "sincronizar_versoes", lambda v: [arquivo_version])

    codigo = main(["1.2.0"])
    assert codigo == 0


def test_main_cli_sincroniza_a_partir_de_version_py(tmp_path):
    pasta_core = tmp_path / "editor" / "core"
    pasta_core.mkdir(parents=True)
    arquivo_version = pasta_core / "version.py"
    arquivo_version.write_text('VERSION = "1.0.0"\n', encoding="utf-8")

    codigo = main([str(arquivo_version), "1.2.0"])
    assert codigo == 0
    assert 'VERSION = "1.2.0"' in arquivo_version.read_text(encoding="utf-8")


def test_main_cli_argumentos_invalidos_ou_excecao(capsys):
    codigo_sem_args = main(["arg1", "arg2", "arg3"])
    assert codigo_sem_args == 1

    codigo_erro_semver = main(["arquivo.py", "versao-invalida"])
    assert codigo_erro_semver == 1
    saida = capsys.readouterr().err
    assert "Erro:" in saida


def test_bump_version_metainfo_sucesso(tmp_path: Path) -> None:
    arquivo_xml = tmp_path / "com.arestaclimb.Editor.metainfo.xml"
    conteudo_inicial = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<component type="desktop-application">\n'
        "  <id>com.arestaclimb.Editor</id>\n"
        "  <name>Editor Aresta</name>\n"
        "  <releases>\n"
        '    <release version="0.4.4" date="2026-10-09">\n'
        "      <description><p>Versão anterior</p></description>\n"
        "    </release>\n"
        "  </releases>\n"
        "</component>\n"
    )
    arquivo_xml.write_text(conteudo_inicial, encoding="utf-8")

    bump_version_metainfo(arquivo_xml, "0.5.15", data="2026-10-15")

    conteudo_final = arquivo_xml.read_text(encoding="utf-8")
    assert 'version="0.5.15"' in conteudo_final
    assert 'date="2026-10-15"' in conteudo_final
    # Garante que a versão nova está no topo de releases
    idx_nova = conteudo_final.find('version="0.5.15"')
    idx_antiga = conteudo_final.find('version="0.4.4"')
    assert idx_nova < idx_antiga


def test_bump_version_metainfo_ignora_versao_dev(tmp_path: Path) -> None:
    arquivo_xml = tmp_path / "com.arestaclimb.Editor.metainfo.xml"
    conteudo_inicial = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<component type="desktop-application">\n'
        "  <id>com.arestaclimb.Editor</id>\n"
        "  <releases>\n"
        '    <release version="0.5.14" date="2026-10-14" />\n'
        "  </releases>\n"
        "</component>\n"
    )
    arquivo_xml.write_text(conteudo_inicial, encoding="utf-8")

    bump_version_metainfo(arquivo_xml, "0.5.15-dev")

    # Não deve adicionar versão -dev
    conteudo_final = arquivo_xml.read_text(encoding="utf-8")
    assert "0.5.15-dev" not in conteudo_final
    assert "0.5.14" in conteudo_final


def test_sincronizar_versoes_com_metainfo(tmp_path: Path) -> None:
    pasta_core = tmp_path / "editor" / "core"
    pasta_core.mkdir(parents=True)
    arquivo_version_py = pasta_core / "version.py"
    arquivo_pyproject = tmp_path / "pyproject.toml"
    arquivo_uv_lock = tmp_path / "uv.lock"

    pasta_flatpak = tmp_path / "editor" / "flatpak"
    pasta_flatpak.mkdir(parents=True)
    arquivo_metainfo = pasta_flatpak / "com.arestaclimb.Editor.metainfo.xml"

    arquivo_version_py.write_text('VERSION = "1.0.0"\n', encoding="utf-8")
    arquivo_pyproject.write_text(
        '[project]\nname = "aresta-db"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    arquivo_uv_lock.write_text(
        '[[package]]\nname = "aresta-db"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    arquivo_metainfo.write_text(
        '<component><releases><release version="1.0.0" date="2026-10-01"/></releases></component>\n',
        encoding="utf-8",
    )

    atualizados = sincronizar_versoes("1.1.0", raiz=tmp_path)
    assert len(atualizados) == 4
    assert arquivo_metainfo in atualizados
    assert 'version="1.1.0"' in arquivo_metainfo.read_text(encoding="utf-8")


def test_bump_version_metainfo_com_descricao_personalizada(tmp_path: Path) -> None:
    arquivo_xml = tmp_path / "com.arestaclimb.Editor.metainfo.xml"
    conteudo_inicial = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<component type="desktop-application">\n'
        "  <releases>\n"
        '    <release version="0.4.4" date="2026-10-09">\n'
        "      <description><p>Versão anterior</p></description>\n"
        "    </release>\n"
        "  </releases>\n"
        "</component>\n"
    )
    arquivo_xml.write_text(conteudo_inicial, encoding="utf-8")

    bump_version_metainfo(
        arquivo_xml,
        "0.5.15",
        data="2026-10-15",
        descricao_release="Novas funcionalidades e correção de bugs na diagramação.",
    )

    conteudo_final = arquivo_xml.read_text(encoding="utf-8")
    assert "<p>Novas funcionalidades e correção de bugs na diagramação.</p>" in conteudo_final


def test_main_cli_com_flag_descricao(tmp_path: Path) -> None:
    pasta_core = tmp_path / "editor" / "core"
    pasta_core.mkdir(parents=True)
    arquivo_version = pasta_core / "version.py"
    arquivo_version.write_text('VERSION = "1.0.0"\n', encoding="utf-8")

    pasta_flatpak = tmp_path / "editor" / "flatpak"
    pasta_flatpak.mkdir(parents=True)
    arquivo_metainfo = pasta_flatpak / "com.arestaclimb.Editor.metainfo.xml"
    arquivo_metainfo.write_text(
        '<component><releases><release version="1.0.0" date="2026-10-01"/></releases></component>\n',
        encoding="utf-8",
    )

    codigo = main(
        [
            str(arquivo_version),
            "1.2.0",
            "--descricao",
            "Melhorias no traçado de vias.",
        ]
    )
    assert codigo == 0
    assert 'VERSION = "1.2.0"' in arquivo_version.read_text(encoding="utf-8")
    assert "<p>Melhorias no traçado de vias.</p>" in arquivo_metainfo.read_text(encoding="utf-8")
