# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QColor, QImage, QUndoStack
from PySide6.QtWidgets import QDialog, QSizePolicy

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.views.componentes.widget_card_mapa import WidgetCardMapa
from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa
from editor.views.tree_view_adapter import ProtobufNode


def _gerar_bytes_imagem_teste(largura: int = 64, altura: int = 48) -> bytes:
    img = QImage(largura, altura, QImage.Format.Format_RGB32)
    img.fill(QColor("forestgreen"))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")  # type: ignore[call-overload]
    return bytes(buffer.data())


class _FormularioStub:
    def __init__(self, current_node=None):
        self.current_node = current_node
        self.dirty = False
        self.tree_changed = False

    def _mark_dirty(self):
        self.dirty = True

    def _notify_tree_changed(self):
        self.tree_changed = True


def test_widget_card_mapa_inicializacao_com_imagem(qapp):
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    mapa = setor.mapas.add(
        caminho_imagem_mapa="imagens/parede_principal_p0.webp",
        largura_mapa=1920,
        altura_mapa=1080,
    )
    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/parede_principal_p0.webp", _gerar_bytes_imagem_teste())
    controller = CroquiController(model, QUndoStack())
    form = _FormularioStub(
        current_node=ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    )

    card = WidgetCardMapa(
        msg_mapa=mapa,
        indice=0,
        model=model,
        controller=controller,
        formulario=form,
        extra_path="expando:mapas/item:0",
    )

    assert card.property("repeated_index") == 0
    assert "Mapa [0]" in card.rotulo_titulo.text()
    assert "parede_principal_p0.webp" in card.rotulo_titulo.text()
    assert "imagens/parede_principal_p0.webp" in card.rotulo_arquivo.text()
    assert "1920 × 1080 px" in card.rotulo_resolucao.text()

    pixmap = card.rotulo_miniatura.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()

    assert card.alca is not None
    assert not hasattr(card, "btn_subir")
    assert not hasattr(card, "btn_descer")
    assert card.btn_remover is not None
    assert card.btn_remover.toolTip() == "Remover mapa"
    assert not card.btn_remover.icon().isNull()
    assert card.btn_abrir_editor is not None
    assert card.btn_abrir_editor.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Maximum
    assert hasattr(card, "btn_substituir_imagem")
    assert card.btn_substituir_imagem.text() == "Substituir Imagem..."


def test_widget_card_mapa_sem_imagem(qapp):
    croqui = croqui_pb2.Croqui()
    model = CroquiModel(croqui)
    mapa = croqui_pb2.Mapa(
        caminho_imagem_mapa="imagens/inexistente.webp",
        largura_mapa=0,
        altura_mapa=0,
    )

    card = WidgetCardMapa(
        msg_mapa=mapa,
        indice=1,
        model=model,
    )

    assert card.property("repeated_index") == 1
    assert "Mapa [1]" in card.rotulo_titulo.text()
    assert "Sem Imagem" in card.rotulo_miniatura.text()
    assert "Resolução não informada" in card.rotulo_resolucao.text()


def test_widget_card_mapa_definir_indice(qapp):
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/mapa1.webp")
    card = WidgetCardMapa(msg_mapa=mapa, indice=0)

    card.definir_indice(3)
    assert card.property("repeated_index") == 3
    assert "Mapa [3]" in card.rotulo_titulo.text()


def test_widget_card_mapa_abrir_no_editor_de_mapas(qapp, monkeypatch):
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    mapa = setor.mapas.add(caminho_imagem_mapa="imagens/setor.webp")
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    form = _FormularioStub(current_node=node)

    import editor.views.widget_editor_dados as wed

    monkeypatch.setattr(wed, "get_node_path", lambda _node: "expando:setores/item:0")

    focos = []
    model.foco_requisitado.connect(focos.append)

    card = WidgetCardMapa(
        msg_mapa=mapa,
        indice=0,
        model=model,
        controller=controller,
        formulario=form,
        extra_path="expando:mapas/item:0",
    )

    card.btn_abrir_editor.click()

    caminho_esperado = "page:mapas/expando:setores/item:0/expando:mapas/item:0"
    assert controller.contexto_atual_path == caminho_esperado
    assert focos == [caminho_esperado]


def test_widget_card_mapa_substituir_imagem_com_reescala_pois_e_undo(qapp, tmp_path, monkeypatch):
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    mapa = setor.mapas.add(
        caminho_imagem_mapa="imagens/setor_p0.webp",
        largura_mapa=100,
        altura_mapa=50,
    )
    poi = mapa.pontos_de_interesse.add(uid="p1", rotulo="1")
    poi.circulo.x = 40
    poi.circulo.y = 20
    poi.circulo.raio = 10

    model = CroquiModel(croqui)
    model.definir_caminho_db(tmp_path)
    model.definir_imagem_memoria("imagens/setor_p0.webp", _gerar_bytes_imagem_teste(100, 50))
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    form = _FormularioStub()

    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    card = WidgetCardMapa(
        msg_mapa=proxy_mapa,
        indice=0,
        model=model,
        controller=controller,
        formulario=form,
    )

    bytes_novos_png = _gerar_bytes_imagem_teste(200, 100)

    def fake_exec(self_dlg):
        self_dlg.carregar_imagem_bytes(bytes_novos_png, nome_sugerido_origem="setor_p0_novo.png")
        self_dlg.input_nome.setText("setor_p0_novo.webp")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(DialogoAdicionarMapa, "exec", fake_exec)

    card.btn_substituir_imagem.click()

    assert mapa.caminho_imagem_mapa == "imagens/setor_p0_novo.webp"
    assert mapa.largura_mapa == 200
    assert mapa.altura_mapa == 100
    assert mapa.pontos_de_interesse[0].circulo.x == 80
    assert mapa.pontos_de_interesse[0].circulo.y == 40
    assert "200 × 100 px" in card.rotulo_resolucao.text()
    assert form.dirty is True
    assert form.tree_changed is True

    # Undo restaura tudo e atualiza o card
    undo_stack.undo()
    assert mapa.caminho_imagem_mapa == "imagens/setor_p0.webp"
    assert mapa.largura_mapa == 100
    assert mapa.altura_mapa == 50
    assert mapa.pontos_de_interesse[0].circulo.x == 40
    assert "100 × 50 px" in card.rotulo_resolucao.text()


def test_widget_card_mapa_reage_a_imagem_alterada(qapp):
    croqui = croqui_pb2.Croqui()
    model = CroquiModel(croqui)
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/foto.webp")

    card = WidgetCardMapa(msg_mapa=mapa, indice=0, model=model)
    assert "Sem Imagem" in card.rotulo_miniatura.text()

    bytes_img = _gerar_bytes_imagem_teste()
    model.definir_imagem_memoria("imagens/foto.webp", bytes_img)
    model.imagem_alterada.emit("imagens/foto.webp")

    model.imagem_alterada.emit("imagens/outra_foto.webp")
    assert card.rotulo_miniatura.pixmap() is not None


def test_widget_card_mapa_bytes_invalidos_exibe_erro(qapp):
    croqui = croqui_pb2.Croqui()
    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/corrompida.webp", b"bytes_corrompidos_que_nao_sao_imagem")
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/corrompida.webp")

    card = WidgetCardMapa(msg_mapa=mapa, indice=0, model=model)
    assert card.rotulo_miniatura.text() == "Erro Imagem"


def test_widget_card_mapa_abrir_ou_substituir_sem_controller_ou_sem_form(qapp):
    mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/foto.webp")
    card = WidgetCardMapa(msg_mapa=mapa, indice=0)

    card.btn_abrir_editor.click()
    card.btn_substituir_imagem.click()

    croqui = croqui_pb2.Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    form = _FormularioStub(current_node=None)
    card2 = WidgetCardMapa(msg_mapa=mapa, indice=0, formulario=form, controller=controller)
    card2.btn_abrir_editor.click()
    assert controller.contexto_atual_path is None
