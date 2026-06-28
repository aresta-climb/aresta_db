import yaml
import ruamel.yaml
from pathlib import Path
import re
from scripts.finalizar_mapas import parse_md_com_frontmatter, salvar_md_com_frontmatter

def extrair_imagens_do_markdown(corpo: str) -> list[str]:
    """Extrai todos os caminhos de imagens de um texto markdown com formato ![alt](caminho)."""
    padrao = r"!\[.*?\]\((.*?)\)"
    return re.findall(padrao, corpo)

def converter_md_texto_para_mapas(frontmatter: dict, corpo: str) -> tuple[dict, str]:
    """
    Converte um markdown que contém imagens no corpo para um markdown com as imagens
    listadas no array 'mapas' do frontmatter.
    Retorna (novo_frontmatter, novo_corpo).
    """
    novo_frontmatter = frontmatter.copy() if frontmatter else {}
    
    # Extrai imagens do corpo
    imagens = extrair_imagens_do_markdown(corpo)
    
    # Inicializa ou usa o array de mapas existente
    mapas_existentes = novo_frontmatter.get("mapas", [])
    mapas_atualizados = list(mapas_existentes)
    
    # Conjunto para evitar duplicatas (caso a imagem já esteja em mapas)
    caminhos_existentes = {m.get("caminho_imagem_mapa") for m in mapas_atualizados if isinstance(m, dict)}
    
    for img in imagens:
        if img not in caminhos_existentes:
            mapas_atualizados.append({
                "caminho_imagem_mapa": img
            })
            caminhos_existentes.add(img)
            
    if mapas_atualizados:
        novo_frontmatter["mapas"] = mapas_atualizados
        
    return novo_frontmatter, corpo

def migrar(pico_path: Path):
    """
    Migração 0003: Migrar mapas_gerais de secoes_textuais para Pico.mapas_gerais
    """
    croqui_yaml_path = pico_path / "croqui.yaml"
    if not croqui_yaml_path.exists():
        return
        
    ryaml = ruamel.yaml.YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 90
    
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_data = ryaml.load(f) or {}
        
    botoes = croqui_data.get("botoes", [])
    mapas_gerais_entry = None
    
    # Encontra a entrada de mapas_gerais nos botoes
    for i, botao in enumerate(botoes):
        destino = botao.get("destino", {})
        secao = destino.get("secao_textual", {})
        if "caminho" in secao:
            if "mapas_gerais" in secao["caminho"].lower():
                mapas_gerais_entry = secao
                botoes.pop(i)
                break
                
    if mapas_gerais_entry:
        croqui_data["botoes"] = botoes
        if not croqui_data["botoes"]:
            del croqui_data["botoes"]
            
        picos = croqui_data.get("picos", [])
        if picos:
            # Associa os mapas gerais ao primeiro pico
            if "mapas_gerais" not in picos[0]:
                picos[0]["mapas_gerais"] = {"caminho": mapas_gerais_entry["caminho"]}
                
        # Processa o arquivo MD
        md_path = pico_path / mapas_gerais_entry["caminho"]
        if md_path.exists():
            frontmatter, corpo = parse_md_com_frontmatter(md_path)
            novo_frontmatter, novo_corpo = converter_md_texto_para_mapas(frontmatter, corpo)
            
            # Limpa o texto original, pois ColecaoDeMapas não tem texto
            novo_corpo = ""
            
            salvar_md_com_frontmatter(md_path, novo_frontmatter, novo_corpo)
            
    with open(croqui_yaml_path, "w", encoding="utf-8") as f:
        ryaml.dump(croqui_data, f)
