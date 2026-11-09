# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Fakes determinísticos em memória para fronteiras externas HTTP e de busca web.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


class RespostaHttpProtocolo(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    @property
    def content(self) -> bytes: ...

    def json(self) -> Any: ...


class ClienteHttpProtocolo(Protocol):
    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10,
    ) -> RespostaHttpProtocolo: ...

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float = 10,
    ) -> RespostaHttpProtocolo: ...


class BuscadorWebProtocolo(Protocol):
    def buscar_texto(self, query: str, max_resultados: int = 10) -> list[dict[str, str]]: ...


@dataclass
class RespostaHttpFake:
    status_code: int = 200
    texto: str = ""
    conteudo_bytes: bytes = b""
    dados_json: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        return self.texto

    @property
    def content(self) -> bytes:
        return self.conteudo_bytes

    def json(self) -> dict[str, Any]:
        if self.dados_json is not None:
            return self.dados_json
        return {}


@dataclass
class ClienteHttpFake:
    """Cliente HTTP determinístico em memória para testes de integração sem rede."""

    respostas: dict[str, RespostaHttpFake] = field(default_factory=dict)
    erros: dict[str, str] = field(default_factory=dict)
    chamadas_get: list[tuple[str, dict[str, Any] | None]] = field(default_factory=list)
    chamadas_post: list[tuple[str, dict[str, Any] | None, dict[str, Any] | None]] = field(
        default_factory=list
    )

    def registrar_json(
        self,
        url: str,
        dados: dict[str, Any],
        status_code: int = 200,
    ) -> None:
        texto = json.dumps(dados, ensure_ascii=False)
        self.respostas[url] = RespostaHttpFake(
            status_code=status_code,
            texto=texto,
            conteudo_bytes=texto.encode("utf-8"),
            dados_json=dados,
        )

    def registrar_texto(self, url: str, texto: str, status_code: int = 200) -> None:
        self.respostas[url] = RespostaHttpFake(
            status_code=status_code,
            texto=texto,
            conteudo_bytes=texto.encode("utf-8"),
        )

    def registrar_bytes(self, url: str, dados: bytes, status_code: int = 200) -> None:
        self.respostas[url] = RespostaHttpFake(
            status_code=status_code,
            texto="",
            conteudo_bytes=dados,
        )

    def registrar_erro(self, url: str, mensagem_erro: str) -> None:
        self.erros[url] = mensagem_erro

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10,
    ) -> RespostaHttpFake:
        _ = (headers, timeout)
        self.chamadas_get.append((url, params))
        if url in self.erros:
            raise ConnectionError(self.erros[url])
        if url in self.respostas:
            return self.respostas[url]
        return RespostaHttpFake(status_code=404, texto="Not Found", conteudo_bytes=b"Not Found")

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float = 10,
    ) -> RespostaHttpFake:
        _ = timeout
        self.chamadas_post.append((url, json, params))
        if url in self.erros:
            raise ConnectionError(self.erros[url])
        if url in self.respostas:
            return self.respostas[url]
        return RespostaHttpFake(status_code=404, texto="Not Found", conteudo_bytes=b"Not Found")


@dataclass
class BuscadorWebFake:
    """Buscador web determinístico em memória para testes de scraping."""

    resultados_por_termo: list[tuple[str, list[dict[str, str]]]] = field(default_factory=list)
    erro_configurado: str | None = None
    queries_executadas: list[tuple[str, int]] = field(default_factory=list)

    def registrar_resultados(
        self,
        termo_query: str,
        resultados: list[dict[str, str]],
    ) -> None:
        self.resultados_por_termo.append((termo_query.lower(), resultados))

    def registrar_erro(self, mensagem_erro: str) -> None:
        self.erro_configurado = mensagem_erro

    def buscar_texto(self, query: str, max_resultados: int = 10) -> list[dict[str, str]]:
        self.queries_executadas.append((query, max_resultados))
        if self.erro_configurado is not None:
            raise RuntimeError(self.erro_configurado)
        q_lower = query.lower()
        for termo, res in self.resultados_por_termo:
            if termo in q_lower:
                return res[:max_resultados]
        return []
