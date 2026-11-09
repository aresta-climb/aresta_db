# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from editor.views.estilo import Icones, configurar_tema_claro_aplicacao


def test_icones_obter_retorna_qicon_valido_e_nulo_para_inexistente(qtbot):
    """Valida se o helper retorna QIcon válido para ações mapeadas e nulo para inexistentes."""
    icon = Icones.obter("salvar")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()

    icon_painel = Icones.obter("painel")
    assert isinstance(icon_painel, QIcon)
    assert not icon_painel.isNull()

    icon_invalido = Icones.obter("acao_inexistente_totalmente_aleatoria")
    assert icon_invalido.isNull()


def test_icones_obter_destaque_lixeira_celular_e_cor_customizada(qtbot):
    """Valida a renderização real dos ícones de destaque, lixeira, celular e cor customizada."""
    icon_destaque = Icones.obter_destaque("dados")
    assert isinstance(icon_destaque, QIcon)
    assert not icon_destaque.isNull()

    icon_custom = Icones.obter("salvar", cor="#FF0000")
    assert isinstance(icon_custom, QIcon)
    assert not icon_custom.isNull()

    icon_lixeira = Icones.obter_lixeira()
    assert isinstance(icon_lixeira, QIcon)
    assert not icon_lixeira.isNull()

    icon_cel_on = Icones.obter_celular(conectado=True)
    icon_cel_off = Icones.obter_celular(conectado=False)
    assert not icon_cel_on.isNull()
    assert not icon_cel_off.isNull()


def test_icones_constantes_estilo_css_definidas():
    """Valida se as constantes de estilo QSS para coleções repetidas estão definidas."""
    assert hasattr(Icones, "QSS_BOTAO_REMOVER_DISCRETO")
    assert "QPushButton" in Icones.QSS_BOTAO_REMOVER_DISCRETO
    assert hasattr(Icones, "QSS_CONTAINER_REPEATED_INTEGRADO")
    assert hasattr(Icones, "QSS_BOTAO_RODAPE_ADICIONAR")
    assert "solid" in Icones.QSS_BOTAO_RODAPE_ADICIONAR


def test_todos_os_mapeamentos_existem_no_qtawesome(qtbot):
    """Garante que todos os nomes no MAPA geram instâncias QIcon válidas pelo QtAwesome."""
    for nome in Icones.MAPA:
        icon = Icones.obter(nome)
        assert isinstance(icon, QIcon)
        assert not icon.isNull()


def test_configurar_tema_claro_aplicacao_define_paleta_clara_e_estilos(qtbot):
    """Garante que configurar_tema_claro_aplicacao força o esquema de cores, paleta clara e QSS."""
    app = QApplication.instance()
    assert isinstance(app, QApplication)

    # Limpa a stylesheet inicial para exercitar a injeção de QToolTip e QLineEdit
    app.setStyleSheet("")

    pal = app.palette()
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#121212"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
    app.setPalette(pal)

    configurar_tema_claro_aplicacao(app)
    # Segunda chamada com stylesheet já preenchida não duplica regras
    configurar_tema_claro_aplicacao(None)
    # Chamada com objeto que não é QApplication retorna sem erro
    configurar_tema_claro_aplicacao("objeto_nao_qapplication")

    if hasattr(app, "styleHints") and hasattr(app.styleHints(), "colorScheme"):
        assert app.styleHints().colorScheme() in (
            Qt.ColorScheme.Light,
            Qt.ColorScheme.Unknown,
        )

    assert app.palette().color(QPalette.ColorRole.WindowText).name().lower() in (
        "#000000",
        "#212529",
    )
    assert app.palette().color(QPalette.ColorRole.Base).name().lower() == "#ffffff"
    assert app.palette().color(QPalette.ColorRole.ToolTipBase).name().lower() == "#ffffff"
    assert app.palette().color(QPalette.ColorRole.ToolTipText).name().lower() == "#212529"

    cor_esperada_disabled = Icones.COR_DESABILITADO.lower()
    assert (
        app.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name().lower()
        == cor_esperada_disabled
    )

    folha = app.styleSheet()
    assert "QLineEdit" in folha
    assert "QToolTip" in folha


def test_icones_publicar_e_sincronizar_renderizam_greyed_out_quando_desabilitados(qtbot):
    """Garante que os ícones ficam greyed out no modo Disabled."""
    app = QApplication.instance()
    configurar_tema_claro_aplicacao(app)

    for nome_icone in ("publicar", "sincronizar"):
        icone = Icones.obter(nome_icone)
        img_normal = icone.pixmap(QSize(24, 24), QIcon.Mode.Normal).toImage()
        img_disabled = icone.pixmap(QSize(24, 24), QIcon.Mode.Disabled).toImage()

        pixels_normal = [
            img_normal.pixelColor(x, y)
            for x in range(img_normal.width())
            for y in range(img_normal.height())
            if img_normal.pixelColor(x, y).alpha() > 128
        ]
        pixels_disabled = [
            img_disabled.pixelColor(x, y)
            for x in range(img_disabled.width())
            for y in range(img_disabled.height())
            if img_disabled.pixelColor(x, y).alpha() > 128
        ]

        assert pixels_normal
        assert pixels_disabled

        media_luminancia_normal = sum(c.lightness() for c in pixels_normal) / len(pixels_normal)
        media_luminancia_disabled = sum(c.lightness() for c in pixels_disabled) / len(
            pixels_disabled
        )
        assert media_luminancia_disabled > media_luminancia_normal + 40
