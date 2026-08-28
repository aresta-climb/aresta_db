# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from unittest.mock import MagicMock
from PySide6.QtGui import QUndoStack
from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
from editor.models.croqui_model import CroquiModel
from editor.controllers.croqui_controller import CroquiController

def test_croqui_controller_alterar_primitivo(qapp):
    croqui = Croqui(nome="Antigo")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    proxy = model.obter_croqui_readonly()
    
    # A view despacha a intenção
    controller.alterar_primitivo(proxy, "nome", "Antigo", "Novo")
    
    # O Controller deve ter empurrado um comando, e o comando já rodou redo()
    assert proxy.nome == "Novo"
    assert undo_stack.count() == 1
    
    # Desfazendo a ação
    undo_stack.undo()
    assert proxy.nome == "Antigo"

    controller.set_contexto("page:dados")
    assert controller.contexto_atual_path == "page:dados"

def test_croqui_controller_adicionar_repeated(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    proxy = model.obter_croqui_readonly()
    
    pico = Pico(nome="Novo Pico")
    controller.adicionar_repeated(proxy, "picos", 0, pico)
    
    assert len(proxy.picos) == 1
    assert proxy.picos[0].nome == "Novo Pico"
    
    undo_stack.undo()
    assert len(proxy.picos) == 0

def test_croqui_controller_remover_repeated(qapp):
    croqui = Croqui()
    croqui.picos.add(nome="A Remover")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    proxy = model.obter_croqui_readonly()
    
    pico_removido = proxy.picos[0]
    controller.remover_repeated(proxy, "picos", 0, pico_removido)
    
    assert len(proxy.picos) == 0
    
    undo_stack.undo()
    assert len(proxy.picos) == 1
    assert proxy.picos[0].nome == "A Remover"

def test_croqui_controller_alterar_oneof(qapp):
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor, ArquivoGrupo
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.caminho = "Setor"
    
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    proxy = model.obter_croqui_readonly()
    proxy_sg = proxy.picos[0].setores_ou_grupos[0]
    
    novo_grupo = ArquivoGrupo()
    novo_grupo.caminho = "Grupo"
    
    arq_grupo = ArquivoGrupo()
    arq_grupo.caminho = "Grupo"
    
    arq_setor = ArquivoSetor()
    arq_setor.caminho = "Setor"
    
    controller.alterar_oneof(proxy_sg, "tipo", "setor", arq_setor, "grupo", arq_grupo)
    
    assert proxy_sg.WhichOneof("tipo") == "grupo"
    assert proxy_sg.grupo.caminho == "Grupo"
    
    undo_stack.undo()
    assert proxy_sg.WhichOneof("tipo") == "setor"
    assert proxy_sg.setor.caminho == "Setor"

from unittest.mock import patch

def test_croqui_controller_mover_repeated_para_cima():
    croqui = Croqui()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    with patch.object(undo_stack, 'push') as mock_push:
        croqui.creditos.extend(["Renato", "Silva"])
        controller.mover_repeated_para_cima(croqui, "creditos", 0)
        mock_push.assert_not_called()

        # Testa mover com index > 0
        controller.mover_repeated_para_cima(croqui, "creditos", 1)
        mock_push.assert_called_once()
        cmd = mock_push.call_args[0][0]
        assert type(cmd).__name__ == "CmdMoverRepeated"
        assert cmd.index_from == 1
        assert cmd.index_to == 0

def test_croqui_controller_alterar_metadados_caminho_novo():
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor
    croqui = Croqui()
    sg = croqui.picos.add().setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor"
    
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    proxy = model.obter_croqui_readonly()
    proxy_setor = proxy.picos[0].setores_ou_grupos[0].setor
    
    controller.alterar_metadados_caminho_novo(proxy_setor, ArquivoSetor.ext_metadados_arquivo, "", "novo_caminho.md")
    
    assert proxy_setor.HasExtension(ArquivoSetor.ext_metadados_arquivo)
    assert proxy_setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == "novo_caminho.md"
    assert undo_stack.count() == 1
    
    undo_stack.undo()
    assert proxy_setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == ""

def test_croqui_controller_mover_repeated_para_baixo():
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    with patch.object(undo_stack, 'push') as mock_push:
        # Testa mover no último elemento (deve ignorar)
        controller.mover_repeated_para_baixo(croqui, "creditos", 2)
        mock_push.assert_not_called()

        # Testa mover num elemento válido
        controller.mover_repeated_para_baixo(croqui, "creditos", 0)
        mock_push.assert_called_once()


def test_mover_repeated_para_baixo_quando_ultimo(qapp):
    """Garante que mover o último item para baixo não faz nada."""
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    with patch.object(undo_stack, 'push') as mock_push:
        controller.mover_repeated_para_baixo(croqui, "creditos", 2)
        mock_push.assert_not_called()

def test_mover_repeated_para_cima_quando_primeiro(qapp):
    """Garante que mover o primeiro item para cima não faz nada."""
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    with patch.object(undo_stack, 'push') as mock_push:
        controller.mover_repeated_para_cima(croqui, "creditos", 0)
        mock_push.assert_not_called()

def test_mover_repeated_quando_unico_elemento(qapp):
    """Garante que mover para cima ou para baixo num array de um elemento não faz nada."""
    croqui = Croqui()
    croqui.creditos.extend(["Unico"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    with patch.object(undo_stack, 'push') as mock_push:
        # Move para cima
        controller.mover_repeated_para_cima(croqui, "creditos", 0)
        mock_push.assert_not_called()
        
        # Move para baixo
        controller.mover_repeated_para_baixo(croqui, "creditos", 0)
        mock_push.assert_not_called()

def test_croqui_controller_adicionar_mapa_com_arquivo(qapp):
    from pathlib import Path
    from aresta_api.proto.generated.croqui_pb2 import Mapa
    from editor.commands.comandos_mapas import CmdAdicionarMapaArquivo
    
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    
    proxy = model.obter_croqui_readonly()
    proxy_setor = proxy.picos[0].setores_ou_grupos[0].setor.conteudo
    
    img_bytes = b"fake"
    caminho_absoluto = Path("/fake/path.webp")
    novo_mapa = Mapa()
    
    with patch.object(undo_stack, 'push') as mock_push:
        controller.adicionar_mapa_com_arquivo(proxy_setor, "mapas", 0, novo_mapa, caminho_absoluto, img_bytes)
        
        mock_push.assert_called_once()
        cmd = mock_push.call_args[0][0]
        assert isinstance(cmd, CmdAdicionarMapaArquivo)
        assert cmd.campo_nome == "mapas"
        assert cmd.index == 0
        assert cmd.caminho_absoluto == caminho_absoluto
        assert cmd.img_bytes == img_bytes


def test_croqui_controller_substituir_imagem(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    bytes_iniciais = b"antigo"
    bytes_novos = b"novo"
    model.definir_imagem_memoria("imagens/mapa.webp", bytes_iniciais)

    # Substitui a imagem
    controller.substituir_imagem("imagens/mapa.webp", bytes_novos)
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_novos
    assert undo_stack.count() == 1

    # Undo
    undo_stack.undo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_iniciais

    # Redo
    undo_stack.redo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_novos


def test_croqui_controller_alterar_campo_imagem(qapp):
    croqui = Croqui()
    croqui.caminho_thumbnail = "imagens/thumb_antiga.webp"
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    bytes_antigo = b"bytes_antigo"
    bytes_novo = b"bytes_novo"
    model.definir_imagem_memoria("imagens/thumb_antiga.webp", bytes_antigo)

    controller.alterar_campo_imagem(
        croqui, "caminho_thumbnail", "imagens/thumb_antiga.webp", bytes_antigo, "imagens/thumb_nova.webp", bytes_novo
    )
    assert croqui.caminho_thumbnail == "imagens/thumb_nova.webp"
    assert model.obter_bytes_imagem("imagens/thumb_nova.webp") == bytes_novo

    undo_stack.undo()
    assert croqui.caminho_thumbnail == "imagens/thumb_antiga.webp"
    assert model.obter_bytes_imagem("imagens/thumb_antiga.webp") == bytes_antigo


def test_croqui_controller_alterar_repeated_item(qapp):
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    pico_novo = Pico(nome="Pico 1 Modificado")
    controller.alterar_repeated_item(croqui, "picos", 0, pico, pico_novo)
    assert croqui.picos[0].nome == "Pico 1 Modificado"

    undo_stack.undo()
    assert croqui.picos[0].nome == "Pico 1"


def test_croqui_controller_grava_no_diario_com_gerenciador_historico(qapp, tmp_path):
    from editor.core.historico import GerenciadorHistorico
    from editor.core.diario import GerenciadorDiario

    croqui = Croqui(nome="Original")
    model = CroquiModel(croqui)
    diario = GerenciadorDiario(tmp_path)
    historico = GerenciadorHistorico(diario=diario)

    controller = CroquiController(model, historico)
    proxy = model.obter_croqui_readonly()

    # Executa mutação pelo controller
    controller.alterar_primitivo(proxy, "nome", "Original", "Modificado")

    assert proxy.nome == "Modificado"
    assert diario.tem_alteracoes_pendentes()
    comandos_pendentes = diario.ler_diario_pendente()
    assert len(comandos_pendentes) == 1
    assert comandos_pendentes[0]["classe"] == "CmdAlterarPrimitivo"
    assert comandos_pendentes[0]["valor_novo"] == "Modificado"


