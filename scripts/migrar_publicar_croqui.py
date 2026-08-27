# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT_DIR / "database"

def migrar_publicar_croqui():
    print(f"Buscando croquis em {DATABASE_DIR}...")
    
    if not DATABASE_DIR.exists():
        print("Diretório database não encontrado.")
        return
        
    for item in sorted(DATABASE_DIR.iterdir()):
        if not item.is_dir():
            continue
            
        croqui_yaml_path = item / "croqui.yaml"
        if not croqui_yaml_path.exists():
            continue
            
        with open(croqui_yaml_path, "r", encoding="utf-8") as f:
            try:
                dados = yaml.safe_load(f)
            except Exception as e:
                print(f"Erro lendo {croqui_yaml_path}: {e}")
                continue
                
        if not isinstance(dados, dict):
            continue
            
        revisado_manualmente = dados.get("revisado_manualmente", False)
        
        # Só insere se não existir
        if "publicar_croqui" not in dados:
            if revisado_manualmente:
                dados["publicar_croqui"] = True
                print(f"[{item.name}] Marcando publicar_croqui=True (era revisado_manualmente)")
            else:
                # Opcional: deixar sem ou marcar como False explícito. 
                # Deixar sem = False padrão no proto.
                # Como a issue pede: "Os outros, como padrão mesmo" (então omitimos e o proto assume false)
                print(f"[{item.name}] Ignorado (revisado_manualmente não é true)")
                continue

            with open(croqui_yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(dados, f, allow_unicode=True, sort_keys=False)

if __name__ == "__main__":
    migrar_publicar_croqui()
