# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from editor.core.coordenadas import (
    e7_para_graus,
    graus_para_e7,
    formatar_graus,
    obter_indicador_cardinal_latitude,
    obter_indicador_cardinal_longitude,
    formatar_cardinal_latitude,
    formatar_cardinal_longitude,
    validar_latitude,
    validar_longitude,
    restringir_latitude,
    restringir_longitude,
    gerar_url_google_maps,
    interpretar_par_coordenadas,
    interpretar_coordenada_individual,
)


class TestConversaoE7:
    def test_conversao_bidirecional_exata(self):
        lat_float = -19.8980280
        lat_e7 = -198980280
        assert graus_para_e7(lat_float) == lat_e7
        assert e7_para_graus(lat_e7) == pytest.approx(lat_float, abs=1e-7)

        lon_float = -43.5212340
        lon_e7 = -435212340
        assert graus_para_e7(lon_float) == lon_e7
        assert e7_para_graus(lon_e7) == pytest.approx(lon_float, abs=1e-7)

    def test_conversao_com_arredondamento(self):
        # Valida que floats com dízimas são arredondados corretamente
        assert graus_para_e7(-19.89802804) == -198980280
        assert graus_para_e7(-19.89802806) == -198980281

    def test_conversao_zero_e_extremos(self):
        assert graus_para_e7(0.0) == 0
        assert e7_para_graus(0) == 0.0

        assert graus_para_e7(90.0) == 900000000
        assert e7_para_graus(900000000) == 90.0

        assert graus_para_e7(-180.0) == -1800000000
        assert e7_para_graus(-1800000000) == -180.0


class TestFormatacaoECardinais:
    def test_formatar_graus(self):
        assert formatar_graus(-19.898028) == "-19.8980280"
        assert formatar_graus(0.0) == "0.0000000"
        assert formatar_graus(-43.5) == "-43.5000000"

    def test_obter_indicador_cardinal_latitude(self):
        sigla, nome = obter_indicador_cardinal_latitude(-19.898028)
        assert sigla == "S"
        assert nome == "Sul"

        sigla, nome = obter_indicador_cardinal_latitude(12.345)
        assert sigla == "N"
        assert nome == "Norte"

        sigla, nome = obter_indicador_cardinal_latitude(0.0)
        assert sigla == ""
        assert nome == "Equador"

    def test_obter_indicador_cardinal_longitude(self):
        sigla, nome = obter_indicador_cardinal_longitude(-43.521234)
        assert sigla == "W"
        assert nome == "Oeste"

        sigla, nome = obter_indicador_cardinal_longitude(15.678)
        assert sigla == "E"
        assert nome == "Leste"

        sigla, nome = obter_indicador_cardinal_longitude(0.0)
        assert sigla == ""
        assert nome == "Greenwich"

    def test_formatar_cardinal_completo(self):
        assert formatar_cardinal_latitude(-19.898028) == "19.8980280° S (Sul)"
        assert formatar_cardinal_latitude(10.5) == "10.5000000° N (Norte)"
        assert formatar_cardinal_latitude(0.0) == "0.0000000° (Linha do Equador)"

        assert formatar_cardinal_longitude(-43.521234) == "43.5212340° W (Oeste)"
        assert formatar_cardinal_longitude(30.0) == "30.0000000° E (Leste)"
        assert formatar_cardinal_longitude(0.0) == "0.0000000° (Meridiano de Greenwich)"


class TestValidacaoERestricao:
    def test_validar_latitude(self):
        assert validar_latitude(-90.0) is True
        assert validar_latitude(90.0) is True
        assert validar_latitude(-19.898028) is True
        assert validar_latitude(-90.000001) is False
        assert validar_latitude(90.000001) is False

    def test_validar_longitude(self):
        assert validar_longitude(-180.0) is True
        assert validar_longitude(180.0) is True
        assert validar_longitude(-43.521234) is True
        assert validar_longitude(-180.000001) is False
        assert validar_longitude(180.000001) is False

    def test_restringir_latitude(self):
        assert restringir_latitude(-100.0) == -90.0
        assert restringir_latitude(120.0) == 90.0
        assert restringir_latitude(-19.5) == -19.5

    def test_restringir_longitude(self):
        assert restringir_longitude(-200.0) == -180.0
        assert restringir_longitude(195.0) == 180.0
        assert restringir_longitude(-43.5) == -43.5


class TestUrlGoogleMaps:
    def test_gerar_url_google_maps(self):
        url = gerar_url_google_maps(-19.898028, -43.521234)
        assert url == "https://www.google.com/maps?q=-19.8980280,-43.5212340"


class TestParserCoordenadas:
    def test_interpretar_coordenada_individual(self):
        assert interpretar_coordenada_individual("-19.898028") == -19.898028
        assert interpretar_coordenada_individual("-19,898028") == -19.898028
        assert interpretar_coordenada_individual("19.898028 S") == -19.898028
        assert interpretar_coordenada_individual("19.898028S") == -19.898028
        assert interpretar_coordenada_individual("19.898028 N") == 19.898028
        assert interpretar_coordenada_individual("43.521234 W") == -43.521234
        assert interpretar_coordenada_individual("43.521234 O") == -43.521234
        assert interpretar_coordenada_individual("43.521234 E") == 43.521234
        assert interpretar_coordenada_individual("43.521234 L") == 43.521234
        assert interpretar_coordenada_individual("texto invalido") is None

    def test_interpretar_par_decimal_simples(self):
        res = interpretar_par_coordenadas("-19.898028, -43.521234")
        assert res is not None
        lat, lon = res
        assert lat == pytest.approx(-19.898028)
        assert lon == pytest.approx(-43.521234)

    def test_interpretar_par_com_virgulas_decimais(self):
        res = interpretar_par_coordenadas("-19,898028; -43,521234")
        assert res is not None
        lat, lon = res
        assert lat == pytest.approx(-19.898028)
        assert lon == pytest.approx(-43.521234)

    def test_interpretar_par_com_letras_cardinais(self):
        # Ordem Lat, Lon com cardinais
        res = interpretar_par_coordenadas("19.898028° S, 43.521234° W")
        assert res is not None
        lat, lon = res
        assert lat == pytest.approx(-19.898028)
        assert lon == pytest.approx(-43.521234)

        # Ordem invertida Lon, Lat com cardinais (deve detectar corretamente pelos cardinais)
        res_inv = interpretar_par_coordenadas("43.521234° W, 19.898028° S")
        assert res_inv is not None
        lat_inv, lon_inv = res_inv
        assert lat_inv == pytest.approx(-19.898028)
        assert lon_inv == pytest.approx(-43.521234)

        # Notação em português (S / O)
        res_pt = interpretar_par_coordenadas("19.898028 S 43.521234 O")
        assert res_pt is not None
        assert res_pt[0] == pytest.approx(-19.898028)
        assert res_pt[1] == pytest.approx(-43.521234)

    def test_interpretar_par_dms(self):
        res = interpretar_par_coordenadas("19°53'52.9\"S 43°31'16.4\"W")
        assert res is not None
        lat, lon = res
        # 19 + 53/60 + 52.9/3600 = 19.8980277...
        assert lat == pytest.approx(-19.8980277, abs=1e-5)
        # 43 + 31/60 + 16.4/3600 = 43.5212222...
        assert lon == pytest.approx(-43.5212222, abs=1e-5)

    def test_interpretar_url_google_maps(self):
        url = "https://www.google.com/maps/@-19.898028,-43.521234,17z"
        res = interpretar_par_coordenadas(url)
        assert res is not None
        assert res[0] == pytest.approx(-19.898028)
        assert res[1] == pytest.approx(-43.521234)

        url_query = "https://maps.google.com/?q=-19.898028,-43.521234"
        res_q = interpretar_par_coordenadas(url_query)
        assert res_q is not None
        assert res_q[0] == pytest.approx(-19.898028)
        assert res_q[1] == pytest.approx(-43.521234)

    def test_interpretar_invalido_retorna_none(self):
        assert interpretar_par_coordenadas("apenas uma frase qualquer") is None
        assert interpretar_par_coordenadas("123.456") is None  # Apenas um número, não é par
        assert interpretar_par_coordenadas("") is None
        assert interpretar_par_coordenadas(None) is None
        assert interpretar_coordenada_individual("") is None
        assert interpretar_coordenada_individual(None) is None

    def test_interpretar_par_com_virgulas_como_decimal(self):
        # Ex: -19,898028, -43,521234
        res = interpretar_par_coordenadas("-19,898028, -43,521234")
        assert res is not None
        assert res[0] == pytest.approx(-19.898028)
        assert res[1] == pytest.approx(-43.521234)

    def test_interpretar_heuristica_lon_lat_invertidos(self):
        # -122.4194 não é latitude válida (fora de [-90, 90]), mas é longitude válida. 37.7749 é latitude válida.
        res = interpretar_par_coordenadas("-122.4194, 37.7749")
        assert res is not None
        # Deve ter invertido para (lat, lon) = (37.7749, -122.4194)
        assert res[0] == pytest.approx(37.7749)
        assert res[1] == pytest.approx(-122.4194)

    def test_interpretar_cardinais_positivos(self):
        res = interpretar_par_coordenadas("19.898028° N, 43.521234° E")
        assert res is not None
        assert res[0] == pytest.approx(19.898028)
        assert res[1] == pytest.approx(43.521234)

    def test_interpretar_multiplos_espacos_e_partes_invalidas(self):
        assert interpretar_par_coordenadas("10, 20, 30") is None
        assert interpretar_par_coordenadas("10 20 30") is None
        assert interpretar_par_coordenadas("-19.898028   -43.521234") == (-19.898028, -43.521234)
