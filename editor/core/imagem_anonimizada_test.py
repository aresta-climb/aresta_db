# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
import pytest
from PIL import Image
from editor.core.imagem_anonimizada import gerar_webp_anonimizado


def _criar_imagem_teste_bytes(formato: str, modo: str, tamanho: tuple[int, int]) -> bytes:
    """Helper para criar bytes de imagem em memória para testes."""
    img = Image.new(modo, tamanho, color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format=formato)
    return buffer.getvalue()


def test_gerar_webp_anonimizado_png_rgb():
    # DADO uma imagem PNG 1920x1080 em modo RGB
    bytes_originais = _criar_imagem_teste_bytes("PNG", "RGB", (1920, 1080))
    
    # QUANDO gerar a versão anonimizada
    bytes_anonimizados = gerar_webp_anonimizado(bytes_originais)
    
    # ENTÃO os bytes devem ser válidos e ter tamanho inferior a 150 bytes
    assert len(bytes_anonimizados) > 0
    assert len(bytes_anonimizados) < 1024
    
    # E ao abrir com Pillow, deve ser formato WEBP com dimensões exatamente 1920x1080
    with Image.open(io.BytesIO(bytes_anonimizados)) as img:
        assert img.format == "WEBP"
        assert img.size == (1920, 1080)


def test_gerar_webp_anonimizado_jpeg_alta_resolucao():
    # DADO uma imagem JPEG 4000x3000 (12 megapixels)
    bytes_originais = _criar_imagem_teste_bytes("JPEG", "RGB", (4000, 3000))
    
    # QUANDO gerar a versão anonimizada
    bytes_anonimizados = gerar_webp_anonimizado(bytes_originais)
    
    # ENTÃO o tamanho deve ser drasticamente reduzido (< 150 bytes)
    assert len(bytes_anonimizados) > 0
    assert len(bytes_anonimizados) < 1024
    
    with Image.open(io.BytesIO(bytes_anonimizados)) as img:
        assert img.format == "WEBP"
        assert img.size == (4000, 3000)


def test_gerar_webp_anonimizado_rgba_transparencia():
    # DADO uma imagem RGBA com transparência
    bytes_originais = _criar_imagem_teste_bytes("PNG", "RGBA", (800, 600))
    
    # QUANDO gerar a versão anonimizada
    bytes_anonimizados = gerar_webp_anonimizado(bytes_originais)
    
    assert len(bytes_anonimizados) > 0
    assert len(bytes_anonimizados) < 1024
    
    with Image.open(io.BytesIO(bytes_anonimizados)) as img:
        assert img.format == "WEBP"
        assert img.size == (800, 600)
        assert img.mode == "RGBA"


def test_gerar_webp_anonimizado_dados_vazios_ou_invalidos():
    # DADO entrada vazia ou corrompida
    assert gerar_webp_anonimizado(b"") == b""
    assert gerar_webp_anonimizado(None) == b""
    assert gerar_webp_anonimizado(b"conteudo_invalido_que_nao_e_imagem") == b""
