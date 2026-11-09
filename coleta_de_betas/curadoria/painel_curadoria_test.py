# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from coleta_de_betas.curadoria.painel_curadoria import (
    CardBetaCuradoria,
    PainelCuradoria,
)
from coleta_de_betas.curadoria.provedor_imagem_aresta import ProvedorImagemAresta
from coleta_de_betas.extratores.cliente_http_fake import ClienteHttpFake
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel


def _criar_croqui_curadoria() -> croqui_pb2.Croqui:
    croqui = croqui_pb2.Croqui(uid="croqui_1", id="serra_cipo", nome="Serra do Cipó")
    pico = croqui.picos.add(nome="Morro da Pedreira")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    setor.uid = "setor_1"
    setor.nome = "Salão"

    esc1 = setor.escaladas.add(uid="esc_1")
    esc1.via_esportiva.nome = "Fusca Azul"
    esc1.betas.add(
        url="https://youtube.com/watch?v=ja_aprovado",
        titulo="Beta Já Aprovado",
        fonte=beta_pb2.FonteMidia.YOUTUBE,
    )

    esc2 = setor.escaladas.add(uid="esc_2")
    esc2.boulder.nome = "Crux de Cristal"

    cur1 = croqui.curadoria_betas.conteudo.escaladas.add(escalada_uid="esc_1")

    # 2 candidatos não revisados fora de ordem (devem aparecer ordenados por score decrescente: 95 depois 60)
    nr_baixo = cur1.betas_nao_revisados.add()
    nr_baixo.midia.url = "https://instagram.com/p/score60"
    nr_baixo.midia.titulo = "Post Score 60"
    nr_baixo.midia.fonte = beta_pb2.FonteMidia.INSTAGRAM
    nr_baixo.resultado_llm.llm_confidence_score = 60
    nr_baixo.resultado_llm.llm_reasoning = "Apenas foto na base."

    nr_alto = cur1.betas_nao_revisados.add()
    nr_alto.midia.url = "https://youtube.com/watch?v=score95"
    nr_alto.midia.titulo = "Vídeo Score 95"
    nr_alto.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
    nr_alto.resultado_llm.llm_confidence_score = 95
    nr_alto.resultado_llm.llm_reasoning = "Mostra todos os movimentos da via."
    nr_alto.snippets.append("Mandando a Fusca Azul")

    # 1 candidato não scorado
    ns = cur1.betas_nao_scorados.add()
    ns.midia.url = "https://blogescalada.com/fusca-azul"
    ns.midia.titulo = "Relato Blog Fusca Azul"
    ns.midia.fonte = beta_pb2.FonteMidia.BLOG
    ns.snippets.append("O crux fica na terceira chapeleta.")

    # 1 beta rejeitado
    cur1.betas_rejeitados.add(
        url="https://youtube.com/watch?v=ruido",
        titulo="Vídeo Ruído",
        fonte=beta_pb2.FonteMidia.YOUTUBE,
    )

    return croqui


def test_painel_curadoria_exibe_4_secoes_ordena_por_score_e_transiciona_1_a_1_com_undo(
    tmp_path: Path, qtbot
) -> None:
    croqui = _criar_croqui_curadoria()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)
    provedor = ProvedorImagemAresta(
        diretorio_cache=tmp_path / "cache",
        cliente_http=ClienteHttpFake(),
    )

    painel = PainelCuradoria(provedor_imagem=provedor, carregar_assincrono=False)
    qtbot.addWidget(painel)
    painel.carregar_dados(model, controller)

    # Verifica que as 4 seções e o banner MCP existem
    assert "avaliar_betas_croqui" in painel.label_instrucoes_mcp.text()
    assert len(painel.cards_nao_revisados) == 2
    assert len(painel.cards_nao_scorados) == 1
    assert len(painel.cards_aprovados) == 1
    assert len(painel.cards_rejeitados) == 1

    # Ordenação por score decrescente em betas_nao_revisados (95 vem antes de 60)
    assert "Vídeo Score 95" in painel.cards_nao_revisados[0].label_titulo.text()
    assert "95%" in painel.cards_nao_revisados[0].label_score.text()
    assert "Post Score 60" in painel.cards_nao_revisados[1].label_titulo.text()

    # 1. Aprovar 1 a 1 o card de score 95 -> vai para escalada.betas
    card_95: CardBetaCuradoria = painel.cards_nao_revisados[0]
    assert card_95.btn_aprovar is not None
    card_95.btn_aprovar.click()

    assert len(painel.cards_nao_revisados) == 1
    assert len(painel.cards_aprovados) == 2
    assert croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].betas[-1].url == (
        "https://youtube.com/watch?v=score95"
    )

    # Undo reverte a aprovação e atualiza o painel automaticamente
    stack.undo()
    assert len(painel.cards_nao_revisados) == 2
    assert len(painel.cards_aprovados) == 1
    stack.redo()

    # 2. Rejeitar 1 a 1 o candidato de betas_nao_scorados -> vai para betas_rejeitados
    card_ns = painel.cards_nao_scorados[0]
    assert card_ns.btn_rejeitar is not None
    card_ns.btn_rejeitar.click()
    assert len(painel.cards_nao_scorados) == 0
    assert len(painel.cards_rejeitados) == 2

    # 3. Restaurar 1 a 1 um item de betas_rejeitados -> volta para betas_nao_scorados
    card_rej = painel.cards_rejeitados[0]
    assert card_rej.btn_restaurar is not None
    card_rej.btn_restaurar.click()
    assert len(painel.cards_rejeitados) == 1
    assert len(painel.cards_nao_scorados) == 1

    # 4. Filtrar por escalada_uid específica ("esc_2" sem candidatos)
    painel.selecionar_escalada_por_uid("esc_2")
    assert len(painel.cards_nao_revisados) == 0
    assert len(painel.cards_aprovados) == 0

    painel.selecionar_escalada_por_uid("esc_1")
    assert len(painel.cards_aprovados) == 2


def test_painel_curadoria_coalesce_mutacoes_em_lote_e_encerra_workers_de_thumbnail(
    tmp_path: Path, qtbot
) -> None:
    croqui = _criar_croqui_curadoria()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)
    provedor = ProvedorImagemAresta(
        diretorio_cache=tmp_path / "cache",
        cliente_http=ClienteHttpFake(),
    )

    painel = PainelCuradoria(provedor_imagem=provedor, carregar_assincrono=True)
    qtbot.addWidget(painel)
    painel.carregar_dados(model, controller)

    atualizacoes_antes = painel.total_atualizacoes_visualizacao
    assert atualizacoes_antes == 1

    # Inserir 5 novos candidatos em lote para esc_2 deve reconstruir os cards apenas 1 vez
    novos_candidatos = [
        beta_pb2.CandidatoMidiaBeta(
            midia=beta_pb2.MidiaBeta(
                url=f"https://youtube.com/watch?v=lote_{i}",
                titulo=f"Beta Lote {i}",
                fonte=beta_pb2.FonteMidia.YOUTUBE,
            )
        )
        for i in range(5)
    ]
    adicionados = controller.adicionar_candidatos_nao_scorados("esc_2", novos_candidatos)
    assert adicionados == 5
    assert painel.total_atualizacoes_visualizacao == atualizacoes_antes + 1
    assert len(painel.cards_nao_scorados) == 6

    # Undo do lote de 5 candidatos também deve reconstruir os cards apenas 1 vez
    stack.undo()
    assert painel.total_atualizacoes_visualizacao == atualizacoes_antes + 2
    assert len(painel.cards_nao_scorados) == 1

