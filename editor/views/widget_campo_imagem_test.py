# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path
from PIL import Image
import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog, QDialog

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.views.widget_campo_imagem import WidgetCampoImagem, DialogoNomeImagem


@pytest.fixture
def imagem_valida_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (300, 200), color=(0, 120, 255))
    img.save(buf, format="WEBP")
    return buf.getvalue()


class TestDialogoNomeImagem:
    def test_dialogo_sugestao_e_validacao(self, qtbot, tmp_path):
        pasta_imagens = tmp_path / "imagens"
        pasta_imagens.mkdir()
        (pasta_imagens / "existente.webp").write_bytes(b"123")

        dialogo = DialogoNomeImagem(
            nome_sugerido="existente.webp",
            pasta_imagens=pasta_imagens,
            imagens_em_memoria=None,
        )
        qtbot.addWidget(dialogo)

        assert dialogo.obter_nome_escolhido() == "existente.webp"
        assert dialogo.possui_conflito() is True

        # Altera para nome livre
        dialogo.definir_nome("livre.webp")
        assert dialogo.obter_nome_escolhido() == "livre.webp"
        assert dialogo.possui_conflito() is False


class TestWidgetCampoImagem:
    def test_inicializacao_sem_imagem(self, qtbot):
        croqui = Croqui()
        model = CroquiModel(croqui)

        widget = WidgetCampoImagem(model=model, caminho_imagem="")
        qtbot.addWidget(widget)

        assert widget.obter_caminho_atual() == ""
        assert "Nenhuma imagem selecionada" in widget.rotulo_status.text()
        assert widget.btn_abrir_editor.isEnabled() is False

    def test_inicializacao_com_imagem_em_memoria(self, qtbot, imagem_valida_bytes):
        croqui = Croqui()
        croqui.caminho_thumbnail = "imagens/thumbnail.webp"
        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/thumbnail.webp", imagem_valida_bytes)

        widget = WidgetCampoImagem(model=model, caminho_imagem="imagens/thumbnail.webp")
        qtbot.addWidget(widget)

        assert widget.obter_caminho_atual() == "imagens/thumbnail.webp"
        assert "300 x 200" in widget.rotulo_metadados.text()
        assert widget.btn_abrir_editor.isEnabled() is True

    def test_aplicar_nova_imagem_emite_sinal(self, qtbot, imagem_valida_bytes):
        croqui = Croqui()
        model = CroquiModel(croqui)

        widget = WidgetCampoImagem(model=model, caminho_imagem="", nome_arquivo_fixo="thumbnail.webp")
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.aplicar_nova_imagem("imagens/thumbnail.webp", imagem_valida_bytes)

        assert blocker.args == ["imagens/thumbnail.webp", imagem_valida_bytes]
        assert widget.obter_caminho_atual() == "imagens/thumbnail.webp"
        assert "300 x 200" in widget.rotulo_metadados.text()

    def test_remover_imagem_emite_sinal(self, qtbot, imagem_valida_bytes):
        croqui = Croqui()
        croqui.caminho_thumbnail = "imagens/thumbnail.webp"
        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/thumbnail.webp", imagem_valida_bytes)

        widget = WidgetCampoImagem(model=model, caminho_imagem="imagens/thumbnail.webp")
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.imagem_removida, timeout=1000):
            widget.remover_imagem()

        assert widget.obter_caminho_atual() == ""
        assert "Nenhuma imagem selecionada" in widget.rotulo_status.text()

    def test_trocar_imagem_com_nome_fixo(self, qtbot, tmp_path, imagem_valida_bytes, monkeypatch):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        arquivo_origem = tmp_path / "foto.png"
        arquivo_origem.write_bytes(imagem_valida_bytes)

        widget = WidgetCampoImagem(model=model, caminho_imagem="", nome_arquivo_fixo="thumbnail.webp")
        qtbot.addWidget(widget)

        # Mock de seleção de arquivo
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(arquivo_origem), "Imagens"))

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.selecionar_e_trocar_imagem()

        caminho_novo, bytes_novos = blocker.args
        assert caminho_novo == "imagens/thumbnail.webp"
        assert len(bytes_novos) > 0

    def test_trocar_imagem_com_nome_personalizado(self, qtbot, tmp_path, imagem_valida_bytes, monkeypatch):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        arquivo_origem = tmp_path / "Foto Minha Parede.png"
        arquivo_origem.write_bytes(imagem_valida_bytes)

        widget = WidgetCampoImagem(model=model, caminho_imagem="", nome_arquivo_fixo=None)
        qtbot.addWidget(widget)

        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(arquivo_origem), "Imagens"))
        monkeypatch.setattr(DialogoNomeImagem, "exec", lambda self: QDialog.DialogCode.Accepted)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.selecionar_e_trocar_imagem()

        caminho_novo, bytes_novos = blocker.args
        assert caminho_novo == "imagens/foto_minha_parede.webp"
        assert len(bytes_novos) > 0

    def test_clique_abrir_no_editor_emite_sinal(self, qtbot, imagem_valida_bytes):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/mapa.webp", imagem_valida_bytes)

        widget = WidgetCampoImagem(model=model, caminho_imagem="imagens/mapa.webp")
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.abrir_no_editor, timeout=1000) as blocker:
            widget.btn_abrir_editor.click()

        assert blocker.args == ["imagens/mapa.webp"]

    def test_definir_caminho_atual_e_arquivo_ausente(self, qtbot):
        croqui = Croqui()
        model = CroquiModel(croqui)

        widget = WidgetCampoImagem(model=model, caminho_imagem="")
        qtbot.addWidget(widget)

        widget.definir_caminho_atual("imagens/ausente.webp")
        assert "Não encontrada" in widget.rotulo_status.text()
        assert widget.btn_remover.isEnabled() is True
        assert widget.btn_abrir_editor.isEnabled() is False

    def test_imagem_corrompida_ou_bytes_invalidos(self, qtbot):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/corrompida.webp", b"dados_invalidos_sem_cabecalho")

        widget = WidgetCampoImagem(model=model, caminho_imagem="imagens/corrompida.webp")
        qtbot.addWidget(widget)

        assert "Erro Img" in widget.rotulo_preview.text()

    def test_cancelamento_selecao_e_dialogo_nome(self, qtbot, tmp_path, monkeypatch):
        croqui = Croqui()
        model = CroquiModel(croqui)

        widget = WidgetCampoImagem(model=model, caminho_imagem="")
        qtbot.addWidget(widget)

        # 1. Cancela no file dialog
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("", ""))
        widget.selecionar_e_trocar_imagem()
        assert widget.obter_caminho_atual() == ""

        # 2. Cancela no diálogo de nome
        arquivo_origem = tmp_path / "foto.png"
        arquivo_origem.write_bytes(b"123")
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(arquivo_origem), "Imagens"))
        monkeypatch.setattr(DialogoNomeImagem, "exec", lambda self: QDialog.DialogCode.Rejected)

        widget.selecionar_e_trocar_imagem()
        assert widget.obter_caminho_atual() == ""
