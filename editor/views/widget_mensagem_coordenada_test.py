# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QWheelEvent, QUndoStack
from PyQt6.QtWidgets import QApplication, QLineEdit, QDoubleSpinBox, QDialog

from aresta_api.proto.generated.croqui_pb2 import Coordenada
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from editor.views.widget_mensagem_coordenada import WidgetMensagemCoordenada
from editor.views.widget_campo_coordenada_e7 import DialogoConfirmarCoordenadas


class TestWidgetMensagemCoordenada:
    def test_inicializacao_vazia(self, qtbot):
        coord = Coordenada()
        model = CroquiModel(coord)
        controller = CroquiController(model, QUndoStack())

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        assert widget.obter_latitude_e7() is None
        assert widget.obter_longitude_e7() is None
        assert widget.edit_lat.text() == ""
        assert widget.edit_lon.text() == ""
        assert widget.rotulo_cardinal_lat.text() == ""
        assert widget.rotulo_cardinal_lon.text() == ""
        assert widget.btn_colar.text() == "Colar"
        assert widget.btn_maps.text() == "Abrir no Maps"
        assert widget.btn_maps.isEnabled() is False

    def test_obter_has_field_objeto_sem_has_field(self, qtbot):
        class ObjetoSimples:
            latitude = 100
            longitude = None

        widget = WidgetMensagemCoordenada(ObjetoSimples())
        qtbot.addWidget(widget)
        assert widget._obter_has_field(widget.msg, "latitude") is True
        assert widget._obter_has_field(widget.msg, "longitude") is False

    def test_inicializacao_preenchida(self, qtbot):
        coord = Coordenada()
        coord.latitude = -198980280
        coord.longitude = -435212340
        model = CroquiModel(coord)
        controller = CroquiController(model, QUndoStack())

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        assert widget.obter_latitude_e7() == -198980280
        assert widget.obter_longitude_e7() == -435212340
        assert widget.obter_latitude_graus() == pytest.approx(-19.898028)
        assert widget.obter_longitude_graus() == pytest.approx(-43.521234)
        assert "S (Sul)" in widget.rotulo_cardinal_lat.text()
        assert "W (Oeste)" in widget.rotulo_cardinal_lon.text()
        assert widget.btn_maps.isEnabled() is True

    def test_inicializacao_com_zeros(self, qtbot):
        coord = Coordenada()
        coord.latitude = 0
        coord.longitude = 0
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        assert widget.obter_latitude_e7() == 0
        assert widget.obter_longitude_e7() == 0
        assert widget.edit_lat.text() == "0"
        assert widget.edit_lon.text() == "0"
        assert widget.rotulo_cardinal_lat.text() == "Equador"
        assert widget.rotulo_cardinal_lon.text() == "Greenwich"

    def test_linha_unica_para_lat_e_lon(self, qtbot):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        # Latitude e Longitude devem usar QLineEdit e não QDoubleSpinBox
        assert isinstance(widget.edit_lat, QLineEdit)
        assert isinstance(widget.edit_lon, QLineEdit)
        assert len(widget.findChildren(QDoubleSpinBox)) == 0

        # Botão de colar e maps únicos
        assert len([btn for btn in widget.findChildren(type(widget.btn_colar)) if btn.text() == "Colar"]) == 1
        assert len([btn for btn in widget.findChildren(type(widget.btn_maps)) if btn.text() == "Abrir no Maps"]) == 1

    def test_edicao_latitude_e_longitude_via_controller(self, qtbot):
        coord = Coordenada()
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        # Edita latitude
        widget.edit_lat.setText("-20.1234567")
        widget._confirmar_edicao_lat()

        assert coord.latitude == -201234567
        assert "S (Sul)" in widget.rotulo_cardinal_lat.text()
        assert undo_stack.canUndo() is True

        # Edita longitude com 0
        widget.edit_lon.setText("0")
        widget._confirmar_edicao_lon()

        assert coord.longitude == 0
        assert widget.rotulo_cardinal_lon.text() == "Greenwich"

        # Undo longitude
        undo_stack.undo()
        assert not coord.HasField("longitude")
        assert widget.edit_lon.text() == ""

        # Undo latitude
        undo_stack.undo()
        assert not coord.HasField("latitude")
        assert widget.edit_lat.text() == ""

    def test_edicao_sem_controller_direto_na_msg(self, qtbot):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        widget.edit_lat.setText("10.5")
        widget._confirmar_edicao_lat()
        assert coord.latitude == 105000000

        widget.edit_lon.setText("20.5")
        widget._confirmar_edicao_lon()
        assert coord.longitude == 205000000

        widget.edit_lat.setText("")
        widget._confirmar_edicao_lat()
        assert not coord.HasField("latitude")

        widget.edit_lon.setText("")
        widget._confirmar_edicao_lon()
        assert not coord.HasField("longitude")

    def test_limpar_campos_com_texto_vazio_apaga_no_protobuf(self, qtbot):
        coord = Coordenada()
        coord.latitude = -198980280
        coord.longitude = -435212340
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        widget.edit_lat.setText("")
        widget._confirmar_edicao_lat()
        assert not coord.HasField("latitude")
        assert widget.rotulo_cardinal_lat.text() == ""

        widget.edit_lon.setText("")
        widget._confirmar_edicao_lon()
        assert not coord.HasField("longitude")
        assert widget.rotulo_cardinal_lon.text() == ""
        assert widget.btn_maps.isEnabled() is False

    def test_textos_invalidos_ou_fora_de_escala(self, qtbot):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        widget.edit_lat.setText("abc")
        assert widget.rotulo_cardinal_lat.text() == "Inválido"
        assert widget.obter_latitude_e7() is None

        widget.edit_lat.setText("999")
        assert widget.rotulo_cardinal_lat.text() == "Inválido"
        assert widget.obter_latitude_e7() is None

        widget.edit_lon.setText("xyz")
        assert widget.rotulo_cardinal_lon.text() == "Inválido"
        assert widget.obter_longitude_e7() is None

        widget.edit_lon.setText("999")
        assert widget.rotulo_cardinal_lon.text() == "Inválido"
        assert widget.obter_longitude_e7() is None

    def test_colar_par_coordenadas(self, qtbot, monkeypatch):
        coord = Coordenada()
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted)

        sucesso = widget.processar_texto_colado("-19.898028, -43.521234")
        assert sucesso is True
        assert coord.latitude == -198980280
        assert coord.longitude == -435212340
        assert widget.obter_latitude_graus() == pytest.approx(-19.898028)
        assert widget.obter_longitude_graus() == pytest.approx(-43.521234)

    def test_colar_par_coordenadas_sem_controller(self, qtbot, monkeypatch):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted)

        sucesso = widget.processar_texto_colado("-19.898028, -43.521234")
        assert sucesso is True
        assert coord.latitude == -198980280
        assert coord.longitude == -435212340

    def test_colar_dialogo_rejeitado_e_texto_invalido(self, qtbot, monkeypatch):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Rejected)
        assert widget.processar_texto_colado("-19.898028, -43.521234") is False
        assert widget.processar_texto_colado("texto_invalido_total") is False

    def test_clique_botao_colar_clipboard(self, qtbot, monkeypatch):
        coord = Coordenada()
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted)

        app = QApplication.instance()
        app.clipboard().setText("-19.898028, -43.521234")
        widget.btn_colar.click()

        assert coord.latitude == -198980280
        assert coord.longitude == -435212340

    def test_colar_coordenada_individual_lat_e_lon(self, qtbot):
        coord = Coordenada()
        model = CroquiModel(coord)
        controller = CroquiController(model, QUndoStack())

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        sucesso_lat = widget.processar_texto_colado("19.898028 S")
        assert sucesso_lat is True
        assert coord.latitude == -198980280

        sucesso_lon = widget.processar_texto_colado("43.521234 W")
        assert sucesso_lon is True
        assert coord.longitude == -435212340

        # Colagem com foco no campo de longitude
        widget.show()
        widget.edit_lon.setFocus()
        QApplication.processEvents()
        sucesso_foco = widget.processar_texto_colado("-44.123456")
        assert sucesso_foco is True
        assert coord.longitude == -441234560

        # Colagem genérica sem foco / cardinal específico
        widget.edit_lat.clearFocus()
        widget.edit_lon.clearFocus()
        sucesso_generico = widget.processar_texto_colado("-10.123456")
        assert sucesso_generico is True
        assert coord.latitude == -101234560

        # Colagem de valor que só cabe em longitude (ex: 150.0)
        sucesso_so_lon = widget.processar_texto_colado("150.0")
        assert sucesso_so_lon is True
        assert coord.longitude == 1500000000

    def test_abrir_google_maps(self, qtbot, monkeypatch):
        coord = Coordenada()
        coord.latitude = -198980280
        coord.longitude = -435212340
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        urls = []
        from PyQt6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls) == 1
        assert "-19.8980280,-43.5212340" in urls[0]

    def test_abrir_google_maps_vazio_nao_abre(self, qtbot, monkeypatch):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        urls = []
        from PyQt6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls) == 0

    def test_scroll_no_line_edit_nao_muda_valor(self, qtbot):
        coord = Coordenada()
        coord.latitude = -198980280
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

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
        QApplication.sendEvent(widget.edit_lat, event)
        assert widget.obter_latitude_e7() == -198980280
