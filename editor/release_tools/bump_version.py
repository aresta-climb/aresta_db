# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Union, List, Tuple
import re
import argparse
import sys
from pathlib import Path

class SemVerError(Exception):
    pass

def validar_semver(versao: str) -> None:
    semver_pattern = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )
    if not semver_pattern.match(versao):
        raise SemVerError(f"A versão {versao} não segue o formato SemVer válido.")

def compare_semver(v1: str, v2: str) -> int:
    def parse(v: str) -> Optional[Tuple[int, int, int, Optional[str]]]:
        m = re.match(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9.-]+))?", v)
        if not m: return None
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
        
    p1 = parse(v1)
    p2 = parse(v2)
    
    if p1 is None or p2 is None:
        return 0
    
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

def bump_version_file(caminho_arquivo: Union[str, Path], nova_versao: str) -> None:
    validar_semver(nova_versao)
    caminho = Path(caminho_arquivo)
    
    with open(caminho, 'r', encoding='utf-8') as f:
        conteudo = f.read()
        
    if caminho.suffix.lower() == ".toml" or caminho.name.lower() == "pyproject.toml":
        padrao = re.compile(r'^version\s*=\s*"(.*)"', re.MULTILINE)
        if not padrao.search(conteudo):
            raise ValueError(f"Padrão version = \".*\" não encontrado no arquivo {caminho_arquivo}")
        substituto = f'version = "{nova_versao}"'
    else:
        padrao = re.compile(r'^VERSION\s*=\s*"(.*)"', re.MULTILINE)
        if not padrao.search(conteudo):
            raise ValueError(f"Padrão VERSION = \".*\" não encontrado no arquivo {caminho_arquivo}")
        substituto = f'VERSION = "{nova_versao}"'
        
    match_atual = padrao.search(conteudo)
    if not match_atual:
        raise ValueError(f"Versão não encontrada no arquivo {caminho_arquivo}")
    versao_atual = match_atual.group(1)
    if compare_semver(nova_versao, versao_atual) <= 0:
        raise SemVerError(f"A nova versão ({nova_versao}) deve ser estritamente maior que a atual ({versao_atual}).")
        
    novo_conteudo = padrao.sub(substituto, conteudo)
    
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)
        
    print(f"Versão atualizada de {versao_atual} para {nova_versao} no arquivo {caminho_arquivo}")

def sincronizar_versoes(nova_versao: str, raiz: Optional[Union[str, Path]] = None) -> List[Path]:
    """Atualiza e sincroniza a versão tanto em editor/core/version.py quanto em pyproject.toml."""
    validar_semver(nova_versao)
    dir_raiz = Path(raiz) if raiz else Path(__file__).resolve().parent.parent.parent
    caminho_version_py = dir_raiz / "editor" / "core" / "version.py"
    caminho_pyproject = dir_raiz / "pyproject.toml"
    
    atualizados: List[Path] = []
    if caminho_version_py.exists():
        bump_version_file(caminho_version_py, nova_versao)
        atualizados.append(caminho_version_py)
        
    if caminho_pyproject.exists():
        bump_version_file(caminho_pyproject, nova_versao)
        atualizados.append(caminho_pyproject)
        
    return atualizados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atualiza e sincroniza a versão do Editor Aresta (version.py e pyproject.toml).")
    parser.add_argument("argumentos", nargs="+", help="[caminho_arquivo] <nova_versao>")
    
    args = parser.parse_args()
    
    try:
        if len(args.argumentos) == 1:
            nova_versao = args.argumentos[0]
            sincronizar_versoes(nova_versao)
        elif len(args.argumentos) == 2:
            arquivo_alvo = Path(args.argumentos[0])
            nova_versao = args.argumentos[1]
            bump_version_file(arquivo_alvo, nova_versao)
            
            # Auto-sincronização de arquivos conhecidos do repositório
            dir_raiz = Path(__file__).resolve().parent.parent.parent
            if arquivo_alvo.resolve() == (dir_raiz / "editor" / "core" / "version.py").resolve():
                caminho_toml = dir_raiz / "pyproject.toml"
                if caminho_toml.exists():
                    bump_version_file(caminho_toml, nova_versao)
            elif arquivo_alvo.resolve() == (dir_raiz / "pyproject.toml").resolve():
                caminho_py = dir_raiz / "editor" / "core" / "version.py"
                if caminho_py.exists():
                    bump_version_file(caminho_py, nova_versao)
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
