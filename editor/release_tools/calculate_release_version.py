# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Union, List
import re
import sys
import argparse
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path para importação absoluta do módulo editor
_raiz_repo = str(Path(__file__).resolve().parents[2])
if _raiz_repo not in sys.path:  # pragma: no cover
    sys.path.insert(0, _raiz_repo)

from editor.release_tools.bump_version import compare_semver, validar_semver, SemVerError

PADRAO_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9.-]+))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

def extrair_versao_de_arquivo(caminho_arquivo: Union[str, Path]) -> str:
    """Extrai a string de versão definida na constante VERSION de um arquivo Python."""
    caminho = Path(caminho_arquivo)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    conteudo = caminho.read_text(encoding="utf-8")
    padrao = re.compile(r'^(?:VERSION(?:\s*:\s*[^=\r\n]+)?\s*=\s*)"(.*)"', re.MULTILINE)
    match = padrao.search(conteudo)
    if not match:
        raise ValueError(f"Padrão VERSION não encontrado no arquivo {caminho}")

    return match.group(1).strip()

def calcular_versao_release(versao_atual: str, tipo_bump: str, custom: Optional[str] = None) -> str:
    """
    Calcula a versão oficial de release baseada na versão atual e no tipo de incremento.
    Tipos suportados: 'patch', 'minor', 'major', 'custom'.
    """
    match_atual = PADRAO_SEMVER.match(versao_atual)
    if not match_atual:
        raise ValueError(f"Versão atual inválida ({versao_atual}): não segue o formato SemVer.")

    major = int(match_atual.group(1))
    minor = int(match_atual.group(2))
    patch = int(match_atual.group(3))
    prerelease = match_atual.group(4)
    eh_dev = bool(prerelease)

    tipo = tipo_bump.lower().strip()

    if tipo == "patch":
        if eh_dev:
            # Em ciclo de desenvolvimento contínuo (ex: 0.2.1-dev), o patch já foi incrementado
            return f"{major}.{minor}.{patch}"
        return f"{major}.{minor}.{patch + 1}"

    elif tipo == "minor":
        return f"{major}.{minor + 1}.0"

    elif tipo == "major":
        return f"{major + 1}.0.0"

    elif tipo == "custom":
        if not custom or not custom.strip():
            raise ValueError("Versão customizada obrigatória quando tipo for 'custom'.")
        versao_custom = custom.strip()
        try:
            validar_semver(versao_custom)
        except SemVerError as e:
            raise ValueError(f"A versão customizada {versao_custom} não segue o formato SemVer válido: {e}")

        if compare_semver(versao_custom, versao_atual) <= 0:
            raise ValueError(f"A versão customizada ({versao_custom}) deve ser estritamente maior que a atual ({versao_atual}).")

        return versao_custom

    else:
        raise ValueError(f"Tipo de incremento inválido: '{tipo_bump}'. Use patch, minor, major ou custom.")

def main(argv: Optional[List[str]] = None) -> int:
    """Função principal da CLI de cálculo de versão de release."""
    parser = argparse.ArgumentParser(description="Calcula a versão oficial de lançamento do Editor Aresta.")
    parser.add_argument("--tipo", default="patch", choices=["patch", "minor", "major", "custom"], help="Tipo de incremento (patch, minor, major, custom)")
    parser.add_argument("--custom", default=None, help="Versão customizada (obrigatória se tipo=custom)")
    parser.add_argument("--versao-atual", default=None, help="Versão atual explícita para cálculo")
    parser.add_argument("--arquivo", default=None, help="Caminho do arquivo de versão (padrão: editor/core/version.py)")

    args = parser.parse_args(argv)

    try:
        if args.versao_atual:
            versao_base = args.versao_atual
        else:
            caminho_padrao = Path(args.arquivo) if args.arquivo else Path(__file__).resolve().parent.parent / "core" / "version.py"
            versao_base = extrair_versao_de_arquivo(caminho_padrao)

        versao_calculada = calcular_versao_release(versao_base, args.tipo, args.custom)
        print(versao_calculada)
        return 0
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

