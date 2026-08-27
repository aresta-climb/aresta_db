# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QApplication, QLineEdit, QDoubleSpinBox, QDialog

from editor.views.widget_campo_coordenada_e7 import (
    WidgetCampoCoordenadaE7,
    TipoCoordenada,
    DialogoConfirmarCoordenadas,
)


class TestWidgetCampoCoordenadaE7:
    def test_inicializacao_vazia_latitude(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        assert isinstance(widget.edit_texto, QLineEdit)
        assert widget.obter_valor_graus() is None
        assert widget.obter_valor_e7() is None
        assert widget.edit_texto.text() == ""
        assert widget.rotulo_cardinal.text() == ""
        assert widget.btn_colar.text() == "Colar"
        assert widget.btn_maps.text() == "Abrir no Maps"
        assert widget.btn_maps.isEnabled() is False

    def test_inicializacao_vazia_longitude(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LONGITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        assert widget.obter_valor_graus() is None
        assert widget.obter_valor_e7() is None
        assert widget.edit_texto.text() == ""
        assert widget.rotulo_cardinal.text() == ""

    def test_inicializacao_com_valor_zero(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=0)
        qtbot.addWidget(widget)

        assert widget.obter_valor_graus() == 0.0
        assert widget.obter_valor_e7() == 0
        assert widget.edit_texto.text() in ("0", "0.0")
        assert widget.rotulo_cardinal.text() == "Equador"
        assert widget.btn_maps.isEnabled() is True

    def test_inicializacao_com_valor_zero_longitude(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LONGITUDE, valor_e7=0)
        qtbot.addWidget(widget)

        assert widget.obter_valor_graus() == 0.0
        assert widget.obter_valor_e7() == 0
        assert widget.rotulo_cardinal.text() == "Greenwich"

    def test_inicializacao_com_valor_preenchido(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=-198980280)
        qtbot.addWidget(widget)

        assert widget.obter_valor_graus() == pytest.approx(-19.898028)
        assert widget.obter_valor_e7() == -198980280
        assert "S (Sul)" in widget.rotulo_cardinal.text()
        assert widget.btn_maps.isEnabled() is True

    def test_definir_valor_graus_none_e_valor(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=-198980280)
        qtbot.addWidget(widget)

        widget.definir_valor_graus(None)
        assert widget.obter_valor_e7() is None
        assert widget.edit_texto.text() == ""

        widget.definir_valor_graus(-20.5)
        assert widget.obter_valor_e7() == -205000000
        assert widget.obter_valor_graus() == -20.5

    def test_sem_botoes_spin_e_scroll_nao_muda_valor(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=-198980280)
        qtbot.addWidget(widget)

        # Não deve possuir QDoubleSpinBox (apenas QLineEdit)
        assert len(widget.findChildren(QDoubleSpinBox)) == 0

        # Simula evento de scroll no QLineEdit
        event = QWheelEvent(
            QPointF(10, 10),
            QPointF(10, 10),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate,
            False,
        )
        QApplication.sendEvent(widget.edit_texto, event)

        assert widget.obter_valor_e7() == -198980280

    def test_apagar_texto_torna_campo_vazio_e_emite_none(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=-198980280)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.valor_alterado_e7, timeout=1000) as blocker:
            widget.edit_texto.setText("")
            widget.confirmar_edicao()

        assert blocker.args == [None]
        assert widget.obter_valor_e7() is None
        assert widget.obter_valor_graus() is None
        assert widget.rotulo_cardinal.text() == ""
        assert widget.btn_maps.isEnabled() is False

    def test_digitar_zero_emite_zero(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.valor_alterado_e7, timeout=1000) as blocker:
            widget.edit_texto.setText("0")
            widget.confirmar_edicao()

        assert blocker.args == [0]
        assert widget.obter_valor_e7() == 0
        assert widget.rotulo_cardinal.text() == "Equador"

    def test_digitar_coordenada_valida_com_virgula_ou_ponto(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LONGITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.valor_alterado_e7, timeout=1000) as blocker:
            widget.edit_texto.setText("-43,521234")
            widget.confirmar_edicao()

        assert blocker.args == [-435212340]
        assert widget.obter_valor_graus() == pytest.approx(-43.521234)
        assert "W (Oeste)" in widget.rotulo_cardinal.text()

    def test_digitar_texto_invalido_mantem_invalido(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        widget.edit_texto.setText("invalido")
        assert "Inválido" in widget.rotulo_cardinal.text()
        assert widget.obter_valor_e7() is None

        # Testar fora dos limites geográficos (> 90 lat)
        widget.edit_texto.setText("999.0")
        assert "Inválido" in widget.rotulo_cardinal.text()
        assert widget.obter_valor_e7() is None

    def test_colar_texto_coordenada_individual(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        sucesso = widget.processar_texto_colado("19.898028 S")
        assert sucesso is True
        assert widget.obter_valor_graus() == pytest.approx(-19.898028)
        assert widget.obter_valor_e7() == -198980280

    def test_clique_botao_colar_le_clipboard(self, qtbot):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LONGITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        app = QApplication.instance()
        app.clipboard().setText("43.521234 W")
        widget.btn_colar.click()

        assert widget.obter_valor_graus() == pytest.approx(-43.521234)
        assert widget.obter_valor_e7() == -435212340

    def test_colar_par_coordenadas_abre_dialogo(self, qtbot, monkeypatch):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        dialogo_aberto = []

        def mock_executar_dialogo(dialogo):
            dialogo_aberto.append(dialogo)
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: mock_executar_dialogo(self))

        callback_par_chamado = []
        widget.ao_receber_par_coordenadas = lambda lat_e7, lon_e7: callback_par_chamado.append((lat_e7, lon_e7))

        sucesso = widget.processar_texto_colado("-19.898028, -43.521234")
        assert sucesso is True
        assert len(dialogo_aberto) == 1
        assert callback_par_chamado == [(-198980280, -435212340)]
        assert widget.obter_valor_graus() == pytest.approx(-19.898028)

    def test_colar_par_coordenadas_em_longitude(self, qtbot, monkeypatch):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LONGITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted)

        callback_par_chamado = []
        widget.ao_receber_par_coordenadas = lambda lat_e7, lon_e7: callback_par_chamado.append((lat_e7, lon_e7))

        sucesso = widget.processar_texto_colado("-19.898028, -43.521234")
        assert sucesso is True
        assert widget.obter_valor_graus() == pytest.approx(-43.521234)
        assert callback_par_chamado == [(-198980280, -435212340)]

    def test_dialogo_inversao_eixos_e_getters(self, qtbot):
        dialogo = DialogoConfirmarCoordenadas(latitude=-19.898028, longitude=-43.521234)
        qtbot.addWidget(dialogo)

        assert dialogo.obter_latitude() == pytest.approx(-19.898028)
        assert dialogo.obter_longitude() == pytest.approx(-43.521234)

        dialogo.inverter_eixos()
        assert dialogo.obter_latitude() == pytest.approx(-43.521234)
        assert dialogo.obter_longitude() == pytest.approx(-19.898028)

        # Simula texto inválido no diálogo
        dialogo.edit_lat.setText("invalido")
        dialogo.edit_lon.setText("invalido")
        assert dialogo.obter_latitude() == pytest.approx(-19.898028)
        assert dialogo.obter_longitude() == pytest.approx(-43.521234)

    def test_abrir_google_maps_latitude_e_longitude(self, qtbot, monkeypatch):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=-198980280)
        widget.definir_longitude_contexto(-435212340)
        qtbot.addWidget(widget)

        urls_abertas = []
        from PyQt6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls_abertas.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls_abertas) == 1
        assert "-19.8980280,-43.5212340" in urls_abertas[0]

    def test_abrir_google_maps_longitude_contexto_latitude(self, qtbot, monkeypatch):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LONGITUDE, valor_e7=-435212340)
        widget.definir_latitude_contexto(-198980280)
        qtbot.addWidget(widget)

        urls_abertas = []
        from PyQt6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls_abertas.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls_abertas) == 1
        assert "-19.8980280,-43.5212340" in urls_abertas[0]

    def test_abrir_google_maps_quando_vazio_nao_abre(self, qtbot, monkeypatch):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        urls_abertas = []
        from PyQt6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls_abertas.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls_abertas) == 0

    def test_dialogo_rejeitado_e_texto_invalido(self, qtbot, monkeypatch):
        widget = WidgetCampoCoordenadaE7(tipo=TipoCoordenada.LATITUDE, valor_e7=None)
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Rejected)
        assert widget.processar_texto_colado("-19.898028, -43.521234") is False
        assert widget.processar_texto_colado("texto_totalmente_invalido") is False
