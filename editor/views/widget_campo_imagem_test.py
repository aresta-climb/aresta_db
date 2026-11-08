# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io

import pytest
from PIL import Image
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QDialog

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa
from editor.views.widget_campo_imagem import WidgetCampoImagem


@pytest.fixture
def imagem_valida_bytes():
    buf = io.BytesIO()
    img = Image.new("RGB", (300, 200), color=(0, 120, 255))
    img.save(buf, format="WEBP")
    return buf.getvalue()


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

    def test_aplicar_nova_imagem_emite_sinal_sem_mutar_modelo_diretamente(
        self, qtbot, imagem_valida_bytes
    ):
        croqui = Croqui()
        model = CroquiModel(croqui)

        widget = WidgetCampoImagem(
            model=model, caminho_imagem="", nome_arquivo_fixo="thumbnail.webp"
        )
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.aplicar_nova_imagem("imagens/thumbnail.webp", imagem_valida_bytes)

        assert blocker.args == ["imagens/thumbnail.webp", imagem_valida_bytes]
        assert widget.obter_caminho_atual() == "imagens/thumbnail.webp"
        assert "300 x 200" in widget.rotulo_metadados.text()
        # A View não deve mutar o CroquiModel diretamente fora do Controller/Histórico
        assert model.obter_bytes_imagem("imagens/thumbnail.webp") is None

    def test_substituicao_thumbnail_com_controller_preserva_bytes_antigos_no_undo(
        self, qtbot, imagem_valida_bytes
    ):
        croqui = Croqui()
        croqui.caminho_thumbnail = "imagens/thumbnail.webp"
        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/thumbnail.webp", imagem_valida_bytes)

        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetCampoImagem(
            model=model,
            caminho_imagem="imagens/thumbnail.webp",
            nome_arquivo_fixo="thumbnail.webp",
        )
        qtbot.addWidget(widget)

        def ao_alterar(caminho_novo: str, bytes_novos: bytes) -> None:
            caminho_antigo = croqui.caminho_thumbnail or None
            bytes_antigos = model.obter_bytes_imagem(caminho_antigo) if caminho_antigo else None
            controller.alterar_campo_imagem(
                croqui,
                "caminho_thumbnail",
                caminho_antigo,
                bytes_antigos,
                caminho_novo,
                bytes_novos,
            )

        widget.imagem_alterada.connect(ao_alterar)

        # Nova imagem com dimensões diferentes (450 x 350)
        buf_nova = io.BytesIO()
        Image.new("RGB", (450, 350), color=(255, 80, 0)).save(buf_nova, format="WEBP")
        bytes_novos = buf_nova.getvalue()

        widget.aplicar_nova_imagem("imagens/thumbnail.webp", bytes_novos)

        assert model.obter_bytes_imagem("imagens/thumbnail.webp") == bytes_novos
        assert "450 x 350" in widget.rotulo_metadados.text()

        # Undo deve restaurar bytes_antigos e atualizar a visualização reativamente
        undo_stack.undo()
        assert model.obter_bytes_imagem("imagens/thumbnail.webp") == imagem_valida_bytes
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

        widget = WidgetCampoImagem(
            model=model, caminho_imagem="", nome_arquivo_fixo="thumbnail.webp"
        )
        qtbot.addWidget(widget)

        def fake_exec(dialogo: DialogoAdicionarMapa):
            assert dialogo.caminho_destino_fixo == "thumbnail.webp"
            dialogo.carregar_imagem_arquivo(str(arquivo_origem))
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.selecionar_e_trocar_imagem()

        caminho_novo, bytes_novos = blocker.args
        assert caminho_novo == "imagens/thumbnail.webp"
        assert len(bytes_novos) > 0

    def test_trocar_imagem_com_nome_personalizado(
        self, qtbot, tmp_path, imagem_valida_bytes, monkeypatch
    ):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        arquivo_origem = tmp_path / "Foto Minha Parede.png"
        arquivo_origem.write_bytes(imagem_valida_bytes)

        widget = WidgetCampoImagem(model=model, caminho_imagem="", nome_arquivo_fixo=None)
        qtbot.addWidget(widget)

        def fake_exec(dialogo: DialogoAdicionarMapa):
            assert dialogo.caminho_destino_fixo is None
            dialogo.carregar_imagem_arquivo(str(arquivo_origem))
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.selecionar_e_trocar_imagem()

        caminho_novo, bytes_novos = blocker.args
        assert caminho_novo == "imagens/foto_minha_parede.webp"
        assert len(bytes_novos) > 0

    def test_trocar_imagem_selecionando_da_galeria_do_croqui(
        self, qtbot, tmp_path, imagem_valida_bytes, monkeypatch
    ):
        pasta_imagens = tmp_path / "imagens"
        pasta_imagens.mkdir()
        (pasta_imagens / "existente_galeria.webp").write_bytes(imagem_valida_bytes)

        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        widget = WidgetCampoImagem(model=model, caminho_imagem="", nome_arquivo_fixo=None)
        qtbot.addWidget(widget)

        def fake_exec(dialogo: DialogoAdicionarMapa):
            dialogo.tab_widget.setCurrentIndex(1)
            dialogo.lista_imagens.setCurrentRow(0)
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.selecionar_e_trocar_imagem()

        caminho_novo, bytes_novos = blocker.args
        assert caminho_novo == "imagens/existente_galeria.webp"
        assert bytes_novos == imagem_valida_bytes

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

    def test_cancelamento_wizard_nao_altera_estado(self, qtbot, monkeypatch):
        croqui = Croqui()
        model = CroquiModel(croqui)

        widget = WidgetCampoImagem(model=model, caminho_imagem="")
        qtbot.addWidget(widget)

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", lambda self: QDialog.DialogCode.Rejected)
        widget.selecionar_e_trocar_imagem()
        assert widget.obter_caminho_atual() == ""

    def test_trocar_imagem_com_area_maxima_customizada(self, qtbot, tmp_path, monkeypatch):
        from editor.core.processamento_imagem_campo import (
            AREA_MAXIMA_ESCALADA,
            obter_metadados_imagem,
        )

        croqui = Croqui()
        model = CroquiModel(croqui)

        # Imagem grande de 2000x2000 = 4 MP
        arquivo_grande = tmp_path / "foto_grande.jpg"
        img = Image.new("RGB", (2000, 2000), color=(255, 0, 0))
        img.save(arquivo_grande, format="JPEG")

        widget = WidgetCampoImagem(
            model=model, nome_arquivo_fixo="capa.webp", area_maxima=AREA_MAXIMA_ESCALADA
        )
        qtbot.addWidget(widget)

        def fake_exec(dialogo: DialogoAdicionarMapa):
            dialogo.carregar_imagem_arquivo(str(arquivo_grande))
            return QDialog.DialogCode.Accepted

        monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

        with qtbot.waitSignal(widget.imagem_alterada, timeout=1000) as blocker:
            widget.selecionar_e_trocar_imagem()

        _, bytes_resultado = blocker.args
        assert bytes_resultado is not None
        w, h, _, _ = obter_metadados_imagem(bytes_resultado)
        assert w * h <= AREA_MAXIMA_ESCALADA
