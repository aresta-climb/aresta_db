# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import re
import shutil
import yaml
import sys

# ===========================================================================
# PYAML CONFIGURATION
# ===========================================================================
# O PyYAML 1.1 interpreta '08' e '09' como strings automaticamente porque não são octais válidos.
# Porém, ao fazer o dump, ele decide remover as aspas por achar que são strings seguras.
# Para manter a formatação visual (e compatibilidade com YAML 1.2), forçamos as aspas
# em qualquer string que seja composta puramente de dígitos.
def _str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    if data.isdigit():
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, _str_representer)
yaml.add_representer(str, _str_representer, Dumper=yaml.SafeDumper)

from pathlib import Path
import json
from google.protobuf import json_format
from PIL import Image
from collections import Counter


# Adiciona o diretório raiz do projeto ao sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent))

import build
from aresta_api.proto.generated import croqui_pb2

# ===========================================================================
# UTILITÁRIOS DE PROCESSAMENTO DE TEXTO E IMAGEM
# ===========================================================================

def parse_md_com_frontmatter(caminho_arquivo):
    """Lê um arquivo Markdown e separa o YAML Frontmatter do conteúdo."""
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read()
    except Exception as e:
        raise RuntimeError(f"Erro ao ler arquivo: {caminho_arquivo}. Erro: {e}")
    
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", conteudo, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            raise ValueError(f"Erro de YAML no frontmatter de {caminho_arquivo}:\n{e}")
        corpo = match.group(2).strip()
        return frontmatter, corpo
    return None, conteudo.strip()

def processar_caminho_imagem(caminho_img_original, pico_path):
    """
    Processa um caminho de imagem original, copia para a pasta de destino com nome único
    e retorna o novo caminho relativo.
    """
    if caminho_img_original.lower().endswith('.png'):
        raise ValueError(f"Imagens no formato PNG não são permitidas: {caminho_img_original}. Por favor converta para WebP ou JPEG.")

    if "raw_pdf_contents/imagens" not in caminho_img_original:
        return caminho_img_original

    src = pico_path / caminho_img_original
    if not src.exists():
        raise FileNotFoundError(f"Imagem referenciada em raw_pdf_contents não encontrada: {src}")
    
    # Exemplo: raw_pdf_contents/imagens/setor_X/pY_iZ.webp -> setor_X_pY_iZ.webp
    partes = caminho_img_original.split("/")
    if len(partes) >= 2 and partes[-2] != "imagens":
        novo_nome_arquivo = f"{partes[-2]}_{partes[-1]}"
    else:
        novo_nome_arquivo = partes[-1]
    
    dest = pico_path / "imagens" / novo_nome_arquivo
    if not dest.parent.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(src, dest)
    return f"imagens/{novo_nome_arquivo}"

def integrar_metadados_mapa(mapa, pico_path):
    """
    Se a imagem do mapa estiver em raw_pdf_contents, procura um arquivo .json
    correspondente e preenche largura_mapa, altura_mapa e pontos_de_interesse.
    """
    img_path_str = mapa.get("caminho_imagem_mapa")
    if not img_path_str or "raw_pdf_contents/imagens" not in img_path_str:
        return False
        
    json_path = pico_path / img_path_str.replace(".webp", ".json")
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            modificado = False
            if "dimensoes_imagem" in data:
                dims = data["dimensoes_imagem"]
                if "largura" in dims:
                    mapa["largura_mapa"] = dims["largura"]
                    modificado = True
                if "altura" in dims:
                    mapa["altura_mapa"] = dims["altura"]
                    modificado = True
            
            if "pontos_de_interesse" in data:
                # Substitui os pontos pelos extraídos do PDF
                mapa["pontos_de_interesse"] = data["pontos_de_interesse"]
                modificado = True
                
            return modificado
        except Exception as e:
            print(f"    Aviso: Erro ao carregar metadados JSON de {json_path}: {e}")
    return False

def coletar_e_atualizar_imagens(texto, pico_path):
    """Encontra imagens no estilo markdown e as processa usando a função utility."""
    md_imgs = re.findall(r"!\[.*?\]\((.*?)\)", texto)
    
    novo_texto = texto
    for img_path_str in md_imgs:
        novo_caminho = processar_caminho_imagem(img_path_str, pico_path)
        if novo_caminho != img_path_str:
            novo_texto = novo_texto.replace(img_path_str, novo_caminho)
    
    return novo_texto

def salvar_md_com_frontmatter(md_path, frontmatter, corpo):
    """Salva o YAML Frontmatter e o corpo de volta no arquivo markdown."""
    with open(md_path, "w", encoding="utf-8") as f:
        if frontmatter:
            f.write("---\n" + yaml.dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n")
        f.write(corpo)

def aplicar_tabela_nas_imagens(texto_md: str) -> str:
    matches = list(re.finditer(r"!\[(.*?)\]\((.*?)\)", texto_md))
    for match in reversed(matches):
        alt_text = match.group(1).strip()
        img_path = match.group(2)
        start, end = match.span()
        if alt_text:
            if start >= 2 and texto_md[start-2:start] == "| ":
                continue
            nova_tag = f"| ![{alt_text}]({img_path}) |\n| :--: |\n| *{alt_text}* |"
            texto_md = texto_md[:start] + nova_tag + texto_md[end:]
    return texto_md

def converter_coordenadas_e7_recursivo(obj) -> bool:
    """
    Recursivamente converte campos 'latitude' e 'longitude' para o formato E7 (int).
    Se os valores forem floats, multiplica por 10^7 e arredonda.
    Retorna True se houver qualquer modificação.
    """
    modificado = False
    if isinstance(obj, list):
        for item in obj:
            if converter_coordenadas_e7_recursivo(item):
                modificado = True
    elif isinstance(obj, dict):
        if "latitude" in obj and "longitude" in obj:
            lat = obj["latitude"]
            lon = obj["longitude"]
            
            # Só converte se for float. Se já for int, assume que já está em E7.
            # Também aceita strings que podem ser convertidas para float.
            def to_e7(val):
                if isinstance(val, (float, int)) and not isinstance(val, bool):
                    if isinstance(val, float):
                        return int(round(val * 10**7)), True
                return val, False

            new_lat, mod_lat = to_e7(lat)
            new_lon, mod_lon = to_e7(lon)
            
            if mod_lat:
                obj["latitude"] = new_lat
                modificado = True
            if mod_lon:
                obj["longitude"] = new_lon
                modificado = True
        
        # Continua a recursão para todos os campos
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                if converter_coordenadas_e7_recursivo(v):
                    modificado = True
    return modificado

def mover_descricao_para_corpo(frontmatter: dict, corpo: str):
    """
    Se o frontmatter contiver um campo 'descricao' (seja no topo ou dentro de pico/setor/grupo),
    move seu conteúdo para o corpo do Markdown e o remove do frontmatter.
    """
    if frontmatter is None:
        return None, corpo, False

    modificado = False
    descricao = None

    # 1. Checa se tem descricao no topo do frontmatter
    if "descricao" in frontmatter:
        descricao = frontmatter.pop("descricao")
        modificado = True
    # 2. Checa se tem descricao dentro de pico, setor ou grupo (legado)
    else:
        for key in ["pico", "setor", "grupo"]:
            if key in frontmatter and isinstance(frontmatter[key], dict):
                if "descricao" in frontmatter[key]:
                    descricao = frontmatter[key].pop("descricao")
                    modificado = True
                    break
    
    if descricao:
        descricao_str = str(descricao).strip()
        if descricao_str:
            # Adiciona ao corpo. Se o corpo já tiver conteúdo, adicionamos separadores.
            if corpo.strip():
                corpo = corpo.rstrip() + "\n\n" + descricao_str + "\n"
            else:
                corpo = descricao_str + "\n"
            
    return frontmatter, corpo, modificado

def desduplicar_referencias_no_md(md_path, pico_path):
    """
    Checa se o mesmo arquivo .md possui a mesma imagem referenciada em mais de um local.
    Caso isso aconteça, duplica a imagem física e atualiza o Markdown para que possam ser editadas individualmente.
    """
    frontmatter, corpo = parse_md_com_frontmatter(md_path)
    if frontmatter is None and not corpo:
        return

    modificado = False
    contagem = Counter()

    def processar_caminho(caminho_rel):
        nonlocal modificado
        if not isinstance(caminho_rel, str) or not caminho_rel.startswith("imagens/"):
            return caminho_rel
        
        contagem[caminho_rel] += 1
        if contagem[caminho_rel] == 1:
            return caminho_rel
        
        # Duplicado detectado!
        base, ext = os.path.splitext(caminho_rel)
        suffix = contagem[caminho_rel]
        novo_caminho = f"{base}_{suffix}{ext}"
        
        # Garante que o novo nome não colida com um arquivo já existente (caso o suffix já tenha sido usado)
        # Embora improvável se rodarmos sempre do zero, é bom ser robusto.
        while (pico_path / novo_caminho).exists():
            suffix += 1
            novo_caminho = f"{base}_{suffix}{ext}"
            
        print(f"    - Duplicando imagem para referência múltipla em {md_path.name}: {caminho_rel} -> {novo_caminho}")
        src = pico_path / caminho_rel
        dest = pico_path / novo_caminho
        if src.exists():
            shutil.copy2(src, dest)
            modificado = True
            # Incrementamos a contagem do novo caminho para evitar usá-lo como base de desduplicação
            contagem[novo_caminho] += 1
            return novo_caminho
        return caminho_rel

    # 1. Processar Frontmatter (Recursivamente)
    def percorrer_frontmatter(obj):
        nonlocal modificado
        if isinstance(obj, list):
            for i in range(len(obj)):
                if isinstance(obj[i], (dict, list)):
                    percorrer_frontmatter(obj[i])
                elif isinstance(obj[i], str) and obj[i].startswith("imagens/"):
                    # Não costuma ter string pura com imagens/ na lista, mas por garantia
                    pass
        elif isinstance(obj, dict):
            # Campos conhecidos que contêm caminhos de imagem
            campos_imagem = ["caminho_imagem_mapa"]
            for campo in campos_imagem:
                if campo in obj:
                    original = obj[campo]
                    novo = processar_caminho(original)
                    if novo != original:
                        obj[campo] = novo
                        modificado = True
            
            # Recorre em todos os campos
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    percorrer_frontmatter(v)

    if frontmatter:
        percorrer_frontmatter(frontmatter)

    # 2. Processar Corpo (Regex para substituir um por um)
    def substituidor_corpo(match):
        alt = match.group(1)
        path = match.group(2)
        novo_path = processar_caminho(path)
        return f"![{alt}]({novo_path})"

    # Usamos re.sub com uma função para processar cada match individualmente
    novo_corpo = re.sub(r"!\[(.*?)\]\((imagens/.*?\.webp)\)", substituidor_corpo, corpo)
    if novo_corpo != corpo:
        corpo = novo_corpo
        modificado = True

    if modificado:
        salvar_md_com_frontmatter(md_path, frontmatter, corpo)


# ===========================================================================
# FASE 1: CORREÇÃO E MIGRAÇÃO (DATABASE)
# ===========================================================================

def processar_croqui_yaml(croqui_data, pico_path, croqui_yaml_path):
    """Processa campos do croqui.yaml e salva no arquivo original se houver mudanças."""
    modificado_yaml = False
    if "caminho_thumbnail" in croqui_data:
        img_original = croqui_data["caminho_thumbnail"]
        novo_caminho = processar_caminho_imagem(img_original, pico_path)
        if novo_caminho != img_original:
            croqui_data["caminho_thumbnail"] = novo_caminho
            modificado_yaml = True
    
    if converter_coordenadas_e7_recursivo(croqui_data):
        modificado_yaml = True

    if modificado_yaml:
        with open(croqui_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(croqui_data, f, allow_unicode=True, sort_keys=False)

def corrigir_setores_ou_grupos_recursivo(setores_ou_grupos_raw, pico_path):
    """Percorre setores ou grupos corrigindo imagens nos arquivos MD e frontmatter."""
    for e_ref in setores_ou_grupos_raw:
        if not e_ref: continue
        # Resolve o objeto interno baseado no oneof (setor ou grupo)
        tipo = "setor" if "setor" in e_ref else "grupo"
        obj_ref = e_ref.get(tipo)
        
        if not obj_ref: continue

        if "caminho" in obj_ref:
            md_path = pico_path / obj_ref["caminho"]
            frontmatter, corpo = parse_md_com_frontmatter(md_path)
            
            if not frontmatter: frontmatter = {}

            # 1. Move descricao para o corpo (se existir)
            frontmatter, corpo, modificado_desc = mover_descricao_para_corpo(frontmatter, corpo)

            # 2. Corrige imagens no corpo do MD
            novo_corpo = coletar_e_atualizar_imagens(corpo, pico_path)
            modificado = (corpo != novo_corpo) or modificado_desc
            
            # 2. Corrige imagens dos mapas no frontmatter
            if "mapas" in frontmatter:
                for mapa in frontmatter["mapas"]:
                    if "caminho_imagem_mapa" in mapa:
                        img_original = mapa["caminho_imagem_mapa"]
                        
                        # Tenta integrar metadados antes de mudar o caminho
                        if integrar_metadados_mapa(mapa, pico_path):
                            modificado = True
                            
                        novo_caminho_img = processar_caminho_imagem(img_original, pico_path)
                        if novo_caminho_img != img_original:
                            mapa["caminho_imagem_mapa"] = novo_caminho_img
                            modificado = True

            # 2.1 Corrige imagens em via_multiplas_enfiadas dentro de escaladas/vias no frontmatter
            for key in ["escaladas", "vias"]:
                if key in frontmatter:
                    for via in frontmatter[key]:
                        if via and isinstance(via, dict) and "via_multiplas_enfiadas" in via:
                            vmf = via["via_multiplas_enfiadas"]
                            if vmf and "mapas" in vmf:
                                for mapa in vmf["mapas"]:
                                    if "caminho_imagem_mapa" in mapa:
                                        img_original = mapa["caminho_imagem_mapa"]
                                        
                                        # Tenta integrar metadados antes de mudar o caminho
                                        if integrar_metadados_mapa(mapa, pico_path):
                                            modificado = True
                                            
                                        novo_caminho_img = processar_caminho_imagem(img_original, pico_path)
                                        if novo_caminho_img != img_original:
                                            mapa["caminho_imagem_mapa"] = novo_caminho_img
                                            modificado = True

            # 2.2 Converte coordenadas para E7 no frontmatter
            if converter_coordenadas_e7_recursivo(frontmatter):
                modificado = True

            if modificado:
                salvar_md_com_frontmatter(md_path, frontmatter, novo_corpo)
            
            # 2.2 Desduplica referências no arquivo MD (mesma imagem usada mais de uma vez no mesmo arquivo)
            desduplicar_referencias_no_md(md_path, pico_path)

            # 3. Recursão para sub-setores (agora 'setores' sob um Grupo ou o legado 'sub_setores')
            # Grupos no MD podem ter o campo 'setores' ou o antigo 'sub_setores'
            filhos = frontmatter.get("setores") or frontmatter.get("sub_setores")
            if filhos:
                # Recursivamente corrige, mas note que filhos são sempre ArquivoSetor (não SetorOuGrupo)
                # Então precisamos de uma função auxiliar ou adaptar esta.
                # Como Grupos só contêm setores, podemos embrulhar para reuso ou simplificar.
                corrigir_arquivo_setor_recursivo(filhos, pico_path)
        else:
            # Caso estruturado diretamente no YAML
            conteudo = obj_ref.get("conteudo") or {}
            filhos = conteudo.get("setores") or conteudo.get("sub_setores")
            if filhos:
                corrigir_arquivo_setor_recursivo(filhos, pico_path)

def corrigir_arquivo_setor_recursivo(setores_raw, pico_path):
    """Auxiliar para corrigir uma lista de ArquivoSetor (usado dentro de Grupos)."""
    # Embrulha cada ArquivoSetor como um SetorOuGrupo fake para reusar a lógica
    fake_setores_ou_grupos = [{"setor": s} for s in setores_raw]
    corrigir_setores_ou_grupos_recursivo(fake_setores_ou_grupos, pico_path)

def coletar_referencias_arquivos(pico_path: Path, croqui_data: dict) -> set:
    """Coleta referências a arquivos (imagens e md) existentes no croqui."""
    referencias = set()
    
    # 1. Thumbnail
    if "caminho_thumbnail" in croqui_data:
        referencias.add(croqui_data["caminho_thumbnail"])
        
    # 2. Markdown Globais em Botões
    for botao in croqui_data.get("botoes", []):
        if isinstance(botao, dict):
            destino = botao.get("destino", {})
            secao = destino.get("secao_textual", {})
            if isinstance(secao, dict) and "caminho" in secao:
                md_path = pico_path / secao["caminho"]
                referencias.add(secao["caminho"])
                if md_path.exists():
                    _, corpo = parse_md_com_frontmatter(md_path)
                    referencias.update(re.findall(r"!\[.*?\]\((.*?)\)", corpo))
            
    # 3. Picos e Elementos
    def coletar_setores_ou_grupos_recursivo(setores_ou_grupos_raw):
        for e_ref in setores_ou_grupos_raw:
            tipo = "setor" if "setor" in e_ref else "grupo"
            obj_ref = e_ref.get(tipo)
            if not obj_ref: continue

            if "caminho" in obj_ref:
                md_path = pico_path / obj_ref["caminho"]
                referencias.add(obj_ref["caminho"])
                if md_path.exists():
                    frontmatter, corpo = parse_md_com_frontmatter(md_path)
                    referencias.update(re.findall(r"!\[.*?\]\((.*?)\)", corpo))
                    if frontmatter and "mapas" in frontmatter:
                        for mapa in frontmatter["mapas"]:
                            if "caminho_imagem_mapa" in mapa:
                                referencias.add(mapa["caminho_imagem_mapa"])
                    
                    # Coleta imagens de mapas de vias de múltiplas enfiadas
                    for key in ["escaladas", "vias"]:
                        if frontmatter and key in frontmatter:
                            for via in frontmatter[key]:
                                if via and isinstance(via, dict) and "via_multiplas_enfiadas" in via:
                                    vmf = via["via_multiplas_enfiadas"]
                                    if vmf and "mapas" in vmf:
                                        for mapa in vmf["mapas"]:
                                            if "caminho_imagem_mapa" in mapa:
                                                referencias.add(mapa["caminho_imagem_mapa"])
                    filhos = frontmatter.get("setores") or frontmatter.get("sub_setores")
                    if filhos:
                        coletar_setores_ou_grupos_recursivo([{"setor": s} for s in filhos])
            else:
                # Caso estruturado diretamente no YAML
                conteudo = obj_ref.get("conteudo") or {}
                if "descricao" in conteudo:
                    referencias.update(re.findall(r"!\[.*?\]\((.*?)\)", conteudo["descricao"]))
                if "mapas" in conteudo:
                    for mapa in conteudo["mapas"]:
                        if "caminho_imagem_mapa" in mapa:
                            referencias.add(mapa["caminho_imagem_mapa"])
                
                # Coleta imagens de mapas de vias de múltiplas enfiadas
                for key in ["escaladas", "vias"]:
                    if key in conteudo:
                        for via in conteudo[key]:
                            if via and isinstance(via, dict) and "via_multiplas_enfiadas" in via:
                                vmf = via["via_multiplas_enfiadas"]
                                if vmf and "mapas" in vmf:
                                    for mapa in vmf["mapas"]:
                                        if "caminho_imagem_mapa" in mapa:
                                            referencias.add(mapa["caminho_imagem_mapa"])
                filhos = conteudo.get("setores") or conteudo.get("sub_setores")
                if filhos:
                    coletar_setores_ou_grupos_recursivo([{"setor": s} for s in filhos if s])

    for pico in croqui_data.get("picos", []):
        if "setores_ou_grupos" in pico:
            coletar_setores_ou_grupos_recursivo(pico["setores_ou_grupos"])
        if "mapas_gerais" in pico:
            mg = pico["mapas_gerais"]
            if isinstance(mg, dict) and "caminho" in mg:
                md_path = pico_path / mg["caminho"]
                referencias.add(mg["caminho"])
                if md_path.exists():
                    frontmatter, corpo = parse_md_com_frontmatter(md_path)
                    referencias.update(re.findall(r"!\[.*?\]\((.*?)\)", corpo))
                    if frontmatter and "mapas" in frontmatter:
                        for mapa in frontmatter["mapas"]:
                            if "caminho_imagem_mapa" in mapa:
                                referencias.add(mapa["caminho_imagem_mapa"])
            
    # Filtra e normaliza: apenas referências que apontam para imagens/ ou .md
    return {ref.replace("\\", "/") for ref in referencias if isinstance(ref, str) and (ref.startswith("imagens/") or ref.endswith(".md"))}

def limpar_arquivos_nao_utilizados(pico_path: Path, croqui_data: dict):
    """Deleta arquivos (imagens e markdowns) que não possuem referências nos metadados."""
    pasta_imagens = pico_path / "imagens"
    
    referencias = coletar_referencias_arquivos(pico_path, croqui_data)
    
    # Arquivos físicos na pasta imagens/ (ignora subdiretórios)
    arquivos_fisicos = set()
    if pasta_imagens.exists():
        arquivos_fisicos.update(f"imagens/{f.name}" for f in pasta_imagens.iterdir() if f.is_file())
        
    # Arquivos físicos markdown na raiz e subdiretórios rasos
    # Aqui procuramos .md dentro da pasta do pico. Não fazemos rglob para evitar apagar coisas fora.
    arquivos_fisicos.update(f.name for f in pico_path.iterdir() if f.is_file() and f.suffix == ".md")
    
    nao_utilizados = arquivos_fisicos - referencias
    
    if nao_utilizados:
        print(f"  Fazendo limpeza de {len(nao_utilizados)} arquivo(s) órfão(s)...")
        for f_rel in sorted(nao_utilizados):
            f_abs = pico_path / f_rel
            if f_abs.exists():
                print(f"    - Deletando: {f_rel}")
                f_abs.unlink()

def corrigir_database(pico_path: Path):
    """
    Função principal que coordena o processamento do database para garantir
    que imagens em raw_pdf_contents sejam migradas e os caminhos corrigidos.
    """
    pico_path = Path(pico_path)
    # Executa o motor de migrações no início da rotina de correção
    from scripts.migrador import aplicar_migracoes
    aplicar_migracoes(pico_path)

    croqui_yaml_path = pico_path / "croqui.yaml"
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_data = yaml.safe_load(f)

    # 1. Corrige thumbnail no croqui.yaml
    try:
        processar_croqui_yaml(croqui_data, pico_path, croqui_yaml_path)
    except Exception as e:
        raise RuntimeError(f"Erro ao processar thumbnail em {croqui_yaml_path}: {e}")

    # 2. Corrige imagens nos markdowns de botões
    for botao in croqui_data.get("botoes", []):
        if isinstance(botao, dict):
            destino = botao.get("destino", {})
            secao = destino.get("secao_textual", {})
            if isinstance(secao, dict) and "caminho" in secao:
                md_path = pico_path / secao["caminho"]
                if md_path.exists():
                    frontmatter, corpo = parse_md_com_frontmatter(md_path)
                    
                    # 1. Move descricao para o corpo (se existir)
                    frontmatter, corpo, modificado_desc = mover_descricao_para_corpo(frontmatter, corpo)

                    # 2. Corrige imagens no corpo do MD
                    novo_corpo = coletar_e_atualizar_imagens(corpo, pico_path)
                    modificado = (corpo != novo_corpo) or modificado_desc
                    
                    if converter_coordenadas_e7_recursivo(frontmatter):
                        modificado = True

                    if modificado:
                        salvar_md_com_frontmatter(md_path, frontmatter, novo_corpo)
                    
                    # 2.1 Desduplica referências
                    desduplicar_referencias_no_md(md_path, pico_path)

    # 3. Corrige imagens nos setores ou grupos de cada pico
    for pico in croqui_data.get("picos", []):
        if "setores_ou_grupos" in pico:
            corrigir_setores_ou_grupos_recursivo(pico["setores_ou_grupos"], pico_path)

    # 4. Limpeza de imagens órfãs
    limpar_arquivos_nao_utilizados(pico_path, croqui_data)

    # 5. Garante comentário SPDX e Copyright em todos os arquivos
    for file_path in pico_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".yaml", ".md"]:
            garantir_comentarios_licenca(file_path)

# ===========================================================================
# FASE 2: COMPILAÇÃO DE ARTEFATOS (GENERATED)
# ===========================================================================

def expandir_arquivo_generico(obj_ref, pico_path):
    """
    Expande um objeto que pode ser Setor ou Grupo.
    Retorna (tipo, dados_expandidos) onde tipo é 'setor' ou 'grupo'.
    dados_expandidos é um dict com 'conteudo' ou 'caminho' (compatível com ArquivoSetor/ArquivoGrupo).
    """
    if "caminho" in obj_ref:
        md_path = pico_path / obj_ref["caminho"]
        frontmatter, corpo = parse_md_com_frontmatter(md_path)
        if not frontmatter: frontmatter = {}

        # Heurística: Se tem setores/sub_setores, é um Grupo. Caso contrário Setor.
        filhos = frontmatter.get("setores") or frontmatter.get("sub_setores")
        
        if filhos:
            # É um Grupo
            # Grupos só podem ter setores filhos (ArquivoSetor)
            # Filtra eventuais nulos na lista de filhos
            setores_expandidos = []
            for s in filhos:
                if not s: continue
                # Se s é string, converte para dict com caminho
                s_ref = {"caminho": s} if isinstance(s, str) else s
                _, dados = expandir_arquivo_generico(s_ref if "caminho" in s_ref else {"conteudo": s_ref.get("conteudo")}, pico_path)
                setores_expandidos.append(dados)
            
            frontmatter["setores"] = setores_expandidos
            # Limpa legados
            if "sub_setores" in frontmatter: del frontmatter["sub_setores"]
            
            grupo_obj = frontmatter.copy()
            grupo_obj["descricao"] = aplicar_tabela_nas_imagens(corpo)
            return "grupo", {"conteudo": grupo_obj}
        else:
            # É um Setor
            setor_obj = frontmatter.copy()
            setor_obj["descricao"] = aplicar_tabela_nas_imagens(corpo)
            return "setor", {"conteudo": setor_obj}
    else:
        # Caso estruturado diretamente no YAML
        conteudo = obj_ref.get("conteudo") or {}
        filhos = conteudo.get("setores") or conteudo.get("sub_setores")
        if filhos:
            # É um Grupo
            setores_expandidos = []
            for s in filhos:
                if not s: continue
                s_ref = {"caminho": s} if isinstance(s, str) else s
                _, dados = expandir_arquivo_generico(s_ref if "caminho" in s_ref else {"conteudo": s_ref.get("conteudo")}, pico_path)
                setores_expandidos.append(dados)
            
            conteudo["setores"] = setores_expandidos
            if "sub_setores" in conteudo: del conteudo["sub_setores"]
            return "grupo", obj_ref
        else:
            # É um Setor
            return "setor", obj_ref

def expandir_setores_ou_grupos_recursivo(setores_ou_grupos_raw, pico_path):
    """Expande o conteúdo de arquivos MD em objetos estruturados (Setor ou Grupo)."""
    processados = []
    for e_ref in setores_ou_grupos_raw:
        # Tenta identificar se é setor ou grupo no input do YAML
        tipo_in = "setor" if "setor" in e_ref else "grupo"
        obj_ref = e_ref.get(tipo_in)
        if not obj_ref: continue

        tipo_out, dados = expandir_arquivo_generico(obj_ref, pico_path)
        processados.append({tipo_out: dados})

    return processados

def atualizar_dimensoes_mapas(obj, pico_path: Path):
    """
    Recursivamente percorre o objeto (dict ou list) em busca de 'caminho_imagem_mapa'.
    Se encontrar, tenta abrir a imagem para preencher 'largura_mapa' e 'altura_mapa'.
    """
    if isinstance(obj, list):
        for item in obj:
            atualizar_dimensoes_mapas(item, pico_path)
    elif isinstance(obj, dict):
        if "caminho_imagem_mapa" in obj:
            caminho_rel = obj["caminho_imagem_mapa"]
            # A imagem pode estar referenciada relativa à raiz do pico ou já estar em imagens/
            caminho_abs = pico_path / caminho_rel
            if caminho_abs.exists():
                try:
                    with Image.open(caminho_abs) as img:
                        w, h = img.size
                        obj["largura_mapa"] = w
                        obj["altura_mapa"] = h
                except Exception as e:
                    print(f"Aviso: Não foi possível obter dimensões da imagem {caminho_rel}: {e}")
        
        # Continua a recursão em todos os campos
        for value in obj.values():
            atualizar_dimensoes_mapas(value, pico_path)

def validar_pontos_de_interesse_recursivo(obj, path=""):
    """
    Valida recursivamente todos os pontos de interesse no objeto.
    Regras:
    - Circular: x, y, raio
    - Box: x, y, comprimento, largura. angulo_graus_x100 (opcional) entre 0 e 36000.
    - Área livre: coordenadas precisa ter número par de elementos.
    """
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            validar_pontos_de_interesse_recursivo(item, f"{path}[{i}]")
    elif isinstance(obj, dict):
        if "pontos_de_interesse" in obj and isinstance(obj["pontos_de_interesse"], list):
            for i, pt in enumerate(obj["pontos_de_interesse"]):
                poi_path = f"{path}.pontos_de_interesse[{i}]"
                label = pt.get('label', pt.get('id', '?'))
                
                if 'circulo' in pt:
                    circ = pt['circulo']
                    for req in ['x', 'y', 'raio']:
                        if req not in circ:
                            raise ValueError(f"POI '{label}' em {poi_path}: Círculo faltando campo '{req}'")
                elif 'retangulo' in pt:
                    ret = pt['retangulo']
                    for req in ['x', 'y', 'comprimento', 'largura']:
                        if req not in ret:
                            raise ValueError(f"POI '{label}' em {poi_path}: Retângulo faltando campo '{req}'")
                    if 'angulo_graus_x100' in ret:
                        ang = ret['angulo_graus_x100']
                        if not (-36000 <= ang <= 36000):
                            raise ValueError(f"POI '{label}' em {poi_path}: angulo_graus_x100 ({ang}) deve estar entre -36000 e 36000")
                elif 'quadrado' in pt:
                    quad = pt['quadrado']
                    for req in ['x', 'y', 'lado']:
                        if req not in quad:
                            raise ValueError(f"POI '{label}' em {poi_path}: Quadrado faltando campo '{req}'")
                    if 'angulo_graus_x100' in quad:
                        ang = quad['angulo_graus_x100']
                        if not (-36000 <= ang <= 36000):
                            raise ValueError(f"POI '{label}' em {poi_path}: angulo_graus_x100 ({ang}) deve estar entre -36000 e 36000")
                elif 'poligono' in pt:
                    pol = pt['poligono']
                    if 'coordenadas' not in pol:
                        raise ValueError(f"POI '{label}' em {poi_path}: Polígono faltando 'coordenadas'")
                    coords = pol['coordenadas']
                    if not isinstance(coords, list) or len(coords) % 2 != 0:
                        raise ValueError(f"POI '{label}' em {poi_path}: Polígono deve ter um número par de coordenadas (x,y pairs). Encontrado {len(coords)} elementos.")
                else:
                    # Se não tem nenhum dos 4 tipos, é inválido no novo esquema
                    raise ValueError(f"POI '{label}' em {poi_path}: Tipo de área não especificado ou inválido (esperado circulo, quadrado, retangulo ou poligono)")

        # Continua a recursão em todos os campos
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                validar_pontos_de_interesse_recursivo(v, f"{path}.{k}")

def validar_referencias_mapa(croqui_data: dict) -> list[str]:
    """
    Valida se as entidades apontadas nas referências dos mapas (escalada, setor, grupo)
    realmente existem dentro do mesmo Pico.
    Retorna uma lista de strings com descrições dos erros.
    """
    erros = []
    
    for pico in croqui_data.get("picos", []):
        pico_nome = pico.get("nome", "Pico Sem Nome")
        
        nomes_escaladas = set()
        nomes_setores = set()
        nomes_grupos = set()
        
        mapas_para_validar = []
        
        if "mapas" in pico:
            mapas_para_validar.append((f"Pico '{pico_nome}'", pico["mapas"]))
            
        def registrar_escaladas(escaladas_lista):
            for esc in escaladas_lista:
                tipo_via = list(esc.keys())[0] if esc else None
                if tipo_via:
                    via = esc[tipo_via]
                    if tipo_via == "via_multiplas_enfiadas" and "enfiadas" in via:
                        nomes_escaladas.add(via.get("nome", "Sem Nome"))
                        for e in via["enfiadas"]:
                            tipo_e = list(e.keys())[0] if e else None
                            if tipo_e:
                                nomes_escaladas.add(e[tipo_e].get("nome", "Sem Nome"))
                    else:
                        nomes_escaladas.add(via.get("nome", "Sem Nome"))

        for obj_sg in pico.get("setores_ou_grupos", []):
            if "grupo" in obj_sg:
                grupo_conteudo = obj_sg["grupo"].get("conteudo", {})
                grupo_nome = grupo_conteudo.get("nome", "Grupo Sem Nome")
                nomes_grupos.add(grupo_nome)
                
                if "mapas" in grupo_conteudo:
                    mapas_para_validar.append((f"Grupo '{grupo_nome}'", grupo_conteudo["mapas"]))
                    
                for obj_s in grupo_conteudo.get("setores", []):
                    setor_conteudo = obj_s.get("conteudo", {})
                    setor_nome = setor_conteudo.get("nome", "Setor Sem Nome")
                    nomes_setores.add(setor_nome)
                    
                    if "mapas" in setor_conteudo:
                        mapas_para_validar.append((f"Setor '{setor_nome}' (no Grupo '{grupo_nome}')", setor_conteudo["mapas"]))
                        
                    registrar_escaladas(setor_conteudo.get("escaladas", []))
                                
            elif "setor" in obj_sg:
                setor_conteudo = obj_sg["setor"].get("conteudo", {})
                setor_nome = setor_conteudo.get("nome", "Setor Sem Nome")
                nomes_setores.add(setor_nome)
                
                if "mapas" in setor_conteudo:
                    mapas_para_validar.append((f"Setor '{setor_nome}'", setor_conteudo["mapas"]))
                    
                registrar_escaladas(setor_conteudo.get("escaladas", []))

        # Valida os mapas
        for contexto_nome, mapas in mapas_para_validar:
            for idx_mapa, mapa in enumerate(mapas):
                for ref in mapa.get("referencias", []):
                    ids_vistos = set()
                    # Validação de duplicação de ID na mesma referência
                    for ref_id in ref.get("ids", []):
                        if ref_id in ids_vistos:
                            nome_ref = ref.get("escalada") or ref.get("setor") or ref.get("grupo") or "Desconhecida"
                            erros.append(f"O ID '{ref_id}' está duplicado na referência '{nome_ref}' (Mapa {idx_mapa+1} em {contexto_nome}).")
                        ids_vistos.add(ref_id)
                        
                    # Validação de existência da entidade
                    if "escalada" in ref:
                        nome = ref["escalada"]
                        if nome not in nomes_escaladas:
                            erros.append(f"Referência à escalada '{nome}' não encontrada no pico '{pico_nome}' (Mapa {idx_mapa+1} em {contexto_nome}).")
                    if "setor" in ref:
                        nome = ref["setor"]
                        if nome not in nomes_setores:
                            erros.append(f"Referência ao setor '{nome}' não encontrada no pico '{pico_nome}' (Mapa {idx_mapa+1} em {contexto_nome}).")
                    if "grupo" in ref:
                        nome = ref["grupo"]
                        if nome not in nomes_grupos:
                            erros.append(f"Referência ao grupo '{nome}' não encontrada no pico '{pico_nome}' (Mapa {idx_mapa+1} em {contexto_nome}).")
                            
    return erros

def computar_precomputados_setor(setor_conteudo: dict):
    """Calcula precomputados para um único setor."""
    escaladas = setor_conteudo.get("escaladas", [])
    total = len(escaladas)
    
    total_esportivas = 0
    total_moveis = 0
    total_boulders = 0
    total_multiplas_enfiadas = 0
    total_highlines = 0

    for e in escaladas:
        if "via_esportiva" in e:
            total_esportivas += 1
        elif "tradicional" in e:
            total_moveis += 1
        elif "boulder" in e:
            total_boulders += 1
        elif "via_multiplas_enfiadas" in e:
            total_multiplas_enfiadas += 1
        elif "highline" in e:
            total_highlines += 1

    precomputados = {
        "total_escaladas": total,
        "total_esportivas": total_esportivas,
        "total_moveis": total_moveis,
        "total_boulders": total_boulders,
        "total_multiplas_enfiadas": total_multiplas_enfiadas,
        "total_highlines": total_highlines
    }
    setor_conteudo["precomputados"] = {k: v for k, v in precomputados.items() if v > 0}

def computar_precomputados_grupo(grupo_conteudo: dict):
    """Calcula precomputados para um grupo, somando dos setores já processados."""
    total_escaladas = 0
    total_esportivas = 0
    total_moveis = 0
    total_boulders = 0
    total_multiplas_enfiadas = 0
    total_highlines = 0

    for setor_ref in grupo_conteudo.get("setores", []):
        setor = setor_ref.get("conteudo", {})
        pre = setor.get("precomputados", {})
        total_escaladas += pre.get("total_escaladas", 0)
        total_esportivas += pre.get("total_esportivas", 0)
        total_moveis += pre.get("total_moveis", 0)
        total_boulders += pre.get("total_boulders", 0)
        total_multiplas_enfiadas += pre.get("total_multiplas_enfiadas", 0)
        total_highlines += pre.get("total_highlines", 0)
        
    precomputados = {
        "total_escaladas": total_escaladas,
        "total_esportivas": total_esportivas,
        "total_moveis": total_moveis,
        "total_boulders": total_boulders,
        "total_multiplas_enfiadas": total_multiplas_enfiadas,
        "total_highlines": total_highlines
    }
    grupo_conteudo["precomputados"] = {k: v for k, v in precomputados.items() if v > 0}

def computar_precomputados_pico(pico: dict):
    """Calcula precomputados do pico, lendo diretamente dos setores e grupos filhos."""
    total_escaladas = 0
    total_setores = 0
    total_grupos = 0
    total_esportivas = 0
    total_moveis = 0
    total_boulders = 0
    total_multiplas_enfiadas = 0
    total_highlines = 0
    
    for ref in pico.get("setores_ou_grupos", []):
        if "setor" in ref:
            node = ref["setor"].get("conteudo", {})
            total_setores += 1
            
        elif "grupo" in ref:
            node = ref["grupo"].get("conteudo", {})
            total_setores += len(node.get("setores", []))
            total_grupos += 1
        else:
            continue
            
        pre = node.get("precomputados", {})
        total_escaladas += pre.get("total_escaladas", 0)
        total_esportivas += pre.get("total_esportivas", 0)
        total_moveis += pre.get("total_moveis", 0)
        total_boulders += pre.get("total_boulders", 0)
        total_multiplas_enfiadas += pre.get("total_multiplas_enfiadas", 0)
        total_highlines += pre.get("total_highlines", 0)
            
    precomputados = {
        "total_escaladas": total_escaladas,
        "total_setores": total_setores,
        "total_grupos": total_grupos,
        "total_esportivas": total_esportivas,
        "total_moveis": total_moveis,
        "total_boulders": total_boulders,
        "total_multiplas_enfiadas": total_multiplas_enfiadas,
        "total_highlines": total_highlines
    }
    pico["precomputados"] = {k: v for k, v in precomputados.items() if v > 0}

def injetar_precomputados(croqui_data: dict):
    picos = croqui_data.get("picos", [])
    
    # 1º Passo: Todos os setores (avulsos ou dentro de grupos)
    for pico in picos:
        for ref in pico.get("setores_ou_grupos", []):
            if "setor" in ref:
                computar_precomputados_setor(ref["setor"].get("conteudo", {}))
            elif "grupo" in ref:
                grupo = ref["grupo"].get("conteudo", {})
                for setor_ref in grupo.get("setores", []):
                    computar_precomputados_setor(setor_ref.get("conteudo", {}))
                    
    # 2º Passo: Todos os grupos
    for pico in picos:
        for ref in pico.get("setores_ou_grupos", []):
            if "grupo" in ref:
                computar_precomputados_grupo(ref["grupo"].get("conteudo", {}))
                
    # 3º Passo: Todos os picos
    for pico in picos:
        computar_precomputados_pico(pico)

def compilar_croqui(pico_path: Path, destino_yaml: Path, destino_binarypb: Path, dados_extras: dict = None):
    """Carrega os dados corrigidos, expande conteúdos e gera os arquivos .yaml e .binarypb de deploy."""
    croqui_yaml_path = pico_path / "croqui.yaml"
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_data = yaml.safe_load(f)

    # 1. Expande arquivos markdown globais contidos em botoes
    botoes_processados = []
    for botao in croqui_data.get("botoes", []):
        if isinstance(botao, dict):
            destino = botao.get("destino", {})
            if "secao_textual" in destino:
                secao = destino["secao_textual"]
                if isinstance(secao, dict) and "caminho" in secao:
                    md_path = pico_path / secao["caminho"]
                    _, corpo = parse_md_com_frontmatter(md_path)
                    
                    novo_botao = {
                        "texto": botao.get("texto", ""),
                        "destino": {
                            "secao_textual": {
                                "conteudo": aplicar_tabela_nas_imagens(corpo)
                            }
                        }
                    }
                    botoes_processados.append(novo_botao)
                else:
                    botoes_processados.append(botao)
            else:
                botoes_processados.append(botao)
        else:
            botoes_processados.append(botao)
    croqui_data["botoes"] = botoes_processados

    # 2. Expande setores ou grupos de cada pico
    for pico in croqui_data.get("picos", []):
        if "setores_ou_grupos" in pico:
            pico["setores_ou_grupos"] = expandir_setores_ou_grupos_recursivo(pico["setores_ou_grupos"], pico_path)

    # 2.5. Expande mapas gerais de cada pico
    for pico in croqui_data.get("picos", []):
        if "mapas_gerais" in pico:
            mg = pico["mapas_gerais"]
            if isinstance(mg, dict) and "caminho" in mg:
                md_path = pico_path / mg["caminho"]
                if md_path.exists():
                    frontmatter, _ = parse_md_com_frontmatter(md_path)
                    if frontmatter and "mapas" in frontmatter:
                        mg["conteudo"] = {"mapas": frontmatter["mapas"]}
                        del mg["caminho"]


    # 3. Atualiza dimensões de mapas automaticamente
    atualizar_dimensoes_mapas(croqui_data, pico_path)

    # 3.1 Valida pontos de interesse conforme novas regras
    validar_pontos_de_interesse_recursivo(croqui_data, pico_path.name)

    # 3.2 Valida referências de IDs no mapa (apenas avisos, não impede compilação)
    erros_mapa = validar_referencias_mapa(croqui_data)
    if erros_mapa:
        print("\n" + "="*80)
        print("AVISO: Inconsistência nas referências de mapa:")
        for e in erros_mapa:
            print("  " + e)
        print("="*80 + "\n")

    # 3.3. Injeta precomputados
    injetar_precomputados(croqui_data)

    # 4. Injeta metadados extras (ex: checksums de imagens)
    if dados_extras:
        croqui_data.update(dados_extras)

    # 4. Garante diretórios de saída
    if destino_yaml:
        destino_yaml.parent.mkdir(parents=True, exist_ok=True)
    destino_binarypb.parent.mkdir(parents=True, exist_ok=True)

    # 5. Salva compilado.yaml
    if destino_yaml:
        with open(destino_yaml, "w", encoding="utf-8") as f:
            yaml.dump(croqui_data, f, allow_unicode=True, sort_keys=False)

    # 6. Salva compilado.binarypb
    croqui_msg = croqui_pb2.Croqui()
    try:
        json_format.ParseDict(croqui_data, croqui_msg, ignore_unknown_fields=False)
    except Exception as e:
        # Tenta extrair uma mensagem mais amigável do erro de validação
        err_msg = str(e)
        if "Failed to parse" in err_msg or "has no field named" in err_msg:
             # Erros de tipo ou campos inexistentes
             raise ValueError(f"Erro de validação Protobuf em {pico_path.name}/croqui.yaml: {err_msg}")
        raise ValueError(f"Erro de estrutura em {pico_path.name}/croqui.yaml: {err_msg}")

    try:
        with open(destino_binarypb, "wb") as f:
            f.write(croqui_msg.SerializeToString())
    except Exception as e:
        print(f"Erro ao salvar binarypb para {pico_path.name}: {e}")
        raise

    return croqui_data

if __name__ == "__main__":
    print("Este arquivo é uma biblioteca e não deve ser executado diretamente.")
    print("Use o script scripts/deploy_generated.py para processar os croquis.")
    sys.exit(1)

def garantir_comentarios_licenca(file_path: Path):
    """
    Garante que as duas linhas de comentário de licença ODbL e Copyright
    estejam presentes e corretas no topo do arquivo (YAML) ou no frontmatter (MD).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except Exception as e:
        print(f"Erro ao ler {file_path} para injetar SPDX: {e}")
        return
        
    if not linhas:
        return
        
    comentario_spdx = "# SPDX-License-Identifier: ODbL-1.0"
    comentario_copy = "# Copyright (C) 2026 Aresta Climb Contributors"
    
    # 1. Checa se o arquivo já está perfeitamente correto para evitar writes desnecessários
    if file_path.suffix == ".yaml" and len(linhas) >= 2:
        if linhas[0].strip() == comentario_spdx and linhas[1].strip() == comentario_copy:
            return
    elif file_path.suffix == ".md" and len(linhas) >= 3:
        if linhas[0].strip() == "---":
            if linhas[1].strip() == comentario_spdx and linhas[2].strip() == comentario_copy:
                return
                
    linhas_limpas = []
    
    if file_path.suffix == ".yaml":
        for i, linha in enumerate(linhas):
            if i < 15:
                l_strip = linha.strip().lower()
                if l_strip.startswith("#"):
                    if "spdx-license-identifier" in l_strip or "copyright" in l_strip:
                        continue
            linhas_limpas.append(linha)
            
    elif file_path.suffix == ".md":
        in_frontmatter = False
        if linhas[0].strip() == "---":
            in_frontmatter = True
            
        for i, linha in enumerate(linhas):
            if in_frontmatter:
                if i > 0 and linha.strip() == "---":
                    in_frontmatter = False
                
                if in_frontmatter and i > 0:
                    l_strip = linha.strip().lower()
                    if l_strip.startswith("#"):
                        if "spdx-license-identifier" in l_strip or "copyright" in l_strip:
                            continue
            linhas_limpas.append(linha)
    else:
        return
            
    comentarios = (
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
    )
    
    if file_path.suffix == ".yaml":
        linhas_limpas.insert(0, comentarios)
    elif file_path.suffix == ".md":
        if linhas_limpas[0].strip() == "---":
            linhas_limpas.insert(1, comentarios)
        else:
            return
            
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(linhas_limpas)
    except Exception as e:
        print(f"Erro ao escrever {file_path} para injetar SPDX: {e}")
