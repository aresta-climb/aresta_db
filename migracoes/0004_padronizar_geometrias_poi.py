# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

from pathlib import Path
from scripts.finalizar_mapas import parse_md_com_frontmatter, salvar_md_com_frontmatter
from editor.core.geometrias_poi import GeometriaPOI

def migrar(pico_path: Path):
    """
    Migração 0004: Padroniza as geometrias de POIs.
    Converte `box` para `retangulo`, `circular` para `circulo` e `area_livre` para `poligono`.
    Mantém compatibilidade com arquivos markdown existentes através da GeometriaPOI.
    """
    for md_path in pico_path.glob("*.md"):
        if not md_path.is_file():
            continue
            
        try:
            frontmatter, corpo = parse_md_com_frontmatter(md_path)
        except Exception:
            continue
            
        if not frontmatter:
            continue
            
        mapas = frontmatter.get("mapas", [])
        if not mapas or not isinstance(mapas, list):
            continue
            
        mudou = False
        for mapa in mapas:
            if not isinstance(mapa, dict):
                continue
            pois = mapa.get("pontos_de_interesse", [])
            if not pois or not isinstance(pois, list):
                continue
                
            novos_pois = []
            for poi_dict in pois:
                if not isinstance(poi_dict, dict):
                    novos_pois.append(poi_dict)
                    continue
                try:
                    # from_dict converte chaves antigas (box, circular, area_livre) p/ novas
                    geom = GeometriaPOI.from_dict(poi_dict)
                    novo_dict = geom.to_dict()
                    novos_pois.append(novo_dict)
                    
                    if "box" in poi_dict or "circular" in poi_dict or "area_livre" in poi_dict:
                        mudou = True
                except ValueError:
                    novos_pois.append(poi_dict)
                    
            mapa["pontos_de_interesse"] = novos_pois
            
        if mudou:
            salvar_md_com_frontmatter(md_path, frontmatter, corpo)
