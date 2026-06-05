# Copyright (C) 2026 ARESTA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import argparse
from pathlib import Path
from PIL import Image

def comprimir_imagem(caminho_imagem, quality=85, max_dim=2048):
    """Redimensiona e comprime uma imagem WebP se necessário (apenas se exceder max_dim)."""
    try:
        with Image.open(caminho_imagem) as img:
            # Se a imagem já estiver dentro do limite, não faz nada
            if max(img.size) <= max_dim:
                return False
                
            size_original = os.path.getsize(caminho_imagem)
            
            # Redimensionar
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            # Salvar temporariamente
            temp_path = caminho_imagem.with_suffix('.tmp.webp')
            img.save(temp_path, "WEBP", quality=quality)
            
            size_novo = os.path.getsize(temp_path)
            
            # Substitui o arquivo original
            os.replace(temp_path, caminho_imagem)
            print(f"  Otimizada: {caminho_imagem.name} ({size_original/1024:.1f}KB -> {size_novo/1024:.1f}KB)")
            return True
    except Exception as e:
        print(f"  Erro ao processar {caminho_imagem}: {e}")
        return False

def processar_diretorio(diretorio, quality, max_dim, recursivo):
    """Percorre o diretório buscando por arquivos .webp para otimizar."""
    arquivos = []
    if recursivo:
        # Busca recursiva ignorando 'raw_pdf_contents'
        for root, dirs, files in os.walk(diretorio):
            if 'raw_pdf_contents' in dirs:
                dirs.remove('raw_pdf_contents') # Não desce nessa pasta
            
            # Opcionalmente: foque apenas em pastas chamadas 'imagens'
            # if Path(root).name != 'imagens':
            #    continue

            for f in files:
                if f.endswith('.webp') and not f.endswith('.tmp.webp'):
                    arquivos.append(Path(root) / f)
    else:
        arquivos = [p for p in Path(diretorio).glob("*.webp") if not p.name.endswith('.tmp.webp')]
    
    if not arquivos:
        print(f"Nenhum arquivo WebP encontrado em {diretorio}")
        return

    print(f"Processando {len(arquivos)} arquivos em {diretorio}...")
    otimizados = 0
    for path in arquivos:
        if comprimir_imagem(path, quality, max_dim):
            otimizados += 1
            
    print(f"\nConcluído! {otimizados} arquivos foram redimensionados/otimizados.")

def main():
    parser = argparse.ArgumentParser(description="Utilitário para otimização em lote de imagens WebP no banco de dados.")
    parser.add_argument("path", help="Caminho para o arquivo ou diretório a ser processado.")
    parser.add_argument("--quality", type=int, default=85, help="Qualidade WebP (padrão: 85).")
    parser.add_argument("--max-dim", type=int, default=2048, help="Dimensão máxima do lado maior (padrão: 2048).")
    parser.add_argument("--recursivo", action="store_true", help="Processar subdiretórios.")
    
    args = parser.parse_args()
    
    input_path = Path(args.path)
    
    if input_path.is_file():
        comprimir_imagem(input_path, args.quality, args.max_dim)
    elif input_path.is_dir():
        processar_diretorio(input_path, args.quality, args.max_dim, args.recursivo)
    else:
        print(f"Erro: Caminho inválido: {input_path}")

if __name__ == "__main__":
    main()
