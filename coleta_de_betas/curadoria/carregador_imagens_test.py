# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtGui import QPixmap
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.curadoria.carregador_imagens import (
    obter_pixmap_fallback,
    baixar_imagem_sincrona
)

def test_obter_pixmap_fallback_instagram(qtbot):
    pixmap = obter_pixmap_fallback(beta_pb2.FonteMidia.INSTAGRAM)
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()
    assert pixmap.width() > 0
    assert pixmap.height() > 0


def test_obter_pixmap_fallback_youtube(qtbot):
    pixmap = obter_pixmap_fallback(beta_pb2.FonteMidia.YOUTUBE)
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()


@patch("requests.get")
def test_baixar_imagem_sincrona_sucesso(mock_get, qtbot):
    from PyQt6.QtGui import QImage
    from PyQt6.QtCore import QBuffer, QIODevice, QByteArray

    img = QImage(2, 2, QImage.Format.Format_RGB32)
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    png_bytes = bytes(ba.data())
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = png_bytes
    mock_get.return_value = mock_resp

    pixmap = baixar_imagem_sincrona("https://exemplo.com/thumb.png", beta_pb2.FonteMidia.YOUTUBE)
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()
    assert pixmap.width() == 2
    assert pixmap.height() == 2


@patch("requests.get")
def test_baixar_imagem_sincrona_erro_usa_fallback(mock_get, qtbot):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    pixmap = baixar_imagem_sincrona("https://exemplo.com/nao_existe.png", beta_pb2.FonteMidia.INSTAGRAM)
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()
