# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpFake
from coleta_de_betas.extratores.youtube import URL_INNERTUBE_SEARCH, ExtratorYouTube


def test_extrator_youtube_monta_query_sem_escalada_e_limpa_complexo() -> None:
    extrator = ExtratorYouTube(intervalo_minimo_s=0.0)
    query = extrator.montar_query(
        nome_escalada="Inanição (Setor Principal - Mapa 1)",
        nome_setor="Setor Principal",
        nome_pico="Complexo Pedra Grande",
        cidade="Igarapé",
    )
    assert query == "Inanição Pedra Grande Igarapé"
    assert "escalada" not in query.lower()
    assert "Setor Principal" not in query

    # Evita duplicar cidade se o nome do pico já a contiver
    query_dup = extrator.montar_query(
        nome_escalada="Via Teste",
        nome_pico="Pedra Grande de Igarapé",
        cidade="Igarapé",
    )
    assert query_dup == "Via Teste Pedra Grande de Igarapé"


def test_extrator_youtube_innertube_extrai_videos_shorts_pacing_e_rejeitados() -> None:
    http = ClienteHttpFake()
    tempos_dormidos: list[float] = []
    relogio = [100.0]

    def _relogio() -> float:
        return relogio[0]

    def _dormir(s: float) -> None:
        tempos_dormidos.append(round(s, 3))
        relogio[0] += s

    http.registrar_json(
        URL_INNERTUBE_SEARCH,
        {
            "contents": {
                "twoColumnSearchResultsRenderer": {
                    "primaryContents": {
                        "sectionListRenderer": {
                            "contents": [
                                {
                                    "itemSectionRenderer": {
                                        "contents": [
                                            {
                                                "videoRenderer": {
                                                    "videoId": "JZsMiVEl8YA",
                                                    "title": {
                                                        "runs": [
                                                            {
                                                                "text": "Inanição (5º VI D2 E3) Pedra Grande de Igarapé, MG"
                                                            }
                                                        ]
                                                    },
                                                    "ownerText": {
                                                        "runs": [{"text": "Serra da Liberdade"}]
                                                    },
                                                    "descriptionSnippet": {
                                                        "runs": [
                                                            {"text": "Escalando em Pedra Grande."}
                                                        ]
                                                    },
                                                    "detailedMetadataSnippets": [
                                                        {
                                                            "snippetText": {
                                                                "runs": [
                                                                    {
                                                                        "text": "Via Inanição em Igarapé MG"
                                                                    }
                                                                ]
                                                            }
                                                        },
                                                        {
                                                            "snippetText": {
                                                                "runs": [
                                                                    {
                                                                        "text": "Via Inanição em Igarapé MG"
                                                                    }
                                                                ]
                                                            }
                                                        },
                                                    ],
                                                }
                                            },
                                            {
                                                "shortsLockupViewModel": {
                                                    "onTap": {
                                                        "innertubeCommand": {
                                                            "reelWatchEndpoint": {
                                                                "videoId": "Sh0rtIgarape"
                                                            }
                                                        }
                                                    },
                                                    "overlayMetadata": {
                                                        "primaryText": {
                                                            "content": "Inanição Igarameca"
                                                        }
                                                    },
                                                }
                                            },
                                            {
                                                "reelItemRenderer": {
                                                    "videoId": "Outr0P1co",
                                                    "headline": {
                                                        "simpleText": "Inanição em Itatiaia"
                                                    },
                                                }
                                            },
                                            {
                                                "videoRenderer": {
                                                    "videoId": "Outr4V1a",
                                                    "title": {
                                                        "simpleText": "Pedra Grande Igarapé trilha"
                                                    },
                                                }
                                            },
                                            {
                                                "videoRenderer": {
                                                    "videoId": "JZsMiVEl8YA",
                                                    "title": {"simpleText": "Duplicado ignorado"},
                                                }
                                            },
                                            {
                                                "videoRenderer": {
                                                    "videoId": "Lim1t3Excedido",
                                                    "title": {
                                                        "simpleText": "Inanição Igarapé Extra"
                                                    },
                                                }
                                            },
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        status_code=200,
    )

    extrator = ExtratorYouTube(
        cliente_http=http,
        intervalo_minimo_s=0.4,
        relogio=_relogio,
        dormir=_dormir,
    )

    # Placeholder retorna vazio com zero requisições HTTP
    assert extrator.buscar_com_rejeitados("Projeto 2", nome_pico="Pedra Grande") == ([], [])
    assert len(http.chamadas_post) == 0

    cands, rejs = extrator.buscar_com_rejeitados(
        nome_escalada="Inanição",
        nome_setor="Setor Norte",
        nome_pico="Complexo Pedra Grande",
        cidade="Igarapé",
        nome_croqui="Pedra Grande (Igarameca)",
        max_resultados=4,
    )

    assert len(http.chamadas_post) == 1
    assert len(cands) == 2
    assert cands[0].midia.url == "https://youtube.com/watch?v=JZsMiVEl8YA"
    assert cands[0].midia.fonte == beta_pb2.FonteMidia.YOUTUBE
    assert cands[0].match_nome_no_snippet is True
    assert "Serra da Liberdade" in cands[0].snippets[0]

    assert cands[1].midia.url == "https://youtube.com/shorts/Sh0rtIgarape"
    assert cands[1].midia.fonte == beta_pb2.FonteMidia.YOUTUBE

    urls_rej = {r.url: r.titulo for r in rejs}
    assert "https://youtube.com/shorts/Outr0P1co" in urls_rej
    assert urls_rej["https://youtube.com/shorts/Outr0P1co"].startswith(
        "[Query: youtube | Auto-filtrado: sem menção ao pico]"
    )
    assert "https://youtube.com/watch?v=Outr4V1a" in urls_rej
    assert urls_rej["https://youtube.com/watch?v=Outr4V1a"].startswith(
        "[Query: youtube | Auto-filtrado: sem menção à via]"
    )

    # 2ª busca em sequência com intervalo decorrido menor que 0.4s ativa o pacing
    relogio[0] += 0.1
    extrator.buscar("Inanição", nome_pico="Pedra Grande", cidade="Igarapé")
    assert tempos_dormidos == [0.3]


def test_extrator_youtube_trata_erro_api_e_conexao() -> None:
    http_500 = ClienteHttpFake()
    http_500.registrar_texto(URL_INNERTUBE_SEARCH, "Erro interno", status_code=500)
    extrator_500 = ExtratorYouTube(cliente_http=http_500, intervalo_minimo_s=0.0)
    with pytest.raises(RuntimeError, match="Erro no YouTube InnerTube"):
        extrator_500.buscar("Inanição", nome_pico="Pedra Grande")

    http_rede = ClienteHttpFake()
    http_rede.registrar_erro(URL_INNERTUBE_SEARCH, "Sem internet")
    extrator_rede = ExtratorYouTube(cliente_http=http_rede, intervalo_minimo_s=0.0)
    with pytest.raises(RuntimeError, match="Erro na conexão com o YouTube InnerTube"):
        extrator_rede.buscar("Inanição", nome_pico="Pedra Grande")
