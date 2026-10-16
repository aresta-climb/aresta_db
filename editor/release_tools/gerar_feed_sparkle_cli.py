# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário de linha de comando para geração do feed Sparkle (appcast.xml) macOS.
Detecta e compõe itens independentes para Apple Silicon (arm64) e Intel (x86_64),
assina digitalmente os artefatos com chaves Ed25519 e salva o arquivo de feed XML.
"""

import argparse
import os
import sys
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path
_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from editor.release_tools.gerador_feed_sparkle import (
    ItemFeedSparkle,
    assinar_arquivo_ed25519,
    gerar_feed_sparkle_multi_arquitetura,
    salvar_feed_sparkle,
)

URI_BASE_PADRAO: str = "https://serving.arestaclimb.com/editor-macos"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera o feed oficial Sparkle (appcast.xml) para distribuição do Editor Aresta no macOS."
    )
    parser.add_argument(
        "--versao",
        required=True,
        help="Versão oficial de lançamento (ex: 0.5.14).",
    )
    parser.add_argument(
        "--diretorio-dist",
        default="dist_macos",
        help="Diretório onde os arquivos .dmg estão localizados (padrão: dist_macos).",
    )
    parser.add_argument(
        "--saida",
        required=False,
        help="Caminho de saída para o arquivo appcast.xml (padrão: <diretorio-dist>/appcast.xml).",
    )
    parser.add_argument(
        "--chave-privada",
        required=False,
        help="Chave privada Ed25519 em Base64 para assinatura Sparkle (ou use env SPARKLE_ED25519_PRIVATE_KEY).",
    )
    parser.add_argument(
        "--forcar-atualizacao",
        action="store_true",
        default=None,
        help="Marca a atualização como obrigatória/crítica no feed Sparkle.",
    )
    parser.add_argument(
        "--dmg-arm64",
        required=False,
        help="Caminho explícito para o arquivo DMG Apple Silicon (arm64).",
    )
    parser.add_argument(
        "--dmg-intel",
        required=False,
        help="Caminho explícito para o arquivo DMG Intel (x86_64).",
    )
    parser.add_argument(
        "--dmg",
        required=False,
        help="Caminho explícito para o arquivo DMG legado (sem distinção de arquitetura).",
    )
    parser.add_argument(
        "--uri-base",
        default=URI_BASE_PADRAO,
        help=f"URL base de download dos artefatos (padrão: {URI_BASE_PADRAO}).",
    )

    args = parser.parse_args(argv)

    diretorio_dist = Path(args.diretorio_dist)
    caminho_saida = Path(args.saida) if args.saida else (diretorio_dist / "appcast.xml")

    chave_privada = (
        args.chave_privada or os.environ.get("SPARKLE_ED25519_PRIVATE_KEY", "")
    ).strip()

    if args.forcar_atualizacao is not None:
        forcar = args.forcar_atualizacao
    else:
        forcar = os.environ.get("FORCAR_ATUALIZACAO", "true").lower() != "false"

    uri_base = args.uri_base.rstrip("/")

    # 1. Identifica artefatos
    caminho_arm64 = (
        Path(args.dmg_arm64)
        if args.dmg_arm64
        else (diretorio_dist / f"EditorAresta-{args.versao}-arm64.dmg")
    )
    caminho_intel = (
        Path(args.dmg_intel)
        if args.dmg_intel
        else (diretorio_dist / f"EditorAresta-{args.versao}-intel.dmg")
    )
    caminho_legado = (
        Path(args.dmg) if args.dmg else (diretorio_dist / f"EditorAresta-{args.versao}.dmg")
    )

    itens: list[ItemFeedSparkle] = []

    if caminho_arm64.exists():
        sig_arm64 = (
            assinar_arquivo_ed25519(caminho_arm64, chave_privada)
            if chave_privada
            else "MOCK_SIGNATURE_DRY_RUN"
        )
        itens.append(
            ItemFeedSparkle(
                versao=args.versao,
                url_download=f"{uri_base}/{caminho_arm64.name}",
                tamanho_bytes=caminho_arm64.stat().st_size,
                assinatura_ed25519=sig_arm64,
                arquitetura="arm64",
                forcar_atualizacao=forcar,
            )
        )

    if caminho_intel.exists():
        sig_intel = (
            assinar_arquivo_ed25519(caminho_intel, chave_privada)
            if chave_privada
            else "MOCK_SIGNATURE_DRY_RUN"
        )
        itens.append(
            ItemFeedSparkle(
                versao=args.versao,
                url_download=f"{uri_base}/{caminho_intel.name}",
                tamanho_bytes=caminho_intel.stat().st_size,
                assinatura_ed25519=sig_intel,
                arquitetura="x86_64",
                forcar_atualizacao=forcar,
            )
        )

    if not itens and caminho_legado.exists():
        sig_legado = (
            assinar_arquivo_ed25519(caminho_legado, chave_privada)
            if chave_privada
            else "MOCK_SIGNATURE_DRY_RUN"
        )
        itens.append(
            ItemFeedSparkle(
                versao=args.versao,
                url_download=f"{uri_base}/{caminho_legado.name}",
                tamanho_bytes=caminho_legado.stat().st_size,
                assinatura_ed25519=sig_legado,
                arquitetura=None,
                forcar_atualizacao=forcar,
            )
        )

    if not itens:
        raise FileNotFoundError(
            f"Nenhum arquivo DMG encontrado em '{diretorio_dist}' para compor o feed Sparkle!"
        )

    xml = gerar_feed_sparkle_multi_arquitetura(itens)
    salvar_feed_sparkle(xml, caminho_saida)
    print(
        f"[OK] Feed Sparkle gerado com sucesso em '{caminho_saida}' contendo {len(itens)} item(ns)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
