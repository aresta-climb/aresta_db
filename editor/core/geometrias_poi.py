# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Módulo para conversão, formatação e validação das geometrias de pontos de interesse (POIs) e elementos visuais.

Este módulo segue o princípio "Library-First", permitindo que o processamento
da representação JSON/Dict das geometrias (`circulo`, `retangulo`, `quadrado`, `poligono`, `linha`)
e propriedades como `cor` seja isolado e testado independentemente do sistema de UI (PyQt).
"""

import math
from collections.abc import Iterable
from typing import Any

from aresta_api.proto.generated import croqui_pb2


class GeometriaPOI:
    """
    Representa a geometria de um Ponto de Interesse (POI) ou Elemento Visual do mapa.
    Fornece métodos utilitários para construir a geometria a partir de um dicionário,
    suportando retrocompatibilidade com chaves antigas (`circular`, `box`, `area_livre`).
    """

    def __init__(
        self,
        tipo: str,
        propriedades: dict[str, Any],
        id_poi: str = "",
        label: str = "",
        cor: str = "",
    ) -> None:
        """
        Inicializa a geometria.

        Args:
            tipo: O tipo de geometria ('circulo', 'retangulo', 'quadrado', 'poligono', 'linha').
            propriedades: As propriedades internas (x, y, raio, comprimento, largura, linha, etc).
            id_poi: Identificador referencial do POI.
            label: O rótulo exibido no mapa.
            cor: String hexadecimal da cor (ex: "#FF6D00").
        """
        self.tipo: str = tipo
        self.propriedades: dict[str, Any] = propriedades
        self.id_poi: str = id_poi
        self.label: str = label
        self.cor: str = cor

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "GeometriaPOI":
        """
        Lê um dicionário (tipicamente vindo de JSON ou YAML) e retorna
        a instância normalizada de GeometriaPOI. Aplica fallback automático
        para formatos desatualizados.

        Args:
            dados: Dicionário contendo os dados do POI.

        Returns:
            GeometriaPOI configurada com os tipos padronizados.

        Raises:
            ValueError: Se o dicionário não contiver nenhum tipo de geometria suportado.
        """
        id_poi = str(dados.get("id", ""))
        label = str(dados.get("label", ""))
        cor = str(dados.get("cor", ""))

        if "circulo" in dados:
            return cls("circulo", dados["circulo"], id_poi, label, cor)
        elif "retangulo" in dados:
            return cls("retangulo", dados["retangulo"], id_poi, label, cor)
        elif "quadrado" in dados:
            return cls("quadrado", dados["quadrado"], id_poi, label, cor)
        elif "poligono" in dados:
            return cls("poligono", dados["poligono"], id_poi, label, cor)
        elif "linha" in dados:
            return cls("linha", dados["linha"], id_poi, label, cor)

        # Fallbacks legados
        elif "circular" in dados:
            return cls("circulo", dados["circular"], id_poi, label, cor)
        elif "box" in dados:
            return cls("retangulo", dados["box"], id_poi, label, cor)
        elif "area_livre" in dados:
            return cls("poligono", dados["area_livre"], id_poi, label, cor)

        raise ValueError(
            "O dicionário não contém um tipo de geometria de POI válido ou reconhecido."
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Serializa a geometria de volta para um dicionário, usando apenas
        os nomes padronizados modernos.

        Returns:
            Dicionário serializável do POI.
        """
        d: dict[str, Any] = {}
        if self.id_poi:
            d["id"] = self.id_poi
        if self.label:
            d["label"] = self.label
        if self.cor:
            d["cor"] = self.cor

        d[self.tipo] = self.propriedades
        return d

    # Atalhos seguros para leitura de propriedades
    @property
    def x(self) -> float | None:
        val = self.propriedades.get("x")
        return float(val) if val is not None else None

    @property
    def y(self) -> float | None:
        val = self.propriedades.get("y")
        return float(val) if val is not None else None

    @property
    def raio(self) -> float | None:
        val = self.propriedades.get("raio")
        return float(val) if val is not None else None

    @property
    def comprimento(self) -> float | None:
        val = self.propriedades.get("comprimento")
        return float(val) if val is not None else None

    @property
    def largura(self) -> float | None:
        val = self.propriedades.get("largura")
        return float(val) if val is not None else None

    @property
    def lado(self) -> float | None:
        val = self.propriedades.get("lado")
        return float(val) if val is not None else None

    @property
    def coordenadas(self) -> list[int] | None:
        coords = self.propriedades.get("coordenadas")
        if isinstance(coords, list):
            return [int(c) for c in coords]
        return None

    @property
    def linha(self) -> dict[str, Any] | None:
        return self.propriedades if self.tipo == "linha" else None

    @property
    def nos(self) -> list[dict[str, Any]]:
        if self.tipo == "linha":
            conteudo = self.propriedades.get("conteudo")
            if isinstance(conteudo, dict):
                nos = conteudo.get("nos")
                if isinstance(nos, list):
                    return [n for n in nos if isinstance(n, dict)]
        return []


def redimensionar_pois_proporcionalmente(
    pontos_de_interesse: Iterable[croqui_pb2.Mapa.PontoDeInteresse],
    largura_antiga: int,
    altura_antiga: int,
    largura_nova: int,
    altura_nova: int,
) -> list[croqui_pb2.Mapa.PontoDeInteresse]:
    """
    Reescala proporcionalmente as coordenadas e dimensões de uma coleção de
    mensagens `Mapa.PontoDeInteresse` da resolução `(largura_antiga, altura_antiga)`
    para `(largura_nova, altura_nova)`.

    Retorna uma nova lista de mensagens `PontoDeInteresse` sem mutar as entradas.
    """
    copias: list[croqui_pb2.Mapa.PontoDeInteresse] = []
    for poi in pontos_de_interesse:
        copia = croqui_pb2.Mapa.PontoDeInteresse()
        copia.CopyFrom(poi)
        copias.append(copia)

    if (
        largura_antiga <= 0
        or altura_antiga <= 0
        or largura_nova <= 0
        or altura_nova <= 0
        or (largura_antiga == largura_nova and altura_antiga == altura_nova)
    ):
        return copias

    sx = largura_nova / largura_antiga
    sy = altura_nova / altura_antiga
    s_iso = math.sqrt(sx * sy)

    for poi_novo in copias:
        tipo = poi_novo.WhichOneof("tipo_area")
        if tipo == "circulo":
            poi_novo.circulo.x = round(poi_novo.circulo.x * sx)
            poi_novo.circulo.y = round(poi_novo.circulo.y * sy)
            poi_novo.circulo.raio = max(1, round(poi_novo.circulo.raio * s_iso))
        elif tipo == "quadrado":
            poi_novo.quadrado.x = round(poi_novo.quadrado.x * sx)
            poi_novo.quadrado.y = round(poi_novo.quadrado.y * sy)
            poi_novo.quadrado.lado = max(1, round(poi_novo.quadrado.lado * s_iso))
        elif tipo == "retangulo":
            poi_novo.retangulo.x = round(poi_novo.retangulo.x * sx)
            poi_novo.retangulo.y = round(poi_novo.retangulo.y * sy)
            poi_novo.retangulo.comprimento = max(1, round(poi_novo.retangulo.comprimento * sx))
            poi_novo.retangulo.largura = max(1, round(poi_novo.retangulo.largura * sy))
        elif tipo == "poligono":
            coords_originais = list(poi_novo.poligono.coordenadas)
            coords_novas = [
                round(val * sx) if idx % 2 == 0 else round(val * sy)
                for idx, val in enumerate(coords_originais)
            ]
            del poi_novo.poligono.coordenadas[:]
            poi_novo.poligono.coordenadas.extend(coords_novas)
        elif tipo == "linha":
            for no in poi_novo.linha.conteudo.nos:
                no.x = round(no.x * sx)
                no.y = round(no.y * sy)

    return copias
