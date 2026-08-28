# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtGui import QUndoCommand
from editor.legacy_views.area_principal import JanelaPrincipal

class ComandoMock(QUndoCommand):
    def __init__(self, estado):
        super().__init__()
        self.estado = estado

    def undo(self):
        self.estado["valor"] = 0

    def redo(self):
        self.estado["valor"] = 1

def test_area_principal_historico_conexoes(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Inicialmente, desfazer e refazer devem estar desabilitados
    assert not janela.acao_desfazer.isEnabled()
    assert not janela.acao_refazer.isEnabled()
    
    # Empilha um comando
    estado = {"valor": -1}
    cmd = ComandoMock(estado)
    janela.historico.executar(cmd)
    
    # O comando roda (redo) imediatamente ao ser empilhado no QUndoStack
    assert estado["valor"] == 1
    
    # Desfazer deve habilitar, refazer continua desabilitado
    assert janela.acao_desfazer.isEnabled()
    assert not janela.acao_refazer.isEnabled()
    
    # Simula clique/gatilho no acao_desfazer
    janela.acao_desfazer.trigger()
    assert estado["valor"] == 0
    
    # Agora refazer deve estar habilitado, desfazer desabilitado
    assert not janela.acao_desfazer.isEnabled()
    assert janela.acao_refazer.isEnabled()
    
    # Simula clique/gatilho no acao_refazer
    janela.acao_refazer.trigger()
    assert estado["valor"] == 1
    
    # Limpa a pilha para que o closeEvent do Qtbot no teardown não trave mostrando messagebox
    janela.historico.obter_pilha().setClean()

def test_janela_roteamento_foco(qtbot):
    from unittest.mock import patch, MagicMock
    from editor.legacy_views.area_principal import JanelaPrincipal
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    # Prepara mock do croqui_model para a busca de mapas
    mapa_mock = MagicMock()
    mapa_mock.caminho_imagem_mapa = "setor.md"
    sg_mock = MagicMock()
    sg_mock.HasField.side_effect = lambda field: field == 'setor'
    sg_mock.setor.conteudo.mapas = [mapa_mock]
    pico_mock = MagicMock()
    pico_mock.HasField.side_effect = lambda field: False
    pico_mock.setores_ou_grupos = [sg_mock]

    croqui_ro = MagicMock()
    croqui_ro.picos = [pico_mock]
    janela.croqui_model = MagicMock()
    janela.croqui_model.obter_croqui_readonly.return_value = croqui_ro

    with patch.object(janela.pagina_mapas.editor, 'selecionar_mapa_por_indices') as mock_selecionar:
        # Roteamento para Dados
        janela.stack.setCurrentIndex(1) # Muda para imagens antes
        janela._on_foco_requisitado("page:dados/node:root")
        assert janela.stack.currentIndex() == 0

        # Roteamento para Mapas
        janela._on_foco_requisitado("page:mapas/file:setor.md")
        assert janela.stack.currentIndex() == 2
        mock_selecionar.assert_called_once_with(0, 0, 0)


