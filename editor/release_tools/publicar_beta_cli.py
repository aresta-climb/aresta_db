# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário de linha de comando para orquestrar a geração dos manifestos e artefatos
do canal Beta e sua publicação imediata no Cloudflare R2 com purgação de CDN.
"""

import argparse
import base64
import sys
from pathlib import Path
from typing import List, Optional

from editor.release_tools.gerador_appinstaller import gerar_conteudo_appinstaller
from editor.release_tools.gerador_instalador_bat import (
    gerar_script_instalador_bat,
    URL_SUCESSO_PADRAO,
)
from editor.release_tools.publicador_r2_beta import PublicadorR2Beta


def converter_bytes_para_pem(dados_der: bytes) -> str:
    """Converte bytes de certificado binário DER para formato PEM textual."""
    b64 = base64.encodebytes(dados_der).decode("ascii").strip()
    return f"-----BEGIN CERTIFICATE-----\n{b64}\n-----END CERTIFICATE-----"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publica o pacote Beta no Cloudflare R2 e purga o cache da CDN."
    )
    parser.add_argument("--versao", required=True, help="Versão oficial de lançamento.")
    parser.add_argument("--msix", required=True, help="Caminho para o arquivo EditorArestaBeta.msix.")
    parser.add_argument("--cer", required=False, help="Caminho para o arquivo de certificado .cer público.")
    parser.add_argument("--url-sucesso", default=URL_SUCESSO_PADRAO, help="URL de redirecionamento do .bat.")
    parser.add_argument("--diretorio-saida", default=".", help="Diretório onde os artefatos serão gerados.")

    args = parser.parse_args(argv)

    caminho_msix = Path(args.msix).resolve()
    if not caminho_msix.exists():
        raise FileNotFoundError(f"Arquivo MSIX não encontrado: {caminho_msix}")

    diretorio_saida = Path(args.diretorio_saida).resolve()
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    # 1. Gera EditorAresta.appinstaller
    caminho_appinstaller = diretorio_saida / "EditorAresta.appinstaller"
    conteudo_appinstaller = gerar_conteudo_appinstaller(args.versao)
    caminho_appinstaller.write_text(conteudo_appinstaller, encoding="utf-8")
    print(f"Manifesto AppInstaller gerado em: {caminho_appinstaller}")

    # 2. Gera InstalarCertificadoEditorArestaBeta.bat se certificado for fornecido
    caminho_bat: Optional[Path] = None
    if args.cer:
        caminho_cer = Path(args.cer).resolve()
        if caminho_cer.exists():
            dados_cer = caminho_cer.read_bytes()
            # Se já for texto PEM, usa diretamente; senão codifica DER em PEM
            try:
                texto_cer = dados_cer.decode("utf-8")
                if "-----BEGIN CERTIFICATE-----" in texto_cer:
                    conteudo_pem = texto_cer
                else:
                    conteudo_pem = converter_bytes_para_pem(dados_cer)
            except UnicodeDecodeError:
                conteudo_pem = converter_bytes_para_pem(dados_cer)

            conteudo_bat = gerar_script_instalador_bat(conteudo_pem, url_sucesso=args.url_sucesso)
            caminho_bat = diretorio_saida / "InstalarCertificadoEditorArestaBeta.bat"
            caminho_bat.write_text(conteudo_bat, encoding="utf-8")
            print(f"Instalador .bat gerado em: {caminho_bat}")

    # 3. Publica no Cloudflare R2 e purga cache
    print("Iniciando upload para Cloudflare R2 e purgação de cache...")
    publicador = PublicadorR2Beta()
    sucesso = publicador.publicar_e_purgar(
        caminho_appinstaller=caminho_appinstaller,
        caminho_msix=caminho_msix,
        caminho_bat=caminho_bat,
    )

    if not sucesso:
        print("Erro: A publicação ou purgação do canal Beta falhou.")
        return 1

    print("Canal Beta publicado e purgado com sucesso no Cloudflare R2!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
