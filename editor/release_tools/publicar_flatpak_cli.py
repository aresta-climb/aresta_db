# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário de linha de comando para bootstrap e publicação do repositório Flatpak OSTree
no Cloudflare R2 e purgação seletiva de cache na CDN.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from editor.release_tools.publicar_flatpak_r2 import (
    PublicadorFlatpakR2,
    verificar_estado_repositorio_remoto,
)

URL_SUMMARY_PADRAO: str = "https://serving.arestaclimb.com/flatpak/repo/summary"
URL_REPO_PADRAO: str = "https://serving.arestaclimb.com/flatpak/repo"
REF_APP_PADRAO: str = "app/com.arestaclimb.Editor/x86_64/stable"


def executar_bootstrap(
    repo_dir: Path,
    url_summary: str = URL_SUMMARY_PADRAO,
    url_repo: str = URL_REPO_PADRAO,
    ref_app: str = REF_APP_PADRAO,
) -> None:
    """
    Verifica se o repositório remoto já existe no Cloudflare R2.
    Se existir, configura o remoto e faz pull do commit anterior para geração de static deltas.
    Caso contrário, inicializa um repositório limpo em modo archive-z2.
    """
    repo_dir = repo_dir.resolve()
    repo_dir.mkdir(parents=True, exist_ok=True)

    existe = verificar_estado_repositorio_remoto(url_summary)
    if existe:
        print("Repositório remoto encontrado no R2. Puxando commit anterior para static deltas...")
        subprocess.run(
            ["ostree", f"--repo={repo_dir}", "remote", "add", "--if-not-exists", "aresta-remote", url_repo],
            check=True,
        )
        subprocess.run(
            ["ostree", f"--repo={repo_dir}", "pull", "--mirror", "aresta-remote", ref_app],
            check=True,
        )
    else:
        print("Primeira publicação histórica detectada. Inicializando repositório limpo...")
        subprocess.run(
            ["ostree", f"--repo={repo_dir}", "init", "--mode=archive-z2"],
            check=True,
        )


def executar_publicacao(
    versao: str,
    repo_dir: Path,
    chave_gpg_base64: str,
    diretorio_meta: Path = Path("dist_flatpak_meta"),
    caminho_icone: Path | None = Path("editor/flatpak/logo_app.png"),
    publicador: PublicadorFlatpakR2 | None = None,
) -> None:
    """
    Sincroniza o repositório OSTree para o R2 em paralelo, gera e publica os metadados
    (.flatpakref, .flatpakrepo, version.json, logo.png) e purga o cache na CDN da Cloudflare.
    """
    if not chave_gpg_base64 or not chave_gpg_base64.strip():
        raise ValueError(
            "A chave pública GPG (em base64) é obrigatória para gerar metadados Flatpak assinados."
        )

    pub = publicador or PublicadorFlatpakR2()

    print(f"Sincronizando repositório OSTree ({repo_dir}) para o Cloudflare R2...")
    chaves = pub.sincronizar_diretorio_ostree(repo_dir)
    print(f"Upload concluído: {len(chaves)} arquivos sincronizados.")

    print(f"Gerando e publicando metadados da versão {versao}...")
    arquivos_meta = pub.publicar_metadados(
        versao=versao,
        chave_gpg_base64=chave_gpg_base64,
        diretorio_saida=diretorio_meta,
        caminho_icone=caminho_icone,
        obrigatoria=True,
    )
    print(f"Metadados publicados: {list(arquivos_meta.keys())}")

    if pub.zone_id and pub.api_token:
        urls = pub.obter_urls_purga()
        pub.purgar_cache(urls)
        print(f"Purgação de cache executada com sucesso para {len(urls)} URLs na Cloudflare.")
    else:
        print("Credenciais da Cloudflare ausentes para purgar cache.")


def gerar_bundle_flatpak(
    repo_dir: Path,
    caminho_saida_bundle: Path,
    app_id: str = "com.arestaclimb.Editor",
    branch: str = "stable",
    chave_gpg_id: str | None = None,
    runtime_repo: str = "https://dl.flathub.org/repo/flathub.flatpakrepo",
) -> Path:
    """
    Gera o arquivo bundle autossuficiente (.flatpak) assinado a partir do repositório OSTree local.
    """
    caminho_saida_bundle = caminho_saida_bundle.resolve()
    caminho_saida_bundle.parent.mkdir(parents=True, exist_ok=True)

    comando = ["flatpak", "build-bundle"]
    if chave_gpg_id:
        comando.append(f"--gpg-sign={chave_gpg_id}")
    if runtime_repo:
        comando.append(f"--runtime-repo={runtime_repo}")
    comando.extend([str(repo_dir.resolve()), str(caminho_saida_bundle), app_id, branch])

    print(f"Gerando bundle Flatpak em {caminho_saida_bundle}...")
    subprocess.run(comando, check=True)
    print(f"Bundle Flatpak gerado com sucesso: {caminho_saida_bundle}")
    return caminho_saida_bundle


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI para gerenciamento do repositório Flatpak."""
    parser = argparse.ArgumentParser(
        description="Utilitário de bootstrap e publicação do repositório Flatpak no Cloudflare R2."
    )
    subparsers = parser.add_subparsers(dest="subcomando", help="Comando a ser executado")

    # Subcomando: bootstrap
    parser_boot = subparsers.add_parser(
        "bootstrap", help="Inicializa ou atualiza o repositório OSTree local a partir do R2."
    )
    parser_boot.add_argument(
        "--repo-dir",
        type=Path,
        default=Path("repo"),
        help="Caminho para o diretório do repositório OSTree local.",
    )
    parser_boot.add_argument(
        "--url-summary",
        default=URL_SUMMARY_PADRAO,
        help="URL do arquivo summary remoto para checagem de existência.",
    )
    parser_boot.add_argument(
        "--url-repo",
        default=URL_REPO_PADRAO,
        help="URL do repositório OSTree remoto.",
    )
    parser_boot.add_argument(
        "--ref-app",
        default=REF_APP_PADRAO,
        help="Referência do aplicativo no OSTree (ex: app/com.arestaclimb.Editor/x86_64/stable).",
    )

    # Subcomando: publicar
    parser_pub = subparsers.add_parser(
        "publicar", help="Sincroniza o repositório com o R2, publica metadados e purga CDN."
    )
    parser_pub.add_argument(
        "--versao",
        required=True,
        help="Versão oficial de lançamento do aplicativo.",
    )
    parser_pub.add_argument(
        "--repo-dir",
        type=Path,
        default=Path("repo"),
        help="Caminho para o diretório do repositório OSTree local.",
    )
    parser_pub.add_argument(
        "--chave-gpg-b64",
        default=os.environ.get("GPG_PUBLIC_B64", ""),
        help="Chave pública GPG codificada em Base64 para os metadados .flatpakref e .flatpakrepo.",
    )
    parser_pub.add_argument(
        "--diretorio-meta",
        type=Path,
        default=Path("dist_flatpak_meta"),
        help="Diretório onde os arquivos de metadados serão gerados localmente.",
    )
    parser_pub.add_argument(
        "--caminho-icone",
        type=Path,
        default=Path("editor/flatpak/logo_app.png"),
        help="Caminho para o ícone PNG da aplicação a ser publicado como logo.png no repositório Flatpak.",
    )

    # Subcomando: empacotar
    parser_bundle = subparsers.add_parser(
        "empacotar", help="Gera o arquivo bundle autossuficiente (.flatpak) a partir do OSTree."
    )
    parser_bundle.add_argument(
        "--repo-dir",
        type=Path,
        default=Path("repo"),
        help="Caminho para o diretório do repositório OSTree local.",
    )
    parser_bundle.add_argument(
        "--saida",
        type=Path,
        required=True,
        help="Caminho do arquivo .flatpak de saída.",
    )
    parser_bundle.add_argument(
        "--chave-gpg-id",
        default=os.environ.get("GPG_KEY_ID"),
        help="ID da chave GPG para assinar o bundle.",
    )
    parser_bundle.add_argument(
        "--app-id",
        default="com.arestaclimb.Editor",
        help="ID do aplicativo Flatpak.",
    )
    parser_bundle.add_argument(
        "--branch",
        default="stable",
        help="Branch do aplicativo.",
    )
    parser_bundle.add_argument(
        "--runtime-repo",
        default="https://dl.flathub.org/repo/flathub.flatpakrepo",
        help="URL do repositório de runtime para download automático de dependências.",
    )

    args = parser.parse_args(argv)

    if args.subcomando == "bootstrap":
        executar_bootstrap(
            repo_dir=args.repo_dir,
            url_summary=args.url_summary,
            url_repo=args.url_repo,
            ref_app=args.ref_app,
        )
        return 0

    if args.subcomando == "publicar":
        executar_publicacao(
            versao=args.versao,
            repo_dir=args.repo_dir,
            chave_gpg_base64=args.chave_gpg_b64,
            diretorio_meta=args.diretorio_meta,
            caminho_icone=args.caminho_icone,
        )
        return 0

    if args.subcomando == "empacotar":
        gerar_bundle_flatpak(
            repo_dir=args.repo_dir,
            caminho_saida_bundle=args.saida,
            app_id=args.app_id,
            branch=args.branch,
            chave_gpg_id=args.chave_gpg_id,
            runtime_repo=args.runtime_repo,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
