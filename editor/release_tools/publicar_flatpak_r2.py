# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para publicação do repositório Flatpak OSTree no Cloudflare R2
e purgação seletiva de cache na CDN Cloudflare.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BUCKET_PADRAO: str = "aresta-serving"
PREFIXO_PADRAO: str = "flatpak"
URI_BASE_PADRAO: str = "https://serving.arestaclimb.com/flatpak"
URL_RUNTIME_REPO_PADRAO: str = "https://dl.flathub.org/repo/flathub.flatpakrepo"
CACHE_CONTROL_PADRAO: str = "public, max-age=31536000, immutable"


def determinar_tipo_conteudo_flatpak(caminho: Path) -> str:
    """Retorna o Content-Type apropriado para os arquivos do repositório Flatpak e metadados."""
    nome = caminho.name.lower()
    if nome.endswith(".json"):
        return "application/json"
    if nome.endswith(".flatpakref") or nome.endswith(".flatpakrepo"):
        return "text/plain; charset=utf-8"
    if nome.endswith(".png"):
        return "image/png"
    return "application/octet-stream"


def verificar_estado_repositorio_remoto(url_summary: str) -> bool:
    """
    Verifica se o repositório remoto já existe consultando a URL do arquivo summary via HTTP.
    Retorna True se HTTP 200 (existente), False se HTTP 404 (novo/bootstrap) ou lança RuntimeError
    em caso de falha de rede ou erro inesperado de servidor, prevenindo o uso de || true.
    """
    requisicao = urllib.request.Request(url_summary, method="HEAD")
    requisicao.add_header("User-Agent", "Aresta-CI-Publisher/1.0")

    try:
        with urllib.request.urlopen(requisicao, timeout=5) as resposta:
            return bool(resposta.status == 200)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise RuntimeError(f"Falha ao checar repositório remoto ({e.code}): {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Erro de rede ao verificar repositório remoto: {e.reason}") from e


def gerar_conteudo_version_json(
    versao: str,
    obrigatoria: bool = True,
    mensagem: str | None = None,
) -> str:
    """Gera a estrutura JSON do arquivo de controle de versão remota para auto-update in-app."""
    payload: dict[str, Any] = {
        "versao": versao,
        "obrigatoria": obrigatoria,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if mensagem:
        payload["mensagem"] = mensagem
    return json.dumps(payload, indent=2, ensure_ascii=False)


def gerar_conteudo_flatpakref(
    nome_app: str,
    branch: str,
    titulo: str,
    url_repo: str,
    chave_gpg_base64: str,
    runtime_repo: str = URL_RUNTIME_REPO_PADRAO,
) -> str:
    """Gera o conteúdo textual no formato padrão INI de um arquivo .flatpakref."""
    return (
        "[Flatpak Ref]\n"
        f"Name={nome_app}\n"
        f"Branch={branch}\n"
        f"Title={titulo}\n"
        f"Url={url_repo}\n"
        "IsRuntime=false\n"
        f"GPGKey={chave_gpg_base64}\n"
        f"RuntimeRepo={runtime_repo}\n"
    )


def gerar_conteudo_flatpakrepo(
    titulo: str,
    url_repo: str,
    homepage: str,
    comentario: str,
    descricao: str,
    url_icone: str,
    chave_gpg_base64: str,
) -> str:
    """Gera o conteúdo textual no formato padrão INI de um arquivo .flatpakrepo."""
    return (
        "[Flatpak Repo]\n"
        f"Title={titulo}\n"
        f"Url={url_repo}\n"
        f"Homepage={homepage}\n"
        f"Comment={comentario}\n"
        f"Description={descricao}\n"
        f"Icon={url_icone}\n"
        f"GPGKey={chave_gpg_base64}\n"
    )


class PublicadorFlatpakR2:
    """Gerencia a sincronização do repositório OSTree para o R2 e invalidação de cache."""

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
        self.prefixo = prefixo.strip("/")
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
        """Inicializa preguiçosamente o cliente S3 via boto3."""
        if self._cliente_s3 is None:
            import boto3
            from botocore.config import Config

            endpoint = os.environ.get("R2_ENDPOINT_URL") or os.environ.get("CLOUDFLARE_S3_API_URL")
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
                config=Config(signature_version="s3v4"),
            )
        return self._cliente_s3

    def sincronizar_diretorio_ostree(self, diretorio_repo: Path) -> list[str]:
        """
        Percorre os arquivos do repositório local e envia para o R2.
        Para arquivos sob objects/, verifica se a chave já existe para evitar re-uploads.
        Arquivos de índice e metadados são sempre enviados.
        """
        if not diretorio_repo.exists() or not diretorio_repo.is_dir():
            raise FileNotFoundError(f"Diretório de repositório inexistente: {diretorio_repo}")

        chaves_enviadas: list[str] = []

        for caminho_arquivo in diretorio_repo.rglob("*"):
            if not caminho_arquivo.is_file():
                continue

            caminho_relativo = caminho_arquivo.relative_to(diretorio_repo).as_posix()
            chave_remota = f"{self.prefixo}/repo/{caminho_relativo}"

            # Se for um objeto imutável de CAS, verifica se já existe
            if caminho_relativo.startswith("objects/"):
                try:
                    self.cliente_s3.head_object(Bucket=self.bucket, Key=chave_remota)
                    # Já existe no bucket, pula o upload
                    continue
                except Exception:
                    pass

            tipo = determinar_tipo_conteudo_flatpak(caminho_arquivo)
            self.cliente_s3.upload_file(
                str(caminho_arquivo),
                self.bucket,
                chave_remota,
                ExtraArgs={
                    "ContentType": tipo,
                    "CacheControl": CACHE_CONTROL_PADRAO,
                },
            )
            chaves_enviadas.append(chave_remota)

        return chaves_enviadas

    def publicar_metadados(
        self,
        versao: str,
        chave_gpg_base64: str,
        diretorio_saida: Path,
        obrigatoria: bool = True,
        mensagem: str | None = None,
    ) -> dict[str, Path]:
        """Gera os metadados localmente e faz o upload para a raiz do prefixo flatpak."""
        diretorio_saida.mkdir(parents=True, exist_ok=True)

        caminho_version = diretorio_saida / "version.json"
        caminho_version.write_text(
            gerar_conteudo_version_json(versao, obrigatoria=obrigatoria, mensagem=mensagem),
            encoding="utf-8",
        )

        caminho_flatpakref = diretorio_saida / "com.arestaclimb.Editor.flatpakref"
        caminho_flatpakref.write_text(
            gerar_conteudo_flatpakref(
                nome_app="com.arestaclimb.Editor",
                branch="stable",
                titulo="Editor Aresta",
                url_repo=f"{self.uri_base}/repo",
                chave_gpg_base64=chave_gpg_base64,
            ),
            encoding="utf-8",
        )

        caminho_flatpakrepo = diretorio_saida / "aresta.flatpakrepo"
        caminho_flatpakrepo.write_text(
            gerar_conteudo_flatpakrepo(
                titulo="Aresta Climb",
                url_repo=f"{self.uri_base}/repo",
                homepage="https://arestaclimb.com",
                comentario="Repositório oficial de aplicativos Aresta Climb",
                descricao="Repositório Flatpak oficial do Editor Aresta",
                url_icone=f"{self.uri_base}/logo.png",
                chave_gpg_base64=chave_gpg_base64,
            ),
            encoding="utf-8",
        )

        arquivos = {
            "version.json": caminho_version,
            "com.arestaclimb.Editor.flatpakref": caminho_flatpakref,
            "aresta.flatpakrepo": caminho_flatpakrepo,
        }

        for nome, caminho in arquivos.items():
            chave_remota = f"{self.prefixo}/{nome}"
            tipo = determinar_tipo_conteudo_flatpak(caminho)
            self.cliente_s3.upload_file(
                str(caminho),
                self.bucket,
                chave_remota,
                ExtraArgs={
                    "ContentType": tipo,
                    "CacheControl": CACHE_CONTROL_PADRAO,
                },
            )

        return arquivos

    def purgar_cache(self, urls: list[str]) -> bool:
        """Dispara requisição de purgação de cache para as URLs na Cloudflare."""
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
            with urllib.request.urlopen(requisicao, timeout=10) as resposta:
                return resposta.status in (200, 201)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Falha ao purgar cache do Cloudflare ({e.code}): {e.reason}") from e

    def obter_urls_purga(self) -> list[str]:
        """Retorna as URLs canônicas mutáveis que devem ser purgadas a cada deploy."""
        return [
            f"{self.uri_base}/repo/summary",
            f"{self.uri_base}/repo/summary.sig",
            f"{self.uri_base}/version.json",
            f"{self.uri_base}/com.arestaclimb.Editor.flatpakref",
            f"{self.uri_base}/aresta.flatpakrepo",
        ]
