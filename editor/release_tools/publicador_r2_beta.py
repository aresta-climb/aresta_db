# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para publicação dos artefatos estáticos do canal Beta no Cloudflare R2
e purgação imediata de cache na CDN Cloudflare.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, List, Optional


BUCKET_PADRAO: str = "aresta-serving"
PREFIXO_PADRAO: str = "editor-beta"
URI_BASE_PADRAO: str = "https://serving.arestaclimb.com/editor-beta"


def determinar_tipo_conteudo(caminho: Path) -> str:
    """Retorna o Content-Type apropriado para os arquivos do canal Beta."""
    nome = caminho.name.lower()
    if nome.endswith(".appinstaller"):
        return "application/appinstaller"
    if nome.endswith(".msix"):
        return "application/msix"
    if nome.endswith(".bat") or nome.endswith(".cmd"):
        return "application/x-bat"
    return "application/octet-stream"


class PublicadorR2Beta:
    """Gerencia o upload para o Cloudflare R2 e a purgação de cache na CDN."""

    def __init__(
        self,
        cliente_s3: Optional[Any] = None,
        bucket: str = BUCKET_PADRAO,
        zone_id: Optional[str] = None,
        api_token: Optional[str] = None,
        uri_base: str = URI_BASE_PADRAO,
    ) -> None:
        self.bucket = bucket
        self.zone_id = zone_id or os.environ.get("CLOUDFLARE_ZONE_ID")
        self.api_token = api_token or os.environ.get("CLOUDFLARE_CACHE_PURGE_API_TOKEN")
        self.uri_base = uri_base.rstrip("/")
        self._cliente_s3 = cliente_s3

    @property
    def cliente_s3(self) -> Any:
        """Inicializa preguiçosamente o cliente S3 via boto3 se não fornecido externamente."""
        if self._cliente_s3 is None:
            import boto3
            from botocore.config import Config

            endpoint = os.environ.get("R2_ENDPOINT_URL")
            self._cliente_s3 = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
        return self._cliente_s3

    def enviar_arquivo(
        self,
        caminho_local: Path,
        chave_remota: str,
        tipo_conteudo: Optional[str] = None,
    ) -> None:
        """Envia um arquivo local para o bucket R2 com o cabeçalho Content-Type correto."""
        if not caminho_local.exists():
            raise FileNotFoundError(f"Arquivo local não encontrado para upload: {caminho_local}")

        tipo = tipo_conteudo or determinar_tipo_conteudo(caminho_local)
        self.cliente_s3.upload_file(
            str(caminho_local),
            self.bucket,
            chave_remota,
            ExtraArgs={"ContentType": tipo},
        )

    def purgar_cache(self, urls: List[str]) -> bool:
        """Dispara requisição de purgação de cache para a lista de URLs na Cloudflare."""
        if not self.zone_id or not self.api_token:
            raise ValueError("Credenciais da Cloudflare ausentes (zone_id ou api_token).")

        url_api = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/purge_cache"
        payload = json.dumps({"files": urls}).encode("utf-8")
        requisicao = urllib.request.Request(
            url_api,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(requisicao) as resposta:
                return resposta.status in (200, 201)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Falha ao purgar cache do Cloudflare ({e.code}): {e.reason}") from e

    def publicar_e_purgar(
        self,
        caminho_appinstaller: Path,
        caminho_msix: Path,
        caminho_bat: Optional[Path] = None,
    ) -> bool:
        """
        Executa a sequência completa de envio dos artefatos estáticos e invalidação do cache.
        """
        self.enviar_arquivo(caminho_appinstaller, f"{PREFIXO_PADRAO}/{caminho_appinstaller.name}")
        self.enviar_arquivo(caminho_msix, f"{PREFIXO_PADRAO}/{caminho_msix.name}")

        if caminho_bat and caminho_bat.exists():
            self.enviar_arquivo(caminho_bat, f"{PREFIXO_PADRAO}/{caminho_bat.name}")

        urls_para_purgar = [
            f"{self.uri_base}/{caminho_appinstaller.name}",
            f"{self.uri_base}/{caminho_msix.name}",
        ]

        return self.purgar_cache(urls_para_purgar)
