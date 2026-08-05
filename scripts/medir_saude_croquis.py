# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

# Copyright (C) 2026 ARESTA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
import sys

# Adiciona o diretório raiz do projeto ao sys.path para importar a lib utilitária
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.preparar_submissao_lib import parse_md_com_frontmatter

def check_partes_json(croqui_path: Path) -> bool:
    """Verifica se partes.json existe e é um JSON válido."""
    partes_path = croqui_path / "partes.json"
    if not partes_path.exists():
        return False
    try:
        with open(partes_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return bool(data) # Deve ser um JSON preenchido
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False

def check_raw_original_pdf(croqui_path: Path) -> bool:
    """Verifica se raw_original_pdf existe e não está vazia."""
    pdf_path = croqui_path / "raw_original_pdf"
    return pdf_path.exists() and pdf_path.is_dir() and any(pdf_path.iterdir())

def check_raw_pdf_contents(croqui_path: Path) -> bool:
    """Verifica se raw_pdf_contents existe e não está vazia."""
    contents_path = croqui_path / "raw_pdf_contents"
    return contents_path.exists() and contents_path.is_dir() and any(contents_path.iterdir())

def check_croqui_yaml(croqui_path: Path) -> bool:
    """Verifica se croqui.yaml existe."""
    yaml_path = croqui_path / "croqui.yaml"
    return yaml_path.exists()

def check_caminho_thumbnail(croqui_path: Path) -> bool:
    """Verifica se croqui.yaml possui caminho_thumbnail preenchido."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return False
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return isinstance(data, dict) and bool(data.get("caminho_thumbnail"))
    except Exception:
        return False

def check_mapas_gerais_exists(croqui_path: Path) -> bool:
    """Verifica se mapas_gerais.md existe."""
    return (croqui_path / "mapas_gerais.md").exists()

def check_publicar_croqui(croqui_path: Path) -> bool:
    """Verifica se croqui.yaml possui publicar_croqui: true."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return False
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return isinstance(data, dict) and data.get("publicar_croqui") is True
    except (yaml.YAMLError, UnicodeDecodeError):
        return False

def check_revisado_manualmente(croqui_path: Path) -> bool:
    """Verifica se croqui.yaml possui revisado_manualmente: true."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return False
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return isinstance(data, dict) and data.get("revisado_manualmente") is True
    except (yaml.YAMLError, UnicodeDecodeError):
        return False

def check_revisado_bounding_circle(croqui_path: Path) -> bool:
    """Verifica se croqui.yaml possui revisado_bounding_circle: true."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return False
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return isinstance(data, dict) and data.get("revisado_bounding_circle") is True
    except (yaml.YAMLError, UnicodeDecodeError):
        return False

def check_status_desenho_extraivel(croqui_path: Path) -> str:
    """Verifica o status de desenhos extraíveis no croqui.yaml."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return "❌"
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        status = data.get("status_desenho_extraivel")
        if status == "NAO_TEM_DESENHO":
            return "✅ (não)"
        elif status == "TEM_DESENHO_MAS_NAO_EXTRAIDO":
            return "⚠️"
        elif status == "DESENHO_EXTRAIDO":
            return "✅"
        else:
            return "❌"
    except Exception:
        return "❌"


def check_pico_coordinates(croqui_path: Path) -> str:
    """Verifica se os picos possuem coordenadas geográficas (latitude/longitude)."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return "N/A"
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        picos = data.get("picos", [])
        if not picos:
            return "N/A"
        
        passaram = 0
        total = len(picos)
        for pico in picos:
            loc = pico.get("localizacao")
            if loc and isinstance(loc, dict) and loc.get("latitude") is not None and loc.get("longitude") is not None:
                passaram += 1
        
        if passaram == total:
            return f"✅ ({passaram}/{total})"
        elif passaram > 0:
            return f"⚠️ ({passaram}/{total})"
        else:
            return f"❌ (0/{total})"
    except Exception:
        return "❌ (Erro)"

def find_all_sectors(croqui_path: Path) -> list[Path]:
    """Encontra recursivamente todos os caminhos de setores definidos no croqui.yaml."""
    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return list(croqui_path.glob("setor_*.md"))

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception:
        return list(croqui_path.glob("setor_*.md"))

    sector_paths = []
    
    def collect_recursively(elements):
        for e in elements:
            if not e or not isinstance(e, dict): continue
            tipo = "setor" if "setor" in e else "grupo"
            obj = e.get(tipo)
            if not obj: continue
            
            if isinstance(obj, str):
                p = croqui_path / obj
                if p.suffix == ".md":
                    if p not in sector_paths:
                        sector_paths.append(p)
                continue

            if not isinstance(obj, dict): continue
            
            if "caminho" in obj:
                p = croqui_path / obj["caminho"]
                # Adicionamos .md independentemente de ser setor ou grupo (ambos podem ter mapas)
                if p.suffix == ".md":
                    if p not in sector_paths:
                        sector_paths.append(p)
                
                # Se for um grupo com caminho, precisamos olhar o frontmatter dele para sub-setores
                if tipo == "grupo":
                    try:
                        fm, _ = parse_md_com_frontmatter(p)
                        if fm:
                            filhos = fm.get("setores") or fm.get("sub_setores")
                            if filhos:
                                collect_recursively([{"setor": s} if isinstance(s, (str, dict)) else s for s in filhos])
                    except Exception:
                        pass

            # Caso o conteúdo esteja estruturado diretamente no YAML
            conteudo = obj.get("conteudo")
            if conteudo and isinstance(conteudo, dict):
                sub = conteudo.get("setores") or conteudo.get("sub_setores")
                if sub:
                    collect_recursively([{"setor": s} if isinstance(s, (str, dict)) else s for s in sub if s])
    
    picos = data.get("picos", [])
    if isinstance(picos, list):
        for pico in picos:
            if isinstance(pico, dict) and "setores_ou_grupos" in pico:
                collect_recursively(pico["setores_ou_grupos"])
            
    # Se não encontrou nada via YAML, fallback para glob
    if not sector_paths:
        return sorted(list(croqui_path.glob("setor_*.md")))
        
    return sorted(sector_paths)

def check_pontos_de_interesse(croqui_path: Path) -> str:
    """Verifica pontos de interesse nos arquivos de setor encontrados recursivamente."""
    setores = find_all_sectors(croqui_path)
    if not setores:
        return "N/A"
    
    passaram = 0
    total = len(setores)
    
    for setor_path in setores:
        try:
            if not setor_path.exists():
                continue
            frontmatter, _ = parse_md_com_frontmatter(setor_path)
            if frontmatter and "mapas" in frontmatter:
                tem_ponto = False
                for mapa in frontmatter["mapas"]:
                    if "pontos_de_interesse" in mapa and isinstance(mapa["pontos_de_interesse"], list) and len(mapa["pontos_de_interesse"]) > 0:
                        tem_ponto = True
                        break
                if tem_ponto:
                    passaram += 1
        except Exception:
            continue
                
    if passaram == total and total > 0:
        return f"✅ ({passaram}/{total})"
    elif passaram > 0:
        return f"⚠️ ({passaram}/{total})"
    else:
        return f"❌ (0/{total})"

def generate_report_table(report_data: list[dict]) -> str:
    """Gera a tabela Markdown a partir dos dados do relatório."""
    total_croquis = len(report_data)
    if total_croquis == 0:
        return ""

    a_publicados = sum(1 for d in report_data if d["Publicado"] == "✅")
    a_revisados = sum(1 for d in report_data if d["Revisado Manual"] == "✅")
    a_revisados_circ = sum(1 for d in report_data if d["Revisado Circ"] == "✅")
    a_pontos = sum(1 for d in report_data if "✅" in d["Pontos de Interesse"])
    a_thumbnail = sum(1 for d in report_data if d["Thumbnail"] == "✅")
    a_coord_picos = sum(1 for d in report_data if "✅" in d["Coordenadas Picos"])
    a_mapas_gerais = sum(1 for d in report_data if d["Mapas Gerais"] == "✅")
    a_croqui_yaml = sum(1 for d in report_data if d["croqui.yaml"] == "✅")
    a_raw_pdf_contents = sum(1 for d in report_data if d["Conteúdo PDF"] == "✅")
    a_partes_json = sum(1 for d in report_data if d["partes.json"] == "✅")
    a_raw_original_pdf = sum(1 for d in report_data if d["PDF Original"] == "✅")
    
    c_nao_tem = sum(1 for d in report_data if d["Status Desenho"] == "✅ (não)")
    c_sim_extraido = sum(1 for d in report_data if d["Status Desenho"] == "✅")
    c_sim_mas_nao = sum(1 for d in report_data if d["Status Desenho"] == "⚠️")
    c_unknown = sum(1 for d in report_data if d["Status Desenho"] == "❌")
    a_status_desenho = c_nao_tem + c_sim_extraido

    headers = [
        "Croqui", 
        f"Publicado ({a_publicados}/{total_croquis})",
        f"Revisado Manual ({a_revisados}/{total_croquis})",
        f"Revisado Circ ({a_revisados_circ}/{total_croquis})",
        f"Desenho Extraível ({a_status_desenho}/{c_sim_mas_nao}/{c_unknown})",
        f"Pontos de Interesse ({a_pontos}/{total_croquis})",
        f"Thumbnail ({a_thumbnail}/{total_croquis})",
        f"Coordenadas Picos ({a_coord_picos}/{total_croquis})",
        f"Mapas Gerais ({a_mapas_gerais}/{total_croquis})",
        f"croqui.yaml ({a_croqui_yaml}/{total_croquis})", 
        f"Conteúdo PDF ({a_raw_pdf_contents}/{total_croquis})", 
        f"partes.json ({a_partes_json}/{total_croquis})", 
        f"PDF Original ({a_raw_original_pdf}/{total_croquis})"
    ]
    
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    for data in report_data:
        row = [
            data["Nome"],
            data["Publicado"],
            data["Revisado Manual"],
            data["Revisado Circ"],
            data["Status Desenho"],
            data["Pontos de Interesse"],
            data["Thumbnail"],
            data["Coordenadas Picos"],
            data["Mapas Gerais"],
            data["croqui.yaml"],
            data["Conteúdo PDF"],
            data["partes.json"],
            data["PDF Original"]
        ]
        lines.append("| " + " | ".join(row) + " |")
        
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Mede a saúde dos croquis na base de dados.")
    parser.add_argument("--output", "-o", default="STATUS_CROQUIS.md", help="Arquivo de saída do relatório Markdown.")
    args = parser.parse_args()
    
    root_path = Path(__file__).resolve().parent.parent
    base_path = root_path / "database"
    
    if not base_path.exists():
        print(f"Erro: Pasta database não encontrada em {base_path}")
        return

    report_data = []
    croquis = sorted([d for d in base_path.iterdir() if d.is_dir()])
    for croqui in croquis:
        nome = croqui.name
        publicado = "✅" if check_publicar_croqui(croqui) else "❌"
        revisado = "✅" if check_revisado_manualmente(croqui) else "❌"
        revisado_circ = "✅" if check_revisado_bounding_circle(croqui) else "❌"
        partes = "✅" if check_partes_json(croqui) else "❌"
        raw_pdf = "✅" if check_raw_original_pdf(croqui) else "❌"
        raw_contents = "✅" if check_raw_pdf_contents(croqui) else "❌"
        yaml_present = "✅" if check_croqui_yaml(croqui) else "❌"
        pontos = check_pontos_de_interesse(croqui)
        thumbnail = "✅" if check_caminho_thumbnail(croqui) else "❌"
        coord_picos = check_pico_coordinates(croqui)
        mapas_gerais = "✅" if check_mapas_gerais_exists(croqui) else "❌"
        status_desenho = check_status_desenho_extraivel(croqui)
        
        report_data.append({
            "Nome": nome,
            "Publicado": publicado,
            "Revisado Manual": revisado,
            "Revisado Circ": revisado_circ,
            "Status Desenho": status_desenho,
            "Pontos de Interesse": pontos,
            "Thumbnail": thumbnail,
            "Coordenadas Picos": coord_picos,
            "Mapas Gerais": mapas_gerais,
            "croqui.yaml": yaml_present,
            "Conteúdo PDF": raw_contents,
            "partes.json": partes,
            "PDF Original": raw_pdf
        })
        
    markdown_output = generate_report_table(report_data)
    
    # Define o caminho de saída relativo à raiz do projeto
    output_path = root_path / args.output
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Estado de Saúde dos Croquis\n\n")
        f.write(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write(markdown_output)
        
    print(f"Relatório gerado com sucesso em: {output_path}")

if __name__ == "__main__":
    main()
