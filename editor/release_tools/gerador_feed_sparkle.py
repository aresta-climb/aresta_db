# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração determinística do feed XML do Sparkle Framework (appcast.xml)
e assinatura digital Ed25519 para atualizações automáticas in-app no macOS.
"""

import base64
import email.utils
import re
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519

PADRAO_VERSAO_SEMANTICA = re.compile(r"^\d+\.\d+\.\d+")


def assinar_arquivo_ed25519(caminho_arquivo: Path, chave_privada_base64: str) -> str:
    """
    Assina digitalmente o arquivo binário utilizando a chave privada Ed25519.
    Retorna a assinatura formatada em Base64 para uso na tag sparkle:edSignature.
    """
    try:
        chave_bytes = base64.b64decode(chave_privada_base64)
        if len(chave_bytes) != 32:
            raise ValueError(f"Tamanho de chave inesperado: {len(chave_bytes)} bytes")
        chave_privada = ed25519.Ed25519PrivateKey.from_private_bytes(chave_bytes)
    except Exception as e:
        raise ValueError(f"Chave privada Ed25519 inválida: {e}") from e

    dados = caminho_arquivo.read_bytes()
    assinatura = chave_privada.sign(dados)
    return base64.b64encode(assinatura).decode("ascii")


def gerar_feed_sparkle(
    versao: str,
    url_download: str,
    tamanho_bytes: int,
    assinatura_ed25519: str,
    data_publicacao: datetime | None = None,
    versao_minima_macos: str = "12.0",
    forcar_atualizacao: bool = True,
) -> str:
    """
    Gera o conteúdo RSS 2.0 do feed appcast.xml compatível com o Sparkle Framework.
    """
    versao_limpa = versao.strip()
    if not PADRAO_VERSAO_SEMANTICA.match(versao_limpa):
        raise ValueError(
            f"Versão inválida para o feed Sparkle: '{versao}'. Esperado formato semântico X.Y.Z."
        )

    data_item = data_publicacao or datetime.now(UTC)
    data_formatada = email.utils.format_datetime(data_item)
    tag_critico = "      <sparkle:criticalUpdate />\n" if forcar_atualizacao else ""

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Atualizações do Editor Aresta</title>
    <link>https://serving.arestaclimb.com/editor-macos/appcast.xml</link>
    <description>Feed oficial de atualizações do Editor Aresta para macOS.</description>
    <language>pt-BR</language>
    <item>
      <title>Versão {versao_limpa}</title>
      <pubDate>{data_formatada}</pubDate>
{tag_critico}      <sparkle:minimumSystemVersion>{versao_minima_macos}</sparkle:minimumSystemVersion>
      <enclosure
        url="{url_download}"
        sparkle:version="{versao_limpa}"
        sparkle:shortVersionString="{versao_limpa}"
        length="{tamanho_bytes}"
        type="application/octet-stream"
        sparkle:edSignature="{assinatura_ed25519}" />
    </item>
  </channel>
</rss>
"""
    return xml


def salvar_feed_sparkle(conteudo_xml: str, caminho_destino: Path) -> None:
    """
    Grava o XML do feed no caminho de destino especificado utilizando UTF-8.
    """
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    caminho_destino.write_text(conteudo_xml, encoding="utf-8")
