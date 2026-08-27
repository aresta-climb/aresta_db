# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário para validação de pull requests, consumindo a biblioteca gerar_croqui_experimental.
"""

import sys
import subprocess
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path para resolução de módulos
_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from scripts.gerar_croqui_experimental import empacotar_databases_para_croqui


def validar_cabecalhos_e_licencas() -> list[str]:
    """
    Executa a suíte de testes de cabeçalhos e licenças (codebase_headers_test.py).
    """
    erros = []
    teste_path = _RAIZ_REPOSITORIO / "scripts" / "codebase_headers_test.py"
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(teste_path)],
        cwd=str(_RAIZ_REPOSITORIO),
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        msg = f"Falha na validação de cabeçalhos e licenças (codebase_headers_test):\n{resultado.stdout}\n{resultado.stderr}"
        print(f"ERRO: {msg}")
        erros.append(msg)
    else:
        print("Sucesso: Testes de cabeçalhos e licenças (codebase_headers_test) passaram com êxito.")
    return erros


def validar_pull_request(pastas_modificadas: list[str], diretorio_saida: str) -> list[str]:
    """
    Valida um pull request:
    1. Executa os testes de conformidade de cabeçalhos e licenças (codebase_headers_test).
    2. Tenta compilar e empacotar uma lista de pastas de croquis modificadas num único .croqui.
    
    Args:
        pastas_modificadas: Lista de caminhos relativos para pastas dentro de database/.
        diretorio_saida: Caminho para o diretório onde o .croqui será gerado.
        
    Returns:
        Uma lista de mensagens de erro. Se estiver vazia, significa sucesso total.
    """
    erros = []
    
    # 1. Validação de cabeçalhos e licenças
    erros.extend(validar_cabecalhos_e_licencas())
    
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
