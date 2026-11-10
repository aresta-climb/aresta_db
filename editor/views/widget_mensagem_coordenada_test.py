# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QUndoStack, QWheelEvent
from PySide6.QtWidgets import QApplication, QDialog, QDoubleSpinBox, QLineEdit

from aresta_api.proto.generated.croqui_pb2 import Coordenada
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.widget_campo_coordenada_e7 import DialogoConfirmarCoordenadas
from editor.views.widget_mensagem_coordenada import (
    DialogoProgressoMalhaEstrada,
    WidgetMensagemCoordenada,
    WorkerGeracaoMalhaEstrada,
)


class TestWidgetMensagemCoordenada:
    def test_inicializacao_vazia(self, qtbot):
        coord = Coordenada()
        model = CroquiModel(coord)
        controller = CroquiController(model, QUndoStack())

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        assert widget.obter_latitude_e7() is None
        assert widget.obter_longitude_e7() is None
        assert widget.edit_lat.text() == ""
        assert widget.edit_lon.text() == ""
        assert widget.rotulo_cardinal_lat.text() == ""
        assert widget.rotulo_cardinal_lon.text() == ""
        assert widget.btn_colar.text() == "Colar"
        assert widget.btn_maps.text() == "Abrir no Maps"
        assert widget.btn_maps.isEnabled() is False

    def test_obter_has_field_objeto_sem_has_field(self, qtbot):
        class ObjetoSimples:
            latitude = 100
            longitude = None

        widget = WidgetMensagemCoordenada(ObjetoSimples())
        qtbot.addWidget(widget)
        assert widget._obter_has_field(widget.msg, "latitude") is True
        assert widget._obter_has_field(widget.msg, "longitude") is False

    def test_inicializacao_preenchida(self, qtbot):
        coord = Coordenada()
        coord.latitude = -198980280
        coord.longitude = -435212340
        model = CroquiModel(coord)
        controller = CroquiController(model, QUndoStack())

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        assert widget.obter_latitude_e7() == -198980280
        assert widget.obter_longitude_e7() == -435212340
        assert widget.obter_latitude_graus() == pytest.approx(-19.898028)
        assert widget.obter_longitude_graus() == pytest.approx(-43.521234)
        assert "S (Sul)" in widget.rotulo_cardinal_lat.text()
        assert "W (Oeste)" in widget.rotulo_cardinal_lon.text()
        assert widget.btn_maps.isEnabled() is True

    def test_inicializacao_com_zeros(self, qtbot):
        coord = Coordenada()
        coord.latitude = 0
        coord.longitude = 0
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        assert widget.obter_latitude_e7() == 0
        assert widget.obter_longitude_e7() == 0
        assert widget.edit_lat.text() == "0"
        assert widget.edit_lon.text() == "0"
        assert widget.rotulo_cardinal_lat.text() == "Equador"
        assert widget.rotulo_cardinal_lon.text() == "Greenwich"

    def test_linha_unica_para_lat_e_lon(self, qtbot):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        # Latitude e Longitude devem usar QLineEdit e não QDoubleSpinBox
        assert isinstance(widget.edit_lat, QLineEdit)
        assert isinstance(widget.edit_lon, QLineEdit)
        assert len(widget.findChildren(QDoubleSpinBox)) == 0

        # Botão de colar e maps únicos
        assert (
            len(
                [
                    btn
                    for btn in widget.findChildren(type(widget.btn_colar))
                    if btn.text() == "Colar"
                ]
            )
            == 1
        )
        assert (
            len(
                [
                    btn
                    for btn in widget.findChildren(type(widget.btn_maps))
                    if btn.text() == "Abrir no Maps"
                ]
            )
            == 1
        )

    def test_edicao_latitude_e_longitude_via_controller(self, qtbot):
        coord = Coordenada()
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        # Edita latitude
        widget.edit_lat.setText("-20.1234567")
        widget._confirmar_edicao_lat()

        assert coord.latitude == -201234567
        assert "S (Sul)" in widget.rotulo_cardinal_lat.text()
        assert undo_stack.canUndo() is True

        # Edita longitude com 0
        widget.edit_lon.setText("0")
        widget._confirmar_edicao_lon()

        assert coord.longitude == 0
        assert widget.rotulo_cardinal_lon.text() == "Greenwich"

        # Undo longitude
        undo_stack.undo()
        assert not coord.HasField("longitude")
        assert widget.edit_lon.text() == ""

        # Undo latitude
        undo_stack.undo()
        assert not coord.HasField("latitude")
        assert widget.edit_lat.text() == ""

    def test_edicao_sem_controller_direto_na_msg(self, qtbot):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        widget.edit_lat.setText("10.5")
        widget._confirmar_edicao_lat()
        assert coord.latitude == 105000000

        widget.edit_lon.setText("20.5")
        widget._confirmar_edicao_lon()
        assert coord.longitude == 205000000

        widget.edit_lat.setText("")
        widget._confirmar_edicao_lat()
        assert not coord.HasField("latitude")

        widget.edit_lon.setText("")
        widget._confirmar_edicao_lon()
        assert not coord.HasField("longitude")

    def test_limpar_campos_com_texto_vazio_apaga_no_protobuf(self, qtbot):
        coord = Coordenada()
        coord.latitude = -198980280
        coord.longitude = -435212340
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        widget.edit_lat.setText("")
        widget._confirmar_edicao_lat()
        assert not coord.HasField("latitude")
        assert widget.rotulo_cardinal_lat.text() == ""

        widget.edit_lon.setText("")
        widget._confirmar_edicao_lon()
        assert not coord.HasField("longitude")
        assert widget.rotulo_cardinal_lon.text() == ""
        assert widget.btn_maps.isEnabled() is False

    def test_textos_invalidos_ou_fora_de_escala(self, qtbot):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        widget.edit_lat.setText("abc")
        assert widget.rotulo_cardinal_lat.text() == "Inválido"
        assert widget.obter_latitude_e7() is None

        widget.edit_lat.setText("999")
        assert widget.rotulo_cardinal_lat.text() == "Inválido"
        assert widget.obter_latitude_e7() is None

        widget.edit_lon.setText("xyz")
        assert widget.rotulo_cardinal_lon.text() == "Inválido"
        assert widget.obter_longitude_e7() is None

        widget.edit_lon.setText("999")
        assert widget.rotulo_cardinal_lon.text() == "Inválido"
        assert widget.obter_longitude_e7() is None

    def test_colar_par_coordenadas(self, qtbot, monkeypatch):
        coord = Coordenada()
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        monkeypatch.setattr(
            DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted
        )

        sucesso = widget.processar_texto_colado("-19.898028, -43.521234")
        assert sucesso is True
        assert coord.latitude == -198980280
        assert coord.longitude == -435212340
        assert widget.obter_latitude_graus() == pytest.approx(-19.898028)
        assert widget.obter_longitude_graus() == pytest.approx(-43.521234)

    def test_colar_par_coordenadas_sem_controller(self, qtbot, monkeypatch):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        monkeypatch.setattr(
            DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted
        )

        sucesso = widget.processar_texto_colado("-19.898028, -43.521234")
        assert sucesso is True
        assert coord.latitude == -198980280
        assert coord.longitude == -435212340

    def test_colar_dialogo_rejeitado_e_texto_invalido(self, qtbot, monkeypatch):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        monkeypatch.setattr(
            DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Rejected
        )
        assert widget.processar_texto_colado("-19.898028, -43.521234") is False
        assert widget.processar_texto_colado("texto_invalido_total") is False

    def test_clique_botao_colar_clipboard(self, qtbot, monkeypatch):
        coord = Coordenada()
        model = CroquiModel(coord)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        monkeypatch.setattr(
            DialogoConfirmarCoordenadas, "exec", lambda self: QDialog.DialogCode.Accepted
        )

        app = QApplication.instance()
        app.clipboard().setText("-19.898028, -43.521234")
        widget.btn_colar.click()

        assert coord.latitude == -198980280
        assert coord.longitude == -435212340

    def test_colar_coordenada_individual_lat_e_lon(self, qtbot):
        coord = Coordenada()
        model = CroquiModel(coord)
        controller = CroquiController(model, QUndoStack())

        widget = WidgetMensagemCoordenada(coord, controller=controller, model=model)
        qtbot.addWidget(widget)

        sucesso_lat = widget.processar_texto_colado("19.898028 S")
        assert sucesso_lat is True
        assert coord.latitude == -198980280

        sucesso_lon = widget.processar_texto_colado("43.521234 W")
        assert sucesso_lon is True
        assert coord.longitude == -435212340

        # Colagem com foco no campo de longitude
        widget.show()
        widget.edit_lon.setFocus()
        QApplication.processEvents()
        sucesso_foco = widget.processar_texto_colado("-44.123456")
        assert sucesso_foco is True
        assert coord.longitude == -441234560

        # Colagem genérica sem foco / cardinal específico
        widget.edit_lat.clearFocus()
        widget.edit_lon.clearFocus()
        sucesso_generico = widget.processar_texto_colado("-10.123456")
        assert sucesso_generico is True
        assert coord.latitude == -101234560

        # Colagem de valor que só cabe em longitude (ex: 150.0)
        sucesso_so_lon = widget.processar_texto_colado("150.0")
        assert sucesso_so_lon is True
        assert coord.longitude == 1500000000

    def test_abrir_google_maps(self, qtbot, monkeypatch):
        coord = Coordenada()
        coord.latitude = -198980280
        coord.longitude = -435212340
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        urls = []
        from PySide6.QtGui import QDesktopServices

        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls) == 1
        assert "-19.8980280,-43.5212340" in urls[0]

    def test_abrir_google_maps_vazio_nao_abre(self, qtbot, monkeypatch):
        coord = Coordenada()
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        urls = []
        from PySide6.QtGui import QDesktopServices

        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls.append(url.toString()))

        widget.abrir_no_google_maps()
        assert len(urls) == 0

    def test_scroll_no_line_edit_nao_muda_valor(self, qtbot):
        coord = Coordenada()
        coord.latitude = -198980280
        widget = WidgetMensagemCoordenada(coord)
        qtbot.addWidget(widget)

        event = QWheelEvent(
            QPointF(10, 10),
            QPointF(10, 10),
            QPoint(0, 0),
            QPoint(0, 120),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.ScrollUpdate,
            False,
        )
        QApplication.sendEvent(widget.edit_lat, event)
        assert widget.obter_latitude_e7() == -198980280

    def test_edicao_apos_undo_que_poda_submensagem_no_pai(self, qtbot):
        from aresta_api.proto.generated.croqui_pb2 import Croqui

        croqui = Croqui(id="crq_coord_pai", nome="Croqui Coord")
        pico = croqui.picos.add(nome="Pico 1")
        setor = pico.setores_ou_grupos.add().setor.conteudo
        setor.uid = "setr0000000001"
        setor.nome = "Setor 1"

        model = CroquiModel(croqui)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        widget = WidgetMensagemCoordenada(
            setor.localizacao_estacionamento,
            controller=controller,
            model=model,
            msg_pai=setor,
            campo_pai="localizacao_estacionamento",
        )
        qtbot.addWidget(widget)

        widget.edit_lat.setText("-20")
        widget._confirmar_edicao_lat()
        assert setor.HasField("localizacao_estacionamento")
        assert setor.localizacao_estacionamento.latitude == -200000000

        # Desfazer poda a submensagem vazia no Setor pai
        undo_stack.undo()
        assert not setor.HasField("localizacao_estacionamento")
        assert widget.edit_lat.text() == ""

        # Refazer recria uma nova submensagem viva no Setor pai e atualiza o widget
        undo_stack.redo()
        assert setor.HasField("localizacao_estacionamento")
        assert widget.edit_lat.text() == "-20"

        # Desfazer novamente e editar latitude e longitude no mesmo widget sem mensagem órfã
        undo_stack.undo()
        assert not setor.HasField("localizacao_estacionamento")

        widget.edit_lat.setText("-21.5")
        widget._confirmar_edicao_lat()
        widget.edit_lon.setText("-43.5")
        widget._confirmar_edicao_lon()
        assert setor.HasField("localizacao_estacionamento")
        assert setor.localizacao_estacionamento.latitude == -215000000
        assert setor.localizacao_estacionamento.longitude == -435000000
        assert widget.btn_gerar_malha is None
        assert widget.rotulo_status_malha is None
        assert widget.gerar_malha_pontos_estrada() is False

    def test_pico_localizacao_exibe_warning_e_botao_gerar_malha_com_undo_redo(
        self, qtbot, monkeypatch
    ):
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from scripts.cliente_overpass_fake import ClienteOverpassFake

        elementos = [
            {"type": "node", "id": 100, "lat": -20.0010, "lon": -44.0010},
            {"type": "node", "id": 101, "lat": -20.0300, "lon": -44.0010},
            {"type": "way", "id": 10, "nodes": [100, 101], "tags": {"highway": "primary"}},
        ]
        fake_overpass = ClienteOverpassFake(elementos_padrao=elementos)

        croqui = Croqui(id="crq_pico_malha", nome="Croqui Malha")
        pico = croqui.picos.add(nome="Pico Malha")
        model = CroquiModel(croqui)
        undo_stack = QUndoStack()
        controller = CroquiController(model, undo_stack)

        ao_concluir_original = DialogoProgressoMalhaEstrada._ao_concluir

        def concluir_e_clicar_botao(dialogo_self, malha):
            ao_concluir_original(dialogo_self, malha)
            assert dialogo_self.btn_concluir.isEnabled() is True
            dialogo_self.btn_concluir.click()

        monkeypatch.setattr(DialogoProgressoMalhaEstrada, "_ao_concluir", concluir_e_clicar_botao)

        widget = WidgetMensagemCoordenada(
            pico.localizacao,
            controller=controller,
            model=model,
            msg_pai=pico,
            campo_pai="localizacao",
            cliente_overpass=fake_overpass,
        )
        qtbot.addWidget(widget)
        widget.show()

        # Inicialmente sem coordenadas: botão desabilitado e status oculto
        assert widget.btn_gerar_malha is not None
        assert widget.rotulo_status_malha is not None
        assert widget.btn_gerar_malha.text() == "Gerar Mapa de Pontos"
        assert widget.btn_gerar_malha.isEnabled() is False
        assert widget.rotulo_status_malha.isVisible() is False

        # Preenche apenas latitude: ainda incompleto, mas ao preencher longitude gera ou exibe status
        widget.edit_lat.setText("-20.0")
        widget._confirmar_edicao_lat()
        assert widget.btn_gerar_malha.isEnabled() is False

        # Ao preencher longitude, como cliente_overpass está configurado, gera automaticamente
        widget.edit_lon.setText("-44.0")
        widget._confirmar_edicao_lon()

        assert len(pico.malha_estrada.conteudo.nos) == 2
        assert pico.malha_estrada.conteudo.latitude_referencia_e7 == -200000000
        assert pico.malha_estrada.conteudo.longitude_referencia_e7 == -440000000
        assert "✅" in widget.rotulo_status_malha.text()
        assert widget.rotulo_status_malha.isVisible() is True
        assert widget.ultimo_dialogo_progresso is not None
        assert widget.ultimo_dialogo_progresso.barra_progresso.value() == 100
        assert "100%" in widget.ultimo_dialogo_progresso.lista_etapas.toPlainText()

        # Se a malha for limpa ou a coordenada mudar sem regerar, exibe o warning
        pico.ClearField("malha_estrada")
        widget._atualizar_status_malha_pico()
        assert "⚠️" in widget.rotulo_status_malha.text()
        assert "não gerado" in widget.rotulo_status_malha.text()

        # Clicar no botão "Gerar Mapa de Pontos" regera via controller com suporte a Undo/Redo
        widget.btn_gerar_malha.click()
        assert len(pico.malha_estrada.conteudo.nos) == 2
        assert "✅" in widget.rotulo_status_malha.text()

        # Undo desfaz a geração da malha e volta a mostrar o warning
        undo_stack.undo()
        assert len(pico.malha_estrada.conteudo.nos) == 0
        assert "⚠️" in widget.rotulo_status_malha.text()

        # Redo restaura a malha e o status positivo
        undo_stack.redo()
        assert len(pico.malha_estrada.conteudo.nos) == 2
        assert "✅" in widget.rotulo_status_malha.text()

        # Se a malha existente não tiver duracao_minutos (> 0) para nós com distancia_metros > 0, reclama!
        for no_malha in pico.malha_estrada.conteudo.nos:
            if no_malha.distancia_metros > 0:
                no_malha.duracao_minutos = 0
        widget._atualizar_status_malha_pico()
        assert "⚠️" in widget.rotulo_status_malha.text()
        assert "sem tempo em minutos" in widget.rotulo_status_malha.text()

    def test_pico_localizacao_sem_controller_e_falha_rede_degrada_graciosamente(
        self, qtbot, monkeypatch
    ):
        from aresta_api.proto.generated.croqui_pb2 import Pico
        from scripts.cliente_overpass_fake import ClienteOverpassFake

        ao_concluir_original = DialogoProgressoMalhaEstrada._ao_concluir

        def concluir_e_clicar_botao(dialogo_self, malha):
            ao_concluir_original(dialogo_self, malha)
            dialogo_self.btn_concluir.click()

        monkeypatch.setattr(DialogoProgressoMalhaEstrada, "_ao_concluir", concluir_e_clicar_botao)

        pico = Pico(nome="Pico Offline")
        pico.localizacao.latitude = -200000000
        pico.localizacao.longitude = -440000000

        fake_falha = ClienteOverpassFake(simular_erro=RuntimeError("Sem conexão com Overpass"))
        widget = WidgetMensagemCoordenada(
            pico.localizacao,
            msg_pai=pico,
            campo_pai="localizacao",
            cliente_overpass=fake_falha,
        )
        qtbot.addWidget(widget)
        widget.show()

        assert widget.btn_gerar_malha is not None
        assert "⚠️" in widget.rotulo_status_malha.text()

        # Ao clicar em gerar com falha de rede, não lança exceção e mantém o warning
        sucesso = widget.gerar_malha_pontos_estrada()
        assert sucesso is False
        assert "⚠️" in widget.rotulo_status_malha.text()
        assert len(pico.malha_estrada.conteudo.nos) == 0

        # Quando a rede volta a funcionar (sem controller, direto na msg), grava em pico.malha_estrada
        fake_falha.simular_erro = None
        fake_falha.registrar_resposta(
            -20.0,
            -44.0,
            [
                {"type": "node", "id": 100, "lat": -20.0010, "lon": -44.0010},
                {"type": "node", "id": 101, "lat": -20.0300, "lon": -44.0010},
                {"type": "way", "id": 10, "nodes": [100, 101], "tags": {"highway": "primary"}},
            ],
        )
        sucesso_ok = widget.gerar_malha_pontos_estrada()
        assert sucesso_ok is True
        assert len(pico.malha_estrada.conteudo.nos) == 2
        assert "✅" in widget.rotulo_status_malha.text()

    def test_dialogo_progresso_malha_estrada_permite_cancelar_sem_alterar_pico(self, qtbot):
        from aresta_api.proto.generated.croqui_pb2 import Pico
        from scripts.cliente_overpass_fake import ClienteOverpassFake

        pico = Pico(nome="Pico Cancelado")
        pico.localizacao.latitude = -200000000
        pico.localizacao.longitude = -440000000

        fake = ClienteOverpassFake(
            elementos_padrao=[
                {"type": "node", "id": 100, "lat": -20.0010, "lon": -44.0010},
                {"type": "node", "id": 101, "lat": -20.0300, "lon": -44.0010},
                {"type": "way", "id": 10, "nodes": [100, 101], "tags": {"highway": "primary"}},
            ]
        )
        worker = WorkerGeracaoMalhaEstrada(-200000000, -440000000, fake)
        dialogo = DialogoProgressoMalhaEstrada(worker)
        qtbot.addWidget(dialogo)

        # Solicita cancelamento pelo botão Cancelar antes/durante a execução
        dialogo.btn_cancelar.click()
        assert worker.foi_cancelado() is True
        worker.run()
        assert dialogo.resultado_malha is None
        assert len(pico.malha_estrada.conteudo.nos) == 0

        # Verifica que ao concluir 100%, o diálogo NÃO fecha sozinho e habilita o botão Concluir
        worker_ok = WorkerGeracaoMalhaEstrada(-200000000, -440000000, fake)
        dialogo_ok = DialogoProgressoMalhaEstrada(worker_ok)
        qtbot.addWidget(dialogo_ok)
        assert dialogo_ok.btn_concluir.isEnabled() is False
        assert dialogo_ok.btn_cancelar.isEnabled() is True
        worker_ok.run()
        assert dialogo_ok.resultado_malha is not None
        assert len(dialogo_ok.resultado_malha.nos) == 2
        assert dialogo_ok.result() == 0
        assert dialogo_ok.btn_cancelar.isEnabled() is False
        assert dialogo_ok.btn_concluir.isEnabled() is True
        dialogo_ok.btn_concluir.click()
        assert dialogo_ok.result() == QDialog.DialogCode.Accepted

        # Verifica que cada linha inclui timestamp + tempo decorrido e que "Recebendo malha viária..." atualiza in-place
        import re

        worker_log = WorkerGeracaoMalhaEstrada(-200000000, -440000000, fake)
        dialogo_log = DialogoProgressoMalhaEstrada(worker_log)
        qtbot.addWidget(dialogo_log)
        dialogo_log._ao_progresso("Consultando malha viária no OpenStreetMap (Overpass API)...", 15)
        dialogo_log._ao_progresso("Aguardando resposta de lz4.overpass-api.de...", 16)
        dialogo_log._ao_progresso("Recebendo malha viária de lz4.overpass-api.de (0.1 MB)...", 18)
        dialogo_log._ao_progresso("Recebendo malha viária de lz4.overpass-api.de (2.4 MB)...", 22)
        dialogo_log._ao_progresso("Recebendo malha viária de lz4.overpass-api.de (6.8 MB)...", 31)
        dialogo_log._ao_progresso(
            "Construindo grafo viário e filtrando componente principal (1200 elementos)...", 45
        )
        linhas_log = dialogo_log.lista_etapas.toPlainText().splitlines()
        assert len(linhas_log) == 4
        padrao_ts = r"^\[\d{2}:\d{2}:\d{2} \+\d+\.\ds\] "
        for linha in linhas_log:
            assert re.match(padrao_ts, linha), f"Linha sem timestamp: {linha}"
        assert linhas_log[0].endswith(
            "[15%] Consultando malha viária no OpenStreetMap (Overpass API)..."
        )
        assert linhas_log[1].endswith("[16%] Aguardando resposta de lz4.overpass-api.de...")
        assert linhas_log[2].endswith(
            "[31%] Recebendo malha viária de lz4.overpass-api.de (6.8 MB)..."
        )
        assert linhas_log[3].endswith(
            "[45%] Construindo grafo viário e filtrando componente principal (1200 elementos)..."
        )

        fake_erro = ClienteOverpassFake(simular_erro=RuntimeError("Falha simulada"))
        worker_erro = WorkerGeracaoMalhaEstrada(-200000000, -440000000, fake_erro)
        dialogo_erro = DialogoProgressoMalhaEstrada(worker_erro)
        qtbot.addWidget(dialogo_erro)
        worker_erro.run()
        assert dialogo_erro.mensagem_erro == "Falha simulada"
