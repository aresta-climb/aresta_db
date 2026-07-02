import json
from pathlib import Path
import shutil
from PIL import Image
import sys
import argparse

def rects_overlap(r1, r2):
    return not (r1[2] < r2[0] or r1[0] > r2[2] or r1[3] < r2[1] or r1[1] > r2[3])

def union_rect(r1, r2):
    return [min(r1[0], r2[0]), min(r1[1], r2[1]), max(r1[2], r2[2]), max(r1[3], r2[3])]

def limpar_imagem(json_path, img_path, raw_path, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        d = json.load(f)
        
    img_w = d.get('width', 1)
    img_h = d.get('height', 1)
    img_area = img_w * img_h
    
    mask_rects = []
    
    # 1. Identificar fundos de legenda (retângulos preenchidos grandes)
    for des in d.get('desenhos', []):
        rect = des.get('rect')
        if not rect: continue
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        area = w * h
        # Se a área for entre 1% e 90% da imagem e for um retângulo preenchido
        if 0.01 * img_area < area < 0.9 * img_area and des.get('type') == 'f':
            mask_rects.append(rect)
            
    # 2. Identificar textos de legenda (textos longos)
    for t in d.get('texto', []):
        text_content = ''
        bbox = t.get('bbox')
        if not bbox: continue
        for line in t.get('lines', []):
            for span in line.get('spans', []):
                text_content += span.get('text', '')
        # Textos de marcadores (POIs) têm 1 a 3 caracteres no máximo (ex: '1', '2', 'P1')
        # Qualquer texto com mais de 3 caracteres é legenda.
        if len(text_content.strip()) > 3:
            mask_rects.append(bbox)
            
    if not mask_rects:
        # Se não há o que limpar, apenas copia a imagem
        if img_path != output_path:
            shutil.copy2(img_path, output_path)
        return False
        
    # Agrupar retângulos que se sobrepõem
    merged = []
    for r in mask_rects:
        matched = False
        for i, mr in enumerate(merged):
            if rects_overlap(r, mr):
                merged[i] = union_rect(r, mr)
                matched = True
                break
        if not matched:
            merged.append(r)
            
    # Refinar o merge
    for _ in range(3):
        new_merged = []
        for r in merged:
            matched = False
            for i, mr in enumerate(new_merged):
                if rects_overlap(r, mr):
                    new_merged[i] = union_rect(r, mr)
                    matched = True
                    break
            if not matched:
                new_merged.append(r)
        merged = new_merged
        
    # Aplicar a máscara
    with Image.open(img_path) as im, Image.open(raw_path) as raw:
        im = im.convert('RGBA')
        raw = raw.convert('RGBA')
        
        # Se os tamanhos não baterem perfeitamente, redimensiona a raw (Pode ocorrer em mosaicos)
        if im.size != raw.size:
            raw = raw.resize(im.size, Image.Resampling.LANCZOS)
            
        for r in merged:
            # Arredondar e dar uma margem de segurança de 5 pixels para não deixar bordas residuais
            box = (int(r[0])-5, int(r[1])-5, int(r[2])+5, int(r[3])+5)
            # Garantir que a caixa não ultrapasse os limites da imagem
            box = (max(0, box[0]), max(0, box[1]), min(im.width, box[2]), min(im.height, box[3]))
            
            cropped = raw.crop(box)
            im.paste(cropped, box)
            
        # Salva a imagem corrigida
        im.save(output_path, 'WEBP', quality=85)
        
    return True

def limpar_todas_imagens(db_folder):
    db_folder = Path(db_folder)
    raw_pdf_contents = db_folder / 'raw_pdf_contents'
    imagens_dir = raw_pdf_contents / 'imagens'
    raw_imagens_dir = raw_pdf_contents / 'raw_imagens'
    
    if not imagens_dir.exists() or not raw_imagens_dir.exists():
        print(f"Erro: As pastas 'imagens' e/ou 'raw_imagens' não foram encontradas em {raw_pdf_contents}.")
        print("Execute 'repartir_pdf.py' primeiro para gerar essas pastas.")
        return
        
    total_imagens = 0
    imagens_limpas = 0
    
    # Iterar por todas as imagens processadas (pX_iY.webp)
    for part_dir in imagens_dir.iterdir():
        if not part_dir.is_dir(): continue
        
        part_name = part_dir.name
        
        for img_path in part_dir.glob('*.webp'):
            if 'raw' in img_path.name: continue
            
            json_path = img_path.with_suffix('.json')
            if not json_path.exists(): continue
            
            # Localizar a raw correspondente
            raw_path = raw_imagens_dir / part_name / f"raw_{img_path.stem}_0.webp"
            if not raw_path.exists():
                print(f"Aviso: Imagem raw não encontrada para {img_path.name}. Pulando...")
                continue
                
            total_imagens += 1
            limpou = limpar_imagem(json_path, img_path, raw_path, img_path)
            
            if limpou:
                print(f"Limpa: {part_name}/{img_path.name}")
                imagens_limpas += 1
                    
    print(f"\nFinalizado! {imagens_limpas} de {total_imagens} imagens foram limpas de legendas e artefatos.")

def main():
    parser = argparse.ArgumentParser(
        description="Remove legendas, caixas de texto e artefatos indesejados das imagens geradas pelo repartir_pdf.py, preservando as rotas e marcadores de POIs."
    )
    
    parser.add_argument("db_folder", help="Pasta do croqui no database (ex: database/br_mg_ouro_preto_ouroboulder)")
    args = parser.parse_args()
    
    limpar_todas_imagens(args.db_folder)

if __name__ == "__main__":
    main()
