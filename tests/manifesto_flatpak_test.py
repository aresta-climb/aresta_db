# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes de conformidade e integridade dos manifestos Flatpak e metadados AppStream.
Valida o app-id com.arestaclimb.Editor, declaração de permissões de sandbox e metadados.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_FLATPAK = PASTA_RAIZ / "editor" / "flatpak"
ARQUIVO_MANIFESTO = PASTA_FLATPAK / "com.arestaclimb.Editor.yaml"
ARQUIVO_METAINFO = PASTA_FLATPAK / "com.arestaclimb.Editor.metainfo.xml"
ARQUIVO_DESKTOP = PASTA_FLATPAK / "com.arestaclimb.Editor.desktop"


def test_manifesto_flatpak_estrutural() -> None:
    """Valida a estrutura do manifesto Flatpak YAML."""
    assert ARQUIVO_MANIFESTO.exists(), f"Manifesto Flatpak não encontrado em {ARQUIVO_MANIFESTO}"

    conteudo = ARQUIVO_MANIFESTO.read_text(encoding="utf-8")
    dados = yaml.safe_load(conteudo)
    assert isinstance(dados, dict)

    assert dados.get("app-id") == "com.arestaclimb.Editor"
    assert dados.get("command") == "EditorAresta"

    finish_args = dados.get("finish-args", [])
    assert isinstance(finish_args, list)

    # Permissões mínimas de GUI e Rede
    assert "--share=network" in finish_args
    assert "--socket=fallback-x11" in finish_args or "--socket=x11" in finish_args
    assert "--socket=wayland" in finish_args
    assert "--share=ipc" in finish_args


def test_metainfo_appstream_estrutural() -> None:
    """Valida o arquivo AppStream XML contra requisitos do Flathub."""
    assert ARQUIVO_METAINFO.exists(), f"Metadados AppStream não encontrados em {ARQUIVO_METAINFO}"

    arvore = ET.parse(ARQUIVO_METAINFO)
    raiz = arvore.getroot()

    assert raiz.tag in ("component", "application")
    id_el = raiz.find("id")
    assert id_el is not None and id_el.text == "com.arestaclimb.Editor"

    nome_el = raiz.find("name")
    assert nome_el is not None and "Editor Aresta" in (nome_el.text or "")

    licenca_meta = raiz.find("metadata_license")
    assert licenca_meta is not None and licenca_meta.text is not None

    licenca_projeto = raiz.find("project_license")
    assert licenca_projeto is not None and licenca_projeto.text == "MPL-2.0"

    categorias = raiz.find("categories")
    assert categorias is not None
    lista_categorias = [c.text for c in categorias.findall("category")]
    assert len(lista_categorias) > 0


def test_arquivo_desktop_estrutural() -> None:
    """Valida o arquivo de atalho de desktop Linux."""
    assert ARQUIVO_DESKTOP.exists(), f"Arquivo .desktop não encontrado em {ARQUIVO_DESKTOP}"

    linhas = ARQUIVO_DESKTOP.read_text(encoding="utf-8").splitlines()
    assert "[Desktop Entry]" in linhas
    assert any(l.strip() == "Type=Application" for l in linhas)
    assert any("Name=Editor Aresta" in l for l in linhas)
    assert any("Exec=EditorAresta" in l for l in linhas)
    assert any("Icon=com.arestaclimb.Editor" in l for l in linhas)
    assert any("Categories=" in l for l in linhas)
