# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit, QSpinBox, QCheckBox
from google.protobuf.message import Message
from aresta_api.proto.generated.croqui_pb2 import Croqui, ViaMovel
from editor.views.protobuf_widget_factory import ProtobufWidgetFactory

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_primitive_widgets(qapp):
    croqui = Croqui()
    # id (string)
    widget_id = ProtobufWidgetFactory.create_widget(croqui.DESCRIPTOR.fields_by_name['id'])
    assert isinstance(widget_id, QLineEdit)
    
    viamovel = ViaMovel()
    # extensao (int32)
    widget_extensao = ProtobufWidgetFactory.create_widget(viamovel.DESCRIPTOR.fields_by_name['extensao'])
    assert isinstance(widget_extensao, QSpinBox)
    
def test_label_extraction(qapp):
    # Testa a leitura de (aresta.texto_na_ui) ou fallback para o nome do campo
    croqui = Croqui()
    label = ProtobufWidgetFactory.get_label(croqui.DESCRIPTOR.fields_by_name['id'])
    # Se não tiver texto_na_ui, retorna o nome do campo capitalizado 'Id'
    assert label == 'Id' or label == 'Identificador'

def test_comment_extraction(qapp):
    croqui = Croqui()
    tooltip = ProtobufWidgetFactory.get_tooltip(croqui.DESCRIPTOR.fields_by_name['id'])
    assert isinstance(tooltip, str)

def test_booleano_widget_e_labels_customizados(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QComboBox
    
    campo_sinal = Setor.DESCRIPTOR.fields_by_name['sinal_de_celular']
    widget = ProtobufWidgetFactory.create_widget(campo_sinal)
    
    assert isinstance(widget, QComboBox)
    assert widget.count() == 3
    assert widget.itemText(0) == "Não informado"
    assert widget.itemData(0) is None
    assert widget.itemText(1) == "Possui sinal"
    assert widget.itemData(1) is True
    assert widget.itemText(2) == "Sem sinal"
    assert widget.itemData(2) is False

def test_booleano_widget_labels_padrao(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QComboBox
    
    # Campo booleano sem anotações específicas
    campo_rev = Croqui.DESCRIPTOR.fields_by_name['revisado_manualmente']
    labels = ProtobufWidgetFactory.get_booleano_labels(campo_rev)
    assert labels == ("Não informado", "Revisado", "Não revisado")

def test_float_widget_como_qlineedit(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Mapa
    from PySide6.QtWidgets import QLineEdit
    from google.protobuf.descriptor import FieldDescriptor
    
    campo_zoom = Mapa.AjusteDeCamera.DESCRIPTOR.fields_by_name['zoom']
    assert campo_zoom.type == FieldDescriptor.TYPE_FLOAT
    
    widget = ProtobufWidgetFactory.create_widget(campo_zoom)
    assert isinstance(widget, QLineEdit)
    assert widget.validator() is not None

def test_inteiro_widget_spinbox_nullable(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from editor.views.protobuf_widget_factory import SpinBoxVazio
    
    campo_mapa_padrao = Setor.DESCRIPTOR.fields_by_name['indice_mapa_padrao']
    widget = ProtobufWidgetFactory.create_widget(campo_mapa_padrao)
    assert isinstance(widget, SpinBoxVazio)
    assert widget.textFromValue(widget.VALOR_NULO) == ""

def test_spinbox_vazio_comportamento_setas_e_esvaziamento(qapp):
    from editor.views.protobuf_widget_factory import SpinBoxVazio
    
    spin = SpinBoxVazio()
    spin.setValue(spin.VALOR_NULO)
    
    # 1. Estado inicial nulo é vazio
    assert spin.textFromValue(spin.VALOR_NULO) == ""
    assert spin.valueFromText("") == spin.VALOR_NULO
    
    # 2. Apertar para cima no estado vazio vira 0
    spin.stepBy(1)
    assert spin.value() == 0
    assert spin.textFromValue(0) == "0"
    
    # 3. Reset para vazio e apertar para baixo vira 0
    spin.setValue(spin.VALOR_NULO)
    spin.stepBy(-1)
    assert spin.value() == 0
    
    # 4. Incremento normal a partir de valor numérico
    spin.stepBy(1)
    assert spin.value() == 1
    spin.stepBy(-1)
    assert spin.value() == 0


def test_spinbox_vazio_ignora_scroll_do_mouse(qapp):
    """Garante que eventos de scroll do mouse (wheelEvent) são ignorados pelo SpinBoxVazio,
    propagando para o pai e não alterando o valor do número."""
    from editor.views.protobuf_widget_factory import SpinBoxVazio
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtWidgets import QApplication
    
    spin = SpinBoxVazio()
    spin.setValue(10)
    
    # Cria evento de rolagem para cima (angleDelta y = 120)
    event = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    
    QApplication.sendEvent(spin, event)
    
    # O evento não deve ser aceito (ignore) e o valor não deve mudar
    assert not event.isAccepted()
    assert spin.value() == 10


def test_combobox_sem_scroll_ignora_wheel_event(qapp):
    """Garante que eventos de scroll do mouse (wheelEvent) são ignorados pelo ComboBoxSemScroll,
    não alterando o índice selecionado."""
    from editor.views.protobuf_widget_factory import ComboBoxSemScroll
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtWidgets import QApplication
    
    combo = ComboBoxSemScroll()
    combo.addItem("Opção 1", 1)
    combo.addItem("Opção 2", 2)
    combo.setCurrentIndex(0)
    
    # Cria evento de rolagem para baixo (angleDelta y = -120)
    event = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    
    QApplication.sendEvent(combo, event)
    
    # O evento deve ser ignorado e a seleção deve permanecer no índice 0
    assert not event.isAccepted()
    assert combo.currentIndex() == 0


def test_booleano_e_enum_usam_combobox_sem_scroll(qapp):
    """Garante que campos booleanos e enums instanciam ComboBoxSemScroll."""
    from aresta_api.proto.generated.croqui_pb2 import Setor, ViaEsportiva
    from editor.views.protobuf_widget_factory import ComboBoxSemScroll
    
    campo_bool = Setor.DESCRIPTOR.fields_by_name['sinal_de_celular']
    campo_enum = ViaEsportiva.DESCRIPTOR.fields_by_name['tipo_parede']
    
    widget_bool = ProtobufWidgetFactory.create_widget(campo_bool)
    widget_enum = ProtobufWidgetFactory.create_widget(campo_enum)
    
    assert isinstance(widget_bool, ComboBoxSemScroll)
    assert isinstance(widget_enum, ComboBoxSemScroll)


def test_spinbox_vazio_apagar_com_backspace_mantem_vazio_ao_perder_foco(qapp):
    """Garante que apagar o texto de um spinbox (deixando vazio) mantém o estado nulo/vazio
    ao perder o foco, em vez de reverter para o valor anterior ou 0."""
    from editor.views.protobuf_widget_factory import SpinBoxVazio
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    
    spin = SpinBoxVazio()
    spin.setValue(5)
    assert spin.value() == 5
    assert spin.text() == "5"
    
    # Simula o usuário apagando o texto
    spin.lineEdit().setText("")
    
    # Simula a perda de foco (focusOutEvent)
    event = QFocusEvent(QEvent.Type.FocusOut)
    QApplication.sendEvent(spin, event)
    
    assert spin.value() == spin.VALOR_NULO
    assert spin.text() == ""
    assert spin.lineEdit().text() == ""


def test_widgets_coordenada_e_imagem(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Coordenada, Croqui
    from editor.views.widget_campo_coordenada_e7 import WidgetCampoCoordenadaE7, TipoCoordenada
    from editor.views.widget_campo_imagem import WidgetCampoImagem

    campo_lat = Coordenada.DESCRIPTOR.fields_by_name['latitude']
    campo_lon = Coordenada.DESCRIPTOR.fields_by_name['longitude']
    campo_thumb = Croqui.DESCRIPTOR.fields_by_name['caminho_thumbnail']

    w_lat = ProtobufWidgetFactory.create_widget(campo_lat)
    w_lon = ProtobufWidgetFactory.create_widget(campo_lon)
    w_thumb = ProtobufWidgetFactory.create_widget(campo_thumb)

    assert isinstance(w_lat, WidgetCampoCoordenadaE7)
    assert w_lat.tipo == TipoCoordenada.LATITUDE

    assert isinstance(w_lon, WidgetCampoCoordenadaE7)
    assert w_lon.tipo == TipoCoordenada.LONGITUDE

    assert isinstance(w_thumb, WidgetCampoImagem)
    assert w_thumb.nome_arquivo_fixo == "thumbnail.webp"






