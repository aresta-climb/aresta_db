# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtWidgets import QWidget
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.painel_curadoria import PainelCuradoria, ItemBetaWidget

def test_item_beta_widget_renderiza_informacoes(qtbot):
    midia = beta_pb2.MidiaBeta()
    midia.url = "https://youtube.com/v1"
    midia.titulo = "Mandando Fusca Azul V4"
    midia.fonte = beta_pb2.FonteMidia.YOUTUBE
    midia.match_multiplas_fontes = True
    midia.match_nome_no_snippet = True
    midia.meta.llm_confidence_score = 95
    midia.meta.llm_reasoning = "Perfeita correspondência"
    midia.meta.resumo_do_movimento = "Pegue a reglete e bote no topo"

    widget = ItemBetaWidget(midia)
    qtbot.addWidget(widget)

    assert "Mandando Fusca Azul V4" in widget.label_titulo.text()
    assert "95%" in widget.label_score.text()
    assert "Perfeita correspondência" in widget.label_reasoning.text()
    assert "Pegue a reglete" in widget.label_crux.text()
    assert widget.checkbox_aprovado.isChecked() is False

    # Marca como aprovado
    widget.checkbox_aprovado.setChecked(True)
    assert widget.esta_aprovado() is True


def test_painel_curadoria_carrega_staging(tmp_path, qtbot):
    arquivo_pb = tmp_path / "betas_pendentes.binarypb"

    msg = beta_pb2.BetasPendentes()
    msg.id_croqui = "croqui_teste"

    escalada = msg.candidatos_por_escalada.add()
    escalada.nome_escalada = "Fusca Azul"
    escalada.nome_setor = "Geriatria"

    m1 = escalada.candidatos.add()
    m1.url = "https://youtube.com/v1"
    m1.titulo = "Vídeo 1"
    m1.meta.llm_confidence_score = 90

    m2 = escalada.candidatos.add()
    m2.url = "https://instagram.com/p/123"
    m2.titulo = "Post 2"
    m2.meta.llm_confidence_score = 30

    with open(arquivo_pb, "wb") as f:
        f.write(msg.SerializeToString())

    painel = PainelCuradoria()
    qtbot.addWidget(painel)

    painel.carregar_staging(arquivo_pb)

    assert painel.obter_id_croqui() == "croqui_teste"
    assert len(painel.itens_widgets) == 2

    # Aprova apenas o item 1
    painel.itens_widgets[0].checkbox_aprovado.setChecked(True)

    aprovados = painel.obter_betas_aprovados()
    assert "Fusca Azul" in aprovados
    assert len(aprovados["Fusca Azul"]) == 1
    assert aprovados["Fusca Azul"][0].url == "https://youtube.com/v1"
