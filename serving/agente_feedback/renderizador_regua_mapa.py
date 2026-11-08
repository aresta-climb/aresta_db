# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Renderizador em memória de régua cartesiana graduada em pixels (eixos X e Y),
grade de referência e pontos de interesse atuais sobre imagens de mapa de setores.
Facilita a leitura visual de coordenadas `(x, y, raio)` pelo modelo multimodal.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw

MARGEM_REGUA_PX = 42
PASSO_GRADE_PX = 100


@dataclass(frozen=True)
class MapaAnotadoEmMemoria:
    """Representa uma imagem de mapa anotada com régua cartesiana pronta para envio ao LLM."""

    caminho_imagem_mapa: str
    largura_mapa: int
    altura_mapa: int
    dados_imagem: bytes
    mime_type: str = "image/png"


def renderizar_mapa_com_regua_bytes(
    caminho_imagem: Path,
    largura_mapa: int,
    altura_mapa: int,
    pontos_de_interesse: list[dict[str, Any]],
) -> bytes:
    """
    Carrega `caminho_imagem`, ajusta para `(largura_mapa, altura_mapa)`, adiciona uma moldura
    externa de `MARGEM_REGUA_PX` com régua graduada nos eixos X e Y, grade a cada `PASSO_GRADE_PX`
    e desenha os círculos e rótulos de `pontos_de_interesse`, retornando os bytes em PNG.
    """
    with Image.open(caminho_imagem) as img_orig:
        img_rgb = img_orig.convert("RGB")
        if img_rgb.size != (largura_mapa, altura_mapa):
            img_rgb = img_rgb.resize((largura_mapa, altura_mapa), Image.Resampling.LANCZOS)

    largura_total = largura_mapa + 2 * MARGEM_REGUA_PX
    altura_total = altura_mapa + 2 * MARGEM_REGUA_PX

    tela = Image.new("RGB", (largura_total, altura_total), color=(24, 24, 28))
    tela.paste(img_rgb, (MARGEM_REGUA_PX, MARGEM_REGUA_PX))

    desenho = ImageDraw.Draw(tela)

    # Moldura ao redor do mapa
    x0 = MARGEM_REGUA_PX
    y0 = MARGEM_REGUA_PX
    x1 = MARGEM_REGUA_PX + largura_mapa
    y1 = MARGEM_REGUA_PX + altura_mapa
    desenho.rectangle([x0 - 1, y0 - 1, x1, y1], outline=(200, 200, 200), width=1)

    # Eixo X: régua no topo e na base + linhas verticais pontilhadas
    for x_rel in range(0, largura_mapa + 1, PASSO_GRADE_PX):
        px = x0 + x_rel
        # Traços da régua
        desenho.line([(px, y0 - 8), (px, y0)], fill=(255, 220, 80), width=2)
        desenho.line([(px, y1), (px, y1 + 8)], fill=(255, 220, 80), width=2)
        # Rótulo numérico X
        rotulo_x = str(x_rel)
        desenho.text((px - 10, y0 - 24), rotulo_x, fill=(255, 220, 80))
        desenho.text((px - 10, y1 + 10), rotulo_x, fill=(255, 220, 80))
        # Linha de grade vertical pontilhada
        if 0 < x_rel < largura_mapa:
            for py_ponto in range(y0, y1, 8):
                desenho.point((px, py_ponto), fill=(255, 255, 255))

    # Eixo Y: régua na esquerda e na direita + linhas horizontais pontilhadas
    for y_rel in range(0, altura_mapa + 1, PASSO_GRADE_PX):
        py = y0 + y_rel
        desenho.line([(x0 - 8, py), (x0, py)], fill=(120, 230, 255), width=2)
        desenho.line([(x1, py), (x1 + 8, py)], fill=(120, 230, 255), width=2)
        rotulo_y = str(y_rel)
        desenho.text((4, py - 6), rotulo_y, fill=(120, 230, 255))
        desenho.text((x1 + 10, py - 6), rotulo_y, fill=(120, 230, 255))
        if 0 < y_rel < altura_mapa:
            for px_ponto in range(x0, x1, 8):
                desenho.point((px_ponto, py), fill=(255, 255, 255))

    # Desenha os pontos de interesse atuais (círculos e rótulos)
    for poi in pontos_de_interesse:
        circulo = poi.get("circulo")
        if not isinstance(circulo, dict):
            continue
        cx = int(circulo.get("x", 0)) + x0
        cy = int(circulo.get("y", 0)) + y0
        raio = max(6, int(circulo.get("raio", 20)))
        rotulo = str(poi.get("rotulo", ""))

        desenho.ellipse(
            [cx - raio, cy - raio, cx + raio, cy + raio],
            outline=(255, 60, 60),
            width=3,
        )
        if rotulo:
            desenho.text((cx - 6, cy - 6), rotulo, fill=(255, 255, 0))

    buffer = io.BytesIO()
    tela.save(buffer, format="PNG")
    return buffer.getvalue()


def extrair_e_renderizar_mapas_do_setor(
    pasta_croqui: Path,
    caminho_relativo_md: str,
) -> list[MapaAnotadoEmMemoria]:
    """
    Lê o arquivo `.md` indicado em `pasta_croqui / caminho_relativo_md`, extrai a lista `mapas`
    do frontmatter YAML e renderiza em memória cada imagem de mapa existente com régua cartesiana.
    """
    caminho_md = pasta_croqui / caminho_relativo_md
    if not caminho_md.is_file():
        return []

    texto = caminho_md.read_text(encoding="utf-8")
    if not texto.startswith("---\n") or "\n---\n" not in texto:
        return []

    bloco_yaml = texto.split("\n---\n", 1)[0][4:]
    dados = yaml.safe_load(bloco_yaml)
    mapas = dados.get("mapas") if isinstance(dados, dict) else None
    if not isinstance(mapas, list):
        return []

    resultado: list[MapaAnotadoEmMemoria] = []
    for item_mapa in mapas:
        caminho_rel_img = str(item_mapa.get("caminho_imagem_mapa", ""))
        caminho_img = pasta_croqui / caminho_rel_img
        if not caminho_rel_img or not caminho_img.is_file():
            continue

        largura = int(item_mapa.get("largura_mapa", 800))
        altura = int(item_mapa.get("altura_mapa", 600))
        pois = item_mapa.get("pontos_de_interesse") or []

        bytes_png = renderizar_mapa_com_regua_bytes(
            caminho_imagem=caminho_img,
            largura_mapa=largura,
            altura_mapa=altura,
            pontos_de_interesse=pois,
        )
        resultado.append(
            MapaAnotadoEmMemoria(
                caminho_imagem_mapa=caminho_rel_img,
                largura_mapa=largura,
                altura_mapa=altura,
                dados_imagem=bytes_png,
            )
        )

    return resultado
