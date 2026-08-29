# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Módulo para conversão, formatação e validação das geometrias de pontos de interesse (POIs).

Este módulo segue o princípio "Library-First", permitindo que o processamento
da representação JSON/Dict das geometrias (`circulo`, `retangulo`, `quadrado`, `poligono`)
seja isolado e testado independentemente do sistema de UI (PyQt).
"""

from typing import Any


class GeometriaPOI:
    """
    Representa a geometria de um Ponto de Interesse (POI).
    Fornece métodos utilitários para construir a geometria a partir de um dicionário,
    suportando retrocompatibilidade com chaves antigas (`circular`, `box`, `area_livre`).
    """
    
    def __init__(self, tipo: str, propriedades: dict[str, Any], id_poi: str = "", label: str = "") -> None:
        """
        Inicializa a geometria.
        
        Args:
            tipo: O tipo de geometria ('circulo', 'retangulo', 'quadrado', 'poligono').
            propriedades: As propriedades internas (x, y, raio, comprimento, largura, etc).
            id_poi: Identificador referencial do POI.
            label: O rótulo exibido no mapa.
        """
        self.tipo: str = tipo
        self.propriedades: dict[str, Any] = propriedades
        self.id_poi: str = id_poi
        self.label: str = label

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
        
        if "circulo" in dados:
            return cls("circulo", dados["circulo"], id_poi, label)
        elif "retangulo" in dados:
            return cls("retangulo", dados["retangulo"], id_poi, label)
        elif "quadrado" in dados:
            return cls("quadrado", dados["quadrado"], id_poi, label)
        elif "poligono" in dados:
            return cls("poligono", dados["poligono"], id_poi, label)
        
        # Fallbacks legados
        elif "circular" in dados:
            return cls("circulo", dados["circular"], id_poi, label)
        elif "box" in dados:
            return cls("retangulo", dados["box"], id_poi, label)
        elif "area_livre" in dados:
            return cls("poligono", dados["area_livre"], id_poi, label)
            
        raise ValueError("O dicionário não contém um tipo de geometria de POI válido ou reconhecido.")

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
    def coordenadas(self) -> list[Any] | None:
        val = self.propriedades.get("coordenadas")
        return list(val) if val is not None else None

