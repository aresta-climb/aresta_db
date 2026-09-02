# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from PIL import Image
import pytest

from editor.core.transformacoes_imagem import (
    rotacionar_imagem_bytes,
    cortar_imagem_bytes,
    aplicar_mascara_bytes,
    obter_cor_pixel,
)


@pytest.fixture
def imagem_teste_bytes() -> bytes:
    """Gera uma imagem de 200x100 em formato WebP para testes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 100), color=(10, 20, 30))
    # Pinta uma região de destaque em (10, 20) até (20, 30)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 20, 20, 30], fill=(255, 128, 0))
    img.save(buf, format="WEBP", quality=95)
    return buf.getvalue()


class TestTransformacoesImagem:
    def test_rotacionar_90_graus_horario(self, imagem_teste_bytes: bytes) -> None:
        resultado = rotacionar_imagem_bytes(imagem_teste_bytes, 90)
        assert isinstance(resultado, bytes)
        assert resultado.startswith(b"RIFF")
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (100, 200)

    def test_rotacionar_90_graus_anti_horario(self, imagem_teste_bytes: bytes) -> None:
        resultado = rotacionar_imagem_bytes(imagem_teste_bytes, -90)
        assert isinstance(resultado, bytes)
        assert resultado.startswith(b"RIFF")
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (100, 200)

    def test_rotacionar_180_graus(self, imagem_teste_bytes: bytes) -> None:
        resultado = rotacionar_imagem_bytes(imagem_teste_bytes, 180)
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (200, 100)

    def test_rotacionar_graus_invalidos(self, imagem_teste_bytes: bytes) -> None:
        with pytest.raises(ValueError, match="múltiplo de 90"):
            rotacionar_imagem_bytes(imagem_teste_bytes, 45)

    def test_rotacionar_bytes_vazios_ou_invalidos(self) -> None:
        with pytest.raises(ValueError, match="Bytes de imagem inválidos"):
            rotacionar_imagem_bytes(b"", 90)
        with pytest.raises(ValueError, match="Bytes de imagem inválidos"):
            rotacionar_imagem_bytes(b"dados_corrompidos", 90)

    def test_cortar_imagem_valida(self, imagem_teste_bytes: bytes) -> None:
        # Corta de (10, 20) até (60, 80) -> largura=50, altura=60
        resultado = cortar_imagem_bytes(imagem_teste_bytes, (10, 20, 60, 80))
        assert isinstance(resultado, bytes)
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (50, 60)

    def test_cortar_imagem_com_coordenadas_invertidas(self, imagem_teste_bytes: bytes) -> None:
        # Passa (60, 80, 10, 20) - a função deve normalizar automaticamente
        resultado = cortar_imagem_bytes(imagem_teste_bytes, (60, 80, 10, 20))
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (50, 60)

    def test_cortar_imagem_com_clamping_alem_dos_limites(self, imagem_teste_bytes: bytes) -> None:
        # Limites da imagem: (200, 100). Pede corte de (-50, -20, 250, 150)
        resultado = cortar_imagem_bytes(imagem_teste_bytes, (-50, -20, 250, 150))
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (200, 100)

    def test_cortar_imagem_area_invalida(self, imagem_teste_bytes: bytes) -> None:
        with pytest.raises(ValueError, match="Área de corte inválida"):
            cortar_imagem_bytes(imagem_teste_bytes, (10, 10, 10, 10))

    def test_cortar_imagem_bytes_invalidos(self) -> None:
        with pytest.raises(ValueError, match="Bytes de imagem inválidos"):
            cortar_imagem_bytes(b"", (0, 0, 10, 10))

    def test_aplicar_mascara_preenchimento(self, imagem_teste_bytes: bytes) -> None:
        cor_vermelha = (255, 0, 0)
        resultado = aplicar_mascara_bytes(imagem_teste_bytes, (20, 20, 50, 50), cor_vermelha)
        assert isinstance(resultado, bytes)
        with Image.open(io.BytesIO(resultado)) as img:
            # Pixel dentro do retângulo de máscara deve ser próximo de vermelho
            px_m = img.getpixel((30, 30))
            assert isinstance(px_m, tuple)
            assert all(abs(a - b) <= 2 for a, b in zip(px_m[:3], cor_vermelha))
            # Pixel fora da máscara deve se manter próximo da cor original da imagem base
            px_f = img.getpixel((5, 5))
            assert isinstance(px_f, tuple)
            cor_base = Image.open(io.BytesIO(imagem_teste_bytes)).getpixel((5, 5))
            assert isinstance(cor_base, tuple)
            assert all(abs(a - b) <= 3 for a, b in zip(px_f[:3], cor_base[:3]))

    def test_aplicar_mascara_coordenadas_invertidas(self, imagem_teste_bytes: bytes) -> None:
        cor_azul = (0, 0, 255)
        resultado = aplicar_mascara_bytes(imagem_teste_bytes, (50, 50, 20, 20), cor_azul)
        with Image.open(io.BytesIO(resultado)) as img:
            px = img.getpixel((30, 30))
            assert isinstance(px, tuple)
            assert all(abs(a - b) <= 2 for a, b in zip(px[:3], cor_azul))

    def test_aplicar_mascara_area_nula_retorna_imagem(self, imagem_teste_bytes: bytes) -> None:
        # Retângulo nulo não altera a imagem
        resultado = aplicar_mascara_bytes(imagem_teste_bytes, (10, 10, 10, 10), (255, 255, 255))
        assert isinstance(resultado, bytes)

    def test_aplicar_mascara_bytes_invalidos(self) -> None:
        with pytest.raises(ValueError, match="Bytes de imagem inválidos"):
            aplicar_mascara_bytes(b"", (0, 0, 10, 10), (0, 0, 0))

    def test_obter_cor_pixel(self, imagem_teste_bytes: bytes) -> None:
        # Pixel comum (devido à compressão WebP com perdas, comparamos com tolerância)
        cor = obter_cor_pixel(imagem_teste_bytes, 0, 0)
        assert all(abs(a - b) <= 2 for a, b in zip(cor, (10, 20, 30)))

        # Pixel com cor de destaque
        cor_destaque = obter_cor_pixel(imagem_teste_bytes, 15, 25)
        assert all(abs(a - b) <= 2 for a, b in zip(cor_destaque, (255, 128, 0)))

    def test_rotacionar_0_graus(self, imagem_teste_bytes: bytes) -> None:
        resultado = rotacionar_imagem_bytes(imagem_teste_bytes, 0)
        assert isinstance(resultado, bytes)
        with Image.open(io.BytesIO(resultado)) as img:
            assert (img.width, img.height) == (200, 100)

    def test_abrir_imagem_tons_de_cinza(self) -> None:
        buf = io.BytesIO()
        img_gray = Image.new("L", (100, 100), color=128)
        img_gray.save(buf, format="PNG")
        bytes_gray = buf.getvalue()

        # Deve converter para RGB/RGBA e permitir rotação e obter_cor_pixel
        rotacionado = rotacionar_imagem_bytes(bytes_gray, 90)
        assert isinstance(rotacionado, bytes)

    def test_obter_cor_pixel_escala_cinza_e_formato_inesperado(self, monkeypatch: pytest.MonkeyPatch) -> None:
        buf = io.BytesIO()
        img_gray = Image.new("L", (50, 50), color=200)
        img_gray.save(buf, format="PNG")
        bytes_gray = buf.getvalue()

        # Simula retorno de int pelo getpixel
        monkeypatch.setattr("PIL.Image.Image.getpixel", lambda self, xy: 200)
        cor = obter_cor_pixel(bytes_gray, 10, 10)
        assert cor == (200, 200, 200)

        # Simula formato inesperado
        monkeypatch.setattr("PIL.Image.Image.getpixel", lambda self, xy: "formato_invalido")
        with pytest.raises(ValueError, match="Formato de pixel inesperado"):
            obter_cor_pixel(bytes_gray, 10, 10)

    def test_obter_cor_pixel_fora_dos_limites(self, imagem_teste_bytes: bytes) -> None:
        with pytest.raises(ValueError, match="fora dos limites"):
            obter_cor_pixel(imagem_teste_bytes, -1, 5)
        with pytest.raises(ValueError, match="fora dos limites"):
            obter_cor_pixel(imagem_teste_bytes, 250, 5)

    def test_obter_cor_pixel_bytes_invalidos(self) -> None:
        with pytest.raises(ValueError, match="Bytes de imagem inválidos"):
            obter_cor_pixel(b"", 0, 0)

    def test_converter_para_webp_disco(self, imagem_teste_bytes: bytes) -> None:
        from editor.core.transformacoes_imagem import converter_para_webp_disco
        bytes_disco = converter_para_webp_disco(imagem_teste_bytes, qualidade=90)
        assert isinstance(bytes_disco, bytes)
        assert bytes_disco.startswith(b"RIFF")
        # Deve estar em modo lossy VP8
        assert bytes_disco[12:16] == b"VP8 "

    def test_transformacoes_com_flag_sem_perdas_false(self, imagem_teste_bytes: bytes) -> None:
        bytes_lossy = rotacionar_imagem_bytes(imagem_teste_bytes, 90, sem_perdas=False)
        assert isinstance(bytes_lossy, bytes)
        assert bytes_lossy[12:16] == b"VP8 "



