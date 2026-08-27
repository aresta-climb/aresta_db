# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import MagicMock

# Importaremos as classes depois de criá-las. Por enquanto os imports vão falhar, o que é o esperado no TDD.
from editor.controllers.compilacao_controller import CompilacaoController
from editor.models.compilacao_log import CompilacaoLog

class ViewMock:
    def __init__(self):
        self.visivel = False
        self.html_exibido = ""
        self.focada = False

    def exibir_painel(self):
        self.visivel = True
        self.focada = True

    def ocultar_painel(self):
        self.visivel = False

    def atualizar_texto(self, html: str):
        self.html_exibido = html

def test_integracao_fluxo_com_erros():
    """Verifica o fluxo completo do controller processando logs com erros e atualizando a view."""
    # Descomentar assim que as classes existirem
    model = CompilacaoLog()
    view = ViewMock()
    controller = CompilacaoController(model, view)
    
    # QUANDO chegam logs de compilação
    logs_brutos = [
        "Iniciando compilação...",
        "Aviso: Ponto de interesse fora do mapa.",
        "Erro: Arquivo croqui.yaml mal formatado."
    ]
    controller.processar_resultado(logs_brutos)
    
    # ENTÃO o modelo deve ter guardado os logs
    assert model.obter_logs() == logs_brutos
    assert model.tem_avisos_ou_erros() is True
    
    # E a view deve ter sido instruída a aparecer e exibir o HTML formatado
    assert view.visivel is True
    assert view.focada is True
    assert "Aviso:" in view.html_exibido
    assert "Erro:" in view.html_exibido

def test_integracao_fluxo_sucesso_absoluto():
    """Verifica o fluxo completo do controller processando logs sem nenhum erro e ocultando a view."""
    # Descomentar assim que as classes existirem
    model = CompilacaoLog()
    view = ViewMock()
    view.visivel = True # Simulando que estava aberto antes
    controller = CompilacaoController(model, view)
    
    # QUANDO chegam logs de compilação sem erro
    logs_brutos = [
        "Iniciando compilação...",
        "Tudo certo."
    ]
    controller.processar_resultado(logs_brutos)
    
    # ENTÃO o modelo deve ter guardado os logs
    assert model.obter_logs() == logs_brutos
    assert model.tem_avisos_ou_erros() is False
    
    # E a view deve ter sido ocultada
    assert view.visivel is False
