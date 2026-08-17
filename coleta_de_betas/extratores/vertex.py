# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import os
import requests
from typing import List, Optional
from aresta_api.proto.generated import beta_pb2

class ExtratorVertexSearch:
    """
    Extrator de postagens e vídeos de escalada no Instagram usando Vertex AI Search (Agent Search).
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        data_store_id: Optional[str] = None,
        location: str = "global",
        api_key: Optional[str] = None
    ):
        self.project_id = project_id or os.environ.get("VERTEX_PROJECT_ID", "")
        self.data_store_id = data_store_id or os.environ.get("VERTEX_DATA_STORE_ID", "")
        self.location = location or os.environ.get("VERTEX_LOCATION", "global")
        self.api_key = api_key or os.environ.get("VERTEX_API_KEY", "")

    def montar_query(self, nome_escalada: str, nome_setor: str = "", nome_pico: str = "") -> str:
        """
        Monta a string de busca para o Vertex AI Search.
        """
        partes = [nome_escalada]
        if nome_setor:
            partes.append(nome_setor)
        if nome_pico:
            partes.append(nome_pico)
        return " ".join(partes)

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10
    ) -> List[beta_pb2.MidiaBeta]:
        """
        Executa a busca no Vertex AI Search e retorna objetos MidiaBeta.
        """
        query = self.montar_query(nome_escalada, nome_setor, nome_pico)
        url_endpoint = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{self.project_id}/"
            f"locations/{self.location}/collections/default_collection/dataStores/{self.data_store_id}/"
            f"servingConfigs/default_search:search"
        )
        params = {}
        if self.api_key:
            params["key"] = self.api_key

        payload = {
            "query": query,
            "pageSize": max_resultados
        }

        try:
            resposta = requests.post(url_endpoint, json=payload, params=params, timeout=10)
        except Exception as e:
            raise RuntimeError(f"Erro na conexão com a API do Vertex AI Search: {e}")

        if resposta.status_code != 200:
            raise RuntimeError(f"Erro na API do Vertex AI Search ({resposta.status_code}): {resposta.text}")

        dados = resposta.json()
        resultados: List[beta_pb2.MidiaBeta] = []
        termo_lower = nome_escalada.lower().strip()

        for item in dados.get("results", []):
            doc = item.get("document", {})
            struct_data = doc.get("derivedStructData", {})
            link = struct_data.get("link", "")
            if not link:
                continue

            titulo = struct_data.get("title", "")
            snippets = struct_data.get("snippets", [])
            snippet_text = " ".join([s.get("snippet", "") for s in snippets])

            # Extração de thumbnail se presente
            thumb_url = ""
            pagemap = struct_data.get("pagemap", {})
            if "cse_image" in pagemap and pagemap["cse_image"]:
                thumb_url = pagemap["cse_image"][0].get("src", "")

            midia = beta_pb2.MidiaBeta()
            midia.url = link
            midia.titulo = titulo
            midia.thumbnail_url = thumb_url
            midia.fonte = beta_pb2.FonteMidia.INSTAGRAM

            texto_completo = f"{titulo} {snippet_text}".lower()
            midia.match_nome_no_snippet = termo_lower in texto_completo

            if snippet_text:
                midia.snippets.append(snippet_text)

            resultados.append(midia)

        return resultados
