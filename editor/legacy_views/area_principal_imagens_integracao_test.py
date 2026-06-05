import pytest
from PyQt6.QtWidgets import QStackedWidget
from editor.legacy_views.area_principal import JanelaPrincipal, PaginaImagens
from unittest.mock import MagicMock, patch

def test_pagina_imagens_contem_editor_de_imagens(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    
    # Navega para a página de imagens
    janela._trocar_pagina(1)
    pagina = janela.stack.currentWidget()
    
    assert isinstance(pagina, PaginaImagens)
    # Este assert deve falhar pois 'editor' ainda não foi adicionado à PaginaImagens
    assert hasattr(pagina, "editor"), "PaginaImagens deve ter um atributo 'editor'"

def test_salvamento_global_chama_salvamento_de_imagens(qtbot):
    with patch("editor.legacy_views.area_principal.yaml.dump"), \
         patch("editor.legacy_views.area_principal.open", MagicMock()), \
         patch("editor.core.croqui_experimental.GerenciadorCroquiExperimental.compilar_croqui"):
        
        janela = JanelaPrincipal(caminho_croqui="temp_croqui")
        qtbot.addWidget(janela)
        janela.croqui_data = {"id": "teste"}
        
        # Mock do editor de imagens na página
        mock_editor = MagicMock()
        janela.pagina_imagens.editor = mock_editor
        
        # Mock do editor de mapas para não falhar
        janela.pagina_mapas.editor = MagicMock()
        
        janela.salvar_croqui()
        
        assert mock_editor.salvar_alteracoes.called, "O salvamento global deve chamar salvar_alteracoes() do editor de imagens"
