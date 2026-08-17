# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import duckduckgo_search
from typing import List
from aresta_api.proto.generated import beta_pb2

class ExtratorDuckDuckGo:
    """
    Extrator de postagens e vídeos do Instagram via scraping da busca do DuckDuckGo.
    """

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
        max_resultados: int = 10
    ) -> List[beta_pb2.MidiaBeta]:
        """
        Executa a busca no DuckDuckGo e formata em objetos MidiaBeta.
        """
        query = self.montar_query(nome_escalada, nome_setor, nome_pico)
        resultados: List[beta_pb2.MidiaBeta] = []
        termo_lower = nome_escalada.lower().strip()

        try:
            with duckduckgo_search.DDGS() as ddgs:
                res_ddg = list(ddgs.text(query, max_results=max_resultados))
        except Exception as e:
            raise RuntimeError(f"Erro na busca via DuckDuckGo: {e}")

        for item in res_ddg:
            link = item.get("href", "")
            if not link:
                continue

            titulo = item.get("title", "")
            body = item.get("body", "")

            midia = beta_pb2.MidiaBeta()
            midia.url = link
            midia.titulo = titulo
            midia.thumbnail_url = "" # DuckDuckGo text search não garante thumbnail estável
            midia.fonte = beta_pb2.FonteMidia.INSTAGRAM

            texto_completo = f"{titulo} {body}".lower()
            midia.match_nome_no_snippet = termo_lower in texto_completo

            if body:
                midia.snippets.append(body)

            resultados.append(midia)

        return resultados
