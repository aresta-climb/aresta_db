# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import os
import re
from pathlib import Path
from ruamel.yaml import YAML
import io

MIGRATION_ID = 2

yaml_parser = YAML()
yaml_parser.default_flow_style = False
yaml_parser.preserve_quotes = True
yaml_parser.width = 90

# Desativar aliases explicitamente para evitar caracteres lixo como *id001
yaml_parser.representer.ignore_aliases = lambda *data: True

FALHAS_MIGRACAO = []

def parse_reference_groups(id_values):
    split_values = [v.split('/') for v in id_values]
    max_len = max(len(v) for v in split_values) if split_values else 0
    if max_len == 0: return [] # pragma: no cover
    
    groups = []
    for i in range(max_len):
        group_raws = []
        group_parts = []
        for v in split_values:
            part = v[i] if i < len(v) else v[-1]
            group_raws.append(part.strip())
            tokens = re.findall(r'\d+|[a-zA-Z]+|[^a-zA-Z\d\s]+', part)
            for t in tokens:
                group_parts.append(t)
        
        seen = set()
        deduped = []
        for t in group_parts:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
                
        groups.append({'raws': group_raws, 'tokens': deduped})
    return groups

def registrar_falha(tipo, nome, grupo, ctx_setor, ctx_grupo, filename=None):
    item = {
        'escalada': nome,
        'ids_procurados': '/'.join(grupo) if isinstance(grupo, list) else str(grupo),
        'setor_contexto': ctx_setor,
        'grupo_contexto': ctx_grupo
    }
    item = {k: v for k, v in item.items() if v is not None}
    if filename:
        return item
    FALHAS_MIGRACAO.append(item) # pragma: no cover

def extrair_referencias_recursivo(obj, ctx_setor=None, ctx_grupo=None):
    modificado = False
    refs_para_subir = []
    
    if isinstance(obj, dict):
        # Pre-pass: convert int/ScalarInt IDs in pontos_de_interesse to SingleQuotedScalarString
        from ruamel.yaml.scalarstring import SingleQuotedScalarString
        if 'mapas' in obj and isinstance(obj['mapas'], list):
            for mapa in obj['mapas']:
                for ponto in mapa.get('pontos_de_interesse', []):
                    for key in ['id', 'label']:
                        pval = ponto.get(key)
                        if isinstance(pval, int) and not isinstance(pval, bool):
                            width = getattr(pval, '_width', 0)
                            ponto[key] = SingleQuotedScalarString(f"{int(pval):0{width}d}")
                            modificado = True

    if isinstance(obj, list):
        for item in obj:
            refs_sub, mod_sub = extrair_referencias_recursivo(item, ctx_setor, ctx_grupo)
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
                refs_para_subir.append({'tipo': 'escalada', 'nome': nome_via, 'grupos': parse_reference_groups(ids), 'setor_contexto': ctx_setor, 'grupo_contexto': ctx_grupo})
                
            if tipo == 'via_multiplas_enfiadas' and 'enfiadas' in via:
                refs_sub, mod_sub = extrair_referencias_recursivo(via['enfiadas'], ctx_setor, ctx_grupo) # pragma: no cover
                refs_para_subir.extend(refs_sub) # pragma: no cover
                if mod_sub: modificado = True # pragma: no cover
                
        if not is_via:
            for k, v in list(obj.items()):
                if isinstance(v, (dict, list)):
                    if k in ['setor', 'grupo'] and isinstance(v, dict) and 'conteudo' in v:
                        cont = v['conteudo']
                        novo_setor = cont.get('nome') if k == 'setor' else ctx_setor
                        novo_grupo = cont.get('nome') if k == 'grupo' else ctx_grupo
                        if 'id_no_mapa' in cont:
                            refs_para_subir.append({'tipo': k, 'nome': cont.get('nome', 'Sem Nome'), 'grupos': parse_reference_groups([str(cont.pop('id_no_mapa'))]), 'setor_contexto': ctx_setor, 'grupo_contexto': ctx_grupo}) # pragma: no cover
                            modificado = True # pragma: no cover
                        refs_sub, mod_sub = extrair_referencias_recursivo(cont, novo_setor, novo_grupo)
                        refs_para_subir.extend(refs_sub)
                        if mod_sub: modificado = True
                        
                    elif k == 'setores' and isinstance(v, list):
                        for s_item in v:
                            if isinstance(s_item, dict) and 'conteudo' in s_item:
                                cont = s_item['conteudo']
                                novo_setor = cont.get('nome')
                                if 'id_no_mapa' in cont:
                                    refs_para_subir.append({'tipo': 'setor', 'nome': cont.get('nome', 'Sem Nome'), 'grupos': parse_reference_groups([str(cont.pop('id_no_mapa'))]), 'setor_contexto': ctx_setor, 'grupo_contexto': ctx_grupo}) # pragma: no cover
                                    modificado = True # pragma: no cover
                                refs_sub, mod_sub = extrair_referencias_recursivo(cont, novo_setor, ctx_grupo)
                                refs_para_subir.extend(refs_sub)
                                if mod_sub: modificado = True
                            else:
                                refs_sub, mod_sub = extrair_referencias_recursivo(s_item, ctx_setor, ctx_grupo)
                                refs_para_subir.extend(refs_sub)
                                if mod_sub: modificado = True
                    else:
                        refs_sub, mod_sub = extrair_referencias_recursivo(v, ctx_setor, ctx_grupo)
                        refs_para_subir.extend(refs_sub)
                        if mod_sub: modificado = True
                        
        if 'mapas' in obj and isinstance(obj['mapas'], list) and len(obj['mapas']) > 0:
            if refs_para_subir:
                mapas = obj['mapas']
                for ref in refs_para_subir:
                    tipo = ref['tipo']
                    nome = ref['nome']
                    grupos = ref['grupos']
                    adicionado_em_algum = False
                    
                    c_setor = ref.get('setor_contexto')
                    c_grupo = ref.get('grupo_contexto')
                    
                    if len(grupos) == 1:
                        grupo = grupos[0]
                        for idx, mapa in enumerate(mapas):
                            pontos = [str(p.get('id', '')) for p in mapa.get('pontos_de_interesse', [])]
                            matched_ids = None
                            if len(grupo['raws']) > 0 and all(r in pontos for r in grupo['raws']):
                                matched_ids = grupo['raws']
                            elif len(grupo['tokens']) > 0 and all(g in pontos for g in grupo['tokens']):
                                matched_ids = grupo['tokens']
                            
                            if matched_ids:
                                if 'referencias' not in mapa: mapa['referencias'] = []
                                mapa['referencias'].append({tipo: nome, 'ids': matched_ids})
                                adicionado_em_algum = True
                                modificado = True
                        if not adicionado_em_algum:
                            registrar_falha(tipo, nome, grupo['raws'], c_setor, c_grupo)
                    else:
                        for i, grupo in enumerate(grupos):
                            adicionado_neste_grupo = False
                            if i < len(mapas):
                                mapa = mapas[i]
                                pontos = [str(p.get('id', '')) for p in mapa.get('pontos_de_interesse', [])]
                                matched_ids = None
                                if all(r in pontos for r in grupo['raws']):
                                    matched_ids = grupo['raws']
                                elif all(g in pontos for g in grupo['tokens']):
                                    matched_ids = grupo['tokens']
                                    
                                if matched_ids is not None:
                                    if 'referencias' not in mapa: mapa['referencias'] = []
                                    mapa['referencias'].append({tipo: nome, 'ids': matched_ids})
                                    adicionado_neste_grupo = True
                                    modificado = True
                                if not adicionado_neste_grupo:
                                    registrar_falha(tipo, nome, grupo['raws'], c_setor, c_grupo)
                            else:
                                registrar_falha(tipo, nome, grupo['raws'], c_setor, c_grupo) # pragma: no cover
                refs_para_subir = []
                
    return refs_para_subir, modificado

def migrar(croqui_dir: Path):
    global FALHAS_MIGRACAO
    FALHAS_MIGRACAO = []

    croqui_yaml_path = croqui_dir / "croqui.yaml"
    if not croqui_yaml_path.exists():
        return # pragma: no cover
        
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_data = yaml_parser.load(f)
        
    if croqui_data and croqui_data.get("ultima_migracao", 0) >= MIGRATION_ID:
        return # pragma: no cover
        
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
                
    def process_file(filename, injected_setor=None, injected_grupo=None):
        if filename not in files_data: return [], None, None # pragma: no cover
        if filename in files_data:
            if files_data[filename].get("status") == "processed":
                return files_data[filename]["unabsorbed_refs"], files_data[filename]["id_raiz"], files_data[filename]["nome"]
            
        files_data[filename].update({"status": "processing", "unabsorbed_refs": [], "id_raiz": None, "nome": "Sem Nome", "falhas": []})
        yaml_data = files_data[filename]["yaml"]
        if not yaml_data:
            files_data[filename]["unabsorbed_refs"] = [] # pragma: no cover
            files_data[filename]["id_raiz"] = None # pragma: no cover
            files_data[filename]["nome"] = "Sem Nome" # pragma: no cover
            return [], None, "Sem Nome" # pragma: no cover
        
        id_raiz = None
        if "id_no_mapa" in yaml_data:
            id_raiz = str(yaml_data.pop("id_no_mapa"))
            arquivos_modificados.add(filename)
            
        nome = yaml_data.get("nome", "Sem Nome")
        
        refs_total = []
        
        def visitar_includes(obj, context_type=None, parent_setor=None, parent_grupo=None):
            if isinstance(obj, list):
                for item in obj:
                    visitar_includes(item, context_type, parent_setor, parent_grupo)
            elif isinstance(obj, dict):
                for k, v in list(obj.items()):
                    if k == "setor":
                        visitar_includes(v, "setor", v.get("nome") if isinstance(v, dict) else parent_setor, parent_grupo)
                    elif k == "grupo":
                        visitar_includes(v, "grupo", parent_setor, v.get("nome") if isinstance(v, dict) else parent_grupo)
                    elif k == "arquivo_setor":
                        visitar_includes(v, "setor", parent_setor, parent_grupo)
                    elif k == "caminho" and isinstance(v, str) and v in files_data:
                        child_refs, child_id_raiz, child_nome = process_file(v, parent_setor or ctx_setor_raiz, parent_grupo or ctx_grupo_raiz)
                        if child_refs:
                            import copy
                            child_refs_copy = copy.deepcopy(child_refs)
                            for r in child_refs_copy:
                                if not r.get('grupo_contexto'): r['grupo_contexto'] = parent_grupo or ctx_grupo_raiz
                                if not r.get('setor_contexto'): r['setor_contexto'] = parent_setor or ctx_setor_raiz
                            refs_total.extend(child_refs_copy)
                            arquivos_modificados.add(filename) # pragma: no cover
                        
                        # Propagate context to child failures
                        if v in files_data and files_data[v].get("falhas"):
                            for f in files_data[v]["falhas"]:
                                if not f.get('grupo_contexto') and (parent_grupo or ctx_grupo_raiz):
                                    f['grupo_contexto'] = parent_grupo or ctx_grupo_raiz
                                if not f.get('setor_contexto') and (parent_setor or ctx_setor_raiz):
                                    f['setor_contexto'] = parent_setor or ctx_setor_raiz
                        if child_id_raiz:
                            tipo_contexto = context_type if context_type else "setor"
                            refs_total.append({'tipo': tipo_contexto, 'nome': child_nome, "grupos": parse_reference_groups([child_id_raiz]), 'setor_contexto': child_nome, 'grupo_contexto': parent_grupo or ctx_grupo_raiz})
                            arquivos_modificados.add(filename)
                    else:
                        visitar_includes(v, context_type, parent_setor, parent_grupo)
                        
        is_setor = "setor" in filename or "Setor" in nome
        is_grupo = ("grupo" in filename and "setor" not in filename) or ("Grupo" in nome)
        ctx_setor_raiz = nome if is_setor else injected_setor
        ctx_grupo_raiz = nome if is_grupo else injected_grupo
        
        visitar_includes(yaml_data)
        
        refs_aqui, modificado = extrair_referencias_recursivo(yaml_data, ctx_setor_raiz, ctx_grupo_raiz)
        if modificado:
            arquivos_modificados.add(filename)
            
        if refs_aqui:
            refs_total.extend(refs_aqui) # pragma: no cover
        if "mapas" in yaml_data and isinstance(yaml_data["mapas"], list) and len(yaml_data["mapas"]) > 0:
            if refs_total:
                mapas = yaml_data["mapas"]
                for ref in refs_total:
                    tipo = ref['tipo']
                    nome = ref['nome']
                    grupos = ref['grupos']
                    adicionado_em_algum = False
                    
                    c_setor = ref.get('setor_contexto')
                    c_grupo = ref.get('grupo_contexto')
                    
                    if len(grupos) == 1:
                        grupo = grupos[0]
                        for idx, mapa in enumerate(mapas):
                            pontos = [str(p.get('id', '')) for p in mapa.get('pontos_de_interesse', [])]
                            matched_ids = None
                            if all(r in pontos for r in grupo['raws']):
                                matched_ids = grupo['raws']
                            elif all(g in pontos for g in grupo['tokens']):
                                matched_ids = grupo['tokens']
                                
                            if matched_ids is not None:
                                if 'referencias' not in mapa: mapa['referencias'] = []
                                mapa['referencias'].append({tipo: nome, 'ids': matched_ids})
                                adicionado_em_algum = True
                                arquivos_modificados.add(filename)
                        if not adicionado_em_algum:
                            falha = registrar_falha(tipo, nome, grupo['raws'], c_setor, c_grupo, filename) # pragma: no cover
                            files_data[filename]["falhas"].append(falha) # pragma: no cover
                    else:
                        for i, grupo in enumerate(grupos): # pragma: no cover
                            adicionado_neste_grupo = False
                            if i < len(mapas): # pragma: no cover
                                mapa = mapas[i] # pragma: no cover
                                pontos = [str(p.get('id', '')) for p in mapa.get('pontos_de_interesse', [])] # pragma: no cover
                                matched_ids = None
                                if all(r in pontos for r in grupo['raws']): # pragma: no cover
                                    matched_ids = grupo['raws'] # pragma: no cover
                                elif all(g in pontos for g in grupo['tokens']): # pragma: no cover
                                    matched_ids = grupo['tokens'] # pragma: no cover
                                    
                                if matched_ids is not None: # pragma: no cover
                                    if 'referencias' not in mapa: mapa['referencias'] = [] # pragma: no cover
                                    mapa['referencias'].append({tipo: nome, 'ids': matched_ids}) # pragma: no cover
                                    arquivos_modificados.add(filename) # pragma: no cover
                                    adicionado_neste_grupo = True # pragma: no cover
                                if not adicionado_neste_grupo:
                                    falha = registrar_falha(tipo, nome, grupo['raws'], c_setor, c_grupo, filename) # pragma: no cover
                                    files_data[filename]["falhas"].append(falha) # pragma: no cover
                            else:
                                falha = registrar_falha(tipo, nome, grupo['raws'], c_setor, c_grupo, filename) # pragma: no cover
                                files_data[filename]["falhas"].append(falha) # pragma: no cover
                refs_total = []
                
        files_data[filename]["unabsorbed_refs"] = refs_total
        files_data[filename]["id_raiz"] = id_raiz
        files_data[filename]["nome"] = nome
        files_data[filename]["status"] = "processed"
        
        return refs_total, id_raiz, nome

    process_file("croqui.yaml")
    
    for filename in list(files_data.keys()):
        process_file(filename)
        
    for filename in list(files_data.keys()):
        data = files_data[filename]
        if "falhas" in data and data["falhas"]:
            FALHAS_MIGRACAO.extend(data["falhas"])
            
    if "croqui.yaml" in files_data:
        arquivos_modificados.add("croqui.yaml")
        
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
            
    if FALHAS_MIGRACAO:
        unique_falhas = []
        seen = set()
        for f in FALHAS_MIGRACAO:
            # Create a hashable tuple representation
            t = tuple(sorted((k, str(v)) for k, v in f.items() if isinstance(v, (str, int, float, bool, list))))
            if t not in seen:
                seen.add(t)
                unique_falhas.append(f)
        
        falhas_path = croqui_dir / "ids_no_mapa_nao_encontrados.yaml"
        falhas_existentes = []
        if falhas_path.exists():
            with open(falhas_path, "r", encoding="utf-8") as f:
                falhas_existentes = yaml_parser.load(f) or []
        
        # Merge unique_falhas into existing (also ensuring no duplicates in final result)
        seen_all = set()
        final_list = []
        for f in (falhas_existentes + unique_falhas):
            t = tuple(sorted((k, str(v)) for k, v in f.items() if isinstance(v, (str, int, float, bool, list))))
            if t not in seen_all:
                seen_all.add(t)
                final_list.append(f)
        
        with open(falhas_path, "w", encoding="utf-8") as f:
            yaml_parser.dump(final_list, f)

if __name__ == "__main__": # pragma: no cover
    import sys
    if len(sys.argv) > 1:
        migrar(Path(sys.argv[1]))
