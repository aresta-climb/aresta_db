# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QEnterEvent

from editor.core.topologia_trajeto import OpcaoCaminhoConfluencia, Ponto2D
from editor.views.componentes.popover_confluencia_rota import PopoverConfluenciaRota


def _criar_opcoes_exemplo() -> list[OpcaoCaminhoConfluencia]:
    return [
        OpcaoCaminhoConfluencia(
            rotulo_exibicao='Seguir até Topo A via "Via 1"',
            nomes_escaladas=("Via 1",),
            rotulo_topo="A",
            coordenadas_remanescentes=(Ponto2D(100.0, 300.0), Ponto2D(80.0, 100.0)),
            id_linha_alvo="l1",
            requer_fatiamento=True,
            incluir_segunda_sublinha_fatiada=True,
            uids_subsequentes=("s_esq",),
        ),
        OpcaoCaminhoConfluencia(
            rotulo_exibicao='Seguir até Topo B via "Via 2"',
            nomes_escaladas=("Via 2",),
            rotulo_topo="B",
            coordenadas_remanescentes=(Ponto2D(100.0, 300.0), Ponto2D(140.0, 100.0)),
            id_linha_alvo="l1",
            requer_fatiamento=True,
            incluir_segunda_sublinha_fatiada=True,
            uids_subsequentes=("s_dir",),
        ),
    ]


def test_popover_pre_seleciona_primeira_opcao_e_emite_foco_ao_exibir(qtbot):
    """[TDD] Ao exibir o popover, a 1ª opção deve vir pré-selecionada e emitir opcao_focada."""
    opcoes = _criar_opcoes_exemplo()
    popover = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover)

    focos_recebidos = []
    popover.opcao_focada.connect(lambda op: focos_recebidos.append(op))

    popover.exibir_em(QPoint(200, 200))

    assert popover.indice_selecionado == 0
    assert len(popover.botoes_opcoes) == 3
    assert '[1] Seguir até Topo A via "Via 1"' in popover.botoes_opcoes[0].text()
    assert '[2] Seguir até Topo B via "Via 2"' in popover.botoes_opcoes[1].text()
    assert "Apenas adicionar ponto e continuar desenhando" in popover.botoes_opcoes[2].text()
    assert focos_recebidos == [opcoes[0]]
    popover.close()


def test_popover_navegacao_setas_atualiza_foco_e_ghost_preview(qtbot):
    """[TDD] Setas Cima/Baixo alternam o foco entre opções de confluência e 'Apenas adicionar ponto'."""
    opcoes = _criar_opcoes_exemplo()
    popover = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover)

    focos_recebidos = []
    popover.opcao_focada.connect(lambda op: focos_recebidos.append(op))
    popover.exibir_em(QPoint(200, 200))
    focos_recebidos.clear()

    # Seta para baixo -> opção 1 (Topo B)
    qtbot.keyClick(popover, Qt.Key.Key_Down)
    assert popover.indice_selecionado == 1
    assert focos_recebidos[-1] == opcoes[1]

    # Seta para baixo -> opção 2 ("Apenas adicionar ponto...", foco None limpa Ghost Preview)
    qtbot.keyClick(popover, Qt.Key.Key_Down)
    assert popover.indice_selecionado == 2
    assert focos_recebidos[-1] is None

    # Seta para baixo no último item -> faz wrap para o índice 0
    qtbot.keyClick(popover, Qt.Key.Key_Down)
    assert popover.indice_selecionado == 0
    assert focos_recebidos[-1] == opcoes[0]

    # Seta para cima no índice 0 -> faz wrap para o índice 2 (None)
    qtbot.keyClick(popover, Qt.Key.Key_Up)
    assert popover.indice_selecionado == 2
    assert focos_recebidos[-1] is None
    popover.close()


def test_popover_hover_mouse_atualiza_foco(qtbot):
    """[TDD] Passar o mouse sobre cada botão do popover atualiza a seleção e emite opcao_focada."""
    opcoes = _criar_opcoes_exemplo()
    popover = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover)

    focos_recebidos = []
    popover.opcao_focada.connect(lambda op: focos_recebidos.append(op))
    popover.exibir_em(QPoint(200, 200))
    focos_recebidos.clear()

    evento_enter = QEnterEvent(QPointF(5.0, 5.0), QPointF(5.0, 5.0), QPointF(205.0, 205.0))
    popover.eventFilter(popover.botoes_opcoes[1], evento_enter)
    assert popover.indice_selecionado == 1
    assert focos_recebidos[-1] == opcoes[1]

    # Hover no mesmo índice já selecionado não reemite sinal redundante
    contagem_antes = len(focos_recebidos)
    popover.eventFilter(popover.botoes_opcoes[1], evento_enter)
    assert len(focos_recebidos) == contagem_antes

    # Hover no último botão emite None
    popover.eventFilter(popover.botoes_opcoes[2], evento_enter)
    assert popover.indice_selecionado == 2
    assert focos_recebidos[-1] is None

    # Evento irrelevante no eventFilter retorna False sem alterar estado
    evento_outro = QEvent(QEvent.Type.FocusIn)
    assert popover.eventFilter(popover.botoes_opcoes[0], evento_outro) is False
    popover.close()


def test_popover_confirmacao_com_enter(qtbot):
    """[TDD] Pressionar Enter confirma a opção selecionada (confluência ou apenas adicionar ponto)."""
    opcoes = _criar_opcoes_exemplo()

    # Caso 1: Enter na 1ª opção pré-selecionada
    popover1 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover1)
    confirmadas = []
    cancelamentos = []
    popover1.opcao_confirmada.connect(lambda op: confirmadas.append(op))
    popover1.cancelado.connect(lambda: cancelamentos.append(True))
    popover1.exibir_em(QPoint(100, 100))

    qtbot.keyClick(popover1, Qt.Key.Key_Return)
    assert confirmadas == [opcoes[0]]
    assert cancelamentos == []

    # Caso 2: Enter na opção "Apenas adicionar ponto e continuar desenhando"
    popover2 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover2)
    apenas_ponto = []
    popover2.apenas_adicionar_ponto.connect(lambda: apenas_ponto.append(True))
    popover2.cancelado.connect(lambda: cancelamentos.append(True))
    popover2.exibir_em(QPoint(100, 100))

    qtbot.keyClick(popover2, Qt.Key.Key_Up)  # Vai para a última opção
    qtbot.keyClick(popover2, Qt.Key.Key_Enter)
    assert apenas_ponto == [True]
    assert cancelamentos == []


def test_popover_atalhos_numericos_e_clique_direto(qtbot):
    """[TDD] Teclas numéricas 1..N e cliques de mouse acionam a opção correspondente."""
    opcoes = _criar_opcoes_exemplo()

    # Tecla '2' confirma a segunda opção de confluência
    popover1 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover1)
    confirmadas = []
    popover1.opcao_confirmada.connect(lambda op: confirmadas.append(op))
    popover1.exibir_em(QPoint(100, 100))

    # Tecla fora da faixa ('9' ou letra) é ignorada
    qtbot.keyClick(popover1, Qt.Key.Key_9)
    qtbot.keyClick(popover1, Qt.Key.Key_A)
    assert confirmadas == []

    qtbot.keyClick(popover1, Qt.Key.Key_2)
    assert confirmadas == [opcoes[1]]

    # Tecla '3' (N+1) ou '0' aciona "Apenas adicionar ponto"
    popover2 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover2)
    apenas_ponto = []
    popover2.apenas_adicionar_ponto.connect(lambda: apenas_ponto.append(True))
    popover2.exibir_em(QPoint(100, 100))
    qtbot.keyClick(popover2, Qt.Key.Key_3)
    assert apenas_ponto == [True]

    # Clique direto no botão da 1ª opção
    popover3 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover3)
    confirmadas_clique = []
    popover3.opcao_confirmada.connect(lambda op: confirmadas_clique.append(op))
    popover3.exibir_em(QPoint(100, 100))
    qtbot.mouseClick(popover3.botoes_opcoes[0], Qt.MouseButton.LeftButton)
    assert confirmadas_clique == [opcoes[0]]


def test_popover_cancelamento_com_esc_e_fechamento_externo(qtbot):
    """[TDD] Pressionar Esc ou fechar o popup sem confirmar emite cancelado uma única vez."""
    opcoes = _criar_opcoes_exemplo()

    # Cancelamento via tecla Esc
    popover1 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover1)
    cancelamentos1 = []
    popover1.cancelado.connect(lambda: cancelamentos1.append(True))
    popover1.exibir_em(QPoint(100, 100))

    qtbot.keyClick(popover1, Qt.Key.Key_Escape)
    assert len(cancelamentos1) == 1

    # Fechamento externo do popup (ex: clique fora do popup)
    popover2 = PopoverConfluenciaRota(opcoes)
    qtbot.addWidget(popover2)
    cancelamentos2 = []
    popover2.cancelado.connect(lambda: cancelamentos2.append(True))
    popover2.exibir_em(QPoint(100, 100))

    popover2.close()
    assert len(cancelamentos2) == 1
