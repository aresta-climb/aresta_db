import os
from pathlib import Path
from ruamel.yaml import YAML

yaml_parser = YAML()
yaml_parser.preserve_quotes = True

def extrair_referencias_recursivo(obj, nome_contexto=None):
    """
    Percorre um dicionario, remove os id_no_mapa das escaladas e retorna uma lista de referencias.
    Se a escalada nao tiver nome, usa 'Sem Nome'.
    """
    referencias = []
    
    if isinstance(obj, list):
        for item in obj:
            referencias.extend(extrair_referencias_recursivo(item, nome_contexto))
    elif isinstance(obj, dict):
        # Primeiro caso: obj eh uma via (tem nome, id_no_mapa, etc)
        # Note que vias estao dentro do dict da tipagem, ex: {"via_esportiva": {"nome": "A", "id_no_mapa": "1"}}
        
        # Identificamos se eh a "casca" de uma via
        chaves = list(obj.keys())
        if len(chaves) == 1 and isinstance(obj[chaves[0]], dict) and "nome" in obj[chaves[0]] and chaves[0] in ["via_esportiva", "boulder", "via_multiplas_enfiadas", "psicobloc", "via_tradicional"]:
            tipo = chaves[0]
            via = obj[tipo]
            
            nome_via = via.get("nome", "Sem Nome")
            
            ids = []
            if "id_no_mapa" in via:
                ids.append(str(via.pop("id_no_mapa")))
            if "id_no_mapa_meio" in via:
                ids.append(str(via.pop("id_no_mapa_meio")))
            if "id_no_mapa_fim" in via:
                ids.append(str(via.pop("id_no_mapa_fim")))
                
            if ids:
                referencias.append({"escalada": nome_via, "ids": ids})
                
            if tipo == "via_multiplas_enfiadas" and "enfiadas" in via:
                referencias.extend(extrair_referencias_recursivo(via["enfiadas"]))
                
        else:
            # Siga recursivamente pelas chaves normais
            for k, v in obj.items():
                if k == "setores_ou_grupos":
                    referencias.extend(extrair_referencias_recursivo(v))
                elif k == "setor":
                    # se for dict, é um conteudo de setor
                    if isinstance(v, dict) and "conteudo" in v:
                        referencias.extend(extrair_referencias_recursivo(v["conteudo"]))
                elif k == "grupo":
                    if isinstance(v, dict) and "conteudo" in v:
                        referencias.extend(extrair_referencias_recursivo(v["conteudo"]))
                elif k == "setores":
                    # lista de setores em um grupo
                    referencias.extend(extrair_referencias_recursivo(v))
                elif k == "escaladas":
                    # lista de escaladas
                    referencias.extend(extrair_referencias_recursivo(v))
                elif k == "conteudo":
                    referencias.extend(extrair_referencias_recursivo(v))
                    
    return referencias

def processar_arquivo(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return
        
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return
        
    yaml_data = yaml_parser.load(parts[1])
    if not yaml_data:
        return
        
    refs = extrair_referencias_recursivo(yaml_data)
    
    # Extrai tambem o id_no_mapa da raiz, se tiver (setores dentro de grupos)
    id_raiz = None
    if "id_no_mapa" in yaml_data:
        id_raiz = str(yaml_data.pop("id_no_mapa"))
        
    # Aplica no mapa do proprio arquivo se tiver
    mapas = yaml_data.get("mapas", [])
    if mapas and refs:
        if "referencias" not in mapas[0]:
            mapas[0]["referencias"] = []
        mapas[0]["referencias"].extend(refs)
        refs = [] # ja foram absorvidos
        
    # TODO save...
    return refs, id_raiz, yaml_data.get("nome", "")

