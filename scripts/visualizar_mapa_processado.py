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

import json
import os
import argparse
from PIL import Image, ImageDraw

def processar_mapa(caminho_imagem, caminho_json):
    # Determinar caminho de saída: mesma pasta do json, com sufixo _processado.webp
    diretorio_json = os.path.dirname(caminho_json)
    base_nome_json = os.path.splitext(os.path.basename(caminho_json))[0]
    
    caminho_saida = os.path.join(diretorio_json, f"{base_nome_json}_processado.webp")

    if not os.path.exists(caminho_imagem):
        print(f"Erro: Imagem {caminho_imagem} não encontrada.")
        return

    if not os.path.exists(caminho_json):
        print(f"Erro: JSON {caminho_json} não encontrado.")
        return

    # Carregar JSON
    with open(caminho_json, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    # Abrir Imagem
    with Image.open(caminho_imagem) as img:
        img = img.convert('RGB')
        
        # Obter dimensões do mapa para o crop
        dim_mapa = dados.get('dimensoes_mapa', {})
        canto = dim_mapa.get('canto_superior_esquerdo', {'x': 0, 'y': 0})
        map_x = canto.get('x', 0)
        map_y = canto.get('y', 0)
        map_w = dim_mapa.get('largura', img.width)
        map_h = dim_mapa.get('altura', img.height)

        # Realizar o recorte (crop)
        img_recortada = img.crop((map_x, map_y, map_x + map_w, map_y + map_h))
        
        draw = ImageDraw.Draw(img_recortada)
        tamanho_marcador = 10

        pontos = dados.get('pontos_de_interesse', [])
        for ponto in pontos:
            # As coordenadas já são relativas ao canto superior esquerdo do mapa
            if 'circular' in ponto:
                circ = ponto['circular']
                x, y, r = circ['x'], circ['y'], circ['raio']
                draw.ellipse([x - r, y - r, x + r, y + r], outline="red", width=3)
            
            elif 'box' in ponto:
                box = ponto['box']
                x, y = box['x'], box['y']
                w, h = box['comprimento'], box['largura']
                angulo = box.get('angulo_graus_x100', 0) / 100.0 # Convert from scaled integer if needed
                
                # Definir os 4 pontos do retângulo original
                p1 = (x, y)
                p2 = (x + w, y)
                p3 = (x + w, y + h)
                p4 = (x, y + h)
                
                if angulo != 0:
                    import math
                    # Centro da rotação (canto superior esquerdo no proto, mas vamos seguir o que o user definiu)
                    # O proto diz: "Definido pela posição do canto superior esquerdo, comprimento e largura."
                    # "Opcionalmente aceita um ângulo para especificar a box de maneira angulada."
                    # Geralmente a rotação é em volta do ponto (x,y).
                    rad = math.radians(angulo)
                    def rotate_point(px, py, cx, cy, angle_rad):
                        dx = px - cx
                        dy = py - cy
                        nx = cx + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
                        ny = cy + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
                        return (nx, ny)
                    
                    p2 = rotate_point(p2[0], p2[1], x, y, rad)
                    p3 = rotate_point(p3[0], p3[1], x, y, rad)
                    p4 = rotate_point(p4[0], p4[1], x, y, rad)
                
                draw.polygon([p1, p2, p3, p4], outline="red", width=3)

            elif 'area_livre' in ponto:
                coords = ponto['area_livre'].get('coordenadas', [])
                if len(coords) >= 4:
                    # coords is [x1, y1, x2, y2, ...]
                    pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                    draw.polygon(pts, outline="red", width=3)

        # Salvar resultado
        img_recortada.save(caminho_saida, "WEBP")
        print(f"Imagem marcada salva com sucesso em: {caminho_saida}")

def main():
    parser = argparse.ArgumentParser(description="Visualizar pontos de interesse em um mapa recortado.")
    parser.add_argument("--imagem", required=True, help="Caminho para o arquivo de imagem do mapa.")
    parser.add_argument("--pontos_json", required=True, help="Caminho para o arquivo JSON com os pontos de interesse.")
    
    args = parser.parse_args()

    processar_mapa(args.imagem, args.pontos_json)

if __name__ == "__main__":
    main()
