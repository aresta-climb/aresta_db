import os
from pathlib import Path
from ruamel.yaml import YAML
import io

MIGRATION_ID = 2

yaml_parser = YAML()
yaml_parser.preserve_quotes = True
yaml_parser.width = 4096

def extrair_referencias_recursivo(obj):
    refs_para_subir = []
    modificado = False
    
    if isinstance(obj, list):
        for item in obj:
            refs_sub, mod_sub = extrair_referencias_recursivo(item)
            refs_para_subir.extend(refs_sub)
            if mod_sub: modificado = True
            
    elif isinstance(obj, dict):
        chaves = list(obj.keys())
        is_via = False
        if len(chaves) == 1 and isinstance(obj[chaves[0]], dict) and 'nome' in obj[chaves[0]] and chaves[0] in ['via_esportiva', 'boulder', 'via_multiplas_enfiadas', 'psicobloc', 'via_tradicional', 'via_movel', 'highline']:
            is_via = True
            tipo = chaves[0]
            via = obj[tipo]
            
            nome_via = via.get('nome', 'Sem Nome')
            ids = []
            for k in ['id_no_mapa', 'id_no_mapa_meio', 'id_no_mapa_fim']:
                if k in via:
                    ids.append(str(via.pop(k)))
                    modificado = True
            if ids:
                refs_para_subir.append({'escalada': nome_via, 'ids': ids})
                
            if tipo == 'via_multiplas_enfiadas' and 'enfiadas' in via:
                refs_sub, mod_sub = extrair_referencias_recursivo(via['enfiadas'])
                refs_para_subir.extend(refs_sub)
                if mod_sub: modificado = True
                
        if not is_via:
            for k, v in list(obj.items()):
                if isinstance(v, (dict, list)):
                    if k in ['setor', 'grupo'] and isinstance(v, dict) and 'conteudo' in v:
                        cont = v['conteudo']
                        if 'id_no_mapa' in cont:
                            refs_para_subir.append({k: cont.get('nome', 'Sem Nome'), 'ids': [str(cont.pop('id_no_mapa'))]})
                            modificado = True
                        refs_sub, mod_sub = extrair_referencias_recursivo(cont)
                        refs_para_subir.extend(refs_sub)
                        if mod_sub: modificado = True
                        
                    elif k == 'setores' and isinstance(v, list):
                        for s_item in v:
                            if isinstance(s_item, dict) and 'conteudo' in s_item:
                                cont = s_item['conteudo']
                                if 'id_no_mapa' in cont:
                                    refs_para_subir.append({'setor': cont.get('nome', 'Sem Nome'), 'ids': [str(cont.pop('id_no_mapa'))]})
                                    modificado = True
                                refs_sub, mod_sub = extrair_referencias_recursivo(cont)
                                refs_para_subir.extend(refs_sub)
                                if mod_sub: modificado = True
                            else:
                                refs_sub, mod_sub = extrair_referencias_recursivo(s_item)
                                refs_para_subir.extend(refs_sub)
                                if mod_sub: modificado = True
                    else:
                        refs_sub, mod_sub = extrair_referencias_recursivo(v)
                        refs_para_subir.extend(refs_sub)
                        if mod_sub: modificado = True
                        
        if 'mapas' in obj and isinstance(obj['mapas'], list) and len(obj['mapas']) > 0:
            if refs_para_subir:
                if 'referencias' not in obj['mapas'][0]:
                    obj['mapas'][0]['referencias'] = []
                obj['mapas'][0]['referencias'].extend(refs_para_subir)
                refs_para_subir = []
                modificado = True
                
    return refs_para_subir, modificado

def migrar(croqui_dir: Path):
    croqui_yaml_path = croqui_dir / "croqui.yaml"
    if not croqui_yaml_path.exists():
        return
        
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_data = yaml_parser.load(f)
        
    if croqui_data and croqui_data.get("ultima_migracao", 0) >= MIGRATION_ID:
        return
        
    files_data = {}
    arquivos_modificados = set()
    
    for filename in os.listdir(croqui_dir):
        if filename.endswith(".md") or filename == "croqui.yaml":
            filepath = croqui_dir / filename
            content = filepath.read_text(encoding="utf-8")
            if filename.endswith(".md"):
                if not content.startswith("---\n"): continue
                parts = content.split("---\n", 2)
                if len(parts) < 3: continue
                ydata = yaml_parser.load(parts[1])
                files_data[filename] = {"yaml": ydata, "parts": parts, "filepath": filepath}
            else:
                ydata = yaml_parser.load(content)
                files_data[filename] = {"yaml": ydata, "filepath": filepath}
                
    def process_file(filename):
        if filename not in files_data: return [], None, None
        if "processed" in files_data[filename]:
            if "unabsorbed_refs" not in files_data[filename]:
                print(f"CRITICAL: {filename} has processed=True but NO unabsorbed_refs! Current keys: {list(files_data[filename].keys())}")
            return files_data[filename]["unabsorbed_refs"], files_data[filename]["id_raiz"], files_data[filename]["nome"]
            
        files_data[filename]["processed"] = True
        yaml_data = files_data[filename]["yaml"]
        if not yaml_data:
            files_data[filename]["unabsorbed_refs"] = []
            files_data[filename]["id_raiz"] = None
            files_data[filename]["nome"] = "Sem Nome"
            return [], None, "Sem Nome"
        
        id_raiz = None
        if "id_no_mapa" in yaml_data:
            id_raiz = str(yaml_data.pop("id_no_mapa"))
            arquivos_modificados.add(filename)
            
        nome = yaml_data.get("nome", "Sem Nome")
        
        refs_total = []
        
        def visitar_includes(obj, context_type=None):
            if isinstance(obj, list):
                for item in obj:
                    visitar_includes(item, context_type)
            elif isinstance(obj, dict):
                for k, v in list(obj.items()):
                    if k == "setor":
                        visitar_includes(v, "setor")
                    elif k == "grupo":
                        visitar_includes(v, "grupo")
                    elif k == "arquivo_setor":
                        visitar_includes(v, "setor")
                    elif k == "caminho" and isinstance(v, str) and v in files_data:
                        print(f"TRACE {filename}: calling process_file({v})")
                        child_refs, child_id_raiz, child_nome = process_file(v)
                        if child_refs:
                            refs_total.extend(child_refs)
                            arquivos_modificados.add(filename)
                        if child_id_raiz:
                            tipo = context_type if context_type else "setor"
                            refs_total.append({tipo: child_nome, "ids": [child_id_raiz]})
                            arquivos_modificados.add(filename)
                    else:
                        visitar_includes(v, context_type)
                        
        print(f"TRACE: starting visitar_includes for {filename}")
        visitar_includes(yaml_data)
        
        print(f"TRACE: starting extrair_referencias_recursivo for {filename}")
        refs_aqui, modificado = extrair_referencias_recursivo(yaml_data)
        if modificado:
            arquivos_modificados.add(filename)
            
        if refs_aqui:
            refs_total.extend(refs_aqui)
            
        if "mapas" in yaml_data and isinstance(yaml_data["mapas"], list) and len(yaml_data["mapas"]) > 0:
            if refs_total:
                if "referencias" not in yaml_data["mapas"][0]:
                    yaml_data["mapas"][0]["referencias"] = []
                yaml_data["mapas"][0]["referencias"].extend(refs_total)
                arquivos_modificados.add(filename)
                refs_total = []
                
        print(f"TRACE: setting unabsorbed_refs for {filename}")
        files_data[filename]["unabsorbed_refs"] = refs_total
        files_data[filename]["id_raiz"] = id_raiz
        files_data[filename]["nome"] = nome
        
        return refs_total, id_raiz, nome

    process_file("croqui.yaml")
    
    for filename in list(files_data.keys()):
        process_file(filename)
        
    for filename in arquivos_modificados:
        data = files_data[filename]
        filepath = data["filepath"]
        
        if filename == "croqui.yaml":
            # Atualiza versao no croqui.yaml
            ydata = data["yaml"]
            ydata["ultima_migracao"] = MIGRATION_ID
            stream = io.StringIO()
            yaml_parser.dump(ydata, stream)
            filepath.write_text(stream.getvalue(), encoding="utf-8")
        else:
            ydata = data["yaml"]
            stream = io.StringIO()
            yaml_parser.dump(ydata, stream)
            new_frontmatter = stream.getvalue()
            novo_conteudo = f"---{os.linesep}{new_frontmatter}---{os.linesep}{data['parts'][2]}"
            filepath.write_text(novo_conteudo, encoding="utf-8")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        migrar(Path(sys.argv[1]))
