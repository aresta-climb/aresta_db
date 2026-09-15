# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtGui import QIcon
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


def test_configurar_tema_claro_aplicacao_define_color_scheme_light(qtbot):
    """Garante que configurar_tema_claro_aplicacao força o esquema de cores e a paleta padrão clara."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette, QColor
    from PySide6.QtCore import Qt
    from editor.views.estilo import configurar_tema_claro_aplicacao

    app = QApplication.instance()
    assert app is not None

    # Simula paleta com texto branco herdada de um Dark Mode externo
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
    app.setPalette(pal)
    assert app.palette().color(QPalette.ColorRole.WindowText).name() == "#ffffff"

    with patch.object(app.styleHints(), "setColorScheme") as mock_set_scheme:
        configurar_tema_claro_aplicacao(app)
        mock_set_scheme.assert_called_once_with(Qt.ColorScheme.Light)

    # A paleta padrão deve ter sido restaurada para texto escuro e fundo claro moderno
    assert app.palette().color(QPalette.ColorRole.WindowText).name() == "#000000"
    assert app.palette().color(QPalette.ColorRole.ButtonText).name() == "#000000"
    assert app.palette().color(QPalette.ColorRole.Window).name() != "#d4d0c8"


def test_configurar_tema_claro_aplicacao_estiliza_qtooltip(qtbot):
    """Garante que configurar_tema_claro_aplicacao define estilo explícito para QToolTip prevenindo renderização preta no Windows."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette
    from editor.views.estilo import configurar_tema_claro_aplicacao

    app = QApplication.instance()
    assert app is not None

    configurar_tema_claro_aplicacao(app)

    # Verifica folha de estilo global da aplicação
    folha = app.styleSheet()
    assert "QToolTip" in folha
    assert "color:" in folha
    assert "background-color:" in folha

    # Verifica a paleta do QToolTip
    pal = app.palette()
    assert pal.color(QPalette.ColorRole.ToolTipBase).name().lower() == "#ffffff"
    assert pal.color(QPalette.ColorRole.ToolTipText).name().lower() == "#212529"


def test_configurar_tema_claro_aplicacao_sem_instancia():
    """Garante que a função retorna graciosamente se nenhuma instância de QApplication existir."""
    from editor.views.estilo import configurar_tema_claro_aplicacao
    with patch("PySide6.QtWidgets.QApplication.instance", return_value=None):
        configurar_tema_claro_aplicacao(None)


def test_configurar_tema_claro_aplicacao_captura_excecoes(qtbot):
    """Garante que a função não propaga exceções se styleHints ou setPalette falharem."""
    from PySide6.QtWidgets import QApplication
    from editor.views.estilo import configurar_tema_claro_aplicacao

    app = QApplication.instance()
    assert app is not None

    with patch.object(app, "styleHints", side_effect=RuntimeError("erro simulado")), \
         patch.object(app, "setPalette", side_effect=RuntimeError("erro paleta")):
        configurar_tema_claro_aplicacao(app)




