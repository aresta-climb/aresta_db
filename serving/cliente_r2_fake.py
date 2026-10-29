# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca test-only de Fake determinístico em memória para o cliente S3/R2.
Segue o Princípio V do AGENTS.md (Fidelidade de Produção e Fakes Determinísticos).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any


class ErroOperacaoR2Fake(RuntimeError):
    """Exceção determinística lançada pelo ClienteR2Fake quando configurado para simular falha de I/O."""


@dataclass(frozen=True)
class ObjetoR2EmMemoria:
    """Representa um objeto armazenado no bucket falso em memória."""

    conteudo: bytes
    tipo_conteudo: str


class ClienteR2Fake:
    """
    Fake determinístico em memória compatível com a interface S3 do boto3 utilizada
    pelas rotinas de publicação e limpeza do serving.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, dict[str, ObjetoR2EmMemoria]] = {}
        self._falhas_configuradas: dict[str, str] = {}

    def configurar_falha(self, nome_operacao: str, mensagem: str) -> None:
        """Configura uma operação (ex: 'put_object', 'list_objects_v2', 'delete_objects') para lançar erro."""
        self._falhas_configuradas[nome_operacao] = mensagem

    def limpar_falhas(self) -> None:
        """Remove todas as falhas simuladas configuradas."""
        self._falhas_configuradas.clear()

    def _verificar_falha(self, nome_operacao: str) -> None:
        if nome_operacao in self._falhas_configuradas:
            raise ErroOperacaoR2Fake(self._falhas_configuradas[nome_operacao])

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes | str,
        ContentType: str = "application/octet-stream",
        **_: Any,
    ) -> dict[str, Any]:
        """Armazena um objeto em memória sob o bucket e chave informados."""
        self._verificar_falha("put_object")
        dados = Body.encode("utf-8") if isinstance(Body, str) else bytes(Body)
        objetos = self._buckets.setdefault(Bucket, {})
        objetos[Key] = ObjetoR2EmMemoria(conteudo=dados, tipo_conteudo=ContentType)
        return {"ETag": f'"{len(dados)}"'}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        """Recupera um objeto armazenado em memória."""
        self._verificar_falha("get_object")
        objetos = self._buckets.get(Bucket, {})
        if Key not in objetos:
            raise ErroOperacaoR2Fake(f"Objeto não encontrado: {Bucket}/{Key}")
        obj = objetos[Key]
        return {
            "Body": io.BytesIO(obj.conteudo),
            "ContentType": obj.tipo_conteudo,
            "ContentLength": len(obj.conteudo),
        }

    def list_objects_v2(
        self,
        *,
        Bucket: str,
        Prefix: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        """Lista objetos armazenados em memória filtrados por prefixo."""
        self._verificar_falha("list_objects_v2")
        objetos = self._buckets.get(Bucket, {})
        chaves_filtradas = sorted(k for k in objetos if k.startswith(Prefix))
        if not chaves_filtradas:
            return {"KeyCount": 0}
        return {
            "KeyCount": len(chaves_filtradas),
            "Contents": [
                {"Key": k, "Size": len(objetos[k].conteudo)} for k in chaves_filtradas
            ],
        }

    def delete_objects(
        self,
        *,
        Bucket: str,
        Delete: dict[str, list[dict[str, str]]],
        **_: Any,
    ) -> dict[str, Any]:
        """Remove um lote de objetos do bucket em memória."""
        self._verificar_falha("delete_objects")
        objetos = self._buckets.setdefault(Bucket, {})
        removidos: list[dict[str, str]] = []
        for item in Delete.get("Objects", []):
            chave = item["Key"]
            objetos.pop(chave, None)
            removidos.append({"Key": chave})
        return {"Deleted": removidos}

    def obter_conteudo(self, bucket: str, chave: str) -> bytes | None:
        """Método auxiliar de inspeção para testes retornando os bytes brutos ou None."""
        obj = self._buckets.get(bucket, {}).get(chave)
        return obj.conteudo if obj is not None else None

    def obter_tipo_conteudo(self, bucket: str, chave: str) -> str | None:
        """Método auxiliar de inspeção para testes retornando o Content-Type ou None."""
        obj = self._buckets.get(bucket, {}).get(chave)
        return obj.tipo_conteudo if obj is not None else None

    def listar_chaves(self, bucket: str, prefixo: str = "") -> list[str]:
        """Retorna todas as chaves armazenadas no bucket iniciadas pelo prefixo."""
        objetos = self._buckets.get(bucket, {})
        return sorted(k for k in objetos if k.startswith(prefixo))
