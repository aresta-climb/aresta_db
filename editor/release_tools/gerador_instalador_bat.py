# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração do script batch (.bat) auto-contido de instalação do certificado
de assinatura de testes do Editor Aresta Beta com execução oculta e redirecionamento web.
"""

import base64
import hashlib
from typing import Optional


URL_SUCESSO_PADRAO: str = "https://arestaclimb.com/editor/beta/certificado-instalado"
MARCADOR_INICIO_PEM: str = "-----BEGIN CERTIFICATE-----"
MARCADOR_FIM_PEM: str = "-----END CERTIFICATE-----"


def calcular_thumbprint_sha256(conteudo_certificado_pem: str) -> str:
    """
    Calcula a impressão digital SHA-256 (Thumbprint) a partir dos dados binários DER
    embutidos no certificado em formato PEM.
    """
    cert_limpo = conteudo_certificado_pem.strip()
    if MARCADOR_INICIO_PEM not in cert_limpo or MARCADOR_FIM_PEM not in cert_limpo:
        raise ValueError(
            f"Certificado PEM inválido: deve conter os marcadores '{MARCADOR_INICIO_PEM}' e '{MARCADOR_FIM_PEM}'."
        )

    inicio = cert_limpo.index(MARCADOR_INICIO_PEM) + len(MARCADOR_INICIO_PEM)
    fim = cert_limpo.index(MARCADOR_FIM_PEM)
    corpo_b64 = "".join(cert_limpo[inicio:fim].split()).replace("-", "+").replace("_", "/")
    corpo_sem_pad = corpo_b64.rstrip("=")
    resto = len(corpo_sem_pad) % 4
    if resto:
        corpo_b64 = corpo_sem_pad + "=" * (4 - resto)
    else:
        corpo_b64 = corpo_sem_pad

    try:
        dados_der = base64.b64decode(corpo_b64, validate=True)
    except Exception as e:
        raise ValueError(f"Certificado PEM inválido: conteúdo Base64 corrompido ({e}).") from e

    return hashlib.sha256(dados_der).hexdigest().lower()


def gerar_script_instalador_bat(
    conteudo_certificado_pem: str,
    url_sucesso: str = URL_SUCESSO_PADRAO,
) -> str:
    """
    Gera o script batch auto-contido contendo o certificado embutido em Base64.
    O script se auto-eleva sem abrir janela de prompt de comando visível,
    extrai e instala o certificado e abre o navegador padrão na página de sucesso.
    """
    thumbprint = calcular_thumbprint_sha256(conteudo_certificado_pem)
    cert_limpo = conteudo_certificado_pem.strip()

    separador = "&" if "?" in url_sucesso else "?"
    url_final = f"{url_sucesso}{separador}origem=instalador&thumbprint={thumbprint}"

    script = f"""@echo off
:: 1. Desbloqueia o arquivo para evitar avisos adicionais de seguranca
powershell -NoProfile -Command "Unblock-File -Path '%~f0'" >nul 2>&1

:: 2. Decodifica o certificado no diretorio temporario
certutil -decode "%~f0" "%TEMP%\\ArestaBeta.cer" >nul 2>&1

:: 3. Instala o certificado na loja TrustedPeople com elevacao apenas para o certutil
net session >nul 2>&1
if %errorLevel% equ 0 (
    certutil -addstore -f "TrustedPeople" "%TEMP%\\ArestaBeta.cer" >nul 2>&1
) else (
    powershell -NoProfile -Command "Start-Process certutil.exe -ArgumentList '-addstore -f TrustedPeople \"%TEMP%\\ArestaBeta.cer\"' -Verb RunAs -WindowStyle Hidden -Wait"
)

:: 4. Remove arquivo temporario e abre pagina de sucesso
del "%TEMP%\\ArestaBeta.cer" >nul 2>&1
start "" "{url_final}"
exit /b 0

{cert_limpo}
"""
    return script
