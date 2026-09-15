# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o diálogo de seleção e criação rápida de rota no mapa (DialogoNovaRotaMapa).
Princípios II (Library-First) e IV (TDD) de AGENTS.md.
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from aresta_api.proto.generated import croqui_pb2
from editor.views.dialogos.dialogo_nova_rota_mapa import DialogoNovaRotaMapa


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def _criar_setor_e_mapa_teste():
    setor = croqui_pb2.Setor(nome="Setor das Pedras")

    # Escalada 1: Boulder mapeado
    e1 = setor.escaladas.add()
    e1.boulder.nome = "Boulder Mapeado"
    e1.boulder.dificuldade = croqui_pb2.GrauBoulder.V4

    # Escalada 2: Boulder não mapeado
    e2 = setor.escaladas.add()
    e2.boulder.nome = "Boulder Livre"
    e2.boulder.dificuldade = croqui_pb2.GrauBoulder.V6

    # Escalada 3: Via esportiva não mapeada
    e3 = setor.escaladas.add()
    e3.via_esportiva.nome = "Via Esportiva Livre"
    e3.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A

    # Mapa atual referenciando a Escalada 1
    mapa = setor.mapas.add()
    mapa.referencias.add(escalada="Boulder Mapeado", ids=["linha_1"])

    return setor, mapa


def test_dialogo_exibe_escaladas_mapeadas_em_cinza_e_desabilita_confirmar(qapp, monkeypatch):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    textos_itens = [dialogo.lista_resultados.item(i).text() for i in range(dialogo.lista_resultados.count())]
    assert any("Boulder Livre" in t for t in textos_itens)
    assert any("Via Esportiva Livre" in t for t in textos_itens)
    assert any("Boulder Mapeado" in t and "[já no mapa]" in t for t in textos_itens)

    # Selecionar o item já mapeado deve desabilitar o botão Confirmar
    idx_mapeado = next(i for i, t in enumerate(textos_itens) if "Boulder Mapeado" in t)
    dialogo.lista_resultados.setCurrentRow(idx_mapeado)
    assert not dialogo.btn_confirmar.isEnabled()
    assert dialogo.painel_nova_rota.isHidden()

    # Duplo clique em item já mapeado não deve aceitar
    aceitou = False
    def mock_accept():
        nonlocal aceitou
        aceitou = True
    monkeypatch.setattr(dialogo, "accept", mock_accept)
    dados_mapeados = dialogo.obter_dados_rota()
    dialogo._ao_entidade_ativada(dados_mapeados)
    assert aceitou is False
    dialogo._on_item_duplo_clicado(dialogo.lista_resultados.currentItem())
    assert aceitou is False



def test_busca_filtra_escaladas_existentes(qapp):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    dialogo.input_busca.setText("Esportiva")
    itens_visiveis = [
        dialogo.lista_resultados.item(i).text()
        for i in range(dialogo.lista_resultados.count())
        if not dialogo.lista_resultados.item(i).isHidden()
    ]
    assert any("Via Esportiva Livre" in t for t in itens_visiveis)
    assert not any("Boulder Livre" in t for t in itens_visiveis)


def test_selecao_escalada_existente(qapp):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    # Seleciona uma escalada existente livre (não mapeada)
    idx_livre = next(i for i in range(dialogo.lista_resultados.count()) if "Livre" in dialogo.lista_resultados.item(i).text())
    dialogo.lista_resultados.setCurrentRow(idx_livre)
    assert dialogo.btn_confirmar.isEnabled()

    dados = dialogo.obter_dados_rota()
    assert dados["nova"] is False
    assert dados["nome"] in ["Boulder Livre", "Via Esportiva Livre"]


def test_opcao_criar_nova_escalada(qapp):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    dialogo.input_busca.setText("Projeto Misterioso")
    # Deve haver a opção especial de criar nova
    item_criar = None
    for i in range(dialogo.lista_resultados.count()):
        item = dialogo.lista_resultados.item(i)
        if "Criar Nova" in item.text():
            item_criar = item
            break
    assert item_criar is not None

    dialogo.lista_resultados.setCurrentItem(item_criar)
    assert not dialogo.painel_nova_rota.isHidden()

    # Configura tipo e grau
    dialogo.combo_tipo.setCurrentText("Boulder")
    dialogo.edit_grau.setText("V8")

    dados = dialogo.obter_dados_rota()
    assert dados["nova"] is True
    assert dados["nome"] == "Projeto Misterioso"
    assert dados["tipo"] == "boulder"
    assert dados["grau"] == "V8"


def test_duplo_clique_seleciona_e_aceita(qapp, monkeypatch):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    aceitou = False
    def mock_accept():
        nonlocal aceitou
        aceitou = True

    monkeypatch.setattr(dialogo, "accept", mock_accept)
    idx_livre = next(i for i in range(dialogo.lista_resultados.count()) if "Livre" in dialogo.lista_resultados.item(i).text())
    dialogo.lista_resultados.setCurrentRow(idx_livre)
    dialogo._on_item_duplo_clicado(dialogo.lista_resultados.currentItem())
    assert aceitou is True


def test_validacao_nome_vazio_desabilita_confirmar(qapp):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    dialogo.input_busca.setText("")
    dialogo.lista_resultados.clearSelection()
    assert not dialogo.btn_confirmar.isEnabled()


def test_escalada_sem_tipo_e_obter_dados_sem_selecao(qapp):
    setor = croqui_pb2.Setor(nome="Setor")
    setor.escaladas.add()  # escalada vazia sem tipo
    mapa = setor.mapas.add()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    # Nenhuma escalada adicionada na lista
    assert dialogo.lista_resultados.count() == 0

    # Deseleciona
    dialogo.lista_resultados.clearSelection()
    dialogo._ao_selecionar_item()
    assert dialogo.painel_nova_rota.isHidden()
    assert dialogo.obter_dados_rota() == {}


def test_acesso_propriedade_escaladas_disponiveis(qapp):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)
    disponiveis = dialogo.escaladas_disponiveis
    assert len(disponiveis) == 3
    nomes = [d["nome"] for d in disponiveis]
    assert "Boulder Mapeado" in nomes
    assert "Boulder Livre" in nomes
    assert "Via Esportiva Livre" in nomes


def test_ao_entidade_ativada_aceita_dialogo(qapp, monkeypatch):
    setor, mapa = _criar_setor_e_mapa_teste()
    dialogo = DialogoNovaRotaMapa(setor=setor, mapa=mapa)

    aceitou = False
    def mock_accept():
        nonlocal aceitou
        aceitou = True

    monkeypatch.setattr(dialogo, "accept", mock_accept)
    idx_livre = next(i for i in range(dialogo.lista_resultados.count()) if "Livre" in dialogo.lista_resultados.item(i).text())
    dialogo.lista_resultados.setCurrentRow(idx_livre)
    dialogo._ao_entidade_ativada(dialogo.obter_dados_rota())
    assert aceitou is True


def test_dialogo_com_model_carrega_escaladas_de_grupos_e_subsetores(qapp):
    """
    Testa a solução do problema das Fotos 1 e 2:
    Quando o mapa é de um Grupo (ou setor não foi resolvido),
    passar o model permite listar escaladas de todos os sub-setores.
    """
    croqui = croqui_pb2.Croqui(nome="Croqui Pedra Grande")
    pico = croqui.picos.add(nome="Pedra Grande")
    sg = pico.setores_ou_grupos.add()
    grupo = sg.grupo.conteudo
    grupo.nome = "Complexo Pedra Grande"

    sub_setor = grupo.setores.add().conteudo
    sub_setor.nome = "Setor Estacionamento"

    via1 = sub_setor.escaladas.add()
    via1.via_esportiva.nome = "Bacon com Linguiça"
    via1.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A

    via2 = sub_setor.escaladas.add()
    via2.via_esportiva.nome = "Bobo da Corte"

    # Mapa do grupo (sem setor direto)
    mapa = grupo.mapas.add()

    from editor.models.croqui_model import CroquiModel
    model = CroquiModel(croqui)

    dialogo = DialogoNovaRotaMapa(setor=None, mapa=mapa, model=model)

    # Ambas as vias devem estar listadas mesmo sem setor direto
    textos = [dialogo.lista_resultados.item(i).text() for i in range(dialogo.lista_resultados.count())]
    assert any("Bacon com Linguiça" in t for t in textos)
    assert any("Bobo da Corte" in t for t in textos)

    # Selecionar "Bacon com Linguiça" deve carregar seu setor_obj correspondente
    dialogo.input_busca.setText("Bacon")
    # 2 itens: a via encontrada + a opção especial de criar nova
    assert dialogo.lista_resultados.count() == 2
    dialogo.lista_resultados.setCurrentRow(0)
    dados = dialogo.obter_dados_rota()
    assert dados["nome"] == "Bacon com Linguiça"
    assert dados["nova"] is False
    assert dados["setor_nome"] == "Setor Estacionamento"
    assert dados["grupo_nome"] == "Complexo Pedra Grande"
    assert dados["setor_obj"] == sub_setor


