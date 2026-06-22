import os
import sys
import importlib.util
from pathlib import Path
import yaml

def obter_lista_migracoes(migracoes_dir: Path):
    """
    Retorna uma lista ordenada de tuplas (MIGRATION_ID, filepath) de scripts de migração válidos.
    """
    migracoes = []
    for filename in os.listdir(migracoes_dir):
        if filename.endswith(".py") and filename[0].isdigit():
            filepath = migracoes_dir / filename
            
            # Lê o arquivo para encontrar o MIGRATION_ID sem executar (ou executando num spec)
            spec = importlib.util.spec_from_file_location("migracao", filepath)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                if hasattr(module, "MIGRATION_ID"):
                    migracoes.append((module.MIGRATION_ID, filepath))
            except Exception as e:
                # Se falhar ao carregar, apenas ignora
                continue
                
    migracoes.sort(key=lambda x: x[0])
    return migracoes

def migrar_todos_os_croquis(db_dir: Path, migracoes_dir: Path):
    """
    Varre a pasta de banco de dados e aplica as migrações sequencialmente a cada croqui.
    """
    migracoes = obter_lista_migracoes(migracoes_dir)
    
    if not migracoes:
        print("Nenhuma migração encontrada.")
        return
        
    print(f"Migrações encontradas: {[m[1].name for m in migracoes]}")
    
    croquis_encontrados = 0
    croquis_atualizados = 0
    
    for entry in db_dir.iterdir():
        croqui_yaml_path = entry / "croqui.yaml"
        if entry.is_dir() and croqui_yaml_path.exists():
            croquis_encontrados += 1
            
            with open(croqui_yaml_path, "r", encoding="utf-8") as f:
                croqui_data = yaml.safe_load(f)
                
            if not croqui_data:
                continue
                
            ultima_migracao = croqui_data.get("ultima_migracao", 0)
            
            atualizou = False
            for mig_id, filepath in migracoes:
                if mig_id > ultima_migracao:
                    # Carrega o módulo da migração
                    spec = importlib.util.spec_from_file_location("mig_script", filepath)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if not hasattr(module, "migrar"):
                        print(f"[ERRO CRÍTICO] A migração {filepath.name} não possui uma função 'migrar(croqui_dir)' ou 'MIGRATION_ID'.")
                        sys.exit(1)
                        
                    print(f"[{entry.name}] Aplicando migração {mig_id} ({filepath.name})...")
                    try:
                        module.migrar(entry)
                        ultima_migracao = mig_id
                        atualizou = True
                    except Exception as e:
                        print(f"[ERRO] Falha ao aplicar {filepath.name} no croqui {entry.name}: {e}")
                        sys.exit(1)
            
            if atualizou:
                croquis_atualizados += 1
                
    print(f"\\nProcesso concluído! {croquis_atualizados} croquis atualizados dentre {croquis_encontrados} encontrados.")

def main():
    if len(sys.argv) < 3:
        print("Uso: python migrar_banco.py <caminho_database> <caminho_migracoes>")
        sys.exit(1)
        
    db_path = Path(sys.argv[1])
    mig_path = Path(sys.argv[2])
    
    if not db_path.exists() or not db_path.is_dir():
        print(f"Diretório database '{db_path}' inválido.")
        sys.exit(1)
        
    if not mig_path.exists() or not mig_path.is_dir():
        print(f"Diretório de migrações '{mig_path}' inválido.")
        sys.exit(1)
        
    migrar_todos_os_croquis(db_path, mig_path)

if __name__ == "__main__":
    main() # pragma: no cover
