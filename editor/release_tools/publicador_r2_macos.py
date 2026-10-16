# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para publicação dos artefatos estáticos do canal macOS no Cloudflare R2
e purgação imediata de cache na CDN Cloudflare.
"""

import os
from pathlib import Path
from typing import Any

import requests

BUCKET_PADRAO: str = "aresta-serving"
PREFIXO_PADRAO: str = "editor-macos"
URI_BASE_PADRAO: str = "https://serving.arestaclimb.com/editor-macos"


class PublicadorR2MacOS:
    """Gerencia o upload de artefatos macOS (.dmg e appcast.xml) para o Cloudflare R2 e purgação de CDN."""

    def __init__(
        self,
        cliente_s3: Any | None = None,
        bucket: str = BUCKET_PADRAO,
        prefixo: str = PREFIXO_PADRAO,
        zone_id: str | None = None,
        api_token: str | None = None,
        uri_base: str = URI_BASE_PADRAO,
    ) -> None:
        self.bucket = bucket
        self.prefixo = prefixo
        self.zone_id = zone_id or os.environ.get("CLOUDFLARE_ZONE_ID")
        self.api_token = (
            api_token
            or os.environ.get("CLOUDFLARE_CACHE_PURGE_API_TOKEN")
            or os.environ.get("CLOUDFLARE_API_TOKEN")
        )
        self.uri_base = uri_base.rstrip("/")
        self._cliente_s3 = cliente_s3

    @property
    def cliente_s3(self) -> Any:
        """Inicializa preguiçosamente o cliente S3 via boto3 se não fornecido externamente."""
        if self._cliente_s3 is None:
            import boto3

            endpoint = os.environ.get("R2_ENDPOINT_URL") or os.environ.get("CLOUDFLARE_S3_API_URL")
            if not endpoint:
                account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get(
                    "CLOUDFLARE_ACOUNT_ID"
                )
                if account_id:
                    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"

            access_key = os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get(
                "CLOUDFLARE_S3_ACCESS_KEY_ID"
            )
            secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get(
                "CLOUDFLARE_S3_SECRET_ACCESS_KEY"
            )

            self._cliente_s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name="auto",
            )
        return self._cliente_s3

    def publicar_artefatos(
        self,
        versao: str,
        caminho_dmg: Path | None = None,
        caminho_appcast: Path | None = None,
        caminho_dmg_arm64: Path | None = None,
        caminho_dmg_intel: Path | None = None,
    ) -> list[str]:
        """
        Envia os DMGs (ARM64, Intel e/ou legado) e o feed appcast.xml para o bucket Cloudflare R2.
        Retorna a lista de chaves publicadas.
        """
        chaves_publicadas: list[str] = []

        if caminho_dmg_arm64 and caminho_dmg_arm64.exists():
            chave_arm64 = f"{self.prefixo}/EditorAresta-{versao}-arm64.dmg"
            print(f"Enviando {caminho_dmg_arm64} -> s3://{self.bucket}/{chave_arm64}")
            self.cliente_s3.upload_file(
                str(caminho_dmg_arm64),
                self.bucket,
                chave_arm64,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            chaves_publicadas.append(chave_arm64)

            chave_arm64_latest = f"{self.prefixo}/EditorAresta-arm64-latest.dmg"
            print(f"Enviando {caminho_dmg_arm64} -> s3://{self.bucket}/{chave_arm64_latest}")
            self.cliente_s3.upload_file(
                str(caminho_dmg_arm64),
                self.bucket,
                chave_arm64_latest,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            chaves_publicadas.append(chave_arm64_latest)

            chave_latest = f"{self.prefixo}/EditorAresta-latest.dmg"
            print(f"Enviando {caminho_dmg_arm64} -> s3://{self.bucket}/{chave_latest}")
            self.cliente_s3.upload_file(
                str(caminho_dmg_arm64),
                self.bucket,
                chave_latest,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            chaves_publicadas.append(chave_latest)

        if caminho_dmg_intel and caminho_dmg_intel.exists():
            chave_intel = f"{self.prefixo}/EditorAresta-{versao}-intel.dmg"
            print(f"Enviando {caminho_dmg_intel} -> s3://{self.bucket}/{chave_intel}")
            self.cliente_s3.upload_file(
                str(caminho_dmg_intel),
                self.bucket,
                chave_intel,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            chaves_publicadas.append(chave_intel)

            chave_intel_latest = f"{self.prefixo}/EditorAresta-intel-latest.dmg"
            print(f"Enviando {caminho_dmg_intel} -> s3://{self.bucket}/{chave_intel_latest}")
            self.cliente_s3.upload_file(
                str(caminho_dmg_intel),
                self.bucket,
                chave_intel_latest,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            chaves_publicadas.append(chave_intel_latest)

        if caminho_dmg and caminho_dmg.exists():
            chave_versao = f"{self.prefixo}/EditorAresta-{versao}.dmg"
            print(f"Enviando {caminho_dmg} -> s3://{self.bucket}/{chave_versao}")
            self.cliente_s3.upload_file(
                str(caminho_dmg),
                self.bucket,
                chave_versao,
                ExtraArgs={"ContentType": "application/octet-stream"},
            )
            chaves_publicadas.append(chave_versao)

            if not (caminho_dmg_arm64 and caminho_dmg_arm64.exists()):
                chave_latest = f"{self.prefixo}/EditorAresta-latest.dmg"
                print(f"Enviando {caminho_dmg} -> s3://{self.bucket}/{chave_latest}")
                self.cliente_s3.upload_file(
                    str(caminho_dmg),
                    self.bucket,
                    chave_latest,
                    ExtraArgs={"ContentType": "application/octet-stream"},
                )
                chaves_publicadas.append(chave_latest)

        if caminho_appcast and caminho_appcast.exists():
            chave_appcast = f"{self.prefixo}/appcast.xml"
            print(f"Enviando {caminho_appcast} -> s3://{self.bucket}/{chave_appcast}")
            self.cliente_s3.upload_file(
                str(caminho_appcast),
                self.bucket,
                chave_appcast,
                ExtraArgs={
                    "ContentType": "application/xml",
                    "CacheControl": "max-age=60",
                },
            )
            chaves_publicadas.append(chave_appcast)

        return chaves_publicadas

    def purga_cache_cloudflare(self, versao: str) -> bool:
        """
        Solicita purgação de cache das URLs públicas do canal macOS na CDN Cloudflare.
        """
        if not self.zone_id or not self.api_token:
            print("[AVISO] CLOUDFLARE_ZONE_ID ou token não configurado. Pulando purgação de cache.")
            return False

        urls = [
            f"{self.uri_base}/EditorAresta-{versao}-arm64.dmg",
            f"{self.uri_base}/EditorAresta-arm64-latest.dmg",
            f"{self.uri_base}/EditorAresta-latest.dmg",
            f"{self.uri_base}/EditorAresta-{versao}-intel.dmg",
            f"{self.uri_base}/EditorAresta-intel-latest.dmg",
            f"{self.uri_base}/EditorAresta-{versao}.dmg",
            f"{self.uri_base}/appcast.xml",
        ]

        endpoint = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/purge_cache"
        try:
            resp = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
                json={"files": urls},
                timeout=30,
            )
            if resp.status_code == 200:
                print(
                    f"[OK] Cache da CDN Cloudflare purgado com sucesso para {len(urls)} arquivos."
                )
                return True
            print(f"[AVISO] Resposta inesperada ao purgar cache Cloudflare: {resp.status_code}")
            return False
        except requests.RequestException as e:
            print(f"[ERRO] Falha ao solicitar purgação de cache na CDN Cloudflare: {e}")
            return False

    def publicar_e_purgar(
        self,
        versao: str,
        caminho_dmg: Path | None = None,
        caminho_appcast: Path | None = None,
        caminho_dmg_arm64: Path | None = None,
        caminho_dmg_intel: Path | None = None,
    ) -> bool:
        """
        Executa o fluxo completo de upload para R2 e subsequente purgação de cache na CDN.
        """
        self.publicar_artefatos(
            versao=versao,
            caminho_dmg=caminho_dmg,
            caminho_appcast=caminho_appcast,
            caminho_dmg_arm64=caminho_dmg_arm64,
            caminho_dmg_intel=caminho_dmg_intel,
        )
        self.purga_cache_cloudflare(versao=versao)
        return True
