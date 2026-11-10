# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import Qt
from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.widget_painel_qualidade import WidgetPainelQualidade


def _criar_croqui_etapa1_completa() -> croqui_pb2.Croqui:
    """Cria um croqui Protobuf que cumpre todas as 7 tarefas da Etapa 1 com setor único."""
    croqui = croqui_pb2.Croqui(
        id="br_mg_painel_teste",
        uid="uid_croqui_0001",
        nome="Serra da Qualidade",
        descricao="Croqui completo de teste para validação da nota de qualidade.",
        caminho_thumbnail="imagens/thumbnail.webp",
    )
    pico = croqui.picos.add(
        nome="Pico Principal",
        descricao="Acesso pela rodovia MG-010, estacionamento ao lado da portaria.",
        url_google_maps="https://maps.google.com/?q=-19.5,-43.5",
    )
    pico.localizacao.latitude = -195000000
    pico.localizacao.longitude = -435000000
    pico.malha_estrada.conteudo.latitude_referencia_e7 = -195000000
    pico.malha_estrada.conteudo.longitude_referencia_e7 = -435000000
    no_malha = pico.malha_estrada.conteudo.nos.add()
    no_malha.no_osm_id = 1001
    no_malha.latitude_e7 = -195000000
    no_malha.longitude_e7 = -435000000
    no_malha.distancia_metros = 0
    no_malha.duracao_minutos = 0

    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "uid_setor_00001"
    setor.nome = "Setor Principal"

    mapa = setor.mapas.add(
        caminho_imagem_mapa="imagens/mapa_setor.webp",
        largura_mapa=1000,
        altura_mapa=800,
    )
    ponto = mapa.pontos_de_interesse.add(uid="uid_ponto_00001", rotulo="1")
    ponto.circulo.x = 100
    ponto.circulo.y = 200
    ponto.circulo.raio = 20

    esc = setor.escaladas.add(uid="uid_esc_0000001")
    esc.via_esportiva.nome = "Via Clássica"
    esc.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP

    ref = mapa.referencias.add(alvo_uid="uid_esc_0000001")
    ref.pontos_uids.append("uid_ponto_00001")

    return croqui


def test_painel_exibe_nota_cascata_etapa1_e_bloqueia_publicacao_em_rascunho_incompleto(
    qtbot,
) -> None:
    """
    Dado um croqui em rascunho com a Etapa 1 incompleta,
    quando o WidgetPainelQualidade é instanciado,
    então exibe a nota parcial, abre a Etapa 1, recolhe as Etapas 2 e 3 e desabilita o botão de publicar.
    """
    croqui = croqui_pb2.Croqui()
    croqui.id = "br_mg_incompleto"
    croqui.nome = "Pedra Incompleta"
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    painel = WidgetPainelQualidade(model, controller)
    qtbot.addWidget(painel)
    painel.show()

    assert "333" in painel.label_nota_qualidade.text()
    assert "Rascunho" in painel.label_status_publicacao.text()
    assert not painel.label_aviso_legado.isVisible()
    assert not painel.botao_publicar.isEnabled()

    assert painel.secoes_etapas[1].esta_expandida() is True
    assert painel.secoes_etapas[2].esta_expandida() is False
    assert painel.secoes_etapas[3].esta_expandida() is False

    # Alternância manual de expando funciona e é preservada enquanto a etapa não muda de conclusão
    qtbot.mouseClick(painel.secoes_etapas[2].botao_cabecalho, Qt.MouseButton.LeftButton)
    assert painel.secoes_etapas[2].esta_expandida() is True
    controller.alterar_primitivo(
        model.obter_croqui_readonly(),
        "caminho_thumbnail",
        "",
        "imagens/capa.webp",
    )
    assert "667" in painel.label_nota_qualidade.text()
    assert painel.secoes_etapas[2].esta_expandida() is True


def test_cascata_automatica_etapas_1_2_3_e_publicacao_via_undo_redo(qtbot) -> None:
    """
    Dado um croqui que conclui a Etapa 1 e depois a Etapa 2,
    quando avaliado pelo WidgetPainelQualidade,
    então recolhe a Etapa 1 abrindo a Etapa 2, depois recolhe a Etapa 2 abrindo a Etapa 3,
    e permite publicar/despublicar o croqui via pilha de Undo/Redo.
    """
    croqui = _criar_croqui_etapa1_completa()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    painel = WidgetPainelQualidade(model, controller)
    qtbot.addWidget(painel)
    painel.show()

    # Etapa 1 completa (7000 pts) -> Etapa 1 fechada, Etapa 2 aberta, Etapa 3 fechada
    assert painel.secoes_etapas[1].esta_expandida() is False
    assert painel.secoes_etapas[2].esta_expandida() is True
    assert painel.secoes_etapas[3].esta_expandida() is False
    assert painel.botao_publicar.isEnabled() is True

    # Clicar em publicar altera publicar_croqui via QUndoStack e suporta undo/redo
    qtbot.mouseClick(painel.botao_publicar, Qt.MouseButton.LeftButton)
    assert model.obter_croqui_readonly().publicar_croqui is True
    assert "Publicado" in painel.label_status_publicacao.text()

    stack.undo()
    assert model.obter_croqui_readonly().publicar_croqui is False
    assert "Rascunho" in painel.label_status_publicacao.text()

    stack.redo()
    assert model.obter_croqui_readonly().publicar_croqui is True

    # Agora completa a Etapa 2 no modelo e verifica transição da cascata para a Etapa 3
    croqui.status_desenho_extraivel = croqui_pb2.Croqui.StatusDesenhoExtraivel.DESENHO_EXTRAIDO
    pico = croqui.picos[0]
    setor = pico.setores_ou_grupos[0].setor.conteudo
    setor.caminho_imagem_capa = "imagens/capa.webp"
    setor.localizacao_estacionamento.latitude = -195000000
    setor.localizacao_estacionamento.longitude = -435000000
    setor.localizacao_escalada.latitude = -195001000
    setor.localizacao_escalada.longitude = -435001000
    setor.sinal_de_celular = True
    setor.amigavel_a_criancas = True
    setor.amigavel_a_bebes = False
    trilha = setor.trilhas.add(
        nome="Trilha Principal",
        descricao="Caminhada leve por 5 minutos.",
        tempo_aproximacao="5 min",
    )
    pt_trilha = trilha.pontos.add(nome="Início")
    pt_trilha.localizacao.latitude = -195000000
    pt_trilha.localizacao.longitude = -435000000

    ponto_mapa = setor.mapas[0].pontos_de_interesse[0]
    ponto_mapa.ClearField("circulo")
    no1 = ponto_mapa.linha.conteudo.nos.add(
        x=100, y=500, tipo=croqui_pb2.NoTrajeto.CIRCULO_IDENTIFICADOR
    )
    no1.rotulo = "1"
    ponto_mapa.linha.conteudo.nos.add(x=100, y=100, tipo=croqui_pb2.NoTrajeto.TOP_PARADA)

    via = setor.escaladas[0].via_esportiva
    via.destaque = True
    via.extensao = 22
    via.quantidade_protecoes_intermediarias = 9
    via.quantidade_protecoes_parada = 2
    via.descricao = "Saída atlética em agarras boas seguida de crux técnico."
    beta = setor.escaladas[0].betas.add()
    beta.fonte = beta_pb2.FonteMidia.YOUTUBE
    beta.url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    # Notifica mudança no modelo
    model.dado_alterado.emit(croqui, "descricao")

    assert painel.secoes_etapas[1].esta_expandida() is False
    assert painel.secoes_etapas[2].esta_expandida() is False
    assert painel.secoes_etapas[3].esta_expandida() is True


def test_clique_acao_rapida_emite_foco_requisitado_e_aviso_croqui_legado_publicado(
    qtbot,
) -> None:
    """
    Dado um croqui legado já publicado mas com pendências na Etapa 1,
    quando exibido no WidgetPainelQualidade e clicado um botão de ação rápida,
    então exibe o aviso de pendências (sem despublicar) e emite foco_requisitado com a URI ContextoUIPath.
    """
    croqui = croqui_pb2.Croqui()
    croqui.id = "br_rj_legado"
    croqui.publicar_croqui = True

    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    painel = WidgetPainelQualidade()
    qtbot.addWidget(painel)
    painel.atualizar_painel()
    painel.set_model_e_controller(model, controller)
    painel.show()

    # Croqui legado publicado com Etapa 1 incompleta mostra aviso e mantém botão habilitado para voltar a rascunho
    assert painel.label_aviso_legado.isVisible() is True
    assert painel.botao_publicar.isEnabled() is True
    assert painel.secoes_etapas[1].esta_expandida() is True

    uris_recebidas: list[str] = []
    model.foco_requisitado.connect(lambda uri: uris_recebidas.append(str(uri)))

    card_identidade = painel.cards_tarefas["etapa1_identidade_capa"]
    assert [b.text() for b in card_identidade.botoes_acao] == [
        "Definir nome do croqui",
        "Adicionar descrição do croqui",
        "Adicionar imagem de capa",
    ]
    qtbot.mouseClick(card_identidade.botoes_acao[0], Qt.MouseButton.LeftButton)

    assert len(uris_recebidas) == 1
    assert uris_recebidas[0] == "page:dados/node:root/node:Croqui/campo:nome"


def test_painel_qualidade_coalesce_atualizacoes_durante_lote_curadoria_betas(qtbot) -> None:
    """
    Dado o WidgetPainelQualidade conectado ao modelo e controlador,
    quando dezenas de candidatos e rejeitados são inseridos em lote via macro de Undo/Redo,
    então o painel recalcula a nota de qualidade apenas 1 única vez ao final do lote.
    """
    croqui = _criar_croqui_etapa1_completa()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    painel = WidgetPainelQualidade(model, controller)
    qtbot.addWidget(painel)
    ct_inicial = painel.total_atualizacoes_painel

    rejeitados = [
        beta_pb2.MidiaBeta(
            url=f"https://example.com/rej/{i}",
            titulo=f"[Query: geral | Auto-filtrado: sem menção à via] Post {i}",
            fonte=beta_pb2.FonteMidia.BLOG,
        )
        for i in range(40)
    ]
    controller.adicionar_betas_rejeitados_lote("uid_esc_0000001", rejeitados)

    assert painel.total_atualizacoes_painel == ct_inicial + 1
