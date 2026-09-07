# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import hashlib
import pytest

from editor.release_tools.gerador_instalador_bat import (
    gerar_script_instalador_bat,
    calcular_thumbprint_sha256,
    URL_SUCESSO_PADRAO,
)

CERTIFICADO_CORPO_B64 = "MIIBtzCCAVygAwIBAgIQCX8s1234567890ABCDEF"
CERTIFICADO_VALIDO_PEM = f"""-----BEGIN CERTIFICATE-----
{CERTIFICADO_CORPO_B64}
-----END CERTIFICATE-----"""


def test_url_sucesso_padrao_aponta_para_certificado_instalado() -> None:
    """Valida se a URL padrão aponta para /editor/beta/certificado-instalado."""
    assert URL_SUCESSO_PADRAO == "https://arestaclimb.com/editor/beta/certificado-instalado"


def test_calcular_thumbprint_sha256_sucesso() -> None:
    """Valida o cálculo determinístico do Thumbprint SHA-256 a partir dos bytes DER do PEM."""
    bytes_esperados = base64.b64decode(CERTIFICADO_CORPO_B64)
    hash_esperada = hashlib.sha256(bytes_esperados).hexdigest().lower()

    thumbprint = calcular_thumbprint_sha256(CERTIFICADO_VALIDO_PEM)
    assert thumbprint == hash_esperada


def test_calcular_thumbprint_sha256_invalido() -> None:
    """Garante que certificados sem marcadores PEM ou vazios falhem ao calcular thumbprint."""
    with pytest.raises(ValueError, match="Certificado PEM inválido"):
        calcular_thumbprint_sha256("texto sem tags")

    with pytest.raises(ValueError, match="Certificado PEM inválido"):
        calcular_thumbprint_sha256("")


def test_calcular_thumbprint_sha256_com_padding_automatico() -> None:
    """Garante que certificados Base64 sem padding '==' sejam completados e decodificados com sucesso."""
    pem_sem_padding = "-----BEGIN CERTIFICATE-----\nMIIBtzCCAVygAwIBAgIQCX8s1234567890ABCD\n-----END CERTIFICATE-----"
    thumbprint = calcular_thumbprint_sha256(pem_sem_padding)
    assert len(thumbprint) == 64


def test_calcular_thumbprint_sha256_base64_corrompido() -> None:
    """Garante que certificados com caracteres não-Base64 entre as tags lancem ValueError informativo."""
    pem_corrompido = "-----BEGIN CERTIFICATE-----\n!@#$%\n-----END CERTIFICATE-----"
    with pytest.raises(ValueError, match="conteúdo Base64 corrompido"):
        calcular_thumbprint_sha256(pem_corrompido)


def test_gerar_script_instalador_bat_sucesso() -> None:
    """Valida a geração do script batch com todos os comandos e parâmetros de URL."""
    script = gerar_script_instalador_bat(CERTIFICADO_VALIDO_PEM)
    thumbprint = calcular_thumbprint_sha256(CERTIFICADO_VALIDO_PEM)

    assert "@echo off" in script
    assert "net session >nul 2>&1" in script
    assert "-WindowStyle Hidden" in script
    assert 'certutil -decode "%~f0"' in script
    assert 'certutil -addstore -f "TrustedPeople"' in script
    assert 'del "%TEMP%\\ArestaBeta.cer"' in script
    assert f'start "" "{URL_SUCESSO_PADRAO}?origem=instalador&thumbprint={thumbprint}"' in script
    assert "exit /b 0" in script
    assert CERTIFICADO_VALIDO_PEM in script


def test_gerar_script_instalador_bat_url_customizada_com_e_sem_query() -> None:
    """Valida se URLs customizadas recebem os parâmetros adequadamente usando ? ou &."""
    thumbprint = calcular_thumbprint_sha256(CERTIFICADO_VALIDO_PEM)

    # Sem query pré-existente
    url_sem_query = "https://meudominio.local/beta/instalado"
    script1 = gerar_script_instalador_bat(CERTIFICADO_VALIDO_PEM, url_sucesso=url_sem_query)
    assert f'start "" "{url_sem_query}?origem=instalador&thumbprint={thumbprint}"' in script1

    # Com query pré-existente
    url_com_query = "https://meudominio.local/beta/instalado?origem_extra=1"
    script2 = gerar_script_instalador_bat(CERTIFICADO_VALIDO_PEM, url_sucesso=url_com_query)
    assert f'start "" "{url_com_query}&origem=instalador&thumbprint={thumbprint}"' in script2


def test_gerar_script_instalador_bat_certificado_invalido() -> None:
    """Garante que certificados sem os marcadores PEM válidos lancem ValueError."""
    with pytest.raises(ValueError, match="Certificado PEM inválido"):
        gerar_script_instalador_bat("conteudo_invalido_sem_tags")

    with pytest.raises(ValueError, match="Certificado PEM inválido"):
        gerar_script_instalador_bat("")
