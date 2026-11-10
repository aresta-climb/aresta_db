# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpFake
from coleta_de_betas.extratores.youtube import ExtratorYouTube


def test_extrator_youtube_monta_query_correta() -> None:
    extrator = ExtratorYouTube(chave_api="TEST_KEY")
    query = extrator.montar_query("Fusca Azul", "Geriatria", "Ouro Preto")
    assert "Fusca Azul" in query
    assert "Geriatria" in query
    assert "Ouro Preto" in query
    assert "escalada" in query.lower() or "boulder" in query.lower()


def test_extrator_youtube_busca_com_sucesso() -> None:
    http = ClienteHttpFake()
    http.registrar_json(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "items": [
                {"id": {}},
                {
                    "id": {"videoId": "vid123"},
                    "snippet": {
                        "title": "Mandando o crux da Fusca Azul V4",
                        "description": "Vídeo mostrando a beta da via Fusca Azul no setor Geriatria.",
                    },
                },
                {
                    "id": {"videoId": "vid456"},
                    "snippet": {
                        "title": "Outra escalada qualquer",
                        "description": "",
                    },
                },
            ]
        },
        status_code=200,
    )

    extrator = ExtratorYouTube(chave_api="TEST_KEY", cliente_http=http)
    resultados = extrator.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    assert len(resultados) == 2

    item1 = resultados[0]
    assert isinstance(item1, beta_pb2.CandidatoMidiaBeta)
    assert item1.midia.url == "https://www.youtube.com/watch?v=vid123"
    assert item1.midia.titulo == "Mandando o crux da Fusca Azul V4"
    assert item1.midia.fonte == beta_pb2.FonteMidia.YOUTUBE
    assert item1.match_nome_no_snippet is True
    assert list(item1.snippets) == ["Vídeo mostrando a beta da via Fusca Azul no setor Geriatria."]

    item2 = resultados[1]
    assert item2.midia.url == "https://www.youtube.com/watch?v=vid456"
    assert item2.match_nome_no_snippet is False
    assert list(item2.snippets) == []


def test_extrator_youtube_trata_erro_api_e_conexao() -> None:
    http_403 = ClienteHttpFake()
    http_403.registrar_texto(
        "https://www.googleapis.com/youtube/v3/search",
        "Quota exceeded",
        status_code=403,
    )
    extrator_403 = ExtratorYouTube(chave_api="TEST_KEY", cliente_http=http_403)
    with pytest.raises(RuntimeError, match="Erro na API do YouTube"):
        extrator_403.buscar("Fusca Azul", "Geriatria", "Ouro Preto")

    http_rede = ClienteHttpFake()
    http_rede.registrar_erro("https://www.googleapis.com/youtube/v3/search", "Sem internet")
    extrator_rede = ExtratorYouTube(chave_api="TEST_KEY", cliente_http=http_rede)
    with pytest.raises(RuntimeError, match="Erro na conexão com a API do YouTube"):
        extrator_rede.buscar("Fusca Azul", "Geriatria", "Ouro Preto")
