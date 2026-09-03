# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Módulo matemático para cálculo e interpolação de Spline Centripetal Catmull-Rom.

Este módulo segue o princípio "Library-First" do Aresta, sendo puramente matemático
e sem dependência de bibliotecas de interface gráfica (como PyQt). Permite converter
uma lista ordenada de nós 2D em Curvas de Bézier Cúbicas suaves e exportar para
o formato padrão SVG Path ("M ... C ...").
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Union, Sequence


@dataclass(frozen=True)
class Ponto2D:
    """Representa um ponto bidimensional com coordenadas de ponto flutuante."""
    x: float
    y: float

    def distancia_ate(self, outro: 'Ponto2D') -> float:
        """Calcula a distância euclidiana até outro ponto."""
        return math.hypot(self.x - outro.x, self.y - outro.y)


@dataclass(frozen=True)
class SegmentoBezierCubica:
    """Representa um segmento de curva cúbica de Bézier."""
    p0: Ponto2D  # Ponto inicial
    c1: Ponto2D  # Primeiro ponto de controle
    c2: Ponto2D  # Segundo ponto de controle
    p3: Ponto2D  # Ponto final


def sanitizar_pontos(
    pontos: Sequence[Union[Tuple[float, float], Ponto2D, Dict[str, Any]]],
    tolerancia: float = 1e-3
) -> List[Ponto2D]:
    """
    Converte e sanitiza uma lista de coordenadas em instâncias de Ponto2D,
    removendo pontos duplicados ou excessivamente próximos de forma consecutiva.
    """
    if not pontos:
        return []

    resultado: List[Ponto2D] = []
    for item in pontos:
        if isinstance(item, Ponto2D):
            p = item
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            p = Ponto2D(float(item[0]), float(item[1]))
        elif isinstance(item, dict) and 'x' in item and 'y' in item:
            p = Ponto2D(float(item['x']), float(item['y']))
        else:
            continue

        if not resultado or resultado[-1].distancia_ate(p) > tolerancia:
            resultado.append(p)

    return resultado


def _calcular_controles_catmull_rom(
    p0: Ponto2D,
    p1: Ponto2D,
    p2: Ponto2D,
    p3: Ponto2D,
    alfa: float = 0.5
) -> Tuple[Ponto2D, Ponto2D]:
    """
    Calcula os dois pontos de controle Bézier (c1, c2) para o segmento entre p1 e p2
    utilizando a formulação Centripetal Catmull-Rom.
    """
    d01 = p0.distancia_ate(p1)
    d12 = p1.distancia_ate(p2)
    d23 = p2.distancia_ate(p3)

    t0 = 0.0
    t1 = t0 + (d01 ** alfa if d01 > 0 else 1.0)
    t2 = t1 + (d12 ** alfa if d12 > 0 else 1.0)
    t3 = t2 + (d23 ** alfa if d23 > 0 else 1.0)

    dt01 = t1 - t0 if t1 != t0 else 1.0
    dt12 = t2 - t1 if t2 != t1 else 1.0
    dt23 = t3 - t2 if t3 != t2 else 1.0
    dt02 = t2 - t0 if t2 != t0 else 1.0
    dt13 = t3 - t1 if t3 != t1 else 1.0

    # Tangente no ponto p1
    fator1 = dt12 / 3.0
    v1_x = (p1.x - p0.x) / dt01 - (p2.x - p0.x) / dt02 + (p2.x - p1.x) / dt12
    v1_y = (p1.y - p0.y) / dt01 - (p2.y - p0.y) / dt02 + (p2.y - p1.y) / dt12
    c1 = Ponto2D(p1.x + fator1 * v1_x, p1.y + fator1 * v1_y)

    # Tangente no ponto p2
    fator2 = dt12 / 3.0
    v2_x = (p3.x - p2.x) / dt23 - (p3.x - p1.x) / dt13 + (p2.x - p1.x) / dt12
    v2_y = (p3.y - p2.y) / dt23 - (p3.y - p1.y) / dt13 + (p2.y - p1.y) / dt12
    c2 = Ponto2D(p2.x - fator2 * v2_x, p2.y - fator2 * v2_y)

    return c1, c2


def converter_pontos_para_bezier(
    pontos: Sequence[Union[Tuple[float, float], Ponto2D, Dict[str, Any]]],
    alfa: float = 0.5
) -> List[SegmentoBezierCubica]:
    """
    Converte uma lista de nós 2D em uma lista de segmentos cúbicos de Bézier
    suavizados via Catmull-Rom Centripetal.
    """
    pts = sanitizar_pontos(pontos)
    n = len(pts)

    if n < 2:
        return []

    if n == 2:
        p0, p1 = pts[0], pts[1]
        c1 = Ponto2D(p0.x + (p1.x - p0.x) / 3.0, p0.y + (p1.y - p0.y) / 3.0)
        c2 = Ponto2D(p0.x + 2.0 * (p1.x - p0.x) / 3.0, p0.y + 2.0 * (p1.y - p0.y) / 3.0)
        return [SegmentoBezierCubica(p0, c1, c2, p1)]

    segmentos: List[SegmentoBezierCubica] = []
    for i in range(n - 1):
        p1 = pts[i]
        p2 = pts[i + 1]

        # Extrapolação virtual para as bordas
        p0 = Ponto2D(2.0 * pts[0].x - pts[1].x, 2.0 * pts[0].y - pts[1].y) if i == 0 else pts[i - 1]
        p3 = Ponto2D(2.0 * pts[-1].x - pts[-2].x, 2.0 * pts[-1].y - pts[-2].y) if i == n - 2 else pts[i + 2]

        c1, c2 = _calcular_controles_catmull_rom(p0, p1, p2, p3, alfa=alfa)
        segmentos.append(SegmentoBezierCubica(p1, c1, c2, p2))

    return segmentos


def gerar_caminho_svg(
    pontos: Sequence[Union[Tuple[float, float], Ponto2D, Dict[str, Any]]],
    alfa: float = 0.5
) -> str:
    """
    Gera a string de Path SVG correspondente à Spline dos nós fornecidos.
    Exemplo de saída: "M 100 800 C 120 700, 140 600, 160 500"
    """
    pts = sanitizar_pontos(pontos)
    if not pts:
        return ""
    if len(pts) == 1:
        return f"M {pts[0].x:.0f} {pts[0].y:.0f}"

    segmentos = converter_pontos_para_bezier(pts, alfa=alfa)
    comandos = [f"M {segmentos[0].p0.x:.0f} {segmentos[0].p0.y:.0f}"]
    for seg in segmentos:
        comandos.append(
            f"C {seg.c1.x:.1f} {seg.c1.y:.1f}, {seg.c2.x:.1f} {seg.c2.y:.1f}, {seg.p3.x:.0f} {seg.p3.y:.0f}"
        )

    return " ".join(comandos)


def calcular_caixa_delimitadora(
    pontos: Sequence[Union[Tuple[float, float], Ponto2D, Dict[str, Any]]]
) -> Tuple[int, int, int, int]:
    """
    Calcula a caixa delimitadora retangular centralizada (x_centro, y_centro, comprimento, largura)
    a partir de uma lista de pontos.
    """
    pts = sanitizar_pontos(pontos)
    if not pts:
        return 0, 0, 0, 0

    min_x = min(p.x for p in pts)
    max_x = max(p.x for p in pts)
    min_y = min(p.y for p in pts)
    max_y = max(p.y for p in pts)

    comprimento = max(1, int(round(max_x - min_x)))
    largura = max(1, int(round(max_y - min_y)))
    x_centro = int(round(min_x + comprimento / 2.0))
    y_centro = int(round(min_y + largura / 2.0))

    return x_centro, y_centro, comprimento, largura


def calcular_angulos_tangentes(
    pontos: Sequence[Union[Tuple[float, float], Ponto2D, Dict[str, Any]]]
) -> List[float]:
    """
    Calcula o ângulo tangencial (em graus, de -180 a 180) para cada nó na sequência.
    Útil para orientar ícones (como chapeletas e tops) de acordo com o sentido do traçado.
    """
    pts = sanitizar_pontos(pontos)
    n = len(pts)
    if not pts:
        return []
    if n == 1:
        return [0.0]

    angulos: List[float] = []
    for i in range(n):
        if i == 0:
            dx = pts[1].x - pts[0].x
            dy = pts[1].y - pts[0].y
        elif i == n - 1:
            dx = pts[-1].x - pts[-2].x
            dy = pts[-1].y - pts[-2].y
        else:
            dx = pts[i + 1].x - pts[i - 1].x
            dy = pts[i + 1].y - pts[i - 1].y

        angulo = math.degrees(math.atan2(dy, dx))
        angulos.append(angulo)

    return angulos


def calcular_spline_catmull_rom(
    pontos: Sequence[Union[Tuple[float, float], Ponto2D, Dict[str, Any]]],
    alfa: float = 0.5
) -> Dict[str, Any]:
    """
    Executa o cálculo integrado completo da spline para uma lista de pontos.
    Retorna um dicionário com caminho_svg, caixa_delimitadora, segmentos_bezier e angulos_tangentes.
    """
    pts = sanitizar_pontos(pontos)
    segmentos = converter_pontos_para_bezier(pts, alfa=alfa)
    caminho_svg = gerar_caminho_svg(pts, alfa=alfa)
    cx, cy, comp, larg = calcular_caixa_delimitadora(pts)
    angulos = calcular_angulos_tangentes(pts)

    return {
        "caminho_svg": caminho_svg,
        "caixa_delimitadora": {
            "x": cx,
            "y": cy,
            "comprimento": comp,
            "largura": larg
        },
        "segmentos_bezier": segmentos,
        "angulos_tangentes": angulos
    }
