# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Aresta Contributors

import requests
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from aresta_api.proto.generated import beta_pb2

def obter_pixmap_fallback(fonte: beta_pb2.FonteMidia.Enum, largura: int = 120, altura: int = 90) -> QPixmap:
    """
    Gera um QPixmap com visual estilizado para servir de fallback quando a thumbnail não estiver disponível.
    """
    pixmap = QPixmap(largura, altura)
    is_instagram = (fonte == beta_pb2.FonteMidia.INSTAGRAM)
    
    # Cor de fundo temática
    cor_fundo = QColor("#E1306C") if is_instagram else QColor("#FF0000")
    texto = "Instagram" if is_instagram else "YouTube"

    pixmap.fill(cor_fundo)
    painter = QPainter(pixmap)
    painter.setPen(QColor("#FFFFFF"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), 0x0084, texto) # AlignCenter
    painter.end()

    return pixmap


def baixar_imagem_sincrona(
    url: str,
    fonte: beta_pb2.FonteMidia.Enum,
    timeout: int = 5
) -> QPixmap:
    """
    Baixa uma imagem via HTTP e carrega em um QPixmap. Se falhar, retorna o fallback temático.
    """
    if not url:
        return obter_pixmap_fallback(fonte)

    try:
        resposta = requests.get(url, timeout=timeout)
        if resposta.status_code == 200:
            imagem = QImage()
            if imagem.loadFromData(resposta.content):
                return QPixmap.fromImage(imagem)
    except Exception:
        pass

    return obter_pixmap_fallback(fonte)


class WorkerCarregadorImagem(QThread):
    """
    Worker assíncrono para download de thumbnail sem travar a thread principal da interface.
    """
    imagem_carregada = pyqtSignal(QPixmap)

    def __init__(self, url: str, fonte: beta_pb2.FonteMidia.Enum, parent=None):
        super().__init__(parent)
        self.url = url
        self.fonte = fonte

    def run(self):
        pixmap = baixar_imagem_sincrona(self.url, self.fonte)
        self.imagem_carregada.emit(pixmap)
