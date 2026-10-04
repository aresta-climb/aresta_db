# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from editor.views.widget_painel_referencias import PainelReferencias
from aresta_api.proto.generated import croqui_pb2

def test_painel_referencias_sem_controller(qapp):
    """[TDD] Verifica se o PainelReferencias não falha ao ser utilizado sem um MapasController (modo standalone)."""
    painel = PainelReferencias(None)
    
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.grupo = "Grupo Teste"
    
    painel.carregar_mapa(mapa)
    
    # Simula clicar em adicionar (não deve falhar, simplesmente ignora)
    try:
        painel._ao_clicar_adicionar()
    except Exception as e:
        pytest.fail(f"_ao_clicar_adicionar() disparou exceção com controller None: {e}")
        
    # Simula clicar em remover (não deve falhar, simplesmente ignora)
    try:
        painel._confirmar_remover(0)
    except Exception as e:
        pytest.fail(f"_confirmar_remover() disparou exceção com controller None: {e}")
        
    assert painel.layout_cards.count() == 1

def test_emit_iniciar_modo_linkagem_com_readonly_proxy(qapp):
    """[TDD] Verifica se o PyQt não dá TypeError ao emitir a referência empacotada no ReadOnlyProxy."""
    painel = PainelReferencias(None)
    
    from editor.models.readonly_proxy import ReadOnlyProxy
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.grupo = "Grupo Teste"
    
    proxy_mapa = ReadOnlyProxy(mapa)
    painel.carregar_mapa(proxy_mapa)
    
    sinais = []
    painel.iniciar_modo_linkagem.connect(lambda idx, r: sinais.append((idx, r)))
    
    card = painel.layout_cards.itemAt(0).widget()
    card.btn_linkar.setChecked(True)
    
    assert len(sinais) == 1
    assert sinais[0][0] == 0
    assert sinais[0][1].grupo == "Grupo Teste"

def test_card_texto_dinamico_e_botao_remover(qapp):
    """[TDD] Verifica se botões de câmera mudam de estado se existe ajuste de câmera."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    painel = PainelReferencias(None)
    
    mapa = croqui_pb2.Mapa()
    ref1 = mapa.referencias.add() # Sem câmera
    ref2 = mapa.referencias.add() # Com câmera
    ref2.ajuste_de_camera.zoom = 2.0
    
    painel.carregar_mapa(ReadOnlyProxy(mapa))
    
    card1 = painel.layout_cards.itemAt(0).widget()
    card2 = painel.layout_cards.itemAt(1).widget()
    
    # Card 1: Sem câmera
    assert "Adicionar" in card1.btn_camera.text()
    assert getattr(card1, 'btn_remover_camera', None) is None or card1.btn_remover_camera.isHidden()
    
    # Card 2: Com câmera
    assert "Modificar" in card2.btn_camera.text()
    assert getattr(card2, 'btn_remover_camera', None) is not None
    assert not card2.btn_remover_camera.isHidden()

def test_hover_in_envia_referencia(qapp):
    """[TDD] Verifica se hover_in emite a referência inteira, não só os IDs."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.grupo = "Hover Test"
    
    painel.carregar_mapa(ReadOnlyProxy(mapa))
    card = painel.layout_cards.itemAt(0).widget()
    
    sinais = []
    painel.destacar_pois.connect(lambda r: sinais.append(r))
    
    card.enterEvent(None)
    
    assert len(sinais) == 1
    # O sinal recebido deve ser o proxy da referência, que tem .grupo
    assert sinais[0].grupo == "Hover Test"

def test_botoes_layout(qapp):
    """[TDD] Verifica se o botão de remover referência tem o texto correto."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    
    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    mapa.referencias.add()
    
    painel.carregar_mapa(ReadOnlyProxy(mapa))
    card = painel.layout_cards.itemAt(0).widget()
    
    assert card.btn_remover.toolTip().strip() == "Excluir Referência"
    assert card.btn_remover.text().strip() == ""

def test_btn_remover_click(qapp):
    """[TDD] Verifica se o clique na lixeira chama _confirmar_remover."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock
    
    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    mapa.referencias.add()
    
    painel.carregar_mapa(ReadOnlyProxy(mapa))
    card = painel.layout_cards.itemAt(0).widget()
    
    painel._confirmar_remover = MagicMock()
    card.btn_remover.clicked.emit()
    painel._confirmar_remover.assert_called_once_with(0)

def test_excluir_referencia_limpa_modos_ativos(qapp):
    """[TDD] Verifica se ao excluir uma referência, os modos câmera e linkagem são cancelados para evitar crashes."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from unittest.mock import MagicMock
    painel = PainelReferencias(None)
    painel._limpar_modos_ativos = MagicMock()
    painel._confirmar_remover(0)
    painel._limpar_modos_ativos.assert_called_once()

def test_card_referencia_nao_tem_texto_referencia_x_e_tem_botao_lapis(qapp):
    """[TDD] Verifica se o card não exibe Referência X e se tem o botão de lápis para editar o alvo."""
    from editor.views.widget_painel_referencias import CardReferencia
    from aresta_api.proto.generated import croqui_pb2
    ref = croqui_pb2.Mapa.Referencia()
    ref.grupo = "meu_mapa"
    card = CardReferencia(ref, 0)
    
    # Não deve ter 'Referência' no label, só o nome do alvo (ou grupo se houver, mas grupo aqui é vazio)
    # Na verdade, a UI vai ter apenas <b>meu_mapa</b> e o botão.
    assert "Referência" not in card.label_titulo.text()
    assert getattr(card, 'btn_editar_alvo', None) is not None
    assert card.btn_editar_alvo.toolTip() == "Editar Referência"

def test_adicionar_referencia_recusa_duplicada(qapp):
    """[TDD] Verifica se adicionar referência recusa caso o alvo já exista."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock, patch
    
    mapa = croqui_pb2.Mapa()
    ref_existente = mapa.referencias.add()
    ref_existente.grupo = "meu_alvo"
    
    controller = MagicMock()
    painel = PainelReferencias(controller)
    painel.carregar_mapa(ReadOnlyProxy(mapa))
    
    # Mock do dialogo para retornar o mesmo alvo
    ref_nova = croqui_pb2.Mapa.Referencia()
    ref_nova.grupo = "meu_alvo"
    
    with patch('editor.views.widget_painel_referencias.DialogoBuscaReferencia') as MockDialogo, \
         patch('PySide6.QtWidgets.QMessageBox.warning') as MockWarning:
        mock_dlg_instance = MockDialogo.return_value
        mock_dlg_instance.exec.return_value = True
        mock_dlg_instance.obter_referencia.return_value = ref_nova
        
        painel._ao_clicar_adicionar()
        
        MockWarning.assert_called_once()
        controller.adicionar_referencia.assert_not_called()

def test_editar_referencia_altera_alvo_e_recusa_duplicada(qapp):
    """[TDD] Verifica se editar a referência atualiza o alvo e recusa se houver duplicata."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    from aresta_api.proto.generated import croqui_pb2
    from unittest.mock import MagicMock, patch
    
    mapa = croqui_pb2.Mapa()
    ref1 = mapa.referencias.add()
    ref1.grupo = "alvo1"
    ref2 = mapa.referencias.add()
    ref2.grupo = "alvo2"
    
    controller = MagicMock()
    painel = PainelReferencias(controller)
    proxy = ReadOnlyProxy(mapa)
    painel.carregar_mapa(proxy)
    
    # 1. Tentar editar alvo1 para alvo2 (duplicada)
    ref_tentativa = croqui_pb2.Mapa.Referencia()
    ref_tentativa.grupo = "alvo2"
    
    with patch('editor.views.widget_painel_referencias.DialogoBuscaReferencia') as MockDialogo, \
         patch('PySide6.QtWidgets.QMessageBox.warning') as MockWarning:
        mock_dlg_instance = MockDialogo.return_value
        mock_dlg_instance.exec.return_value = True
        mock_dlg_instance.obter_referencia.return_value = ref_tentativa
        
        painel._ao_clicar_editar_alvo(0, proxy.referencias[0])
        
        MockWarning.assert_called_once()
        controller.alterar_referencia.assert_not_called()
        
    # 2. Tentar editar alvo1 para alvo3 (sucesso)
    ref_tentativa.grupo = "alvo3"
    with patch('editor.views.widget_painel_referencias.DialogoBuscaReferencia') as MockDialogo, \
         patch('PySide6.QtWidgets.QMessageBox.warning') as MockWarning:
        mock_dlg_instance = MockDialogo.return_value
        mock_dlg_instance.exec.return_value = True
        mock_dlg_instance.obter_referencia.return_value = ref_tentativa
        
        painel._ao_clicar_editar_alvo(0, proxy.referencias[0])
        
        MockWarning.assert_not_called()
        controller.alterar_referencia.assert_called_once()
        ref_antiga_passada = controller.alterar_referencia.call_args[0][2]
        ref_nova_passada = controller.alterar_referencia.call_args[0][3]
        
        assert ref_antiga_passada.grupo == "alvo1"
        assert ref_nova_passada.grupo == "alvo3"


def test_card_referencia_exibe_preview_codenome_valido(qapp):
    """[TDD] Verifica se o CardReferencia exibe badge com o codenome (ex: 5-C) quando há nós identificadores."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy

    mapa = croqui_pb2.Mapa()
    p1 = mapa.pontos_de_interesse.add()
    p1.id = "linha_1"
    m1 = p1.linha.compilado.marcadores.add()
    m1.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    m1.rotulo = "5"

    p2 = mapa.pontos_de_interesse.add()
    p2.id = "linha_2"
    m2 = p2.linha.compilado.marcadores.add()
    m2.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    m2.rotulo = "C"

    ref = mapa.referencias.add()
    ref.escalada = "Via Teste"
    ref.ids.extend(["linha_1", "linha_2"])

    painel = PainelReferencias(None)
    painel.carregar_mapa(ReadOnlyProxy(mapa))

    card = painel.layout_cards.itemAt(0).widget()
    assert hasattr(card, "lbl_preview")
    assert "5-C" in card.lbl_preview.text()


def test_card_referencia_exibe_aviso_sem_rotulo(qapp):
    """[TDD] Verifica se o CardReferencia exibe indicativo de aviso quando a referência não possui identificador."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy

    mapa = croqui_pb2.Mapa()
    p = mapa.pontos_de_interesse.add()
    p.id = "linha_sem_no"
    n = p.linha.conteudo.nos.add()
    n.tipo = croqui_pb2.NoTrajeto.TipoNo.PASSAGEM

    ref = mapa.referencias.add()
    ref.escalada = "Via Sem Rotulo"
    ref.ids.append("linha_sem_no")

    painel = PainelReferencias(None)
    painel.carregar_mapa(ReadOnlyProxy(mapa))

    card = painel.layout_cards.itemAt(0).widget()
    assert hasattr(card, "lbl_preview")
    assert "Sem rótulo" in card.lbl_preview.text()


def test_card_referencia_botao_inverter_chama_alterar_referencia(qapp):
    """[TDD] Verifica se o clique em Inverter Ordem chama alterar_referencia com os IDs invertidos."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from editor.models.readonly_proxy import ReadOnlyProxy
    from unittest.mock import MagicMock

    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.escalada = "Via Teste"
    ref.ids.extend(["linha_21", "linha_18", "linha_9", "linha_16", "linha_12"])

    controller = MagicMock()
    painel = PainelReferencias(controller)
    proxy = ReadOnlyProxy(mapa)
    painel.carregar_mapa(proxy)

    card = painel.layout_cards.itemAt(0).widget()
    assert hasattr(card, "btn_inverter")

    card.btn_inverter.click()

    controller.alterar_referencia.assert_called_once()
    args = controller.alterar_referencia.call_args[0]
    msg_mapa, idx, ref_antiga, ref_nova = args
    assert idx == 0
    assert list(ref_nova.ids) == ["linha_12", "linha_16", "linha_9", "linha_18", "linha_21"]


def test_inversao_ids_reversibilidade_undo_redo(qapp):
    """[TDD] Verifica a reversibilidade total (Undo/Redo) da inversão de IDs com MapasController real."""
    from PySide6.QtGui import QUndoStack
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.mapas_controller import MapasController
    from editor.views.widget_painel_referencias import PainelReferencias

    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    mapa = sg.setor.conteudo.mapas.add()

    p1 = mapa.pontos_de_interesse.add()
    p1.id = "seg_a"
    m1 = p1.linha.compilado.marcadores.add()
    m1.tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    m1.rotulo = "1"

    p2 = mapa.pontos_de_interesse.add()
    p2.id = "seg_b"
    m2 = p2.linha.compilado.marcadores.add()
    m2.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    m2.rotulo = "TOP"

    ref = mapa.referencias.add()
    ref.escalada = "Via Reversivel"
    ref.ids.extend(["seg_a", "seg_b"])

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = MapasController(model, undo_stack)
    painel = PainelReferencias(controller)

    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    painel.carregar_mapa(proxy_mapa)

    card = painel.layout_cards.itemAt(0).widget()
    assert "1-TOP" in card.lbl_preview.text()

    # 1. Clicar em inverter
    card.btn_inverter.click()

    # Atualiza painel com o proxy modificado
    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    painel.carregar_mapa(proxy_mapa)
    card = painel.layout_cards.itemAt(0).widget()
    assert list(proxy_mapa.referencias[0].ids) == ["seg_b", "seg_a"]
    assert "TOP-1" in card.lbl_preview.text()

    # 2. Desfazer (Undo)
    undo_stack.undo()
    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    painel.carregar_mapa(proxy_mapa)
    card = painel.layout_cards.itemAt(0).widget()
    assert list(proxy_mapa.referencias[0].ids) == ["seg_a", "seg_b"]
    assert "1-TOP" in card.lbl_preview.text()

    # 3. Refazer (Redo)
    undo_stack.redo()
    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    painel.carregar_mapa(proxy_mapa)
    card = painel.layout_cards.itemAt(0).widget()
    assert list(proxy_mapa.referencias[0].ids) == ["seg_b", "seg_a"]
    assert "TOP-1" in card.lbl_preview.text()


def test_ao_clicar_inverter_ids_sem_controller(qapp):
    """Verifica que _ao_clicar_inverter_ids não lança exceção quando controller ou proxy são None."""
    from editor.views.widget_painel_referencias import PainelReferencias

    painel = PainelReferencias(None)
    ref = croqui_pb2.Mapa.Referencia()
    ref.ids.append("seg_1")
    # Não deve lançar exceção
    painel._ao_clicar_inverter_ids(0, ref)


def test_card_referencia_possui_estilo_qtooltip(qapp):
    """[TDD] Garante que CardReferencia possui regra de estilo para QToolTip com fundo claro e texto escuro."""
    from editor.views.widget_painel_referencias import CardReferencia
    ref = croqui_pb2.Mapa.Referencia()
    card = CardReferencia(ref, 0)
    estilo = card.styleSheet()
    assert "QToolTip" in estilo
    assert "background-color" in estilo
    assert "color" in estilo


def test_atualizar_previews_atualiza_cards(qapp):
    """[TDD] Garante que atualizar_previews atualiza o texto do badge sem recriar os widgets."""
    from editor.views.widget_painel_referencias import PainelReferencias

    mapa = croqui_pb2.Mapa()
    p1 = mapa.pontos_de_interesse.add()
    p1.id = "p1"
    p1.label = "1"
    p1.circulo.x = 100
    p1.circulo.y = 100
    p1.circulo.raio = 10

    ref = mapa.referencias.add()
    ref.escalada = "Via Teste"
    ref.ids.append("p1")

    painel = PainelReferencias(None)
    painel.carregar_mapa(mapa)

    card = painel.layout_cards.itemAt(0).widget()
    assert "Codenome: <b>[ 1 ]</b>" in card.lbl_preview.text()

    # Altera label do POI
    p1.label = "2"
    painel.atualizar_previews()
    assert "Codenome: <b>[ 2 ]</b>" in card.lbl_preview.text()

    # Remove rótulo
    p1.ClearField("label")
    painel.atualizar_previews()
    assert "⚠️ Sem rótulo" in card.lbl_preview.text()


def test_card_referencia_clique_define_selecionado_e_emite_sinais(qapp):
    """[TDD] Garante que clicar no CardReferencia seleciona o card, emite referencia_selecionada e toggle emite referencia_desmarcada."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QPointF, QEvent

    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    ref1 = mapa.referencias.add()
    ref1.grupo = "Grupo 1"
    ref2 = mapa.referencias.add()
    ref2.grupo = "Grupo 2"

    painel.carregar_mapa(mapa)

    sinais_selecao = []
    sinais_desmarcacao = []
    painel.referencia_selecionada.connect(lambda idx, r: sinais_selecao.append((idx, r)))
    painel.referencia_desmarcada.connect(lambda: sinais_desmarcacao.append(True))

    card1 = painel.layout_cards.itemAt(0).widget()
    card2 = painel.layout_cards.itemAt(1).widget()

    assert not card1.selecionado
    assert not card2.selecionado

    # 1. Clique com botão esquerdo no Card 1
    ev_press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(10, 10), QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    card1.mousePressEvent(ev_press)

    assert card1.selecionado
    assert not card2.selecionado
    assert len(sinais_selecao) == 1
    assert sinais_selecao[0][0] == 0
    assert sinais_selecao[0][1].grupo == "Grupo 1"
    assert len(sinais_desmarcacao) == 0

    # 2. Clique no Card 2 desmarca Card 1 e seleciona Card 2
    ev_press2 = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(10, 10), QPointF(10, 10), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    card2.mousePressEvent(ev_press2)

    assert not card1.selecionado
    assert card2.selecionado
    assert len(sinais_selecao) == 2
    assert sinais_selecao[1][0] == 1
    assert sinais_selecao[1][1].grupo == "Grupo 2"

    # 3. Toggle: Clicar novamente no Card 2 selecionado desmarca
    card2.mousePressEvent(ev_press2)

    assert not card2.selecionado
    assert len(sinais_desmarcacao) == 1


def test_card_referencia_definir_selecionado_estilo(qapp):
    """[TDD] Verifica se o método definir_selecionado aplica cursor apontador e estilo visual de destaque."""
    from editor.views.widget_painel_referencias import CardReferencia
    from PySide6.QtCore import Qt

    ref = croqui_pb2.Mapa.Referencia()
    card = CardReferencia(ref, 0)

    assert not getattr(card, "selecionado", False)
    assert card.cursor().shape() == Qt.CursorShape.PointingHandCursor

    card.definir_selecionado(True)
    assert card.selecionado is True
    assert "#007bff" in card.styleSheet()

    card.definir_selecionado(False)
    assert card.selecionado is False
    assert "#007bff" not in card.styleSheet()


def test_selecionar_referencia_com_rolagem_e_preservacao_ao_atualizar(qapp):
    """[TDD] Verifica se selecionar_referencia chama ensureWidgetVisible e se atualizar_cards preserva a seleção."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from unittest.mock import MagicMock

    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    ref1 = mapa.referencias.add()
    ref1.grupo = "Grupo 1"
    ref2 = mapa.referencias.add()
    ref2.grupo = "Grupo 2"

    painel.carregar_mapa(mapa)

    painel.scroll_area.ensureWidgetVisible = MagicMock()
    sinais_emitidos = []
    painel.referencia_selecionada.connect(lambda idx, ref: sinais_emitidos.append((idx, ref)))

    # 1. Seleciona a referência 1 programaticamente
    painel.selecionar_referencia(1)

    assert painel.idx_card_selecionado == 1
    card1 = painel.layout_cards.itemAt(1).widget()
    assert card1.selecionado is True
    painel.scroll_area.ensureWidgetVisible.assert_called_once_with(card1)
    assert len(sinais_emitidos) == 1
    assert sinais_emitidos[0][0] == 1

    # 2. Chama atualizar_cards (reconstrução dos cards) e verifica se preserva a seleção
    painel.atualizar_cards()

    assert painel.idx_card_selecionado == 1
    novo_card1 = painel.layout_cards.itemAt(1).widget()
    assert novo_card1.selecionado is True

    # 3. Se o mapa agora tiver apenas 1 referência, o índice selecionado anterior (1) fica fora e deve ser resetado
    del mapa.referencias[1]
    painel.atualizar_cards()
    assert painel.idx_card_selecionado is None


def test_mouse_press_botao_direito_nao_seleciona(qapp):
    """[TDD] Garante que clicar com botão direito no CardReferencia não emite o sinal de clique de seleção."""
    from editor.views.widget_painel_referencias import PainelReferencias
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QPointF, QEvent

    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.grupo = "Grupo Teste"
    painel.carregar_mapa(mapa)

    card = painel.layout_cards.itemAt(0).widget()
    sinais_clique = []
    card.clicado.connect(lambda idx: sinais_clique.append(idx))

    ev_direito = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(10, 10), QPointF(10, 10), Qt.MouseButton.RightButton, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier)
    card.mousePressEvent(ev_direito)

    assert len(sinais_clique) == 0


def test_confirmar_remover_ajusta_indice_selecionado(qapp):
    """[TDD] Verifica se ao remover um card, o índice selecionado é ajustado corretamente."""
    from editor.views.widget_painel_referencias import PainelReferencias

    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    for i in range(3):
        r = mapa.referencias.add()
        r.grupo = f"Grupo {i}"
    painel.carregar_mapa(mapa)

    # Seleciona o card 2
    painel.selecionar_referencia(2)
    assert painel.idx_card_selecionado == 2

    # Remove o card 0 (anterior ao selecionado)
    painel._confirmar_remover(0)
    assert painel.idx_card_selecionado == 1

    # Remove o próprio card selecionado (agora no índice 1)
    painel._confirmar_remover(1)
    assert painel.idx_card_selecionado is None


def test_card_referencia_renomeacao_vincular_elementos_texto_e_tooltip(qapp):
    """[TDD 1.1] Verifica se o botão de vinculação possui o texto e tooltip em português brasileiro."""
    from editor.views.widget_painel_referencias import CardReferencia
    ref = croqui_pb2.Mapa.Referencia()
    card = CardReferencia(ref, 0)

    # Verifica tanto btn_vincular quanto btn_linkar (compatibilidade)
    assert hasattr(card, "btn_vincular")
    assert card.btn_vincular is card.btn_linkar
    assert "Vincular Elementos" in card.btn_vincular.text()
    assert "Vincular ou desvincular elementos (pontos e trajetos) do mapa a esta referência" in card.btn_vincular.toolTip()


def test_card_referencia_botao_vincular_toggle_texto_e_selecao_automatica(qapp):
    """[TDD 1.1] Verifica se ativar Vincular Elementos muda o texto para 'Vinculando...' e seleciona o card no painel."""
    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    ref = mapa.referencias.add()
    ref.grupo = "Grupo Teste"
    painel.carregar_mapa(mapa)

    card = painel.layout_cards.itemAt(0).widget()
    assert "Vincular Elementos" in card.btn_vincular.text()
    assert painel.idx_card_selecionado is None

    # Ativa vinculação
    card.btn_vincular.setChecked(True)
    assert "Vinculando..." in card.btn_vincular.text()
    assert painel.idx_card_selecionado == 0
    assert card.selecionado is True

    # Desativa vinculação
    card.btn_vincular.setChecked(False)
    assert "Vincular Elementos" in card.btn_vincular.text()


def test_alternar_vinculacao_entre_cards_sincroniza_selecao_e_desativa_anterior(qapp):
    """[TDD 1.1] Verifica que ativar vinculação no card B seleciona B e desativa o modo no card A."""
    painel = PainelReferencias(None)
    mapa = croqui_pb2.Mapa()
    ref0 = mapa.referencias.add()
    ref0.grupo = "Grupo 0"
    ref1 = mapa.referencias.add()
    ref1.grupo = "Grupo 1"
    painel.carregar_mapa(mapa)

    card0 = painel.layout_cards.itemAt(0).widget()
    card1 = painel.layout_cards.itemAt(1).widget()

    card0.btn_vincular.setChecked(True)
    assert painel.idx_card_selecionado == 0
    assert card0.btn_vincular.isChecked() is True
    assert card1.btn_vincular.isChecked() is False

    # Agora ativa no card 1
    card1.btn_vincular.setChecked(True)
    assert painel.idx_card_selecionado == 1
    assert card1.btn_vincular.isChecked() is True
    assert card0.btn_vincular.isChecked() is False

