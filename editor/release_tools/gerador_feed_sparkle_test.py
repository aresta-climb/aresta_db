# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o gerador de feed Sparkle (appcast.xml) e assinatura Ed25519.
"""

import base64
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from editor.release_tools.gerador_feed_sparkle import (
    assinar_arquivo_ed25519,
    gerar_feed_sparkle,
    salvar_feed_sparkle,
)


def test_assinar_arquivo_ed25519_com_chave_valida(tmp_path: Path) -> None:
    """Gera um arquivo de teste, assina com chave Ed25519 e valida criptograficamente."""
    # Gera uma chave real para o teste
    chave_privada = ed25519.Ed25519PrivateKey.generate()
    chave_bytes = chave_privada.private_bytes_raw()
    chave_b64 = base64.b64encode(chave_bytes).decode("ascii")

    arquivo_dmg = tmp_path / "EditorAresta.dmg"
    conteudo_teste = b"BINARIO_DMG_SIMULADO_TESTE_ARESTA"
    arquivo_dmg.write_bytes(conteudo_teste)

    assinatura_b64 = assinar_arquivo_ed25519(arquivo_dmg, chave_b64)
    assert isinstance(assinatura_b64, str)
    assert len(assinatura_b64) > 0

    # Valida criptograficamente usando a chave pública
    assinatura_bytes = base64.b64decode(assinatura_b64)
    chave_publica = chave_privada.public_key()
    chave_publica.verify(assinatura_bytes, conteudo_teste)


def test_assinar_arquivo_ed25519_chave_invalida(tmp_path: Path) -> None:
    """Lança ValueError caso a chave privada não seja um Base64 de 32 bytes válido."""
    arquivo_dmg = tmp_path / "EditorAresta.dmg"
    arquivo_dmg.write_bytes(b"teste")

    # Caso 1: string inválida para decodificação
    with pytest.raises(ValueError, match="Chave privada Ed25519 inválida"):
        assinar_arquivo_ed25519(arquivo_dmg, "chave_invalida_curta")

    # Caso 2: base64 válido mas com tamanho diferente de 32 bytes
    chave_tamanho_errado = base64.b64encode(b"apenas_16_bytes!").decode("ascii")
    with pytest.raises(ValueError, match="Chave privada Ed25519 inválida"):
        assinar_arquivo_ed25519(arquivo_dmg, chave_tamanho_errado)


def test_gerar_feed_sparkle_conteudo_valido() -> None:
    """Valida se o XML do feed contém todos os nós exigidos pelo Sparkle RSS 2.0."""
    data_ref = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)
    xml = gerar_feed_sparkle(
        versao="0.4.0",
        url_download="https://serving.arestaclimb.com/editor-macos/EditorAresta-0.4.0.dmg",
        tamanho_bytes=45000000,
        assinatura_ed25519="MOCK_ED25519_SIG_BASE64",
        data_publicacao=data_ref,
        versao_minima_macos="12.0",
    )

    assert '<?xml version="1.0" encoding="utf-8"?>' in xml
    assert 'xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"' in xml
    assert "<title>Versão 0.4.0</title>" in xml
    assert 'sparkle:version="0.4.0"' in xml
    assert 'sparkle:shortVersionString="0.4.0"' in xml
    assert "<sparkle:minimumSystemVersion>12.0</sparkle:minimumSystemVersion>" in xml
    assert 'sparkle:edSignature="MOCK_ED25519_SIG_BASE64"' in xml
    assert 'length="45000000"' in xml
    assert 'url="https://serving.arestaclimb.com/editor-macos/EditorAresta-0.4.0.dmg"' in xml
    assert (
        "Sun, 04 Oct 2026 12:00:00 +0000" in xml
        or "Sun, 04 Oct 2026 12:00:00 GMT" in xml
        or "04 Oct 2026" in xml
    )


def test_gerar_feed_sparkle_versao_invalida() -> None:
    """Garante que versões fora do formato semântico levantem erro."""
    with pytest.raises(ValueError, match="Versão inválida"):
        gerar_feed_sparkle(
            versao="versao_invalida",
            url_download="https://exemplo.com/app.dmg",
            tamanho_bytes=100,
            assinatura_ed25519="sig",
        )


def test_salvar_feed_sparkle(tmp_path: Path) -> None:
    """Valida a gravação do XML do feed em arquivo de destino."""
    destino = tmp_path / "appcast.xml"
    xml_conteudo = "<rss><channel><title>Teste</title></channel></rss>"
    salvar_feed_sparkle(xml_conteudo, destino)

    assert destino.exists()
    assert destino.read_text(encoding="utf-8") == xml_conteudo


def test_gerar_feed_sparkle_data_padrao() -> None:
    """Valida geração do feed utilizando a data/hora UTC corrente por padrão."""
    xml = gerar_feed_sparkle(
        versao="1.0.0",
        url_download="https://exemplo.com/app.dmg",
        tamanho_bytes=500,
        assinatura_ed25519="sig123",
    )
    assert "<pubDate>" in xml
    assert 'sparkle:version="1.0.0"' in xml
    assert "<sparkle:criticalUpdate />" in xml


def test_gerar_feed_sparkle_sem_forcar_atualizacao() -> None:
    """Garante que a tag sparkle:criticalUpdate seja omitida quando forcar_atualizacao=False."""
    xml = gerar_feed_sparkle(
        versao="1.0.0",
        url_download="https://exemplo.com/app.dmg",
        tamanho_bytes=500,
        assinatura_ed25519="sig123",
        forcar_atualizacao=False,
    )
    assert "<sparkle:criticalUpdate />" not in xml
