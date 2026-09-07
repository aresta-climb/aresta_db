# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import xml.etree.ElementTree as ET

from editor.release_tools.gerador_appinstaller import (
    gerar_conteudo_appinstaller,
    formatar_versao_quatro_partes,
)


def test_formatar_versao_quatro_partes_valida() -> None:
    """Testa a normalização de versões semânticas de 3 para 4 dígitos exigida pelo Windows."""
    assert formatar_versao_quatro_partes("1.2.3") == "1.2.3.0"
    assert formatar_versao_quatro_partes("1.2.3.4") == "1.2.3.4"
    assert formatar_versao_quatro_partes("0.1.0") == "0.1.0.0"


def test_formatar_versao_invalida_lanca_excecao() -> None:
    """Garante que versões malformadas lancem ValueError descritivo."""
    with pytest.raises(ValueError, match="Versão inválida"):
        formatar_versao_quatro_partes("")
    with pytest.raises(ValueError, match="Versão inválida"):
        formatar_versao_quatro_partes("1.2")
    with pytest.raises(ValueError, match="Versão inválida"):
        formatar_versao_quatro_partes("abc")


def test_gerar_conteudo_appinstaller_estrutura_xml() -> None:
    """Testa se o XML gerado é sintaticamente válido e possui todos os nós e atributos obrigatórios."""
    versao = "0.2.1"
    uri_base = "https://serving.arestaclimb.com/editor-beta"
    xml_str = gerar_conteudo_appinstaller(versao, uri_base)

    # Valida integridade do XML
    raiz = ET.fromstring(xml_str)
    ns = {"appx": "http://schemas.microsoft.com/appx/appinstaller/2018"}

    assert raiz.tag == f"{{{ns['appx']}}}AppInstaller"
    assert raiz.attrib["Version"] == "0.2.1.0"
    assert raiz.attrib["Uri"] == "https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.appinstaller"

    main_pkg = raiz.find("appx:MainPackage", ns)
    assert main_pkg is not None
    assert main_pkg.attrib["Name"] == "ArestaClimbApps.EditorArestaClimb.Beta"
    assert main_pkg.attrib["Version"] == "0.2.1.0"
    assert main_pkg.attrib["ProcessorArchitecture"] == "x64"
    assert main_pkg.attrib["Uri"] == "https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.msix"

    update_settings = raiz.find("appx:UpdateSettings", ns)
    assert update_settings is not None

    on_launch = update_settings.find("appx:OnLaunch", ns)
    assert on_launch is not None
    assert on_launch.attrib["HoursBetweenUpdateChecks"] == "0"

    auto_bg = update_settings.find("appx:AutomaticBackgroundTask", ns)
    assert auto_bg is not None

    force_update = update_settings.find("appx:ForceUpdateFromAnyVersion", ns)
    assert force_update is not None
    assert force_update.text == "true"


def test_gerar_conteudo_appinstaller_normaliza_barras_uri() -> None:
    """Garante que barras extras no final do uri_base sejam tratadas sem duplicação."""
    xml_str = gerar_conteudo_appinstaller("1.0.0", "https://serving.arestaclimb.com/editor-beta///")
    assert "https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.appinstaller" in xml_str
    assert "https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.msix" in xml_str
