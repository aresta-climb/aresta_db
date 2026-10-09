# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Dict, Any, List, Tuple, Set, Union
import os
import re
import shutil
import time
import yaml
import sys

# ===========================================================================
# PYAML CONFIGURATION
# ===========================================================================
# O PyYAML 1.1 interpreta '08' e '09' como strings automaticamente porque não são octais válidos.
# Porém, ao fazer o dump, ele decide remover as aspas por achar que são strings seguras.
# Para manter a formatação visual (e compatibilidade com YAML 1.2), forçamos as aspas
# em qualquer string que seja composta puramente de dígitos.
def _str_representer(dumper: Any, data: str) -> Any:
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

from aresta_api.proto.generated import croqui_pb2
from scripts.gerenciar_uids_lib import validar_uid
from editor.core.processamento_imagem_campo import (
    AREA_MAXIMA_ESCALADA,
    AREA_MAXIMA_PADRAO,
    QUALIDADE_WEBP_ESCALADA,
    QUALIDADE_WEBP_PADRAO,
    comprimir_imagem_para_bytes_webp,
)

# ===========================================================================
# UTILITÁRIOS DE PROCESSAMENTO DE TEXTO E IMAGEM
# ===========================================================================

def parse_md_com_frontmatter(caminho_arquivo: Union[str, Path]) -> Tuple[Optional[Dict[str, Any]], str]:
    """Lê um arquivo Markdown e separa o YAML Frontmatter do conteúdo."""
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as f:
            conteudo = f.read()
    except Exception as e:
        raise RuntimeError(f"Erro ao ler arquivo: {caminho_arquivo}. Erro: {e}")
    
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", conteudo, re.DOTALL)
    if match:
        try:
            frontmatter: Optional[Dict[str, Any]] = yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            raise ValueError(f"Erro de YAML no frontmatter de {caminho_arquivo}:\n{e}")
        corpo = match.group(2).strip()
        return frontmatter, corpo
    return None, conteudo.strip()


def processar_caminho_imagem(
    caminho_img_original: str,
    pico_path: Path,
    eh_escalada: bool = False,
) -> str:
    """
    Processa um caminho de imagem original, comprime para a pasta de destino com nome único
    respeitando o perfil da entidade (1.0 MP @ Q85 para escalada, 2.5 MP @ Q85 para setor/grupo)
    e retorna o novo caminho relativo.
    """
    caminho_img_original = caminho_img_original.replace("\\", "/")
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
    
    max_area = AREA_MAXIMA_ESCALADA if eh_escalada else AREA_MAXIMA_PADRAO
    quality = QUALIDADE_WEBP_ESCALADA if eh_escalada else QUALIDADE_WEBP_PADRAO

    try:
        bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(
            src,
            quality=quality,
            max_area=max_area,
        )
        dest.write_bytes(bytes_webp)
    except Exception as e:
        print(f"    Aviso: Falha ao comprimir imagem {src}, recorrendo a cópia direta: {e}")
        shutil.copy2(src, dest)

    return f"imagens/{novo_nome_arquivo}"

def integrar_metadados_mapa(mapa: Dict[str, Any], pico_path: Path) -> bool:
    """
    Se a imagem do mapa estiver em raw_pdf_contents, procura um arquivo .json
    correspondente e preenche largura_mapa, altura_mapa e pontos_de_interesse.
    """
    img_path_str = mapa.get("caminho_imagem_mapa")
    if not img_path_str:
        return False
    img_path_str = img_path_str.replace("\\", "/")
    if "raw_pdf_contents/imagens" not in img_path_str:
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

def coletar_e_atualizar_imagens(texto: str, pico_path: Path) -> str:
    """Encontra imagens no estilo markdown e as processa usando a função utility."""
    md_imgs = re.findall(r"!\[.*?\]\((.*?)\)", texto)
    
    novo_texto = texto
    for img_path_str in md_imgs:
        novo_caminho = processar_caminho_imagem(img_path_str, pico_path)
        if novo_caminho != img_path_str:
            novo_texto = novo_texto.replace(img_path_str, novo_caminho)
    
    return novo_texto

def salvar_md_com_frontmatter(md_path: Path, frontmatter: Optional[Dict[str, Any]], corpo: str) -> None:
    """Salva o YAML Frontmatter e o corpo de volta no arquivo markdown."""
    with open(md_path, "w", encoding="utf-8") as f:
        if frontmatter:
            f.write(
                "---\n"
                "# SPDX-License-Identifier: ODbL-1.0\n"
                "# Copyright (C) 2026 Aresta Climb Contributors\n"
                + yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
                + "---\n\n"
            )
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

def converter_coordenadas_e7_recursivo(obj: Any) -> bool:
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
            def to_e7(val: Any) -> Tuple[Any, bool]:
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

def mover_descricao_para_corpo(frontmatter: Optional[Dict[str, Any]], corpo: str) -> Tuple[Optional[Dict[str, Any]], str, bool]:
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

def desduplicar_referencias_no_md(md_path: Path, pico_path: Path) -> None:

    """
    Checa se o mesmo arquivo .md possui a mesma imagem referenciada em mais de um local.
    Caso isso aconteça, duplica a imagem física e atualiza o Markdown para que possam ser editadas individualmente.
    """
    frontmatter, corpo = parse_md_com_frontmatter(md_path)
    if frontmatter is None and not corpo:
        return

    modificado = False
    contagem: Counter[str] = Counter()

    def processar_caminho(caminho_rel: Any) -> Any:
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
    def percorrer_frontmatter(obj: Any, ignorar: bool = False) -> None:
        nonlocal modificado
        if isinstance(obj, list):
            for i in range(len(obj)):
                if isinstance(obj[i], (dict, list)):
                    percorrer_frontmatter(obj[i], ignorar=ignorar)
                elif isinstance(obj[i], str) and obj[i].startswith("imagens/"):
                    # Não costuma ter string pura com imagens/ na lista, mas por garantia
                    pass
        elif isinstance(obj, dict):
            # Recorre em todos os campos, mas ignora escaladas/vias para desduplicação
            for k, v in obj.items():
                ignorar_filho = ignorar or k in ("escaladas", "vias")
                if not ignorar and k in ("caminho_imagem_mapa", "caminho_imagem_capa"):
                    original = v
                    novo = processar_caminho(original)
                    if novo != original:
                        obj[k] = novo
                        modificado = True
                elif isinstance(v, (dict, list)):
                    percorrer_frontmatter(v, ignorar=ignorar_filho)

    if frontmatter:
        percorrer_frontmatter(frontmatter)

    # 2. Processar Corpo (Regex para substituir um por um)
    def substituidor_corpo(match: re.Match[str]) -> str:
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

def processar_croqui_yaml(croqui_data: Dict[str, Any], pico_path: Path, croqui_yaml_path: Path) -> None:
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

    from scripts.migrador import obter_ultima_versao_migracao
    versao_maxima = obter_ultima_versao_migracao()
    if versao_maxima > 0 and croqui_data.get("ultima_migracao", 0) < versao_maxima:
        croqui_data["ultima_migracao"] = versao_maxima
        modificado_yaml = True

    if modificado_yaml:
        with open(croqui_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(croqui_data, f, allow_unicode=True, sort_keys=False)

def corrigir_setores_ou_grupos_recursivo(setores_ou_grupos_raw: List[Any], pico_path: Path) -> None:
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
            
            if frontmatter is None:
                frontmatter = {}

            # 1. Move descricao para o corpo (se existir)
            frontmatter_atualizado, corpo, modificado_desc = mover_descricao_para_corpo(frontmatter, corpo)
            frontmatter = frontmatter_atualizado or {}

            # 2. Corrige imagens no corpo do MD
            novo_corpo = coletar_e_atualizar_imagens(corpo, pico_path)
            modificado = (corpo != novo_corpo) or modificado_desc
            
            # 2. Corrige imagens dos mapas no frontmatter
            if "mapas" in frontmatter and isinstance(frontmatter["mapas"], list):
                for mapa in frontmatter["mapas"]:
                    if isinstance(mapa, dict) and "caminho_imagem_mapa" in mapa:
                        img_original = mapa["caminho_imagem_mapa"]
                        
                        # Tenta integrar metadados antes de mudar o caminho
                        if integrar_metadados_mapa(mapa, pico_path):
                            modificado = True
                            
                        novo_caminho_img = processar_caminho_imagem(img_original, pico_path)
                        if novo_caminho_img != img_original:
                            mapa["caminho_imagem_mapa"] = novo_caminho_img
                            modificado = True

            # 2.1 Corrige imagens de mapas em escaladas/vias no frontmatter
            for key in ["escaladas", "vias"]:
                if key in frontmatter and isinstance(frontmatter[key], list):
                    for via in frontmatter[key]:
                        if not via or not isinstance(via, dict):
                            continue
                        mapas_lista = via.get("mapas")
                        if not mapas_lista and "via_multiplas_enfiadas" in via and isinstance(via["via_multiplas_enfiadas"], dict):
                            mapas_lista = via["via_multiplas_enfiadas"].get("mapas")
                        if mapas_lista and isinstance(mapas_lista, list):
                            for mapa in mapas_lista:
                                if isinstance(mapa, dict):
                                    if "pontos_de_interesse" in mapa:
                                        del mapa["pontos_de_interesse"]
                                        modificado = True
                                    if "caminho_imagem_mapa" in mapa:
                                        img_original = mapa["caminho_imagem_mapa"]
                                        novo_caminho_img = processar_caminho_imagem(img_original, pico_path, eh_escalada=True)
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

def corrigir_arquivo_setor_recursivo(setores_raw: List[Any], pico_path: Path) -> None:
    """Auxiliar para corrigir uma lista de ArquivoSetor (usado dentro de Grupos)."""
    # Embrulha cada ArquivoSetor como um SetorOuGrupo fake para reusar a lógica
    fake_setores_ou_grupos = [{"setor": s} for s in setores_raw]
    corrigir_setores_ou_grupos_recursivo(fake_setores_ou_grupos, pico_path)

def corrigir_mapas_gerais(mapas_gerais_raw: Dict[str, Any], pico_path: Path) -> bool:
    """
    Percorre mapas gerais corrigindo imagens (migrando de raw_pdf_contents),
    integrando metadados e convertendo coordenadas.
    Retorna True se houve modificações inline no YAML que precisam ser salvas.
    """
    if not mapas_gerais_raw or not isinstance(mapas_gerais_raw, dict):
        return False

    modificado_yaml = False

    if "caminho" in mapas_gerais_raw and isinstance(mapas_gerais_raw["caminho"], str):
        md_path = pico_path / mapas_gerais_raw["caminho"]
        if md_path.exists():
            frontmatter, corpo = parse_md_com_frontmatter(md_path)
            if frontmatter is None:
                frontmatter = {}

            # 1. Move descricao para o corpo (se existir)
            frontmatter_atualizado, corpo, modificado_desc = mover_descricao_para_corpo(frontmatter, corpo)
            frontmatter = frontmatter_atualizado or {}

            # 2. Corrige imagens no corpo do MD se houver
            novo_corpo = coletar_e_atualizar_imagens(corpo, pico_path)
            modificado = (corpo != novo_corpo) or modificado_desc

            # 3. Corrige imagens dos mapas no frontmatter
            if "mapas" in frontmatter and isinstance(frontmatter["mapas"], list):
                for mapa in frontmatter["mapas"]:
                    if isinstance(mapa, dict) and "caminho_imagem_mapa" in mapa:
                        img_original = mapa["caminho_imagem_mapa"]

                        # Tenta integrar metadados antes de mudar o caminho
                        if integrar_metadados_mapa(mapa, pico_path):
                            modificado = True

                        novo_caminho_img = processar_caminho_imagem(img_original, pico_path)
                        if novo_caminho_img != img_original:
                            mapa["caminho_imagem_mapa"] = novo_caminho_img
                            modificado = True

            # 4. Converte coordenadas para E7 no frontmatter
            if converter_coordenadas_e7_recursivo(frontmatter):
                modificado = True

            if modificado:
                salvar_md_com_frontmatter(md_path, frontmatter, novo_corpo)

            # 5. Desduplica referências no arquivo MD
            desduplicar_referencias_no_md(md_path, pico_path)

    else:
        # Caso estruturado diretamente inline no YAML
        conteudo = mapas_gerais_raw.get("conteudo") if "conteudo" in mapas_gerais_raw else mapas_gerais_raw
        if isinstance(conteudo, dict):
            mapas_lista = conteudo.get("mapas")
            if isinstance(mapas_lista, list):
                for mapa in mapas_lista:
                    if isinstance(mapa, dict) and "caminho_imagem_mapa" in mapa:
                        img_original = mapa["caminho_imagem_mapa"]

                        if integrar_metadados_mapa(mapa, pico_path):
                            modificado_yaml = True

                        novo_caminho_img = processar_caminho_imagem(img_original, pico_path)
                        if novo_caminho_img != img_original:
                            mapa["caminho_imagem_mapa"] = novo_caminho_img
                            modificado_yaml = True

            if converter_coordenadas_e7_recursivo(conteudo):
                modificado_yaml = True

    return modificado_yaml


def coletar_referencias_arquivos(pico_path: Path, croqui_data: Dict[str, Any]) -> Set[str]:
    """Coleta referências a arquivos (imagens, anexos e md) existentes no croqui."""
    referencias: Set[str] = set()
    md_visitados: Set[str] = set()

    def adicionar_referencia_imagem(caminho_img: str) -> None:
        caminho_norm = caminho_img.replace("\\", "/").strip()
        if not caminho_norm:
            return
        referencias.add(caminho_norm)
        if not caminho_norm.startswith("imagens/") and any(
            caminho_norm.lower().endswith(ext)
            for ext in (".webp", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".heic", ".heif")
        ):
            referencias.add(f"imagens/{caminho_norm}")

    def adicionar_referencia_anexo(caminho_anexo: str) -> None:
        caminho_norm = caminho_anexo.replace("\\", "/").strip()
        if not caminho_norm or "://" in caminho_norm or caminho_norm.startswith("mailto:"):
            return
        referencias.add(caminho_norm)
        if not caminho_norm.startswith("anexos/"):
            referencias.add(f"anexos/{caminho_norm}")

    def extrair_links_markdown(texto: str) -> None:
        for match in re.findall(r"!\[.*?\]\((.*?)\)", texto):
            adicionar_referencia_imagem(match)
        for match in re.findall(r"\[.*?\]\((.*?)\)", texto):
            caminho_link = match.strip()
            if caminho_link.startswith("anexos/"):
                adicionar_referencia_anexo(caminho_link)
            elif caminho_link.startswith("imagens/"):
                adicionar_referencia_imagem(caminho_link)

    def processar_md(caminho_rel: str) -> None:
        caminho_norm = caminho_rel.replace("\\", "/").strip()
        if caminho_norm in md_visitados:
            return
        md_visitados.add(caminho_norm)
        referencias.add(caminho_norm)
        md_path = pico_path / caminho_norm
        if md_path.exists():
            frontmatter, corpo = parse_md_com_frontmatter(md_path)
            extrair_links_markdown(corpo)
            if frontmatter:
                varrer_objeto(frontmatter)

    def varrer_objeto(obj: Any) -> None:
        if isinstance(obj, str):
            extrair_links_markdown(obj)
        elif isinstance(obj, dict):
            if "caminho" in obj and isinstance(obj["caminho"], str) and obj["caminho"].endswith(".md"):
                processar_md(obj["caminho"])
            for k, v in obj.items():
                if k in ("caminho_imagem_mapa", "caminho_thumbnail", "caminho_imagem", "caminho_imagem_capa") and isinstance(v, str):
                    adicionar_referencia_imagem(v)
                elif k in ("caminho_anexo", "anexo") and isinstance(v, str):
                    adicionar_referencia_anexo(v)
                else:
                    varrer_objeto(v)
        elif isinstance(obj, list):
            for item in obj:
                varrer_objeto(item)

    varrer_objeto(croqui_data)

    # Filtra e normaliza: apenas referências que apontam para imagens/, anexos/ ou .md
    return {
        ref.replace("\\", "/").strip()
        for ref in referencias
        if isinstance(ref, str)
        and (
            ref.replace("\\", "/").strip().startswith("imagens/")
            or ref.replace("\\", "/").strip().startswith("anexos/")
            or ref.replace("\\", "/").strip().endswith(".md")
        )
    }

def limpar_arquivos_nao_utilizados(pico_path: Path, croqui_data: Dict[str, Any]) -> None:
    """Deleta arquivos (imagens, anexos e markdowns) que não possuem referências nos metadados."""
    pasta_imagens = pico_path / "imagens"
    pasta_anexos = pico_path / "anexos"
    
    referencias = coletar_referencias_arquivos(pico_path, croqui_data)
    
    # Arquivos físicos na pasta imagens/ (ignora subdiretórios)
    arquivos_fisicos: Set[str] = set()
    if pasta_imagens.exists():
        arquivos_fisicos.update(f"imagens/{f.name}" for f in pasta_imagens.iterdir() if f.is_file())

    # Arquivos físicos na pasta anexos/ (suporta arquivos diretos e subdiretórios)
    if pasta_anexos.exists():
        arquivos_fisicos.update(
            f"anexos/{f.relative_to(pasta_anexos).as_posix()}"
            for f in pasta_anexos.rglob("*")
            if f.is_file()
        )
        
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

        # Se subdiretórios ou a pasta anexos ficarem vazios, remove diretórios vazios
        if pasta_anexos.exists():
            for subpasta in sorted(pasta_anexos.glob("**/*"), key=lambda p: len(p.parts), reverse=True):
                if subpasta.is_dir() and not any(subpasta.iterdir()):
                    try:
                        subpasta.rmdir()
                    except OSError:
                        pass
            if not any(pasta_anexos.iterdir()):
                try:
                    pasta_anexos.rmdir()
                except OSError:
                    pass

def _obter_snapshot_arquivos_croqui(pico_path: Path) -> Dict[str, Tuple[int, int]]:
    """Captura o estado dos arquivos do croqui (caminho_relativo -> (tamanho, mtime_ns))."""
    snapshot = {}
    if pico_path.exists():
        for arq in pico_path.rglob("*"):
            if arq.is_file():
                try:
                    st = arq.stat()
                    snapshot[arq.relative_to(pico_path).as_posix()] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    pass
    return snapshot


def _extrair_nome_escalada(escalada: Dict[str, Any]) -> str:
    """Extrai o nome de uma escalada suportando modelo plano ou polimórfico."""
    if not isinstance(escalada, dict):
        return ""
    if "nome" in escalada and isinstance(escalada["nome"], str):
        return escalada["nome"].strip()
    for subtipo in (
        "via_esportiva",
        "via_movel",
        "via_tradicional",
        "boulder",
        "via_psicobloc",
        "via_artificial",
        "highline",
        "via_multiplas_enfiadas",
    ):
        conteudo_sub = escalada.get(subtipo)
        if isinstance(conteudo_sub, dict) and "nome" in conteudo_sub:
            return str(conteudo_sub.get("nome", "")).strip()
    for k, v in escalada.items():
        if k not in ("uid", "betas", "mapas") and isinstance(v, dict) and "nome" in v:
            return str(v.get("nome", "")).strip()
    return ""


def auditar_uids_database(pico_path: Path, croqui_data: Dict[str, Any]) -> None:
    """
    Audita e valida que todas as entidades do banco de dados (Croqui, Picos/Grupos/Setores,
    Escaladas e Pontos de Interesse) possuem UIDs válidos de 14 caracteres Base62.
    Lança ValueError caso qualquer entidade possua UID ausente ou inválido.
    """
    croqui_uid = croqui_data.get("uid")
    if not validar_uid(croqui_uid):
        raise ValueError(
            f"Croqui em {pico_path.name} possui UID ausente ou inválido: '{croqui_uid}'. "
            f"Esperado NanoID de 14 caracteres Base62."
        )

    for botao in croqui_data.get("botoes", []):
        if isinstance(botao, dict):
            b_uid = botao.get("uid")
            if not validar_uid(b_uid):
                texto_btn = botao.get("texto", "Sem Texto")
                raise ValueError(
                    f"Botão '{texto_btn}' no croqui '{pico_path.name}' possui UID ausente ou inválido: '{b_uid}'"
                )

    for pico in croqui_data.get("picos", []):
        pico_nome = pico.get("nome", "Pico Sem Nome")
        mapas_pico: List[Dict[str, Any]] = []
        if "mapas" in pico and isinstance(pico["mapas"], list):
            mapas_pico.extend(pico["mapas"])
        if "mapas_gerais" in pico:
            mg = pico["mapas_gerais"]
            if isinstance(mg, dict):
                conteudo = mg.get("conteudo") if "conteudo" in mg else mg
                if isinstance(conteudo, dict) and "mapas" in conteudo and isinstance(conteudo["mapas"], list):
                    mapas_pico.extend(conteudo["mapas"])

        for mapa in mapas_pico:
            if isinstance(mapa, dict):
                for poi in mapa.get("pontos_de_interesse", []):
                    if isinstance(poi, dict):
                        p_uid = poi.get("uid")
                        if not validar_uid(p_uid):
                            raise ValueError(
                                f"Ponto de interesse '{poi.get('id')}' no pico '{pico_nome}' possui UID ausente ou inválido: '{p_uid}'"
                            )

        def _auditar_entidade(obj_ref: Dict[str, Any], tipo: str) -> None:
            dados = None
            origem = ""
            if "caminho" in obj_ref and isinstance(obj_ref["caminho"], str):
                md_path = pico_path / obj_ref["caminho"]
                origem = md_path.name
                if md_path.exists():
                    fm, _ = parse_md_com_frontmatter(md_path)
                    dados = fm or {}
            elif "conteudo" in obj_ref:
                dados = obj_ref["conteudo"]
                origem = f"conteudo inline ({tipo})"
            elif isinstance(obj_ref, dict):
                dados = obj_ref
                origem = f"objeto inline ({tipo})"

            if not dados or not isinstance(dados, dict):
                return

            ent_uid = dados.get("uid")
            if not validar_uid(ent_uid):
                nome_ent = dados.get("nome", "Sem Nome")
                raise ValueError(
                    f"Entidade '{nome_ent}' em {origem} possui UID ausente ou inválido: '{ent_uid}'"
                )

            for esc in dados.get("escaladas", []):
                if isinstance(esc, dict):
                    esc_uid = esc.get("uid")
                    if not validar_uid(esc_uid):
                        nome_esc = _extrair_nome_escalada(esc) or "Sem Nome"
                        raise ValueError(
                            f"Escalada '{nome_esc}' em {origem} possui UID ausente ou inválido: '{esc_uid}'"
                        )

            for mapa in dados.get("mapas", []):
                if isinstance(mapa, dict):
                    for poi in mapa.get("pontos_de_interesse", []):
                        if isinstance(poi, dict):
                            poi_uid = poi.get("uid")
                            if not validar_uid(poi_uid):
                                raise ValueError(
                                    f"Ponto de interesse '{poi.get('id')}' em {origem} possui UID ausente ou inválido: '{poi_uid}'"
                                )

            filhos = dados.get("setores") or dados.get("sub_setores") or []
            for f in filhos:
                f_ref = {"caminho": f} if isinstance(f, str) else f
                _auditar_entidade(f_ref, "setor")

        for sg in pico.get("setores_ou_grupos", []):
            if not isinstance(sg, dict):
                continue
            tipo = "setor" if "setor" in sg else "grupo"
            obj = sg.get(tipo, {})
            _auditar_entidade(obj, tipo)


def sanear_uids_database(pico_path: Path) -> None:
    """Executa o saneamento contínuo e idempotente de UIDs e referências de mapas.

    Garante que todas as entidades (Croqui, Grupo, Setor, Escalada, PontoDeInteresse e Botao)
    possuam NanoIDs 14c Base62 válidos, que labels legados sejam convertidos para rotulo,
    e que referências semânticas textuais (escalada/setor/grupo) sejam convertidas para alvo_uid/pontos_uids,
    preservando integralmente os UIDs pré-existentes.
    """
    from scripts.gerenciar_uids_lib import sanear_uids_croqui
    sanear_uids_croqui(pico_path)


def corrigir_database(pico_path: Path) -> bool:
    """
    Função principal que coordena o processamento do database para garantir
    que imagens em raw_pdf_contents sejam migradas e os caminhos corrigidos.
    Retorna True se qualquer arquivo do database foi criado, modificado, movido ou excluído.
    """
    pico_path = Path(pico_path)
    snapshot_antes = _obter_snapshot_arquivos_croqui(pico_path)

    # Executa o motor de migrações no início da rotina de correção
    from scripts.migrador import aplicar_migracoes
    aplicar_migracoes(pico_path)

    # Saneamento contínuo e idempotente de UIDs e referências para novos rascunhos e entidades
    sanear_uids_database(pico_path)

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

    # 3. Corrige imagens nos setores ou grupos de cada pico e mapas gerais
    yaml_modificado = False
    for pico in croqui_data.get("picos", []):
        if "mapas_gerais" in pico:
            if corrigir_mapas_gerais(pico["mapas_gerais"], pico_path):
                yaml_modificado = True
        if "setores_ou_grupos" in pico:
            corrigir_setores_ou_grupos_recursivo(pico["setores_ou_grupos"], pico_path)

    if yaml_modificado:
        with open(croqui_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(croqui_data, f, allow_unicode=True, sort_keys=False)

    # 4. Limpeza de imagens órfãs
    limpar_arquivos_nao_utilizados(pico_path, croqui_data)

    # 5. Garante comentário SPDX e Copyright em todos os arquivos
    for file_path in pico_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".yaml", ".md"]:
            garantir_comentarios_licenca(file_path)

    # 6. Audita e valida integridade de UIDs em todas as entidades
    auditar_uids_database(pico_path, croqui_data)

    snapshot_depois = _obter_snapshot_arquivos_croqui(pico_path)
    return snapshot_antes != snapshot_depois


# ===========================================================================
# FASE 2: COMPILAÇÃO DE ARTEFATOS (GENERATED)
# ===========================================================================

def expandir_arquivo_generico(
    obj_ref: Dict[str, Any],
    pico_path: Path,
    tipo_esperado: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Expande um objeto que pode ser Setor ou Grupo.
    Retorna (tipo, dados_expandidos) onde tipo é 'setor' ou 'grupo'.
    dados_expandidos é um dict com 'conteudo' ou 'caminho' (compatível com ArquivoSetor/ArquivoGrupo).
    """
    if "caminho" in obj_ref:
        md_path = pico_path / obj_ref["caminho"]
        frontmatter, corpo = parse_md_com_frontmatter(md_path)
        if not frontmatter: frontmatter = {}

        if tipo_esperado == "grupo":
            eh_grupo = True
        elif tipo_esperado == "setor":
            eh_grupo = False
        else:
            eh_grupo = ("setores" in frontmatter) or ("sub_setores" in frontmatter)
        
        if eh_grupo:
            # É um Grupo
            # Grupos só podem ter setores filhos (ArquivoSetor)
            # Filtra eventuais nulos na lista de filhos
            filhos = frontmatter.get("setores") or frontmatter.get("sub_setores") or []
            setores_expandidos = []
            for s in filhos:
                if not s: continue
                # Se s é string, converte para dict com caminho
                s_ref = {"caminho": s} if isinstance(s, str) else s
                _, dados = expandir_arquivo_generico(
                    s_ref if "caminho" in s_ref else {"conteudo": s_ref.get("conteudo")},
                    pico_path,
                    tipo_esperado="setor"
                )
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
        if tipo_esperado == "grupo":
            eh_grupo = True
        elif tipo_esperado == "setor":
            eh_grupo = False
        else:
            eh_grupo = ("setores" in conteudo) or ("sub_setores" in conteudo)

        if eh_grupo:
            # É um Grupo
            filhos = conteudo.get("setores") or conteudo.get("sub_setores") or []
            setores_expandidos = []
            for s in filhos:
                if not s: continue
                s_ref = {"caminho": s} if isinstance(s, str) else s
                _, dados = expandir_arquivo_generico(
                    s_ref if "caminho" in s_ref else {"conteudo": s_ref.get("conteudo")},
                    pico_path,
                    tipo_esperado="setor"
                )
                setores_expandidos.append(dados)
            
            conteudo["setores"] = setores_expandidos
            if "sub_setores" in conteudo: del conteudo["sub_setores"]
            return "grupo", obj_ref
        else:
            # É um Setor
            return "setor", obj_ref

def expandir_setores_ou_grupos_recursivo(setores_ou_grupos_raw: List[Any], pico_path: Path) -> List[Dict[str, Any]]:
    """Expande o conteúdo de arquivos MD em objetos estruturados (Setor ou Grupo)."""
    processados: List[Dict[str, Any]] = []
    for e_ref in setores_ou_grupos_raw:
        # Tenta identificar se é setor ou grupo no input do YAML
        tipo_in = "setor" if "setor" in e_ref else "grupo"
        obj_ref = e_ref.get(tipo_in)
        if not obj_ref: continue

        tipo_out, dados = expandir_arquivo_generico(obj_ref, pico_path, tipo_esperado=tipo_in)
        processados.append({tipo_out: dados})

    return processados

def atualizar_dimensoes_mapas(obj: Any, pico_path: Path) -> None:
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

def validar_pontos_de_interesse_recursivo(obj: Any, path: str = "") -> None:
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
                poi_id = str(pt.get("uid") or pt.get("id") or "").strip()
                if not poi_id:
                    raise ValueError(f"Ponto de interesse em {poi_path}: campo obrigatório 'uid' (ou 'id') não informado ou vazio")

                label = pt.get('rotulo') or pt.get('label') or poi_id
                
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
                elif 'linha' in pt:
                    linha = pt['linha']
                    if 'conteudo' in linha:
                        conteudo = linha['conteudo']
                        nos = conteudo.get('nos', [])
                        if not isinstance(nos, list) or len(nos) < 2:
                            raise ValueError(f"POI '{label}' em {poi_path}: Linha deve conter pelo menos 2 nós em 'conteudo.nos'")
                    elif 'compilado' in linha:
                        compilado = linha['compilado']
                        if 'caminho_svg' not in compilado:
                            raise ValueError(f"POI '{label}' em {poi_path}: Linha compilada faltando 'caminho_svg'")
                    else:
                        raise ValueError(f"POI '{label}' em {poi_path}: Linha faltando 'conteudo' ou 'compilado'")
                else:
                    # Se não tem nenhum dos 5 tipos, é inválido no novo esquema
                    raise ValueError(f"POI '{label}' em {poi_path}: Tipo de área não especificado ou inválido (esperado circulo, quadrado, retangulo, poligono ou linha)")

        # Continua a recursão em todos os campos
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                validar_pontos_de_interesse_recursivo(v, f"{path}.{k}")


def preencher_compatibilidade_legada_em_memoria(croqui_data: Dict[str, Any]) -> None:
    """
    Percorre croqui_data preenchendo em memória:
    1. Campos legados em referências de mapa (escalada, setor, grupo, ids) a partir de alvo_uid e pontos_uids.
    2. Campo legado label em pontos de interesse a partir de rotulo (e vice-versa).
    3. alvo_uid e pontos_uids em referências caso venham de fontes legadas com escalada/setor/grupo/ids.
    """
    catalogo_uids: Dict[str, Tuple[str, str, Optional[str]]] = {}
    catalogo_escaladas_nome: Dict[Tuple[str, str], str] = {}
    catalogo_escaladas_simples: Dict[str, str] = {}
    catalogo_setores_nome: Dict[str, str] = {}
    catalogo_grupos_nome: Dict[str, str] = {}

    def _catalogar_escaladas(escaladas: List[Any], setor_nome: str) -> None:
        for esc in escaladas:
            if not isinstance(esc, dict):
                continue
            esc_uid = esc.get("uid", "")
            nome_esc = _extrair_nome_escalada(esc)
            if esc_uid:
                catalogo_uids[esc_uid] = ("escalada", nome_esc, setor_nome)
            if nome_esc:
                if setor_nome:
                    catalogo_escaladas_nome[(setor_nome, nome_esc)] = esc_uid
                catalogo_escaladas_simples[nome_esc] = esc_uid

    def _catalogar_setor(setor_conteudo: Dict[str, Any]) -> None:
        setor_uid = setor_conteudo.get("uid", "")
        setor_nome = setor_conteudo.get("nome", "")
        if setor_uid:
            catalogo_uids[setor_uid] = ("setor", setor_nome, None)
        if setor_nome and setor_uid:
            catalogo_setores_nome[setor_nome] = setor_uid
        _catalogar_escaladas(setor_conteudo.get("escaladas", []), setor_nome)

    for pico in croqui_data.get("picos", []):
        for sg in pico.get("setores_ou_grupos", []):
            if not isinstance(sg, dict):
                continue
            if "grupo" in sg:
                grupo_conteudo = sg["grupo"].get("conteudo") or sg["grupo"]
                grupo_uid = grupo_conteudo.get("uid", "")
                grupo_nome = grupo_conteudo.get("nome", "")
                if grupo_uid:
                    catalogo_uids[grupo_uid] = ("grupo", grupo_nome, None)
                if grupo_nome and grupo_uid:
                    catalogo_grupos_nome[grupo_nome] = grupo_uid
                for s in grupo_conteudo.get("setores", []):
                    setor_conteudo = s.get("conteudo") or s
                    _catalogar_setor(setor_conteudo)
            elif "setor" in sg:
                setor_conteudo = sg["setor"].get("conteudo") or sg["setor"]
                _catalogar_setor(setor_conteudo)

    def _processar_mapas(obj: Any) -> None:
        if isinstance(obj, list):
            for item in obj:
                _processar_mapas(item)
        elif isinstance(obj, dict):
            if "mapas" in obj and isinstance(obj["mapas"], list):
                for mapa in obj["mapas"]:
                    if not isinstance(mapa, dict):
                        continue
                    poi_uid_para_id: Dict[str, str] = {}
                    poi_id_para_uid: Dict[str, str] = {}
                    for poi in mapa.get("pontos_de_interesse", []):
                        if not isinstance(poi, dict):
                            continue
                        p_uid = str(poi.get("uid", "") or "").strip()
                        p_id = str(poi.get("id", "") or "").strip()
                        if p_uid and not p_id:
                            poi["id"] = p_uid
                            p_id = p_uid
                        elif p_id and not p_uid:
                            poi["uid"] = p_id
                            p_uid = p_id

                        if p_uid and p_id:
                            poi_uid_para_id[p_uid] = p_id
                            poi_id_para_uid[p_id] = p_uid

                        # Retrocompatibilidade rotulo <-> label
                        if "rotulo" in poi and "label" not in poi:
                            poi["label"] = str(poi["rotulo"])
                        elif "label" in poi and "rotulo" not in poi:
                            poi["rotulo"] = str(poi["label"])

                    for ref in mapa.get("referencias", []):
                        if not isinstance(ref, dict):
                            continue
                        alvo_uid = ref.get("alvo_uid")
                        if alvo_uid and alvo_uid in catalogo_uids:
                            tipo_ent, nome_ent, _ = catalogo_uids[alvo_uid]
                            if tipo_ent == "escalada" and "escalada" not in ref:
                                ref["escalada"] = nome_ent
                            elif tipo_ent == "setor" and "setor" not in ref:
                                ref["setor"] = nome_ent
                            elif tipo_ent == "grupo" and "grupo" not in ref:
                                ref["grupo"] = nome_ent
                        elif not alvo_uid:
                            if "escalada" in ref:
                                ref["alvo_uid"] = catalogo_escaladas_simples.get(ref["escalada"], "")
                            elif "setor" in ref:
                                ref["alvo_uid"] = catalogo_setores_nome.get(ref["setor"], "")
                            elif "grupo" in ref:
                                ref["alvo_uid"] = catalogo_grupos_nome.get(ref["grupo"], "")

                        # Preenche retrocompatibilidade ids <-> pontos_uids
                        if "pontos_uids" in ref and ("ids" not in ref or not ref["ids"]):
                            ref["ids"] = [poi_uid_para_id.get(puid, puid) for puid in ref["pontos_uids"]]
                        elif "ids" in ref and ("pontos_uids" not in ref or not ref["pontos_uids"]):
                            ref["pontos_uids"] = [poi_id_para_uid.get(str(pid), str(pid)) for pid in ref["ids"]]

            for v in obj.values():
                if isinstance(v, (dict, list)):
                    _processar_mapas(v)

    _processar_mapas(croqui_data)


def validar_referencias_mapa(croqui_data: Dict[str, Any]) -> List[str]:
    """
    Valida se as entidades apontadas nas referências dos mapas (escalada, setor, grupo)
    realmente existem dentro do mesmo Pico.
    Retorna uma lista de strings com descrições dos erros.
    """
    erros: List[str] = []
    
    for pico in croqui_data.get("picos", []):
        pico_nome = pico.get("nome", "Pico Sem Nome")
        
        nomes_escaladas: Set[str] = set()
        nomes_setores: Set[str] = set()
        nomes_grupos: Set[str] = set()
        uids_escaladas: Set[str] = set()
        uids_setores: Set[str] = set()
        uids_grupos: Set[str] = set()
        
        mapas_para_validar: List[Tuple[str, List[Any]]] = []
        
        if "mapas" in pico:
            mapas_para_validar.append((f"Pico '{pico_nome}'", pico["mapas"]))
        if "mapas_gerais" in pico and isinstance(pico["mapas_gerais"], dict):
            conteudo_mg = pico["mapas_gerais"].get("conteudo")
            if isinstance(conteudo_mg, dict) and "mapas" in conteudo_mg and isinstance(conteudo_mg["mapas"], list):
                mapas_para_validar.append((f"Pico '{pico_nome}' (Mapas Gerais)", conteudo_mg["mapas"]))
            elif "mapas" in pico["mapas_gerais"] and isinstance(pico["mapas_gerais"]["mapas"], list):
                mapas_para_validar.append((f"Pico '{pico_nome}' (Mapas Gerais)", pico["mapas_gerais"]["mapas"]))
            
        def registrar_escaladas(escaladas_lista: List[Any], contexto_local: str = "") -> None:
            for esc in escaladas_lista:
                if not esc or not isinstance(esc, dict):
                    continue
                if esc.get("uid"):
                    uids_escaladas.add(str(esc["uid"]).strip())

                via_nome = _extrair_nome_escalada(esc)
                if not via_nome:
                    tipo_via = [k for k in esc.keys() if k not in ("uid", "betas", "mapas")]
                    tipo_via_nome = tipo_via[0] if tipo_via else None
                    if tipo_via_nome and isinstance(esc[tipo_via_nome], dict):
                        via_nome = esc[tipo_via_nome].get("nome", "Sem Nome")
                    elif tipo_via_nome == "nome":
                        via_nome = str(esc[tipo_via_nome])
                    else:
                        via_nome = "Sem Nome"

                nomes_escaladas.add(via_nome)

                if "via_multiplas_enfiadas" in esc and isinstance(esc["via_multiplas_enfiadas"], dict):
                    enfiadas = esc["via_multiplas_enfiadas"].get("enfiadas", [])
                    for e in enfiadas:
                        if isinstance(e, dict):
                            if e.get("uid"):
                                uids_escaladas.add(str(e["uid"]).strip())
                            nome_enf = _extrair_nome_escalada(e)
                            if nome_enf:
                                nomes_escaladas.add(nome_enf)

                # Inclui mapas da escalada na validação
                if "mapas" in esc and isinstance(esc["mapas"], list):
                    mapas_para_validar.append((f"Escalada '{via_nome}' ({contexto_local})", esc["mapas"]))

        for obj_sg in pico.get("setores_ou_grupos", []):
            if "grupo" in obj_sg:
                grupo_conteudo = obj_sg["grupo"].get("conteudo") or obj_sg["grupo"]
                grupo_nome = grupo_conteudo.get("nome", "Grupo Sem Nome")
                nomes_grupos.add(grupo_nome)
                if grupo_conteudo.get("uid"):
                    uids_grupos.add(str(grupo_conteudo["uid"]).strip())
                
                if "mapas" in grupo_conteudo:
                    mapas_para_validar.append((f"Grupo '{grupo_nome}'", grupo_conteudo["mapas"]))
                    
                for obj_s in grupo_conteudo.get("setores", []):
                    setor_conteudo = obj_s.get("conteudo") or obj_s
                    setor_nome = setor_conteudo.get("nome", "Setor Sem Nome")
                    nomes_setores.add(setor_nome)
                    if setor_conteudo.get("uid"):
                        uids_setores.add(str(setor_conteudo["uid"]).strip())
                    
                    if "mapas" in setor_conteudo:
                        mapas_para_validar.append((f"Setor '{setor_nome}' (no Grupo '{grupo_nome}')", setor_conteudo["mapas"]))
                        
                    registrar_escaladas(setor_conteudo.get("escaladas", []), f"Setor '{setor_nome}' no Grupo '{grupo_nome}'")
                                
            elif "setor" in obj_sg:
                setor_conteudo = obj_sg["setor"].get("conteudo") or obj_sg["setor"]
                setor_nome = setor_conteudo.get("nome", "Setor Sem Nome")
                nomes_setores.add(setor_nome)
                if setor_conteudo.get("uid"):
                    uids_setores.add(str(setor_conteudo["uid"]).strip())
                
                if "mapas" in setor_conteudo:
                    mapas_para_validar.append((f"Setor '{setor_nome}'", setor_conteudo["mapas"]))
                    
                registrar_escaladas(setor_conteudo.get("escaladas", []), f"Setor '{setor_nome}'")

        # Validação de mapas duplicados (mesma imagem de mapa sendo exibida em múltiplos locais)
        locais_por_imagem_mapa: Dict[str, List[str]] = {}
        for contexto_nome, mapas in mapas_para_validar:
            if not isinstance(mapas, list):
                continue
            for idx_mapa, mapa in enumerate(mapas):
                if not isinstance(mapa, dict):
                    continue
                caminho_img = mapa.get("caminho_imagem_mapa")
                if caminho_img and isinstance(caminho_img, str):
                    if caminho_img not in locais_por_imagem_mapa:
                        locais_por_imagem_mapa[caminho_img] = []
                    locais_por_imagem_mapa[caminho_img].append(f"{contexto_nome} (Mapa {idx_mapa+1})")

        for caminho_img, locais in sorted(locais_por_imagem_mapa.items()):
            if len(locais) > 1:
                locais_str = ", ".join(locais)
                erros.append(
                    f"A imagem de mapa '{caminho_img}' no pico '{pico_nome}' está sendo exibida em mais de um local: {locais_str}. "
                    f"No geral, se estiver em mais de um lugar indica duplicação indevida de informação."
                )

        # Valida os mapas
        for contexto_nome, mapas in mapas_para_validar:
            for idx_mapa, mapa in enumerate(mapas):
                referencias = mapa.get("referencias", [])
                pois = mapa.get("pontos_de_interesse", [])
                ids_nas_referencias: Set[str] = set()

                for ref in referencias:
                    ids_vistos: Set[str] = set()
                    # Validação de duplicação de ID na mesma referência
                    for ref_id in ref.get("ids", []):
                        ref_id_str = str(ref_id)
                        if ref_id_str in ids_vistos:
                            nome_ref = ref.get("escalada") or ref.get("setor") or ref.get("grupo") or "Desconhecida"
                            erros.append(f"O ID '{ref_id_str}' está duplicado na referência '{nome_ref}' (Mapa {idx_mapa+1} em {contexto_nome}).")
                        ids_vistos.add(ref_id_str)
                        ids_nas_referencias.add(ref_id_str)
                        
                    # Validação de existência da entidade
                    alvo_uid = str(ref.get("alvo_uid", "") or "").strip()
                    if alvo_uid:
                        if alvo_uid not in uids_escaladas and alvo_uid not in uids_setores and alvo_uid not in uids_grupos:
                            nome_ref = ref.get("escalada") or ref.get("setor") or ref.get("grupo") or alvo_uid
                            erros.append(f"Referência com alvo_uid '{alvo_uid}' ('{nome_ref}') não encontrada no pico '{pico_nome}' (Mapa {idx_mapa+1} em {contexto_nome}).")
                    else:
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

                # Se houver POIs e referências cadastradas no mapa, valida se há POIs órfãos ou referências quebradas
                if pois and referencias:
                    ids_pois_existentes: Set[str] = {str(p.get("id")) for p in pois if isinstance(p, dict) and p.get("id") is not None}

                    # 1. POIs órfãos (existem no mapa, mas não estão em nenhuma referência)
                    for p in pois:
                        if not isinstance(p, dict):
                            continue
                        p_id = str(p.get("id", ""))
                        if p_id and p_id not in ids_nas_referencias:
                            tipo_poi = "Linha" if "linha" in p else ("Círculo" if "circulo" in p else ("Polígono" if "poligono" in p else ("Retângulo" if "retangulo" in p else ("Quadrado" if "quadrado" in p else "Ponto"))))
                            rotulo = p.get("label") or p.get("texto_visivel") or ""
                            if not rotulo and "linha" in p:
                                marcadores = p["linha"].get("compilado", {}).get("marcadores", [])
                                if marcadores and marcadores[0].get("rotulo"):
                                    rotulo = marcadores[0]["rotulo"]
                                else:
                                    nos = p["linha"].get("conteudo", {}).get("nos", [])
                                    if nos and nos[0].get("rotulo"):
                                        rotulo = nos[0]["rotulo"]

                            detalhe_rotulo = f" (rótulo: '{rotulo}')" if rotulo else ""
                            erros.append(
                                f"O Ponto de Interesse [{tipo_poi}] com ID '{p_id}'{detalhe_rotulo} em {contexto_nome} (Mapa {idx_mapa+1}) "
                                f"não possui nenhuma referência associada em 'referencias' e será ignorado pelo aplicativo."
                            )

                    # 2. Referências quebradas (apontam para IDs que não existem em pontos_de_interesse)
                    for ref_id in sorted(ids_nas_referencias):
                        if ref_id not in ids_pois_existentes:
                            erros.append(
                                f"A referência no Mapa {idx_mapa+1} em {contexto_nome} aponta para o ID '{ref_id}', "
                                f"mas esse ID não existe em nenhum Ponto de Interesse do mapa."
                            )

                    # 3. Referências sem label ou rótulo em círculo identificador
                    pois_map = {str(p.get("id")): p for p in pois if isinstance(p, dict) and p.get("id") is not None}
                    for ref in referencias:
                        nome_ref = ref.get("escalada") or ref.get("setor") or ref.get("grupo") or "Desconhecida"
                        ref_ids = [str(i) for i in ref.get("ids", [])]
                        if not ref_ids:
                            continue

                        tem_identificador = False
                        for rid in ref_ids:
                            p = pois_map.get(rid)
                            if not p:
                                continue

                            if "linha" not in p:
                                label_str = str(p.get("label") or "").strip()
                                if label_str:
                                    tem_identificador = True
                                    break
                            else:
                                linha = p.get("linha", {})
                                marcadores = linha.get("compilado", {}).get("marcadores", [])
                                nos = linha.get("conteudo", {}).get("nos", []) or marcadores
                                for no in nos:
                                    tipo_no = str(no.get("tipo", "")).upper()
                                    if tipo_no in (
                                        "1", "CIRCULO_IDENTIFICADOR", "TIPO_NO_CIRCULO_IDENTIFICADOR",
                                        "2", "INICIO_AGACHADO", "TIPO_NO_INICIO_AGACHADO",
                                        "11", "FIM_TOP", "TIPO_NO_FIM_TOP"
                                    ):
                                        rotulo = str(no.get("rotulo") or "").strip()
                                        if rotulo:
                                            tem_identificador = True
                                            break
                                if tem_identificador:
                                    break

                        if not tem_identificador:
                            erros.append(
                                f"A referência '{nome_ref}' no Mapa {idx_mapa+1} em {contexto_nome} "
                                f"não possui label ou rótulo em círculo identificador e não exibirá identificador no mapa do aplicativo."
                            )
                            
    return erros

def computar_precomputados_setor(setor_conteudo: Dict[str, Any]) -> None:
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

def computar_precomputados_grupo(grupo_conteudo: Dict[str, Any]) -> None:
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

def computar_precomputados_pico(pico: Dict[str, Any]) -> None:
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

def injetar_precomputados(croqui_data: Dict[str, Any]) -> None:
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

def precompilar_linhas_mapas_recursivo(obj: Any) -> None:
    """
    Percorre recursivamente croqui_data e para cada PontoDeInteresse com 'linha.conteudo',
    calcula os dados pré-compilados (caminho_svg, caixa_delimitadora, marcadores)
    e substitui 'conteudo' por 'compilado' para máxima performance no app mobile.
    """
    if isinstance(obj, list):
        for item in obj:
            precompilar_linhas_mapas_recursivo(item)
    elif isinstance(obj, dict):
        if "pontos_de_interesse" in obj and isinstance(obj["pontos_de_interesse"], list):
            for pt in obj["pontos_de_interesse"]:
                if isinstance(pt, dict) and "linha" in pt:
                    linha = pt["linha"]
                    if isinstance(linha, dict) and "conteudo" in linha:
                        conteudo = linha["conteudo"]
                        nos = conteudo.get("nos", [])
                        if nos:
                            from editor.core.spline_catmull_rom import calcular_spline_catmull_rom
                            res = calcular_spline_catmull_rom(nos)
                            angulos = res.get("angulos_tangentes", [])
                            marcadores = []
                            for i, no in enumerate(nos):
                                tipo_no = no.get("tipo", 0)
                                if not tipo_no or str(tipo_no).upper() in ("0", "PASSAGEM", "TIPO_NO_PASSAGEM"):
                                    continue
                                ang_deg = angulos[i] if i < len(angulos) else 0.0
                                marcador_dict: Dict[str, Any] = {
                                    "tipo": tipo_no,
                                    "x": int(round(no.get("x", 0))),
                                    "y": int(round(no.get("y", 0))),
                                    "angulo_graus_x100": int(round(ang_deg * 100)),
                                    "rotulo": str(no.get("rotulo", ""))
                                }
                                if no.get("raio"):
                                    marcador_dict["raio"] = int(no["raio"])
                                if no.get("tamanho_fonte"):
                                    marcador_dict["tamanho_fonte"] = int(no["tamanho_fonte"])
                                marcadores.append(marcador_dict)
                            linha["compilado"] = {
                                "caminho_svg": res["caminho_svg"],
                                "caixa_delimitadora": res["caixa_delimitadora"],
                                "marcadores": marcadores,
                            }
                            del linha["conteudo"]
        for v in obj.values():
            if isinstance(v, (dict, list)):
                precompilar_linhas_mapas_recursivo(v)

def compilar_croqui(
    pico_path: Path,
    destino_yaml: Optional[Path],
    destino_binarypb: Path,
    dados_extras: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Carrega os dados corrigidos, expande conteúdos e gera os arquivos .yaml e .binarypb de deploy."""
    croqui_yaml_path = pico_path / "croqui.yaml"
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_data: Dict[str, Any] = yaml.safe_load(f)

    # 1. Expande arquivos markdown globais contidos em botoes
    botoes_processados: List[Dict[str, Any]] = []
    for botao in croqui_data.get("botoes", []):
        if isinstance(botao, dict):
            b_uid = botao.get("uid", "")
            destino = botao.get("destino", {})
            if "secao_textual" in destino:
                secao = destino["secao_textual"]
                if isinstance(secao, dict) and "caminho" in secao:
                    md_path = pico_path / secao["caminho"]
                    _, corpo = parse_md_com_frontmatter(md_path)
                    
                    novo_botao = {
                        "uid": b_uid,
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

    # 2.6 Preenche em memória campos legados para retrocompatibilidade
    preencher_compatibilidade_legada_em_memoria(croqui_data)

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

    # 3.4. Pré-compila caminhos SVG e caixas delimitadoras de traçados vetoriais
    precompilar_linhas_mapas_recursivo(croqui_data)

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

def garantir_comentarios_licenca(file_path: Path) -> None:

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
            
    sucesso_escrita = False
    ultimo_erro: Optional[Exception] = None
    for tentativa in range(1, 4):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(linhas_limpas)
            sucesso_escrita = True
            break
        except OSError as e:
            ultimo_erro = e
            if tentativa < 3:
                time.sleep(0.05 * tentativa)
        except Exception as e:
            ultimo_erro = e
            break

    if not sucesso_escrita:
        print(f"Erro ao escrever {file_path} para injetar SPDX: {ultimo_erro}")
