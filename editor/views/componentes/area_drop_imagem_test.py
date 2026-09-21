# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o componente visual AreaDropImagem.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QMimeData, QPoint
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QPixmap, QImage, QColor
from PySide6.QtWidgets import QFileDialog

from editor.views.componentes.area_drop_imagem import AreaDropImagem, EXTENSOES_IMAGEM_SUPORTADAS


def criar_bytes_imagem_teste(largura: int = 20, altura: int = 20) -> bytes:
    img = QImage(largura, altura, QImage.Format.Format_RGB32)
    img.fill(QColor("blue"))
    from PySide6.QtCore import QBuffer, QIODevice
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
    img.save(buffer, "PNG")
    return bytes(buffer.data().data())


def test_area_drop_imagem_inicializacao(qtbot):
    area = AreaDropImagem()
    qtbot.addWidget(area)
    area.show()

    assert area.acceptDrops() is True
    assert area.label_info.isVisible() is True
    assert area.label_preview.isHidden() is True


def test_area_drop_imagem_clique_seleciona_arquivo(qtbot, monkeypatch, tmp_path):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    arquivo_fake = tmp_path / "foto.webp"
    arquivo_fake.write_bytes(b"dummy")

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(arquivo_fake), "Filtro"),
    )

    sinais = []
    area.imagem_selecionada.connect(sinais.append)

    # Simula clique com botão esquerdo
    from PySide6.QtCore import QPointF
    evento_clique = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.mousePressEvent(evento_clique)

    assert len(sinais) == 1
    assert sinais[0] == str(arquivo_fake)


def test_area_drop_imagem_clique_cancelado_nao_emite_sinal(qtbot, monkeypatch):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: ("", ""),
    )

    sinais = []
    area.imagem_selecionada.connect(sinais.append)

    from PySide6.QtCore import QPointF
    evento_clique = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.mousePressEvent(evento_clique)

    assert len(sinais) == 0


def test_area_drop_imagem_clique_botao_direito_ignorado(qtbot, monkeypatch):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    chamado = []
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: chamado.append(True) or ("", ""),
    )

    from PySide6.QtCore import QPointF
    evento_clique = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.mousePressEvent(evento_clique)

    assert len(chamado) == 0


def test_area_drop_imagem_drag_enter_valido(qtbot, tmp_path):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    for ext in EXTENSOES_IMAGEM_SUPORTADAS:
        mime = QMimeData()
        caminho = tmp_path / f"teste{ext}"
        mime.setUrls([QUrl.fromLocalFile(str(caminho))])

        event = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dragEnterEvent(event)
        assert event.isAccepted() is True, f"Deveria aceitar extensão {ext}"


def test_area_drop_imagem_drag_enter_invalido(qtbot, tmp_path):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    # 1. Extensão inválida
    mime_txt = QMimeData()
    caminho_txt = tmp_path / "arquivo.txt"
    mime_txt.setUrls([QUrl.fromLocalFile(str(caminho_txt))])

    event_txt = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_txt,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dragEnterEvent(event_txt)
    assert event_txt.isAccepted() is False

    # 2. Sem URLs
    mime_vazio = QMimeData()
    event_vazio = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_vazio,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dragEnterEvent(event_vazio)
    assert event_vazio.isAccepted() is False


def test_area_drop_imagem_drop_event(qtbot, tmp_path):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    caminho = tmp_path / "foto_drop.webp"
    caminho.write_bytes(b"dummy")

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(caminho))])

    sinais = []
    area.imagem_selecionada.connect(sinais.append)

    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dropEvent(event)

    assert event.isAccepted() is True
    assert len(sinais) == 1
    assert Path(sinais[0]).resolve() == caminho.resolve()


def test_area_drop_imagem_drop_event_invalido(qtbot, tmp_path):
    area = AreaDropImagem()
    qtbot.addWidget(area)

    caminho = tmp_path / "arquivo.txt"
    caminho.write_text("dummy")

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(caminho))])

    sinais = []
    area.imagem_selecionada.connect(sinais.append)

    event = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dropEvent(event)

    assert event.isAccepted() is False
    assert len(sinais) == 0


def test_area_drop_imagem_definir_preview_bytes(qtbot):
    area = AreaDropImagem()
    qtbot.addWidget(area)
    area.show()

    bytes_img = criar_bytes_imagem_teste(80, 60)
    area.definir_preview_bytes(bytes_img)

    assert area.label_preview.isVisible() is True
    assert area.label_info.isHidden() is True
    pix = area.label_preview.pixmap()
    assert pix is not None and not pix.isNull()


def test_area_drop_imagem_definir_preview_bytes_invalidos(qtbot):
    area = AreaDropImagem()
    qtbot.addWidget(area)
    area.show()

    area.definir_preview_bytes(b"dados_corrompidos_nao_imagem")
    assert area.label_preview.isHidden() is True
    assert area.label_info.isVisible() is True


def test_area_drop_imagem_processar_caminho(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    area = AreaDropImagem()
    qtbot.addWidget(area)
    area.show()

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: avisos.append(True))

    # 1. Caminho inexistente
    area.processar_caminho(tmp_path / "inexistente.png")
    assert len(avisos) == 1

    # 2. Arquivo corrompido / não imagem
    arquivo_txt = tmp_path / "falso.png"
    arquivo_txt.write_text("nao_imagem")
    area.processar_caminho(arquivo_txt)
    assert len(avisos) == 2

    # 3. Caminho válido com imagem
    arquivo_valido = tmp_path / "foto_valida.png"
    qimg = QImage(40, 40, QImage.Format.Format_RGB32)
    qimg.save(str(arquivo_valido), "PNG")

    sinais = []
    area.imagem_selecionada.connect(sinais.append)
    area.processar_caminho(arquivo_valido)
    assert len(sinais) == 1
    assert sinais[0] == str(arquivo_valido)
    assert area.label_preview.isVisible() is True

    # 4. Falha de leitura de bytes no preview
    orig_read = Path.read_bytes

    def falha_read(self):
        if "foto_valida" in str(self):
            raise IOError("Falha simulada de leitura")
        return orig_read(self)

    monkeypatch.setattr(Path, "read_bytes", falha_read)
    area.processar_caminho(arquivo_valido)
    assert len(sinais) == 2


def test_area_drop_imagem_processar_qimage(qtbot):
    area = AreaDropImagem()
    qtbot.addWidget(area)
    area.show()

    # 1. QImage nula
    qimg_nula = QImage()
    area.processar_qimage(qimg_nula)
    assert area.label_preview.isHidden() is True

    # 2. QImage válida
    qimg = QImage(50, 50, QImage.Format.Format_RGB32)
    qimg.fill(QColor("red"))
    area.processar_qimage(qimg)
    assert area.label_preview.isVisible() is True

