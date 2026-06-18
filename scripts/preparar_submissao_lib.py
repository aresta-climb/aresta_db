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
import re
import shutil
import yaml
import sys
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
    Varre o croqui.yaml e todos os arquivos markdown referenciados para garantir
    que imagens em raw_pdf_contents sejam migradas e os caminhos corrigidos.
    """
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
                
                if 'circular' in pt:
                    c = pt['circular']
                    for field in ['x', 'y', 'raio']:
                        if field not in c:
                            raise ValueError(f"POI '{label}' em {poi_path}: Círculo faltando campo '{field}'")
                elif 'box' in pt:
                    b = pt['box']
                    for field in ['x', 'y', 'comprimento', 'largura']:
                        if field not in b:
                            raise ValueError(f"POI '{label}' em {poi_path}: Box faltando campo '{field}'")
                    if 'angulo_graus_x100' in b:
                        ang = b['angulo_graus_x100']
                        if not (-36000 <= ang <= 36000):
                            raise ValueError(f"POI '{label}' em {poi_path}: angulo_graus_x100 ({ang}) deve estar entre -36000 e 36000")
                elif 'area_livre' in pt:
                    al = pt['area_livre']
                    if 'coordenadas' not in al:
                        raise ValueError(f"POI '{label}' em {poi_path}: Area livre faltando 'coordenadas'")
                    coords = al['coordenadas']
                    if not isinstance(coords, list) or len(coords) % 2 != 0:
                        raise ValueError(f"POI '{label}' em {poi_path}: Area livre deve ter um número par de coordenadas (x,y pairs). Encontrado {len(coords)} elementos.")
                else:
                    # Se não tem nenhum dos 3 tipos, é inválido no novo esquema
                    raise ValueError(f"POI '{label}' em {poi_path}: Tipo de área não especificado ou inválido (esperado circular, box ou area_livre)")

        # Continua a recursão em todos os campos
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                validar_pontos_de_interesse_recursivo(v, f"{path}.{k}")

def validar_referencias_mapa(croqui_data: dict) -> list[str]:
    """
    Valida se id_no_mapa, id_no_mapa_meio e id_no_mapa_fim de cada escalada
    existem em algum mapa do setor, grupo ou pico correspondente.
    Retorna uma lista de strings com descrições dos erros.
    """
    erros = []
    
    # 0. Verifica se existe PELO MENOS UM POI em todo o croqui.
    # Se não houver nenhum, pulamos a validação para evitar warnings em croquis
    # que ainda não começaram a ser processados (sem mapas/POIs).
    def tem_algum_poi_recursivo(obj):
        if isinstance(obj, list):
            return any(tem_algum_poi_recursivo(item) for item in obj)
        elif isinstance(obj, dict):
            if "pontos_de_interesse" in obj and obj["pontos_de_interesse"]:
                return True
            return any(tem_algum_poi_recursivo(v) for v in obj.values())
        return False

    if not tem_algum_poi_recursivo(croqui_data):
        return []

    def coletar_ids_de_mapas(mapas):
        ids = set()
        for mapa in mapas:
            for poi in mapa.get("pontos_de_interesse", []):
                if "id" in poi:
                    ids.add(poi["id"])
        return ids

    def validar_escalada(escalada, ids_validos, erros_contexto, ids_vistos):
        if not isinstance(escalada, dict):
            return
            
        # A escalada pode ser um de vários tipos (via_esportiva, boulder, etc)
        # Extraímos o dicionário real da escalada
        tipo_via = list(escalada.keys())[0] if escalada else None
        if not tipo_via:
            return
        
        dados_via = escalada[tipo_via]
        if not isinstance(dados_via, dict):
            return
            
        nome_via = dados_via.get("nome", "Sem Nome")
        
        id_refs = []
        has_any_id = False
        for campo in ["id_no_mapa", "id_no_mapa_meio", "id_no_mapa_fim"]:
            id_ref = dados_via.get(campo)
            if id_ref:
                has_any_id = True
                id_str = str(id_ref)
                if id_str not in ids_validos:
                    erros_contexto.append(f"Via '{nome_via}': {campo} '{id_ref}' não encontrado nos mapas.")
                id_refs.append(id_str)
            else:
                id_refs.append(None)
                
        if has_any_id:
            combo = tuple(id_refs)
            if combo in ids_vistos:
                if nome_via not in ids_vistos[combo]:
                    ids_vistos[combo].append(nome_via)
            else:
                ids_vistos[combo] = [nome_via]

        # Se for multiplas enfiadas, validar as enfiadas recursivamente
        if tipo_via == "via_multiplas_enfiadas" and "enfiadas" in dados_via:
            for e in dados_via["enfiadas"]:
                validar_escalada(e, ids_validos, erros_contexto, ids_vistos)

    def formatar_ids(ids_set):
        if not ids_set:
            return "[]"
        ids_sorted = sorted(list(ids_set))
        return "[" + ", ".join([f"'{i}'" for i in ids_sorted]) + "]"

    def processar_setor(setor, ids_pai, pico_nome, grupo_nome=None):
        setor_conteudo = setor.get("conteudo", {})
        setor_nome = setor_conteudo.get("nome", "Setor Sem Nome")
        
        if grupo_nome:
            contexto_str = f"Pico '{pico_nome}' -> Grupo '{grupo_nome}' -> Setor '{setor_nome}'"
        else:
            contexto_str = f"Pico '{pico_nome}' -> Setor '{setor_nome}'"
        
        ids_setor = coletar_ids_de_mapas(setor_conteudo.get("mapas", []))
        ids_permitidos = ids_setor | ids_pai
        
        erros_setor = []
        
        # Validação do ID do próprio setor no mapa pai (pico ou grupo)
        id_setor = setor_conteudo.get("id_no_mapa")
        if id_setor and str(id_setor) not in ids_pai:
             erros_setor.append(f"Setor '{setor_nome}': id_no_mapa '{id_setor}' não encontrado nos mapas superiores.")

        ids_vistos = {}
        for esc in setor_conteudo.get("escaladas", []):
            validar_escalada(esc, ids_permitidos, erros_setor, ids_vistos)

        for combo, nomes in ids_vistos.items():
            if len(nomes) > 1:
                nomes_str = ", ".join(nomes)
                combo_str = ", ".join([str(x) for x in combo if x is not None])
                erros_setor.append(f"A combinação de IDs de mapa ({combo_str}) está duplicada e sendo usada pelas escaladas: {nomes_str}.")
            
        if erros_setor:
            erros.append(f"- {contexto_str}:")
            for e in erros_setor:
                erros.append(f"    * {e}")
            erros.append(f"    * IDs de mapa disponíveis no contexto: {formatar_ids(ids_permitidos)}")

    def processar_setores_ou_grupos(setores_ou_grupos, ids_pico, pico_nome):
        ids_vistos_pico = {}
        for item in setores_ou_grupos:
            if "setor" in item:
                processar_setor(item["setor"], ids_pico, pico_nome)
                
                setor_conteudo = item["setor"].get("conteudo", {})
                id_setor = setor_conteudo.get("id_no_mapa")
                nome_setor = setor_conteudo.get("nome", "Setor Sem Nome")
                if id_setor:
                    id_str = str(id_setor)
                    item_nome = f"Setor '{nome_setor}'"
                    if id_str in ids_vistos_pico:
                        ids_vistos_pico[id_str].append(item_nome)
                    else:
                        ids_vistos_pico[id_str] = [item_nome]

            elif "grupo" in item:
                grupo_conteudo = item["grupo"].get("conteudo", {})
                grupo_nome = grupo_conteudo.get("nome", "Grupo Sem Nome")
                ids_grupo = coletar_ids_de_mapas(grupo_conteudo.get("mapas", []))
                ids_contexto_grupo = ids_grupo | ids_pico
                
                erros_grupo = []
                id_grupo = grupo_conteudo.get("id_no_mapa")
                if id_grupo:
                    id_str = str(id_grupo)
                    if id_str not in ids_pico:
                        erros_grupo.append(f"Grupo '{grupo_nome}': id_no_mapa '{id_grupo}' não encontrado nos mapas do pico.")
                    
                    item_nome = f"Grupo '{grupo_nome}'"
                    if id_str in ids_vistos_pico:
                        ids_vistos_pico[id_str].append(item_nome)
                    else:
                        ids_vistos_pico[id_str] = [item_nome]
                
                ids_vistos_grupo = {}
                # Processar setores dentro do grupo
                for s_ref in grupo_conteudo.get("setores", []):
                    processar_setor(s_ref, ids_contexto_grupo, pico_nome, grupo_nome)
                    
                    setor_conteudo = s_ref.get("conteudo", {})
                    id_setor = setor_conteudo.get("id_no_mapa")
                    nome_setor = setor_conteudo.get("nome", "Setor Sem Nome")
                    if id_setor:
                        id_str = str(id_setor)
                        item_nome = f"Setor '{nome_setor}'"
                        if id_str in ids_vistos_grupo:
                            ids_vistos_grupo[id_str].append(item_nome)
                        else:
                            ids_vistos_grupo[id_str] = [item_nome]

                for id_str, nomes in ids_vistos_grupo.items():
                    if len(nomes) > 1:
                        nomes_str = ", ".join(nomes)
                        erros_grupo.append(f"O id_no_mapa '{id_str}' está duplicado e sendo usado por: {nomes_str}.")

                if erros_grupo:
                    erros.append(f"- Pico '{pico_nome}' -> Grupo '{grupo_nome}':")
                    for e in erros_grupo:
                        erros.append(f"    * {e}")
                    erros.append(f"    * IDs de mapa disponíveis no contexto: {formatar_ids(ids_pico)}")

        erros_pico = []
        for id_str, nomes in ids_vistos_pico.items():
            if len(nomes) > 1:
                nomes_str = ", ".join(nomes)
                erros_pico.append(f"O id_no_mapa '{id_str}' está duplicado e sendo usado por: {nomes_str}.")
        
        if erros_pico:
            erros.append(f"- Pico '{pico_nome}':")
            for e in erros_pico:
                erros.append(f"    * {e}")

    for pico in croqui_data.get("picos", []):
        pico_nome = pico.get("nome", "Pico Sem Nome")
        ids_pico = coletar_ids_de_mapas(pico.get("mapas", []))
        if "setores_ou_grupos" in pico:
            processar_setores_ou_grupos(pico["setores_ou_grupos"], ids_pico, pico_nome)

    return erros

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

    # 3. Atualiza dimensões de mapas automaticamente
    atualizar_dimensoes_mapas(croqui_data, pico_path)

    # 3.1 Valida pontos de interesse conforme novas regras
    validar_pontos_de_interesse_recursivo(croqui_data, pico_path.name)

    # 3.2 Valida referências de IDs no mapa (apenas avisos, não impede compilação)
    erros_mapa = validar_referencias_mapa(croqui_data)
    if erros_mapa:
        print("\n  AVISO: Inconsistência de IDs nos mapas:")
        for e in erros_mapa:
            print(f"    {e}")
        print("")

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

if __name__ == "__main__":
    print("Este arquivo é uma biblioteca e não deve ser executado diretamente.")
    print("Use o script scripts/deploy_generated.py para processar os croquis.")
    sys.exit(1)
