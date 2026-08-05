# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtGui import QIcon
from editor.views.estilo import Icones
from unittest.mock import patch, MagicMock

def test_icones_obter_retorna_qicon_valido(qtbot):
    """Valida se o helper retorna uma instância de QIcon."""
    icon = Icones.obter("salvar")
    assert isinstance(icon, QIcon)

def test_icones_obter_nome_invalido_retorna_icon_vazio():
    """Valida se nomes inexistentes retornam um ícone nulo."""
    icon = Icones.obter("acao_inexistente_totalmente_aleatoria")
    assert icon.isNull()

def test_icones_obter_destaque_retorna_icon_valido(qtbot):
    """Valida se o método de destaque retorna um ícone."""
    icon = Icones.obter_destaque("dados")
    assert isinstance(icon, QIcon)

def test_icones_obter_usa_qtawesome_com_cores_corretas():
    """Valida a integração com qtawesome e o uso das cores de design."""
    with patch("qtawesome.icon") as mock_qta:
        mock_qta.return_value = QIcon()
        Icones.obter("salvar")
        
        # Verifica se chamou qta.icon com o identificador correto e cores padrão definidas no design
        mock_qta.assert_called_once_with(
            "fa5s.save", 
            color=Icones.COR_NORMAL,
            color_active=Icones.COR_DESTAQUE,
            color_selected=Icones.COR_DESTAQUE
        )

def test_icones_obter_aceita_cor_customizada():
    """Valida se é possível sobrescrever a cor base."""
    with patch("qtawesome.icon") as mock_qta:
        mock_qta.return_value = QIcon()
        cor_custom = "#FF0000"
        Icones.obter("salvar", cor=cor_custom)
        
        mock_qta.assert_called_once_with(
            "fa5s.save", 
            color=cor_custom,
            color_active=Icones.COR_DESTAQUE,
            color_selected=Icones.COR_DESTAQUE
        )

def test_icones_obter_celular_retorna_icon_valido(qtbot):
    """Valida se o ícone composto de celular é retornado."""
    icon = Icones.obter_celular(conectado=True)
    assert isinstance(icon, QIcon)
    
    icon_off = Icones.obter_celular(conectado=False)
    assert isinstance(icon_off, QIcon)

def test_icones_obter_celular_usa_stacking_correto():
    """Valida se o qtawesome é chamado com múltiplos argumentos para empilhamento."""
    with patch("qtawesome.icon") as mock_qta:
        mock_qta.return_value = QIcon()
        
        # Teste conectado
        Icones.obter_celular(conectado=True)
        args, kwargs = mock_qta.call_args
        assert args == ('fa5s.mobile-alt', 'fa5s.circle')
        options = kwargs['options']
        assert len(options) == 2
        assert options[1]['color'] == Icones.COR_SUCESSO
        
        # Teste desconectado
        Icones.obter_celular(conectado=False)
        args, kwargs = mock_qta.call_args
        options = kwargs['options']
        assert options[1]['color'] == Icones.COR_ERRO

def test_todos_os_mapeamentos_existem_no_qtawesome(qtbot):
    """
    Teste de fumaça para garantir que todos os nomes no MAPA 
    estão em um formato que o QtAwesome pelo menos tenta processar.
    """
    for nome in Icones.MAPA:
        icon = Icones.obter(nome)
        assert isinstance(icon, QIcon)
        # Note: não verificamos icon.isNull() aqui pois depende do ambiente 
        # de execução (fontes instaladas), mas a chamada não deve dar erro.
