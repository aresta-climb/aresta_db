# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any
import os
import re
from pathlib import Path
from PIL import Image
import numpy as np
from paddleocr import PaddleOCR
import json

def extrair() -> None:
    img_dir = Path('database/br_mg_ouro_preto_ouroboulder/raw_original_pdf/original_com_legenda/0.5x')
    if not img_dir.exists():
        print(f'Diretorio nao encontrado: {img_dir}')
        return

    print('Inicializando OCR v5...')
    ocr = PaddleOCR(use_doc_orientation_classify=False, 
                    use_doc_unwarping=False,
                    use_textline_orientation=False, 
                    lang='pt')
    
    def get_num(p: Path) -> int:
        m = re.search(r'\d+', p.name)
        return int(m.group()) if m else 0

    arquivos = list(img_dir.glob('*.jpg'))
    arquivos.sort(key=get_num)

    
    print(f'Total de arquivos para OCR: {len(arquivos)}')
    
    for i, p in enumerate(arquivos):
        json_path = p.with_suffix('.ocr_result.json')
        if json_path.exists():
            print(f'[{i+1}/{len(arquivos)}] Pulando {p.name} (JSON ja existe)')
            continue
            
        print(f'[{i+1}/{len(arquivos)}] Processando {p.name}...')
        img = Image.open(p).convert('RGB')
        img_np = np.array(img)[:, :, ::-1] # BGR
            
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj: Any) -> Any:
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.generic):
                    return obj.item()
                return super().default(obj)

                
        try:
            resultados = ocr.predict(input=[img_np])[0]
            if isinstance(resultados, dict):
                clean_res = {
                    'dt_polys': resultados.get('dt_polys', []),
                    'rec_texts': resultados.get('rec_texts', []),
                    'rec_scores': resultados.get('rec_scores', []),
                }
            else:
                clean_res = resultados
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(clean_res, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        except Exception as e:
            print(f'Erro ao processar {p.name}: {e}')

if __name__ == "__main__":
    extrair()
