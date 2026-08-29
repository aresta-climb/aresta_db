# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Dict, List, Optional
import json
import re
from pathlib import Path
import yaml

def gerar_mapping_completo() -> None:
    img_dir = Path('database/br_mg_ouro_preto_ouroboulder/raw_original_pdf/original_com_legenda/0.5x')
    json_files = list(img_dir.glob('*.ocr_result.json'))
    
    # Sort files by natural number based on original PNG name
    def extract_num(filename: Path) -> int:
        m = re.search(r'\d+', filename.name)
        return int(m.group()) if m else 0

    sorted_files = sorted(json_files, key=extract_num)

    # 1. Agrupar pranchetas pelo OCR
    grupos: Dict[str, List[str]] = {}

    
    # Generate list of prancheta png names based on sorted jsons
    pranchetas_names = []
    for jf in sorted_files:
        png_name = jf.name.replace('.ocr_result.json', '.png')
        pranchetas_names.append(png_name)
        
        with open(jf, 'r', encoding='utf-8') as f:
            try:
                dados = json.load(f)
            except:
                continue
                
        # Procurar texto 'Bloco:' e 'Setor:' na estrutura do paddleOCR
        bloco = ''
        
        if isinstance(dados, dict) and 'rec_texts' in dados:
            texts = dados.get('rec_texts', [])
            full_text = '  '.join(texts)
            m_bloco = re.search(r'Bloco:?\s*(.*?)(?:\s*Setor|$)', full_text, flags=re.IGNORECASE)
            if m_bloco:
                bloco = m_bloco.group(1).strip()
        
        bloco = bloco.lower().replace('é', 'e').replace('á', 'a').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ã', 'a').replace('õ', 'o').replace('ç', 'c').strip()
        
        if not bloco:
            continue
            
        chave = f'{bloco}'
        if chave not in grupos:
            grupos[chave] = []
        grupos[chave].append(png_name)

    # 2. Ler todos os MDs
    db_path = Path('database/br_mg_ouro_preto_ouroboulder')
    md_files = list(db_path.glob('grupo_*_setor_bloco_*.md'))
    
    mapping_final = {f: '' for f in pranchetas_names} # Iniciar tudo vazio, mantendo ordem!
    
    for md_file in md_files:
        content = md_file.read_text(encoding='utf-8')
        if not content.startswith('---'): continue
        parts = re.split(r'^---$', content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) < 3: continue
        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
        except: continue
        
        nome_bloco = (frontmatter.get('nome') or '').lower().replace('é', 'e').replace('á', 'a').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ã', 'a').replace('õ', 'o').replace('ç', 'c').strip()
        mapas = frontmatter.get('mapas', [])
        
        if not mapas: continue
        
        chave_correspondente = None
        for chave in grupos.keys():
            if nome_bloco in chave or chave in nome_bloco:
                chave_correspondente = chave
                break
                
        if chave_correspondente:
            pranchetas = grupos[chave_correspondente]
            for i, prancheta in enumerate(pranchetas):
                if i < len(mapas):
                    url_mapa = mapas[i].get('caminho_imagem_mapa')
                    if url_mapa:
                        # Map to the corresponding file but in WEBP instead of PNG
                        # Wait, no, we map the Prancheta@4x.png to the target final path (which is WEBP in md, so we keep WEBP filename)
                        filename = Path(url_mapa).name
                        
                        # In the design, mapping maps "Prancheta X@4x.png" -> target.webp
                        # But the json was extracted for 0.5x, the original png name is Prancheta X@4x.png 
                        # actually they might be called Prancheta X@0.5x.png ? 
                        # Let's clean the name and replace 0.5x with 4x so the rename script works correctly later
                        key_name = prancheta.replace('@0.5x-80.jpg', '@4x.png').replace('@0.5x.jpg', '@4x.png')
                        
                        if '@' not in key_name:
                            key_name = key_name.replace('.jpg', '@4x.png')
                            
                        # add it to dict or update
                        if prancheta in mapping_final:
                            del mapping_final[prancheta]
                        mapping_final[key_name] = filename

    # Fix all keys to be 4x instead of 0.5x since the mapping is used to rename 4x files
    fixed_mapping = {}
    for k, v in mapping_final.items():
        fixed_k = k.replace('@0.5x-80', '@4x').replace('.jpg', '.png')
        fixed_mapping[fixed_k] = v

    with open('mapping.json', 'w', encoding='utf-8') as f:
        json.dump(fixed_mapping, f, indent=4, ensure_ascii=False)
        
    print('mapping.json atualizado via arquivos locais .ocr_result.json!')

if __name__ == '__main__':
    gerar_mapping_completo()
