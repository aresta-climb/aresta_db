# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest

from aresta_api.proto.generated import croqui_pb2
from editor.core.geometrias_poi import (
    GeometriaPOI,
    calcular_cor_texto_contraste,
    calcular_tamanho_fonte_poi,
    redimensionar_pois_proporcionalmente,
)


class GeometriasPOITest(unittest.TestCase):
    def test_leitura_circulo(self):
        dados = {
            "id": "01",
            "label": "L1",
            "cor": "#FF0000",
            "circulo": {"x": 10, "y": 20, "raio": 5},
        }
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
                        {"x": 120, "y": 100, "tipo": "TOP_PARADA"},
                    ]
                },
            },
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
        geom_vazia = GeometriaPOI("circulo", {})
        self.assertIsNone(geom_vazia.coordenadas)

    def test_redimensionar_pois_proporcionalmente_todas_geometrias(self):
        poi_circulo = croqui_pb2.Mapa.PontoDeInteresse(uid="c1", rotulo="C1")
        poi_circulo.circulo.x = 100
        poi_circulo.circulo.y = 200
        poi_circulo.circulo.raio = 20

        poi_quadrado = croqui_pb2.Mapa.PontoDeInteresse(uid="q1")
        poi_quadrado.quadrado.x = 50
        poi_quadrado.quadrado.y = 80
        poi_quadrado.quadrado.lado = 10

        poi_retangulo = croqui_pb2.Mapa.PontoDeInteresse(uid="r1")
        poi_retangulo.retangulo.x = 40
        poi_retangulo.retangulo.y = 60
        poi_retangulo.retangulo.comprimento = 30
        poi_retangulo.retangulo.largura = 50
        poi_retangulo.retangulo.angulo_graus_x100 = 4500

        poi_poligono = croqui_pb2.Mapa.PontoDeInteresse(uid="p1")
        poi_poligono.poligono.coordenadas.extend([10, 20, 30, 40, 50, 60])

        poi_linha = croqui_pb2.Mapa.PontoDeInteresse(uid="l1")
        no1 = poi_linha.linha.conteudo.nos.add()
        no1.x = 100
        no1.y = 300
        no2 = poi_linha.linha.conteudo.nos.add()
        no2.x = 200
        no2.y = 400

        resultado = redimensionar_pois_proporcionalmente(
            [poi_circulo, poi_quadrado, poi_retangulo, poi_poligono, poi_linha],
            largura_antiga=1000,
            altura_antiga=1000,
            largura_nova=2000,
            altura_nova=500,
        )

        self.assertEqual(len(resultado), 5)
        # sx = 2.0, sy = 0.5, s_iso = sqrt(2.0 * 0.5) = 1.0
        self.assertEqual(resultado[0].circulo.x, 200)
        self.assertEqual(resultado[0].circulo.y, 100)
        self.assertEqual(resultado[0].circulo.raio, 20)

        self.assertEqual(resultado[1].quadrado.x, 100)
        self.assertEqual(resultado[1].quadrado.y, 40)
        self.assertEqual(resultado[1].quadrado.lado, 10)

        self.assertEqual(resultado[2].retangulo.x, 80)
        self.assertEqual(resultado[2].retangulo.y, 30)
        self.assertEqual(resultado[2].retangulo.comprimento, 60)
        self.assertEqual(resultado[2].retangulo.largura, 25)
        self.assertEqual(resultado[2].retangulo.angulo_graus_x100, 4500)

        self.assertEqual(list(resultado[3].poligono.coordenadas), [20, 10, 60, 20, 100, 30])

        self.assertEqual(resultado[4].linha.conteudo.nos[0].x, 200)
        self.assertEqual(resultado[4].linha.conteudo.nos[0].y, 150)
        self.assertEqual(resultado[4].linha.conteudo.nos[1].x, 400)
        self.assertEqual(resultado[4].linha.conteudo.nos[1].y, 200)
        # Garante que os objetos de entrada não foram mutados in-place
        self.assertEqual(poi_circulo.circulo.x, 100)

    def test_redimensionar_pois_mesma_resolucao_ou_dimensoes_invalidas(self):
        poi = croqui_pb2.Mapa.PontoDeInteresse(uid="c1")
        poi.circulo.x = 100
        poi.circulo.y = 200
        poi.circulo.raio = 20

        mesmo = redimensionar_pois_proporcionalmente([poi], 1000, 800, 1000, 800)
        self.assertEqual(mesmo[0].circulo.x, 100)
        self.assertEqual(mesmo[0].circulo.y, 200)

        invalido = redimensionar_pois_proporcionalmente([poi], 0, 800, 1000, 800)
        self.assertEqual(invalido[0].circulo.x, 100)
        self.assertEqual(invalido[0].circulo.y, 200)

    def test_calcular_tamanho_fonte_poi_manual_sobrescreve_automatico(self):
        pt_manual = {
            "texto_visivel": "132",
            "tamanho_fonte": 24,
            "retangulo": {"x": 10, "y": 20, "comprimento": 14, "largura": 10},
        }
        self.assertEqual(calcular_tamanho_fonte_poi(pt_manual), 24)

    def test_calcular_tamanho_fonte_poi_automatico_por_geometria_e_comprimento_texto(self):
        ret_pequeno = {
            "texto_visivel": "132",
            "retangulo": {"x": 10, "y": 20, "comprimento": 14, "largura": 10},
        }
        ret_grande = {
            "texto_visivel": "132",
            "retangulo": {"x": 10, "y": 20, "comprimento": 60, "largura": 40},
        }
        self.assertLess(
            calcular_tamanho_fonte_poi(ret_pequeno),
            calcular_tamanho_fonte_poi(ret_grande),
        )
        self.assertEqual(calcular_tamanho_fonte_poi(ret_pequeno), 6)
        self.assertEqual(calcular_tamanho_fonte_poi(ret_grande), 26)

        circulo_pequeno = {"texto_visivel": "99", "circulo": {"x": 0, "y": 0, "raio": 8}}
        circulo_grande = {"texto_visivel": "99", "circulo": {"x": 0, "y": 0, "raio": 20}}
        self.assertLess(
            calcular_tamanho_fonte_poi(circulo_pequeno),
            calcular_tamanho_fonte_poi(circulo_grande),
        )

        quadrado_pequeno = {"texto_visivel": "88", "quadrado": {"x": 0, "y": 0, "lado": 14}}
        quadrado_grande = {"texto_visivel": "88", "quadrado": {"x": 0, "y": 0, "lado": 40}}
        self.assertLess(
            calcular_tamanho_fonte_poi(quadrado_pequeno),
            calcular_tamanho_fonte_poi(quadrado_grande),
        )

        poligono = {"texto_visivel": "Setor A", "poligono": {"coordenadas": [0, 0, 50, 0, 50, 50]}}
        self.assertEqual(calcular_tamanho_fonte_poi(poligono), 12)

    def test_redimensionar_pois_proporcionalmente_escala_tamanho_fonte_e_raio_no(self):
        poi_ret = croqui_pb2.Mapa.PontoDeInteresse(
            uid="r1",
            texto_visivel="132",
            tamanho_fonte=10,
        )
        poi_ret.retangulo.x = 50
        poi_ret.retangulo.y = 50
        poi_ret.retangulo.comprimento = 20
        poi_ret.retangulo.largura = 15

        poi_linha = croqui_pb2.Mapa.PontoDeInteresse(uid="l1")
        poi_linha.linha.espessura = 3
        no = poi_linha.linha.conteudo.nos.add()
        no.x = 100
        no.y = 100
        no.tamanho_fonte = 12
        no.raio = 14

        poi_linha_comp = croqui_pb2.Mapa.PontoDeInteresse(uid="l2")
        marcador = poi_linha_comp.linha.compilado.marcadores.add()
        marcador.x = 100
        marcador.y = 100
        marcador.tamanho_fonte = 12
        marcador.raio = 14

        resultado = redimensionar_pois_proporcionalmente(
            [poi_ret, poi_linha, poi_linha_comp],
            largura_antiga=1000,
            altura_antiga=1000,
            largura_nova=2000,
            altura_nova=2000,
        )
        self.assertEqual(resultado[0].tamanho_fonte, 20)
        self.assertEqual(resultado[1].linha.espessura, 6)
        self.assertEqual(resultado[1].linha.conteudo.nos[0].tamanho_fonte, 24)
        self.assertEqual(resultado[1].linha.conteudo.nos[0].raio, 28)
        self.assertEqual(resultado[2].linha.compilado.marcadores[0].x, 200)
        self.assertEqual(resultado[2].linha.compilado.marcadores[0].y, 200)
        self.assertEqual(resultado[2].linha.compilado.marcadores[0].tamanho_fonte, 24)
        self.assertEqual(resultado[2].linha.compilado.marcadores[0].raio, 28)

    def test_calcular_cor_texto_contraste_opaco_e_translucido(self):
        self.assertEqual(calcular_cor_texto_contraste("#000000", preenchido=False), "#000000")
        self.assertEqual(calcular_cor_texto_contraste("#000000", preenchido=True), "#FFFFFF")
        self.assertEqual(calcular_cor_texto_contraste("#212121", preenchido=True), "#FFFFFF")
        self.assertEqual(calcular_cor_texto_contraste("#AA00FF", preenchido=True), "#FFFFFF")
        self.assertEqual(calcular_cor_texto_contraste("#FFD600", preenchido=True), "#000000")
        self.assertEqual(calcular_cor_texto_contraste("#00FF00", preenchido=True), "#000000")
        self.assertEqual(calcular_cor_texto_contraste("", preenchido=True), "#000000")



if __name__ == "__main__":
    unittest.main()
