# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest

from editor.core.imagens_markdown import (
    sanitizar_nome_imagem,
    gerar_nome_imagem_padrao,
    gerar_nome_imagem_clipboard,
    formatar_tag_markdown,
    salvar_imagem_otimizada,
)


def test_sanitizar_nome_imagem():
    # Converte acentos, pontuações, espaços e extensão para .webp em snake_case
    assert sanitizar_nome_imagem("Foto do Setor Principal (Cópia).png") == "foto_do_setor_principal_copia.webp"
    assert sanitizar_nome_imagem("Área de Escalada - Via 1!.JPG") == "area_de_escalada_via_1.webp"
    assert sanitizar_nome_imagem("imagem.webp") == "imagem.webp"
    assert sanitizar_nome_imagem("nome_com___muitos---tracos e espacos.jpeg") == "nome_com_muitos_tracos_e_espacos.webp"
    assert sanitizar_nome_imagem("") == "imagem.webp"
    assert sanitizar_nome_imagem("!!!???...") == "imagem.webp"


def test_gerar_nome_imagem_padrao(tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()

    # Primeiro arquivo: não existe colisão
    nome1 = gerar_nome_imagem_padrao("Foto Bloco.jpg", pasta_imagens)
    assert nome1 == "foto_bloco.webp"

    # Cria o arquivo para simular colisão
    (pasta_imagens / "foto_bloco.webp").write_bytes(b"teste")

    # Segundo arquivo com mesmo nome: deve adicionar sufixo numérico _1
    nome2 = gerar_nome_imagem_padrao("Foto Bloco.jpg", pasta_imagens)
    assert nome2 == "foto_bloco_1.webp"

    # Cria o arquivo _1
    (pasta_imagens / "foto_bloco_1.webp").write_bytes(b"teste")

    # Terceiro arquivo: deve virar _2
    nome3 = gerar_nome_imagem_padrao("Foto Bloco.jpg", pasta_imagens)
    assert nome3 == "foto_bloco_2.webp"


def test_gerar_nome_imagem_clipboard(tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()

    nome = gerar_nome_imagem_clipboard(pasta_imagens)
    assert nome.startswith("imagem_")
    assert nome.endswith(".webp")

    # Se criarmos o arquivo com o mesmo nome, deve evitar colisão adicionando sufixo
    (pasta_imagens / nome).write_bytes(b"teste")
    nome_colisao = gerar_nome_imagem_clipboard(pasta_imagens)
    assert nome_colisao.endswith(".webp")
    assert not (pasta_imagens / nome_colisao).exists()


def test_formatar_tag_markdown():
    assert formatar_tag_markdown("bloco.webp", "Vista Frontal") == "![Vista Frontal](imagens/bloco.webp)"
    assert formatar_tag_markdown("bloco.webp", "") == "![](imagens/bloco.webp)"
    assert formatar_tag_markdown("bloco.webp", None) == "![](imagens/bloco.webp)"
    assert formatar_tag_markdown("bloco.webp") == "![](imagens/bloco.webp)"


def test_salvar_imagem_otimizada(tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()
    caminho_destino = pasta_imagens / "foto_salva.webp"

    # Cria uma imagem PIL para salvar
    img = Image.new("RGB", (300, 200), color=(255, 0, 0))
    largura, altura = salvar_imagem_otimizada(img, caminho_destino)

    assert caminho_destino.exists()
    assert largura == 300
    assert altura == 200

    # Verifica formato do arquivo gravado
    with Image.open(caminho_destino) as img_gravada:
        assert img_gravada.format == "WEBP"
        assert img_gravada.size == (300, 200)


def test_salvar_imagem_otimizada_a_partir_de_bytes(tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()
    caminho_destino = pasta_imagens / "foto_bytes.webp"

    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(0, 255, 0))
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    largura, altura = salvar_imagem_otimizada(png_bytes, caminho_destino)
    assert caminho_destino.exists()
    assert largura == 100
    assert altura == 100
