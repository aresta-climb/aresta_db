# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Biblioteca pura de gerenciamento de UIDs universais e links canônicos aresta.cc.

Esta biblioteca é o ponto único da verdade para criação, validação e formatação
de identificadores imutáveis NanoID 14c em Base62 para todo o ecossistema Aresta Climb.
O uso da biblioteca externa 'nanoid' é estritamente encapsulado neste módulo.
"""

from typing import Optional
import re
import string
import urllib.parse
import nanoid

# Alfabeto Base62 estritamente alfanumérico contínuo: [0-9a-zA-Z]
ALFABETO_BASE62: str = string.digits + string.ascii_letters
TAMANHO_UID: int = 14
DOMINIO_CURTO: str = "aresta.cc"
PREFIXO_URL: str = f"https://{DOMINIO_CURTO}/"

_REGEX_UID = re.compile(r"^[0-9a-zA-Z]{14}$")


def gerar_uid() -> str:
    """Gera um NanoID de 14 caracteres Base62 contínuo, seguro e sem viés estatístico.

    Utiliza o algoritmo oficial do nanoid com CSPRNG do sistema operacional
    e o alfabeto Base62 [0-9a-zA-Z].
    """
    return nanoid.generate(alphabet=ALFABETO_BASE62, size=TAMANHO_UID)


def validar_uid(uid: Optional[str]) -> bool:
    """Valida se o identificador possui exatamente 14 caracteres alfanuméricos Base62.

    Rejeita nulos, tamanhos diferentes de 14, caracteres especiais (incluindo
    hífens e underscores) e espaços.
    """
    if not isinstance(uid, str):
        return False
    return bool(_REGEX_UID.match(uid))


def formatar_url_aresta(uid: str) -> str:
    """Retorna a URL canônica encurtada correspondente ao UID informado.

    Formato: https://aresta.cc/<uid> (exatamente 32 caracteres).
    Levanta ValueError se o UID for inválido.
    """
    if not validar_uid(uid):
        raise ValueError(f"UID inválido: '{uid}'. Deve conter exatamente 14 caracteres Base62.")
    return f"{PREFIXO_URL}{uid}"


def extrair_uid_de_url(url: str) -> Optional[str]:
    """Extrai e valida o UID a partir de uma URL curta ou link escaneado.

    Aceita variações com http, https, com ou sem barra final, e parâmetros de consulta.
    Retorna None se a URL não pertencer ao domínio aresta.cc ou se o UID for inválido.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    texto = url.strip()
    if not texto.startswith(("http://", "https://")):
        texto = f"https://{texto}"

    try:
        parsed = urllib.parse.urlparse(texto)
    except Exception:
        return None

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if host != DOMINIO_CURTO:
        return None

    caminho = parsed.path.strip("/")
    if not caminho:
        return None

    segmentos = caminho.split("/")
    candidato = segmentos[0]

    if validar_uid(candidato):
        return candidato

    return None
