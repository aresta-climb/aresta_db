from PyQt6.QtCore import QItemSelectionModel
import pytest
from PyQt6.QtWidgets import QApplication, QTreeView, QStackedWidget, QLineEdit, QFrame, QComboBox
from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController
from PyQt6.QtGui import QUndoStack
from editor.views.widget_editor_dados import WidgetEditorDados
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens
from editor.legacy_views.editor_mapas import WidgetEditorMapas

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
    assert widget.stacked_widget.count() >= 3  # Formulário padrão, Imagens, Mapas

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
    # Sob o Croqui, o primeiro item é o expando Picos
    expando_picos = modelo.index(0, 0, croqui_idx)
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
    expando_picos = modelo.index(0, 0, croqui_idx)
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
    exp_picos = modelo.index(0, 0, croqui_idx)
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


def test_widget_formulario_padrao_no_overlap(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipo"
    
    model = CroquiModel(croqui)
    
    controller = CroquiController(model, QUndoStack())
    
    widget = WidgetEditorDados(model, controller)
    modelo = widget.tree_model
    croqui_idx = modelo.index(0, 0)
    expando_picos = modelo.index(0, 0, croqui_idx)
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
    from PyQt6.QtCore import Qt, QItemSelectionModel, QItemSelectionModel
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
    from PyQt6.QtWidgets import QLineEdit
    
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Fantastico"
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_setor_fantastico.md"
    
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
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
    from PyQt6.QtWidgets import QLineEdit
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
    from PyQt6.QtWidgets import QComboBox, QTextEdit
    
    md_msg = ArquivoMarkdown()
    md_msg.conteudo = "# Ola"
    
    node = ProtobufNode(name="Markdown", message=md_msg, descriptor=md_msg.DESCRIPTOR)
    
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
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
    from PyQt6.QtWidgets import QTextEdit, QTextBrowser
    
    setor = Setor()
    setor.descricao = "Descricao inicial"
    
    # Campo descricao de Setor tem conteudo_markdown = true
    field = Setor.DESCRIPTOR.fields_by_name["descricao"]
    
    node = ProtobufNode(name="Setor", message=setor, descriptor=setor.DESCRIPTOR)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
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
    assert md_editor.preview.toPlainText().strip() == "Novo markdown"  # renderizado (HTML/rich text de-formatted to plain text is "Novo markdown")
    assert setor.descricao == "Novo **markdown**"


def test_markdown_editor_frontmatter_and_base_url(qapp):
    from editor.views.tree_view_adapter import ProtobufNode
    from editor.views.widget_editor_dados import WidgetFormularioPadrao, WidgetEditorMarkdown
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PyQt6.QtWidgets import QWidget
    
    # 1. Cria uma janela mock com caminho_croqui
    class MockWindow(QWidget):
        def __init__(self):
            super().__init__()
            from pathlib import Path
            self.caminho_croqui = Path("C:/test_croqui_folder")
    
    win = MockWindow()
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
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
    assert base_url == "C:/test_croqui_folder/database/"


def test_markdown_editor_image_auto_scaling(qapp):
    from editor.views.widget_editor_dados import AutoScalingTextBrowser
    from PyQt6.QtCore import QUrl, QSize
    from PyQt6.QtGui import QImage
    
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
    from PyQt6.QtGui import QUndoStack

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
    from PyQt6.QtWidgets import QLineEdit

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
    from PyQt6.QtGui import QUndoStack
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
    from PyQt6.QtGui import QUndoStack
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
    from PyQt6.QtWidgets import QSpinBox

    pico = Pico()
    node = ProtobufNode(name="Pico", message=pico, descriptor=pico.DESCRIPTOR)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_dummy = Croqui()
    model = CroquiModel(croqui_dummy)
    controller = CroquiController(model, QUndoStack())
    form = WidgetFormularioPadrao(model, controller)
    form.load_node(node)

    # QLineEdit de campos primitivos curtos deve ter max-width <= 450
    line_edits = form.findChildren(QLineEdit)
    # Exclui o QLineEdit que está dentro de um WidgetEditorMarkdown (que é largo)
    from editor.views.widget_editor_dados import WidgetEditorMarkdown
    editores_md = form.findChildren(WidgetEditorMarkdown)
    line_edits_md = []
    for md in editores_md:
        line_edits_md.extend(md.findChildren(QLineEdit))

    primitivos = [le for le in line_edits if le not in line_edits_md]
    for le in primitivos:
        assert le.maximumWidth() <= 450, f"QLineEdit sem max-width controlada: {le.maximumWidth()}"


def test_menu_contexto_adicionar_item_repeated(qapp):
    """Menu de contexto em nó expando deve adicionar item na coleção Protobuf."""
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import QMenu
    from PyQt6.QtTest import QTest

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico A"

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


def test_no_virtual_adicao_cria_e_seleciona(qapp):
    """Ao selecionar o nó virtual '+', um item deve ser criado e selecionado na árvore."""
    from editor.views.tree_view_adapter import ProtobufNode

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
    assert no_adicao.eh_no_adicao is True

    # Simula seleção do nó virtual — deve criar um pico
    widget.tree_view.selectionModel().select(
        no_adicao_idx,
        widget.tree_view.selectionModel().SelectionFlag.ClearAndSelect
    )

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

    # Mocka o QInputDialog para retornar a primeira opcao sem bloquear a UI
    # (o dialog intencional do ONEOF de SetorOuGrupo.tipo nao pode abrir em testes)
    import editor.views.widget_editor_dados
    class _MockQInputDialog:
        @staticmethod
        def getItem(parent, title, label, items, current=0, editable=False):
            return (items[0] if items else "", True)
    monkeypatch.setattr(editor.views.widget_editor_dados, "QInputDialog", _MockQInputDialog)

    # Executa o adicionar (bypassa o dialog de oneof)
    widget._executar_adicionar_item(no_virtual_idx)

    # Deve ter adicionado um novo SetorOuGrupo
    assert len(pico.setores_ou_grupos) == 2, "Novo SetorOuGrupo nao foi adicionado"

    # Apos adicionar, o stacked_widget deve estar no form padrao (indice 0)
    assert widget.stacked_widget.currentIndex() == 0, (
        "stacked_widget deveria estar no form padrao (indice 0), "
        f"mas esta em {widget.stacked_widget.currentIndex()}"
    )

    # O form padrao NAO deve conter um WidgetEditorMarkdown
    container = widget.form_padrao.currentWidget()
    has_markdown_editor = False
    if container:
        for child in container.findChildren(WidgetEditorMarkdown):
            has_markdown_editor = True
            break
    assert not has_markdown_editor, (
        "form_padrao nao deveria conter um WidgetEditorMarkdown apos adicionar SetorOuGrupo"
    )

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
    from PyQt6.QtGui import QUndoStack

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
    exp_picos = modelo.index(0, 0, croqui_idx)
    pico_idx = modelo.index(0, 0, exp_picos)
    pico_node = pico_idx.internalPointer()
    
    form = widget.form_padrao
    form.load_node(pico_node)
    
    # Encontra QLineEdit do nome
    line_edits = form.findChildren(QLineEdit)
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
    from PyQt6.QtGui import QUndoStack
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
    from editor.views.widget_editor_dados import get_node_path, WidgetEditorDados, _get_id
    from editor.views.tree_view_adapter import ProtobufNode
    from aresta_api.proto.generated.croqui_pb2 import Setor
    from PyQt6.QtWidgets import QPushButton
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack

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
    
    # Inicialmente setor.amigavel_a_criancas não está setado, então tem um "Adicionar"
    btn_add = None
    for widget_child in container.findChildren(QPushButton):
        if widget_child.text() == "Adicionar":
            btn_add = widget_child
            break
    assert btn_add is not None
    
    # Emula a adição (HasPresence) + signal emitido, como num undo/redo
    setor.amigavel_a_criancas = True
    model.oneof_alterado.emit(setor, "amigavel_a_criancas")
    
    # Processa eventos do Qt para que deleteLater() execute no layout
    qapp.processEvents()
    
    # O container do field foi recriado. "Adicionar" some, e "Remover" aparece
    btn_add_novo = None
    btn_remove_novo = None
    for widget_child in container.findChildren(QPushButton):
        if widget_child.text() == "Adicionar":
            btn_add_novo = widget_child
        elif widget_child.text() == "Remover":
            btn_remove_novo = widget_child
            
    assert btn_add_novo is None, "Botão Adicionar ainda deveria existir após ser recriado?"
    assert btn_remove_novo is not None, "Botão Remover deveria ter aparecido"

def test_widget_formulario_padrao_oneof_conteudo_renderizacao(qapp):
    """Garante que a renderizacao de uma mensagem ONEOF_CONTEUDO via _render_message_fields
    nao crie um QComboBox do oneof, mas sim renderize seu conteudo diretamente."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, ArquivoSetor
    from PyQt6.QtWidgets import QComboBox, QVBoxLayout, QWidget
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
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
    assert len(comboboxes) == 0, "Nao deveria existir combobox para ONEOF_CONTEUDO"

def test_on_campo_alterado_spinbox_typeerror_regression(qapp):
    """Garante que _on_campo_alterado não quebra com TypeError ao atualizar
    QSpinBox (que exige int) e QDoubleSpinBox (que exige float) com valores mistos (ex: float ou string de undo)."""
    from editor.views.widget_editor_dados import WidgetFormularioPadrao
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    from PyQt6.QtGui import QUndoStack
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QVBoxLayout
    
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
    from PyQt6.QtGui import QUndoStack

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
    from PyQt6.QtWidgets import QWidget
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
    from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout
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
    assert controller.contexto_atual_path == get_node_path(pico_idx.internalPointer())

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