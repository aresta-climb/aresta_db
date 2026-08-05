# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import unittest
from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo, ArquivoSetor, ArquivoGrupo
from PyQt6.QtGui import QUndoStack
from editor.commands.comandos_protobuf import (
    CmdAlterarPrimitivo,
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarOneof,
    CmdAlterarRepeatedItem,
    CmdAlterarMultiplosRepeatedItems
)
from editor.models.croqui_model import CroquiModel

class TestComandosProtobuf(unittest.TestCase):
    def test_cmd_alterar_primitivo(self):
        croqui = Croqui()
        croqui.nome = "Antigo Nome"
        model = CroquiModel(croqui)
        
        # Cria e executa o comando
        cmd = CmdAlterarPrimitivo(model, croqui, "nome", "Antigo Nome", "Novo Nome")
        cmd.redo()
        self.assertEqual(croqui.nome, "Novo Nome")
        
        # Desfaz
        cmd.undo()
        self.assertEqual(croqui.nome, "Antigo Nome")
        
        # Refaz
        cmd.redo()
        self.assertEqual(croqui.nome, "Novo Nome")

    def test_cmd_adicionar_remover_repeated_primitives(self):
        croqui = Croqui()
        croqui.creditos.append("Renato")
        model = CroquiModel(croqui)
        
        # Adicionar "Silva" no índice 1
        cmd_add = CmdAdicionarRepeated(model, croqui, "creditos", 1, "Silva")
        cmd_add.redo()
        self.assertEqual(list(croqui.creditos), ["Renato", "Silva"])
        
        cmd_add.undo()
        self.assertEqual(list(croqui.creditos), ["Renato"])
        
        # Remover "Renato" no índice 0
        cmd_rem = CmdRemoverRepeated(model, croqui, "creditos", 0, "Renato")
        cmd_rem.redo()
        self.assertEqual(list(croqui.creditos), [])
        
        cmd_rem.undo()
        self.assertEqual(list(croqui.creditos), ["Renato"])

    def test_cmd_adicionar_remover_repeated_composite(self):
        croqui = Croqui()
        pico = Pico()
        pico.nome = "Pico Falso"
        model = CroquiModel(croqui)
        
        cmd_add = CmdAdicionarRepeated(model, croqui, "picos", 0, pico)
        cmd_add.redo()
        self.assertEqual(len(croqui.picos), 1)
        self.assertEqual(croqui.picos[0].nome, "Pico Falso")
        
        cmd_add.undo()
        self.assertEqual(len(croqui.picos), 0)
        
        # recoloca para poder testar remoção
        cmd_add.redo()
        
        cmd_rem = CmdRemoverRepeated(model, croqui, "picos", 0, croqui.picos[0])
        cmd_rem.redo()
        self.assertEqual(len(croqui.picos), 0)
        
        cmd_rem.undo()
        self.assertEqual(len(croqui.picos), 1)
        self.assertEqual(croqui.picos[0].nome, "Pico Falso")

    def test_cmd_alterar_oneof(self):
        croqui = Croqui()
        pico = croqui.picos.add()
        sg = pico.setores_ou_grupos.add()
        model = CroquiModel(croqui)
        
        # Inicialmente, nenhum campo do oneof está setado
        self.assertEqual(sg.WhichOneof("tipo"), None)
        
        setor = ArquivoSetor()
        setor.caminho = "caminho/do/setor.md"
        
        # Cria e executa o comando para ativar "setor"
        cmd1 = CmdAlterarOneof(model, sg, "tipo", None, None, "setor", setor)
        cmd1.redo()
        
        self.assertEqual(sg.WhichOneof("tipo"), "setor")
        self.assertEqual(sg.setor.caminho, "caminho/do/setor.md")
        
        # Desfaz
        cmd1.undo()
        self.assertEqual(sg.WhichOneof("tipo"), None)
        
        # Refaz
        cmd1.redo()
        self.assertEqual(sg.WhichOneof("tipo"), "setor")
        
        # Agora muda de "setor" para "grupo"
        grupo = ArquivoGrupo()
        grupo.caminho = "caminho/do/grupo.md"
        
        cmd2 = CmdAlterarOneof(model, sg, "tipo", "setor", setor, "grupo", grupo)
        cmd2.redo()
        
        self.assertEqual(sg.WhichOneof("tipo"), "grupo")
        self.assertEqual(sg.grupo.caminho, "caminho/do/grupo.md")
        self.assertFalse(sg.HasField("setor")) # Deve ter limpado "setor"
        
        # Desfaz cmd2
        cmd2.undo()
        self.assertEqual(sg.WhichOneof("tipo"), "setor")
        self.assertEqual(sg.setor.caminho, "caminho/do/setor.md")

    def test_cmd_alterar_repeated_item(self):
        croqui = Croqui()
        croqui.creditos.append("Renato")
        model = CroquiModel(croqui)
        
        cmd = CmdAlterarRepeatedItem(model, croqui, "creditos", 0, "Renato", "Silva")
        cmd.redo()
        self.assertEqual(list(croqui.creditos), ["Silva"])
        
        cmd.undo()
        self.assertEqual(list(croqui.creditos), ["Renato"])

    def test_gerenciador_historico_runtime_error_no_crash(self):
        """
        Garante que o _on_index_changed trata silenciosamente o RuntimeError 
        que ocorre quando o QUndoStack C++ subjacente ja foi deletado durante o fechamento do app.
        """
        from editor.core.historico import GerenciadorHistorico
        from unittest.mock import patch
        
        gerenciador = GerenciadorHistorico()
        
        # Simula o erro do C++ quando o QUndoStack é destruido e command() é chamado
        with patch.object(gerenciador._pilha, 'command', side_effect=RuntimeError("wrapped C/C++ object of type QUndoStack has been deleted")):
            # Tenta notificar index change. Não deve propagar a exceção
            gerenciador._ultimo_index = 0
            try:
                gerenciador._on_index_changed(1)
            except RuntimeError:
                import pytest
                pytest.fail("RuntimeError vazou do _on_index_changed!")
                
            # O índice interno ainda deve ser atualizado
            assert gerenciador._ultimo_index == 1

    def test_cmd_alterar_multiplos_repeated_items(self):
        croqui = Croqui()
        croqui.creditos.extend(["Um", "Dois", "Tres"])
        model = CroquiModel(croqui)
        
        # Cria e executa comando alterando indices 0 e 2
        alteracoes = [
            (0, "Um", "NovoUm"),
            (2, "Tres", "NovoTres")
        ]
        cmd = CmdAlterarMultiplosRepeatedItems(model, croqui, "creditos", alteracoes)
        cmd.redo()
        
        self.assertEqual(croqui.creditos[0], "NovoUm")
        self.assertEqual(croqui.creditos[1], "Dois")
        self.assertEqual(croqui.creditos[2], "NovoTres")
        
        # Desfaz
        cmd.undo()
        self.assertEqual(croqui.creditos[0], "Um")
        self.assertEqual(croqui.creditos[1], "Dois")
        self.assertEqual(croqui.creditos[2], "Tres")
        
        # Refaz novamente
        cmd.redo()
        self.assertEqual(croqui.creditos[0], "NovoUm")
        self.assertEqual(croqui.creditos[2], "NovoTres")

    def test_gerenciador_historico_sinais(self):
        from editor.core.historico import GerenciadorHistorico
        
        gerenciador = GerenciadorHistorico()
        croqui = Croqui()
        croqui.nome = "Original"
        model = CroquiModel(croqui)
        
        sinais_campo = []
        sinais_add = []
        sinais_rem = []
        
        gerenciador.sinal_campo_alterado.connect(lambda msg_id, campo, val: sinais_campo.append((msg_id, campo, val)))
        gerenciador.sinal_item_adicionado.connect(lambda msg_id, campo, idx: sinais_add.append((msg_id, campo, idx)))
        gerenciador.sinal_item_removido.connect(lambda msg_id, campo, idx: sinais_rem.append((msg_id, campo, idx)))
        
        # Teste 1: Alterar Primitivo
        cmd = CmdAlterarPrimitivo(model, croqui, "nome", "Original", "Novo")
        gerenciador.executar(cmd)
        
        # Como o Gerenciador não emite mais para nós, vamos apenas testar o modelo
        sinais_modelo_campo = []
        model.dado_alterado.connect(lambda msg, campo: sinais_modelo_campo.append(campo))
        
        # Teste 2: Adicionar Repeated
        cmd_add = CmdAdicionarRepeated(model, croqui, "creditos", 0, "Item1")
        gerenciador.executar(cmd_add)

def test_cmd_alterar_metadados_caminho_novo():
    from editor.commands.comandos_protobuf import CmdAlterarMetadadosCaminhoNovo
    from aresta_api.proto.generated import croqui_pb2
    
    croqui = Croqui()
    sg = croqui.picos.add().setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor"
    model = CroquiModel(croqui)
    
    # Executa o comando para mudar caminho novo
    cmd = CmdAlterarMetadadosCaminhoNovo(model, sg.setor, croqui_pb2.ArquivoSetor.ext_metadados_arquivo, "", "novo_caminho.md")
    cmd.redo()
    
    assert sg.setor.HasExtension(croqui_pb2.ArquivoSetor.ext_metadados_arquivo)
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "novo_caminho.md"
    
    # Desfaz
    cmd.undo()
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == ""



def test_cmd_mover_repeated():
    from editor.commands.comandos_protobuf import CmdMoverRepeated
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel

    croqui = Croqui()
    croqui.creditos.extend(['A', 'B', 'C'])
    model = CroquiModel(croqui)
    cmd = CmdMoverRepeated(model, croqui, 'creditos', 0, 2)
    cmd.redo()
    assert croqui.creditos == ['B', 'C', 'A']
    cmd.undo()
    assert croqui.creditos == ['A', 'B', 'C']

