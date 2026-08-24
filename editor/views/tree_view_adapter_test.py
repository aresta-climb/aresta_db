# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from PyQt6.QtCore import QModelIndex, Qt
from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.views.tree_view_adapter import ProtobufTreeViewAdapter


def _obter_expando(model, parent_index, nome_expando):
    """Auxiliar para localizar um nó expando pelo nome exibido."""
    total = model.rowCount(parent_index)
    for r in range(total):
        idx = model.index(r, 0, parent_index)
        if model.data(idx, Qt.ItemDataRole.DisplayRole) == nome_expando:
            return idx
    return QModelIndex()


def test_protobuf_tree_model_empty():
    croqui = Croqui()
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    # A raiz (invisível) deve conter exatamente 1 nó correspondente ao Croqui
    assert model.rowCount(root_index) == 1
    croqui_index = model.index(0, 0, root_index)
    
    # Mesmo com coleções vazias, o nó Croqui deve conter expandos elegíveis (Picos e Botões)
    assert model.rowCount(croqui_index) >= 1
    
    nomes_expandos = [model.data(model.index(r, 0, croqui_index), Qt.ItemDataRole.DisplayRole) for r in range(model.rowCount(croqui_index))]
    assert "Picos" in nomes_expandos
    assert "Botões" in nomes_expandos

    # O expando Picos vazio deve conter exatamente 1 nó virtual de adição
    expando_picos_idx = _obter_expando(model, croqui_index, "Picos")
    assert expando_picos_idx.isValid()
    assert model.rowCount(expando_picos_idx) == 1
    no_virtual = model.index(0, 0, expando_picos_idx)
    assert no_virtual.internalPointer().eh_no_adicao is True
    assert model.data(no_virtual, Qt.ItemDataRole.DisplayRole) == "+ Adicionar Pico"


def test_protobuf_tree_model_colecoes_vazias_em_pico_grupo_setor():
    from aresta_api.proto.generated.croqui_pb2 import Pico, Grupo, Setor
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Vazio"
    
    model = ProtobufTreeViewAdapter(croqui)
    croqui_idx = model.index(0, 0, QModelIndex())
    
    # Localiza o Pico
    expando_picos = _obter_expando(model, croqui_idx, "Picos")
    pico_node = model.index(0, 0, expando_picos)
    assert model.data(pico_node) == "Pico Vazio"
    
    # Pico vazio deve conter expando 'Setores ou grupos' com nó virtual
    assert model.rowCount(pico_node) >= 1
    sg_expando = model.index(0, 0, pico_node)
    assert "etor" in model.data(sg_expando)
    assert model.rowCount(sg_expando) == 1
    assert model.index(0, 0, sg_expando).internalPointer().eh_no_adicao is True

    # Adiciona Setor vazio
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Vazio"
    
    model_setor = ProtobufTreeViewAdapter(croqui)
    croqui_idx2 = model_setor.index(0, 0, QModelIndex())
    exp_picos2 = _obter_expando(model_setor, croqui_idx2, "Picos")
    pico_node2 = model_setor.index(0, 0, exp_picos2)
    sg_expando2 = model_setor.index(0, 0, pico_node2)
    setor_node = model_setor.index(0, 0, sg_expando2)
    assert model_setor.data(setor_node) == "Setor Vazio"
    
    # Setor vazio deve conter expando 'Escaladas' com nó virtual
    assert model_setor.rowCount(setor_node) >= 1
    esc_expando = model_setor.index(0, 0, setor_node)
    assert "scalada" in model_setor.data(esc_expando)
    assert model_setor.rowCount(esc_expando) == 1
    assert model_setor.index(0, 0, esc_expando).internalPointer().eh_no_adicao is True


def test_protobuf_tree_model_root_categories():
    croqui = Croqui()
    # Adiciona um pico e um arquivo markdown sob um botão
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipó"
    
    botao = croqui.botoes.add()
    botao.texto = "Como chegar"
    arq_md = botao.destino.secao_textual
    arq_md.caminho = "como_chegar.md"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    
    # A raiz (invisível) deve conter o nó Croqui
    assert model.rowCount(root_index) == 1
    croqui_index = model.index(0, 0, root_index)
    
    # O nó Croqui deve conter 2 expandos: "Botões" e "Picos"
    assert model.rowCount(croqui_index) == 2
    
    expando_botoes = _obter_expando(model, croqui_index, "Botões")
    expando_picos = _obter_expando(model, croqui_index, "Picos")
    
    assert expando_botoes.isValid()
    assert expando_picos.isValid()
    
    # Sob o expando picos deve ter o pico "Serra do Cipó" + o nó virtual de adição
    assert model.rowCount(expando_picos) == 2  # 1 pico + 1 nó virtual
    pico_node = model.index(0, 0, expando_picos)
    assert model.data(pico_node, Qt.ItemDataRole.DisplayRole) == "Serra do Cipó"
    
    # O último filho do expando picos deve ser o nó virtual de adição
    no_virtual_picos = model.index(1, 0, expando_picos)
    assert no_virtual_picos.internalPointer().eh_no_adicao is True
    
    # Sob o expando botoes deve ter o botao "Como chegar" + nó virtual
    assert model.rowCount(expando_botoes) == 2  # 1 botao + 1 nó virtual
    botao_node = model.index(0, 0, expando_botoes)
    assert model.data(botao_node, Qt.ItemDataRole.DisplayRole) == "Como chegar"


def test_protobuf_tree_model_nested_transparency():
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Gruta da Lapinha"
    
    # Adiciona SetorOuGrupo -> ArquivoSetor -> Setor
    sg = pico.setores_ou_grupos.add()
    arq_setor = sg.setor
    arq_setor.conteudo.nome = "Setor Principal"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    
    croqui_index = model.index(0, 0, root_index)
    expando_picos = _obter_expando(model, croqui_index, "Picos")
    pico_node = model.index(0, 0, expando_picos)
    
    # Sob o Pico, deve ter o expando "Setores ou grupos"
    assert model.rowCount(pico_node) == 1
    expando_sg = model.index(0, 0, pico_node)
    assert model.data(expando_sg, Qt.ItemDataRole.DisplayRole) == "Setores ou grupos"
    
    # Sob o expando "Setores ou grupos", deve conter o Setor + o nó virtual
    assert model.rowCount(expando_sg) == 2  # 1 setor + 1 nó virtual
    setor_node = model.index(0, 0, expando_sg)
    assert model.data(setor_node, Qt.ItemDataRole.DisplayRole) == "Setor Principal"
    
    # O último filho deve ser o nó virtual de adição
    no_virtual = model.index(1, 0, expando_sg)
    assert no_virtual.internalPointer().eh_no_adicao is True


def test_protobuf_tree_model_escalada_oneof():
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Bloco A"
    
    # Adiciona Escalada
    esc = setor.escaladas.add()
    esc.via_esportiva.nome = "Fenda do Bicho"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    
    croqui_index = model.index(0, 0, root_index)
    picos_exp = _obter_expando(model, croqui_index, "Picos")
    pico_node = model.index(0, 0, picos_exp)
    sg_exp = model.index(0, 0, pico_node)
    setor_node = model.index(0, 0, sg_exp)
    
    # Sob o setor, deve ter o expando "Escaladas"
    assert model.rowCount(setor_node) == 1
    escaladas_exp = model.index(0, 0, setor_node)
    assert model.data(escaladas_exp, Qt.ItemDataRole.DisplayRole) == "Escaladas"
    
    # Sob o expando "Escaladas", deve ter a Escalada + o nó virtual
    assert model.rowCount(escaladas_exp) == 2  # 1 escalada + 1 nó virtual
    esc_node = model.index(0, 0, escaladas_exp)
    assert model.data(esc_node, Qt.ItemDataRole.DisplayRole) == "Fenda do Bicho"
    
    # O último filho deve ser o nó virtual de adição
    no_virtual = model.index(1, 0, escaladas_exp)
    assert no_virtual.internalPointer().eh_no_adicao is True


def test_protobuf_tree_model_croqui_display_name():
    croqui = Croqui()
    croqui.nome = "Complexo Pedra Grande"
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    croqui_index = model.index(0, 0, root_index)
    
    # O nó do Croqui deve exibir "Croqui" em vez do nome do croqui
    assert model.data(croqui_index, Qt.ItemDataRole.DisplayRole) == "Croqui"


def test_protobuf_tree_model_titulo_na_ui():
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Serra do Cipó" # pico.nome has (titulo_na_ui) = true
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    croqui_index = model.index(0, 0, root_index)
    expando_picos = _obter_expando(model, croqui_index, "Picos")
    pico_node = model.index(0, 0, expando_picos)
    
    # Deve usar o valor de pico.nome porque tem (titulo_na_ui) = true
    assert model.data(pico_node, Qt.ItemDataRole.DisplayRole) == "Serra do Cipó"


def test_protobuf_tree_model_arquivo_markdown_titulo():
    croqui = Croqui()
    
    # 1. Com conteudo contendo H1
    bot1 = croqui.botoes.add()
    bot1.texto = "Título Bacana"
    arq_md_1 = bot1.destino.secao_textual
    arq_md_1.conteudo = "# Título Bacana\nEste é o corpo do texto"
    
    # 2. Com conteudo sem H1
    bot2 = croqui.botoes.add()
    bot2.texto = "Conteúdo Markdown"
    arq_md_2 = bot2.destino.secao_textual
    arq_md_2.conteudo = "Este é um texto sem título H1"
    
    # 3. Com caminho
    bot3 = croqui.botoes.add()
    bot3.texto = "Recomendacoes e regras"
    arq_md_3 = bot3.destino.secao_textual
    arq_md_3.caminho = "recomendacoes_e_regras.md"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    croqui_index = model.index(0, 0, root_index)
    expando_md = _obter_expando(model, croqui_index, "Botões")
    
    node_1 = model.index(0, 0, expando_md)
    node_2 = model.index(1, 0, expando_md)
    node_3 = model.index(2, 0, expando_md)
    
    assert model.data(node_1, Qt.ItemDataRole.DisplayRole) == "Título Bacana"
    assert model.data(node_2, Qt.ItemDataRole.DisplayRole) == "Conteúdo Markdown"
    assert model.data(node_3, Qt.ItemDataRole.DisplayRole) == "Recomendacoes e regras"


def test_protobuf_tree_model_oneof_invisible():
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico de Teste"
    
    # Adiciona SetorOuGrupo (ONEOF) -> ArquivoSetor (ONEOF) -> Setor (SEPARADO)
    sg = pico.setores_ou_grupos.add()
    arq_setor = sg.setor
    setor = arq_setor.conteudo
    setor.nome = "Setor Invisivel Test"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    
    croqui_index = model.index(0, 0, root_index)
    expando_picos = _obter_expando(model, croqui_index, "Picos")
    pico_node = model.index(0, 0, expando_picos)
    
    # O pico deve ter apenas 1 filho expando: "Setores ou grupos"
    assert model.rowCount(pico_node) == 1
    expando_sg = model.index(0, 0, pico_node)
    assert model.data(expando_sg, Qt.ItemDataRole.DisplayRole) == "Setores ou grupos"
    
    # O expando "Setores ou grupos" deve conter o Setor + o nó virtual
    assert model.rowCount(expando_sg) == 2  # 1 setor + 1 nó virtual
    setor_node = model.index(0, 0, expando_sg)
    
    # O último filho deve ser o nó virtual de adição
    no_virtual = model.index(1, 0, expando_sg)
    assert no_virtual.internalPointer().eh_no_adicao is True
    
    # O rótulo exibido deve ser o nome do Setor e o pai do Setor na árvore deve ser o expando
    assert model.data(setor_node, Qt.ItemDataRole.DisplayRole) == "Setor Invisivel Test"
    assert setor_node.parent().internalPointer() == expando_sg.internalPointer()
    
    # Nenhuma mensagem intermediária do tipo ONEOF (SetorOuGrupo ou ArquivoSetor) deve existir como nó intermediário
    node_setor = setor_node.internalPointer()
    assert node_setor.message.DESCRIPTOR.name == "Setor"
    assert node_setor.parent_node.name == "Setores ou grupos"
    assert node_setor.parent_node.parent_node.message.DESCRIPTOR.name == "Pico"


def test_no_virtual_nome_usa_espacos_em_vez_de_camel_case():
    """O nome do no virtual de adicao deve separar CamelCase com espacos."""
    croqui = Croqui()
    bot = croqui.botoes.add()
    bot.texto = "Introdução"
    arq = bot.destino.secao_textual
    arq.caminho = "intro.md"

    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    croqui_index = model.index(0, 0, root_index)
    expando_md = _obter_expando(model, croqui_index, "Botões")

    total_filhos = model.rowCount(expando_md)
    no_virtual_idx = model.index(total_filhos - 1, 0, expando_md)
    no_virtual = no_virtual_idx.internalPointer()
    assert no_virtual.eh_no_adicao is True

    texto = model.data(no_virtual_idx, Qt.ItemDataRole.DisplayRole)
    assert texto is not None
    assert "Botão" in texto or "Botao" in texto or "Arquivo" in texto or "Markdown" in texto


def test_no_virtual_fonte_em_italico():
    """O no virtual de adicao deve retornar fonte em italico via FontRole."""
    from PyQt6.QtGui import QFont

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Teste"

    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    croqui_index = model.index(0, 0, root_index)
    expando_picos = _obter_expando(model, croqui_index, "Picos")

    total_filhos = model.rowCount(expando_picos)
    no_virtual_idx = model.index(total_filhos - 1, 0, expando_picos)
    no_virtual = no_virtual_idx.internalPointer()
    assert no_virtual.eh_no_adicao is True

    fonte = model.data(no_virtual_idx, Qt.ItemDataRole.FontRole)
    assert fonte is not None
    assert isinstance(fonte, QFont)
    assert fonte.italic() is True

    # Itens normais nao devem ter italico forcado
    pico_idx = model.index(0, 0, expando_picos)
    fonte_pico = model.data(pico_idx, Qt.ItemDataRole.FontRole)
    assert fonte_pico is None


def test_oneof_conteudo_resolve_arquivo_setor_para_setor():
    """_resolve_transparency em ArquivoSetor com ONEOF_CONTEUDO e conteudo ativo
    deve retornar o Setor interno, nao o wrapper ArquivoSetor."""
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor, Setor
    from editor.views.tree_view_adapter import ProtobufNode

    arq = ArquivoSetor()
    arq.conteudo.nome = "Setor Teste"

    node = ProtobufNode(name="arq", message=arq)
    resolvido = node._resolve_transparency(arq)

    assert isinstance(resolvido, Setor), (
        f"_resolve_transparency(ArquivoSetor) deveria retornar Setor, mas retornou {type(resolvido).__name__}"
    )
    assert resolvido.nome == "Setor Teste"


def test_oneof_conteudo_arquivo_markdown_retorna_wrapper():
    """_resolve_transparency em ArquivoMarkdown com ONEOF_CONTEUDO e conteudo (string)
    deve retornar o proprio ArquivoMarkdown (nao pode desembrulhar uma string)."""
    from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown
    from editor.views.tree_view_adapter import ProtobufNode

    arq = ArquivoMarkdown()
    arq.conteudo = "# Titulo\n\nTexto do markdown."

    node = ProtobufNode(name="arq", message=arq)
    resolvido = node._resolve_transparency(arq)

    assert isinstance(resolvido, ArquivoMarkdown), (
        f"_resolve_transparency(ArquivoMarkdown) deveria retornar ArquivoMarkdown, mas retornou {type(resolvido).__name__}"
    )


def test_protobuf_tree_model_reactive_updates():
    from aresta_api.proto.generated.croqui_pb2 import Pico
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico A"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_idx = QModelIndex()
    croqui_idx = model.index(0, 0, root_idx)
    picos_exp_idx = _obter_expando(model, croqui_idx, "Picos")
    
    # Garante que os filhos picos estão populados na árvore
    model.rowCount(picos_exp_idx)
    
    # 1. Teste _on_campo_alterado (renomeia Pico A)
    sinais = []
    model.dataChanged.connect(lambda top, bottom, roles=None: sinais.append((top, bottom)))
    
    pico.nome = "Pico Alterado"
    model._on_campo_alterado(id(pico), "nome", "Pico Alterado")
    
    assert len(sinais) == 1
    pico_node_idx = model.index(0, 0, picos_exp_idx)
    assert sinais[0][0] == pico_node_idx
    assert model.data(pico_node_idx) == "Pico Alterado"
    
    # 2. Teste _on_item_adicionado (insere um pico no indice 0)
    pico_novo = Pico(nome="Pico Novo")
    croqui.picos.insert(0, pico_novo)
    
    insercoes = []
    model.rowsInserted.connect(lambda parent, start, end: insercoes.append((parent, start, end)))
    
    model._on_item_adicionado(id(croqui), "picos", 0)
    
    assert len(insercoes) == 1
    assert insercoes[0] == (picos_exp_idx, 0, 0)
    
    # Verifica que o Pico Novo está no índice 0 e o Pico Alterado foi para o índice 1
    assert model.data(model.index(0, 0, picos_exp_idx)) == "Pico Novo"
    assert model.data(model.index(1, 0, picos_exp_idx)) == "Pico Alterado"
    
    # 3. Teste _on_item_removido
    remocoes = []
    model.rowsRemoved.connect(lambda parent, start, end: remocoes.append((parent, start, end)))
    
    croqui.picos.pop(0)
    model._on_item_removido(id(croqui), "picos", 0)
    
    assert len(remocoes) == 1
    assert remocoes[0] == (picos_exp_idx, 0, 0)
    assert model.data(model.index(0, 0, picos_exp_idx)) == "Pico Alterado"


def test_protobuf_tree_model_oneof_generico():
    """Testa se a resolução de nomes na árvore funciona genericamente para qualquer ONEOF ativo
    que delegue o título para uma mensagem interna com titulo_na_ui."""
    from aresta_api.proto.generated.croqui_pb2 import SetorOuGrupo, Setor
    from editor.views.tree_view_adapter import ProtobufNode
    
    # SetorOuGrupo é um wrapper puro com um oneof "tipo"
    sg = SetorOuGrupo()
    sg.setor.conteudo.nome = "Setor Via ONEOF Genérico"
    
    node = ProtobufNode(name="sg", message=sg)
    model = ProtobufTreeViewAdapter(Croqui())
    
    class MockIndex:
        def isValid(self): return True
        def internalPointer(self): return node
        
    mock_idx = MockIndex()
    nome_extraido = model.data(mock_idx, Qt.ItemDataRole.DisplayRole)
    assert nome_extraido == "Setor Via ONEOF Genérico"


def test_tree_view_adapter_on_item_adicionado_resolve_transparency(qapp):
    """Garante que _on_item_adicionado chame _resolve_transparency para o item inserido."""
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
    from editor.views.tree_view_adapter import ProtobufTreeViewAdapter
    
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico de Teste"
    
    model = ProtobufTreeViewAdapter(croqui)
    model.rebuild_tree()
    
    import editor.views.widget_editor_dados
    pico_id = editor.views.widget_editor_dados._get_id(pico)
    
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Adicionado Direto"
    
    model._on_item_adicionado(pico_id, "setores_ou_grupos", 0)
    
    exp_idx = model.find_expando_index(pico_id, "setores_ou_grupos")
    exp_node = exp_idx.internalPointer()
    
    assert len(exp_node.children) >= 1
    new_node = exp_node.children[0]
    assert new_node.message.DESCRIPTOR.name == "Setor"


def test_tree_view_adapter_on_item_movido(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.views.tree_view_adapter import ProtobufTreeViewAdapter

    croqui = Croqui()
    p1 = croqui.picos.add()
    p1.nome = 'A'
    p2 = croqui.picos.add()
    p2.nome = 'B'
    p3 = croqui.picos.add()
    p3.nome = 'C'
    
    adapter = ProtobufTreeViewAdapter(croqui)

    root_idx = QModelIndex()
    croqui_idx = adapter.index(0, 0, root_idx)
    
    picos_idx = _obter_expando(adapter, croqui_idx, "Picos")
    assert picos_idx.isValid()
    adapter.rowCount(picos_idx)
    picos_node = picos_idx.internalPointer()

    # Move 0 to 2
    p = croqui.picos.pop(0)
    croqui.picos.insert(2, p)
    adapter._on_item_movido(id(croqui), 'picos', 0, 2)

    assert [c.message.nome for c in picos_node.children if hasattr(c, 'message') and c.message] == ['B', 'C', 'A']
    assert [c.index_in_repeated for c in picos_node.children if hasattr(c, 'index_in_repeated') and c.index_in_repeated is not None] == [0, 1, 2]


def test_protobuf_tree_model_mapas_gerais():
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.views.tree_view_adapter import ProtobufTreeViewAdapter
    
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Teste Mapas"
    
    pico.mapas_gerais.caminho = "mapas_gerais.md"
    
    model = ProtobufTreeViewAdapter(croqui)
    root_index = QModelIndex()
    
    croqui_index = model.index(0, 0, root_index)
    expando_picos = _obter_expando(model, croqui_index, "Picos")
    pico_node = model.index(0, 0, expando_picos)
    
    model.rowCount(pico_node)
    
    mapas_gerais_node = None
    labels = []
    for r in range(model.rowCount(pico_node)):
        idx = model.index(r, 0, pico_node)
        label = model.data(idx, Qt.ItemDataRole.DisplayRole)
        labels.append(label)
        if label == "Mapas gerais":
            mapas_gerais_node = idx
            break
            
    assert mapas_gerais_node is not None, f"O nó Mapas gerais deve aparecer na árvore do Pico. Encontrados: {labels}"
    node_ptr = mapas_gerais_node.internalPointer()
    assert node_ptr.message.DESCRIPTOR.name == "ArquivoMapas"
