# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PySide6.QtCore import Qt, QUrl, QMimeData, QPointF, QPoint
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPushButton, QLineEdit, QFileDialog, QMessageBox

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa, AreaDropImagem


@pytest.fixture
def imagem_png_teste(tmp_path):
    img_path = tmp_path / "foto_setor.png"
    img = Image.new("RGB", (300, 200), color=(100, 150, 200))
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def imagem_bytes_png():
    buf = io.BytesIO()
    img = Image.new("RGB", (300, 200), color=(100, 150, 200))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestDialogoAdicionarMapa:
    def test_inicializacao_dialogo(self, qtbot, tmp_path):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        dialogo = DialogoAdicionarMapa("mapa_setor_a.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)

        assert dialogo.windowTitle() == "Adicionar Novo Mapa"
        assert dialogo.btn_selecionar.text() == "Selecionar Imagem..."
        assert dialogo.input_nome.text() == "mapa_setor_a.webp"
        assert "imagens/mapa_setor_a.webp" in dialogo.rotulo_caminho_destino.text()
        assert dialogo.btn_ok.isEnabled() is False
        assert dialogo.obter_bytes_imagem_processada() is None
        assert dialogo.obter_caminho_final_absoluto() == tmp_path / "imagens" / "mapa_setor_a.webp"

    def test_selecionar_imagem_via_arquivo(self, qtbot, tmp_path, imagem_png_teste):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        dialogo = DialogoAdicionarMapa("novo_mapa.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)

        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        # Deve processar e converter automaticamente para WebP
        bytes_webp = dialogo.obter_bytes_imagem_processada()
        assert bytes_webp is not None
        assert bytes_webp.startswith(b"RIFF")
        assert b"WEBP" in bytes_webp[:16]

        # Metadados e preview devem estar preenchidos
        assert "300 x 200" in dialogo.rotulo_metadados.text()
        assert dialogo.btn_ok.isEnabled() is True
        assert dialogo.obter_dimensoes_imagem() == (300, 200)

        # Teste accept quando válido
        dialogo.accept()
        assert dialogo.result() == QDialog.DialogCode.Accepted

    def test_validacao_conflito_nome_no_disco(self, qtbot, tmp_path, imagem_png_teste):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        # Cria arquivo existente no disco
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "mapa_existente.webp").write_bytes(b"antigo")

        dialogo = DialogoAdicionarMapa("mapa_existente.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        # Como o nome já existe no disco, deve alertar e bloquear o botão OK
        assert "já existe" in dialogo.rotulo_aviso.text()
        assert dialogo.btn_ok.isEnabled() is False

        # Ao digitar um nome novo, deve liberar
        dialogo.input_nome.setText("mapa_novo_livre")
        assert dialogo.rotulo_aviso.text() == ""
        assert dialogo.btn_ok.isEnabled() is True
        assert dialogo.obter_caminho_final_relativo() == "imagens/mapa_novo_livre.webp"

    def test_validacao_conflito_nome_na_memoria_ram(self, qtbot, tmp_path, imagem_png_teste):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        model.definir_imagem_memoria("imagens/mapa_ram.webp", b"bytes_na_ram")

        dialogo = DialogoAdicionarMapa("mapa_ram.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        # Alerta conflito com imagem que está apenas na RAM
        assert "já existe" in dialogo.rotulo_aviso.text()
        assert dialogo.btn_ok.isEnabled() is False

    def test_sanitizacao_automatica_de_slug_ao_digitar(self, qtbot, tmp_path, imagem_png_teste):
        dialogo = DialogoAdicionarMapa("", db_dir=None)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        assert dialogo.obter_caminho_final_absoluto() is None

        dialogo.input_nome.setText("Setor da Família #1 (Croqui)")
        assert dialogo.obter_caminho_final_relativo() == "imagens/setor_da_familia_1_croqui.webp"
        assert dialogo.btn_ok.isEnabled() is True

        # Input vazio gera fallback 'mapa.webp'
        dialogo.input_nome.setText("")
        assert dialogo.obter_caminho_final_relativo() == "imagens/mapa.webp"

    def test_area_drop_drag_and_drop(self, qtbot, imagem_png_teste):
        area = AreaDropImagem()
        qtbot.addWidget(area)

        caminhos_recebidos = []
        area.imagem_selecionada.connect(lambda p: caminhos_recebidos.append(p))

        # Simula DragEnter com arquivo válido
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(imagem_png_teste))])
        drag_event = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime_data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dragEnterEvent(drag_event)
        assert drag_event.isAccepted() is True

        # Simula DragEnter com arquivo inválido (ex: .txt)
        mime_invalido = QMimeData()
        mime_invalido.setUrls([QUrl.fromLocalFile("arquivo.txt")])
        drag_invalido = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime_invalido,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dragEnterEvent(drag_invalido)
        assert drag_invalido.isAccepted() is False

        # Simula Drop Event
        drop_event = QDropEvent(
            QPointF(10, 10),
            Qt.DropAction.CopyAction,
            mime_data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dropEvent(drop_event)
        assert len(caminhos_recebidos) == 1
        assert Path(caminhos_recebidos[0]) == Path(imagem_png_teste)

    def test_area_drop_mouse_press_e_abrir_seletor(self, qtbot, monkeypatch, imagem_png_teste):
        area = AreaDropImagem()
        qtbot.addWidget(area)

        caminhos = []
        area.imagem_selecionada.connect(lambda p: caminhos.append(p))

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(imagem_png_teste), "PNG"))
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.mousePressEvent(mouse_event)
        assert len(caminhos) == 1
        assert Path(caminhos[0]) == Path(imagem_png_teste)

    def test_botao_selecionar_do_dialogo(self, qtbot, monkeypatch, imagem_png_teste):
        dialogo = DialogoAdicionarMapa("teste.webp")
        qtbot.addWidget(dialogo)

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(imagem_png_teste), "PNG"))
        dialogo._abrir_seletor_arquivos()

        assert dialogo.bytes_processados_webp is not None

    def test_erros_leitura_arquivo_e_bytes_invalidos(self, qtbot, monkeypatch, tmp_path):
        dialogo = DialogoAdicionarMapa("teste.webp", db_dir=tmp_path)
        qtbot.addWidget(dialogo)

        avisos = []
        monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: avisos.append(text))

        # Arquivo não existente
        dialogo.carregar_imagem_arquivo("inexistente.png")
        assert len(avisos) == 1

        # Erro ao ler arquivo
        arquivo_travado = tmp_path / "travado.png"
        arquivo_travado.write_bytes(b"dummy")
        monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(PermissionError("sem permissao")))
        dialogo.carregar_imagem_arquivo(str(arquivo_travado))
        assert len(avisos) == 2

        # Bytes inválidos
        dialogo.carregar_imagem_bytes(b"bytes_corrompidos_invalidos")
        assert len(avisos) == 3
        assert "inválido" in avisos[2]

        # Tentar accept sem imagem
        dialogo.accept()
        assert len(avisos) == 4
        assert "selecione uma imagem" in avisos[3]

    def test_validacao_conflito_disco_sem_model_e_accept_bloqueado(self, qtbot, tmp_path, imagem_png_teste):
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "mapa_duplicado.webp").write_bytes(b"existente")

        dialogo = DialogoAdicionarMapa("mapa_duplicado.webp", db_dir=tmp_path, model=None)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        assert dialogo.btn_ok.isEnabled() is False
        assert "já existe" in dialogo.rotulo_aviso.text()

        # Tentar chamar accept com botão bloqueado
        dialogo.accept()
        assert dialogo.result() != QDialog.DialogCode.Accepted

