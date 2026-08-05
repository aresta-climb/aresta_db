# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import glob
import json
import io
import math
from pathlib import Path
from PIL import Image
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True

def scale_value(val, scale):
    if val is None: return None
    return int(round(val * scale))

def process_poi(poi, scale_x, scale_y):
    # Scale points depending on the structure
    if "circular" in poi:
        poi["circular"]["x"] = scale_value(poi["circular"]["x"], scale_x)
        poi["circular"]["y"] = scale_value(poi["circular"]["y"], scale_y)
        if "raio" in poi["circular"]:
            poi["circular"]["raio"] = scale_value(poi["circular"]["raio"], (scale_x+scale_y)/2.0)
            
    if "circulo" in poi:
        poi["circulo"]["x"] = scale_value(poi["circulo"]["x"], scale_x)
        poi["circulo"]["y"] = scale_value(poi["circulo"]["y"], scale_y)
        if "raio" in poi["circulo"]:
            poi["circulo"]["raio"] = scale_value(poi["circulo"]["raio"], (scale_x+scale_y)/2.0)
            
    if "retangulo" in poi:
        poi["retangulo"]["x"] = scale_value(poi["retangulo"]["x"], scale_x)
        poi["retangulo"]["y"] = scale_value(poi["retangulo"]["y"], scale_y)
        if "largura" in poi["retangulo"]:
            poi["retangulo"]["largura"] = scale_value(poi["retangulo"]["largura"], scale_x)
        if "altura" in poi["retangulo"]:
            poi["retangulo"]["altura"] = scale_value(poi["retangulo"]["altura"], scale_y)
            
    if "linha" in poi:
        if "pontos" in poi["linha"]:
            for pt in poi["linha"]["pontos"]:
                pt["x"] = scale_value(pt["x"], scale_x)
                pt["y"] = scale_value(pt["y"], scale_y)
                
    if "poligono" in poi:
        if "pontos" in poi["poligono"]:
            for pt in poi["poligono"]["pontos"]:
                pt["x"] = scale_value(pt["x"], scale_x)
                pt["y"] = scale_value(pt["y"], scale_y)

def main():
    db_path = Path("database/br_mg_ouro_preto_ouroboulder")
    imagens_dir = db_path / "imagens"
    raw_mapas_dir = imagens_dir / "raw_mapas"
    
    # Pre-cache image sizes
    image_sizes = {}
    for img_path in imagens_dir.glob("*.webp"):
        with Image.open(img_path) as img:
            image_sizes[img_path.name] = (img.width, img.height)
            
    # Passo 1: Atualizar JSONs em raw_mapas
    print("Atualizando arquivos JSON em raw_mapas...")
    json_modificados = 0
    for json_path in raw_mapas_dir.glob("*.json"):
        if ".ocr_result" in json_path.name: continue
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        caminho_imagem = data.get("caminho_imagem_mapa", "")
        if not caminho_imagem: continue
        img_name = caminho_imagem.split("/")[-1]
        
        if img_name not in image_sizes:
            continue
            
        new_w, new_h = image_sizes[img_name]
        
        old_w = data.get("dimensoes_imagem", {}).get("largura", 0)
        old_h = data.get("dimensoes_imagem", {}).get("altura", 0)
        
        if old_w == 0 or old_h == 0: continue
        
        # Só redimensiona se houver diferença de mais de 2px
        if abs(old_w - new_w) <= 2 and abs(old_h - new_h) <= 2:
            continue
            
        scale_x = new_w / old_w
        scale_y = new_h / old_h
        
        for poi in data.get("pontos_de_interesse", []):
            process_poi(poi, scale_x, scale_y)
            
        data["dimensoes_imagem"]["largura"] = new_w
        data["dimensoes_imagem"]["altura"] = new_h
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        json_modificados += 1
        
    print(f"{json_modificados} arquivos JSON modificados.")

    # Passo 2: Atualizar os Markdowns
    print("Atualizando arquivos Markdown (.md)...")
    md_modificados = 0
    for md_file in db_path.glob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not content.startswith('---'): continue
        parts = content.split('---', 2)
        if len(parts) < 3: continue
        
        frontmatter_str = parts[1]
        data = yaml.load(frontmatter_str)
        
        if not data or "mapas" not in data: continue
        
        changed = False
        for mapa in data["mapas"]:
            caminho_imagem = mapa.get("caminho_imagem_mapa", "")
            if not caminho_imagem: continue
            
            img_name = caminho_imagem.split("/")[-1]
            if img_name not in image_sizes: continue
            
            new_w, new_h = image_sizes[img_name]
            old_w = mapa.get("largura_mapa", 0)
            old_h = mapa.get("altura_mapa", 0)
            
            if old_w == 0 or old_h == 0: continue
            if abs(old_w - new_w) <= 2 and abs(old_h - new_h) <= 2: continue
            
            scale_x = new_w / old_w
            scale_y = new_h / old_h
            
            mapa["largura_mapa"] = new_w
            mapa["altura_mapa"] = new_h
            
            for poi in mapa.get("pontos_de_interesse", []):
                process_poi(poi, scale_x, scale_y)
                
            changed = True
            
        if changed:
            buf = io.StringIO()
            yaml.dump(data, buf)
            new_frontmatter = buf.getvalue()
            new_content = f"---{new_frontmatter}---{parts[2]}"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            md_modificados += 1
            
    print(f"{md_modificados} arquivos Markdown modificados.")

if __name__ == '__main__':
    main()
