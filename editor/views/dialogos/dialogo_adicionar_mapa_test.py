# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
)

from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.dialogo_adicionar_mapa import AreaDropImagem, DialogoAdicionarMapa


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


@pytest.fixture
def imagem_heic_teste(tmp_path):
    import pillow_heif

    pillow_heif.register_heif_opener()
    img_path = tmp_path / "mapa_foto.heic"
    img = Image.new("RGB", (320, 240), color=(120, 140, 160))
    img.save(img_path, format="HEIF")
    return img_path


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

    def test_arquivo_no_disco_nao_acusa_conflito_de_ram(self, qtbot, tmp_path, imagem_png_teste):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        # Cria arquivo no disco diretamente
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "mapa_disco.webp").write_bytes(b"conteudo_disco")

        # Não existe na RAM
        assert "imagens/mapa_disco.webp" not in model.obter_imagens_em_memoria()

        dialogo = DialogoAdicionarMapa("mapa_disco.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        # Deve acusar que existe na pasta imagens/ (disco), mas NÃO na memória RAM
        assert "já existe na pasta imagens/" in dialogo.rotulo_aviso.text()
        assert "memória RAM" not in dialogo.rotulo_aviso.text()
        assert dialogo.btn_ok.isEnabled() is False

    def test_limpeza_em_ram_libera_botao_confirmacao(self, qtbot, tmp_path, imagem_png_teste):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        model.definir_imagem_memoria("imagens/mapa_temporario.webp", b"bytes_ram")

        dialogo = DialogoAdicionarMapa("mapa_temporario.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        # Bloqueado por existir na RAM
        assert "já existe na memória RAM" in dialogo.rotulo_aviso.text()
        assert dialogo.btn_ok.isEnabled() is False

        # Ao remover da memória RAM e revalidar
        model.remover_imagem_memoria("imagens/mapa_temporario.webp")
        dialogo._validar_estado()

        assert dialogo.rotulo_aviso.text() == ""
        assert dialogo.btn_ok.isEnabled() is True

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

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", lambda *a, **k: (str(imagem_png_teste), "PNG")
        )
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

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", lambda *a, **k: (str(imagem_png_teste), "PNG")
        )
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
        monkeypatch.setattr(
            Path, "read_bytes", lambda self: (_ for _ in ()).throw(PermissionError("sem permissao"))
        )
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

    def test_validacao_conflito_disco_sem_model_e_accept_bloqueado(
        self, qtbot, tmp_path, imagem_png_teste
    ):
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

    def test_selecionar_imagem_heic_via_arquivo(self, qtbot, tmp_path, imagem_heic_teste):
        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)

        dialogo = DialogoAdicionarMapa("novo_mapa.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)

        dialogo.carregar_imagem_arquivo(str(imagem_heic_teste))

        # Deve processar e converter automaticamente para WebP
        bytes_webp = dialogo.obter_bytes_imagem_processada()
        assert bytes_webp is not None
        assert bytes_webp.startswith(b"RIFF")
        assert b"WEBP" in bytes_webp[:16]

        # Metadados e preview devem estar preenchidos
        assert "320 x 240" in dialogo.rotulo_metadados.text()
        assert dialogo.btn_ok.isEnabled() is True
        assert dialogo.obter_dimensoes_imagem() == (320, 240)
        assert dialogo.input_nome.text() == "mapa_foto.webp"

    def test_area_drop_drag_and_drop_heic_e_heif(self, qtbot, tmp_path):
        area = AreaDropImagem()
        qtbot.addWidget(area)

        caminhos_recebidos = []
        area.imagem_selecionada.connect(lambda p: caminhos_recebidos.append(p))

        # Testa extensão .heic
        mime_heic = QMimeData()
        mime_heic.setUrls([QUrl.fromLocalFile(str(tmp_path / "foto.heic"))])
        drag_heic = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime_heic,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dragEnterEvent(drag_heic)
        assert drag_heic.isAccepted() is True

        # Testa extensão .heif
        mime_heif = QMimeData()
        mime_heif.setUrls([QUrl.fromLocalFile(str(tmp_path / "foto.heif"))])
        drag_heif = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime_heif,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dragEnterEvent(drag_heif)
        assert drag_heif.isAccepted() is True

        # Testa extensão em caixa alta .HEIC
        mime_alta = QMimeData()
        mime_alta.setUrls([QUrl.fromLocalFile(str(tmp_path / "foto.HEIC"))])
        drag_alta = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            mime_alta,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.dragEnterEvent(drag_alta)
        assert drag_alta.isAccepted() is True

    def test_filtro_seletor_inclui_heic_e_constantes(self, qtbot, monkeypatch, tmp_path):
        from editor.views.dialogos.dialogo_adicionar_mapa import (
            EXTENSOES_IMAGEM_SUPORTADAS,
            FILTRO_ARQUIVOS_IMAGEM,
        )

        assert ".heic" in EXTENSOES_IMAGEM_SUPORTADAS
        assert ".heif" in EXTENSOES_IMAGEM_SUPORTADAS
        assert "*.heic" in FILTRO_ARQUIVOS_IMAGEM
        assert "*.heif" in FILTRO_ARQUIVOS_IMAGEM

        # Valida que o filtro é passado para o QFileDialog
        filtros_usados = []

        def mock_get_open_file_name(parent, caption, dir, filter):
            filtros_usados.append(filter)
            return ("", "")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", mock_get_open_file_name)

        dialogo = DialogoAdicionarMapa("teste.webp")
        qtbot.addWidget(dialogo)
        dialogo._abrir_seletor_arquivos()

        area = AreaDropImagem()
        qtbot.addWidget(area)
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        area.mousePressEvent(mouse_event)

        assert len(filtros_usados) == 2
        for f in filtros_usados:
            assert "*.heic" in f
            assert "*.heif" in f

    def test_carregar_heic_sem_pillow_heif_disponivel(self, qtbot, monkeypatch, tmp_path):
        import editor.views.dialogos.dialogo_adicionar_mapa as mod_dialogo

        monkeypatch.setattr(mod_dialogo, "garantir_suporte_heif", lambda: False)

        avisos = []
        monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: avisos.append(text))

        dialogo = DialogoAdicionarMapa("teste.webp", db_dir=tmp_path)
        qtbot.addWidget(dialogo)

        dialogo.carregar_imagem_bytes(b"\x00\x00\x00\x18ftypheic", nome_sugerido_origem="foto.heic")
        assert len(avisos) == 1
        assert "pillow-heif" in avisos[0]

    def test_carregar_imagem_usa_parametros_otimizados_webp_2_5_mp_e_metodo_6(
        self, qtbot, tmp_path, imagem_png_teste, monkeypatch
    ):
        import inspect

        import editor.views.dialogos.dialogo_adicionar_mapa as mod_dialogo

        chamadas_compressao = []
        fn_original = mod_dialogo.comprimir_imagem_para_bytes_webp
        sig = inspect.signature(fn_original)

        def mock_comprimir(*args, **kwargs):
            vinculo = sig.bind(*args, **kwargs)
            vinculo.apply_defaults()
            chamadas_compressao.append(vinculo.arguments)
            return fn_original(*args, **kwargs)

        monkeypatch.setattr(mod_dialogo, "comprimir_imagem_para_bytes_webp", mock_comprimir)

        dialogo = DialogoAdicionarMapa("teste.webp", db_dir=tmp_path)
        qtbot.addWidget(dialogo)

        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        assert len(chamadas_compressao) == 1
        assert chamadas_compressao[0]["quality"] == 85
        assert chamadas_compressao[0]["max_area"] == 2_500_000
        assert chamadas_compressao[0]["method"] == 6

    def test_dialogo_escalada_banner_dica_e_perfil_1_0_mp(self, qtbot, tmp_path, monkeypatch):
        import inspect

        import editor.views.dialogos.dialogo_adicionar_mapa as mod_dialogo

        chamadas_compressao = []
        fn_original = mod_dialogo.comprimir_imagem_para_bytes_webp
        sig = inspect.signature(fn_original)

        def mock_comprimir(*args, **kwargs):
            vinculo = sig.bind(*args, **kwargs)
            vinculo.apply_defaults()
            chamadas_compressao.append(vinculo.arguments)
            return fn_original(*args, **kwargs)

        monkeypatch.setattr(mod_dialogo, "comprimir_imagem_para_bytes_webp", mock_comprimir)

        # Imagem grande 2000 x 1000
        img_path = tmp_path / "boulder_saida.png"
        img = Image.new("RGB", (2000, 1000), color=(100, 120, 140))
        img.save(img_path, format="PNG")

        dialogo = DialogoAdicionarMapa(
            "boulder_la_bamba_p0.webp", db_dir=tmp_path, eh_escalada=True
        )
        qtbot.addWidget(dialogo)

        assert dialogo.eh_escalada is True
        assert hasattr(dialogo, "banner_dica")
        assert not dialogo.banner_dica.isHidden()
        assert "Dica de Qualidade" in dialogo.banner_dica.text()

        dialogo.carregar_imagem_arquivo(str(img_path))

        assert len(chamadas_compressao) == 1
        assert chamadas_compressao[0]["quality"] == 85
        assert chamadas_compressao[0]["max_area"] == 1_000_000
        assert chamadas_compressao[0]["method"] == 6

    def test_dialogo_setor_nao_exibe_banner_dica_e_usa_perfil_padrao(self, qtbot, tmp_path):
        dialogo = DialogoAdicionarMapa(
            "setor_fugitivos_p0.webp", db_dir=tmp_path, eh_escalada=False
        )
        qtbot.addWidget(dialogo)

        assert dialogo.eh_escalada is False
        assert dialogo.banner_dica.isHidden()

    def test_recorte_imagem_e_reverter_para_original(self, qtbot, tmp_path):
        img_path = tmp_path / "bloco_original.png"
        img = Image.new("RGB", (400, 400), color=(200, 100, 50))
        img.save(img_path, format="PNG")

        dialogo = DialogoAdicionarMapa("boulder_bloco_p0.webp", db_dir=tmp_path, eh_escalada=True)
        qtbot.addWidget(dialogo)
        dialogo.carregar_imagem_arquivo(str(img_path))

        assert dialogo.obter_dimensoes_imagem() == (400, 400)
        assert dialogo.btn_reverter_corte.isEnabled() is False

        # Aplica corte de 200x200 no centro
        dialogo.aplicar_corte((100, 100, 300, 300))
        assert dialogo.obter_dimensoes_imagem() == (200, 200)
        assert dialogo.btn_reverter_corte.isEnabled() is True

        # Reverte para original
        dialogo.reverter_corte()
        assert dialogo.obter_dimensoes_imagem() == (400, 400)
        assert dialogo.btn_reverter_corte.isEnabled() is False

    def test_area_drop_rubber_band_selecao(self, qtbot, imagem_bytes_png):
        area = AreaDropImagem()
        qtbot.addWidget(area)
        area.resize(500, 400)
        area.show()
        area.definir_preview_bytes(imagem_bytes_png)

        # Com imagem carregada, arrastar com o mouse deve ativar QRubberBand
        assert hasattr(area, "rubber_band")
        ponto_inicio = area.rect().center()
        ponto_fim = ponto_inicio + QPoint(100, 80)

        # Mouse press
        qtbot.mousePress(area, Qt.MouseButton.LeftButton, pos=ponto_inicio)
        # Mouse move
        qtbot.mouseMove(area, pos=ponto_fim)
        # Mouse release
        qtbot.mouseRelease(area, Qt.MouseButton.LeftButton, pos=ponto_fim)

        ret = area.obter_retangulo_selecionado_imagem()
        assert ret is not None
        assert ret[2] > ret[0]
        assert ret[3] > ret[1]
