# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Utilitário para recalcular proporcionalmente coordenadas de POIs após redimensionamento de mapas."""

import json
from pathlib import Path
from typing import Any

from PIL import Image

from scripts.markdown_frontmatter_lib import (
    parse_md_com_frontmatter,
    salvar_md_com_frontmatter,
)


def escalar_valor(valor: int | float | None, escala: float) -> int | None:
    """Aplica fator de escala e arredonda para inteiro."""
    if valor is None:
        return None
    return int(round(valor * escala))


def processar_poi(poi: dict[str, Any], escala_x: float, escala_y: float) -> None:
    """Redimensiona coordenadas geométricas de um ponto de interesse."""
    if "circular" in poi:
        poi["circular"]["x"] = escalar_valor(poi["circular"]["x"], escala_x)
        poi["circular"]["y"] = escalar_valor(poi["circular"]["y"], escala_y)
        if "raio" in poi["circular"]:
            poi["circular"]["raio"] = escalar_valor(
                poi["circular"]["raio"], (escala_x + escala_y) / 2.0
            )

    if "circulo" in poi:
        poi["circulo"]["x"] = escalar_valor(poi["circulo"]["x"], escala_x)
        poi["circulo"]["y"] = escalar_valor(poi["circulo"]["y"], escala_y)
        if "raio" in poi["circulo"]:
            poi["circulo"]["raio"] = escalar_valor(
                poi["circulo"]["raio"], (escala_x + escala_y) / 2.0
            )

    if "retangulo" in poi:
        poi["retangulo"]["x"] = escalar_valor(poi["retangulo"]["x"], escala_x)
        poi["retangulo"]["y"] = escalar_valor(poi["retangulo"]["y"], escala_y)
        if "largura" in poi["retangulo"]:
            poi["retangulo"]["largura"] = escalar_valor(poi["retangulo"]["largura"], escala_x)
        if "altura" in poi["retangulo"]:
            poi["retangulo"]["altura"] = escalar_valor(poi["retangulo"]["altura"], escala_y)

    if "linha" in poi and "pontos" in poi["linha"]:
        for pt in poi["linha"]["pontos"]:
            pt["x"] = escalar_valor(pt["x"], escala_x)
            pt["y"] = escalar_valor(pt["y"], escala_y)

    if "poligono" in poi and "pontos" in poi["poligono"]:
        for pt in poi["poligono"]["pontos"]:
            pt["x"] = escalar_valor(pt["x"], escala_x)
            pt["y"] = escalar_valor(pt["y"], escala_y)


def recalcular_coordenadas(
    caminho_croqui: Path = Path("database/br_mg_ouro_preto_ouroboulder"),
) -> tuple[int, int]:
    """Recalcula coordenadas em JSONs de raw_mapas e arquivos Markdown do croqui informado."""
    imagens_dir = caminho_croqui / "imagens"
    raw_mapas_dir = imagens_dir / "raw_mapas"

    tamanhos_imagens: dict[str, tuple[int, int]] = {}
    for img_path in imagens_dir.glob("*.webp"):
        with Image.open(img_path) as img:
            tamanhos_imagens[img_path.name] = (img.width, img.height)

    # Passo 1: Atualizar JSONs em raw_mapas
    json_modificados = 0
    for json_path in raw_mapas_dir.glob("*.json"):
        if ".ocr_result" in json_path.name:
            continue

        with open(json_path, encoding="utf-8") as f:
            dados_json = json.load(f)

        caminho_imagem = dados_json.get("caminho_imagem_mapa", "")
        if not caminho_imagem:
            continue
        nome_img = caminho_imagem.split("/")[-1]

        if nome_img not in tamanhos_imagens:
            continue

        nova_largura, nova_altura = tamanhos_imagens[nome_img]
        largura_antiga = dados_json.get("dimensoes_imagem", {}).get("largura", 0)
        altura_antiga = dados_json.get("dimensoes_imagem", {}).get("altura", 0)

        if largura_antiga == 0 or altura_antiga == 0:
            continue

        if abs(largura_antiga - nova_largura) <= 2 and abs(altura_antiga - nova_altura) <= 2:
            continue

        escala_x = nova_largura / largura_antiga
        escala_y = nova_altura / altura_antiga

        for poi in dados_json.get("pontos_de_interesse", []):
            processar_poi(poi, escala_x, escala_y)

        dados_json["dimensoes_imagem"]["largura"] = nova_largura
        dados_json["dimensoes_imagem"]["altura"] = nova_altura

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dados_json, f, indent=2, ensure_ascii=False)
        json_modificados += 1

    # Passo 2: Atualizar os Markdowns
    md_modificados = 0
    for md_file in caminho_croqui.glob("*.md"):
        dados_fm, corpo = parse_md_com_frontmatter(md_file)
        if not dados_fm or "mapas" not in dados_fm:
            continue

        modificado = False
        for mapa in dados_fm["mapas"]:
            caminho_imagem = mapa.get("caminho_imagem_mapa", "")
            if not caminho_imagem:
                continue

            nome_img = caminho_imagem.split("/")[-1]
            if nome_img not in tamanhos_imagens:
                continue

            nova_largura, nova_altura = tamanhos_imagens[nome_img]
            largura_antiga = mapa.get("largura_mapa", 0)
            altura_antiga = mapa.get("altura_mapa", 0)

            if largura_antiga == 0 or altura_antiga == 0:
                continue
            if abs(largura_antiga - nova_largura) <= 2 and abs(altura_antiga - nova_altura) <= 2:
                continue

            escala_x = nova_largura / largura_antiga
            escala_y = nova_altura / altura_antiga

            mapa["largura_mapa"] = nova_largura
            mapa["altura_mapa"] = nova_altura

            for poi in mapa.get("pontos_de_interesse", []):
                processar_poi(poi, escala_x, escala_y)

            modificado = True

        if modificado:
            salvar_md_com_frontmatter(md_file, dados_fm, corpo)
            md_modificados += 1

    return json_modificados, md_modificados
