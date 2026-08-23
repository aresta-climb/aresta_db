# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

"""
Biblioteca pura para conversão, formatação, validação e interpretação de coordenadas geográficas
no padrão E7 (graus * 10^7) e ponto flutuante.
"""

import re
from typing import Optional, Tuple


def e7_para_graus(valor_e7: int) -> float:
    """Converte um valor inteiro no padrão E7 para graus em ponto flutuante."""
    return valor_e7 / 10_000_000.0


def graus_para_e7(graus: float | int) -> int:
    """Converte um valor em graus para inteiro no padrão E7 com arredondamento."""
    return int(round(float(graus) * 10_000_000))


def formatar_graus(graus: float, casas_decimais: int = 7) -> str:
    """Formata um valor de graus com a quantidade especificada de casas decimais."""
    return f"{graus:.{casas_decimais}f}"


def obter_indicador_cardinal_latitude(graus: float) -> Tuple[str, str]:
    """Retorna a sigla e o nome em português do hemisfério de latitude (S/N)."""
    if graus < 0:
        return ("S", "Sul")
    if graus > 0:
        return ("N", "Norte")
    return ("", "Equador")


def obter_indicador_cardinal_longitude(graus: float) -> Tuple[str, str]:
    """Retorna a sigla e o nome em português do hemisfério de longitude (W/E)."""
    if graus < 0:
        return ("W", "Oeste")
    if graus > 0:
        return ("E", "Leste")
    return ("", "Greenwich")


def formatar_cardinal_latitude(graus: float, casas_decimais: int = 7) -> str:
    """Retorna a formatação textual completa da latitude com rosa dos ventos."""
    sigla, nome = obter_indicador_cardinal_latitude(graus)
    if not sigla:
        return f"{formatar_graus(abs(graus), casas_decimais)}° (Linha do Equador)"
    return f"{formatar_graus(abs(graus), casas_decimais)}° {sigla} ({nome})"


def formatar_cardinal_longitude(graus: float, casas_decimais: int = 7) -> str:
    """Retorna a formatação textual completa da longitude com rosa dos ventos."""
    sigla, nome = obter_indicador_cardinal_longitude(graus)
    if not sigla:
        return f"{formatar_graus(abs(graus), casas_decimais)}° (Meridiano de Greenwich)"
    return f"{formatar_graus(abs(graus), casas_decimais)}° {sigla} ({nome})"


def validar_latitude(graus: float) -> bool:
    """Verifica se o valor de latitude está no intervalo válido de -90.0 a +90.0 graus."""
    return -90.0 <= graus <= 90.0


def validar_longitude(graus: float) -> bool:
    """Verifica se o valor de longitude está no intervalo válido de -180.0 a +180.0 graus."""
    return -180.0 <= graus <= 180.0


def restringir_latitude(graus: float) -> float:
    """Restringe a latitude ao intervalo [-90.0, +90.0]."""
    return max(-90.0, min(90.0, graus))


def restringir_longitude(graus: float) -> float:
    """Restringe a longitude ao intervalo [-180.0, +180.0]."""
    return max(-180.0, min(180.0, graus))


def gerar_url_google_maps(latitude: float, longitude: float) -> str:
    """Gera o link web para visualização do ponto no Google Maps."""
    return f"https://www.google.com/maps?q={formatar_graus(latitude)},{formatar_graus(longitude)}"


def interpretar_coordenada_individual(texto: str) -> Optional[float]:
    """
    Tenta interpretar uma única coordenada a partir de um texto (ex: '-19.898', '19.898S', '43.5W').
    Retorna o valor em ponto flutuante com sinal ou None se inválido.
    """
    if not texto:
        return None
    texto_limpo = texto.strip().replace(",", ".")
    padrao_cardinal = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([NSEWOL])?$", texto_limpo, re.IGNORECASE)
    if not padrao_cardinal:
        return None

    num_str, cardinal = padrao_cardinal.groups()
    val = float(num_str)

    if cardinal:
        card = cardinal.upper()
        if card in ("S", "W", "O"):
            val = -abs(val)
        elif card in ("N", "E", "L"):
            val = abs(val)

    return val


def interpretar_par_coordenadas(texto: str) -> Optional[Tuple[float, float]]:
    """
    Interpreta uma string contendo um par de coordenadas (Latitude, Longitude).
    Suporta diversos formatos:
    - Decimais: "-19.898028, -43.521234" ou "-19,898028; -43,521234"
    - Com cardinais: "19.898028° S, 43.521234° W" ou "43.521234° W, 19.898028° S"
    - DMS (Graus/Minutos/Segundos): '19°53\'52.9"S 43°31\'16.4"W'
    - URLs do Google Maps contendo query 'q=lat,lon' ou '/@lat,lon'
    Retorna (latitude, longitude) ou None se não for possível interpretar.
    """
    if not texto or not isinstance(texto, str):
        return None

    texto = texto.strip()

    # 1. Tenta extrair de URLs do Google Maps
    match_url_query = re.search(r"[?&]q=([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)", texto)
    if match_url_query:
        return float(match_url_query.group(1)), float(match_url_query.group(2))

    match_url_at = re.search(r"/@([+-]?\d+(?:\.\d+)?),([+-]?\d+(?:\.\d+)?)", texto)
    if match_url_at:
        return float(match_url_at.group(1)), float(match_url_at.group(2))

    # 2. Tenta formato DMS: Ex: 19°53'52.9"S 43°31'16.4"W
    padrao_dms = re.findall(r"(\d+)[°\s]+(\d+)[\'\s]+(\d+(?:\.\d+)?)\"?\s*([NSEWOL])", texto, re.IGNORECASE)
    if len(padrao_dms) == 2:
        partes_coords = {}
        for d, m, s, card in padrao_dms:
            grau = float(d) + float(m) / 60.0 + float(s) / 3600.0
            card_up = card.upper()
            if card_up in ("S", "W", "O"):
                grau = -grau
            if card_up in ("N", "S"):
                partes_coords["lat"] = grau
            elif card_up in ("E", "W", "L", "O"):
                partes_coords["lon"] = grau

        if "lat" in partes_coords and "lon" in partes_coords:
            return partes_coords["lat"], partes_coords["lon"]

    # 3. Tenta formato com letras cardinais e graus decimais: Ex: 19.898028° S, 43.521234° W
    padrao_cardinal = re.findall(r"([+-]?\d+(?:[\.,]\d+)?)[°\s]*\s*([NSEWOL])", texto, re.IGNORECASE)
    if len(padrao_cardinal) == 2:
        partes_coords = {}
        for val_str, card in padrao_cardinal:
            val = float(val_str.replace(",", "."))
            card_up = card.upper()
            if card_up in ("S", "W", "O"):
                val = -abs(val)
            elif card_up in ("N", "E", "L"):
                val = abs(val)

            if card_up in ("N", "S"):
                partes_coords["lat"] = val
            elif card_up in ("E", "W", "L", "O"):
                partes_coords["lon"] = val

        if "lat" in partes_coords and "lon" in partes_coords:
            return partes_coords["lat"], partes_coords["lon"]

    # 4. Tenta separadores comuns (vírgula, ponto e vírgula, espaço ou barra)
    # Primeiro substitui vírgulas entre dígitos decimais se houver ponto e vírgula separando
    texto_padronizado = texto
    if ";" in texto_padronizado:
        partes = [p.strip() for p in texto_padronizado.split(";") if p.strip()]
    elif "," in texto_padronizado:
        # Se tem vírgula, verifica se é separador de coordenadas ou separador decimal
        partes_virgula = [p.strip() for p in texto_padronizado.split(",") if p.strip()]
        if len(partes_virgula) == 2:
            partes = partes_virgula
        elif len(partes_virgula) == 4:
            # Exemplo: -19,898028, -43,521234
            partes = [f"{partes_virgula[0]}.{partes_virgula[1]}", f"{partes_virgula[2]}.{partes_virgula[3]}"]
        else:
            partes = [p.strip() for p in re.split(r"\s+", texto_padronizado) if p.strip()]
    else:
        partes = [p.strip() for p in re.split(r"\s+", texto_padronizado) if p.strip()]

    if len(partes) == 2:
        val1 = interpretar_coordenada_individual(partes[0])
        val2 = interpretar_coordenada_individual(partes[1])
        if val1 is not None and val2 is not None:
            # Heurística: se val1 não cabe em latitude [-90, 90] mas cabe em longitude [-180, 180],
            # e val2 cabe em latitude, então val1 é lon e val2 é lat
            if not validar_latitude(val1) and validar_longitude(val1) and validar_latitude(val2):
                return val2, val1
            return val1, val2

    return None
