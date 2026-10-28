# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import io
import json
from collections.abc import Sequence
from typing import Any

from PIL import Image, ImageDraw

MARGEM_REGUA_PX = 28
JANELA_RECORTE_MEIO_PX = 60
ESCALA_RECORTE = 2


def _codificar_png_base64(imagem: Image.Image) -> str:
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _extrair_info_poi(poi: Any) -> dict[str, Any]:
    """Extrai uid, rótulo, tipo_area, coordenada âncora (x, y) e parâmetros geométricos de um POI."""
    poi_obj = getattr(poi, "_obj", poi)
    uid = str(getattr(poi_obj, "uid", "") or "")
    rotulo = str(getattr(poi_obj, "rotulo", "") or getattr(poi_obj, "label", "") or "")
    tipo_area = poi_obj.WhichOneof("tipo_area") if hasattr(poi_obj, "WhichOneof") else None

    if tipo_area == "circulo":
        c = poi_obj.circulo
        return {
            "uid": uid,
            "rotulo": rotulo,
            "tipo_area": "circulo",
            "ancora_x": int(c.x),
            "ancora_y": int(c.y),
            "raio": max(int(c.raio), 4),
        }
    if tipo_area == "quadrado":
        q = poi_obj.quadrado
        return {
            "uid": uid,
            "rotulo": rotulo,
            "tipo_area": "quadrado",
            "ancora_x": int(q.x),
            "ancora_y": int(q.y),
            "lado": max(int(q.lado), 6),
        }
    if tipo_area == "retangulo":
        r = poi_obj.retangulo
        return {
            "uid": uid,
            "rotulo": rotulo,
            "tipo_area": "retangulo",
            "ancora_x": int(r.x),
            "ancora_y": int(r.y),
            "comprimento": max(int(r.comprimento), 6),
            "largura": max(int(r.largura), 6),
        }
    if tipo_area == "poligono":
        coords = list(poi_obj.poligono.coordenadas)
        pares = [
            (int(coords[i]), int(coords[i + 1])) for i in range(0, len(coords) - 1, 2)
        ]
        cx = sum(p[0] for p in pares) // len(pares)
        cy = sum(p[1] for p in pares) // len(pares)
        return {
            "uid": uid,
            "rotulo": rotulo,
            "tipo_area": "poligono",
            "ancora_x": cx,
            "ancora_y": cy,
            "pontos": pares,
        }
    if tipo_area == "linha":
        nos = [(int(n.x), int(n.y)) for n in poi_obj.linha.conteudo.nos]
        ax, ay = nos[0]
        return {
            "uid": uid,
            "rotulo": rotulo,
            "tipo_area": "linha",
            "ancora_x": ax,
            "ancora_y": ay,
            "nos": nos,
        }

    return {
        "uid": uid,
        "rotulo": rotulo,
        "tipo_area": "",
        "ancora_x": None,
        "ancora_y": None,
    }


def _desenhar_pois_na_imagem(
    imagem_rgba: Image.Image, infos_pois: Sequence[dict[str, Any]]
) -> Image.Image:
    """Desenha todas as geometrias de POIs em vermelho translúcido sobre a imagem do mapa."""
    camada = Image.new("RGBA", imagem_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(camada)
    cor_borda = (235, 30, 30, 235)
    cor_preenchimento = (235, 30, 30, 55)

    for info in infos_pois:
        tipo = info["tipo_area"]
        x = info["ancora_x"]
        y = info["ancora_y"]
        if x is None or y is None:
            continue

        if tipo == "circulo":
            r = info["raio"]
            draw.ellipse(
                (x - r, y - r, x + r, y + r),
                fill=cor_preenchimento,
                outline=cor_borda,
                width=2,
            )
        elif tipo == "quadrado":
            meio = info["lado"] // 2
            draw.rectangle(
                (x - meio, y - meio, x + meio, y + meio),
                fill=cor_preenchimento,
                outline=cor_borda,
                width=2,
            )
        elif tipo == "retangulo":
            mx = info["comprimento"] // 2
            my = info["largura"] // 2
            draw.rectangle(
                (x - mx, y - my, x + mx, y + my),
                fill=cor_preenchimento,
                outline=cor_borda,
                width=2,
            )
        elif tipo == "poligono":
            draw.polygon(info["pontos"], fill=cor_preenchimento, outline=cor_borda)
        elif tipo == "linha":
            draw.line(info["nos"], fill=cor_borda, width=3)

        rotulo = info["rotulo"]
        draw.text((x + 6, y - 10), rotulo, fill=(255, 255, 0, 255))

    return Image.alpha_composite(imagem_rgba, camada)


def _aplicar_grade_e_reguas_globais(imagem_rgba: Image.Image) -> Image.Image:
    """Adiciona grade métrica semitransparente (50px/100px) e réguas graduadas X/Y nas bordas."""
    larg, alt = imagem_rgba.size
    camada_grade = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
    draw_grade = ImageDraw.Draw(camada_grade)

    for x in range(0, larg, 50):
        cor = (0, 220, 255, 110) if x % 100 == 0 else (255, 255, 255, 50)
        draw_grade.line([(x, 0), (x, alt)], fill=cor, width=1)
    for y in range(0, alt, 50):
        cor = (0, 220, 255, 110) if y % 100 == 0 else (255, 255, 255, 50)
        draw_grade.line([(0, y), (larg, y)], fill=cor, width=1)

    com_grade = Image.alpha_composite(imagem_rgba, camada_grade)

    # Cria moldura com réguas nas bordas superior (X) e esquerda (Y)
    m = MARGEM_REGUA_PX
    painel = Image.new("RGBA", (larg + m, alt + m), (24, 28, 34, 255))
    painel.paste(com_grade, (m, m))
    draw_regua = ImageDraw.Draw(painel)

    for x in range(0, larg, 100):
        px = m + x
        draw_regua.line([(px, m - 6), (px, m)], fill=(0, 220, 255, 255), width=1)
        draw_regua.text((px + 2, 6), str(x), fill=(230, 240, 250, 255))

    for y in range(0, alt, 100):
        py = m + y
        draw_regua.line([(m - 6, py), (m, py)], fill=(0, 220, 255, 255), width=1)
        draw_regua.text((2, py + 2), str(y), fill=(230, 240, 250, 255))

    return painel


def _gerar_recorte_poi_com_regua_relativa(
    imagem_base_com_pois: Image.Image, info: dict[str, Any]
) -> Image.Image:
    """
    Gera um recorte centrado em `(ancora_x, ancora_y)` com janela de `120x120px`
    (`-60px` a `+60px`), escalado 2x (`240x240px`), mira em `(0, 0)` e réguas relativas (`-50..+50`).
    """
    cx = int(info["ancora_x"])
    cy = int(info["ancora_y"])
    meio = JANELA_RECORTE_MEIO_PX
    lado_orig = meio * 2
    lado_zoom = lado_orig * ESCALA_RECORTE

    janela = Image.new("RGBA", (lado_orig, lado_orig), (30, 30, 30, 255))
    recorte = imagem_base_com_pois.crop((cx - meio, cy - meio, cx + meio, cy + meio))
    janela.paste(recorte, (0, 0))

    ampliada = janela.resize((lado_zoom, lado_zoom), Image.Resampling.NEAREST)
    sobreposicao = Image.new("RGBA", (lado_zoom, lado_zoom), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(sobreposicao)
    centro_px = meio * ESCALA_RECORTE

    # Grade relativa fina a cada 25px e mira central em (0, 0)
    for delta in (-50, -25, 0, 25, 50):
        pos = centro_px + delta * ESCALA_RECORTE
        cor = (0, 255, 200, 150) if delta == 0 else (255, 255, 255, 65)
        draw_ov.line([(pos, 0), (pos, lado_zoom)], fill=cor, width=1)
        draw_ov.line([(0, pos), (lado_zoom, pos)], fill=cor, width=1)

    ampliada = Image.alpha_composite(ampliada, sobreposicao)

    m = MARGEM_REGUA_PX
    painel = Image.new("RGBA", (lado_zoom + m, lado_zoom + m), (24, 28, 34, 255))
    painel.paste(ampliada, (m, m))
    draw_regua = ImageDraw.Draw(painel)

    for delta in (-50, -25, 0, 25, 50):
        pos = m + centro_px + delta * ESCALA_RECORTE
        rotulo_delta = f"+{delta}" if delta > 0 else str(delta)
        draw_regua.line([(pos, m - 5), (pos, m)], fill=(0, 255, 200, 255), width=1)
        draw_regua.text((pos - 8, 6), rotulo_delta, fill=(230, 240, 250, 255))
        draw_regua.line([(m - 5, pos), (m, pos)], fill=(0, 255, 200, 255), width=1)
        draw_regua.text((2, pos - 6), rotulo_delta, fill=(230, 240, 250, 255))

    return painel


def renderizar_pacote_visual_mapa(
    bytes_imagem: bytes,
    pontos_de_interesse: Sequence[Any],
    incluir_grade: bool = True,
    incluir_recortes_pois: bool = True,
    candidatos_vetoriais: Sequence[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Renderiza o pacote visual completo de um mapa para inspeção por agentes LLM via MCP,
    retornando uma lista intercalada de blocos `[Texto, Imagem]`:
    - Bloco 0 (Texto): Metadados do mapa, candidatos vetoriais extraídos do PDF e resumo dos POIs.
    - Bloco 1 (Imagem): Visão geral completa do mapa com POIs em vermelho e grade métrica de 100px.
    - Blocos seguintes (Pares `[Texto, Imagem]`): Para cada POI com coordenada válida, metadados
      da âncora e recorte ampliado centrado em `(0, 0)` com régua relativa (`-50px` a `+50px`).
    """
    img_original = Image.open(io.BytesIO(bytes_imagem)).convert("RGBA")
    largura, altura = img_original.size

    infos_pois = [_extrair_info_poi(p) for p in pontos_de_interesse]
    img_com_pois = _desenhar_pois_na_imagem(img_original, infos_pois)
    img_visao_geral = (
        _aplicar_grade_e_reguas_globais(img_com_pois) if incluir_grade else img_com_pois
    )

    resumo_metadados = {
        "largura": largura,
        "altura": altura,
        "total_pois": len(infos_pois),
        "incluir_grade": incluir_grade,
        "instrucoes_leitura_grade": (
            "A imagem a seguir exibe o mapa completo com réguas graduadas em pixels nas bordas "
            "superior (X) e esquerda (Y) e grade a cada 50px/100px."
        ),
        "candidatos_vetoriais": list(candidatos_vetoriais or []),
        "pois": [
            {
                "uid": info["uid"],
                "rotulo": info["rotulo"],
                "tipo_area": info["tipo_area"],
                "ancora_x": info["ancora_x"],
                "ancora_y": info["ancora_y"],
            }
            for info in infos_pois
        ],
    }

    blocos: list[dict[str, Any]] = [
        {"type": "text", "text": json.dumps(resumo_metadados, ensure_ascii=False)},
        {
            "type": "image",
            "data": _codificar_png_base64(img_visao_geral.convert("RGB")),
            "mimeType": "image/png",
        },
    ]

    if incluir_recortes_pois:
        for idx, info in (
            (i, inf) for i, inf in enumerate(infos_pois) if inf["ancora_x"] is not None
        ):
            recorte_img = _gerar_recorte_poi_com_regua_relativa(img_com_pois, info)
            texto_poi = {
                "indice_poi": idx,
                "uid": info["uid"],
                "rotulo": info["rotulo"],
                "tipo_area": info["tipo_area"],
                "ancora_x": info["ancora_x"],
                "ancora_y": info["ancora_y"],
                "instrucao_ajuste": (
                    "A mira central verde/ciano corresponde a (0, 0) na âncora atual "
                    f"({info['ancora_x']}, {info['ancora_y']}). Para centralizar sobre o número "
                    "na foto, leia o deslocamento (dx, dy) nas réguas relativas (-50 a +50) e "
                    "atualize para (ancora_x + dx, ancora_y + dy)."
                ),
            }
            blocos.append({"type": "text", "text": json.dumps(texto_poi, ensure_ascii=False)})
            blocos.append(
                {
                    "type": "image",
                    "data": _codificar_png_base64(recorte_img.convert("RGB")),
                    "mimeType": "image/png",
                }
            )

    return blocos
