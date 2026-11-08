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

    def test_aba_galeria_imagens_do_croqui_disco_e_ram_com_busca(
        self, qtbot, tmp_path, imagem_bytes_png
    ):
        from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp

        bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(imagem_bytes_png)
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "setor_norte.webp").write_bytes(bytes_webp)

        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        model.definir_imagem_memoria("imagens/setor_sul_ram.webp", bytes_webp)

        dialogo = DialogoAdicionarMapa("novo_mapa.webp", db_dir=tmp_path, model=model)
        qtbot.addWidget(dialogo)

        assert hasattr(dialogo, "tab_widget")
        assert dialogo.tab_widget.count() == 2
        assert dialogo.tab_widget.tabText(0) == "Importar Nova Imagem"
        assert dialogo.tab_widget.tabText(1) == "Imagens do Croqui"

        # Alterna para aba Imagens do Croqui
        dialogo.tab_widget.setCurrentIndex(1)
        assert dialogo.lista_imagens.count() == 2

        # Filtra busca
        dialogo.input_busca.setText("sul_ram")
        assert dialogo.lista_imagens.item(0).isHidden() is True
        assert dialogo.lista_imagens.item(1).isHidden() is False

        # Seleciona item da galeria
        dialogo.lista_imagens.setCurrentRow(1)
        assert dialogo.btn_ok.isEnabled() is True
        assert dialogo.obter_caminho_final_relativo() == "imagens/setor_sul_ram.webp"
        assert dialogo.obter_dimensoes_imagem() == (300, 200)
        assert dialogo.obter_bytes_imagem_processada() == bytes_webp

    def test_modo_caminho_destino_fixo_nao_acusa_colisao_consigo_mesmo(
        self, qtbot, tmp_path, imagem_png_teste
    ):
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "thumbnail.webp").write_bytes(b"antigo")

        croqui = Croqui()
        model = CroquiModel(croqui)
        model.definir_caminho_db(tmp_path)
        model.definir_imagem_memoria("imagens/thumbnail.webp", b"antigo_ram")

        dialogo = DialogoAdicionarMapa(
            "thumbnail.webp",
            db_dir=tmp_path,
            model=model,
            caminho_destino_fixo="thumbnail.webp",
        )
        qtbot.addWidget(dialogo)

        assert dialogo.input_nome.isReadOnly() is True
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        assert dialogo.rotulo_aviso.text() == ""
        assert dialogo.btn_ok.isEnabled() is True
        assert dialogo.obter_caminho_final_relativo() == "imagens/thumbnail.webp"

    def test_modo_substituicao_mapa_exibe_checkbox_reescalar_pois_quando_muda_resolucao(
        self, qtbot, tmp_path, imagem_png_teste
    ):
        # imagem_png_teste tem 300 x 200
        dialogo = DialogoAdicionarMapa(
            "setor_a_p0.webp",
            db_dir=tmp_path,
            modo_substituicao_mapa=True,
            largura_mapa_antiga=600,
            altura_mapa_antiga=400,
            qtd_pois_mapa=4,
        )
        qtbot.addWidget(dialogo)
        dialogo.show()

        # Antes de carregar imagem, checkbox está oculto
        assert dialogo.chk_reescalar_pois.isHidden() is True
        assert dialogo.deve_reescalar_pois() is False

        # Carrega imagem 300x200 (diferente de 600x400) -> exibe checkbox marcado por padrão
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))
        assert dialogo.chk_reescalar_pois.isVisible() is True
        assert dialogo.chk_reescalar_pois.isChecked() is True
        assert dialogo.deve_reescalar_pois() is True

        # Se a resolução antiga já era 300x200, não exibe checkbox
        dialogo_mesma_res = DialogoAdicionarMapa(
            "setor_a_p0.webp",
            db_dir=tmp_path,
            modo_substituicao_mapa=True,
            largura_mapa_antiga=300,
            altura_mapa_antiga=200,
            qtd_pois_mapa=4,
        )
        qtbot.addWidget(dialogo_mesma_res)
        dialogo_mesma_res.show()
        dialogo_mesma_res.carregar_imagem_arquivo(str(imagem_png_teste))
        assert dialogo_mesma_res.chk_reescalar_pois.isHidden() is True
        assert dialogo_mesma_res.deve_reescalar_pois() is False

    def test_galeria_duplo_clique_deselecao_erro_disco_e_opcoes_customizadas(
        self, qtbot, tmp_path, imagem_bytes_png, monkeypatch
    ):
        from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp

        bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(imagem_bytes_png)
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "img_ok.webp").write_bytes(bytes_webp)
        (pasta_img / "img_erro.webp").write_bytes(b"dados")

        orig_read = Path.read_bytes

        def falha_leitura(self):
            if self.name == "img_erro.webp":
                raise PermissionError("Sem permissão")
            return orig_read(self)

        monkeypatch.setattr(Path, "read_bytes", falha_leitura)

        dialogo = DialogoAdicionarMapa(
            "capa.webp",
            db_dir=tmp_path,
            max_area_override=1_000_000,
            titulo_janela="Trocar Capa",
            texto_botao_ok="Salvar Capa",
        )
        qtbot.addWidget(dialogo)

        assert dialogo.windowTitle() == "Trocar Capa"
        assert dialogo.btn_ok.text() == "Salvar Capa"
        assert dialogo.max_area == 1_000_000

        # Chamadas de corte sem imagem carregada não falham
        dialogo.aplicar_corte((0, 0, 10, 10))
        dialogo.reverter_corte()

        # Alterna para galeria, seleciona, deseleciona e dá duplo clique
        dialogo.tab_widget.setCurrentIndex(1)
        assert dialogo.lista_imagens.count() == 1
        dialogo.lista_imagens.setCurrentRow(0)
        assert dialogo.btn_ok.isEnabled() is True
        dialogo.lista_imagens.clearSelection()
        assert dialogo.btn_ok.isEnabled() is False

        item = dialogo.lista_imagens.item(0)
        dialogo._ao_duplo_clique_galeria(item)
        assert dialogo.result() == QDialog.DialogCode.Accepted

    def test_recorte_via_botao_e_tratamento_erro(
        self, qtbot, tmp_path, imagem_png_teste, monkeypatch
    ):
        dialogo = DialogoAdicionarMapa("mapa.webp", db_dir=tmp_path)
        qtbot.addWidget(dialogo)
        dialogo.resize(560, 520)
        dialogo.show()
        dialogo.carregar_imagem_arquivo(str(imagem_png_teste))

        # Simula seleção rubber-band no area_drop e clique em btn_recortar
        ponto_ini = dialogo.area_drop.rect().center()
        ponto_fim = ponto_ini + QPoint(80, 60)
        qtbot.mousePress(dialogo.area_drop, Qt.MouseButton.LeftButton, pos=ponto_ini)
        qtbot.mouseMove(dialogo.area_drop, pos=ponto_fim)
        qtbot.mouseRelease(dialogo.area_drop, Qt.MouseButton.LeftButton, pos=ponto_fim)
        assert dialogo.btn_recortar.isEnabled() is True
        dialogo.btn_recortar.click()
        assert dialogo.corte_ativo is True

    def test_abertura_lazy_nao_carrega_galeria_no_init_e_le_bytes_sob_demanda(
        self, qtbot, tmp_path, imagem_bytes_png, monkeypatch
    ):
        from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp
        from editor.views.dialogos.componentes_dialogo_imagem import (
            limpar_cache_miniaturas_imagem,
        )

        limpar_cache_miniaturas_imagem()
        bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(imagem_bytes_png)
        pasta_img = tmp_path / "imagens"
        pasta_img.mkdir(parents=True, exist_ok=True)
        (pasta_img / "mapa_lazy.webp").write_bytes(bytes_webp)

        leituras_disco = []
        orig_read_bytes = Path.read_bytes

        def contar_read_bytes(self: Path) -> bytes:
            leituras_disco.append(self.name)
            return orig_read_bytes(self)

        monkeypatch.setattr(Path, "read_bytes", contar_read_bytes)

        # 1. Ao abrir na Aba 0 ("Importar Nova Imagem"), nenhuma imagem da galeria é lida
        dialogo = DialogoAdicionarMapa("novo_mapa.webp", db_dir=tmp_path)
        qtbot.addWidget(dialogo)
        assert dialogo._galeria_carregada is False
        assert dialogo.lista_imagens.count() == 0
        assert leituras_disco == []

        # 2. Ao alternar para a Aba 1 ("Imagens do Croqui"), carrega as miniaturas sob demanda
        dialogo.tab_widget.setCurrentIndex(1)
        assert dialogo._galeria_carregada is True
        assert dialogo.lista_imagens.count() == 1
        item = dialogo.lista_imagens.item(0)
        # UserRole guarda apenas o nome do arquivo, não os bytes inteiros
        assert item.data(Qt.ItemDataRole.UserRole) == "mapa_lazy.webp"

        # 3. Ao selecionar o item, carrega os bytes completos sob demanda
        dialogo.lista_imagens.setCurrentRow(0)
        assert dialogo.obter_bytes_imagem_processada() == bytes_webp
        assert dialogo.obter_dimensoes_imagem() == (300, 200)
        assert dialogo.btn_ok.isEnabled() is True

        # 4. Se o arquivo for removido antes da seleção de outro item, trata ausência com segurança
        (pasta_img / "mapa_lazy.webp").unlink()
        dialogo._ao_selecionar_item_galeria()
        assert dialogo.obter_bytes_imagem_processada() is None
        assert dialogo.btn_ok.isEnabled() is False
