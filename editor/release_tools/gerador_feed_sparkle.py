# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração determinística do feed XML do Sparkle Framework (appcast.xml)
e assinatura digital Ed25519 para atualizações automáticas in-app no macOS.
"""

import base64
import email.utils
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519

PADRAO_VERSAO_SEMANTICA = re.compile(r"^\d+\.\d+\.\d+")


@dataclass(frozen=True)
class ItemFeedSparkle:
    """Representa uma versão empacotada individual para um canal/arquitetura no feed do Sparkle."""

    versao: str
    url_download: str
    tamanho_bytes: int
    assinatura_ed25519: str
    arquitetura: str | None = None
    versao_minima_macos: str = "12.0"
    forcar_atualizacao: bool = True
    titulo: str | None = None


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


def gerar_feed_sparkle_multi_arquitetura(
    itens: list[ItemFeedSparkle],
    data_publicacao: datetime | None = None,
) -> str:
    """
    Gera o conteúdo RSS 2.0 do feed appcast.xml suportando múltiplos itens por arquitetura
    decorados com sparkle:hardwareRequirements (ex: arm64 e x86_64).
    """
    if not itens:
        raise ValueError("Pelo menos um item deve ser fornecido para gerar o feed Sparkle.")

    data_item = data_publicacao or datetime.now(UTC)
    data_formatada = email.utils.format_datetime(data_item)

    blocos_itens: list[str] = []
    for item in itens:
        versao_limpa = item.versao.strip()
        if not PADRAO_VERSAO_SEMANTICA.match(versao_limpa):
            raise ValueError(
                f"Versão inválida para o feed Sparkle: '{item.versao}'. Esperado formato semântico X.Y.Z."
            )

        titulo = item.titulo or f"Versão {versao_limpa}"
        tag_critico = "      <sparkle:criticalUpdate />\n" if item.forcar_atualizacao else ""
        tag_hardware = (
            f"      <sparkle:hardwareRequirements>{item.arquitetura}</sparkle:hardwareRequirements>\n"
            if item.arquitetura
            else ""
        )

        bloco_item = f"""    <item>
      <title>{titulo}</title>
      <pubDate>{data_formatada}</pubDate>
{tag_critico}{tag_hardware}      <sparkle:minimumSystemVersion>{item.versao_minima_macos}</sparkle:minimumSystemVersion>
      <enclosure
        url="{item.url_download}"
        sparkle:version="{versao_limpa}"
        sparkle:shortVersionString="{versao_limpa}"
        length="{item.tamanho_bytes}"
        type="application/octet-stream"
        sparkle:edSignature="{item.assinatura_ed25519}" />
    </item>"""
        blocos_itens.append(bloco_item)

    conteudo_itens = "\n".join(blocos_itens)

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Atualizações do Editor Aresta</title>
    <link>https://serving.arestaclimb.com/editor-macos/appcast.xml</link>
    <description>Feed oficial de atualizações do Editor Aresta para macOS.</description>
    <language>pt-BR</language>
{conteudo_itens}
  </channel>
</rss>
"""
    return xml


def gerar_feed_sparkle(
    versao: str,
    url_download: str,
    tamanho_bytes: int,
    assinatura_ed25519: str,
    data_publicacao: datetime | None = None,
    versao_minima_macos: str = "12.0",
    forcar_atualizacao: bool = True,
    arquitetura: str | None = None,
) -> str:
    """
    Gera o conteúdo RSS 2.0 do feed appcast.xml compatível com o Sparkle Framework para um item único.
    """
    item = ItemFeedSparkle(
        versao=versao,
        url_download=url_download,
        tamanho_bytes=tamanho_bytes,
        assinatura_ed25519=assinatura_ed25519,
        arquitetura=arquitetura,
        versao_minima_macos=versao_minima_macos,
        forcar_atualizacao=forcar_atualizacao,
    )
    return gerar_feed_sparkle_multi_arquitetura([item], data_publicacao=data_publicacao)


def salvar_feed_sparkle(conteudo_xml: str, caminho_destino: Path) -> None:
    """
    Grava o XML do feed no caminho de destino especificado utilizando UTF-8.
    """
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    caminho_destino.write_text(conteudo_xml, encoding="utf-8")
