# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual para seleção e arrastar e soltar (Drag & Drop) de imagens.
"""

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox, QRubberBand, QVBoxLayout, QWidget

EXTENSOES_IMAGEM_SUPORTADAS: tuple[str, ...] = (
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
    Área visual para arrastar e soltar (Drag & Drop), clicar para selecionar uma imagem
    e seleção interativa de recorte retangular (Rubber-band selection).
    """

    imagem_selecionada = Signal(str)
    regiao_selecionada = Signal(tuple)

    def __init__(self, parent: QWidget | None = None) -> None:
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
        self.label_info.setStyleSheet(
            "border: none; background: transparent; color: #555; font-size: 13px;"
        )

        self.label_preview = QLabel()
        self.label_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_preview.setStyleSheet("border: none; background: transparent;")
        self.label_preview.hide()

        self.layout_conteudo.addWidget(self.label_info)
        self.layout_conteudo.addWidget(self.label_preview)

        # Suporte a seleção com Rubber-band
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._ponto_origem_selecao: QPoint | None = None
        self._retangulo_selecionado_img: tuple[int, int, int, int] | None = None
        self.bytes_imagem_atual: bytes | None = None
        self.dimensoes_imagem_original: tuple[int, int] | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.bytes_imagem_atual and self.label_preview.isVisible():
                self._ponto_origem_selecao = (
                    event.position().toPoint() if hasattr(event, "position") else event.pos()
                )
                self.rubber_band.setGeometry(QRect(self._ponto_origem_selecao, QSize()))
                self.rubber_band.show()
                return

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

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._ponto_origem_selecao is not None and self.rubber_band:
            pos_atual = event.position().toPoint() if hasattr(event, "position") else event.pos()
            self.rubber_band.setGeometry(QRect(self._ponto_origem_selecao, pos_atual).normalized())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._ponto_origem_selecao is not None:
            rect = self.rubber_band.geometry()
            if rect.width() > 5 and rect.height() > 5 and self.dimensoes_imagem_original:
                orig_w, orig_h = self.dimensoes_imagem_original
                lbl_geom = self.label_preview.geometry()
                px = self.label_preview.pixmap()
                if px and not px.isNull() and px.width() > 0 and px.height() > 0:
                    offset_x = lbl_geom.x() + (lbl_geom.width() - px.width()) // 2
                    offset_y = lbl_geom.y() + (lbl_geom.height() - px.height()) // 2

                    x1_disp = max(0, min(px.width(), rect.left() - offset_x))
                    y1_disp = max(0, min(px.height(), rect.top() - offset_y))
                    x2_disp = max(0, min(px.width(), rect.right() - offset_x))
                    y2_disp = max(0, min(px.height(), rect.bottom() - offset_y))

                    escala_x = orig_w / px.width()
                    escala_y = orig_h / px.height()

                    img_x1 = max(0, min(orig_w, int(x1_disp * escala_x)))
                    img_y1 = max(0, min(orig_h, int(y1_disp * escala_y)))
                    img_x2 = max(0, min(orig_w, int(x2_disp * escala_x)))
                    img_y2 = max(0, min(orig_h, int(y2_disp * escala_y)))

                    if img_x2 > img_x1 and img_y2 > img_y1:
                        self._retangulo_selecionado_img = (img_x1, img_y1, img_x2, img_y2)
                        self.regiao_selecionada.emit(self._retangulo_selecionado_img)
            self._ponto_origem_selecao = None
        super().mouseReleaseEvent(event)

    def obter_retangulo_selecionado_imagem(self) -> tuple[int, int, int, int] | None:
        """Retorna o retângulo de seleção mapeado para as coordenadas em pixels da imagem."""
        return self._retangulo_selecionado_img

    def limpar_selecao(self) -> None:
        """Limpa a seleção atual do rubber-band."""
        self._retangulo_selecionado_img = None
        if hasattr(self, "rubber_band"):
            self.rubber_band.hide()

    def definir_preview_bytes(self, bytes_img: bytes) -> None:
        self.bytes_imagem_atual = bytes_img
        self._retangulo_selecionado_img = None
        if hasattr(self, "rubber_band"):
            self.rubber_band.hide()

        pixmap = QPixmap()
        if pixmap.loadFromData(bytes_img):
            self.dimensoes_imagem_original = (pixmap.width(), pixmap.height())
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

    def processar_caminho(self, caminho_arquivo: str | Path) -> None:
        caminho = Path(caminho_arquivo)
        if not caminho.exists() or not caminho.is_file():
            QMessageBox.warning(
                self, "Erro", "Não foi possível carregar o arquivo de imagem selecionado."
            )
            return
        pixmap = QPixmap(str(caminho_arquivo))
        if pixmap.isNull():
            QMessageBox.warning(
                self, "Erro", "Não foi possível carregar o arquivo de imagem selecionado."
            )
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
