# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
from PySide6.QtWidgets import QApplication, QPushButton
from aresta_api.proto.generated.croqui_pb2 import Pico, ArquivoMapas, ColecaoDeMapas, Mapa
from editor.views.widget_editor_dados import WidgetFormularioPadrao
from unittest.mock import MagicMock

class MockController:
    def alterar_primitivo(self, msg, campo_nome, valor_antigo, valor_novo):
        pass
    def alterar_oneof(self, msg, oneof_nome, nome_antigo, valor_antigo, nome_novo, valor_novo):
        pass

def test_pico_renders_mapas_gerais_inline(qtbot):
    pico = Pico()
    pico.nome = "Gruta da Lapinha"
    pico.mapas_gerais.conteudo.mapas.add().caminho_imagem_mapa = "mapa1.webp"
    
    controller = MockController()
    mock_model = MagicMock()
    widget = WidgetFormularioPadrao(model=mock_model, controller=controller)
    mock_node = MagicMock()
    mock_node.message = pico
    mock_node.field = None
    widget.load_node(mock_node)
    
    # We must find the collapsible widget or the label for Mapas gerais
    from PySide6.QtWidgets import QLabel
    found_mapas_gerais = False
    for label in widget.findChildren(QLabel):
        if "Mapas gerais" in label.text() or "Mapas Gerais" in label.text():
            found_mapas_gerais = True
            break
            
    assert found_mapas_gerais, "Label 'Mapas gerais' not found inside Pico, so the field is being skipped"

def test_verify_mapas_gerais_path(qtbot, monkeypatch):
    pico = Pico()
    pico.nome = "Gruta da Lapinha"
    pico.mapas_gerais.conteudo.mapas.add().caminho_imagem_mapa = "mapa1.webp"
    
    class MockController2:
        def __init__(self):
            self.last_path = None
        def set_contexto(self, path):
            self.last_path = path
    
    controller = MockController2()
    mock_model = MagicMock()
    widget = WidgetFormularioPadrao(model=mock_model, controller=controller)
    mock_node = MagicMock()
    mock_node.message = pico
    mock_node.field = None
    
    # We must patch get_node_path
    import editor.views.widget_editor_dados
    monkeypatch.setattr(editor.views.widget_editor_dados, "get_node_path", lambda n: "expando:picos/item:0")
    
    widget.load_node(mock_node)
    
    from editor.views.widget_editor_dados import WidgetColapsavel
    for colapsavel in widget.findChildren(WidgetColapsavel):
        colapsavel.toggle_button.setChecked(True) # forces lazy loading if closed
    
    for btn in widget.findChildren(QPushButton):
        print("BTN:", btn.text())
        if btn.text() == "Abrir no Editor de Mapas":
            btn.click()
            print("PATH EMITTED:", controller.last_path)
            break
            
    assert controller.last_path is not None, "Button was not clicked or path not emitted"


def test_integracao_renomear_escalada_com_sincronizacao_mapas_e_sessao_foco(qtbot):
    """
    Teste de integração ponta-a-ponta (Princípios II, V e VII):
    1. Usuário digita no QLineEdit de nome da escalada no formulário de dados.
    2. Sincronização automática com referências em mapas em tempo real.
    3. Digitação contínua mescla no mesmo passo de histórico (count == 1).
    4. Um único Undo desfaz toda a digitação e retorna tanto a escalada quanto referências ao original.
    5. Um Redo reaplica a edição.
    6. Ao perder e retomar foco, inicia nova sessão (novo session_id).
    7. Referência adicionada entre sessões é encontrada na nova busca limpa e sincronizada.
    8. Undos em cascata respeitam o isolamento de sessões.
    """
    from aresta_api.proto.generated import croqui_pb2
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from PySide6.QtGui import QUndoStack, QFocusEvent
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QLineEdit

    # 1. Configuração do modelo e dados
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pedra do Baú")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Bauzinho"

    via = setor.escaladas.add()
    via.via_esportiva.nome = "Via Normal"

    mapa_setor = setor.mapas.add()
    ref_setor = mapa_setor.referencias.add(escalada="Via Normal", ids=["linha_1"])

    mapa_geral = pico.mapas_gerais.conteudo.mapas.add()
    ref_geral = mapa_geral.referencias.add(setor="Bauzinho", escalada="Via Normal", ids=["poi_geral"])

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 2. Carrega a escalada no formulário de dados
    form = WidgetFormularioPadrao(model=model, controller=controller)
    proxy_via = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva
    proxy_ref_setor = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0].referencias[0]
    proxy_ref_geral = model.obter_croqui_readonly().picos[0].mapas_gerais.conteudo.mapas[0].referencias[0]

    mock_node = MagicMock()
    mock_node.message = proxy_via
    mock_node.field = None
    form.load_node(mock_node)

    # Localiza o QLineEdit do campo "nome"
    campo_nome = None
    for le in form.findChildren(QLineEdit):
        if le.property("protobuf_field") == "nome":
            campo_nome = le
            break

    assert campo_nome is not None, "QLineEdit para campo nome não encontrado"
    assert campo_nome.text() == "Via Normal"

    # 3. Simula digitação contínua dentro da mesma sessão de foco
    campo_nome.setText("Via Normal ")
    campo_nome.setText("Via Normal D")
    campo_nome.setText("Via Normal Direta")

    # Verifica mesclagem em 1 único comando no histórico
    assert undo_stack.count() == 1
    assert proxy_via.nome == "Via Normal Direta"
    assert proxy_ref_setor.escalada == "Via Normal Direta"
    assert proxy_ref_geral.escalada == "Via Normal Direta"

    # 4. Undo único reverte tudo ao estado original
    undo_stack.undo()
    assert undo_stack.index() == 0
    assert proxy_via.nome == "Via Normal"
    assert proxy_ref_setor.escalada == "Via Normal"
    assert proxy_ref_geral.escalada == "Via Normal"

    # 5. Redo reaplica a edição consolidada
    undo_stack.redo()
    assert undo_stack.index() == 1
    assert proxy_via.nome == "Via Normal Direta"
    assert proxy_ref_setor.escalada == "Via Normal Direta"
    assert proxy_ref_geral.escalada == "Via Normal Direta"

    # 6. Simula perda e retomada de foco (início de nova sessão de foco)
    evento_focus_out = QFocusEvent(QEvent.Type.FocusOut)
    QApplication.sendEvent(campo_nome, evento_focus_out)

    evento_focus_in = QFocusEvent(QEvent.Type.FocusIn)
    QApplication.sendEvent(campo_nome, evento_focus_in)

    # 7. Usuário cria uma nova referência em outro mapa apontando para "Via Normal Direta"
    mapa_novo = setor.mapas.add()
    ref_nova = mapa_novo.referencias.add(escalada="Via Normal Direta", ids=["linha_nova"])
    proxy_ref_nova = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[1].referencias[0]

    # 8. Digita nova alteração no campo com nova sessão de foco
    campo_nome.setText("Via Normal Direta Variante")

    # Deve ter criado um NOVO comando na pilha (count == 2) sem mesclar com a sessão anterior
    assert undo_stack.count() == 2
    assert undo_stack.index() == 2
    assert proxy_via.nome == "Via Normal Direta Variante"
    assert proxy_ref_setor.escalada == "Via Normal Direta Variante"
    assert proxy_ref_geral.escalada == "Via Normal Direta Variante"
    # A nova referência descoberta na nova busca também foi atualizada!
    assert proxy_ref_nova.escalada == "Via Normal Direta Variante"

    # 9. Primeiro Undo desfaz a segunda sessão (volta para "Via Normal Direta")
    undo_stack.undo()
    assert undo_stack.index() == 1
    assert proxy_via.nome == "Via Normal Direta"
    assert proxy_ref_setor.escalada == "Via Normal Direta"
    assert proxy_ref_geral.escalada == "Via Normal Direta"
    assert proxy_ref_nova.escalada == "Via Normal Direta"

    # 10. Segundo Undo desfaz a primeira sessão (volta para "Via Normal")
    undo_stack.undo()
    assert undo_stack.index() == 0
    assert proxy_via.nome == "Via Normal"
    assert proxy_ref_setor.escalada == "Via Normal"
    assert proxy_ref_geral.escalada == "Via Normal"

            
