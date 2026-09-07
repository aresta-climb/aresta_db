# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração determinística do manifesto XML do Windows App Installer (.appinstaller).
Permite a distribuição e atualização automática do pacote MSIX do canal Beta.
"""

import re
from typing import Optional


PADRAO_VERSAO_TRES_DIGITOS = re.compile(r"^\d+\.\d+\.\d+$")
PADRAO_VERSAO_QUATRO_DIGITOS = re.compile(r"^\d+\.\d+\.\d+\.\d+$")

NOME_PACOTE_PADRAO: str = "ArestaClimbApps.EditorArestaClimb.Beta"
PUBLISHER_PADRAO: str = "CN=0C77D74C-16DF-46A3-A959-0CA285AF3E46"
URI_BASE_PADRAO: str = "https://serving.arestaclimb.com/editor-beta"


def formatar_versao_quatro_partes(versao: str) -> str:
    """
    Normaliza a versão semântica para o formato de 4 partes exigido pelo manifesto MSIX.
    Ex: '1.2.0' -> '1.2.0.0'.
    """
    versao_limpa = versao.strip()
    if PADRAO_VERSAO_QUATRO_DIGITOS.match(versao_limpa):
        return versao_limpa
    if PADRAO_VERSAO_TRES_DIGITOS.match(versao_limpa):
        return f"{versao_limpa}.0"

    raise ValueError(f"Versão inválida para o manifesto AppInstaller: '{versao}'. Esperado formato X.Y.Z ou X.Y.Z.W.")


def gerar_conteudo_appinstaller(
    versao: str,
    uri_base: str = URI_BASE_PADRAO,
    nome_pacote: str = NOME_PACOTE_PADRAO,
    publisher: str = PUBLISHER_PADRAO,
) -> str:
    """
    Gera o conteúdo XML formatado do arquivo .appinstaller apontando para o binário no R2.
    """
    versao_normalizada = formatar_versao_quatro_partes(versao)
    uri_limpa = uri_base.rstrip("/")

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<AppInstaller
    xmlns="http://schemas.microsoft.com/appx/appinstaller/2018"
    Version="{versao_normalizada}"
    Uri="{uri_limpa}/EditorArestaBeta.appinstaller">

    <MainPackage
        Name="{nome_pacote}"
        Publisher="{publisher}"
        Version="{versao_normalizada}"
        ProcessorArchitecture="x64"
        Uri="{uri_limpa}/EditorArestaBeta.msix" />

    <UpdateSettings>
        <OnLaunch HoursBetweenUpdateChecks="0" ShowPrompt="false" UpdateBlocksActivation="true" />
        <AutomaticBackgroundTask />
        <ForceUpdateFromAnyVersion>true</ForceUpdateFromAnyVersion>
    </UpdateSettings>
</AppInstaller>
"""
    return xml
