# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import yaml
import json
from pathlib import Path
import sys
import io

# Força o uso de UTF-8 para stdout, especialmente importante no Windows
# Em executáveis --windowed do PyInstaller, sys.stdout e sys.stderr podem ser None.
if sys.stdout is not None and getattr(sys.stdout, 'encoding', None) != 'utf-8':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

if sys.stderr is not None and getattr(sys.stderr, 'encoding', None) != 'utf-8':
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def render_dict(d, indent=""):
    lines = []
    if not isinstance(d, dict):
        return lines
        
    # Order prioritary keys to be printed first
    keys = list(d.keys())
    for prioritary in ["nome", "titulo", "id", "descricao"]:
        if prioritary in keys:
            keys.remove(prioritary)
            keys.insert(0, prioritary)

    for k in keys:
        v = d[k]
        if v is None:
            continue
        if isinstance(v, dict):
            lines.append(f"{indent}- **{k}**:")
            lines.extend(render_dict(v, indent + "  "))
        elif isinstance(v, list):
            if len(v) == 0:
                lines.append(f"{indent}- **{k}**: []")
            else:
                lines.append(f"{indent}- **{k}**:")
                for idx, item in enumerate(v):
                    if isinstance(item, dict):
                        lines.append(f"{indent}  - **[{idx}]**:")
                        lines.extend(render_dict(item, indent + "    "))
                    else:
                        lines.append(f"{indent}  - {item}")
        else:
            # Check if value is an image path
            v_str = str(v)
            if isinstance(v, str) and (v.endswith(".webp") or v.endswith(".png") or v.endswith(".jpg")):
                lines.append(f"{indent}- **{k}**: ![{k}]({v})")
            elif isinstance(v, str) and "\n" in v:
                lines.append(f"{indent}- **{k}**:")
                for subline in v.split("\n"):
                     lines.append(f"{indent}    {subline}")
            else:
                lines.append(f"{indent}- **{k}**: {v}")
    return lines

def gerar_compilado_md(croqui_dir: Path, compilado_yaml_path: Path, output_md_path: Path):
    with open(compilado_yaml_path, "r", encoding="utf-8") as f:
        compilado = yaml.safe_load(f)
        
    croqui_yaml_path = croqui_dir / "croqui.yaml"
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui = yaml.safe_load(f)

    md_lines = []
    md_lines.append(f"# Croqui: {compilado.get('nome', 'Sem nome')}\n")
    
    # Global fields (exclude secoes_textuais, picos, arquivos_externos)
    globais = {k: v for k, v in compilado.items() if k not in ["secoes_textuais", "picos", "arquivos_externos"]}
    if globais:
        md_lines.append("## Informações Gerais\n")
        md_lines.extend(render_dict(globais))
        md_lines.append("\n")

    partes_json_path = croqui_dir / "partes.json"
    ordem_partes = []
    if partes_json_path.exists():
        with open(partes_json_path, "r", encoding="utf-8") as f:
             partes = json.load(f)
             ordem_partes = list(partes.keys())
             
    blocks = {}
    
    secoes_textuais = croqui.get("secoes_textuais", [])
    compilado_am = compilado.get("secoes_textuais", [])
    for i, am in enumerate(secoes_textuais):
        if "caminho" in am and i < len(compilado_am):
            blocks[Path(am["caminho"]).stem] = {
                "tipo": "arquivo_markdown",
                "dados": compilado_am[i]
            }

    def coletar_blocos_recursivo(setores_ou_grupos_list, compilado_setores_ou_grupos_list, pico_nome):
        for j, elemento in enumerate(setores_ou_grupos_list):
            if j >= len(compilado_setores_ou_grupos_list): continue
            
            tipo = "setor" if "setor" in elemento else "grupo"
            dados_compilados = compilado_setores_ou_grupos_list[j].get(tipo)
            dados_originais = elemento.get(tipo)
            
            if "caminho" in dados_originais:
                stem = Path(dados_originais["caminho"]).stem
                blocks[stem] = {
                    "tipo": tipo,
                    "pico_nome": pico_nome,
                    "dados": dados_compilados
                }
            
            # Se for um grupo, processa seus setores internos
            if tipo == "grupo":
                conteudo_compilado = dados_compilados.get("conteudo", dados_compilados)
                conteudo_original = dados_originais.get("conteudo", dados_originais)
                
                filhos_compilados = conteudo_compilado.get("setores", [])
                filhos_originais = conteudo_original.get("setores", [])
                coletar_blocos_recursivo(filhos_originais, filhos_compilados, pico_nome)

    picos = croqui.get("picos", [])
    compilado_picos = compilado.get("picos", [])
    for i, pico in enumerate(picos):
        setores_ou_grupos = pico.get("setores_ou_grupos", [])
        if i < len(compilado_picos):
            compilado_setores_ou_grupos = compilado_picos[i].get("setores_ou_grupos", [])
            coletar_blocos_recursivo(setores_ou_grupos, compilado_setores_ou_grupos, compilado_picos[i].get("nome", f"Pico {i}"))

    emisssed_blocks = set()
    for parte in ordem_partes:
        if parte in blocks:
            bloco = blocks[parte]
            emisssed_blocks.add(parte)
            
            md_lines.append(f"## Parte: {parte}\n")
            if bloco["tipo"] == "arquivo_markdown":
                dados = bloco["dados"]
                titulo = dados.get("titulo", parte)
                md_lines.append(f"### {titulo}\n")
                if "conteudo" in dados:
                   md_lines.append("#### Conteúdo:\n")
                   md_lines.append(dados["conteudo"])
                   md_lines.append("\n")
                
                outros = {k: v for k, v in dados.items() if k not in ["titulo", "conteudo"]}
                if outros:
                    md_lines.append("#### Detalhes Extras:\n")
                    md_lines.extend(render_dict(outros))
                    md_lines.append("\n")

            elif bloco["tipo"] in ["setor", "grupo"]:
                label = "Setor" if bloco["tipo"] == "setor" else "Grupo"
                md_lines.append(f"### {label} (Pico: {bloco['pico_nome']})\n")
                
                conteudo = bloco["dados"].get("conteudo", bloco["dados"])
                if isinstance(conteudo, dict):
                    md_lines.extend(render_dict(conteudo))
                    md_lines.append("\n")
                else:
                    md_lines.append(str(conteudo))
                    md_lines.append("\n")
                    
    # Missing blocks not covered by partes.json
    for k, bloco in blocks.items():
        if k not in emisssed_blocks:
            md_lines.append(f"## Parte: {k} (não listada em partes.json)\n")
            if bloco["tipo"] == "arquivo_markdown":
                dados = bloco["dados"]
                titulo = dados.get("titulo", k)
                md_lines.append(f"### {titulo}\n")
                if "conteudo" in dados:
                   md_lines.append("#### Conteúdo:\n")
                   md_lines.append(dados["conteudo"])
                   md_lines.append("\n")
                outros = {k: v for k, v in dados.items() if k not in ["titulo", "conteudo"]}
                if outros:
                    md_lines.append("#### Detalhes Extras:\n")
                    md_lines.extend(render_dict(outros))
                    md_lines.append("\n")
            elif bloco["tipo"] in ["setor", "grupo"]:
                label = "Setor" if bloco["tipo"] == "setor" else "Grupo"
                md_lines.append(f"### {label} (Pico: {bloco['pico_nome']})\n")
                conteudo = bloco["dados"].get("conteudo", bloco["dados"])
                if isinstance(conteudo, dict):
                    md_lines.extend(render_dict(conteudo))
                    md_lines.append("\n")
                else:
                    md_lines.append(str(conteudo))
                    md_lines.append("\n")

    if "arquivos_externos" in compilado:
        md_lines.append("## Arquivos Externos\n")
        md_lines.extend(render_dict({"arquivos_externos": compilado["arquivos_externos"]}))
        md_lines.append("\n")
        
    with open(output_md_path, "w", encoding="utf-8") as f:
         f.write("\n".join(md_lines) + "\n")
    # We remove the print statement from here so that the caller can decide to print it or not.

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--croqui_dir", required=True)
    parser.add_argument("--compilado_yaml", required=True)
    parser.add_argument("--output_md", required=True)
    args = parser.parse_args()
    gerar_compilado_md(Path(args.croqui_dir), Path(args.compilado_yaml), Path(args.output_md))
