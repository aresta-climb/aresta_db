# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest

from editor.core.processamento_imagem_campo import (
    sanitizar_nome_arquivo_imagem,
    verificar_conflito_nome_imagem,
    sugerir_nome_arquivo_disponivel,
    obter_metadados_imagem,
    comprimir_imagem_para_bytes_webp,
)


@pytest.fixture
def imagem_rgb_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 100), color=(255, 0, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def imagem_rgba_bytes():
    buf = io.BytesIO()
    img = Image.new("RGBA", (300, 150), color=(0, 255, 0, 128))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestSanitizacaoENomes:
    def test_sanitizar_nome_arquivo_imagem(self):
        assert sanitizar_nome_arquivo_imagem("Foto do Setor 01!.jpg") == "foto_do_setor_01.webp"
        assert sanitizar_nome_arquivo_imagem("Capa_Principal.PNG") == "capa_principal.webp"
        assert sanitizar_nome_arquivo_imagem("miniatura.webp") == "miniatura.webp"
        assert sanitizar_nome_arquivo_imagem("caminho/para/arquivo/Imagem 123.jpeg") == "imagem_123.webp"
        assert sanitizar_nome_arquivo_imagem("") == "imagem.webp"

    def test_verificar_conflito_nome_imagem(self, tmp_path):
        pasta_imagens = tmp_path / "imagens"
        pasta_imagens.mkdir()
        (pasta_imagens / "capa.webp").write_bytes(b"teste")

        assert verificar_conflito_nome_imagem("capa.webp", pasta_imagens) is True
        assert verificar_conflito_nome_imagem("outra.webp", pasta_imagens) is False

        # Verifica conflito também com buffer em memória
        imagens_memoria = {"imagens/em_memoria.webp": b"123"}
        assert verificar_conflito_nome_imagem("em_memoria.webp", pasta_imagens, imagens_memoria) is True
        assert verificar_conflito_nome_imagem("inexistente.webp", pasta_imagens, imagens_memoria) is False

    def test_sugerir_nome_arquivo_disponivel(self, tmp_path):
        pasta_imagens = tmp_path / "imagens"
        pasta_imagens.mkdir()
        (pasta_imagens / "setor.webp").write_bytes(b"1")
        (pasta_imagens / "setor_1.webp").write_bytes(b"2")

        sugestao = sugerir_nome_arquivo_disponivel("setor.webp", pasta_imagens)
        assert sugestao == "setor_2.webp"

        sugestao_livre = sugerir_nome_arquivo_disponivel("novo.webp", pasta_imagens)
        assert sugestao_livre == "novo.webp"


class TestMetadadosECompressao:
    def test_obter_metadados_imagem_a_partir_de_bytes(self, imagem_rgb_bytes):
        w, h, size_bytes, str_kb = obter_metadados_imagem(imagem_rgb_bytes)
        assert w == 200
        assert h == 100
        assert size_bytes == len(imagem_rgb_bytes)
        assert "KB" in str_kb or "B" in str_kb

    def test_obter_metadados_imagem_a_partir_de_arquivo(self, tmp_path, imagem_rgb_bytes):
        arquivo_teste = tmp_path / "teste.png"
        arquivo_teste.write_bytes(imagem_rgb_bytes)

        w, h, size_bytes, str_kb = obter_metadados_imagem(arquivo_teste)
        assert w == 200
        assert h == 100
        assert size_bytes == len(imagem_rgb_bytes)

    def test_obter_metadados_imagem_invalida_ou_inexistente(self, tmp_path):
        assert obter_metadados_imagem(b"dados invalidos") == (0, 0, 0, "0 KB")
        assert obter_metadados_imagem(tmp_path / "arquivo_fantasma.webp") == (0, 0, 0, "0 KB")
        assert obter_metadados_imagem("") == (0, 0, 0, "0 KB")
        assert obter_metadados_imagem(None) == (0, 0, 0, "0 KB")
        assert obter_metadados_imagem(123) == (0, 0, 0, "0 KB")

    def test_comprimir_imagem_rgb_para_bytes_webp(self, imagem_rgb_bytes):
        bytes_webp, w, h = comprimir_imagem_para_bytes_webp(imagem_rgb_bytes, quality=85)
        assert isinstance(bytes_webp, bytes)
        assert w == 200
        assert h == 100
        # Verifica se os bytes resultantes são lidos como WebP válido
        with Image.open(io.BytesIO(bytes_webp)) as img:
            assert img.format == "WEBP"
            assert img.size == (200, 100)

    def test_comprimir_imagem_rgba_para_bytes_webp(self, imagem_rgba_bytes):
        bytes_webp, w, h = comprimir_imagem_para_bytes_webp(imagem_rgba_bytes, quality=85)
        assert isinstance(bytes_webp, bytes)
        assert w == 300
        assert h == 150
        with Image.open(io.BytesIO(bytes_webp)) as img:
            assert img.format == "WEBP"

        # Testa também passando o objeto Image RGBA direto
        img_rgba = Image.new("RGBA", (50, 50), color=(0, 255, 0, 100))
        bytes_webp2, w2, h2 = comprimir_imagem_para_bytes_webp(img_rgba)
        assert w2 == 50

    def test_sanitizar_nome_arquivo_apenas_simbolos(self):
        assert sanitizar_nome_arquivo_imagem("!!!.jpg") == "imagem.webp"
        assert sanitizar_nome_arquivo_imagem(None) == "imagem.webp"

    def test_verificar_conflito_nome_vazio_e_com_prefixo_imagens(self, tmp_path):
        assert verificar_conflito_nome_imagem("", tmp_path) is False
        imagens_memoria = {"imagens/teste.webp": b"123"}
        assert verificar_conflito_nome_imagem("imagens/teste.webp", tmp_path, imagens_memoria) is True

    def test_obter_metadados_tamanhos_variados(self, tmp_path):
        # Tamanho pequeno < 1KB
        pequeno = Image.new("RGB", (10, 10))
        buf_pequeno = io.BytesIO()
        pequeno.save(buf_pequeno, format="PNG")
        w, h, sz, txt = obter_metadados_imagem(buf_pequeno.getvalue())
        assert "B" in txt

        # Tamanho grande > 1MB
        dados_1mb = b"0" * (1024 * 1024 + 100)
        # Mock com open
        arquivo_1mb = tmp_path / "grande.bin"
        arquivo_1mb.write_bytes(dados_1mb)
        # Teste com arquivo inexistente ou inválido
        assert obter_metadados_imagem(arquivo_1mb) == (0, 0, 0, "0 KB")

    def test_comprimir_imagem_com_redimensionamento_de_area(self):
        # Cria imagem grande (ex: 3000 x 2000 = 6MP > 4MP limite padrão)
        buf = io.BytesIO()
        img_grande = Image.new("RGB", (3000, 2000), color=(100, 150, 200))
        img_grande.save(buf, format="JPEG")

        max_area = 2000000  # 2MP para teste
        bytes_webp, w, h = comprimir_imagem_para_bytes_webp(buf.getvalue(), max_area=max_area)
        assert w * h <= max_area
        assert w < 3000
        assert h < 2000

        # Testa também passando o objeto Image.Image diretamente
        bytes_webp2, w2, h2 = comprimir_imagem_para_bytes_webp(img_grande, max_area=max_area)
        assert w2 * h2 <= max_area

    def test_obter_metadados_imagem_grande_em_mb(self, tmp_path):
        # Imagem grande válida
        img = Image.new("RGB", (2000, 2000), color=(128, 128, 128))
        caminho = tmp_path / "foto_mb.bmp"
        img.save(caminho, format="BMP")  # BMP fica > 10MB
        w, h, sz, txt = obter_metadados_imagem(caminho)
        assert "MB" in txt
        assert w == 2000

        # Imagem em KB
        img_kb = Image.new("RGB", (300, 300), color=(100, 100, 100))
        caminho_kb = tmp_path / "foto_kb.jpg"
        img_kb.save(caminho_kb, format="JPEG")
        w2, h2, sz2, txt2 = obter_metadados_imagem(caminho_kb)
        assert "KB" in txt2

    def test_sanitizar_nome_arquivo_espacos_e_pontos(self):
        assert sanitizar_nome_arquivo_imagem("   .jpg") == "imagem.webp"
        assert sanitizar_nome_arquivo_imagem("   ---   .jpg") == "imagem.webp"

    def test_sanitizar_nome_arquivo_extensao_pura(self):
        assert sanitizar_nome_arquivo_imagem(".webp") == "webp.webp"
        assert sanitizar_nome_arquivo_imagem(".png") == "png.webp"

    def test_comprimir_arquivo_escala_de_cinza(self, tmp_path):
        img_l = Image.new("L", (80, 80), color=128)
        caminho_l = tmp_path / "cinza.png"
        img_l.save(caminho_l)
        bytes_webp, w, h = comprimir_imagem_para_bytes_webp(str(caminho_l))
        assert w == 80
        assert h == 80
        assert len(bytes_webp) > 0

        # Testa Image em modo P direto
        img_p = Image.new("P", (60, 60))
        bytes_p, w_p, h_p = comprimir_imagem_para_bytes_webp(img_p)
        assert w_p == 60

    def test_comprimir_imagem_path_e_stream(self, tmp_path):
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 100))
        caminho = tmp_path / "stream_teste.png"
        img.save(caminho)

        # Usando Path
        bytes1, w1, h1 = comprimir_imagem_para_bytes_webp(caminho)
        assert len(bytes1) > 0

        # Usando objeto de stream aberto
        with open(caminho, "rb") as f:
            bytes2, w2, h2 = comprimir_imagem_para_bytes_webp(f)
            assert len(bytes2) > 0
