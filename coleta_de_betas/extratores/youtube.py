# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import requests
from typing import List, Optional, Union, Dict
from aresta_api.proto.generated import beta_pb2


class ExtratorYouTube:
    """
    Extrator de mídias e vídeos de betas de escalada via YouTube Data API v3.
    """

    def __init__(self, chave_api: Optional[str] = None) -> None:
        self.chave_api = chave_api or os.environ.get("YOUTUBE_API_KEY", "")

    def montar_query(self, nome_escalada: str, nome_setor: str = "", nome_pico: str = "") -> str:
        """
        Monta a string de busca combinando o nome da via, setor, pico e palavras-chave.
        """
        partes = [nome_escalada]
        if nome_setor:
            partes.append(nome_setor)
        if nome_pico:
            partes.append(nome_pico)
        partes.append("escalada boulder")
        return " ".join(partes)

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10
    ) -> List[beta_pb2.MidiaBeta]:
        """
        Executa a pesquisa na API do YouTube e retorna uma lista de objetos MidiaBeta.
        """
        query = self.montar_query(nome_escalada, nome_setor, nome_pico)
        url_api = "https://www.googleapis.com/youtube/v3/search"
        parametros: Dict[str, Union[str, int]] = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "maxResults": max_resultados,
            "key": self.chave_api
        }


        try:
            resposta = requests.get(url_api, params=parametros, timeout=10)
        except Exception as e:
            raise RuntimeError(f"Erro na conexão com a API do YouTube: {e}")

        if resposta.status_code != 200:
            raise RuntimeError(f"Erro na API do YouTube ({resposta.status_code}): {resposta.text}")

        dados = resposta.json()
        itens = dados.get("items", [])
        resultados: List[beta_pb2.MidiaBeta] = []

        termo_lower = nome_escalada.lower().strip()

        for item in itens:
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            titulo = snippet.get("title", "")
            descricao = snippet.get("description", "")
            thumbnails = snippet.get("thumbnails", {})
            
            # Prioriza resolução maior
            thumb_url = ""
            for qualidade in ["high", "medium", "default"]:
                if qualidade in thumbnails and "url" in thumbnails[qualidade]:
                    thumb_url = thumbnails[qualidade]["url"]
                    break

            midia = beta_pb2.MidiaBeta()
            midia.url = f"https://www.youtube.com/watch?v={video_id}"
            midia.titulo = titulo
            midia.thumbnail_url = thumb_url
            midia.fonte = beta_pb2.FonteMidia.YOUTUBE
            # Checa se o nome da escalada aparece no título ou na descrição
            texto_completo = f"{titulo} {descricao}".lower()
            midia.match_nome_no_snippet = termo_lower in texto_completo

            if descricao:
                midia.snippets.append(descricao)

            resultados.append(midia)

        return resultados
