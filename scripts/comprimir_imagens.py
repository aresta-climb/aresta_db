# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import os
import argparse
import io
import math
from pathlib import Path
from PIL import Image

def comprimir_imagem_para_bytes(imagem_path_ou_bytes, quality=85, max_area=4194304):
    """
    Redimensiona e comprime uma imagem (WebP) se necessário (apenas se exceder max_area).
    Retorna uma tupla (bytes, largura, altura).
    """
    if isinstance(imagem_path_ou_bytes, bytes):
        img_file = io.BytesIO(imagem_path_ou_bytes)
    else:
        img_file = imagem_path_ou_bytes
        
    with Image.open(img_file) as img:
        # Se img tiver palette e formos converter para WebP, precisamos garantir RGB
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
        
        area = img.width * img.height
        if area > max_area:
            scale = math.sqrt(max_area / area)
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        out_buf = io.BytesIO()
        img.save(out_buf, format="WEBP", quality=quality)
        return out_buf.getvalue(), img.width, img.height


def comprimir_imagem(caminho_imagem, quality=85, max_area=4194304):
    """Redimensiona e comprime uma imagem WebP se necessário no disco."""
    try:
        # Verifica se já está dentro dos limites
        with Image.open(caminho_imagem) as img:
            area = img.width * img.height
            is_webp = img.format == "WEBP"
            if area <= max_area and is_webp:
                return False

        size_original = os.path.getsize(caminho_imagem)
        
        # Obter os bytes comprimidos
        img_bytes, w, h = comprimir_imagem_para_bytes(caminho_imagem, quality, max_area)
        
        temp_path = caminho_imagem.with_suffix('.tmp.webp')
        with open(temp_path, 'wb') as f:
            f.write(img_bytes)
            
        size_novo = os.path.getsize(temp_path)
        
        # Se o original não era webp, mudar a extensão final para .webp
        caminho_final = caminho_imagem.with_suffix('.webp')
        os.replace(temp_path, caminho_final)
        
        # Se mudamos a extensão, apagar o original
        if caminho_final != caminho_imagem:
            try: os.remove(caminho_imagem)
            except: pass
            
        print(f"  Otimizada: {caminho_imagem.name} ({size_original/1024:.1f}KB -> {size_novo/1024:.1f}KB)")
        return True
    except Exception as e:
        print(f"  Erro ao processar {caminho_imagem}: {e}")
        return False

def processar_diretorio(diretorio, quality, max_area, recursivo):
    """Percorre o diretório buscando por arquivos de imagem para otimizar."""
    arquivos = []
    if recursivo:
        # Busca recursiva ignorando 'raw_pdf_contents'
        for root, dirs, files in os.walk(diretorio):
            if 'raw_pdf_contents' in dirs:
                dirs.remove('raw_pdf_contents') # Não desce nessa pasta
            
            for f in files:
                if f.lower().endswith(('.webp', '.png', '.jpg', '.jpeg')) and not f.endswith('.tmp.webp'):
                    arquivos.append(Path(root) / f)
    else:
        for ext in ("*.webp", "*.png", "*.jpg", "*.jpeg"):
            arquivos.extend([p for p in Path(diretorio).glob(ext) if not p.name.endswith('.tmp.webp')])
    
    if not arquivos:
        print(f"Nenhum arquivo WebP encontrado em {diretorio}")
        return

    print(f"Processando {len(arquivos)} arquivos em {diretorio}...")
    otimizados = 0
    for path in arquivos:
        if comprimir_imagem(path, quality, max_area):
            otimizados += 1
            
    print(f"\nConcluído! {otimizados} arquivos foram redimensionados/otimizados.")

def main():
    parser = argparse.ArgumentParser(description="Utilitário para otimização em lote de imagens WebP no banco de dados.")
    parser.add_argument("path", help="Caminho para o arquivo ou diretório a ser processado.")
    parser.add_argument("--quality", type=int, default=85, help="Qualidade WebP (padrão: 85).")
    parser.add_argument("--max-area", type=int, default=4194304, help="Área máxima da imagem (padrão: 4194304).")
    parser.add_argument("--recursivo", action="store_true", help="Processar subdiretórios.")
    
    args = parser.parse_args()
    
    input_path = Path(args.path)
    
    if input_path.is_file():
        comprimir_imagem(input_path, args.quality, args.max_area)
    elif input_path.is_dir():
        processar_diretorio(input_path, args.quality, args.max_area, args.recursivo)
    else:
        print(f"Erro: Caminho inválido: {input_path}")

if __name__ == "__main__":
    main()
