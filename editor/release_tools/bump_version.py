# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import re
import argparse
import sys

class SemVerError(Exception):
    pass

def validar_semver(versao):
    semver_pattern = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    if not semver_pattern.match(versao):
        raise SemVerError(f"A versão {versao} não segue o formato SemVer válido.")

def compare_semver(v1, v2):
    def parse(v):
        m = re.match(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9.-]+))?", v)
        if not m: return None
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        
    p1 = parse(v1)
    p2 = parse(v2)
    
    if p1[:3] != p2[:3]:
        return 1 if p1[:3] > p2[:3] else -1
        
    pre1, pre2 = p1[3], p2[3]
    if pre1 == pre2: return 0
    if pre1 is None: return 1
    if pre2 is None: return -1
    
    parts1, parts2 = pre1.split('.'), pre2.split('.')
    for p_a, p_b in zip(parts1, parts2):
        if p_a == p_b: continue
        if p_a.isdigit() and p_b.isdigit():
            return 1 if int(p_a) > int(p_b) else -1
        return 1 if p_a > p_b else -1
    return 1 if len(parts1) > len(parts2) else -1

def bump_version_file(caminho_arquivo, nova_versao):
    validar_semver(nova_versao)
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
        
    padrao = re.compile(r'^VERSION\s*=\s*"(.*)"', re.MULTILINE)
    
    match = padrao.search(conteudo)
    if not match:
        raise ValueError(f"Padrão VERSION = \".*\" não encontrado no arquivo {caminho_arquivo}")
        
    versao_atual = match.group(1)
    if compare_semver(nova_versao, versao_atual) <= 0:
        raise SemVerError(f"A nova versão ({nova_versao}) deve ser estritamente maior que a atual ({versao_atual}).")
        
    novo_conteudo = padrao.sub(f'VERSION = "{nova_versao}"', conteudo)
    
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)
        
    print(f"Versão atualizada de {versao_atual} para {nova_versao} no arquivo {caminho_arquivo}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atualiza a string VERSION de um arquivo Python.")
    parser.add_argument("arquivo", help="Caminho para o arquivo version.py")
    parser.add_argument("versao", help="Nova versão em formato SemVer")
    
    args = parser.parse_args()
    
    try:
        bump_version_file(args.arquivo, args.versao)
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
