# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário de linha de comando para publicação imediata dos artefatos macOS
(imagem .dmg e feed appcast.xml) no Cloudflare R2 com purgação de cache na CDN.
"""

import argparse
import sys
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path
_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from editor.release_tools.publicador_r2_macos import PublicadorR2MacOS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publica os artefatos macOS no Cloudflare R2 e purga o cache da CDN."
    )
    parser.add_argument(
        "--versao", required=True, help="Versão oficial de lançamento (ex: 0.5.13)."
    )
    parser.add_argument(
        "--diretorio-dist",
        default="dist_macos",
        help="Diretório onde os artefatos foram gerados (padrão: dist_macos).",
    )
    parser.add_argument(
        "--dmg",
        required=False,
        help="Caminho explícito para o arquivo .dmg legado (opcional).",
    )
    parser.add_argument(
        "--dmg-arm64",
        required=False,
        help="Caminho explícito para o arquivo .dmg ARM64 (opcional).",
    )
    parser.add_argument(
        "--dmg-intel",
        required=False,
        help="Caminho explícito para o arquivo .dmg Intel (opcional).",
    )
    parser.add_argument(
        "--appcast",
        required=False,
        help="Caminho explícito para o arquivo appcast.xml (opcional).",
    )

    args = parser.parse_args(argv)

    diretorio_dist = Path(args.diretorio_dist)
    caminho_dmg = Path(args.dmg) if args.dmg else diretorio_dist / f"EditorAresta-{args.versao}.dmg"
    caminho_dmg_arm64 = (
        Path(args.dmg_arm64)
        if args.dmg_arm64
        else diretorio_dist / f"EditorAresta-{args.versao}-arm64.dmg"
    )
    caminho_dmg_intel = (
        Path(args.dmg_intel)
        if args.dmg_intel
        else diretorio_dist / f"EditorAresta-{args.versao}-intel.dmg"
    )
    caminho_appcast = Path(args.appcast) if args.appcast else diretorio_dist / "appcast.xml"

    print(f"Publicando canal macOS para a versão {args.versao}...")
    publicador = PublicadorR2MacOS()
    publicador.publicar_e_purgar(
        versao=args.versao,
        caminho_dmg=caminho_dmg,
        caminho_appcast=caminho_appcast,
        caminho_dmg_arm64=caminho_dmg_arm64,
        caminho_dmg_intel=caminho_dmg_intel,
    )
    print("Publicação do canal macOS concluída com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
