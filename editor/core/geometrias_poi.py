# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

"""
Módulo para conversão, formatação e validação das geometrias de pontos de interesse (POIs).

Este módulo segue o princípio "Library-First", permitindo que o processamento
da representação JSON/Dict das geometrias (`circulo`, `retangulo`, `quadrado`, `poligono`)
seja isolado e testado independentemente do sistema de UI (PyQt).
"""

class GeometriaPOI:
    """
    Representa a geometria de um Ponto de Interesse (POI).
    Fornece métodos utilitários para construir a geometria a partir de um dicionário,
    suportando retrocompatibilidade com chaves antigas (`circular`, `box`, `area_livre`).
    """
    
    def __init__(self, tipo: str, propriedades: dict, id_poi: str = "", label: str = ""):
        """
        Inicializa a geometria.
        
        Args:
            tipo: O tipo de geometria ('circulo', 'retangulo', 'quadrado', 'poligono').
            propriedades: As propriedades internas (x, y, raio, comprimento, largura, etc).
            id_poi: Identificador referencial do POI.
            label: O rótulo exibido no mapa.
        """
        self.tipo = tipo
        self.propriedades = propriedades
        self.id_poi = id_poi
        self.label = label

    @classmethod
    def from_dict(cls, dados: dict) -> 'GeometriaPOI':
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
        id_poi = dados.get("id", "")
        label = dados.get("label", "")
        
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

    def to_dict(self) -> dict:
        """
        Serializa a geometria de volta para um dicionário, usando apenas
        os nomes padronizados modernos.
        
        Returns:
            Dicionário serializável do POI.
        """
        d = {}
        if self.id_poi:
            d["id"] = self.id_poi
        if self.label:
            d["label"] = self.label
            
        d[self.tipo] = self.propriedades
        return d

    # Atalhos seguros para leitura de propriedades
    @property
    def x(self):
        return self.propriedades.get("x")
        
    @property
    def y(self):
        return self.propriedades.get("y")
        
    @property
    def raio(self):
        return self.propriedades.get("raio")
        
    @property
    def comprimento(self):
        return self.propriedades.get("comprimento")
        
    @property
    def largura(self):
        return self.propriedades.get("largura")
        
    @property
    def lado(self):
        return self.propriedades.get("lado")
        
    @property
    def coordenadas(self):
        return self.propriedades.get("coordenadas")
