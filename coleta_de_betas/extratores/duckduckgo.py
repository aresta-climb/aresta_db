# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.blog import _BuscadorDuckDuckGoPadrao
from coleta_de_betas.extratores.cliente_http_fake import BuscadorWebProtocolo


class ExtratorDuckDuckGo:
    """
    Extrator de postagens e vídeos do Instagram via scraping da busca do DuckDuckGo.
    """

    def __init__(self, buscador: BuscadorWebProtocolo | None = None) -> None:
        self._buscador: BuscadorWebProtocolo = buscador or _BuscadorDuckDuckGoPadrao()

    def montar_query(self, nome_escalada: str, nome_setor: str = "", nome_pico: str = "") -> str:
        """
        Monta a query restrita ao domínio do Instagram.
        """
        partes = [nome_escalada]
        if nome_setor:
            partes.append(nome_setor)
        if nome_pico:
            partes.append(nome_pico)
        partes.append("site:instagram.com")
        return " ".join(partes)

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
    ) -> list[beta_pb2.CandidatoMidiaBeta]:
        """
        Executa a busca no DuckDuckGo e formata em objetos CandidatoMidiaBeta.
        """
        query = self.montar_query(nome_escalada, nome_setor, nome_pico)
        resultados: list[beta_pb2.CandidatoMidiaBeta] = []
        termo_lower = nome_escalada.lower().strip()

        try:
            res_ddg = self._buscador.buscar_texto(query, max_resultados=max_resultados)
        except Exception as e:
            raise RuntimeError(f"Erro na busca via DuckDuckGo: {e}")

        for item in res_ddg:
            link = item.get("href", "")
            if not link:
                continue

            titulo = item.get("title", "")
            body = item.get("body", "")

            candidato = beta_pb2.CandidatoMidiaBeta()
            candidato.midia.url = link
            candidato.midia.titulo = titulo
            candidato.midia.fonte = beta_pb2.FonteMidia.INSTAGRAM

            texto_completo = f"{titulo} {body}".lower()
            candidato.match_nome_no_snippet = termo_lower in texto_completo

            if body:
                candidato.snippets.append(body)

            resultados.append(candidato)

        return resultados
