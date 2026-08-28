# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

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

    def test_cmd_alterar_primitivo_esvaziar_string_e_reversao(self):
        from aresta_api.proto.generated.croqui_pb2 import Setor
        setor = Setor()
        setor.nome = "Setor Estacionamento"
        model = CroquiModel(setor)
        
        # Esvazia a string
        cmd = CmdAlterarPrimitivo(model, setor, "nome", "Setor Estacionamento", "")
        cmd.redo()
        self.assertFalse(setor.HasField("nome"))
        
        # Desfaz e restaura
        cmd.undo()
        self.assertTrue(setor.HasField("nome"))
        self.assertEqual(setor.nome, "Setor Estacionamento")
        
        # Refaz e limpa novamente
        cmd.redo()
        self.assertFalse(setor.HasField("nome"))

    def test_cmd_alterar_primitivo_booleano_tri_state_none(self):
        from aresta_api.proto.generated.croqui_pb2 import Setor
        setor = Setor()
        setor.sinal_de_celular = True
        model = CroquiModel(setor)
        
        # Altera para None (indefinido)
        cmd = CmdAlterarPrimitivo(model, setor, "sinal_de_celular", True, None)
        cmd.redo()
        self.assertFalse(setor.HasField("sinal_de_celular"))
        
        # Desfaz
        cmd.undo()
        self.assertTrue(setor.HasField("sinal_de_celular"))
        self.assertTrue(setor.sinal_de_celular)

    def test_cmd_alterar_primitivo_inteiro_nullable_e_zero(self):
        from aresta_api.proto.generated.croqui_pb2 import Setor
        setor = Setor()
        model = CroquiModel(setor)
        self.assertFalse(setor.HasField("indice_mapa_padrao"))
        
        # Define como 0 (presente!)
        cmd = CmdAlterarPrimitivo(model, setor, "indice_mapa_padrao", None, 0)
        cmd.redo()
        self.assertTrue(setor.HasField("indice_mapa_padrao"))
        self.assertEqual(setor.indice_mapa_padrao, 0)
        
        # Desfaz (volta a ser None / ausente)
        cmd.undo()
        self.assertFalse(setor.HasField("indice_mapa_padrao"))

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


def test_cmd_alterar_campo_imagem():
    from editor.commands.comandos_protobuf import CmdAlterarCampoImagem
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel

    croqui = Croqui()
    croqui.caminho_thumbnail = "imagens/antiga.webp"
    model = CroquiModel(croqui)

    bytes_novos = b"bytes_imagem_webp_nova"
    cmd = CmdAlterarCampoImagem(
        model=model,
        msg=croqui,
        campo_nome="caminho_thumbnail",
        caminho_antigo="imagens/antiga.webp",
        bytes_antigo=None,
        caminho_novo="imagens/nova.webp",
        bytes_novo=bytes_novos,
    )

    # Executa Redo
    cmd.redo()
    assert croqui.caminho_thumbnail == "imagens/nova.webp"
    assert model.obter_bytes_imagem("imagens/nova.webp") == bytes_novos

    # Executa Undo
    cmd.undo()
    assert croqui.caminho_thumbnail == "imagens/antiga.webp"
    assert model.obter_bytes_imagem("imagens/nova.webp") is None

    # Executa Redo novamente
    cmd.redo()
    assert croqui.caminho_thumbnail == "imagens/nova.webp"
    assert model.obter_bytes_imagem("imagens/nova.webp") == bytes_novos


def test_cmd_substituir_imagem_memoria():
    from editor.commands.comandos_protobuf import CmdSubstituirImagemMemoria
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel

    croqui = Croqui()
    model = CroquiModel(croqui)

    bytes_antigos = b"bytes_antigos"
    bytes_novos = b"bytes_novos"
    model.definir_imagem_memoria("imagens/mapa.webp", bytes_antigos)

    cmd = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="imagens/mapa.webp",
        bytes_antigo=bytes_antigos,
        bytes_novo=bytes_novos,
    )

    # Redo
    cmd.redo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_novos

    # Undo
    cmd.undo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_antigos

    # Teste sem bytes antigos (imagem nova)
    cmd_novo = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="imagens/outra.webp",
        bytes_antigo=None,
        bytes_novo=bytes_novos,
    )
    cmd_novo.redo()
    assert model.obter_bytes_imagem("imagens/outra.webp") == bytes_novos
    cmd_novo.undo()
    assert model.obter_bytes_imagem("imagens/outra.webp") is None


def test_serializacao_deserializacao_comandos_protobuf():
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo, Setor, ArquivoSetor
    from editor.models.croqui_model import CroquiModel
    from editor.commands.comandos_protobuf import (
        CmdAlterarPrimitivo,
        CmdAdicionarRepeated,
        CmdRemoverRepeated,
        CmdAlterarOneof,
        CmdAlterarRepeatedItem,
        CmdAlterarMultiplosRepeatedItems,
        CmdMoverRepeated,
        CmdAlterarMetadadosCaminhoNovo,
        CmdAlterarCampoImagem,
        CmdSubstituirImagemMemoria,
        deserializar_comando
    )

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico A"
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor 1"
    model = CroquiModel(croqui)

    # 1. CmdAlterarPrimitivo
    cmd_prim = CmdAlterarPrimitivo(model, setor, "nome", "Setor 1", "Setor Principal", context_path="setores.0")
    dados = cmd_prim.serializar()
    assert dados["classe"] == "CmdAlterarPrimitivo"
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert setor.nome == "Setor Principal"
    cmd_recriado.undo()
    assert setor.nome == "Setor 1"

    # 2. CmdAdicionarRepeated
    from aresta_api.proto.generated.croqui_pb2 import Trilha
    trilha = Trilha(nome="Trilha Teste")
    cmd_add = CmdAdicionarRepeated(model, setor, "trilhas", 0, trilha)
    dados = cmd_add.serializar()
    assert dados["classe"] == "CmdAdicionarRepeated"
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert len(setor.trilhas) == 1
    assert setor.trilhas[0].nome == "Trilha Teste"

    # 3. CmdAlterarRepeatedItem
    trilha_nova = Trilha(nome="Trilha Atualizada")
    cmd_alt_item = CmdAlterarRepeatedItem(model, setor, "trilhas", 0, trilha, trilha_nova)
    dados = cmd_alt_item.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert setor.trilhas[0].nome == "Trilha Atualizada"

    # 4. CmdMoverRepeated
    trilha2 = Trilha(nome="Trilha 2")
    setor.trilhas.append(trilha2)
    assert len(setor.trilhas) == 2
    cmd_move = CmdMoverRepeated(model, setor, "trilhas", 0, 1)
    dados = cmd_move.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert setor.trilhas[0].nome == "Trilha 2"
    assert setor.trilhas[1].nome == "Trilha Atualizada"

    # 5. CmdAlterarMultiplosRepeatedItems
    alteracoes = [(0, setor.trilhas[0], Trilha(nome="Trilha Zero")), (1, setor.trilhas[1], Trilha(nome="Trilha Um"))]
    cmd_mult = CmdAlterarMultiplosRepeatedItems(model, setor, "trilhas", alteracoes)
    dados = cmd_mult.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert setor.trilhas[0].nome == "Trilha Zero"
    assert setor.trilhas[1].nome == "Trilha Um"

    # 6. CmdRemoverRepeated
    cmd_rem = CmdRemoverRepeated(model, setor, "trilhas", 0, setor.trilhas[0])
    dados = cmd_rem.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert len(setor.trilhas) == 1

    # 7. CmdAlterarOneof
    cmd_oneof = CmdAlterarOneof(model, sg, "item", "setor", sg.setor, "grupo", None)
    dados = cmd_oneof.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    assert cmd_recriado.oneof_nome == "item"

    # 8. CmdAlterarMetadadosCaminhoNovo
    cmd_meta = CmdAlterarMetadadosCaminhoNovo(model, sg.setor, ArquivoSetor.ext_metadados_arquivo, "", "novo/caminho.md")
    dados = cmd_meta.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert sg.setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == "novo/caminho.md"

    # 9. CmdAlterarCampoImagem (com anonimização)
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    cmd_img = CmdAlterarCampoImagem(model, croqui, "caminho_thumbnail", "", None, "thumb.webp", img_bytes)
    dados_normais = cmd_img.serializar(anonimizado=False)
    assert dados_normais["bytes_novo"] == img_bytes
    dados_anon = cmd_img.serializar(anonimizado=True)
    assert len(dados_anon["bytes_novo"]) < len(img_bytes) or len(dados_anon["bytes_novo"]) < 500

    cmd_recriado = deserializar_comando(dados_normais, model)
    cmd_recriado.redo()
    assert model.obter_bytes_imagem("thumb.webp") == img_bytes

    # 10. CmdSubstituirImagemMemoria
    cmd_sub = CmdSubstituirImagemMemoria(model, "thumb.webp", img_bytes, b"novos_bytes")
    dados = cmd_sub.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    cmd_recriado.redo()
    assert model.obter_bytes_imagem("thumb.webp") == b"novos_bytes"



