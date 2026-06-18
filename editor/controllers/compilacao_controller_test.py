import pytest
from unittest.mock import MagicMock
from editor.controllers.compilacao_controller import CompilacaoController

def test_controller_com_sucesso():
    model = MagicMock()
    model.tem_avisos_ou_erros.return_value = False
    
    view = MagicMock()
    
    controller = CompilacaoController(model, view)
    controller.processar_resultado(["Compilado."])
    
    model.atualizar.assert_called_once_with(["Compilado."])
    view.ocultar_painel.assert_called_once()
    view.exibir_painel.assert_not_called()

def test_controller_com_erros():
    model = MagicMock()
    model.tem_avisos_ou_erros.return_value = True
    
    view = MagicMock()
    
    controller = CompilacaoController(model, view)
    mensagens = ["Aviso: X", "Erro: Y"]
    controller.processar_resultado(mensagens)
    
    model.atualizar.assert_called_once_with(mensagens)
    view.exibir_painel.assert_called_once()
    view.atualizar_texto.assert_called_once()
    
    html_gerado = view.atualizar_texto.call_args[0][0]
    assert "#F57C00" in html_gerado  # Cor de aviso
    assert "#D32F2F" in html_gerado  # Cor de erro

def test_formatacao_html():
    model = MagicMock()
    view = MagicMock()
    controller = CompilacaoController(model, view)
    
    html = controller._formatar_para_html(["Erro: X", "aviso: Y", "normal"])
    
    # Erro vermelho
    assert '<span style="color: #D32F2F;">Erro: X</span>' in html
    # Aviso laranja
    assert '<span style="color: #F57C00;">aviso: Y</span>' in html
    # Normal cinza/padrao
    assert '<span style="color: #333333;">normal</span>' in html
    assert "<br>" in html
    assert "white-space: pre-wrap" in html
