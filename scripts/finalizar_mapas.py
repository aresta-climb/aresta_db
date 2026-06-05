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
import yaml
import re
import argparse
from pathlib import Path
from PIL import Image

def parse_md_com_frontmatter(caminho_arquivo):
    """Lê um arquivo Markdown e separa o YAML Frontmatter do conteúdo."""
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        conteudo = f.read()
    
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", conteudo, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        corpo = match.group(2).strip()
        return frontmatter, corpo
    return None, conteudo.strip()

def salvar_md_com_frontmatter(md_path, frontmatter, corpo):
    """Salva o YAML Frontmatter e o corpo de volta no arquivo markdown."""
    with open(md_path, "w", encoding="utf-8") as f:
        if frontmatter:
            f.write("---\n" + yaml.dump(frontmatter, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n")
        f.write(corpo)

def finalizar_mapas(pico_path):
    pico_path = Path(pico_path)
    if not pico_path.exists() or not pico_path.is_dir():
        print(f"Erro: O diretório '{pico_path}' não foi encontrado.")
        return

    json_dir = pico_path / "imagens" / "raw_mapas"
    if not json_dir.exists():
        print(f"Diretório não existe: {json_dir}.")
        return

    json_files = [f for f in json_dir.glob("*.json") if not f.name.endswith(".ocr_result.json")]
    if not json_files:
        print("Nenhum arquivo JSON para processar.")
        return

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except Exception as e:
            print(f"Erro ao ler {json_file.name}: {e}")
            continue

        md_filename = dados.get("arquivo_md")
        img_relative_path = dados.get("caminho_imagem_mapa")
        if not md_filename or not img_relative_path:
            print(f"Aviso: JSON incompleto {json_file.name} - faltando arquivo_md ou caminho_imagem_mapa.")
            continue

        full_img_path = pico_path / img_relative_path
        full_md_path = pico_path / md_filename

        # 1. Atualizar Metadata no arquivo .md
        if not full_md_path.exists():
            print(f"Erro: Arquivo Markdown de origem não encontrado: {full_md_path}")
            continue

        frontmatter, corpo = parse_md_com_frontmatter(full_md_path)
        if not frontmatter:
            print(f"Erro: Não foi possível carregar frontmatter em {full_md_path}")
            continue

        # Encontrar a entrada correspondente no campo 'mapas'
        mapas = frontmatter.get("mapas", [])
        mapa_alvo = None
        for mapa in mapas:
            if mapa.get("caminho_imagem_mapa") == img_relative_path:
                mapa_alvo = mapa
                break

        if mapa_alvo is not None:
            dim_img = dados.get("dimensoes_imagem", {})
            mapa_alvo["largura_mapa"] = dim_img.get("largura")
            mapa_alvo["altura_mapa"] = dim_img.get("altura")

            # Validar pontos de interesse
            novos_pontos = []
            for pt in dados.get("pontos_de_interesse", []):
                # Se encontrar formato legado, joga erro conforme solicitado
                if 'box' in pt and ('xmin' in pt['box'] or 'ymin' in pt['box']):
                    raise ValueError(f"Erro: Formato legado 'xmin/ymin' detectado no POI '{pt.get('id')}' do mapa {json_file.name}. Por favor migre para o formato de centro (x, y, comprimento, largura).")

                if 'circular' in pt:
                    novos_pontos.append(pt)
                elif 'box' in pt:
                    box = pt['box']
                    if all(k in box for k in ['x', 'y', 'comprimento', 'largura']):
                        # Limpeza de campos legados
                        if 'angulo' in box:
                            if 'angulo_graus_x100' not in box:
                                box['angulo_graus_x100'] = int(round(box['angulo'] * 100))
                            del box['angulo']
                        novos_pontos.append(pt)
                    else:
                        print(f"Aviso: Ponto de interesse '{pt.get('label', pt.get('id', '?'))}' no mapa {img_relative_path} está incompleto e será ignorado.")
                elif 'area_livre' in pt:
                    novos_pontos.append(pt)
                else:
                    print(f"Aviso: Ponto de interesse '{pt.get('label', pt.get('id', '?'))}' no mapa {img_relative_path} tem formato desconhecido e será ignorado.")
            
            mapa_alvo["pontos_de_interesse"] = novos_pontos
            
            salvar_md_com_frontmatter(full_md_path, frontmatter, corpo)
            print(f"Sucesso: Metadata atualizado em {md_filename} para o mapa {img_relative_path}.")
        else:
            print(f"Aviso: O mapa {img_relative_path} não foi encontrado na lista 'mapas' de {md_filename}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lê os JSONs de mapas e atualiza o Markdown de origem.")
    parser.add_argument("pico", help="Pasta do pico que contém a subpasta imagens/raw_mapas/")
    args = parser.parse_args()
    finalizar_mapas(args.pico)
