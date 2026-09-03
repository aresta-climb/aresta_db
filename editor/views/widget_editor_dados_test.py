# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QItemSelectionModel
import pytest
from PySide6.QtWidgets import QApplication, QTreeView, QStackedWidget, QLineEdit, QFrame, QComboBox
from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from PySide6.QtGui import QUndoStack
from editor.views.widget_editor_dados import WidgetEditorDados
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens
from editor.views.widget_editor_mapas import WidgetEditorMapas

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_widget_editor_dados_instantiation(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    
    # Verifica componentes principais
    assert isinstance(widget.tree_view, QTreeView)
    assert isinstance(widget.stacked_widget, QStackedWidget)
    assert widget.stacked_widget.count() >= 1  # Formulário padrão

def test_widget_editor_dados_routing(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    
    # Test routing to normal field/root
    widget._on_tree_selection_changed(None, None)
    # O roteamento padrão deve ser o formulário genérico
    assert widget.stacked_widget.currentIndex() == 0

def test_widget_formulario_padrao_renderizacao_campos(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipó"
    
    # Criamos o widget e carregamos o nó do Pico
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    # Procuramos o nó na árvore
    modelo = widget.tree_model
    # Sob a raiz invisível, o primeiro item é o Croqui
    croqui_idx = modelo.index(0, 0)
    # Localiza o expando Picos
    expando_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
    # Sob o expando Picos, o primeiro item é o Pico Serra do Cipó
    pico_idx = modelo.index(0, 0, expando_picos)
    pico_node = pico_idx.internalPointer()
    
    widget.form_padrao.load_node(pico_node)
    
    # Deve conter um QLineEdit para o campo 'nome'
    line_edits = widget.form_padrao.findChildren(QLineEdit)
    nomes_campos = [le.text() for le in line_edits]
    assert "Serra do Cipó" in nomes_campos

def test_widget_formulario_padrao_inline_e_borda(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipó"
    # Inicializa a localização (sub-mensagem inline)
    pico.localizacao.latitude = -190000000
    
    model = CroquiModel(croqui)
    
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    expando_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = modelo.index(0, 0, expando_picos)
    pico_node = pico_idx.internalPointer()
    
    widget.form_padrao.load_node(pico_node)
    
    # Deve conter um QFrame com nome SubMessageFrame para a coordenada inline
    frames = widget.form_padrao.findChildren(QFrame)
    frames_inline = [f for f in frames if f.objectName() == "SubMessageFrame"]
    assert len(frames_inline) >= 1

def test_widget_formulario_padrao_oneof(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor A"
    
    # Adiciona escalada
    esc = setor.escaladas.add()
    
    model = CroquiModel(croqui)
    
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    
    # Navega até o nó da Escalada na árvore
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    exp_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = modelo.index(0, 0, exp_picos)
    exp_sg = modelo.index(0, 0, pico_idx)
    setor_idx = modelo.index(0, 0, exp_sg)
    exp_esc = modelo.index(0, 0, setor_idx)
    esc_idx = modelo.index(0, 0, exp_esc)
    esc_node = esc_idx.internalPointer()
    
    widget.form_padrao.load_node(esc_node)
    
    # Deve mostrar um QComboBox para selecionar o tipo da Escalada (oneof)
    combos = widget.form_padrao.findChildren(QComboBox)
    assert len(combos) >= 1

def test_widget_editor_dados_select_root_node(qapp):
    croqui = Croqui()
    croqui.nome = "Complexo Pedra Grande"
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    
    # Seleciona o nó raiz "Croqui" na árvore
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    
    # Simula seleção na tree view
    widget.tree_view.selectionModel().select(croqui_idx, widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect)
    # Dispara o evento de seleção
    widget._on_tree_selection_changed(None, None)
    
    # Deve carregar o formulário padrão (índice 0)
    assert widget.stacked_widget.currentIndex() == 0
    
    # Deve conter um QLineEdit para o campo 'nome' com o valor configurado
    line_edits = widget.form_padrao.findChildren(QLineEdit)
    nomes_campos = [le.text() for le in line_edits]
    assert "Complexo Pedra Grande" in nomes_campos


def test_form_renderiza_botao_para_mapa(qapp):
    """[TDD] Verifica que um Mapa renderiza um botão em vez de sub-campos do Protobuf."""
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QPushButton
    
    setor = Setor()
    mapa = setor.mapas.add()
    mapa.caminho_imagem_mapa = "mapa.webp"
    
    node = ProtobufNode(name="Mapa", message=mapa, descriptor=mapa.DESCRIPTOR)
    
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)
    
    # Busca por botões
    botoes = form.findChildren(QPushButton)
    textos = [b.text() for b in botoes]
    assert "Abrir no Editor de Mapas" in textos
    
    # Garante que não renderizou outros campos (como caminho_imagem_mapa) como QLineEdit
    from PySide6.QtWidgets import QLineEdit
    line_edits = form.findChildren(QLineEdit)
    assert len(line_edits) == 0


def test_form_botao_mapa_emite_foco_requisitado(qapp):
    """[TDD] Verifica que clicar no botão do mapa emite foco_requisitado para a aba de mapas."""
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QPushButton
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico A"
    setor_grupo = pico.setores_ou_grupos.add()
    setor = setor_grupo.setor
    mapa = setor.conteudo.mapas.add()
    mapa.caminho_imagem_mapa = "mapa.webp"
    
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    
    node = ProtobufNode(name="Mapa", message=mapa, descriptor=mapa.DESCRIPTOR)
    
    form.load_node(node)
    
    botoes = form.findChildren(QPushButton)
    btn_mapa = next((b for b in botoes if b.text() == "Abrir no Editor de Mapas"), None)
    assert btn_mapa is not None

    focos_recebidos = []
    model.foco_requisitado.connect(focos_recebidos.append)
    
    # Simula o clique
    btn_mapa.clicked.emit()
    
    # Deve ter emitido o foco e setado o contexto
    assert len(focos_recebidos) == 1
    assert focos_recebidos[0] == "page:mapas/node:Mapa"
    assert controller.contexto_atual_path == focos_recebidos[0]


def test_widget_formulario_padrao_no_overlap(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipo"
    
    model = CroquiModel(croqui)
    
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    expando_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = modelo.index(0, 0, expando_picos)
    pico_node = pico_idx.internalPointer()
    
    form = widget.form_padrao
    croqui_container = form.currentWidget()
    
    # Carrega o nó Pico
    form.load_node(pico_node)
    pico_container = form.currentWidget()
    
    assert pico_container is not croqui_container
    assert form.indexOf(croqui_container) >= 0
    assert form.indexOf(pico_container) >= 0


def test_widget_editor_dados_header_hidden_and_auto_expansion(qapp):
    from PySide6.QtCore import Qt, QItemSelectionModel, QItemSelectionModel
    croqui = Croqui()
    croqui.nome = "Complexo Pedra Grande"
    
    # Adiciona botão com secao textual
    bot = croqui.botoes.add()
    bot.texto = "Capa"
    arq_md = bot.destino.secao_textual
    arq_md.caminho = "capa.md"
    
    # Adiciona pico
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipo"
    
    # Adiciona setor
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Bloco Principal"
    
    model = CroquiModel(croqui)
    
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    
    # 1. Verifica se o cabecalho esta oculto
    assert widget.tree_view.isHeaderHidden() is True
    
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    
    # 2. O no raiz (Croqui) deve estar expandido
    assert widget.tree_view.isExpanded(croqui_idx) is True
    
    # 3. O expando de botões e o pico devem estar expandidos
    exp_md_idx = modelo.index(0, 0, croqui_idx)
    assert modelo.data(exp_md_idx, Qt.ItemDataRole.DisplayRole) == "Botões"
    assert widget.tree_view.isExpanded(exp_md_idx) is True
    
    exp_picos_idx = modelo.index(1, 0, croqui_idx)
    assert modelo.data(exp_picos_idx, Qt.ItemDataRole.DisplayRole) == "Picos"
    assert widget.tree_view.isExpanded(exp_picos_idx) is True
    
    # 4. O pico deve estar expandido
    pico_idx = modelo.index(0, 0, exp_picos_idx)
    assert modelo.data(pico_idx, Qt.ItemDataRole.DisplayRole) == "Serra do Cipo"
    assert widget.tree_view.isExpanded(pico_idx) is True
    
    # 5. O expando de setores do pico deve estar expandido
    exp_sg_idx = modelo.index(0, 0, pico_idx)
    assert modelo.data(exp_sg_idx, Qt.ItemDataRole.DisplayRole) == "Setores ou grupos"
    assert widget.tree_view.isExpanded(exp_sg_idx) is True
    
    # 6. O setor em si nao deve estar expandido (e folha/nivel alvo)
    setor_idx = modelo.index(0, 0, exp_sg_idx)
    assert widget.tree_view.isExpanded(setor_idx) is False


def test_widget_formulario_padrao_oneof_default(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    # ArquivoSetor agora e ONEOF_CONTEUDO: inicializar_oneofs sempre usa o campo 'conteudo'
    # (ignora oneof_default=True do campo 'caminho', que era o comportamento antigo incorreto)
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor, Setor
    arq_setor = ArquivoSetor()

    assert arq_setor.WhichOneof("arquivo") is None

    # Executa a inicializacao
    form.inicializar_oneofs(arq_setor)

    # Com ONEOF_CONTEUDO, deve sempre inicializar 'conteudo' (Setor inline), nao 'caminho'
    assert arq_setor.WhichOneof("arquivo") == "conteudo"
    assert isinstance(arq_setor.conteudo, Setor)



def test_formulario_exibe_e_edita_nome_de_arquivo(qapp):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QLineEdit
    
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Fantastico"
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_setor_fantastico.md"
    
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    # Encontra o node
    croqui_idx = modelo.index(0, 0)
    
    # Encontra picos_idx (Expando "Picos")
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None
    
    pico_idx = modelo.index(0, 0, exp_picos_idx)
    
    # Encontra setores_ou_grupos_idx
    exp_sg_idx = None
    for r in range(modelo.rowCount(pico_idx)):
        idx = modelo.index(r, 0, pico_idx)
        if modelo.data(idx) == "Setores ou grupos":
            exp_sg_idx = idx
            break
    assert exp_sg_idx is not None
    
    setor_idx = modelo.index(0, 0, exp_sg_idx)
    
    form = widget.form_padrao
    form.load_node(setor_idx.internalPointer())
    
    # 2. Verifica se a UI renderizou o QLineEdit do nome do arquivo
    line_edits = form.findChildren(QLineEdit)
    edit_filename = next(le for le in line_edits if le.property("protobuf_field") == "__filename__")
    assert edit_filename is not None
    assert edit_filename.text() == "setor_setor_fantastico.md"
    
    # 3. Simula alteração do usuário no nome do arquivo na UI
    edit_filename.setText("setor_perfeito.md")
    edit_filename.editingFinished.emit()
    
    # Verifica se a UI usou o comando e alterou a extensão!
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_perfeito.md"


def test_formulario_usa_croqui_controller_para_caminho_novo(qapp):
    from editor.views.widget_editor_dados import WidgetEditorDados
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QLineEdit
    from unittest.mock import MagicMock
    
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor 2"
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "caminho_velho.md"
    
    from editor.models.croqui_model import CroquiModel
    model = CroquiModel(croqui)
    
    # Mock do controller
    controller = MagicMock()
    
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model
    
    # Encontra o node
    croqui_idx = modelo.index(0, 0)
    
    # Encontra picos_idx (Expando "Picos")
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None
    
    pico_idx = modelo.index(0, 0, exp_picos_idx)
    
    # Encontra setores_ou_grupos_idx
    exp_sg_idx = None
    for r in range(modelo.rowCount(pico_idx)):
        idx = modelo.index(r, 0, pico_idx)
        if modelo.data(idx) == "Setores ou grupos":
            exp_sg_idx = idx
            break
    assert exp_sg_idx is not None
    
    setor_idx = modelo.index(0, 0, exp_sg_idx)
    form = widget.form_padrao
    form.load_node(setor_idx.internalPointer())
    
    line_edits = form.findChildren(QLineEdit)
    edit_filename = next(le for le in line_edits if le.property("protobuf_field") == "__filename__")
    
    # Altera e emite o sinal
    edit_filename.setText("caminho_novissimo.md")
    edit_filename.editingFinished.emit()
    
    # Verifica se o método correto do controller foi acionado
    controller.alterar_metadados_caminho_novo.assert_called_once()
    
    args, kwargs = controller.alterar_metadados_caminho_novo.call_args
    assert args[0] == sg.setor
    assert args[1] == croqui_pb2.ArquivoSetor.ext_metadados_arquivo
    assert args[2] == "caminho_velho.md"
    assert args[3] == "caminho_novissimo.md"


def test_formulario_oneof_transparencia_primitivos(qapp):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown
    from PySide6.QtWidgets import QComboBox, QTextEdit
    
    md_msg = ArquivoMarkdown()
    md_msg.conteudo = "# Ola"
    
    node = ProtobufNode(name="Markdown", message=md_msg, descriptor=md_msg.DESCRIPTOR)
    
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)
    
    # 1. Não deve ter QComboBox para o oneof, pois mostramos apenas o campo ativo diretamente
    combos = form.findChildren(QComboBox)
    assert len(combos) == 0
    
    # 2. Deve ter o editor de texto (QTextEdit) para a string de conteudo
    text_edits = form.findChildren(QTextEdit)
    assert len(text_edits) > 0


def test_formulario_markdown_editor_split(qapp):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QTextEdit, QTextBrowser
    
    setor = Setor()
    setor.descricao = "Descricao inicial"
    
    # Campo descricao de Setor tem conteudo_markdown = true
    field = Setor.DESCRIPTOR.fields_by_name["descricao"]
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)
    
    # Deve encontrar o WidgetEditorMarkdown
    md_editors = form.findChildren(WidgetEditorMarkdown)
    assert len(md_editors) == 1
    
    md_editor = md_editors[0]
    
    # Deve ter editor (QTextEdit) e preview (QTextBrowser)
    assert isinstance(md_editor.editor, QTextEdit)
    assert isinstance(md_editor.preview, QTextBrowser)
    
    # Altera texto no editor e verifica se atualizou o preview e o protobuf
    md_editor.editor.setPlainText("Novo **markdown**")
    md_editor.forcar_consolidacao()
    assert md_editor.preview.toPlainText().strip() == "Novo markdown"  # renderizado (HTML/rich text de-formatted to plain text is "Novo markdown")
    assert setor.descricao == "Novo **markdown**"


def test_markdown_editor_frontmatter_and_base_url(qapp):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QWidget
    
    # 1. Cria uma janela mock com caminho_croqui
    class MockWindow(QWidget):
        def __init__(self):
            super().__init__()
            from pathlib import Path
            self.caminho_croqui = Path("C:/test_croqui_folder")
    
    win = MockWindow()
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller, parent=win)
    
    setor = Setor()
    setor.descricao = """---
nome: Setor Fantasma
---
Este é o corpo do markdown.
"""
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    form.load_node(node)
    
    md_editor = form.findChild(WidgetEditorMarkdown)
    assert md_editor is not None
    
    # O editor deve conter todo o texto (incluindo o frontmatter)
    assert "nome: Setor Fantasma" in md_editor.editor.toPlainText()
    
    # O preview deve ter pulado o frontmatter
    assert "nome: Setor Fantasma" not in md_editor.preview.toPlainText()
    assert "Este é o corpo do markdown." in md_editor.preview.toPlainText()
    
    # O base URL do preview deve ter sido definido apontando para o caminho do banco de dados
    base_url = md_editor.preview.document().baseUrl().toLocalFile()
    assert base_url.rstrip("/") == "C:/test_croqui_folder/database"


def test_markdown_editor_base_url_from_model_and_local_image(qapp, tmp_path):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack, QImage
    from PySide6.QtWidgets import QWidget

    # Cria pasta de imagens com uma imagem WebP real
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    caminho_foto = pasta_imagens / "foto_teste.webp"
    
    img = QImage(200, 100, QImage.Format.Format_RGB32)
    img.fill(0xFF00FF)
    img.save(str(caminho_foto), "WEBP")

    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, QUndoStack())
    
    # Parent sem qualquer caminho_croqui
    parent_simples = QWidget()
    form = WidgetFormularioPadrao(model, controller, parent=parent_simples)
    
    setor = Setor()
    setor.descricao = "Texto com imagem: ![Minha Foto](imagens/foto_teste.webp)"
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    form.load_node(node)
    
    md_editor = form.findChild(WidgetEditorMarkdown)
    assert md_editor is not None
    
    # Verifica que o baseUrl aponta para tmp_path
    base_url = md_editor.preview.document().baseUrl().toLocalFile()
    assert base_url.replace("\\", "/").rstrip("/") == str(tmp_path).replace("\\", "/").rstrip("/")
    
    # Dispara redimensionamento para testar scale_images
    md_editor.preview.resize(400, 300)
    md_editor.preview.scale_images()



def test_markdown_editor_image_auto_scaling(qapp):
    from editor.views.widget_editor_dados import AutoScalingTextBrowser
    from PySide6.QtCore import QUrl, QSize
    from PySide6.QtGui import QImage
    
    tb = AutoScalingTextBrowser()
    tb.setFixedSize(200, 150) # Very narrow viewport
    
    tb.setMarkdown("![Large Image](imagens/test_large.png)")
    
    # Mock a large image resource in document
    img = QImage(QSize(1000, 600), QImage.Format.Format_RGB32)
    img_url = QUrl("imagens/test_large.png")
    tb.document().addResource(tb.document().ResourceType.ImageResource, img_url, img)
    
    # Force layout and scaling
    tb.scale_images()
    
    # Check the format width of the image inside the document
    doc = tb.document()
    block = doc.begin()
    found = False
    while block.isValid():
        char_it = block.begin()
        while not char_it.atEnd():
            fragment = char_it.fragment()
            if fragment.isValid():
                fmt = fragment.charFormat()
                if fmt.isImageFormat():
                    img_fmt = fmt.toImageFormat()
                    assert img_fmt.width() < 1000
                    # Viewport width is usually resize width minus scrollbar/margins
                    assert img_fmt.width() == tb.viewport().width() - 24
                    found = True
            char_it += 1
        block = block.next()
        
    assert found is True

def test_arvore_indentacao_12px(qapp):
    """Verifica que a árvore está configurada com indentação de 12px."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    assert widget.tree_view.indentation() == 12


def test_formulario_campo_invisivel_nao_renderizado(qapp):
    """Campos com formato_na_ui = INVISIVEL não devem aparecer no formulário."""
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QLineEdit

    # Croqui tem o campo 'arquivos_externos' com formato_na_ui = INVISIVEL.
    # Ao renderizar o formulário do Croqui, nenhum widget deve ser criado para esse campo.
    croqui = Croqui()
    croqui.nome = "Croqui Teste"
    # Adiciona um arquivo externo para garantir que, se renderizado, apareceria na UI
    arq = croqui.arquivos_externos.add()
    arq.caminho = "foto.jpg"

    node = ProtobufNode(name="Croqui", message=croqui, descriptor=croqui.DESCRIPTOR)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)

    # Busca todos os QLineEdit presentes - não deve haver nenhum com "foto.jpg"
    line_edits = form.findChildren(QLineEdit)
    textos = [le.text() for le in line_edits]
    assert "foto.jpg" not in textos


def test_formulario_campos_em_cards_qframe(qapp):
    """Cada campo renderizado deve estar dentro de um QFrame com objectName 'CardCampo'."""
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from aresta_api.proto.generated.croqui_pb2 import Pico

    pico = Pico()
    pico.nome = "Pico Teste"

    node = ProtobufNode(name="Pico", message=pico, descriptor=pico.DESCRIPTOR)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)

    # Deve haver ao menos um QFrame com objectName 'CardCampo'
    frames = form.findChildren(QFrame)
    cards = [f for f in frames if f.objectName() == "CardCampo"]
    assert len(cards) >= 1


def test_formulario_primitivo_largura_maxima(qapp):
    """Widgets primitivos (QSpinBox, QLineEdit curto) devem ter largura máxima definida."""
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from aresta_api.proto.generated.croqui_pb2 import Pico
    from PySide6.QtWidgets import QSpinBox

    pico = Pico()
    node = ProtobufNode(name="Pico", message=pico, descriptor=pico.DESCRIPTOR)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)

    # QLineEdit de campos primitivos curtos deve ter max-width <= 450
    line_edits = form.findChildren(QLineEdit)
    # Exclui o QLineEdit interno de QSpinBox e de WidgetEditorMarkdown
    from editor.views.widget_editor_dados import WidgetEditorMarkdown
    editores_md = form.findChildren(WidgetEditorMarkdown)
    line_edits_md = []
    for md in editores_md:
        line_edits_md.extend(md.findChildren(QLineEdit))

    primitivos = [
        le for le in line_edits
        if le not in line_edits_md and not isinstance(le.parent(), QSpinBox)
    ]
    for le in primitivos:
        assert le.maximumWidth() <= 450, f"QLineEdit sem max-width controlada: {le.maximumWidth()}"



def test_menu_contexto_adicionar_item_repeated(qapp, monkeypatch):
    """Menu de contexto em nó expando deve adicionar novo item à coleção Protobuf."""
    from editor.views.dialogos.dialogo_criar_pico import DialogoCriarPico
    from editor.views.widget_editor_dados import WidgetEditorDados
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    monkeypatch.setattr(
        DialogoCriarPico,
        "obter_dados",
        lambda *args, **kwargs: ("Novo Pico Mock", True)
    )

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Existente"

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    # Localiza o expando de picos
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None

    # Confirma que existe apenas 1 pico antes do menu
    qtd_antes = len(croqui.picos)
    assert qtd_antes == 1

    # Seleciona o nó expando e dispara o menu de contexto via método público
    widget.tree_view.selectionModel().select(
        exp_picos_idx,
        widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect
    )
    widget._executar_adicionar_item(exp_picos_idx)

    # Verifica que foi adicionado um pico
    assert len(croqui.picos) == qtd_antes + 1


def test_menu_contexto_remover_item_repeated(qapp):
    """Menu de contexto em item filho deve remover o item da coleção Protobuf."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    pico_a = croqui.picos.add()
    pico_a.nome = "Pico A"
    pico_b = croqui.picos.add()
    pico_b.nome = "Pico B"

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None

    # Seleciona o primeiro pico filho
    pico_idx = modelo.index(0, 0, exp_picos_idx)
    widget.tree_view.selectionModel().select(
        pico_idx,
        widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect
    )

    qtd_antes = len(croqui.picos)
    widget._executar_remover_item(pico_idx)
    assert len(croqui.picos) == qtd_antes - 1


def test_menu_contexto_mover_item_para_cima(qapp):
    """Menu de contexto deve mover um item para cima na coleção."""
    croqui = Croqui()
    pico_a = croqui.picos.add()
    pico_a.nome = "Pico A"
    pico_b = croqui.picos.add()
    pico_b.nome = "Pico B"

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None

    # Seleciona o segundo pico (índice 1) e move para cima
    pico_b_idx = modelo.index(1, 0, exp_picos_idx)
    widget._executar_mover_para_cima(pico_b_idx)

    # Após mover, "Pico B" deve ser o primeiro
    assert croqui.picos[0].nome == "Pico B"
    assert croqui.picos[1].nome == "Pico A"


def test_no_virtual_adicao_cria_e_seleciona(qapp, monkeypatch):
    """Nó virtual de adição deve criar um novo item e selecioná-lo na árvore."""
    from editor.views.dialogos.dialogo_criar_pico import DialogoCriarPico
    from editor.views.tree_view_adapter import ProtobufNode

    monkeypatch.setattr(
        DialogoCriarPico,
        "obter_dados",
        lambda *args, **kwargs: ("Novo Pico Virtual", True)
    )

    croqui = Croqui()
    # Adiciona um pico para que o expando exista na árvore
    pico_inicial = croqui.picos.add()
    pico_inicial.nome = "Pico Inicial"
    assert len(croqui.picos) == 1

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    widget.tree_view.expand(croqui_idx)

    # Localiza o expando de Picos
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None

    widget.tree_view.expand(exp_picos_idx)

    # O último filho do expando deve ser o nó virtual de adição
    total_filhos = modelo.rowCount(exp_picos_idx)
    assert total_filhos >= 2  # ao menos o pico + o nó '+'
    no_adicao_idx = modelo.index(total_filhos - 1, 0, exp_picos_idx)
    no_adicao = no_adicao_idx.internalPointer()
    assert no_adicao is not None
    assert hasattr(no_adicao, 'eh_no_adicao')
    # Simula clique do usuário no nó virtual — deve criar um pico
    widget._on_tree_clicked(no_adicao_idx)

    # Mais um pico deve ter sido criado (total: 2)
    assert len(croqui.picos) == 2




def test_mover_item_para_cima_atualiza_formulario(qapp):
    """Apos mover um item para cima, o formulario deve exibir os dados do item movido.

    Regressao: apos mover, o formulario continuava mostrando os dados do item na
    posicao antiga, porque a selecao nao era atualizada para a nova posicao.
    """
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Botao

    croqui = Croqui()
    md_a = croqui.botoes.add()
    md_a.texto = "Primeiro"
    md_a.destino.secao_textual.conteudo = "# Primeiro"
    md_a.destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = "doc_primeiro.md"
    
    md_b = croqui.botoes.add()
    md_b.texto = "Segundo"
    md_b.destino.secao_textual.conteudo = "# Segundo"
    md_b.destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = "doc_segundo.md"

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    widget.tree_view.expand(croqui_idx)

    # Localiza o expando de Botões
    exp_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Botões":
            exp_idx = idx
            break
    assert exp_idx is not None

    widget.tree_view.expand(exp_idx)

    # Seleciona o segundo item (indice 1) e move para cima
    idx_segundo = modelo.index(1, 0, exp_idx)
    widget._executar_mover_para_cima(idx_segundo)

    # Apos mover, o segundo md deve estar na posicao 0
    assert croqui.botoes[0].destino.secao_textual.conteudo == "# Segundo"
    assert croqui.botoes[1].destino.secao_textual.conteudo == "# Primeiro"

    # O item selecionado na arvore deve ser o que foi movido (agora na posicao 0)
    indexes = widget.tree_view.selectionModel().selectedIndexes()
    assert len(indexes) == 1
    no_selecionado = indexes[0].internalPointer()
    assert no_selecionado is not None
    assert no_selecionado.index_in_repeated == 0
    # O conteudo da mensagem no no selecionado deve ser "# Segundo"
    assert no_selecionado.message.destino.secao_textual.conteudo == "# Segundo"

def test_adicionar_setor_ou_grupo_mostra_form_proto_nao_markdown(qapp, monkeypatch):

    """Ao adicionar um novo SetorOuGrupo, o formulario deve exibir o form proto,
    nao um editor de Markdown.

    Regressao: apos clicar em '+ Adicionar Setor Ou Grupo', o painel direito
    abria um WidgetEditorMarkdown vazio em vez do formulario do proto adicionado.
    """
    from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown
    from editor.views.widget_editor_dados import WidgetEditorMarkdown

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Teste"
    # Adiciona um setor existente para que o expando "Setores ou grupos" exista
    sg_existente = pico.setores_ou_grupos.add()
    sg_existente.setor.conteudo.nome = "Setor Existente"

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    widget.tree_view.expand(croqui_idx)

    # Localiza o expando "Picos"
    picos_exp = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            picos_exp = idx
            break
    assert picos_exp is not None, "Expando 'Picos' nao encontrado"
    widget.tree_view.expand(picos_exp)

    # Localiza o Pico
    pico_idx = modelo.index(0, 0, picos_exp)
    widget.tree_view.expand(pico_idx)

    # Localiza o expando "Setores ou grupos"
    sg_exp = None
    for r in range(modelo.rowCount(pico_idx)):
        idx = modelo.index(r, 0, pico_idx)
        node = idx.internalPointer()
        if node and node.is_expando and "etor" in (modelo.data(idx) or ""):
            sg_exp = idx
            break
    assert sg_exp is not None, "Expando 'Setores ou grupos' nao encontrado"
    widget.tree_view.expand(sg_exp)

    # Localiza o no virtual de adicao (ultimo filho do expando)
    total_filhos = modelo.rowCount(sg_exp)
    no_virtual_idx = modelo.index(total_filhos - 1, 0, sg_exp)
    no_virtual = no_virtual_idx.internalPointer()
    assert no_virtual is not None and no_virtual.eh_no_adicao, "No virtual de adicao nao encontrado"

    # Mocka o DialogoCriarSetorOuGrupo para retornar setor sem bloquear a UI
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo
    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: ("setor", "Novo Setor", "setor_novo.md", True)
    )

    # Executa o adicionar
    widget._executar_adicionar_item(no_virtual_idx)

    # Deve ter adicionado um novo SetorOuGrupo
    assert len(pico.setores_ou_grupos) == 2, "Novo SetorOuGrupo nao foi adicionado"

    # Apos adicionar, o stacked_widget deve estar no form padrao (indice 0)
    assert widget.stacked_widget.currentIndex() == 0, (
        "stacked_widget deveria estar no form padrao (indice 0), "
        f"mas esta em {widget.stacked_widget.currentIndex()}"
    )

    # O form padrao deve conter o formulário proto com o campo nome do Setor
    container = widget.form_padrao.currentWidget()
    assert container is not None
    line_edits = container.findChildren(QLineEdit)
    assert any(le.property("protobuf_field") == "nome" for le in line_edits)

    # O node selecionado NAO deve ser um no virtual nem ter message=ArquivoMarkdown
    indexes = widget.tree_view.selectionModel().selectedIndexes()
    if indexes:
        no_selecionado = indexes[0].internalPointer()
        assert no_selecionado is not None
        assert not no_selecionado.eh_no_adicao, "No virtual foi selecionado apos adicionar"
        if no_selecionado.message is not None:
            assert not isinstance(no_selecionado.message, ArquivoMarkdown), (
                "Mensagem selecionada eh ArquivoMarkdown, deveria ser SetorOuGrupo"
            )


def test_inicializar_oneofs_oneof_conteudo_auto_inicializa_conteudo_sem_dialog(qapp):
    """Para mensagens ONEOF_CONTEUDO, inicializar_oneofs deve popular o campo
    'conteudo' sem abrir nenhum dialog interativo.

    Regressao: ArquivoSetor era inicializado com 'caminho' (mime_type=text/markdown),
    causando abertura do WidgetEditorMarkdown incorretamente.
    """
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor, ArquivoGrupo, ArquivoMarkdown, Setor, Grupo
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)

    # ArquivoSetor: ONEOF_CONTEUDO. Deve inicializar 'conteudo' (Setor), nao 'caminho'.
    arq_setor = ArquivoSetor()
    form.inicializar_oneofs(arq_setor)
    assert arq_setor.WhichOneof("arquivo") == "conteudo", (
        "ArquivoSetor deve ser inicializado com 'conteudo' (inline Setor), "
        f"mas WhichOneof retornou '{arq_setor.WhichOneof('arquivo')}'"
    )
    assert isinstance(arq_setor.conteudo, Setor)

    # ArquivoGrupo: ONEOF_CONTEUDO. Deve inicializar 'conteudo' (Grupo), nao 'caminho'.
    arq_grupo = ArquivoGrupo()
    form.inicializar_oneofs(arq_grupo)
    assert arq_grupo.WhichOneof("arquivo") == "conteudo", (
        "ArquivoGrupo deve ser inicializado com 'conteudo' (inline Grupo), "
        f"mas WhichOneof retornou '{arq_grupo.WhichOneof('arquivo')}'"
    )
    assert isinstance(arq_grupo.conteudo, Grupo)

    # ArquivoMarkdown: ONEOF_CONTEUDO. Deve inicializar 'conteudo' (string), nao 'caminho'.
    arq_md = ArquivoMarkdown()
    form.inicializar_oneofs(arq_md)
    assert arq_md.WhichOneof("arquivo") == "conteudo", (
        "ArquivoMarkdown deve ser inicializado com 'conteudo' (string markdown), "
        f"mas WhichOneof retornou '{arq_md.WhichOneof('arquivo')}'"
    )


def test_mover_item_para_cima_mantem_caminho_correto(qapp):
    """Verifica que ao mover um item para cima na árvore, as extensões
    (Shadow State) acompanham o conteúdo.
    """
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Botao

    croqui = Croqui()
    md_a = croqui.botoes.add()
    md_a.texto = "Primeiro"
    md_a.destino.secao_textual.conteudo = "# Primeiro"
    md_a.destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = "doc_primeiro.md"
    
    md_b = croqui.botoes.add()
    md_b.texto = "Segundo"
    md_b.destino.secao_textual.conteudo = "# Segundo"
    md_b.destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = "doc_segundo.md"

    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    widget.tree_view.expand(croqui_idx)

    exp_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Botões":
            exp_idx = idx
            break
    assert exp_idx is not None

    widget.tree_view.expand(exp_idx)

    # Seleciona o segundo item (indice 1) e move para cima
    idx_segundo = modelo.index(1, 0, exp_idx)
    widget._executar_mover_para_cima(idx_segundo)

    # Apos mover:
    assert croqui.botoes[0].destino.secao_textual.conteudo == "# Segundo"
    assert croqui.botoes[1].destino.secao_textual.conteudo == "# Primeiro"

    assert croqui.botoes[0].destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo == "doc_segundo.md"
    assert croqui.botoes[1].destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo == "doc_primeiro.md"

def test_widget_formulario_padrao_on_campo_alterado(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Original"
    
    # Criamos o widget e carregamos o Pico
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    exp_picos = next(modelo.index(r, 0, croqui_idx) for r in range(modelo.rowCount(croqui_idx)) if modelo.data(modelo.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = modelo.index(0, 0, exp_picos)
    pico_node = pico_idx.internalPointer()
    
    form = widget.form_padrao
    form.load_node(pico_node)
    
    # Encontra QLineEdit do nome no widget ativo
    line_edits = form.currentWidget().findChildren(QLineEdit)
    edit_nome = next(le for le in line_edits if le.property("protobuf_field") == "nome")
    assert edit_nome.text() == "Pico Original"
    
    # Dispara slot reativo
    form._on_campo_alterado(id(pico), "nome", "Pico Reativo")
    
    # Deve atualizar o texto in-place
    assert edit_nome.text() == "Pico Reativo"
    
def test_container_repeated_widget_reactive_updates(qapp):
    from editor.views.widget_editor_dados import ContainerRepeatedWidget
    from aresta_api.proto.generated.croqui_pb2 import Pico
    croqui = Croqui()
    pico1 = croqui.picos.add()
    pico1.nome = "Pico Um"
    
    model = CroquiModel(croqui)
    
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    # Cria o ContainerRepeatedWidget
    field_descriptor = croqui.DESCRIPTOR.fields_by_name["picos"]
    container = ContainerRepeatedWidget(croqui, field_descriptor, form)
    
    # Inicialmente, tem 1 pico
    assert container.items_layout.count() == 1
    w_pico1 = container.items_layout.itemAt(0).widget()
    assert w_pico1.property("repeated_index") == 0
    
    # 1. Simula adição reativa de um segundo pico na posição 0
    pico0 = Pico(nome="Pico Zero")
    croqui.picos.insert(0, pico0)
    container._on_item_adicionado(croqui, "picos", 0)
    
    # Deve agora ter 2 itens no layout
    assert container.items_layout.count() == 2
    
    # Verifica que w_pico1 foi deslocado para o índice 1
    assert w_pico1.property("repeated_index") == 1
    
    # Verifica que o novo widget foi inserido na posição 0
    w_pico0 = container.items_layout.itemAt(0).widget()
    assert w_pico0.property("repeated_index") == 0
    
    # 2. Simula remoção reativa do item do índice 0 (Pico Zero)
    croqui.picos.pop(0)
    container._on_item_removido(croqui, "picos", 0)
    
    # Deve voltar a ter 1 item no layout
    assert container.items_layout.count() == 1
    
    # O w_pico1 deve voltar a ter repeated_index == 0
    assert w_pico1.property("repeated_index") == 0
def test_menu_contexto_mover_item_para_baixo(qapp):
    """Menu de contexto deve mover um item para baixo na coleção."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from editor.views.widget_editor_dados import WidgetEditorDados

    croqui = Croqui()
    pico_a = croqui.picos.add()
    pico_a.nome = "Pico A"
    pico_b = croqui.picos.add()
    pico_b.nome = "Pico B"

    model = CroquiModel(croqui)

    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    croqui_idx = modelo.index(0, 0)
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None

    # Seleciona o primeiro pico (índice 0) e move para baixo
    pico_a_idx = modelo.index(0, 0, exp_picos_idx)
    widget._executar_mover_para_baixo(pico_a_idx)

    # Após mover, "Pico B" deve ser o primeiro
    assert croqui.picos[0].nome == "Pico B"
    assert croqui.picos[1].nome == "Pico A"


def test_widget_formulario_padrao_estrutura_campo_alterada(qapp):
    """Garante que campos de formulário não possuem botões Adicionar/Remover e são editáveis diretamente."""
    from editor.views.widget_editor_dados import get_node_path, WidgetEditorDados, _get_id
    from editor.views.tree_view_adapter import ProtobufNode
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QPushButton, QComboBox, QLineEdit
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    setor = Setor()
    model = CroquiModel(setor)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)
    
    # Pega o container do 'amigavel_a_criancas'
    container_info = widget.form_padrao.field_containers.get((_get_id(setor), "amigavel_a_criancas"))
    assert container_info is not None
    layout, container, desc, msg = container_info
    
    # Não deve existir nenhum botão Adicionar ou Remover
    botoes = [btn.text() for btn in container.findChildren(QPushButton)]
    assert "Adicionar" not in botoes
    assert "Remover" not in botoes
    
    # Deve existir um QComboBox para o booleano
    combos = container.findChildren(QComboBox)
    assert len(combos) == 1
    combo = combos[0]
    assert combo.count() == 3
    assert combo.currentIndex() == 0  # "Não informado"
    
    # Altera para "Adequado para crianças" (True)
    combo.setCurrentIndex(1)
    qapp.processEvents()
    assert setor.HasField("amigavel_a_criancas")
    assert setor.amigavel_a_criancas is True
    
    # Volta para "Não informado" (None)
    combo.setCurrentIndex(0)
    qapp.processEvents()
    assert not setor.HasField("amigavel_a_criancas")


def test_widget_formulario_submensagem_coordenada_sem_botoes(qapp):
    """Garante que submensagens inline como Coordenada são renderizadas diretamente
    sem botões Adicionar/Remover e são limpas quando os campos ficam vazios."""
    from editor.views.widget_editor_dados import WidgetEditorDados, _get_id
    from editor.views.tree_view_adapter import ProtobufNode
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PySide6.QtWidgets import QPushButton, QLineEdit
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    setor = Setor()
    model = CroquiModel(setor)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)
    
    container_info = widget.form_padrao.field_containers.get((_get_id(setor), "localizacao_estacionamento"))
    assert container_info is not None
    layout, container, desc, msg = container_info
    
    # Não deve ter botões Adicionar/Remover
    botoes = [btn.text() for btn in container.findChildren(QPushButton)]
    assert "Adicionar" not in botoes
    assert "Remover" not in botoes
    
    # Deve conter campos de entrada para Latitude e Longitude
    line_edits = container.findChildren(QLineEdit)
    assert len(line_edits) >= 2


def test_widget_formulario_padrao_oneof_conteudo_renderizacao(qapp):
    """Garante que a renderizacao de uma mensagem ONEOF_CONTEUDO via _render_message_fields
    nao crie um QComboBox do oneof, mas sim renderize seu conteudo diretamente."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, ArquivoSetor
    from PySide6.QtWidgets import QComboBox, QVBoxLayout, QWidget
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from editor.views.widget_editor_dados import WidgetEditorDados
    
    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    arq_setor = ArquivoSetor()
    arq_setor.conteudo.nome = "Setor Teste ONEOF CONTEUDO"
    
    container = QWidget()
    layout = QVBoxLayout(container)
    form._render_message_fields(arq_setor, layout)
    
    comboboxes = container.findChildren(QComboBox)
    oneof_combos = [cb for cb in comboboxes if cb.property("protobuf_oneof") == "tipo_conteudo"]
    assert len(oneof_combos) == 0, "Nao deveria existir combobox de seleção para ONEOF_CONTEUDO"
    assert any(le.property("protobuf_field") == "nome" for le in container.findChildren(QLineEdit))

def test_on_campo_alterado_spinbox_typeerror_regression(qapp):
    """Garante que _on_campo_alterado não quebra com TypeError ao atualizar
    QSpinBox (que exige int) e QDoubleSpinBox (que exige float) com valores mistos (ex: float ou string de undo)."""
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox, QVBoxLayout
    
    croqui = Croqui()
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    
    # Cria os componentes layout do form base
    if not form.layout:
        form.layout = QVBoxLayout()
        form.setLayout(form.layout)
    
    # Simula spinboxes registrados como filhos do formulário
    spin_int = QSpinBox(parent=form)
    spin_int.setProperty("protobuf_field", "campo_int")
    spin_int.setProperty("protobuf_msg_id", 123)
    
    spin_double = QDoubleSpinBox(parent=form)
    spin_double.setProperty("protobuf_field", "campo_double")
    spin_double.setProperty("protobuf_msg_id", 123)
    
    # 1. Teste para QSpinBox com um float (simulando um float vindo do undo que antes causava TypeError)
    try:
        form._on_campo_alterado(123, "campo_int", 42.0)
    except TypeError as e:
        import pytest
        pytest.fail(f"TypeError levantado no QSpinBox: {e}")
        
    assert spin_int.value() == 42
    
    # 2. Teste para QDoubleSpinBox com int ou string numérico
    try:
        form._on_campo_alterado(123, "campo_double", 42)
        assert spin_double.value() == 42.0
        
        form._on_campo_alterado(123, "campo_double", "45.5")
    except TypeError as e:
        import pytest
        pytest.fail(f"TypeError levantado no QDoubleSpinBox: {e}")
        
    assert spin_double.value() == 45.5


def test_container_repeated_widget_mover_item(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
    from editor.views.widget_editor_dados import WidgetEditorDados, ContainerRepeatedWidget
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    croqui.picos.extend([Pico(nome='P1'), Pico(nome='P2'), Pico(nome='P3')])
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())

    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    # Cria o ContainerRepeatedWidget
    field_descriptor = croqui.DESCRIPTOR.fields_by_name['picos']
    container = ContainerRepeatedWidget(croqui, field_descriptor, form)

    assert container.items_layout.count() == 3
    w0 = container.items_layout.itemAt(0).widget()
    w1 = container.items_layout.itemAt(1).widget()
    w2 = container.items_layout.itemAt(2).widget()

    assert w0.property('repeated_index') == 0
    assert w1.property('repeated_index') == 1
    assert w2.property('repeated_index') == 2

    # Move 0 -> 2
    croqui.picos.pop(0)
    croqui.picos.insert(2, Pico(nome='P1'))
    container._on_item_movido(croqui, 'picos', 0, 2)

    assert container.items_layout.count() == 3
    # The widget instances should be preserved
    assert container.items_layout.itemAt(0).widget() is w1
    assert container.items_layout.itemAt(1).widget() is w2

    assert container.items_layout.itemAt(2).widget() is w0

    assert w1.property('repeated_index') == 0
    assert w2.property('repeated_index') == 1
    assert w0.property('repeated_index') == 2


def test_container_repeated_evita_flash_janela_remocao(qapp):
    from editor.views.widget_editor_dados import ContainerRepeatedWidget
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QWidget
    from unittest.mock import patch

    croqui = Croqui()
    croqui.creditos.extend(["Item 1"])
    field = croqui.DESCRIPTOR.fields_by_name["creditos"]
    
    class MockFormulario:
        model = None
        controller = None
    
    container = ContainerRepeatedWidget(croqui, field, MockFormulario(), None)
    container._renderizar_item_no_indice(0)
    
    with patch.object(QWidget, 'hide') as spy_hide:
        # Simula a remoção
        container._on_item_removido(croqui, "creditos", 0)
        
        # Deve chamar hide no item removido para evitar o flash no Windows
        assert spy_hide.call_count >= 1

def test_widget_formulario_padrao_evita_flash_janela_limpeza_layout(qapp):
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from unittest.mock import patch

    croqui = Croqui()
    field = croqui.DESCRIPTOR.fields_by_name["nome"]
    
    form = WidgetFormularioPadrao(None, None)
    
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # Cria um item com widget interno
    w = QWidget()
    layout.addWidget(w)
    
    # Cria um item com layout aninhado
    nested_layout = QHBoxLayout()
    layout.addLayout(nested_layout)
    
    with patch.object(QWidget, 'hide') as spy_hide:
        # Limpa layout simulando render_field_inner
        form._render_field_inner(croqui, field, layout, container)
        
        # Deve ter chamado hide no widget E no widget dummy (layout cleaner)
        assert spy_hide.call_count >= 1

def test_undo_redo_navegacao_foco(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Original"
    setor = pico.setores_ou_grupos.add()
    setor.setor.conteudo.nome = "Setor A"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    # Seleciona o Pico e edita
    croqui_idx = modelo.index(0, 0)
    widget.tree_view.expand(croqui_idx)
    
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None
    widget.tree_view.expand(exp_picos_idx)

    pico_idx = modelo.index(0, 0, exp_picos_idx)
    widget.tree_view.selectionModel().select(pico_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    
    # O contexto deve ser o pico
    from editor.views.widget_editor_dados import get_node_path
    assert controller.contexto_atual_path == "page:dados/" + get_node_path(pico_idx.internalPointer())

    # Executa uma alteração
    controller.alterar_primitivo(pico, "nome", "Pico Original", "Pico Editado")

    # Muda a seleção para o Setor
    widget.tree_view.expand(pico_idx)
    sg_exp = None
    for r in range(modelo.rowCount(pico_idx)):
        idx = modelo.index(r, 0, pico_idx)
        node = idx.internalPointer()
        if node and node.is_expando and "etor" in (modelo.data(idx) or ""):
            sg_exp = idx
            break
    assert sg_exp is not None
    widget.tree_view.expand(sg_exp)

    setor_idx = modelo.index(0, 0, sg_exp)
    widget.tree_view.selectionModel().select(setor_idx, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    widget._on_tree_selection_changed(None, None)
    
    # Verifica que estamos no setor
    indexes = widget.tree_view.selectionModel().selectedIndexes()
    assert indexes[0] == setor_idx
    

    # Desfaz a alteração do pico!
    undo_stack.undo()

    # O foco deve voltar para o pico
    indexes = widget.tree_view.selectionModel().selectedIndexes()
    assert indexes[0].data() == "Pico Original"

    # Refaz a alteração
    undo_stack.redo()

    # O foco deve continuar no pico (pois o undo/redo do pico solicita foco para ele)
    indexes = widget.tree_view.selectionModel().selectedIndexes()
    assert indexes[0].data() == "Pico Editado"

def test_exclusao_nao_dispara_adicao_automatica(qapp, monkeypatch):
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.widget_editor_dados import _get_id
    from PySide6.QtGui import QUndoStack
    from PySide6.QtCore import QModelIndex

    croqui = Croqui()
    pico1 = croqui.picos.add()
    pico1.nome = "Pico 1"
    
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    widget.show()

    widget.expandir_arvore_ate_alvos()

    exp_picos_idx = widget.tree_model.find_expando_index(_get_id(widget.croqui), "picos")
    assert exp_picos_idx.isValid(), "Expando Picos nao encontrado"
    
    widget.tree_view.expand(exp_picos_idx)

    pico_idx = widget.tree_model.index(0, 0, exp_picos_idx)
    assert pico_idx.isValid() and pico_idx.internalPointer().name == "[0]", "Pico 1 nao encontrado"
    
    widget.tree_view.setCurrentIndex(pico_idx)
    widget.tree_view.selectionModel().select(
        pico_idx, 
        widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect
    )
    qapp.processEvents()
    
    widget._executar_remover_item(pico_idx)
    qapp.processEvents()

    assert len(croqui.picos) == 0, "A exclusao disparou uma adicao automatica!"

    selected_indexes_after = widget.tree_view.selectionModel().selectedIndexes()
    assert len(selected_indexes_after) == 0, "A selecao permaneceu travada no no de adicao"

def test_repeated_fields_usa_widget_colapsavel(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
    from editor.views.widget_editor_dados import ContainerRepeatedWidget, WidgetColapsavel
    
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico TDD"
    
    class MockFormulario:
        model = None
        controller = None
        def _mark_dirty(self): pass
        def _notify_tree_changed(self): pass
        def _render_message_fields(self, msg, layout): pass
        
    field = croqui.DESCRIPTOR.fields_by_name["picos"]
    container = ContainerRepeatedWidget(croqui, field, MockFormulario(), None)
    
    assert container.items_layout.count() == 1
    item_widget = container.items_layout.itemAt(0).widget()
    
    colapsaveis = item_widget.findChildren(WidgetColapsavel)
    assert len(colapsaveis) == 1, "WidgetColapsavel nao foi instanciado para o repeated field de mensagem"

def test_widget_colapsavel_lazy_load(qapp):
    from editor.views.widget_editor_dados import WidgetColapsavel
    from aresta_api.proto.generated.croqui_pb2 import Pico
    from PySide6.QtWidgets import QWidget
    
    pico = Pico(nome="Pico TDD Lazy")
    
    chamou_lazy = False
    def lazy_loader(msg, layout):
        nonlocal chamou_lazy
        chamou_lazy = True
        
    widget = WidgetColapsavel(pico, "1", lazy_loader)
    
    # Ao instanciar, nao deve ter chamado o loader
    assert not chamou_lazy
    
    # Ao expandir, deve chamar
    widget.toggle_button.setChecked(True)
    assert chamou_lazy

def test_widget_colapsavel_heuristica_titulo(qapp):
    from editor.views.widget_editor_dados import _extrair_titulo_heuristico
    from aresta_api.proto.generated.croqui_pb2 import Pico
    from unittest.mock import Mock
    
    # Tem nome
    pico = Pico(nome="Pico Especial")
    assert _extrair_titulo_heuristico(pico) == "Pico Especial"
    
    # Fake obj com id
    ponto = Mock()
    ponto.HasField.side_effect = lambda f: f == "id"
    ponto.id = "P01"
    assert _extrair_titulo_heuristico(ponto) == "P01"
    
    # Sem nada
    pico2 = Pico()
    assert _extrair_titulo_heuristico(pico2) is None

def test_widget_colapsavel_undo_redo_atualiza_titulo(qapp):
    from editor.views.widget_editor_dados import WidgetColapsavel
    from aresta_api.proto.generated.croqui_pb2 import Pico
    
    pico = Pico(nome="Original")
    
    def lazy_loader(msg, layout): pass
        
    widget = WidgetColapsavel(pico, "Item 0", lazy_loader)
    
    # Titulo inicial
    assert widget.toggle_button.text() == "▶ Item 0 - Original"
    
    # Mudanca por Undo
    pico.nome = "Alterado"
    widget.update_title()
    
    assert widget.toggle_button.text() == "▶ Item 0 - Alterado"

def test_formulario_exibe_e_edita_nome_de_arquivo_mapas_gerais(qapp):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PySide6.QtWidgets import QLineEdit
    
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico A"
    pico.mapas_gerais.caminho = "mapas_gerais.md"
    pico.mapas_gerais.Extensions[croqui_pb2.ArquivoMapas.ext_metadados_arquivo].caminho_novo = "mapas_gerais_novo.md"
    
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model

    # Encontra o node
    croqui_idx = modelo.index(0, 0)
    
    exp_picos_idx = None
    for r in range(modelo.rowCount(croqui_idx)):
        idx = modelo.index(r, 0, croqui_idx)
        if modelo.data(idx) == "Picos":
            exp_picos_idx = idx
            break
    assert exp_picos_idx is not None
    
    pico_idx = modelo.index(0, 0, exp_picos_idx)
    
    # Encontra Mapas Gerais
    mapas_idx = None
    for r in range(modelo.rowCount(pico_idx)):
        idx = modelo.index(r, 0, pico_idx)
        if modelo.data(idx) == "Mapas gerais":
            mapas_idx = idx
            break
    assert mapas_idx is not None
    
    form = widget.form_padrao
    form.load_node(mapas_idx.internalPointer())
    
    # Verifica se a UI renderizou o QLineEdit do nome do arquivo
    line_edits = form.findChildren(QLineEdit)
    edit_filename = next((le for le in line_edits if le.property("protobuf_field") == "__filename__"), None)
    assert edit_filename is not None
    assert edit_filename.text() == "mapas_gerais_novo.md"


def test_fluxo_integracao_carregamento_e_salvamento_yaml_campos_vazios(tmp_path, qapp):
    """Garante que campos vazios não aparecem no YAML salvo e campos preenchidos aparecem,
    sem presença de botões Adicionar/Remover nos cards de campos."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Setor, Coordenada
    from editor.views.tree_view_adapter import ProtobufNode
    from PySide6.QtWidgets import QPushButton, QLineEdit, QComboBox
    import yaml
    
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Teste"
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Completo"
    sg.setor.conteudo.amigavel_a_criancas = True
    # sinal_de_celular e amigavel_a_bebes não estão definidos (ausentes)
    # localizacao_estacionamento não está definida (ausente)
    
    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    node = ProtobufNode(name="Setor", message=sg.setor.conteudo, descriptor=Setor.DESCRIPTOR)
    form.load_node(node)
    
    # 1. Valida que nenhum botão [Adicionar] ou [Remover] de card individual foi renderizado
    botoes = [btn.text() for btn in form.findChildren(QPushButton)]
    assert "Adicionar" not in botoes, f"Botão 'Adicionar' não deveria existir nos cards: {botoes}"
    assert "Remover" not in botoes, f"Botão 'Remover' não deveria existir nos cards: {botoes}"
    
    # 2. Salva no disco via extrair_arquivos_e_serializar e lê o arquivo YAML
    model.extrair_arquivos_e_serializar(tmp_path)
    arquivo_setor = tmp_path / "setor_setor_completo.md"
    assert arquivo_setor.exists()
    
    with open(arquivo_setor, "r", encoding="utf-8") as f:
        conteudo_md = f.read()
    
    # Extrai o frontmatter YAML
    partes = conteudo_md.split("---")
    assert len(partes) >= 3
    dados_yaml = yaml.safe_load(partes[1])
    
    assert dados_yaml["nome"] == "Setor Completo"
    assert dados_yaml["amigavel_a_criancas"] is True
    assert "sinal_de_celular" not in dados_yaml
    assert "amigavel_a_bebes" not in dados_yaml
    assert "localizacao_estacionamento" not in dados_yaml


def test_formulario_inteiro_vazio_e_step_by_vira_zero(qapp):
    """Garante que campos de inteiros são exibidos como vazios quando ausentes,
    e que ao clicar para cima/baixo eles inicializam com 0 e gravam a alteração."""
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from editor.views.protobuf_widget_factory import SpinBoxVazio
    from editor.views.tree_view_adapter import ProtobufNode
    
    setor = Setor()
    pilha = QUndoStack()
    model = CroquiModel(setor)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=Setor.DESCRIPTOR)
    form.load_node(node)
    
    # Encontra o spinbox do indice_mapa_padrao
    spins = form.findChildren(SpinBoxVazio)
    spin_mapa = next(s for s in spins if s.property("protobuf_field") == "indice_mapa_padrao")
    
    # 1. Campo inicialmente vazio (texto vazio)
    assert not setor.HasField("indice_mapa_padrao")
    assert spin_mapa.text() == ""
    assert spin_mapa.value() == spin_mapa.VALOR_NULO
    
    # 2. Clicar para cima (stepBy 1) transforma em 0
    spin_mapa.stepBy(1)
    qapp.processEvents()
    assert spin_mapa.value() == 0
    assert spin_mapa.text() == "0"
    assert setor.HasField("indice_mapa_padrao")
    assert setor.indice_mapa_padrao == 0
    
    # 3. Undo restaura para vazio
    pilha.undo()
    qapp.processEvents()
    assert not setor.HasField("indice_mapa_padrao")
    assert spin_mapa.text() == ""
    assert spin_mapa.value() == spin_mapa.VALOR_NULO


def test_booleano_selecionar_nao_informado_permanece_nao_informado(qapp):
    """Garante que selecionar a opção 'Não informado' em um booleano tri-state
    mantém o valor como 'Não informado' (ausente/None) e não muda para 'Não' (False)."""
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from editor.views.tree_view_adapter import ProtobufNode
    from PySide6.QtWidgets import QComboBox
    
    setor = Setor()
    setor.sinal_de_celular = False  # Usuário tinha 'Não'
    pilha = QUndoStack()
    model = CroquiModel(setor)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=Setor.DESCRIPTOR)
    form.load_node(node)
    
    combo = next(cb for cb in form.findChildren(QComboBox) if cb.property("protobuf_field") == "sinal_de_celular")
    assert combo.currentIndex() == 2  # "Sem sinal"
    
    # 1. Seleciona "Não informado" (índice 0) a partir de "Não"
    combo.setCurrentIndex(0)
    qapp.processEvents()
    
    assert not setor.HasField("sinal_de_celular")
    assert combo.currentIndex() == 0
    assert combo.currentData() is None
    assert combo.currentText() == "Não informado"
    
    # 2. Seleciona "Sim" (índice 1)
    combo.setCurrentIndex(1)
    qapp.processEvents()
    
    assert setor.HasField("sinal_de_celular")
    assert setor.sinal_de_celular is True
    assert combo.currentIndex() == 1
    assert combo.currentData() is True
    assert combo.currentText() == "Possui sinal"
    
    # 3. Seleciona "Não informado" (índice 0) a partir de "Sim"
    combo.setCurrentIndex(0)
    qapp.processEvents()
    
    assert not setor.HasField("sinal_de_celular")
    assert combo.currentIndex() == 0
    assert combo.currentData() is None
    assert combo.currentText() == "Não informado"


def test_formulario_inteiro_apagar_com_backspace_limpa_campo_no_modelo(qapp):
    """Garante que no formulário, ao apagar o valor de um inteiro com backspace e perder o foco,
    o campo tem sua presença limpa no Protobuf e a UI permanece vazia."""
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.protobuf_widget_factory import SpinBoxVazio
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    
    setor = Setor()
    setor.indice_mapa_padrao = 5
    pilha = QUndoStack()
    model = CroquiModel(setor)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=Setor.DESCRIPTOR)
    form.load_node(node)
    
    spin = next(s for s in form.findChildren(SpinBoxVazio) if s.property("protobuf_field") == "indice_mapa_padrao")
    assert spin.value() == 5
    assert spin.text() == "5"
    assert setor.HasField("indice_mapa_padrao")
    
    # Simula o usuário apagando o conteúdo
    spin.lineEdit().setText("")
    
    # Simula a perda de foco (focusOutEvent)
    event = QFocusEvent(QEvent.Type.FocusOut)
    QApplication.sendEvent(spin, event)
    qapp.processEvents()
    
    assert not setor.HasField("indice_mapa_padrao")
    assert spin.value() == SpinBoxVazio.VALOR_NULO
    assert spin.text() == ""


def test_integracao_adicao_subelementos_novo_croqui(qapp, monkeypatch):
    """Testa a integração ponta a ponta de criação de subelementos em um croqui novo:
    Pico -> Setor -> Escalada e Grupo -> Setor, via árvore, menu de contexto e cartões."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from PySide6.QtWidgets import QInputDialog, QPushButton

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pedra do Baú"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # 1. Verifica se o nó expando de 'Setores ou grupos' existe sob o Pico mesmo estando vazio
    croqui_node_idx = widget.tree_model.index(0, 0)
    picos_expando_idx = next(widget.tree_model.index(r, 0, croqui_node_idx) for r in range(widget.tree_model.rowCount(croqui_node_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_node_idx)) == "Picos")
    pico_node_idx = widget.tree_model.index(0, 0, picos_expando_idx)
    assert pico_node_idx.isValid()

    widget.tree_view.expand(pico_node_idx)
    qapp.processEvents()

    # O Pico deve conter o expando 'Setores ou grupos'
    assert widget.tree_model.rowCount(pico_node_idx) >= 1
    sg_expando_idx = widget.tree_model.index(0, 0, pico_node_idx)
    assert sg_expando_idx.isValid()
    assert "etor" in widget.tree_model.data(sg_expando_idx)

    # Sob o expando 'Setores ou grupos', deve conter o nó virtual de adição
    assert widget.tree_model.rowCount(sg_expando_idx) == 1
    no_virtual_add = widget.tree_model.index(0, 0, sg_expando_idx)
    assert no_virtual_add.internalPointer().eh_no_adicao is True

    # 2. Simula adição de um Setor via nó virtual com diálogo
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo
    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: ("setor", "Setor 1", "setor_1.md", True)
    )
    widget._executar_adicionar_item(no_virtual_add)
    qapp.processEvents()

    assert len(pico.setores_ou_grupos) == 1
    sg_item = pico.setores_ou_grupos[0]
    assert sg_item.HasField("setor")

    # 3. Verifica se sob o novo Setor, o expando 'Escaladas' e o nó virtual existem mesmo vazios
    setor_item_idx = widget.tree_model.index(0, 0, sg_expando_idx)
    assert setor_item_idx.isValid()
    widget.tree_view.expand(setor_item_idx)
    qapp.processEvents()

    assert widget.tree_model.rowCount(setor_item_idx) >= 1
    escaladas_expando_idx = widget.tree_model.index(0, 0, setor_item_idx)
    assert escaladas_expando_idx.isValid()
    assert "scalada" in widget.tree_model.data(escaladas_expando_idx)

    # 4. Adiciona uma Escalada (Via Esportiva)
    from editor.views.dialogos.dialogo_criar_escalada import DialogoCriarEscalada
    monkeypatch.setattr(
        DialogoCriarEscalada,
        "obter_dados",
        lambda *args, **kwargs: ("via_esportiva", "Via Teste", True)
    )
    no_virtual_esc = widget.tree_model.index(0, 0, escaladas_expando_idx)
    widget._executar_adicionar_item(no_virtual_esc)
    qapp.processEvents()

    setor = sg_item.setor.conteudo
    assert len(setor.escaladas) == 1
    assert setor.escaladas[0].HasField("via_esportiva")
    assert setor.escaladas[0].via_esportiva.nome == "Via Teste"

    # 5. Verifica se o formulário do Pico possui o cartão de subelementos no rodapé
    widget.tree_view.selectionModel().select(pico_node_idx, widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect)
    widget._on_tree_selection_changed(None, None)
    qapp.processEvents()

    botoes_cartao = [b for b in widget.form_padrao.findChildren(QPushButton) if "Adicionar" in b.text() and ("Setor" in b.text() or "Grupo" in b.text())]
    assert len(botoes_cartao) >= 1


def test_integracao_desfazer_refazer_adicao_subelementos(qapp, monkeypatch):
    """Garante que a adição de subelementos é completamente passível de Desfazer e Refazer via Undo/Redo."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Undo"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    croqui_node_idx = widget.tree_model.index(0, 0)
    picos_expando_idx = next(widget.tree_model.index(r, 0, croqui_node_idx) for r in range(widget.tree_model.rowCount(croqui_node_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_node_idx)) == "Picos")
    pico_node_idx = widget.tree_model.index(0, 0, picos_expando_idx)
    widget.tree_view.expand(pico_node_idx)
    qapp.processEvents()

    sg_expando_idx = widget.tree_model.index(0, 0, pico_node_idx)
    no_virtual_add = widget.tree_model.index(0, 0, sg_expando_idx)

    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: ("grupo", "Grupo Undo", "grupo_undo.md", True)
    )
    widget._executar_adicionar_item(no_virtual_add)
    qapp.processEvents()

    assert len(pico.setores_ou_grupos) == 1
    assert pico.setores_ou_grupos[0].HasField("grupo")

    # Desfaz a adição
    pilha.undo()
    qapp.processEvents()
    assert len(pico.setores_ou_grupos) == 0

    # Refaz a adição
    pilha.redo()
    qapp.processEvents()
    assert len(pico.setores_ou_grupos) == 1
    assert pico.setores_ou_grupos[0].HasField("grupo")


def test_menu_contexto_no_estrutural_adicao_filhos(qapp):
    """Garante que o menu de contexto em nós estruturais pais (Pico, Setor, Croqui)
    exibe ações para adicionar seus subelementos filhos diretamente."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Menu Contexto"
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Menu Contexto"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # 1. Clica com botão direito no nó do Pico
    croqui_node_idx = widget.tree_model.index(0, 0)
    # Localiza o expando de Picos
    expando_picos_idx = next(widget.tree_model.index(r, 0, croqui_node_idx) for r in range(widget.tree_model.rowCount(croqui_node_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_node_idx)) == "Picos")
    pico_node_idx = widget.tree_model.index(0, 0, expando_picos_idx)

    menu_pico = widget._construir_menu_contexto(widget.tree_view.visualRect(pico_node_idx).center())
    assert menu_pico is not None
    acoes_pico = [a.text() for a in menu_pico.actions()]
    assert any("Adicionar" in a and ("Setor" in a or "Grupo" in a) for a in acoes_pico)
    assert "Excluir item" in acoes_pico

    # 2. Clica com botão direito no nó do Croqui
    menu_croqui = widget._construir_menu_contexto(widget.tree_view.visualRect(croqui_node_idx).center())
    assert menu_croqui is not None
    acoes_croqui = [a.text() for a in menu_croqui.actions()]
    assert any("Pico" in a for a in acoes_croqui)
    assert any("Botão" in a or "Botao" in a for a in acoes_croqui)


def test_cartoes_subelementos_no_formulario(qapp):
    """Garante que o formulário de entidades estruturais (Croqui, Pico, Grupo, Setor)
    renderiza cartões informativos de subelementos com contagem e botão de adição."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, Grupo, Setor
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.tree_view_adapter import ProtobufNode
    from PySide6.QtWidgets import QLabel, QPushButton

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico dos Cartões"
    
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    # 1. Carrega o nó do Pico no formulário
    node_pico = ProtobufNode(name="Pico", message=pico, descriptor=Pico.DESCRIPTOR)
    form.load_node(node_pico)
    qapp.processEvents()

    # Verifica se há o cartão de Setores ou Grupos com botão
    labels = [lbl.text() for lbl in form.findChildren(QLabel)]
    assert any("Setores ou grupos" in l or "Setores e Grupos" in l for l in labels)
    assert any("0 itens" in l or "0 item" in l for l in labels)
    
    botoes = [btn.text() for btn in form.findChildren(QPushButton)]
    assert any("Adicionar Setor ou Grupo" in b for b in botoes)

    # 2. Carrega um Setor no formulário
    setor = Setor(nome="Setor Cartões")
    node_setor = ProtobufNode(name="Setor", message=setor, descriptor=Setor.DESCRIPTOR)
    form.load_node(node_setor)
    qapp.processEvents()

    labels_setor = [lbl.text() for lbl in form.findChildren(QLabel)]
    assert any("Escaladas" in l for l in labels_setor)
    botoes_setor = [btn.text() for btn in form.findChildren(QPushButton)]
    assert any("Adicionar Escalada" in b for b in botoes_setor)


def test_clique_botao_cartao_adiciona_subelemento_com_undo(qapp, monkeypatch):
    """Garante que clicar no botão de adição do cartão no formulário cria o subelemento
    e empilha o comando de Undo/Redo corretamente."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.tree_view_adapter import ProtobufNode
    from PySide6.QtWidgets import QPushButton, QInputDialog

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Ação Cartão"
    
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    node_pico = ProtobufNode(name="Pico", message=pico, descriptor=pico.DESCRIPTOR)
    form.load_node(node_pico)
    qapp.processEvents()

    # Encontra o botão de adição do cartão
    btn_add = next(b for b in form.findChildren(QPushButton) if "Adicionar Setor ou Grupo" in b.text())
    
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo
    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: ("setor", "Setor Cartao", "setor_cartao.md", True)
    )
    btn_add.click()
    qapp.processEvents()

    assert len(pico.setores_ou_grupos) == 1
    assert pico.setores_ou_grupos[0].HasField("setor")

    # Testa que pode ser desfeito via histórico
    pilha.undo()
    qapp.processEvents()
    assert len(pico.setores_ou_grupos) == 0

    # Testa que pode ser refeito
    pilha.redo()
    qapp.processEvents()
    assert len(pico.setores_ou_grupos) == 1


def test_cartao_adicao_grupo_e_cancelamento(qapp, monkeypatch):
    """Testa a renderização do cartão em Grupo e cancelamento de diálogo em ONEOFs."""
    from aresta_api.proto.generated.croqui_pb2 import Grupo
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo
    from PySide6.QtWidgets import QPushButton

    croqui = Croqui()
    grupo = Grupo(nome="Grupo dos Cartões")
    
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    node_grupo = ProtobufNode(name="Grupo", message=grupo, descriptor=Grupo.DESCRIPTOR)
    form.load_node(node_grupo)
    qapp.processEvents()

    # O botão para ArquivoSetor deve exibir '+ Adicionar Setor'
    btn_add = next(b for b in form.findChildren(QPushButton) if "Adicionar Setor" in b.text())
    assert btn_add is not None

    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: ("setor", "Setor Grupo", "setor_grupo.md", True)
    )
    # Testa clique no botão do Grupo
    btn_add.click()
    qapp.processEvents()
    assert len(grupo.setores) == 1

    # Testa cancelamento no diálogo de um ONEOF sem default (SetorOuGrupo em Pico)
    pico = croqui.picos.add(nome="Pico Cancelar")
    node_pico = ProtobufNode(name="Pico", message=pico, descriptor=pico.DESCRIPTOR)
    form.load_node(node_pico)
    qapp.processEvents()

    btn_add_pico = next(b for b in form.findChildren(QPushButton) if "Adicionar Setor ou Grupo" in b.text())
    # Simula usuário clicando em 'Cancelar'
    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: ("", "", "", False)
    )
    btn_add_pico.click()
    qapp.processEvents()

    # Nenhum item deve ter sido adicionado
    assert len(pico.setores_ou_grupos) == 0


def test_cartao_adicao_croqui(qapp, monkeypatch):
    """Testa a renderização dos cartões no Croqui (Picos e Botões)."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.dialogos.dialogo_criar_botao import DialogoCriarBotao
    from PySide6.QtWidgets import QPushButton

    croqui = Croqui(nome="Croqui Teste Cartões")
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    node_croqui = ProtobufNode(name="Croqui", message=croqui, descriptor=Croqui.DESCRIPTOR)
    form.load_node(node_croqui)
    qapp.processEvents()

    btn_picos = next(b for b in form.findChildren(QPushButton) if "Adicionar Pico" in b.text())
    btn_botoes = next(b for b in form.findChildren(QPushButton) if "Adicionar Botão" in b.text() or "Adicionar Botao" in b.text())

    assert btn_picos is not None
    assert btn_botoes is not None

    from editor.views.dialogos.dialogo_criar_pico import DialogoCriarPico
    monkeypatch.setattr(
        DialogoCriarPico,
        "obter_dados",
        lambda *args, **kwargs: ("Novo Pico Cartao", True)
    )
    btn_picos.click()
    qapp.processEvents()
    assert len(croqui.picos) == 1
    assert croqui.picos[0].nome == "Novo Pico Cartao"

    monkeypatch.setattr(
        DialogoCriarBotao,
        "obter_dados",
        lambda *args, **kwargs: ("Como Chegar", "como_chegar.md", True)
    )
    btn_botoes.click()
    qapp.processEvents()
    assert len(croqui.botoes) == 1
    assert croqui.botoes[0].texto == "Como Chegar"


def test_integracao_adicionar_escalada_em_setores_distintos_foca_escalada_correta(qapp, monkeypatch):
    """Garante que ao adicionar uma escalada no Setor B (quando o Setor A já tem escaladas),
    o editor seleciona e foca exatamente a nova escalada no Setor B, e não uma do Setor A."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_escalada import DialogoCriarEscalada

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pedra do Baú")
    
    sg_a = pico.setores_ou_grupos.add()
    setor_a = sg_a.setor.conteudo
    setor_a.nome = "Setor A"
    esc_a1 = setor_a.escaladas.add()
    esc_a1.via_esportiva.nome = "Via do Setor A1"
    esc_a2 = setor_a.escaladas.add()
    esc_a2.via_esportiva.nome = "Via do Setor A2"

    sg_b = pico.setores_ou_grupos.add()
    setor_b = sg_b.setor.conteudo
    setor_b.nome = "Setor B"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Localiza o expando de Escaladas do Setor B
    croqui_idx = widget.tree_model.index(0, 0)
    picos_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = widget.tree_model.index(0, 0, picos_exp_idx)
    sg_exp_idx = widget.tree_model.index(0, 0, pico_idx)
    setor_b_idx = widget.tree_model.index(1, 0, sg_exp_idx)
    assert widget.tree_model.data(setor_b_idx) == "Setor B"

    widget.tree_view.expand(setor_b_idx)
    qapp.processEvents()

    esc_b_exp_idx = widget.tree_model.index(0, 0, setor_b_idx)
    assert "scalada" in widget.tree_model.data(esc_b_exp_idx)
    no_virtual_add_b = widget.tree_model.index(0, 0, esc_b_exp_idx)

    # Executa a adição no Setor B
    monkeypatch.setattr(
        DialogoCriarEscalada,
        "obter_dados",
        lambda parent=None, nomes_existentes=None: ("via_esportiva", "Via Inédita B", True)
    )
    widget._executar_adicionar_item(no_virtual_add_b)
    qapp.processEvents()

    # Verifica se a nova escalada foi adicionada no Setor B
    assert len(setor_b.escaladas) == 1
    assert setor_b.escaladas[0].via_esportiva.nome == "Via Inédita B"

    # Verifica se a seleção da árvore aponta para a escalada no Setor B
    selected = widget.tree_view.selectionModel().selectedIndexes()
    assert len(selected) > 0
    selected_node = selected[0].internalPointer()
    assert selected_node.parent_node.parent_node.message == setor_b
    assert selected_node.index_in_repeated == 0


def test_integracao_wizard_criar_setor_com_nome_e_arquivo(qapp, monkeypatch):
    """Garante que a criação de Setor pelo wizard preenche o nome e os metadados do arquivo novo."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, ArquivoSetor
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Teste")

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Localiza o nó de adição de Setor ou Grupo no Pico
    croqui_idx = widget.tree_model.index(0, 0)
    picos_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = widget.tree_model.index(0, 0, picos_exp_idx)
    sg_exp_idx = widget.tree_model.index(0, 0, pico_idx)
    no_add = widget.tree_model.index(0, 0, sg_exp_idx)

    # Simula resposta do DialogoCriarSetorOuGrupo
    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda parent=None, modo="ambos", nome_sugerido="", nomes_existentes=None, arquivos_existentes=None: ("setor", "Falésia Sol", "setor_falesia_sol.md", True)
    )

    widget._executar_adicionar_item(no_add)
    qapp.processEvents()

    assert len(pico.setores_ou_grupos) == 1
    sg = pico.setores_ou_grupos[0]
    assert sg.HasField("setor")
    assert sg.setor.conteudo.nome == "Falésia Sol"
    assert sg.setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_falesia_sol.md"

    # Testa Undo
    pilha.undo()
    qapp.processEvents()
    assert len(pico.setores_ou_grupos) == 0

    # Testa Redo
    pilha.redo()
    qapp.processEvents()
    assert len(pico.setores_ou_grupos) == 1
    assert pico.setores_ou_grupos[0].setor.conteudo.nome == "Falésia Sol"


def test_undo_nao_dispara_wizard_ao_selecionar_no_virtual(qapp, monkeypatch):
    """Garante que desfazer uma adição não aciona o diálogo modal de criação."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Teste Undo Seguro")

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Adiciona setor via controller
    from aresta_api.proto.generated.croqui_pb2 import SetorOuGrupo
    sg = SetorOuGrupo()
    sg.setor.conteudo.nome = "Setor A"
    controller.adicionar_repeated(pico, "setores_ou_grupos", 0, sg)
    qapp.processEvents()

    # Flag para detectar se o diálogo foi chamado indevidamente
    dialogo_chamado = []
    monkeypatch.setattr(
        DialogoCriarSetorOuGrupo,
        "obter_dados",
        lambda *args, **kwargs: (dialogo_chamado.append(True) or ("setor", "X", "x.md", True))
    )

    # Executa Undo
    pilha.undo()
    qapp.processEvents()

    # O diálogo NUNCA deve ter sido chamado durante o Undo
    assert len(dialogo_chamado) == 0
    assert len(pico.setores_ou_grupos) == 0


def test_integracao_wizard_criar_botao_com_texto_e_arquivo(qapp, monkeypatch):
    """Garante que a criação de Botão pelo wizard preenche o texto e o arquivo Markdown vinculado."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, ArquivoMarkdown
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_botao import DialogoCriarBotao

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Localiza o expando de Botões no Croqui
    croqui_idx = widget.tree_model.index(0, 0)
    botoes_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Botões")
    no_add_botao = widget.tree_model.index(0, 0, botoes_exp_idx)

    # Simula resposta do DialogoCriarBotao
    monkeypatch.setattr(
        DialogoCriarBotao,
        "obter_dados",
        lambda *args, **kwargs: ("Como Chegar", "secao_como_chegar.md", True)
    )

    widget._executar_adicionar_item(no_add_botao)
    qapp.processEvents()

    assert len(croqui.botoes) == 1
    botao = croqui.botoes[0]
    assert botao.texto == "Como Chegar"
    assert botao.HasField("destino")
    assert botao.destino.WhichOneof("destino") == "secao_textual"
    assert botao.destino.secao_textual.Extensions[ArquivoMarkdown.ext_metadados_arquivo].caminho_novo == "secao_como_chegar.md"


def test_integracao_wizard_criar_escalada_com_nome(qapp, monkeypatch):
    """Garante que a criação de Escalada pelo wizard preenche o tipo e o nome da via na árvore."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_escalada import DialogoCriarEscalada

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Escaladas")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Principal"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Localiza o expando de Escaladas
    croqui_idx = widget.tree_model.index(0, 0)
    picos_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = widget.tree_model.index(0, 0, picos_exp_idx)
    sg_exp_idx = widget.tree_model.index(0, 0, pico_idx)
    setor_idx = widget.tree_model.index(0, 0, sg_exp_idx)
    widget.tree_view.expand(setor_idx)
    qapp.processEvents()

    esc_exp_idx = widget.tree_model.index(0, 0, setor_idx)
    no_add_esc = widget.tree_model.index(0, 0, esc_exp_idx)

    # Simula resposta do DialogoCriarEscalada
    monkeypatch.setattr(
        DialogoCriarEscalada,
        "obter_dados",
        lambda *args, **kwargs: ("via_movel", "Fissura da Meia Noite", True)
    )

    widget._executar_adicionar_item(no_add_esc)
    qapp.processEvents()

    assert len(setor.escaladas) == 1
    esc = setor.escaladas[0]
    assert esc.HasField("via_movel")
    assert esc.via_movel.nome == "Fissura da Meia Noite"


def test_integracao_adicionar_setores_em_grupo_mantem_ordem_e_sincronismo_arvore(qapp, monkeypatch):
    """Garante que adicionar múltiplos setores em um Grupo via cartão de ação rápida
    mantém o nó virtual '+ Adicionar Setor' sempre no final da lista e a contagem sincronizada."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Teste Grupo")
    sg = pico.setores_ou_grupos.add()
    grupo = sg.grupo.conteudo
    grupo.nome = "Grupo Principal"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Adiciona 3 setores sucessivos ao grupo via executar_adicionar_subelemento (mesmo método dos cartões)
    nomes = ["Setor 1", "Setor 2", "Setor 3"]
    for i, nome in enumerate(nomes):
        monkeypatch.setattr(
            DialogoCriarSetorOuGrupo,
            "obter_dados",
            lambda *args, nome_i=nome, **kwargs: ("setor", nome_i, f"setor_{i}.md", True)
        )
        widget.executar_adicionar_subelemento(grupo, "setores")
        qapp.processEvents()

    assert len(grupo.setores) == 3

    # Localiza o expando 'Setores' dentro do Grupo na árvore
    croqui_idx = widget.tree_model.index(0, 0)
    picos_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Picos")
    pico_idx = widget.tree_model.index(0, 0, picos_exp_idx)
    sg_exp_idx = widget.tree_model.index(0, 0, pico_idx)
    grupo_idx = widget.tree_model.index(0, 0, sg_exp_idx)
    widget.tree_view.expand(grupo_idx)
    qapp.processEvents()

    setores_exp_idx = widget.tree_model.index(0, 0, grupo_idx)
    widget.tree_view.expand(setores_exp_idx)
    qapp.processEvents()

    # Deve conter 4 linhas: Setor 1 (0), Setor 2 (1), Setor 3 (2), + Adicionar Setor (3)
    total_linhas = widget.tree_model.rowCount(setores_exp_idx)
    assert total_linhas == 4

    # Linha 0: Setor 1
    idx_0 = widget.tree_model.index(0, 0, setores_exp_idx)
    assert widget.tree_model.data(idx_0) == "Setor 1"
    assert idx_0.internalPointer().eh_no_adicao is False

    # Linha 1: Setor 2
    idx_1 = widget.tree_model.index(1, 0, setores_exp_idx)
    assert widget.tree_model.data(idx_1) == "Setor 2"
    assert idx_1.internalPointer().eh_no_adicao is False

    # Linha 2: Setor 3
    idx_2 = widget.tree_model.index(2, 0, setores_exp_idx)
    assert widget.tree_model.data(idx_2) == "Setor 3"
    assert idx_2.internalPointer().eh_no_adicao is False

    # Linha 3 (ÚLTIMA): + Adicionar Setor
    idx_3 = widget.tree_model.index(3, 0, setores_exp_idx)
    assert "+ Adicionar" in widget.tree_model.data(idx_3)
    assert idx_3.internalPointer().eh_no_adicao is True


def test_integracao_wizard_criar_pico_com_nome(qapp, monkeypatch):
    """Garante que a criação de Pico pelo wizard preenche o nome e foca o item na árvore."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados
    from editor.views.dialogos.dialogo_criar_pico import DialogoCriarPico

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Localiza o expando de Picos no Croqui
    croqui_idx = widget.tree_model.index(0, 0)
    picos_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Picos")
    no_add_pico = widget.tree_model.index(0, 0, picos_exp_idx)

    # Simula resposta do DialogoCriarPico
    monkeypatch.setattr(
        DialogoCriarPico,
        "obter_dados",
        lambda *args, **kwargs: ("Pedra Grande", True)
    )

    widget._executar_adicionar_item(no_add_pico)
    qapp.processEvents()

    assert len(croqui.picos) == 1
    pico = croqui.picos[0]
    assert pico.nome == "Pedra Grande"

    # Verifica se o pico está selecionado na árvore e no formulário
    selected = widget.tree_view.selectionModel().selectedIndexes()
    assert len(selected) > 0
    assert widget.tree_model.data(selected[0]) == "Pedra Grande"


def test_integracao_botao_renderiza_texto_e_markdown_inline_mesma_pagina(qapp):
    """Garante que o nó de Botão na árvore é uma folha e renderiza texto, nome do arquivo e markdown inline na mesma página."""
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown

    croqui = Croqui()
    botao = croqui.botoes.add()
    botao.texto = "Apoio e Doações"
    botao.destino.secao_textual.conteudo = "# Ajude nosso projeto"
    botao.destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = "apoio.md"

    pilha = QUndoStack()
    model = CroquiModel(croqui)
    controller = CroquiController(model, pilha)
    widget = WidgetEditorDados(model, controller)
    widget.show()
    widget.expandir_arvore_ate_alvos()
    qapp.processEvents()

    # Localiza o nó do Botão na árvore
    croqui_idx = widget.tree_model.index(0, 0)
    botoes_exp_idx = next(widget.tree_model.index(r, 0, croqui_idx) for r in range(widget.tree_model.rowCount(croqui_idx)) if widget.tree_model.data(widget.tree_model.index(r, 0, croqui_idx)) == "Botões")
    widget.tree_view.expand(botoes_exp_idx)
    qapp.processEvents()

    botao_idx = widget.tree_model.index(0, 0, botoes_exp_idx)
    assert widget.tree_model.data(botao_idx) == "Apoio e Doações"

    # O nó de Botão não deve ter filhos na árvore (é folha, não tem filho secao_textual)
    assert widget.tree_model.rowCount(botao_idx) == 0

    # Seleciona o Botão na árvore
    widget.tree_view.selectionModel().select(botao_idx, widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect)
    widget._on_tree_selection_changed(None, None)
    qapp.processEvents()

    # O formulário padrão deve estar ativo
    assert widget.stacked_widget.currentIndex() == 0
    form = widget.form_padrao.currentWidget()
    assert form is not None

    # Deve conter o campo de texto do botão
    line_edits = form.findChildren(QLineEdit)
    texto_edits = [le for le in line_edits if le.property("protobuf_field") == "texto"]
    assert len(texto_edits) == 1
    assert texto_edits[0].text() == "Apoio e Doações"

    # Deve conter o campo do nome do arquivo inline
    filename_edits = [le for le in line_edits if le.property("protobuf_field") == "__filename__"]
    assert len(filename_edits) == 1
    assert filename_edits[0].text() == "apoio.md"

    # Deve conter o editor markdown inline (raw + preview)
    md_editors = form.findChildren(WidgetEditorMarkdown)
    assert len(md_editors) == 1
    assert md_editors[0].editor.toPlainText() == "# Ajude nosso projeto"


def test_markdown_editor_botao_inserir_imagem_com_undo_redo(qapp, tmp_path, monkeypatch):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack
    from PySide6.QtWidgets import QDialog
    from editor.views.dialogos.dialogo_inserir_imagem_markdown import DialogoInserirImagemMarkdown

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, pilha)

    widget = WidgetEditorDados(model, controller)
    setor = Setor()
    setor.descricao = "Introdução do setor."
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)

    md_editor = widget.form_padrao.findChild(WidgetEditorMarkdown)
    assert md_editor is not None
    assert hasattr(md_editor, "btn_inserir_imagem")

    # Mock do dialogo
    class MockDialogo:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return QDialog.DialogCode.Accepted
        def obter_tag_markdown(self):
            return "![Foto 1](imagens/foto_1.webp)"

    monkeypatch.setattr("editor.views.widget_editor_dados.DialogoInserirImagemMarkdown", MockDialogo)

    # Posiciona o cursor no final
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)

    # Clica no botão inserir imagem
    md_editor.btn_inserir_imagem.click()

    # O texto deve ter sido inserido
    assert md_editor.editor.toPlainText() == "Introdução do setor.![Foto 1](imagens/foto_1.webp)"
    assert setor.descricao == "Introdução do setor.![Foto 1](imagens/foto_1.webp)"
    assert "foto_1.webp" in md_editor.preview.toHtml()

    # Desfaz (Undo)
    pilha.undo()
    qapp.processEvents()
    assert md_editor.editor.toPlainText() == "Introdução do setor."
    assert setor.descricao == "Introdução do setor."
    assert "foto_1.webp" not in md_editor.preview.toHtml()

    # Refaz (Redo)
    pilha.redo()
    qapp.processEvents()
    assert md_editor.editor.toPlainText() == "Introdução do setor.![Foto 1](imagens/foto_1.webp)"
    assert setor.descricao == "Introdução do setor.![Foto 1](imagens/foto_1.webp)"
    assert "foto_1.webp" in md_editor.preview.toHtml()


def test_markdown_editor_imagem_preview_em_memoria_sem_disco(qapp, tmp_path):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack, QImage, QTextDocument
    from PySide6.QtCore import QBuffer, QIODevice, QUrl

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, pilha)

    img = QImage(100, 80, QImage.Format.Format_RGB32)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.ReadWrite)
    img.save(buf, "WEBP")
    bytes_webp = bytes(buf.data())

    # Adiciona a imagem APENAS no buffer de memória RAM do model (não no disco)
    model.definir_imagem_memoria("imagens/mapa_ram.webp", bytes_webp)

    # Garante que não existe no disco
    assert not (tmp_path / "imagens" / "mapa_ram.webp").exists()

    widget = WidgetEditorDados(model, controller)
    setor = Setor()
    setor.descricao = "![Legenda](imagens/mapa_ram.webp)"
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)

    md_editor = widget.form_padrao.findChild(WidgetEditorMarkdown)
    # Força escalonamento
    md_editor.preview.scale_images()

    # O preview deve ter carregado o recurso de imagem a partir da RAM
    res = md_editor.preview.document().resource(QTextDocument.ResourceType.ImageResource, QUrl("imagens/mapa_ram.webp"))
    assert res is not None


def test_markdown_editor_drag_and_drop_imagem_interna(qapp, tmp_path, monkeypatch):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack, QDropEvent, QDragEnterEvent
    from PySide6.QtCore import Qt, QMimeData, QUrl, QPoint, QPointF
    from PySide6.QtWidgets import QDialog

    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    caminho_img = pasta_imagens / "setor_bloco.webp"
    caminho_img.write_bytes(b"dummy")

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, pilha)

    widget = WidgetEditorDados(model, controller)
    setor = Setor()
    setor.descricao = "Texto inicial. "
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)

    md_editor = widget.form_padrao.findChild(WidgetEditorMarkdown)

    class MockDialogo:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return QDialog.DialogCode.Accepted
        def obter_tag_markdown(self):
            return "![Bloco Principal](imagens/setor_bloco.webp)"

    monkeypatch.setattr("editor.views.widget_editor_dados.DialogoInserirImagemMarkdown", MockDialogo)

    # Simula DragEnter
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(caminho_img))])
    event_enter = QDragEnterEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    md_editor.editor.dragEnterEvent(event_enter)
    assert event_enter.isAccepted()

    # Simula Drop de imagem interna (abre assistente exigindo legenda)
    event_drop = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    md_editor.editor.dropEvent(event_drop)
    assert event_drop.isAccepted()
    assert "![Bloco Principal](imagens/setor_bloco.webp)" in md_editor.editor.toPlainText()


def test_markdown_editor_drag_and_drop_imagem_externa(qapp, tmp_path, monkeypatch):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack, QDropEvent, QDragEnterEvent
    from PySide6.QtCore import Qt, QMimeData, QUrl, QPoint, QPointF
    from PySide6.QtWidgets import QDialog

    pasta_ext = tmp_path / "externo"
    pasta_ext.mkdir()
    caminho_img_ext = pasta_ext / "minha_foto.png"
    caminho_img_ext.write_bytes(b"dummy")

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, pilha)

    widget = WidgetEditorDados(model, controller)
    setor = Setor()
    setor.descricao = ""
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)

    md_editor = widget.form_padrao.findChild(WidgetEditorMarkdown)

    class MockDialogo:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return QDialog.DialogCode.Accepted
        def obter_tag_markdown(self):
            return "![Minha Foto](imagens/minha_foto.webp)"

    monkeypatch.setattr("editor.views.widget_editor_dados.DialogoInserirImagemMarkdown", MockDialogo)

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(caminho_img_ext))])
    event_drop = QDropEvent(
        QPointF(10.0, 10.0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    md_editor.editor.dropEvent(event_drop)
    assert event_drop.isAccepted()
    assert md_editor.editor.toPlainText() == "![Minha Foto](imagens/minha_foto.webp)"


def test_markdown_editor_colar_imagem_clipboard(qapp, tmp_path, monkeypatch):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack, QImage
    from PySide6.QtCore import QMimeData
    from PySide6.QtWidgets import QDialog

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, pilha)

    widget = WidgetEditorDados(model, controller)
    setor = Setor()
    setor.descricao = ""
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)

    md_editor = widget.form_padrao.findChild(WidgetEditorMarkdown)

    class MockDialogo:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return QDialog.DialogCode.Accepted
        def obter_tag_markdown(self):
            return "![Captura de Tela](imagens/imagem_clipboard.webp)"

    monkeypatch.setattr("editor.views.widget_editor_dados.DialogoInserirImagemMarkdown", MockDialogo)

    # Simula insertFromMimeData com QImage
    mime = QMimeData()
    img = QImage(10, 10, QImage.Format.Format_RGB32)
    mime.setImageData(img)

    md_editor.editor.insertFromMimeData(mime)
    assert md_editor.editor.toPlainText() == "![Captura de Tela](imagens/imagem_clipboard.webp)"


def test_markdown_editor_autocompletar(qapp, tmp_path):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PySide6.QtGui import QUndoStack, QKeyEvent
    from PySide6.QtCore import Qt

    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    (pasta_imagens / "via_lactea.webp").write_bytes(b"dummy")
    (pasta_imagens / "bloco_central.webp").write_bytes(b"dummy")

    croqui = Croqui()
    pilha = QUndoStack()
    model = CroquiModel(croqui)
    model._caminho_db_atual = tmp_path
    controller = CroquiController(model, pilha)

    widget = WidgetEditorDados(model, controller)
    setor = Setor()
    setor.descricao = ""
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    widget.form_padrao.load_node(node)

    md_editor = widget.form_padrao.findChild(WidgetEditorMarkdown)
    assert md_editor.editor.completer() is not None

    # 1. Verifica itens do completer
    model_completer = md_editor.editor.completer().model()
    itens = [model_completer.index(r, 0).data() for r in range(model_completer.rowCount())]
    assert "via_lactea.webp" in itens
    assert "bloco_central.webp" in itens

    # 2. Testa extração de token sob o cursor
    md_editor.editor.setPlainText("Veja a foto: ![Setor](imagens/via")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)

    token, busca = md_editor.editor._obter_token_sob_cursor()
    assert token == "imagens/via"
    assert busca == "via"

    # 3. Testa inserção da completion substituindo o token
    md_editor.editor._insert_completion("via_lactea.webp")
    assert md_editor.editor.toPlainText() == "Veja a foto: ![Setor](imagens/via_lactea.webp"

    # 4. Testa acionamento do atalho Ctrl+Space dentro de tag de imagem
    event_ctrl_space = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Space,
        Qt.KeyboardModifier.ControlModifier,
    )
    md_editor.editor.keyPressEvent(event_ctrl_space)
    assert md_editor.editor.completer().popup().isVisible() is True
    md_editor.editor.completer().popup().hide()

    # 5. Testa que texto comum e links comuns não disparam autocompletar
    md_editor.editor.setPlainText("Esta via é muito bonita e técnica")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    token_normal, busca_normal = md_editor.editor._obter_token_sob_cursor()
    assert token_normal == ""
    assert busca_normal == ""

    # Digitação em texto comum não abre popup
    event_char = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a")
    md_editor.editor.keyPressEvent(event_char)
    assert md_editor.editor.completer().popup().isVisible() is False

    # Ctrl+Space em texto comum não abre popup
    md_editor.editor.keyPressEvent(event_ctrl_space)
    assert md_editor.editor.completer().popup().isVisible() is False

    # Link normal [Texto](via...) não abre popup e não extrai token
    md_editor.editor.setPlainText("Veja o [documento](via")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    token_link, busca_link = md_editor.editor._obter_token_sob_cursor()
    assert token_link == ""
    assert busca_link == ""
    md_editor.editor.keyPressEvent(event_ctrl_space)
    assert md_editor.editor.completer().popup().isVisible() is False

    # Imagem já fechada seguida de texto normal não extrai token
    md_editor.editor.setPlainText("![Foto](imagens/via_lactea.webp) mais texto sobre a via")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    token_fechado, busca_fechado = md_editor.editor._obter_token_sob_cursor()
    assert token_fechado == ""
    assert busca_fechado == ""
    md_editor.editor.keyPressEvent(event_ctrl_space)
    assert md_editor.editor.completer().popup().isVisible() is False

    # Múltiplas tags na mesma linha: segunda imagem em edição deve disparar autocompletar
    md_editor.editor.setPlainText("![Foto 1](imagens/bloco_central.webp) e ![Foto 2](imagens/via")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    token_multi, busca_multi = md_editor.editor._obter_token_sob_cursor()
    assert token_multi == "imagens/via"
    assert busca_multi == "via"

    # Multilinha: linha anterior com texto normal e linha atual com imagem
    md_editor.editor.setPlainText("Primeira linha de texto\nSegunda linha com ![Foto](imagens/via")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    token_multi_linha, busca_multi_linha = md_editor.editor._obter_token_sob_cursor()
    assert token_multi_linha == "imagens/via"
    assert busca_multi_linha == "via"

    # Cursor posicionado no meio de uma tag existente
    md_editor.editor.setPlainText("Veja: ![Foto](imagens/via_lactea.webp) fim")
    cursor = md_editor.editor.textCursor()
    # Posiciona logo após 'imagens/via' (índice 25)
    cursor.setPosition(25)
    md_editor.editor.setTextCursor(cursor)
    token_meio, busca_meio = md_editor.editor._obter_token_sob_cursor()
    assert token_meio == "imagens/via"
    assert busca_meio == "via"

    # Escape de markdown (\![...](...)) não deve ser considerado tag de imagem
    md_editor.editor.setPlainText(r"Texto com \![Falso](imagens/via")
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    token_escapado, busca_escapado = md_editor.editor._obter_token_sob_cursor()
    assert token_escapado == ""
    assert busca_escapado == ""


def test_container_repeated_widget_adicionar_item_trilha(qapp):
    """Verifica se clicar no botão de adicionar item em um campo repeated de mensagem (como trilhas) funciona sem UnboundLocalError."""
    from editor.views.widget_editor_dados import ContainerRepeatedWidget
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Micos"

    model = CroquiModel(croqui)
    controller = CroquiController(model, QUndoStack())
    widget = WidgetEditorDados(model, controller)
    form = widget.form_padrao

    field_descriptor = setor.DESCRIPTOR.fields_by_name["trilhas"]
    container = ContainerRepeatedWidget(setor, field_descriptor, form)

    assert len(setor.trilhas) == 0

    # Clica no botão Adicionar Item
    container.btn_add.click()

    # Deve ter adicionado uma trilha
    assert len(setor.trilhas) == 1


def test_widget_editor_markdown_coalescencia_digitacao(qapp):
    from unittest.mock import MagicMock
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    setor = Setor()
    setor.descricao = "Texto Inicial"

    model = CroquiModel(croqui)
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)
    widget_dados = WidgetEditorDados(model, controller)

    campo_desc = setor.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(setor, campo_desc, widget_dados.form_padrao)

    assert hasattr(md_editor, "temporizador"), "WidgetEditorMarkdown deve possuir temporizador"
    assert md_editor.editor.toPlainText() == "Texto Inicial"

    # Simula digitação no final do texto
    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    md_editor.editor.insertPlainText(" digitado")
    assert md_editor.temporizador.esta_ativo() is True
    assert setor.descricao == "Texto Inicial", "Modelo não deve ser mutado antes da expiração do temporizador"

    # Força descarga
    md_editor.temporizador.forcar_descarga()
    assert setor.descricao == "Texto Inicial digitado"
    assert md_editor.temporizador.esta_ativo() is False


def test_widget_editor_markdown_focus_out_forca_descarga(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from PySide6.QtGui import QUndoStack, QFocusEvent
    from PySide6.QtCore import QEvent

    croqui = Croqui()
    setor = Setor()
    setor.descricao = "Original"

    model = CroquiModel(croqui)
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)
    widget_dados = WidgetEditorDados(model, controller)

    campo_desc = setor.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(setor, campo_desc, widget_dados.form_padrao)

    cursor = md_editor.editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    md_editor.editor.setTextCursor(cursor)
    md_editor.editor.insertPlainText(" modificado")
    assert md_editor.temporizador.esta_ativo() is True

    # Simula perda de foco
    evento_foco = QFocusEvent(QEvent.Type.FocusOut)
    md_editor.editor.focusOutEvent(evento_foco)

    assert md_editor.temporizador.esta_ativo() is False
    assert setor.descricao == "Original modificado"


def test_widget_editor_markdown_set_conteudo_guarda_igualdade(qapp, monkeypatch):
    from unittest.mock import MagicMock
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    setor = Setor()
    setor.descricao = "Mesmo Texto"

    model = CroquiModel(croqui)
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)
    widget_dados = WidgetEditorDados(model, controller)

    campo_desc = setor.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(setor, campo_desc, widget_dados.form_padrao)

    # Monitora chamadas a preview.setMarkdown
    mock_set_markdown = MagicMock()
    monkeypatch.setattr(md_editor.preview, "setMarkdown", mock_set_markdown)

    # Chamada com texto idêntico ao já existente
    md_editor.set_conteudo("Mesmo Texto")

    # Não deve ter chamado o parse do markdown novamente
    assert mock_set_markdown.call_count == 0


def test_formulario_on_campo_alterado_instalacao_idempotente_filtro_undo_redo(qapp, monkeypatch):
    from unittest.mock import MagicMock
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from editor.views.widget_editor_dados import WidgetEditorDados, WidgetEditorMarkdown, _get_id
    from PySide6.QtGui import QUndoStack

    croqui = Croqui()
    setor = Setor()
    setor.descricao = "Inicial"

    model = CroquiModel(croqui)
    pilha = QUndoStack()
    controller = CroquiController(model, pilha)
    widget_dados = WidgetEditorDados(model, controller)

    campo_desc = setor.DESCRIPTOR.fields_by_name["descricao"]
    md_editor = WidgetEditorMarkdown(setor, campo_desc, widget_dados.form_padrao, parent=widget_dados.form_padrao)

    # Espiona o método installEventFilter do editor
    chamadas_filtro = []
    original_install = md_editor.editor.installEventFilter

    def spy_install(filtro):
        chamadas_filtro.append(filtro)
        return original_install(filtro)

    monkeypatch.setattr(md_editor.editor, "installEventFilter", spy_install)

    msg_id = _get_id(setor)
    # Invoca _on_campo_alterado múltiplas vezes
    widget_dados.form_padrao._on_campo_alterado(msg_id, "descricao", "Valor 1")
    widget_dados.form_padrao._on_campo_alterado(msg_id, "descricao", "Valor 2")
    widget_dados.form_padrao._on_campo_alterado(msg_id, "descricao", "Valor 3")

    # Deve ter instalado o filtro no máximo 1 vez, sem duplicatas
    from editor.views.widget_editor_dados import GlobalUndoRedoFilter
    filtros_undo = [f for f in chamadas_filtro if isinstance(f, GlobalUndoRedoFilter)]
    assert len(filtros_undo) <= 1, f"Filtros de Undo acumulados indevidamente: {len(filtros_undo)}"
