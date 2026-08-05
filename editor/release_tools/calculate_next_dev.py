# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import sys
import re
import argparse

def calculate_next_dev(version: str) -> str:
    parts = version.split('-', 1)
    base_parts = parts[0].split('.')
    
    if len(base_parts) != 3:
        raise ValueError(f"Versão '{version}' não possui formato Major.Minor.Patch na base")
        
    match = re.match(r"^(\d+)", base_parts[2])
    if not match:
        raise ValueError(f"O patch da versão '{version}' não começa com números.")
        
    patch_num = int(match.group(1))
    base_parts[2] = str(patch_num + 1)
    return '.'.join(base_parts) + "-dev"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a próxima versão -dev.")
    parser.add_argument("versao", help="Versão atual")
    
    args = parser.parse_args()
    
    try:
        next_ver = calculate_next_dev(args.versao)
        print(next_ver)
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
