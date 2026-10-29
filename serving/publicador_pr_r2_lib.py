# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para publicação de artefatos compilados de uma Pull Request em `pr/<id>/`
no Cloudflare R2 e limpeza integral quando a Pull Request é fechada.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

_TIPOS_MIME_POR_EXTENSAO: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".yaml": "text/yaml; charset=utf-8",
    ".yml": "text/yaml; charset=utf-8",
    ".webp": "image/webp",
    ".binarypb": "application/x-protobuf",
    ".db": "application/vnd.sqlite3",
}


@dataclass(frozen=True)
class ResultadoPublicacaoPR:
    """Resultado consolidado da sincronização da pasta da PR no bucket R2."""

    prefixo: str
    arquivos_enviados: list[str] = field(default_factory=list)
    arquivos_orfaos_removidos: list[str] = field(default_factory=list)


def obter_tipo_mime_arquivo(caminho: Path) -> str:
    """Retorna o Content-Type apropriado para um artefato publicado no R2."""
    return _TIPOS_MIME_POR_EXTENSAO.get(
        caminho.suffix.lower(),
        "application/octet-stream",
    )


def criar_cliente_r2_do_ambiente(
    ambiente: Mapping[str, str] | None = None,
) -> tuple[Any, str] | None:
    """
    Cria o cliente S3 (boto3) apontando para o Cloudflare R2 a partir das variáveis de ambiente.
    Retorna `None` caso as credenciais não estejam presentes (ex: PR vinda de fork externo).
    """
    env = os.environ if ambiente is None else ambiente
    access_key = env.get("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = env.get("AWS_SECRET_ACCESS_KEY", "").strip()
    endpoint_url = env.get("R2_ENDPOINT_URL", "").strip()
    bucket = env.get("R2_BUCKET", "aresta-serving").strip() or "aresta-serving"

    if not access_key or not secret_key or not endpoint_url:
        return None

    cliente = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=env.get("AWS_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )
    return (cliente, bucket)


def _listar_chaves_prefixo(cliente_r2: Any, bucket: str, prefixo: str) -> list[str]:
    resposta = cliente_r2.list_objects_v2(Bucket=bucket, Prefix=prefixo)
    conteudos = resposta.get("Contents", [])
    return sorted(str(item["Key"]) for item in conteudos)


def publicar_diretorio_pr_no_r2(
    diretorio_compilado: Path,
    numero_pr: int,
    cliente_r2: Any,
    bucket: str = "aresta-serving",
) -> ResultadoPublicacaoPR:
    """
    Publica todos os arquivos contidos em `diretorio_compilado` sob o prefixo `pr/<numero_pr>/`
    no bucket R2 e remove quaisquer objetos órfãos de commits anteriores da mesma PR.
    """
    prefixo = f"pr/{numero_pr}/"
    chaves_anteriores = set(_listar_chaves_prefixo(cliente_r2, bucket, prefixo))

    arquivos_locais = sorted(
        p for p in diretorio_compilado.rglob("*") if p.is_file()
    )
    chaves_atuais: list[str] = []

    for caminho_arquivo in arquivos_locais:
        rel_posix = caminho_arquivo.relative_to(diretorio_compilado).as_posix()
        chave_r2 = f"{prefixo}{rel_posix}"
        cliente_r2.put_object(
            Bucket=bucket,
            Key=chave_r2,
            Body=caminho_arquivo.read_bytes(),
            ContentType=obter_tipo_mime_arquivo(caminho_arquivo),
        )
        chaves_atuais.append(chave_r2)

    orfaos = sorted(chaves_anteriores - set(chaves_atuais))
    if orfaos:
        cliente_r2.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in orfaos]},
        )

    return ResultadoPublicacaoPR(
        prefixo=prefixo,
        arquivos_enviados=chaves_atuais,
        arquivos_orfaos_removidos=orfaos,
    )


def limpar_pasta_pr_no_r2(
    numero_pr: int,
    cliente_r2: Any,
    bucket: str = "aresta-serving",
) -> list[str]:
    """
    Remove integralmente todos os objetos armazenados sob `pr/<numero_pr>/` no bucket R2.
    """
    prefixo = f"pr/{numero_pr}/"
    chaves = _listar_chaves_prefixo(cliente_r2, bucket, prefixo)
    if not chaves:
        return []

    cliente_r2.delete_objects(
        Bucket=bucket,
        Delete={"Objects": [{"Key": k} for k in chaves]},
    )
    return chaves
