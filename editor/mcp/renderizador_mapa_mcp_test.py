# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import base64
import io
import json

from PIL import Image

from aresta_api.proto.generated import croqui_pb2
from editor.mcp.renderizador_mapa_mcp import (
    renderizar_cena_mapa_editor,
    renderizar_pacote_visual_mapa,
)
from editor.views.widget_editor_mapas import ItemBoundingQuadrado, criar_item_visual_poi


def _gerar_imagem_png_bytes(largura: int = 320, altura: int = 240) -> bytes:
    img = Image.new("RGB", (largura, altura), color=(60, 80, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_renderizar_pacote_visual_mapa_com_grade_e_recortes_todas_geometrias():
    """
    Valida a geração da lista intercalada [Texto, Imagem] contendo:
    1. Metadados + candidatos vetoriais + visão geral com grade métrica de 100px e réguas X/Y.
    2. Pares [Texto do POI, Recorte ampliado com mira relativa -50..+50] para círculo, quadrado,
       retângulo, polígono e linha.
    """
    bytes_img = _gerar_imagem_png_bytes(320, 240)

    p_circ = croqui_pb2.Mapa.PontoDeInteresse(uid="uid_p1", rotulo="1")
    p_circ.circulo.x = 100
    p_circ.circulo.y = 120
    p_circ.circulo.raio = 14

    p_quad = croqui_pb2.Mapa.PontoDeInteresse(uid="uid_p2", rotulo="2")
    p_quad.quadrado.x = 180
    p_quad.quadrado.y = 90
    p_quad.quadrado.lado = 24

    p_ret = croqui_pb2.Mapa.PontoDeInteresse(uid="uid_p3", rotulo="E1")
    p_ret.retangulo.x = 250
    p_ret.retangulo.y = 160
    p_ret.retangulo.comprimento = 36
    p_ret.retangulo.largura = 20
    p_ret.retangulo.angulo_graus_x100 = 4500

    img_cena = renderizar_cena_mapa_editor(bytes_img, [p_circ, p_quad, p_ret])
    assert img_cena.size == (320, 240)
    # Verifica que os itens da QGraphicsScene do Editor (incluindo o retângulo rotacionado)
    # foram efetivamente desenhados sobre o fundo (60, 80, 100) nas coordenadas das âncoras
    assert img_cena.getpixel((100, 120))[:3] != (60, 80, 100)
    assert img_cena.getpixel((180, 90))[:3] != (60, 80, 100)
    assert img_cena.getpixel((250, 160))[:3] != (60, 80, 100)

    item_quad = criar_item_visual_poi(p_quad)
    assert isinstance(item_quad, ItemBoundingQuadrado)

    p_poli = croqui_pb2.Mapa.PontoDeInteresse(uid="uid_p4", rotulo="P1")
    p_poli.poligono.coordenadas.extend([40, 40, 70, 40, 55, 70])

    p_linha = croqui_pb2.Mapa.PontoDeInteresse(uid="uid_p5", rotulo="L1")
    n1 = p_linha.linha.conteudo.nos.add(x=80, y=200)
    n2 = p_linha.linha.conteudo.nos.add(x=90, y=140)
    assert n1.x == 80 and n2.y == 140

    blocos = renderizar_pacote_visual_mapa(
        bytes_imagem=bytes_img,
        pontos_de_interesse=[p_circ, p_quad, p_ret, p_poli, p_linha],
        incluir_grade=True,
        incluir_recortes_pois=True,
        candidatos_vetoriais=[{"texto": "1", "x": 100, "y": 120}],
    )

    # 2 blocos globais (Texto + Imagem geral) + 5 pares [Texto POI, Imagem Recorte] = 12 blocos
    assert len(blocos) == 12
    assert blocos[0]["type"] == "text"
    meta_geral = json.loads(blocos[0]["text"])
    assert meta_geral["largura"] == 320
    assert meta_geral["altura"] == 240
    assert meta_geral["total_pois"] == 5
    assert meta_geral["candidatos_vetoriais"] == [{"texto": "1", "x": 100, "y": 120}]

    assert blocos[1]["type"] == "image"
    assert blocos[1]["mimeType"] == "image/png"
    img_geral = Image.open(io.BytesIO(base64.b64decode(blocos[1]["data"])))
    # Com réguas nas bordas (margem de régua superior e esquerda), a imagem geral tem pelo menos 320x240
    assert img_geral.width >= 320
    assert img_geral.height >= 240

    # Verifica o primeiro par de recorte de POI (uid_p1)
    assert blocos[2]["type"] == "text"
    meta_poi_1 = json.loads(blocos[2]["text"])
    assert meta_poi_1["uid"] == "uid_p1"
    assert meta_poi_1["rotulo"] == "1"
    assert meta_poi_1["tipo_area"] == "circulo"
    assert meta_poi_1["ancora_x"] == 100
    assert meta_poi_1["ancora_y"] == 120

    assert blocos[3]["type"] == "image"
    img_recorte = Image.open(io.BytesIO(base64.b64decode(blocos[3]["data"])))
    assert img_recorte.width >= 240
    assert img_recorte.height >= 240


def test_renderizar_pacote_visual_mapa_sem_grade_e_sem_recortes():
    """Quando incluir_grade=False e incluir_recortes_pois=False, retorna apenas os 2 blocos iniciais."""
    bytes_img = _gerar_imagem_png_bytes(200, 150)
    p_vazio = croqui_pb2.Mapa.PontoDeInteresse(uid="uid_sem_area", rotulo="X")

    blocos = renderizar_pacote_visual_mapa(
        bytes_imagem=bytes_img,
        pontos_de_interesse=[p_vazio],
        incluir_grade=False,
        incluir_recortes_pois=False,
    )
    assert len(blocos) == 2
    img_geral = Image.open(io.BytesIO(base64.b64decode(blocos[1]["data"])))
    assert img_geral.size == (200, 150)
