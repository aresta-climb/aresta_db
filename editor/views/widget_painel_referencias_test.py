# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

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
         patch('PyQt6.QtWidgets.QMessageBox.warning') as MockWarning:
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
         patch('PyQt6.QtWidgets.QMessageBox.warning') as MockWarning:
        mock_dlg_instance = MockDialogo.return_value
        mock_dlg_instance.exec.return_value = True
        mock_dlg_instance.obter_referencia.return_value = ref_tentativa
        
        painel._ao_clicar_editar_alvo(0, proxy.referencias[0])
        
        MockWarning.assert_called_once()
        controller.alterar_referencia.assert_not_called()
        
    # 2. Tentar editar alvo1 para alvo3 (sucesso)
    ref_tentativa.grupo = "alvo3"
    with patch('editor.views.widget_painel_referencias.DialogoBuscaReferencia') as MockDialogo, \
         patch('PyQt6.QtWidgets.QMessageBox.warning') as MockWarning:
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
