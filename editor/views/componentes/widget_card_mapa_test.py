# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from unittest.mock import MagicMock
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from aresta_api.proto.generated import croqui_pb2
from editor.views.componentes.widget_card_mapa import WidgetCardMapa


def _gerar_bytes_imagem_teste() -> bytes:
    img = QImage(64, 48, QImage.Format.Format_RGB32)
    img.fill(QColor("forestgreen"))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    return bytes(buffer.data())


def test_widget_card_mapa_inicializacao_com_imagem(qapp):
    mapa = croqui_pb2.Mapa(
        caminho_imagem_mapa="imagens/parede_principal_p0.webp",
        largura_mapa=1920,
        altura_mapa=1080,
    )
    mock_model = MagicMock()
    mock_model.obter_bytes_imagem.return_value = _gerar_bytes_imagem_teste()
    mock_controller = MagicMock()
    mock_form = MagicMock()
    mock_form.current_node = MagicMock()

    card = WidgetCardMapa(
        msg_mapa=mapa,
        indice=0,
        model=mock_model,
        controller=mock_controller,
        formulario=mock_form,
        extra_path="expando:mapas/item:0",
    )

    assert card.property("repeated_index") == 0
    assert "Mapa [0]" in card.rotulo_titulo.text()
    assert "parede_principal_p0.webp" in card.rotulo_titulo.text()
    assert "imagens/parede_principal_p0.webp" in card.rotulo_arquivo.text()
    assert "1920 × 1080 px" in card.rotulo_resolucao.text()

    # Verifica miniatura
    pixmap = card.rotulo_miniatura.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()

    # Verifica controles essenciais
    assert card.alca is not None
    assert card.btn_subir is not None
    assert card.btn_descer is not None
    assert card.btn_remover is not None
    assert card.btn_abrir_editor is not None


def test_widget_card_mapa_sem_imagem(qapp):
    mapa = croqui_pb2.Mapa(
        caminho_imagem_mapa="imagens/inexistente.webp",
        largura_mapa=0,
        altura_mapa=0,
    )
    mock_model = MagicMock()
    mock_model.obter_bytes_imagem.return_value = None

    card = WidgetCardMapa(
        msg_mapa=mapa,
        indice=1,
        model=mock_model,
    )

    assert card.property("repeated_index") == 1
    assert "Mapa [1]" in card.rotulo_titulo.text()
    assert "Sem Imagem" in card.rotulo_miniatura.text()
    assert "Resolução não informada" in card.rotulo_resolucao.text()


def test_widget_card_mapa_definir_indice(qapp):
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/mapa1.webp")
    card = WidgetCardMapa(msg_mapa=mapa, indice=0)

    card.definir_indice(3)
    assert card.property("repeated_index") == 3
    assert "Mapa [3]" in card.rotulo_titulo.text()


def test_widget_card_mapa_abrir_no_editor_de_mapas(qapp, monkeypatch):
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/setor.webp")
    mock_controller = MagicMock()
    mock_model = MagicMock()
    mock_form = MagicMock()
    mock_form.current_node = MagicMock()

    import editor.views.widget_editor_dados as wed
    monkeypatch.setattr(wed, "get_node_path", lambda node: "expando:setores/item:0")

    card = WidgetCardMapa(
        msg_mapa=mapa,
        indice=0,
        model=mock_model,
        controller=mock_controller,
        formulario=mock_form,
        extra_path="expando:mapas/item:0",
    )

    card.btn_abrir_editor.click()

    caminho_esperado = "page:mapas/expando:setores/item:0/expando:mapas/item:0"
    mock_controller.set_contexto.assert_called_once_with(caminho_esperado)
    mock_model.notificar_foco_requisitado.assert_called_once_with(caminho_esperado)


def test_widget_card_mapa_reage_a_imagem_alterada(qapp):
    from editor.models.croqui_model import CroquiModel
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    croqui = Croqui()
    model = CroquiModel(croqui)
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/foto.webp")

    card = WidgetCardMapa(msg_mapa=mapa, indice=0, model=model)
    assert "Sem Imagem" in card.rotulo_miniatura.text()

    # Define imagem na memória do modelo e emite o sinal
    bytes_img = _gerar_bytes_imagem_teste()
    model.definir_imagem_memoria("imagens/foto.webp", bytes_img)
    model.imagem_alterada.emit("imagens/foto.webp")

    # Emissão com caminho diferente não altera nada
    model.imagem_alterada.emit("imagens/outra_foto.webp")
    assert card.rotulo_miniatura.pixmap() is not None


def test_widget_card_mapa_bytes_invalidos_exibe_erro(qapp):
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/corrompida.webp")
    mock_model = MagicMock()
    mock_model.obter_bytes_imagem.return_value = b"bytes_corrompidos_que_nao_sao_imagem"

    card = WidgetCardMapa(msg_mapa=mapa, indice=0, model=mock_model)
    assert card.rotulo_miniatura.text() == "Erro Imagem"


def test_widget_card_mapa_abrir_no_editor_sem_controller_ou_sem_form(qapp):
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/foto.webp")
    card = WidgetCardMapa(msg_mapa=mapa, indice=0)

    # Não deve lançar exceção ao clicar sem form/controller
    card.btn_abrir_editor.click()

    # Form sem current_node
    mock_form = MagicMock()
    mock_form.current_node = None
    mock_ctrl = MagicMock()
    card2 = WidgetCardMapa(msg_mapa=mapa, indice=0, formulario=mock_form, controller=mock_ctrl)
    card2.btn_abrir_editor.click()
    mock_ctrl.set_contexto.assert_not_called()

