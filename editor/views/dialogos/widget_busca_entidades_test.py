# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para WidgetBuscaEntidades.
Atende aos Princípios I, II, III e IV de AGENTS.md (TDD, 100% de cobertura).
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.widget_busca_entidades import WidgetBuscaEntidades


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def _criar_croqui_teste():
    croqui = croqui_pb2.Croqui(nome="Croqui Completo")

    # Pico 1 com Grupo e Sub-setor
    pico1 = croqui.picos.add(nome="Pedra Grande")
    sg1 = pico1.setores_ou_grupos.add()
    grupo = sg1.grupo.conteudo
    grupo.nome = "Complexo Pedra Grande"

    setor1 = grupo.setores.add().conteudo
    setor1.nome = "Setor Estacionamento"

    # Escalada 1 no Sub-setor: Via esportiva com grau
    v1 = setor1.escaladas.add()
    v1.via_esportiva.nome = "Bacon com Linguiça"
    v1.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A

    # Escalada 2 no Sub-setor: Boulder com acento e grau
    b1 = setor1.escaladas.add()
    b1.boulder.nome = "Vía Láctea"
    b1.boulder.dificuldade = croqui_pb2.GrauBoulder.V4

    # Escalada vazia no Sub-setor
    setor1.escaladas.add()

    # Pico 2 com Setor direto (sem Grupo)
    pico2 = croqui.picos.add(nome="Pico Isolado")
    sg2 = pico2.setores_ou_grupos.add()
    setor2 = sg2.setor.conteudo
    setor2.nome = "Setor das Sombras"

    # Escalada 3: Via móvel sem grau definido
    v2 = setor2.escaladas.add()
    v2.via_movel.nome = "Fissura das Sombras"

    # Escalada 4: Sem tipo preenchido (WhichOneof nulo)
    setor2.escaladas.add()

    return croqui, setor1, setor2


def test_inicializacao_padrao_carrega_todas_as_entidades(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model)

    # Entidades esperadas:
    # 1. Grupo: Complexo Pedra Grande
    # 2. Setor: Setor Estacionamento
    # 3. Escalada: Bacon com Linguiça
    # 4. Escalada: Vía Láctea
    # 5. Setor: Setor das Sombras
    # 6. Escalada: Fissura das Sombras
    assert len(widget.todas_entidades) == 6
    assert widget.lista_resultados.count() == 6

    # O primeiro item deve ser selecionado automaticamente
    assert widget.lista_resultados.currentRow() == 0
    sel = widget.obter_entidade_selecionada()
    assert sel is not None
    assert sel["tipo"] == "Grupo"
    assert sel["grupo"] == "Complexo Pedra Grande"


def test_filtro_por_tipos_permitidos_apenas_escaladas(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model, tipos_permitidos={"Escalada"})

    # Apenas as 3 escaladas válidas devem estar na lista
    assert len(widget.todas_entidades) == 3
    assert all(e["tipo"] == "Escalada" for e in widget.todas_entidades)
    assert widget.lista_resultados.count() == 3

    nomes = [e["escalada"] for e in widget.todas_entidades]
    assert "Bacon com Linguiça" in nomes
    assert "Vía Láctea" in nomes
    assert "Fissura das Sombras" in nomes


def test_filtro_por_tipos_permitidos_grupos_e_setores(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model, tipos_permitidos={"Grupo", "Setor"})

    assert len(widget.todas_entidades) == 3
    tipos = [e["tipo"] for e in widget.todas_entidades]
    assert tipos.count("Grupo") == 1
    assert tipos.count("Setor") == 2


def test_inicializacao_com_setor_avulso_sem_model(qapp):
    _, setor1, _ = _criar_croqui_teste()
    widget = WidgetBuscaEntidades(setor=setor1, tipos_permitidos={"Escalada"})

    # Deve listar as escaladas do setor1
    assert len(widget.todas_entidades) == 2
    nomes = [e["escalada"] for e in widget.todas_entidades]
    assert "Bacon com Linguiça" in nomes
    assert "Vía Láctea" in nomes


def test_mapa_filtro_marca_escaladas_ja_mapeadas_como_greyed_out(qapp):
    croqui, setor1, _ = _criar_croqui_teste()
    mapa = setor1.mapas.add()
    mapa.referencias.add(escalada="Bacon com Linguiça", ids=["linha_1"])

    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(
        model=model,
        mapa_filtro=mapa,
        tipos_permitidos={"Escalada"}
    )

    # "Bacon com Linguiça" NÃO deve ser omitida; deve estar presente com ja_mapeada=True
    nomes = [e["escalada"] for e in widget.todas_entidades]
    assert "Bacon com Linguiça" in nomes
    assert "Vía Láctea" in nomes

    entidade_mapeada = next(e for e in widget.todas_entidades if e["escalada"] == "Bacon com Linguiça")
    assert entidade_mapeada["ja_mapeada"] is True

    entidade_livre = next(e for e in widget.todas_entidades if e["escalada"] == "Vía Láctea")
    assert entidade_livre["ja_mapeada"] is False

    # Na lista de resultados:
    item_mapeado = None
    for i in range(widget.lista_resultados.count()):
        it = widget.lista_resultados.item(i)
        if "Bacon com Linguiça" in it.text():
            item_mapeado = it
            break

    assert item_mapeado is not None
    assert "[já no mapa]" in item_mapeado.text()
    assert "Esta escalada já possui traçado neste mapa" in item_mapeado.toolTip()
    assert item_mapeado.foreground().color().name().lower() == "#888888"



def test_busca_insensivel_a_acentos_e_caixa(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model, tipos_permitidos={"Escalada"})

    # Buscar "via lactea" (sem acento, minúsculo) deve encontrar "Vía Láctea"
    widget.definir_filtro("via lactea")
    assert widget.lista_resultados.count() == 1
    item = widget.lista_resultados.item(0)
    assert "Vía Láctea" in item.text()
    assert widget.lista_resultados.currentRow() == 0

    # Buscar "linguica" (sem cedilha) deve encontrar "Bacon com Linguiça"
    widget.definir_filtro("linguica")
    assert widget.lista_resultados.count() == 1
    assert "Bacon com Linguiça" in widget.lista_resultados.item(0).text()


def test_permitir_criacao_nova_adiciona_item_especial(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(
        model=model,
        tipos_permitidos={"Escalada"},
        permitir_criacao_nova=True
    )

    # Sem texto de busca: nenhum item especial
    assert not any("Criar Nova" in widget.lista_resultados.item(i).text() for i in range(widget.lista_resultados.count()))

    # Com texto de busca: o último item deve ser o especial de criação
    widget.definir_filtro("Novo Projeto")
    total = widget.lista_resultados.count()
    assert total >= 1
    ultimo_item = widget.lista_resultados.item(total - 1)
    assert "Criar Nova Escalada" in ultimo_item.text()
    assert "Novo Projeto" in ultimo_item.text()

    # Seleciona o item de criação
    widget.lista_resultados.setCurrentRow(total - 1)
    dados = widget.obter_entidade_selecionada()
    assert dados is not None
    assert dados["nova"] is True
    assert dados["nome"] == "Novo Projeto"


def test_emissao_de_sinais_selecionada_e_ativada(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model)

    selecionada = None
    def ao_selecionar(dados):
        nonlocal selecionada
        selecionada = dados

    ativada = None
    def ao_ativar(dados):
        nonlocal ativada
        ativada = dados

    widget.entidade_selecionada.connect(ao_selecionar)
    widget.entidade_ativada.connect(ao_ativar)

    # Mudar seleção
    widget.lista_resultados.setCurrentRow(1)
    assert selecionada is not None
    assert selecionada["tipo"] == "Setor"

    # Duplo clique
    item = widget.lista_resultados.item(1)
    widget._ao_item_duplo_clicado(item)
    assert ativada is not None
    assert ativada["tipo"] == "Setor"


def test_recarregar_entidades_atualiza_lista(qapp):
    croqui, setor1, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model, tipos_permitidos={"Escalada"})
    assert widget.lista_resultados.count() == 3

    # Adiciona mais uma via ao modelo
    nova = setor1.escaladas.add()
    nova.via_esportiva.nome = "Nova Via Recarregada"

    widget.recarregar_entidades()
    assert widget.lista_resultados.count() == 4
    nomes = [e["escalada"] for e in widget.todas_entidades]
    assert "Nova Via Recarregada" in nomes


def test_obter_entidade_selecionada_vazia_quando_sem_selecao(qapp):
    croqui, _, _ = _criar_croqui_teste()
    model = CroquiModel(croqui)
    widget = WidgetBuscaEntidades(model=model)

    widget.lista_resultados.clearSelection()
    widget.lista_resultados.setCurrentRow(-1)
    assert widget.obter_entidade_selecionada() is None


def test_modelo_vazio_ou_sem_picos(qapp):
    croqui_vazio = croqui_pb2.Croqui()
    model = CroquiModel(croqui_vazio)
    widget = WidgetBuscaEntidades(model=model)
    assert len(widget.todas_entidades) == 0
    assert widget.lista_resultados.count() == 0
    assert widget.obter_entidade_selecionada() is None


def test_inicializacao_com_croqui_direto(qapp):
    croqui, _, _ = _criar_croqui_teste()
    widget = WidgetBuscaEntidades(croqui=croqui, tipos_permitidos={"Escalada"})
    assert widget.lista_resultados.count() == 3


def test_setor_avulso_com_escalada_vazia_e_mapeada_e_sem_caminho(qapp):
    setor = croqui_pb2.Setor(nome="")
    # Escalada 1: normal
    e1 = setor.escaladas.add()
    e1.boulder.nome = "Bloco 1"

    # Escalada 2: vazia sem tipo
    setor.escaladas.add()

    # Escalada 3: mapeada
    e3 = setor.escaladas.add()
    e3.boulder.nome = "Bloco Mapeado"
    mapa = setor.mapas.add()
    mapa.referencias.add(escalada="Bloco Mapeado")

    widget = WidgetBuscaEntidades(setor=setor, mapa_filtro=mapa, tipos_permitidos={"Escalada"})
    assert widget.lista_resultados.count() == 2
    # Como setor.nome="", caminho_hierarquia é vazio e rotulo cobre linha 121
    assert "🧗 Boulder: Bloco 1" in widget.lista_resultados.item(0).text()
    assert "[já no mapa]" in widget.lista_resultados.item(1).text()


def test_dificuldade_com_atributo_name(qapp):
    class DificuldadeFake:
        name = "V10"

    class ConteudoFake:
        nome = "Fake Route"
        dificuldade = DificuldadeFake()

    class EscaladaFake:
        def WhichOneof(self, campo):
            return "boulder"
        boulder = ConteudoFake()

    widget = WidgetBuscaEntidades()
    nome, tipo, grau = widget._obter_info_escalada(EscaladaFake())
    assert nome == "Fake Route"
    assert tipo == "boulder"
    assert grau == "V10"

