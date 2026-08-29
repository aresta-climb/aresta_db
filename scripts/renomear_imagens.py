# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import shutil
from pathlib import Path

def renomear_imagens() -> None:

    map_file = Path('mapping.json')
    if not map_file.exists():
        print('mapping.json nao encontrado!')
        return
        
    with open(map_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    src_dir = Path('database/br_mg_ouro_preto_ouroboulder/raw_original_pdf/sem_legenda/4x')
    dst_dir = Path('database/br_mg_ouro_preto_ouroboulder/temp_mapas')
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    sucesso = 0
    falhas = 0
    
    for original, target_webp in mapping.items():
        if not target_webp:
            continue
            
        src_file = src_dir / original
        if not src_file.exists():
            print(f'Erro: {original} nao encontrado na pasta de origem.')
            falhas += 1
            continue
            
        # Trocar a ext de webp para png no destino, 
        # pois ainda sera convertido de png para webp depois.
        target_png = target_webp.replace('.webp', '.png')
        dst_file = dst_dir / target_png
        
        shutil.copy2(src_file, dst_file)
        sucesso += 1
        
    print(f'Concluido! {sucesso} imagens copiadas para {dst_dir}')
    if falhas > 0:
        print(f'{falhas} imagens falharam.')

if __name__ == '__main__':
    renomear_imagens()
