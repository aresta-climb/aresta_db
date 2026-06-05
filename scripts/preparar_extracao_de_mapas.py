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
import sys
import json
import math
import numpy as np
import yaml
import re
import argparse
import time
from pathlib import Path
from PIL import Image
from paddleocr import PaddleOCR

class PreparadorDeMapas:
    def __init__(self, idioma):
        """
        Inicializa o preparador de mapas e carrega o motor PaddleOCR apenas uma vez.
        """
        print(f"Inicializando motor PaddleOCR v5 (Idioma: {idioma})...")
        start_init = time.time()
        self.ocr_engine = PaddleOCR(use_doc_orientation_classify=False, 
                                     use_doc_unwarping=False,
                                     use_textline_orientation=False, 
                                     lang=idioma)
        end_init = time.time()
        print(f"Motor carregado em {end_init - start_init:.2f} segundos.\n")

    def executar(self, pico_path):
        """
        Executa a extração e preparação de mapas para um diretório de pico.
        """
        pico_path = Path(pico_path)
        if not pico_path.exists() or not pico_path.is_dir():
            print(f"Erro: O diretório '{pico_path}' não foi encontrado.")
            return

        # 1. Encontrar todos os arquivos setor_*.md e grupo_*.md
        md_files = list(pico_path.glob("setor_*.md")) + list(pico_path.glob("grupo_*.md"))
        if not md_files:
            print(f"Nenhum arquivo 'setor_*.md' ou 'grupo_*.md' encontrado em {pico_path}.")
            return

        # Pasta de destino para os JSONs
        output_dir = pico_path / "imagens" / "raw_mapas"
        output_dir.mkdir(parents=True, exist_ok=True)

        imagens_de_mapa = []
        for md_file in md_files:
            imagens_de_mapa += self._processar_arquivo_md(md_file, pico_path, output_dir)

        self._extrair_ocr_das_imagens(imagens_de_mapa, output_dir)

    def _processar_arquivo_md(self, md_file, pico_path, output_dir):
        """
        Processa um arquivo MD (setor ou grupo) e extrai mapas.
        Retorna os caminhos para as imagens de mapa encontradas.
        """
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Erro ao ler {md_file.name}: {e}")
            return []

        # Extrair frontmatter para buscar o campo 'mapas'
        frontmatter = {}
        if content.startswith("---"):
            parts = re.split(r"^---$", content, maxsplit=2, flags=re.MULTILINE)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    print(f"Erro ao processar frontmatter em {md_file.name}: {e}")
                    return []

        mapas = frontmatter.get("mapas", [])
        if not mapas:
            return []

        imagens_de_mapa = []
        for mapa in mapas:
            caminho_img = mapa.get("caminho_imagem_mapa")
            if not caminho_img:
                continue

            full_img_path = pico_path / caminho_img
            if not full_img_path.exists():
                print(f"Aviso: Imagem não encontrada: {full_img_path}")
                continue
            imagens_de_mapa.append(full_img_path)

            # Obter dimensões da imagem
            try:
                with Image.open(full_img_path) as img:
                    largura, altura = img.size
            except Exception as e:
                print(f"Erro ao abrir imagem {full_img_path.name}: {e}")
                continue

            # Criar ou atualizar o JSON individual
            nome_base = full_img_path.stem
            target_json = output_dir / f"{nome_base}.json"

            if target_json.exists():
                print(f"Aviso: O arquivo JSON {target_json.name} já existe. Pulando criação do metadado.")
            else:
                # Estrutura do JSON inicial, preenchendo com pontos já existentes se houver
                pontos_existentes = mapa.get("pontos_de_interesse", [])
                dados = {
                    "arquivo_md": md_file.name,
                    "caminho_imagem_mapa": caminho_img,
                    "dimensoes_imagem": {
                        "largura": largura,
                        "altura": altura
                    },
                    "pontos_de_interesse": pontos_existentes
                }

                try:
                    with open(target_json, "w", encoding="utf-8") as f:
                        json.dump(dados, f, indent=2, ensure_ascii=False)
                    print(f"Criado JSON: {target_json.name} (Fonte: {md_file.name})")
                except Exception as e:
                    print(f"Erro ao salvar JSON {target_json.name}: {e}")
                    continue

        return imagens_de_mapa

    def _extrair_ocr_das_imagens(self, imagens_de_mapa, output_dir):
        """
        Extrai o OCR de imagens usando o motor já inicializado.
        """
        print(f"Processando OCR para {len(imagens_de_mapa)} imagens...")

        image_inputs = []
        for img_path in imagens_de_mapa:
            try:
                img = Image.open(img_path).convert('RGB')
                img_np = np.array(img)[:, :, ::-1] # BGR para PaddleOCR
                image_inputs.append(img_np)
            except Exception as e:
                print(f"Erro ao ler imagem {img_path.name}: {e}")
                return

        start_ocr = time.time()
        resultados = self.ocr_engine.predict(input=image_inputs)
        end_ocr = time.time()
        print(f"OCR finalizado em {end_ocr - start_ocr:.2f} segundos.")

        if len(resultados) != len(imagens_de_mapa):
            print(f"Aviso: O número de resultados ({len(resultados)}) não coincide com o número de imagens ({len(imagens_de_mapa)}).")
            return

        # Salvar resultados
        for img_path, res in zip(imagens_de_mapa, resultados):
            res.save_to_img(output_dir / f"{img_path.stem}.ocr_result.png")

            custom_data = {'ocr_result': []}
            texts = res.get('rec_texts', [])
            boxes = res.get('rec_boxes', [])

            if len(texts) == len(boxes) and len(texts) > 0:
                rec_polys = res.get('rec_polys', [])
                for i, (text, box) in enumerate(zip(texts, boxes)):
                    try:
                        # Priorizar o polígono (4 pontos) se disponível para calcular ângulo
                        poly = rec_polys[i].tolist() if (i < len(rec_polys) and hasattr(rec_polys[i], 'tolist')) else (rec_polys[i] if i < len(rec_polys) else None)
                        
                        box_data = None
                        if poly and len(poly) == 4 and isinstance(poly[0], (list, tuple, np.ndarray)):
                            # Caso de 4 pontos (quadrilátero oblíquo) - MAIS PRECISO
                            p0, p1, p2, p3 = poly
                            cx = (p0[0] + p1[0] + p2[0] + p3[0]) / 4
                            cy = (p0[1] + p1[1] + p2[1] + p3[1]) / 4
                            
                            comprimento = ((p1[0] - p0[0])**2 + (p1[1] - p0[1])**2)**0.5
                            largura = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5
                            
                            angulo_rad = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                            angulo_graus = math.degrees(angulo_rad)
                            
                            box_data = {
                                "x": int(round(cx)),
                                "y": int(round(cy)),
                                "comprimento": int(round(comprimento)),
                                "largura": int(round(largura))
                            }
                            
                            angulo_x100 = int(round(angulo_graus * 100))
                            if angulo_x100 != 0:
                                box_data["angulo_graus_x100"] = angulo_x100
                        else:
                            # Fallback para o bbox achatado
                            bbox = box.tolist() if hasattr(box, 'tolist') else box
                            if len(bbox) == 4:
                                if not isinstance(bbox[0], (list, tuple, np.ndarray)):
                                    xmin, ymin, xmax, ymax = bbox
                                    box_data = {
                                        "x": int(round((xmin + xmax) / 2)),
                                        "y": int(round((ymin + ymax) / 2)),
                                        "comprimento": int(xmax - xmin),
                                        "largura": int(ymax - ymin)
                                    }
                                else:
                                    # Caso extremo: bbox são os 4 pontos
                                    p0, p1, p2, p3 = bbox
                                    cx = (p0[0] + p1[0] + p2[0] + p3[0]) / 4
                                    cy = (p0[1] + p1[1] + p2[1] + p3[1]) / 4
                                    comprimento = ((p1[0] - p0[0])**2 + (p1[1] - p0[1])**2)**0.5
                                    largura = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5
                                    angulo_rad = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                                    angulo_graus = math.degrees(angulo_rad)
                                    box_data = {
                                        "x": int(round(cx)),
                                        "y": int(round(cy)),
                                        "comprimento": int(round(comprimento)),
                                        "largura": int(round(largura))
                                    }
                                    angulo_x100 = int(round(angulo_graus * 100))
                                    if angulo_x100 != 0:
                                        box_data["angulo_graus_x100"] = angulo_x100

                        if box_data:
                            custom_data['ocr_result'].append({
                                "text": text,
                                "box": box_data,
                            })
                    except Exception as e:
                        print(f"Aviso: Erro ao processar detecção '{text}' na imagem {img_path.name}: {e}")
                        continue
            
            custom_filename = output_dir / f"{img_path.stem}.ocr_result.json"
            try:
                with open(custom_filename, "w", encoding="utf-8") as f:
                    json.dump(custom_data, f, ensure_ascii=False, indent=4)
                print(f"JSON de OCR salvo em: {custom_filename.name}")
            except Exception as e:
                print(f"Erro ao salvar OCR JSON: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unifica extração de mapas e criação de JSON inicial.")
    parser.add_argument("pico", help="Pasta do pico dentro de database/")
    parser.add_argument("--idioma", default="pt", help="Idioma para o OCR (default: pt)")
    args = parser.parse_args()

    preparador = PreparadorDeMapas(idioma=args.idioma)
    preparador.executar(args.pico)
