# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import threading
import time
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from coleta_de_betas.extratores.blog import ExtratorBlog
from coleta_de_betas.extratores.cliente_http_fake import BuscadorWebFake, ClienteHttpFake
from coleta_de_betas.extratores.youtube import URL_INNERTUBE_SEARCH, ExtratorYouTube
from editor.controllers.croqui_controller import CroquiController
from editor.mcp.despachante import DespachanteQt
from editor.mcp.ferramentas_betas import registrar_ferramentas_betas
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def _montar_croqui_betas(
    tmp_path: Path,
    extratores: list[Any] | None = None,
) -> tuple[CroquiModel, QUndoStack, CroquiController, ServidorMCP, BuscadorWebFake]:
    croqui = croqui_pb2.Croqui(uid="uid_croqui_lapinha", id="lapinha", nome="Gruta da Lapinha")
    pico = croqui.picos.add(nome="Gruta da Lapinha")

    # Setor direto no pico
    sg1 = pico.setores_ou_grupos.add()
    setor1 = sg1.setor.conteudo
    setor1.uid = "uid_setor_savassinha"
    setor1.nome = "Setor Savassinha"

    esc1 = setor1.escaladas.add(uid="uid_via_cova01")
    esc1.via_esportiva.nome = "Cova dos Leões"
    esc1.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7B
    esc1.via_esportiva.conquistadores.extend(["Emerson", "Gilberto"])

    esc2 = setor1.escaladas.add(uid="uid_via_rato02")
    esc2.via_esportiva.nome = "Rato Assassino"
    esc2.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_8A

    # Setor dentro de um grupo (com diversas modalidades para cobrir extração de metadados)
    sg2 = pico.setores_ou_grupos.add()
    grupo = sg2.grupo.conteudo
    grupo.uid = "uid_grupo_gruta"
    grupo.nome = "Grupo Gruta"
    arq_setor2 = grupo.setores.add()
    setor2 = arq_setor2.conteudo
    setor2.uid = "uid_setor_tunel"
    setor2.nome = "Setor Túnel"

    esc3 = setor2.escaladas.add(uid="uid_via_gota03")
    esc3.via_movel.nome = "Gota D'água"
    esc3.via_movel.dificuldade = croqui_pb2.GrauVia.BR_6

    esc4 = setor2.escaladas.add(uid="uid_boulder_04")
    esc4.boulder.nome = "Bloco do Cristal"
    esc4.boulder.dificuldade = croqui_pb2.GrauBoulder.V5

    buscador = BuscadorWebFake()
    buscador.registrar_resultados(
        "cova dos leões",
        [
            {
                "href": "https://pt.scribd.com/document/123/Guia-Lapinha",
                "title": "Guia Gruta da Lapinha PDF",
                "body": "Cova dos Leões 7b na Gruta da Lapinha.",
            },
            {
                "href": "https://pt.scribd.com/document/123/Guia-Lapinha",
                "title": "Guia Gruta da Lapinha PDF Duplicado",
                "body": "Cova dos Leões 7b na Gruta da Lapinha.",
            },
        ],
    )
    buscador.registrar_resultados(
        "rato assassino",
        [
            {
                "href": "https://instagram.com/reel/C7e8V1mulrh",
                "title": "Via Rato Assassino - 8a - Gruta da Lapinha",
                "body": "Cadena na Gruta da Lapinha setor Savassinha.",
            }
        ],
    )

    http_yt = ClienteHttpFake()
    http_yt.registrar_json(
        URL_INNERTUBE_SEARCH,
        {
            "contents": {
                "videoRenderer": {
                    "videoId": "EQYAydeVEsY",
                    "title": {"simpleText": "Cova dos Leões - Gruta da Lapinha"},
                }
            }
        },
    )

    lista_extratores = (
        extratores
        if extratores is not None
        else [
            ExtratorYouTube(cliente_http=http_yt, intervalo_minimo_s=0.0),
            ExtratorBlog(buscador=buscador, cliente_http=ClienteHttpFake()),
        ]
    )
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    registrar_ferramentas_betas(
        servidor=servidor,
        model=model,
        controller=controller,
        extratores=lista_extratores,
    )
    return model, undo_stack, controller, servidor, buscador


def _chamar(servidor: ServidorMCP, nome: str, argumentos: dict[str, Any]) -> dict[str, Any]:
    resp = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": nome, "arguments": argumentos},
        }
    )
    assert resp is not None
    res = resp["result"]
    if res.get("isError"):
        raise ValueError(res["content"][0]["text"])
    return res["structuredContent"]


def test_coletar_betas_conclui_no_long_polling_e_filtra_ja_coletadas(qapp, tmp_path: Path):
    """
    Valida que aresta_coletar_betas(acao='iniciar') executa a coleta multi-fonte,
    grava candidatos em betas_nao_scorados e descartes em betas_rejeitados no CroquiController,
    e ignora vias já coletadas quando apenas_sem_coleta=True.
    """
    model, undo_stack, _, servidor, _ = _montar_croqui_betas(tmp_path)

    # 1. Antes de iniciar, status é 'ocioso'
    status_inicial = _chamar(servidor, "aresta_coletar_betas", {"acao": "status"})
    assert status_inicial["status"] == "ocioso"
    assert status_inicial["total_escaladas_com_nao_scorados"] == 0

    # 2. Inicia coleta apenas para o Setor Savassinha (2 vias: Cova dos Leões e Rato Assassino)
    res = _chamar(
        servidor,
        "aresta_coletar_betas",
        {
            "acao": "iniciar",
            "alvo_setor": "uid_setor_savassinha",
            "aguardar_segundos": 5.0,
            "tamanho_lote_flush": 1,
        },
    )
    assert res["status"] == "concluido"
    assert res["total_escaladas"] == 2
    assert res["escaladas_processadas"] == 2
    assert res["escaladas_restantes"] == 0
    assert res["novos_candidatos_adicionados"] == 2
    assert res["novos_rejeitados_adicionados"] >= 1
    assert res["total_escaladas_com_nao_scorados"] == 2
    assert res["total_candidatos_nao_scorados"] == 2
    assert undo_stack.count() >= 1

    # 3. Chamar novamente para o mesmo setor com apenas_sem_coleta=True deve filtrar as 2 vias já coletadas
    res_repetido = _chamar(
        servidor,
        "aresta_coletar_betas",
        {
            "acao": "iniciar",
            "alvo_setor": "Setor Savassinha",
            "apenas_sem_coleta": True,
            "aguardar_segundos": 5.0,
        },
    )
    assert res_repetido["status"] == "concluido"
    assert res_repetido["total_escaladas"] == 0
    assert res_repetido["escaladas_processadas"] == 0

    # 4. Filtrar por escaladas_uids específicas com apenas_sem_coleta=False permite re-executar
    res_forcado = _chamar(
        servidor,
        "aresta_coletar_betas",
        {
            "acao": "iniciar",
            "escaladas_uids": ["uid_via_cova01"],
            "apenas_sem_coleta": False,
            "aguardar_segundos": 5.0,
        },
    )
    assert res_forcado["status"] == "concluido"
    assert res_forcado["total_escaladas"] == 1
    # Como a URL já existe em betas_nao_scorados, o controller deduplica e adiciona 0 duplicatas
    assert res_forcado["novos_candidatos_adicionados"] == 0


def test_listar_betas_nao_scorados_paginacao_enriquecimento_e_omissao_rejeitados(
    qapp, tmp_path: Path
):
    """
    Valida que aresta_listar_betas_nao_scorados retorna apenas escaladas com betas_nao_scorados > 0,
    enriquecidas com metadados (indice_curadoria, nome, dificuldade, modalidade, setor, pico),
    suportando paginação (offset, limite) e omitindo betas_rejeitados.
    """
    _, _, controller, servidor, _ = _montar_croqui_betas(tmp_path)

    # Coleta as vias do Setor Savassinha (Cova dos Leões e Rato Assassino)
    _chamar(
        servidor,
        "aresta_coletar_betas",
        {"acao": "iniciar", "alvo_setor": "uid_setor_savassinha", "aguardar_segundos": 5.0},
    )
    # Adiciona também um candidato não scorado manualmente para a via móvel do grupo (Gota D'água)
    cand_gota = beta_pb2.CandidatoMidiaBeta()
    cand_gota.midia.url = "https://youtube.com/watch?v=gota123"
    cand_gota.midia.titulo = "Via Gota D'água - Gruta da Lapinha"
    cand_gota.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
    controller.adicionar_candidatos_nao_scorados("uid_via_gota03", [cand_gota])

    # E adiciona uma escalada com apenas beta rejeitado (0 não scorados) para garantir que é filtrada
    rej_boulder = beta_pb2.MidiaBeta(
        url="https://scribd.com/doc/999",
        titulo="Descartado",
        fonte=beta_pb2.FonteMidia.BLOG,
    )
    controller.adicionar_betas_rejeitados_lote("uid_boulder_04", [rej_boulder])

    # Página 1: offset=0, limite=2 -> deve retornar 2 escaladas e tem_mais=True
    pag1 = _chamar(
        servidor,
        "aresta_listar_betas_nao_scorados",
        {"offset": 0, "limite": 2},
    )
    assert pag1["total_escaladas_pendentes"] == 3
    assert pag1["total_candidatos_pendentes"] == 3
    assert pag1["offset"] == 0
    assert pag1["limite"] == 2
    assert pag1["tem_mais"] is True
    assert len(pag1["escaladas"]) == 2

    item0 = pag1["escaladas"][0]
    assert item0["indice_curadoria"] == 0
    assert item0["escalada_uid"] == "uid_via_cova01"
    assert item0["nome"] == "Cova dos Leões"
    assert item0["dificuldade"] == "BR_7B"
    assert item0["modalidade"] == "via_esportiva"
    assert item0["setor_uid"] == "uid_setor_savassinha"
    assert item0["setor_nome"] == "Setor Savassinha"
    assert item0["pico_nome"] == "Gruta da Lapinha"
    assert item0["conquistadores"] == ["Emerson", "Gilberto"]
    assert len(item0["betas_nao_scorados"]) == 1
    assert "betas_rejeitados" not in item0

    # Página 2: offset=2, limite=2 -> deve retornar a 3ª escalada (Gota D'água) e tem_mais=False
    pag2 = _chamar(
        servidor,
        "aresta_listar_betas_nao_scorados",
        {"offset": 2, "limite": 2},
    )
    assert pag2["tem_mais"] is False
    assert len(pag2["escaladas"]) == 1
    assert pag2["escaladas"][0]["escalada_uid"] == "uid_via_gota03"
    assert pag2["escaladas"][0]["modalidade"] == "via_movel"
    assert pag2["escaladas"][0]["setor_nome"] == "Setor Túnel"

    # Filtro por alvo_setor na listagem paginada
    pag_setor = _chamar(
        servidor,
        "aresta_listar_betas_nao_scorados",
        {"alvo_setor": "uid_setor_tunel"},
    )
    assert pag_setor["total_escaladas_pendentes"] == 1
    assert pag_setor["escaladas"][0]["escalada_uid"] == "uid_via_gota03"


def test_coleta_em_background_micro_lotes_status_e_cancelamento_preservando_progresso(
    qapp, tmp_path: Path
):
    """
    Valida que uma coleta mais longa retorna status='em_andamento' quando excede aguardar_segundos,
    persiste micro-lotes incrementalmente via DespachanteQt e preserva o progresso parcial ao cancelar.
    """
    evento_liberar_segunda_via = threading.Event()
    primeira_via_concluida = threading.Event()

    class _ExtratorControlado:
        def __init__(self) -> None:
            self.chamadas = 0
            self._lock = threading.Lock()

        def buscar_com_rejeitados(
            self,
            nome_escalada: str,
            nome_setor: str = "",
            nome_pico: str = "",
        ) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
            _ = (nome_setor, nome_pico)
            with self._lock:
                self.chamadas += 1
                num = self.chamadas
            if num == 1:
                cand = beta_pb2.CandidatoMidiaBeta()
                cand.midia.url = f"https://youtube.com/watch?v=via_{num}"
                cand.midia.titulo = f"Beta {nome_escalada}"
                cand.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
                rej = beta_pb2.MidiaBeta(
                    url=f"https://scribd.com/doc/{num}",
                    titulo="Auto-filtrado",
                    fonte=beta_pb2.FonteMidia.BLOG,
                )
                primeira_via_concluida.set()
                return [cand], [rej]

            evento_liberar_segunda_via.wait(timeout=2.0)
            return [], []

    model, _, _, servidor, _ = _montar_croqui_betas(
        tmp_path,
        extratores=[_ExtratorControlado()],
    )

    # Inicia em uma thread cliente simulando a thread HTTP do Uvicorn (fora da thread do Qt)
    caixa_inicio: list[dict[str, Any]] = []

    def _iniciar_remoto() -> None:
        res = _chamar(
            servidor,
            "aresta_coletar_betas",
            {
                "acao": "iniciar",
                "aguardar_segundos": 0.05,
                "tamanho_lote_flush": 1,
                "max_workers": 1,
            },
        )
        caixa_inicio.append(res)

    t_req = threading.Thread(target=_iniciar_remoto)
    t_req.start()

    prazo = time.monotonic() + 3.0
    while t_req.is_alive() and time.monotonic() < prazo:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    t_req.join(timeout=1.0)

    assert len(caixa_inicio) == 1
    assert caixa_inicio[0]["status"] == "em_andamento"

    # Aguarda o flush da 1ª via processar os sinais do DespachanteQt na thread principal
    prazo_via1 = time.monotonic() + 3.0
    while not primeira_via_concluida.is_set() and time.monotonic() < prazo_via1:
        QCoreApplication.processEvents()
        time.sleep(0.01)
    for _ in range(10):
        QCoreApplication.processEvents()
        time.sleep(0.01)

    # Consulta 'status' com long-polling curto enquanto a coleta segue em andamento
    caixa_status: list[dict[str, Any]] = []
    t_status = threading.Thread(
        target=lambda: caixa_status.append(
            _chamar(servidor, "aresta_coletar_betas", {"acao": "status", "aguardar_segundos": 0.02})
        )
    )
    t_status.start()
    while t_status.is_alive():
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert caixa_status[0]["status"] == "em_andamento"

    # Chamar 'iniciar' novamente enquanto já está em_andamento deve apenas consultar o job ativo
    caixa_dup: list[dict[str, Any]] = []
    t_dup = threading.Thread(
        target=lambda: caixa_dup.append(
            _chamar(
                servidor, "aresta_coletar_betas", {"acao": "iniciar", "aguardar_segundos": 0.01}
            )
        )
    )
    t_dup.start()
    while t_dup.is_alive():
        QCoreApplication.processEvents()
        time.sleep(0.01)
    assert caixa_dup[0]["status"] == "em_andamento"
    assert caixa_dup[0]["escaladas_processadas"] >= 1
    assert caixa_dup[0]["novos_candidatos_adicionados"] == 1

    # Cancela a coleta enquanto a 2ª via está em execução e libera o bloqueio logo em seguida
    caixa_canc: list[dict[str, Any]] = []
    t_canc = threading.Thread(
        target=lambda: caixa_canc.append(
            _chamar(servidor, "aresta_coletar_betas", {"acao": "cancelar"})
        )
    )
    t_canc.start()
    time.sleep(0.02)
    evento_liberar_segunda_via.set()
    while t_canc.is_alive():
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert caixa_canc[0]["status"] == "cancelado"
    # O micro-lote da 1ª via foi preservado no modelo!
    raiz = model.obter_croqui_readonly()
    assert len(raiz.curadoria_betas.conteudo.escaladas) == 1
    assert len(raiz.curadoria_betas.conteudo.escaladas[0].betas_nao_scorados) == 1


def test_validacoes_fail_fast_ferramentas_betas(qapp, tmp_path: Path):
    """Valida erros descritivos para parâmetros inválidos em aresta_coletar_betas e aresta_listar_betas_nao_scorados."""
    _, _, _, servidor, _ = _montar_croqui_betas(tmp_path)

    with pytest.raises(ValueError, match="Ação inválida"):
        _chamar(servidor, "aresta_coletar_betas", {"acao": "invalida"})

    with pytest.raises(ValueError, match="Setor"):
        _chamar(
            servidor,
            "aresta_coletar_betas",
            {"acao": "iniciar", "alvo_setor": "setor_inexistente"},
        )

    with pytest.raises(ValueError, match="Nenhuma escalada encontrada"):
        _chamar(
            servidor,
            "aresta_coletar_betas",
            {"acao": "iniciar", "escaladas_uids": ["uid_inexistente"]},
        )

    with pytest.raises(ValueError, match="offset"):
        _chamar(servidor, "aresta_listar_betas_nao_scorados", {"offset": -1})

    with pytest.raises(ValueError, match="limite"):
        _chamar(servidor, "aresta_listar_betas_nao_scorados", {"limite": 0})

    with pytest.raises(ValueError, match="Setor"):
        _chamar(
            servidor,
            "aresta_listar_betas_nao_scorados",
            {"alvo_setor": "setor_inexistente"},
        )


def test_aresta_pontuar_betas_promove_e_expoe_cidade_croqui_na_listagem(qapp, tmp_path: Path):
    """
    Valida que aresta_listar_betas_nao_scorados expõe pico_cidade e croqui_nome, e que
    aresta_pontuar_betas promove candidatos via MCP preservando snippets sem reenviar a lista completa.
    """
    model, undo_stack, controller, servidor, _ = _montar_croqui_betas(tmp_path)
    raiz_raw = getattr(model.obter_croqui_readonly(), "_obj", model.obter_croqui_readonly())
    raiz_raw.picos[0].cidade = "Lagoa Santa"

    cand = beta_pb2.CandidatoMidiaBeta()
    cand.midia.url = "https://youtube.com/watch?v=EQYAydeVEsY"
    cand.midia.titulo = "Cova dos Leões - Lagoa Santa"
    cand.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
    cand.snippets.append("Cadena clássica em Lagoa Santa.")
    controller.adicionar_candidatos_nao_scorados("uid_via_cova01", [cand])

    pag = _chamar(servidor, "aresta_listar_betas_nao_scorados", {"offset": 0, "limite": 10})
    assert pag["escaladas"][0]["pico_cidade"] == "Lagoa Santa"
    assert pag["escaladas"][0]["croqui_nome"] == "Gruta da Lapinha"

    res_pont = _chamar(
        servidor,
        "aresta_pontuar_betas",
        {
            "escaladas": [
                {
                    "escalada_uid": "uid_via_cova01",
                    "avaliacoes": [
                        {
                            "url": "https://youtube.com/watch?v=EQYAydeVEsY",
                            "llm_confidence_score": 96,
                            "llm_reasoning": "Cadena exata da via Cova dos Leões na Lapinha.",
                        }
                    ],
                }
            ]
        },
    )
    assert res_pont["status"] == "ok"
    assert res_pont["escaladas_atualizadas"] == 1
    assert res_pont["candidatos_pontuados"] == 1
    assert res_pont["total_escaladas_pendentes"] == 0
    assert res_pont["total_candidatos_pendentes"] == 0

    cur = raiz_raw.curadoria_betas.conteudo.escaladas[0]
    assert len(cur.betas_nao_scorados) == 0
    assert len(cur.betas_nao_revisados) == 1
    assert list(cur.betas_nao_revisados[0].snippets) == ["Cadena clássica em Lagoa Santa."]
    assert cur.betas_nao_revisados[0].resultado_llm.llm_confidence_score == 96

    undo_stack.undo()
    assert len(cur.betas_nao_scorados) == 1
    assert len(cur.betas_nao_revisados) == 0

    with pytest.raises(ValueError, match="Informe uma lista em 'escaladas'"):
        _chamar(servidor, "aresta_pontuar_betas", {"escaladas": "nao_e_lista"})


def test_aresta_coletar_betas_reavalia_auto_filtrados_e_propaga_cidade(qapp, tmp_path: Path):
    """
    Valida que aresta_coletar_betas reavalia itens [Auto-filtrado: ...] offline no início
    (incluindo em escaladas que já possuem coleta com apenas_sem_coleta=True) e contabiliza
    `auto_filtrados_promovidos` na resposta.
    """
    model, _, controller, servidor, _ = _montar_croqui_betas(tmp_path)
    raiz_raw = getattr(model.obter_croqui_readonly(), "_obj", model.obter_croqui_readonly())
    raiz_raw.picos[0].cidade = "Lagoa Santa"

    cur = raiz_raw.curadoria_betas.conteudo.escaladas.add(escalada_uid="uid_via_cova01")
    cur.betas_rejeitados.add(
        url="https://youtube.com/watch?v=resgatado_lagoa",
        titulo="[Query: youtube | Auto-filtrado: sem menção ao pico] Cova dos Leões Lagoa Santa",
        fonte=beta_pb2.FonteMidia.YOUTUBE,
    )

    res = _chamar(
        servidor,
        "aresta_coletar_betas",
        {
            "acao": "iniciar",
            "escaladas_uids": ["uid_via_cova01"],
            "apenas_sem_coleta": True,
            "aguardar_segundos": 5.0,
        },
    )
    assert res["status"] == "concluido"
    assert res["auto_filtrados_promovidos"] == 1
    assert res["total_escaladas"] == 0
    assert [c.midia.url for c in cur.betas_nao_scorados] == [
        "https://youtube.com/watch?v=resgatado_lagoa"
    ]


def test_aresta_adicionar_betas_revisao_e_remover_betas_via_mcp_e_multi_croqui(
    qapp, tmp_path: Path
):
    """
    Valida as ferramentas MCP `aresta_adicionar_betas_revisao` e `aresta_remover_betas`,
    incluindo string JSON, roteamento proxy multi-janela com `id_croqui` e erros fail-fast.
    """
    import json

    from editor.mcp.despachante import DespachanteQt
    from editor.mcp.ferramentas_betas import registrar_ferramentas_betas
    from editor.mcp.servidor import ServidorMCP
    from editor.mcp.sessao import alocar_porta_mcp

    dir_sessao = tmp_path / "sessao_betas_multi"
    model_1, undo_1, ctrl_1, srv_1, _ = _montar_croqui_betas(tmp_path / "c1")
    raiz_1 = getattr(model_1.obter_croqui_readonly(), "_obj", model_1.obter_croqui_readonly())

    # 1. Chamada com string JSON (Constrained Decoding) adicionando para betas_nao_revisados
    itens_json = json.dumps(
        [
            {
                "escalada_uid": "uid_via_cova01",
                "url": "https://youtu.be/beta_manual_01",
                "titulo": "Beta Adicionado via MCP",
                "llm_confidence_score": 91,
                "llm_reasoning": "Vídeo claro da cadena da via.",
            }
        ]
    )
    res_add = _chamar(srv_1, "aresta_adicionar_betas_revisao", {"itens": itens_json})
    assert res_add["status"] == "ok"
    assert res_add["adicionados_nao_revisados"] == 1
    assert res_add["total_escaladas_pendentes"] == 0
    assert len(raiz_1.curadoria_betas.conteudo.escaladas[0].betas_nao_revisados) == 1

    # 2. Adiciona item sem score -> entra em betas_nao_scorados e contabiliza pendentes
    res_add_ns = _chamar(
        srv_1,
        "aresta_adicionar_betas_revisao",
        {
            "itens": [
                {
                    "escalada_uid": "uid_via_cova01",
                    "url": "https://instagram.com/reel/CreelNovo1",
                    "titulo": "Reel Pendente",
                }
            ]
        },
    )
    assert res_add_ns["adicionados_nao_scorados"] == 1
    assert res_add_ns["total_escaladas_pendentes"] == 1
    assert res_add_ns["total_candidatos_pendentes"] == 1

    # 3. Remoção via aresta_remover_betas move para betas_rejeitados por padrão
    res_rem = _chamar(
        srv_1,
        "aresta_remover_betas",
        {
            "itens": [
                {
                    "escalada_uid": "uid_via_cova01",
                    "url": "https://youtube.com/watch?v=beta_manual_01",
                }
            ]
        },
    )
    assert res_rem["status"] == "ok"
    assert res_rem["removidos_de_pendentes"] == 1
    assert res_rem["movidos_para_rejeitados"] == 1
    assert [m.url for m in raiz_1.curadoria_betas.conteudo.escaladas[0].betas_rejeitados] == [
        "https://youtube.com/watch?v=beta_manual_01"
    ]

    # 4. Validação fail-fast de payloads não-lista
    with pytest.raises(ValueError, match="lista"):
        _chamar(srv_1, "aresta_adicionar_betas_revisao", {"itens": "invalido"})
    with pytest.raises(ValueError, match="lista"):
        _chamar(srv_1, "aresta_remover_betas", {"itens": "invalido"})

    # 5. Roteamento proxy multi-janela com id_croqui entre duas instâncias reais de ServidorMCP
    porta_1 = alocar_porta_mcp()
    srv_proxy_1 = ServidorMCP(
        despachante=DespachanteQt(),
        porta_preferencial=porta_1,
        diretorio_sessao=dir_sessao,
    )
    srv_proxy_1.definir_croqui_ativo("croqui_alfa", croqui_aberto=True)
    registrar_ferramentas_betas(srv_proxy_1, model_1, ctrl_1, extratores=[])

    croqui_2 = croqui_pb2.Croqui(uid="uid_croqui_2", id="croqui_beta", nome="Croqui Beta")
    pico_2 = croqui_2.picos.add(nome="Pico Beta")
    setor_2 = pico_2.setores_ou_grupos.add().setor.conteudo
    setor_2.uid = "setor_beta"
    esc_2 = setor_2.escaladas.add(uid="esc_beta_01")
    esc_2.via_esportiva.nome = "Via Beta"
    model_2 = CroquiModel(croqui_2)
    ctrl_2 = CroquiController(model_2, undo_1.__class__())
    srv_proxy_2 = ServidorMCP(
        despachante=DespachanteQt(),
        porta_preferencial=porta_1 + 1,
        diretorio_sessao=dir_sessao,
    )
    srv_proxy_2.definir_croqui_ativo("croqui_beta", croqui_aberto=True)
    registrar_ferramentas_betas(srv_proxy_2, model_2, ctrl_2, extratores=[])

    srv_proxy_1.iniciar()
    srv_proxy_2.iniciar()
    try:
        resp_roteada = srv_proxy_1.processar_mensagem_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {
                    "name": "aresta_adicionar_betas_revisao",
                    "arguments": {
                        "id_croqui": "croqui_beta",
                        "itens": [
                            {
                                "escalada_uid": "esc_beta_01",
                                "url": "https://youtube.com/watch?v=beta_croqui_2",
                                "titulo": "Beta Croqui 2",
                            }
                        ],
                    },
                },
            }
        )
        assert resp_roteada is not None
        assert resp_roteada["result"]["isError"] is False
        assert resp_roteada["result"]["structuredContent"]["adicionados_nao_scorados"] == 1
        assert (
            len(
                model_2.obter_croqui_readonly()
                .curadoria_betas.conteudo.escaladas[0]
                .betas_nao_scorados
            )
            == 1
        )
    finally:
        srv_proxy_2.parar()
        srv_proxy_1.parar()
