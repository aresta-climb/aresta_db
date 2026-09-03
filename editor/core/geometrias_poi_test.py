# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from editor.core.geometrias_poi import GeometriaPOI

class GeometriasPOITest(unittest.TestCase):
    def test_leitura_circulo(self):
        dados = {"id": "01", "label": "L1", "cor": "#FF0000", "circulo": {"x": 10, "y": 20, "raio": 5}}
        geom = GeometriaPOI.from_dict(dados)
        self.assertEqual(geom.tipo, "circulo")
        self.assertEqual(geom.x, 10)
        self.assertEqual(geom.y, 20)
        self.assertEqual(geom.raio, 5)
        self.assertEqual(geom.cor, "#FF0000")
        self.assertEqual(geom.nos, [])
        self.assertIsNone(geom.linha)
        self.assertEqual(geom.to_dict(), dados)

    def test_leitura_retangulo(self):
        dados = {"id": "02", "retangulo": {"x": 10, "y": 20, "comprimento": 30, "largura": 40}}
        geom = GeometriaPOI.from_dict(dados)
        self.assertEqual(geom.tipo, "retangulo")
        self.assertEqual(geom.x, 10)
        self.assertEqual(geom.y, 20)
        self.assertEqual(geom.comprimento, 30)
        self.assertEqual(geom.largura, 40)
        self.assertEqual(geom.cor, "")
        self.assertEqual(geom.to_dict(), dados)

    def test_leitura_quadrado(self):
        dados = {"id": "03", "quadrado": {"x": 10, "y": 20, "lado": 15}}
        geom = GeometriaPOI.from_dict(dados)
        self.assertEqual(geom.tipo, "quadrado")
        self.assertEqual(geom.x, 10)
        self.assertEqual(geom.y, 20)
        self.assertEqual(geom.lado, 15)
        self.assertEqual(geom.to_dict(), dados)

    def test_leitura_poligono(self):
        dados = {"id": "04", "poligono": {"coordenadas": [0, 0, 10, 0, 10, 10]}}
        geom = GeometriaPOI.from_dict(dados)
        self.assertEqual(geom.tipo, "poligono")
        self.assertEqual(geom.coordenadas, [0, 0, 10, 0, 10, 10])
        self.assertEqual(geom.to_dict(), dados)

    def test_leitura_linha(self):
        dados = {
            "id": "linha_01",
            "label": "Via Teste",
            "cor": "#FF6D00",
            "linha": {
                "estilo": "TRACEJADO",
                "espessura": 3,
                "conteudo": {
                    "nos": [
                        {"x": 100, "y": 200, "tipo": "CIRCULO_IDENTIFICADOR", "rotulo": "01"},
                        {"x": 120, "y": 100, "tipo": "TOP_PARADA"}
                    ]
                }
            }
        }
        geom = GeometriaPOI.from_dict(dados)
        self.assertEqual(geom.tipo, "linha")
        self.assertEqual(geom.cor, "#FF6D00")
        self.assertEqual(geom.linha["estilo"], "TRACEJADO")
        self.assertEqual(len(geom.nos), 2)
        self.assertEqual(geom.to_dict(), dados)

    def test_fallback_legado_box(self):
        dados_legado = {"id": "02", "box": {"x": 10, "y": 20, "comprimento": 30, "largura": 40}}
        geom = GeometriaPOI.from_dict(dados_legado)
        self.assertEqual(geom.tipo, "retangulo")
        dados_salvos = geom.to_dict()
        self.assertIn("retangulo", dados_salvos)
        self.assertNotIn("box", dados_salvos)

    def test_fallback_legado_circular(self):
        dados_legado = {"id": "01", "circular": {"x": 10, "y": 20, "raio": 5}}
        geom = GeometriaPOI.from_dict(dados_legado)
        self.assertEqual(geom.tipo, "circulo")
        self.assertIn("circulo", geom.to_dict())

    def test_fallback_legado_area_livre(self):
        dados_legado = {"id": "04", "area_livre": {"coordenadas": [0, 0, 10, 10]}}
        geom = GeometriaPOI.from_dict(dados_legado)
        self.assertEqual(geom.tipo, "poligono")
        self.assertIn("poligono", geom.to_dict())

    def test_falha_geometria_invalida(self):
        dados_invalidos = {"id": "99"}
        with self.assertRaises(ValueError):
            GeometriaPOI.from_dict(dados_invalidos)

if __name__ == '__main__':
    unittest.main()
