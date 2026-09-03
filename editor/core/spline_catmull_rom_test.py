# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import math
import pytest
from editor.core.spline_catmull_rom import (
    Ponto2D,
    SegmentoBezierCubica,
    calcular_spline_catmull_rom,
    converter_pontos_para_bezier,
    gerar_caminho_svg,
    calcular_caixa_delimitadora,
    calcular_angulos_tangentes,
    sanitizar_pontos
)


class TestSplineCatmullRom:
    def test_sanitizar_pontos_vazio_e_unitario(self):
        assert sanitizar_pontos([]) == []
        assert sanitizar_pontos([(10, 20)]) == [Ponto2D(10.0, 20.0)]

    def test_sanitizar_pontos_com_dicionarios_e_objetos_invalidos(self):
        entrada = [
            {"x": 10, "y": 20},
            {"x": 10, "y": 20},  # duplicado
            Ponto2D(30.0, 40.0),
            "invalido",
            None,
            [50, 60]
        ]
        pts = sanitizar_pontos(entrada)
        assert len(pts) == 3
        assert pts[0] == Ponto2D(10.0, 20.0)
        assert pts[1] == Ponto2D(30.0, 40.0)
        assert pts[2] == Ponto2D(50.0, 60.0)

    def test_sanitizar_pontos_remove_duplicatas_consecutivas(self):
        pontos = [(10, 10), (10, 10), (20, 20), (20, 20.2), (50, 50)]
        resultado = sanitizar_pontos(pontos, tolerancia=0.5)
        assert len(resultado) == 3
        assert resultado[0] == Ponto2D(10.0, 10.0)
        assert resultado[1] == Ponto2D(20.0, 20.0)
        assert resultado[2] == Ponto2D(50.0, 50.0)

    def test_conversao_pontos_insuficientes(self):
        assert converter_pontos_para_bezier([]) == []
        assert converter_pontos_para_bezier([(10, 20)]) == []

    def test_conversao_dois_pontos_reta(self):
        pontos = [Ponto2D(0.0, 0.0), Ponto2D(100.0, 0.0)]
        segmentos = converter_pontos_para_bezier(pontos)
        assert len(segmentos) == 1
        seg = segmentos[0]
        assert seg.p0 == Ponto2D(0.0, 0.0)
        assert seg.p3 == Ponto2D(100.0, 0.0)
        assert math.isclose(seg.c1.y, 0.0, abs_tol=1e-3)
        assert math.isclose(seg.c2.y, 0.0, abs_tol=1e-3)
        assert seg.c1.x > seg.p0.x
        assert seg.c2.x > seg.c1.x

    def test_conversao_multiplos_pontos_suavizados(self):
        pontos = [
            Ponto2D(100.0, 800.0),
            Ponto2D(120.0, 600.0),
            Ponto2D(150.0, 400.0),
            Ponto2D(130.0, 200.0)
        ]
        segmentos = converter_pontos_para_bezier(pontos)
        assert len(segmentos) == 3
        for i, seg in enumerate(segmentos):
            assert seg.p0 == pontos[i]
            assert seg.p3 == pontos[i + 1]

    def test_gerar_caminho_svg(self):
        pontos = [(100, 800), (120, 600), (150, 400)]
        caminho_svg = gerar_caminho_svg(pontos)
        assert caminho_svg.startswith("M 100 800")
        assert " C " in caminho_svg

    def test_gerar_caminho_svg_casos_borda(self):
        assert gerar_caminho_svg([]) == ""
        assert gerar_caminho_svg([(50, 60)]) == "M 50 60"

    def test_calcular_caixa_delimitadora(self):
        pontos = [(100, 200), (300, 600), (200, 400)]
        cx, cy, comp, larg = calcular_caixa_delimitadora(pontos)
        assert comp == 200 # 300 - 100
        assert larg == 400 # 600 - 200
        assert cx == 200
        assert cy == 400

    def test_calcular_caixa_delimitadora_vazia(self):
        cx, cy, comp, larg = calcular_caixa_delimitadora([])
        assert (cx, cy, comp, larg) == (0, 0, 0, 0)

    def test_calcular_angulos_tangentes(self):
        assert calcular_angulos_tangentes([]) == []
        assert calcular_angulos_tangentes([(10, 20)]) == [0.0]

        pontos = [(0, 0), (100, 0), (100, 100)]
        angulos = calcular_angulos_tangentes(pontos)
        assert len(angulos) == 3
        assert math.isclose(angulos[0], 0.0, abs_tol=1e-1)
        assert math.isclose(angulos[2], 90.0, abs_tol=1e-1)
        assert 30.0 <= angulos[1] <= 60.0

    def test_calcular_spline_catmull_rom_integrado(self):
        pontos = [(100, 800), (150, 500), (120, 200)]
        resultado = calcular_spline_catmull_rom(pontos)
        assert "caminho_svg" in resultado
        assert "caixa_delimitadora" in resultado
        assert "segmentos_bezier" in resultado
        assert "angulos_tangentes" in resultado
        assert len(resultado["segmentos_bezier"]) == 2
        assert len(resultado["angulos_tangentes"]) == 3
