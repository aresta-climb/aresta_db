# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual para seleção e arrastar e soltar (Drag & Drop) de imagens.
"""

from pathlib import Path
from typing import Optional, Tuple, Any, Union
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QMouseEvent, QImage


EXTENSOES_IMAGEM_SUPORTADAS: Tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
    ".heif",
)

FILTRO_ARQUIVOS_IMAGEM: str = (
    f"Imagens ({' '.join(f'*{ext}' for ext in EXTENSOES_IMAGEM_SUPORTADAS)})"
)


class AreaDropImagem(QWidget):
    """
    Área visual para arrastar e soltar (Drag & Drop) ou clicar para selecionar uma imagem.
    """
    imagem_selecionada = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(420, 220)
        self.setStyleSheet("""
            AreaDropImagem {
                border: 2px dashed #888;
                border-radius: 8px;
                background-color: #fafafa;
            }
            AreaDropImagem:hover {
                background-color: #f0f4f8;
                border-color: #0066cc;
            }
        """)

        self.layout_conteudo = QVBoxLayout(self)
        self.layout_conteudo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_conteudo.setContentsMargins(12, 12, 12, 12)

        self.label_info = QLabel("Arraste e solte uma imagem aqui\nou clique para selecionar")
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_info.setStyleSheet("border: none; background: transparent; color: #555; font-size: 13px;")

        self.label_preview = QLabel()
        self.label_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_preview.setStyleSheet("border: none; background: transparent;")
        self.label_preview.hide()

        self.layout_conteudo.addWidget(self.label_info)
        self.layout_conteudo.addWidget(self.label_preview)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            arquivo, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar Imagem",
                "",
                FILTRO_ARQUIVOS_IMAGEM,
            )
            if arquivo:
                self.imagem_selecionada.emit(arquivo)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                ext = Path(urls[0].toLocalFile()).suffix.lower()
                if ext in EXTENSOES_IMAGEM_SUPORTADAS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            arquivo = urls[0].toLocalFile()
            ext = Path(arquivo).suffix.lower()
            if ext in EXTENSOES_IMAGEM_SUPORTADAS:
                self.imagem_selecionada.emit(arquivo)
                event.acceptProposedAction()
                return
        event.ignore()

    def definir_preview_bytes(self, bytes_img: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(bytes_img):
            largura_max = max(10, self.width() - 30)
            altura_max = max(10, self.height() - 30)
            pixmap_scaled = pixmap.scaled(
                largura_max,
                altura_max,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.label_preview.setPixmap(pixmap_scaled)
            self.label_info.hide()
            self.label_preview.show()

    def processar_caminho(self, caminho_arquivo: Union[str, Path]) -> None:
        caminho = Path(caminho_arquivo)
        if not caminho.exists() or not caminho.is_file():
            QMessageBox.warning(self, "Erro", "Não foi possível carregar o arquivo de imagem selecionado.")
            return
        pixmap = QPixmap(str(caminho_arquivo))
        if pixmap.isNull():
            QMessageBox.warning(self, "Erro", "Não foi possível carregar o arquivo de imagem selecionado.")
            return
        try:
            self.definir_preview_bytes(caminho.read_bytes())
        except Exception:
            pass
        self.imagem_selecionada.emit(str(caminho_arquivo))

    def processar_qimage(self, qimage: QImage) -> None:
        if qimage.isNull():
            return
        from PySide6.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        qimage.save(buffer, "PNG")  # type: ignore[call-overload]
        self.definir_preview_bytes(bytes(buffer.data().data()))
