"""
Utilitário para validação de pull requests, consumindo a biblioteca gerar_croqui_experimental.
"""

from pathlib import Path
from scripts.gerar_croqui_experimental import empacotar_databases_para_croqui

def validar_pull_request(pastas_modificadas: list[str], diretorio_saida: str) -> list[str]:
    """
    Tenta compilar e empacotar uma lista de pastas de croquis modificadas num único .croqui
    
    Args:
        pastas_modificadas: Lista de caminhos relativos para pastas dentro de database/.
        diretorio_saida: Caminho para o diretório onde o .croqui será gerado.
        
    Returns:
        Uma lista de mensagens de erro. Se estiver vazia, significa sucesso total.
    """
    erros = []
    out_dir = Path(diretorio_saida)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not pastas_modificadas:
        return erros
        
    db_paths = [Path(p) for p in pastas_modificadas]
    
    try:
        arquivo_gerado = empacotar_databases_para_croqui(db_paths, out_dir)
        print(f"Sucesso: {arquivo_gerado.name} gerado contendo {len(pastas_modificadas)} croqui(s)")
    except Exception as e:
        msg_erro = f"Falha ao compilar lote de croquis: {str(e)}"
        print(f"ERRO: {msg_erro}")
        erros.append(msg_erro)
            
    return erros

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Valida pastas modificadas do database/")
    parser.add_argument("--pastas", nargs="+", required=True, help="Lista de pastas modificadas")
    parser.add_argument("--saida", required=True, help="Diretório de saída para os artefatos")
    
    args = parser.parse_args()
    erros = validar_pull_request(args.pastas, args.saida)
    
    if erros:
        print(f"\nValidação concluída com {len(erros)} erro(s).")
        sys.exit(1)
    else:
        print("\nValidação concluída com sucesso.")
        sys.exit(0)
