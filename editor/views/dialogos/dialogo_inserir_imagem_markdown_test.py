# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QSize, QMimeData, QUrl
from PySide6.QtGui import QImage, QDropEvent, QDragEnterEvent
from PySide6.QtWidgets import QDialogButtonBox

from editor.views.dialogos.dialogo_inserir_imagem_markdown import DialogoInserirImagemMarkdown


def test_dialogo_galeria_listagem_e_busca(qapp, tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)

    # Cria duas imagens para teste
    img1 = QImage(100, 100, QImage.Format.Format_RGB32)
    img1.fill(0xFF0000)
    img1.save(str(pasta_imagens / "setor_bloco_a.webp"), "WEBP")

    img2 = QImage(100, 100, QImage.Format.Format_RGB32)
    img2.fill(0x00FF00)
    img2.save(str(pasta_imagens / "setor_bloco_b.webp"), "WEBP")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    assert dialogo.tab_widget.currentIndex() == 0  # Inicia na aba de galeria

    # Verifica que as 2 imagens aparecem na lista
    assert dialogo.lista_imagens.count() == 2

    # Testa o filtro de busca
    dialogo.input_busca.setText("bloco_a")
    assert dialogo.lista_imagens.item(0).isHidden() is False
    assert dialogo.lista_imagens.item(1).isHidden() is True

    # Limpa a busca
    dialogo.input_busca.setText("")
    assert dialogo.lista_imagens.item(0).isHidden() is False
    assert dialogo.lista_imagens.item(1).isHidden() is False

    # Seleciona o primeiro item e insere com legenda
    dialogo.lista_imagens.setCurrentRow(0)
    dialogo.input_legenda.setText("Bloco A Principal")
    
    assert dialogo.btn_inserir.isEnabled() is True
    assert dialogo.obter_tag_markdown() == "![Bloco A Principal](imagens/setor_bloco_a.webp)"
    assert dialogo.obter_nome_imagem() == "setor_bloco_a.webp"


def test_dialogo_galeria_legenda_obrigatoria(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)

    img = QImage(50, 50, QImage.Format.Format_RGB32)
    img.save(str(pasta_imagens / "foto_teste.webp"), "WEBP")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    dialogo.lista_imagens.setCurrentRow(0)
    assert dialogo.nome_imagem_selecionada == "foto_teste.webp"
    
    # Sem legenda, botão Inserir deve estar desabilitado
    assert dialogo.btn_inserir.isEnabled() is False
    dialogo.accept()
    assert dialogo.result() == 0  # Não aceita

    # Digita legenda
    dialogo.input_legenda.setText("Foto da Base")
    assert dialogo.btn_inserir.isEnabled() is True
    dialogo.accept()
    assert dialogo.result() == 1
    assert dialogo.obter_tag_markdown() == "![Foto da Base](imagens/foto_teste.webp)"


def test_dialogo_imagem_inicial_interna(qapp, tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)

    caminho_img = pasta_imagens / "setor_interno.webp"
    img = QImage(50, 50, QImage.Format.Format_RGB32)
    img.save(str(caminho_img), "WEBP")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path, imagem_inicial=caminho_img)
    assert dialogo.tab_widget.currentIndex() == 0  # Permanece na galeria
    assert dialogo.nome_imagem_selecionada == "setor_interno.webp"


def test_dialogo_importar_nova_imagem_arquivo(qapp, tmp_path):
    caminho_db = tmp_path / "croqui_db"
    caminho_db.mkdir()
    pasta_externa = tmp_path / "externo"
    pasta_externa.mkdir()

    # Cria uma imagem externa PNG
    caminho_png_externo = pasta_externa / "Entrada Do Setor.png"
    img_externa = QImage(300, 200, QImage.Format.Format_RGB32)
    img_externa.fill(0x0000FF)
    img_externa.save(str(caminho_png_externo), "PNG")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=caminho_db)
    dialogo.tab_widget.setCurrentIndex(1)  # Aba de importação

    # Carrega o arquivo externo
    dialogo.carregar_imagem_externa(caminho_png_externo)

    # O nome sugerido deve ser sanitizado em snake_case com extensão .webp
    assert dialogo.input_nome_arquivo.text() == "entrada_do_setor.webp"
    # Sem legenda, botão Inserir fica desabilitado
    assert dialogo.btn_inserir.isEnabled() is False

    dialogo.input_legenda.setText("Vista da entrada")
    assert dialogo.btn_inserir.isEnabled() is True
    # Executa a ação de inserir/salvar
    dialogo.accept()

    # Verifica que o arquivo foi gravado na pasta imagens/ do croqui
    arquivo_salvo = caminho_db / "imagens" / "entrada_do_setor.webp"
    assert arquivo_salvo.exists()
    assert dialogo.obter_tag_markdown() == "![Vista da entrada](imagens/entrada_do_setor.webp)"


def test_dialogo_importar_imagem_clipboard(qapp, tmp_path):
    caminho_db = tmp_path / "croqui_db"
    caminho_db.mkdir()

    img_clipboard = QImage(150, 150, QImage.Format.Format_RGB32)
    img_clipboard.fill(0xFFFF00)

    # Inicia o diálogo já com a imagem do clipboard
    dialogo = DialogoInserirImagemMarkdown(caminho_db=caminho_db, imagem_inicial=img_clipboard)
    assert dialogo.tab_widget.currentIndex() == 1  # Deve focar na aba de importação
    assert dialogo.input_nome_arquivo.text().startswith("imagem_")
    assert dialogo.input_nome_arquivo.text().endswith(".webp")

    # Permite editar o nome antes de salvar
    dialogo.input_nome_arquivo.setText("meu_print_personalizado.webp")
    dialogo.input_legenda.setText("Croqui esquemático")
    dialogo.accept()

    arquivo_salvo = caminho_db / "imagens" / "meu_print_personalizado.webp"
    assert arquivo_salvo.exists()
    assert dialogo.obter_tag_markdown() == "![Croqui esquemático](imagens/meu_print_personalizado.webp)"


def test_dialogo_importar_validacao_nome_vazio(qapp, tmp_path):
    caminho_db = tmp_path / "croqui_db"
    caminho_db.mkdir()

    img = QImage(50, 50, QImage.Format.Format_RGB32)
    dialogo = DialogoInserirImagemMarkdown(caminho_db=caminho_db, imagem_inicial=img)
    dialogo.input_legenda.setText("Legenda válida")
    dialogo.input_nome_arquivo.setText("")
    
    # Com nome vazio, não deve permitir aceitar
    assert dialogo.btn_inserir.isEnabled() is False
    dialogo.accept()
    assert dialogo.result() == 0  # Não aceitou


def test_dialogo_galeria_duplo_clique(qapp, tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)

    img = QImage(50, 50, QImage.Format.Format_RGB32)
    img.save(str(pasta_imagens / "duplo_clique.webp"), "WEBP")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    item = dialogo.lista_imagens.item(0)

    # Duplo clique sem legenda não fecha e foca na legenda
    dialogo._ao_duplo_clique_galeria(item)
    assert dialogo.result() == 0

    # Duplo clique com legenda aceita
    dialogo.input_legenda.setText("Legenda do duplo clique")
    dialogo._ao_duplo_clique_galeria(item)
    assert dialogo.obter_nome_imagem() == "duplo_clique.webp"
    assert dialogo.result() == 1  # Accepted


def test_dialogo_area_drop_drag_and_drop_events(qapp, tmp_path):
    pasta_externa = tmp_path / "ext"
    pasta_externa.mkdir()
    caminho_img = pasta_externa / "drop_teste.jpg"
    img = QImage(50, 50, QImage.Format.Format_RGB32)
    img.save(str(caminho_img), "JPEG")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    area = dialogo.area_drop

    from PySide6.QtCore import QPoint, QPointF
    # Simula DragEnter com arquivo válido
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(caminho_img))])
    event_enter = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dragEnterEvent(event_enter)
    assert event_enter.isAccepted()

    # Simula DragEnter com arquivo inválido (.txt)
    mime_txt = QMimeData()
    mime_txt.setUrls([QUrl.fromLocalFile(str(tmp_path / "arquivo.txt"))])
    event_enter_txt = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime_txt,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dragEnterEvent(event_enter_txt)
    assert not event_enter_txt.isAccepted()

    # Simula DropEvent
    event_drop = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    area.dropEvent(event_drop)
    assert event_drop.isAccepted()
    assert dialogo.input_nome_arquivo.text() == "drop_teste.webp"


def test_dialogo_area_drop_mouse_press_qfiledialog(qapp, tmp_path, monkeypatch):
    caminho_img = tmp_path / "arquivo_dialogo.png"
    img = QImage(50, 50, QImage.Format.Format_RGB32)
    img.save(str(caminho_img), "PNG")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    area = dialogo.area_drop

    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(caminho_img), "PNG"))

    class FakeMouseEvent:
        def button(self):
            return Qt.MouseButton.LeftButton

    area.mousePressEvent(FakeMouseEvent())
    assert dialogo.input_nome_arquivo.text() == "arquivo_dialogo.webp"


def test_dialogo_carregar_bytes(qapp, tmp_path):
    caminho_db = tmp_path / "croqui_db"
    caminho_db.mkdir()

    dialogo = DialogoInserirImagemMarkdown(caminho_db=caminho_db)
    dialogo.carregar_imagem_externa(b"fake_bytes")
    assert dialogo.input_nome_arquivo.text().startswith("imagem_")


def test_dialogo_pasta_imagens_inexistente(qapp, tmp_path):
    caminho_db = tmp_path / "croqui_vazio"
    # Não cria a pasta imagens
    dialogo = DialogoInserirImagemMarkdown(caminho_db=caminho_db)
    assert dialogo.lista_imagens.count() == 0


def test_dialogo_area_drop_imagem_invalida(qapp, tmp_path, monkeypatch):
    caminho_txt = tmp_path / "fake.png"
    caminho_txt.write_text("not an image")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    area = dialogo.area_drop

    avisos = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: avisos.append(True))
    area.processar_caminho(str(caminho_txt))
    assert len(avisos) == 1

    # processar_qimage com QImage nula
    qimg_nula = QImage()
    area.processar_qimage(qimg_nula)


def test_dialogo_deselecao_e_accept_vazios(qapp, tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    img = QImage(10, 10, QImage.Format.Format_RGB32)
    img.save(str(pasta_imagens / "img.webp"), "WEBP")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    dialogo.input_legenda.setText("Legenda válida")
    dialogo.lista_imagens.setCurrentRow(0)
    assert dialogo.btn_inserir.isEnabled() is True

    # Limpa selecao na galeria
    dialogo.lista_imagens.clearSelection()
    assert dialogo.nome_imagem_selecionada == ""
    assert dialogo.btn_inserir.isEnabled() is False
    dialogo.accept()
    assert dialogo.result() == 0

    # Vai para aba de importacao sem fonte carregada
    dialogo.tab_widget.setCurrentIndex(1)
    dialogo.fonte_imagem_importacao = None
    dialogo.accept()
    assert dialogo.result() == 0

    # Com fonte mas com nome vazio
    dialogo.fonte_imagem_importacao = img
    dialogo.input_nome_arquivo.setText("")
    dialogo.accept()
    assert dialogo.result() == 0

def test_dialogo_importar_imagem_em_memoria_com_model(qapp, tmp_path):
    from editor.models.croqui_model import CroquiModel
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    croqui = Croqui()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path

    img = QImage(60, 40, QImage.Format.Format_RGB32)
    img.fill(0x00FF00)

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path, model=model, imagem_inicial=img)
    dialogo.input_nome_arquivo.setText("foto_na_ram.webp")
    dialogo.input_legenda.setText("Foto em memória")
    dialogo.accept()

    # O arquivo NÃO deve ter sido salvo no disco ainda
    arquivo_disco = tmp_path / "imagens" / "foto_na_ram.webp"
    assert not arquivo_disco.exists()

    # A imagem DEVE estar no buffer em memória do model
    imagens_ram = model.obter_imagens_em_memoria()
    assert "imagens/foto_na_ram.webp" in imagens_ram
    assert len(imagens_ram["imagens/foto_na_ram.webp"]) > 0


def test_dialogo_gerar_nome_unico_com_colisao(qapp, tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    (pasta_imagens / "foto.webp").write_bytes(b"dummy")
    (pasta_imagens / "foto_1.webp").write_bytes(b"dummy")

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    # Testa colisão com múltiplos arquivos em disco
    assert dialogo._gerar_nome_unico("foto.webp") == "foto_2.webp"

    # Testa com entrada de bytes brutos em carregar_imagem_externa
    dialogo.carregar_imagem_externa(b"fakebytes")
    assert dialogo.input_nome_arquivo.text().startswith("imagem_")


def test_dialogo_galeria_lista_imagens_em_memoria(qapp, tmp_path):
    from editor.models.croqui_model import CroquiModel
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    croqui = Croqui()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path

    img = QImage(20, 20, QImage.Format.Format_RGB32)
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.ReadWrite)
    img.save(buf, "WEBP")
    bytes_webp = bytes(buf.data())

    # Adiciona imagem apenas na RAM
    model.definir_imagem_memoria("imagens/apenas_na_ram.webp", bytes_webp)

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path, model=model)
    assert dialogo.lista_imagens.count() == 1
    assert dialogo.lista_imagens.item(0).text() == "apenas_na_ram.webp"


def test_dialogo_area_drop_clique_cancelado(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("", ""))

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPointF, Qt
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    dialogo.area_drop.mousePressEvent(event)
    assert dialogo.fonte_imagem_importacao is None


def test_dialogo_area_drop_clique_selecionado(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    arquivo_png = tmp_path / "selecionado.png"
    img = QImage(20, 20, QImage.Format.Format_RGB32)
    img.save(str(arquivo_png), "PNG")

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(arquivo_png), "PNG"))

    dialogo = DialogoInserirImagemMarkdown(caminho_db=tmp_path)
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPointF, Qt
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    dialogo.area_drop.mousePressEvent(event)
    assert dialogo.fonte_imagem_importacao == str(arquivo_png)


