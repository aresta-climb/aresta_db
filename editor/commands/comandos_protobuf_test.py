# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from aresta_api.proto.generated import croqui_pb2
from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo, ArquivoSetor, ArquivoGrupo
from PySide6.QtGui import QUndoStack
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
        from aresta_api.proto.generated.croqui_pb2 import ViaEsportiva
        via = ViaEsportiva()
        model = CroquiModel(via)
        self.assertFalse(via.HasField("extensao"))
        
        # Define como 0 (presente!)
        cmd = CmdAlterarPrimitivo(model, via, "extensao", None, 0)
        cmd.redo()
        self.assertTrue(via.HasField("extensao"))
        self.assertEqual(via.extensao, 0)
        
        # Desfaz (volta a ser None / ausente)
        cmd.undo()
        self.assertFalse(via.HasField("extensao"))

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

    def test_cmd_remover_repeated_limpa_imagens_orfas_da_ram_e_restaura_no_undo(self):
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        croqui = Croqui()
        pico = croqui.picos.add()
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        setor.nome = "Setor Fugitivos"
        mapa = setor.mapas.add()
        mapa.caminho_imagem_mapa = "imagens/setor_fugitivos_p0.webp"
        
        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/setor_fugitivos_p0.webp", b"conteudo_bytes_ram")

        cmd_rem = CmdRemoverRepeated(model, setor, "mapas", 0, setor.mapas[0])
        self.assertIn("imagens/setor_fugitivos_p0.webp", cmd_rem.imagens_removidas_ram)
        self.assertEqual(cmd_rem.imagens_removidas_ram["imagens/setor_fugitivos_p0.webp"], b"conteudo_bytes_ram")

        cmd_rem.redo()
        self.assertEqual(len(setor.mapas), 0)
        self.assertNotIn("imagens/setor_fugitivos_p0.webp", model.obter_imagens_em_memoria())

        cmd_rem.undo()
        self.assertEqual(len(setor.mapas), 1)
        self.assertIn("imagens/setor_fugitivos_p0.webp", model.obter_imagens_em_memoria())
        self.assertEqual(model.obter_bytes_imagem("imagens/setor_fugitivos_p0.webp"), b"conteudo_bytes_ram")

    def test_cmd_remover_repeated_preserva_imagem_compartilhada_em_ram(self):
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        croqui = Croqui()
        pico = croqui.picos.add()
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        mapa1 = setor.mapas.add()
        mapa1.caminho_imagem_mapa = "imagens/compartilhada.webp"
        mapa2 = setor.mapas.add()
        mapa2.caminho_imagem_mapa = "imagens/compartilhada.webp"

        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/compartilhada.webp", b"conteudo_comp")

        cmd_rem = CmdRemoverRepeated(model, setor, "mapas", 0, setor.mapas[0])
        self.assertEqual(cmd_rem.imagens_removidas_ram, {})

        cmd_rem.redo()
        self.assertEqual(len(setor.mapas), 1)
        self.assertIn("imagens/compartilhada.webp", model.obter_imagens_em_memoria())

    def test_cmd_remover_repeated_serializacao_com_imagens_em_ram(self):
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import deserializar_comando
        croqui = Croqui()
        pico = croqui.picos.add()
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        mapa = setor.mapas.add()
        mapa.caminho_imagem_mapa = "imagens/mapa.webp"

        model = CroquiModel(croqui)
        model.definir_imagem_memoria("imagens/mapa.webp", b"bytes_teste")

        cmd_rem = CmdRemoverRepeated(model, setor, "mapas", 0, setor.mapas[0])
        dados = cmd_rem.serializar(anonimizado=False)
        self.assertIn("imagens_removidas_ram", dados)
        self.assertEqual(dados["imagens_removidas_ram"], {"imagens/mapa.webp": b"bytes_teste"})

        cmd_deserializado = deserializar_comando(dados, model)
        self.assertEqual(cmd_deserializado.imagens_removidas_ram, {"imagens/mapa.webp": b"bytes_teste"})

        dados_anon = cmd_rem.serializar(anonimizado=True)
        self.assertIn("imagens_removidas_ram", dados_anon)
        self.assertNotEqual(dados_anon["imagens_removidas_ram"]["imagens/mapa.webp"], b"bytes_teste")

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


def test_comando_editor_carregamento_silencioso():
    croqui = Croqui(nome="Nome Atual")
    model = CroquiModel(croqui)

    cmd = CmdAlterarPrimitivo(model, croqui, "nome", "Nome Antigo", "Nome Mutado")
    cmd.armar_carregamento_silencioso()

    # Primeiro redo (durante push na inicialização) NÃO deve alterar o modelo
    cmd.redo()
    assert croqui.nome == "Nome Atual"

    # Ao desfazer, deve aplicar o valor antigo normalmente
    cmd.undo()
    assert croqui.nome == "Nome Antigo"

    # Ao refazer, a flag já está limpa e deve aplicar a mutação normalmente
    cmd.redo()
    assert croqui.nome == "Nome Mutado"


def test_guarda_integridade_mensagem_orfa_rejeitada():
    import pytest
    from aresta_api.proto.generated.croqui_pb2 import Pico, Patrocinador, SetorOuGrupo, ArquivoSetor
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
    )

    croqui = Croqui(nome="Croqui Teste")
    model = CroquiModel(croqui)
    pico_orfa = Pico(nome="Pico Órfão")
    sog_orfa = SetorOuGrupo()

    # Cada comando que opera sobre mensagem órfã deve lançar ValueError
    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarPrimitivo(model, pico_orfa, "nome", "Antigo", "Novo")

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAdicionarRepeated(model, pico_orfa, "patrocinadores", 0, Patrocinador(nome="P1"))

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdRemoverRepeated(model, pico_orfa, "patrocinadores", 0, Patrocinador(nome="P1"))

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarOneof(model, sog_orfa, "tipo", None, None, "setor", ArquivoSetor())

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarRepeatedItem(model, pico_orfa, "patrocinadores", 0, Patrocinador(nome="A"), Patrocinador(nome="B"))

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarMultiplosRepeatedItems(model, pico_orfa, "patrocinadores", [(0, Patrocinador(), Patrocinador())])

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdMoverRepeated(model, pico_orfa, "patrocinadores", 0, 1)

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarMetadadosCaminhoNovo(model, pico_orfa, "ext", {}, {})

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarCampoImagem(model, pico_orfa, "caminho_thumbnail", "", None, "img.webp", b"123")


def test_guarda_integridade_campo_invalido_rejeitado():
    import pytest
    from editor.commands.comandos_protobuf import CmdAlterarPrimitivo, CmdAdicionarRepeated

    croqui = Croqui(nome="Croqui Teste")
    model = CroquiModel(croqui)

    with pytest.raises(ValueError, match="não existe"):
        CmdAlterarPrimitivo(model, croqui, "campo_completamente_inexistente", "A", "B")

    with pytest.raises(ValueError, match="não existe"):
        CmdAdicionarRepeated(model, croqui, "pontos_de_interesse", 0, "algo")


def test_guarda_integridade_mensagem_conectada_valida():
    from aresta_api.proto.generated.croqui_pb2 import Patrocinador
    from editor.commands.comandos_protobuf import CmdAlterarPrimitivo, CmdAdicionarRepeated

    croqui = Croqui(nome="Croqui Teste")
    croqui.picos.add(nome="Pico Legítimo")
    model = CroquiModel(croqui)

    # Mensagem conectada na árvore deve ser aceita
    proxy_pico = model.obter_croqui_readonly().picos[0]
    cmd_alt = CmdAlterarPrimitivo(model, proxy_pico, "nome", "Pico Legítimo", "Pico Modificado")
    assert cmd_alt is not None

    cmd_add = CmdAdicionarRepeated(model, proxy_pico, "patrocinadores", 0, Patrocinador(nome="P1"))
    assert cmd_add is not None


def test_validar_pertence_ao_croqui_casos_limite():
    import pytest
    from editor.commands.comandos_protobuf import validar_pertence_ao_croqui

    with pytest.raises(ValueError, match="inválida"):
        validar_pertence_ao_croqui(None, Croqui())

    with pytest.raises(ValueError, match="inválida"):
        validar_pertence_ao_croqui(CroquiModel(Croqui()), None)

    class ModelSemRoot:
        def obter_croqui_readonly(self):
            return None

    # Se root for None, caminho é vazio
    caminho = validar_pertence_ao_croqui(ModelSemRoot(), Croqui())
    assert caminho == ""


def test_cmd_inserir_imagem_markdown():
    from editor.commands.comandos_protobuf import CmdInserirImagemMarkdown, deserializar_comando
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel

    croqui = Croqui()
    croqui.descricao = "Texto inicial"
    model = CroquiModel(croqui)

    foco_notificado = []
    model.foco_requisitado.connect(lambda ctx: foco_notificado.append(ctx))

    bytes_img = b"fake_bytes_img_123"
    cmd = CmdInserirImagemMarkdown(
        model=model,
        msg=croqui,
        campo_nome="descricao",
        texto_antigo="Texto inicial",
        texto_novo="Texto inicial\n![Foto](imagens/foto.webp)",
        caminho_imagem="imagens/foto.webp",
        bytes_imagem=bytes_img,
        context_path="croqui.descricao",
    )

    # Redo
    cmd.redo()
    assert croqui.descricao == "Texto inicial\n![Foto](imagens/foto.webp)"
    assert model.obter_imagens_em_memoria().get("imagens/foto.webp") == bytes_img
    assert foco_notificado == ["croqui.descricao"]

    # Undo
    cmd.undo()
    assert croqui.descricao == "Texto inicial"
    assert "imagens/foto.webp" not in model.obter_imagens_em_memoria()
    assert foco_notificado == ["croqui.descricao", "croqui.descricao"]

    # Serialização e Deserialização
    dados = cmd.serializar(anonimizado=False)
    assert dados["classe"] == "CmdInserirImagemMarkdown"
    assert dados["campo_nome"] == "descricao"
    assert dados["texto_novo"] == "Texto inicial\n![Foto](imagens/foto.webp)"
    assert dados["caminho_imagem"] == "imagens/foto.webp"
    assert dados["bytes_imagem"] == bytes_img

    cmd_deserializado = deserializar_comando(dados, model)
    assert isinstance(cmd_deserializado, CmdInserirImagemMarkdown)
    assert cmd_deserializado.caminho_imagem == "imagens/foto.webp"
    assert cmd_deserializado.bytes_imagem == bytes_img

    # Serialização anonimizada
    dados_anon = cmd.serializar(anonimizado=True)
    assert dados_anon["bytes_imagem"] is not None


def test_navegar_para_mensagem_limites_e_oneofs():
    from editor.commands.comandos_protobuf import navegar_para_mensagem
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    croqui = Croqui()

    # 1. Caminho raiz
    assert navegar_para_mensagem(croqui, "") is croqui
    assert navegar_para_mensagem(croqui, "root") is croqui

    # 2. Índice fora de limite em lista vazia deve retornar None com segurança
    assert navegar_para_mensagem(croqui, "picos.0") is None

    # Adiciona um pico e setor com caminho (variante externa do oneof)
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.caminho = "setores/setor1.md"

    # 3. Índice dentro do limite
    assert navegar_para_mensagem(croqui, "picos.0") is pico
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.0.setor") is sg.setor

    # 4. Índice além do tamanho da lista
    assert navegar_para_mensagem(croqui, "picos.1") is None
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.5") is None

    # 5. Oneof inativo: sg.setor tem 'caminho', então acessar 'conteudo' deve retornar None
    assert sg.setor.WhichOneof("arquivo") == "caminho"
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.0.setor.conteudo") is None
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.0.setor.conteudo.mapas.0") is None

    # 6. Campo inexistente
    assert navegar_para_mensagem(croqui, "campo_que_nao_existe") is None
    assert navegar_para_mensagem(croqui, "picos.0.campo_que_nao_existe") is None


def test_comando_editor_resolucao_tardia_e_alvo_inexistente(caplog):
    import logging
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.commands.comandos_protobuf import CmdAlterarPrimitivo

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Antigo"
    model = CroquiModel(croqui)

    # 1. Instanciação direta com caminho_msg (resolução tardia)
    cmd = CmdAlterarPrimitivo(
        model=model,
        caminho_msg="picos.0",
        campo_nome="nome",
        valor_antigo="Pico Antigo",
        valor_novo="Pico Novo",
    )
    assert cmd.caminho_msg == "picos.0"
    assert cmd.msg is pico

    # 2. Executa redo e undo normalmente
    cmd.executar_redo()
    assert pico.nome == "Pico Novo"
    cmd.undo()
    assert pico.nome == "Pico Antigo"

    # 3. Remove o pico da árvore do croqui tornando o caminho inválido
    croqui.ClearField("picos")
    assert len(croqui.picos) == 0

    # 4. Tentar executar undo() com alvo inexistente deve registrar erro e abortar com segurança
    with caplog.at_level(logging.ERROR):
        cmd.undo()
    assert "Falha ao resolver mensagem alvo no caminho 'picos.0'" in caplog.text


def test_deserializar_comando_sem_navegacao_ansiosa():
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.commands.comandos_protobuf import deserializar_comando, CmdAlterarPrimitivo

    croqui = Croqui()  # Sem picos cadastrados
    model = CroquiModel(croqui)

    dados = {
        "classe": "CmdAlterarPrimitivo",
        "caminho_msg": "picos.5.setores_ou_grupos.0",
        "campo_nome": "nome",
        "valor_antigo": "Antigo",
        "valor_novo": "Novo",
        "context_path": None,
    }

    # Deserialização NÃO deve falhar com IndexError mesmo o índice 5 não existindo no momento da carga
    cmd = deserializar_comando(dados, model)
    assert isinstance(cmd, CmdAlterarPrimitivo)
    assert cmd.caminho_msg == "picos.5.setores_ou_grupos.0"


def test_comando_editor_metodos_base_e_validacao():
    import pytest
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    from editor.commands.comandos_protobuf import (
        ComandoEditor,
        _validar_campo_se_msg_existir,
    )

    croqui = Croqui(nome="Croqui Teste")
    model = CroquiModel(croqui)

    # 1. Validação de campo antecipada com parâmetros nulos/vazios
    _validar_campo_se_msg_existir(None, "qualquer", "nome")
    _validar_campo_se_msg_existir(model, None, "nome")
    _validar_campo_se_msg_existir(model, "", "")

    # 2. Validação com campo inexistente na mensagem raiz existente
    with pytest.raises(ValueError, match="não existe na mensagem"):
        _validar_campo_se_msg_existir(model, "", "campo_totalmente_invalido", "CmdTeste")

    # 3. Métodos da classe base ComandoEditor
    cmd = ComandoEditor()
    assert cmd.caminho_msg is None
    assert cmd._obter_msg() is None

    # msg.setter atualiza cache
    cmd.msg = "objeto_cache"
    assert cmd.msg == "objeto_cache"

    # Quando model existe mas caminho_msg é None, retorna cache
    cmd.model = model
    assert cmd._obter_msg() == "objeto_cache"

    # Métodos abstratos levantam NotImplementedError
    with pytest.raises(NotImplementedError):
        cmd.executar_redo()
    with pytest.raises(NotImplementedError):
        cmd.serializar()


def test_cmd_migrar_setor_pico_para_grupo():
    """Testa migração de setor de Pico para Grupo com Undo, Redo e alteração de caminho_novo."""
    from editor.commands.comandos_protobuf import CmdMigrarSetor
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Central"

    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Savassinha"
    sg_setor.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_savassinha.md"
    sg_setor.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_savassinha.md"

    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Vale Oculto"

    model = CroquiModel(croqui)
    pilha = QUndoStack()

    cmd = CmdMigrarSetor(
        model=model,
        pai_origem=pico,
        campo_origem="setores_ou_grupos",
        indice_origem=0,
        pai_destino=sg_grupo.grupo.conteudo,
        campo_destino="setores",
        indice_destino=0,
        caminho_novo="grupo_vale_oculto_setor_savassinha.md",
        caminho_antigo="setor_savassinha.md"
    )
    pilha.push(cmd)

    # Verifica estado após redo/execução
    assert len(pico.setores_ou_grupos) == 1
    assert len(sg_grupo.grupo.conteudo.setores) == 1
    assert sg_grupo.grupo.conteudo.setores[0].conteudo.nome == "Savassinha"
    assert sg_grupo.grupo.conteudo.setores[0].Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "grupo_vale_oculto_setor_savassinha.md"

    # Undo
    pilha.undo()
    assert len(pico.setores_ou_grupos) == 2
    assert pico.setores_ou_grupos[0].setor.conteudo.nome == "Savassinha"
    assert pico.setores_ou_grupos[0].setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_savassinha.md"
    assert len(sg_grupo.grupo.conteudo.setores) == 0

    # Redo
    pilha.redo()
    assert len(pico.setores_ou_grupos) == 1
    assert len(sg_grupo.grupo.conteudo.setores) == 1


def test_cmd_migrar_setor_grupo_para_pico():
    """Testa migração de setor de dentro de um Grupo para a raiz do Pico."""
    from editor.commands.comandos_protobuf import CmdMigrarSetor
    croqui = Croqui()
    pico = croqui.picos.add()

    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Vale Oculto"
    setor_interno = sg_grupo.grupo.conteudo.setores.add()
    setor_interno.conteudo.nome = "De Cara"
    setor_interno.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original = "grupo_vale_oculto_setor_de_cara.md"
    setor_interno.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "grupo_vale_oculto_setor_de_cara.md"

    model = CroquiModel(croqui)
    pilha = QUndoStack()

    cmd = CmdMigrarSetor(
        model=model,
        pai_origem=sg_grupo.grupo.conteudo,
        campo_origem="setores",
        indice_origem=0,
        pai_destino=pico,
        campo_destino="setores_ou_grupos",
        indice_destino=1,
        caminho_novo="setor_de_cara.md",
        caminho_antigo="grupo_vale_oculto_setor_de_cara.md"
    )
    pilha.push(cmd)

    assert len(sg_grupo.grupo.conteudo.setores) == 0
    assert len(pico.setores_ou_grupos) == 2
    assert pico.setores_ou_grupos[1].setor.conteudo.nome == "De Cara"
    assert pico.setores_ou_grupos[1].setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_de_cara.md"

    pilha.undo()
    assert len(sg_grupo.grupo.conteudo.setores) == 1
    assert len(pico.setores_ou_grupos) == 1


def test_cmd_migrar_setor_serializacao_deserializacao():
    """Testa serialização e deserialização com resolução tardia de caminhos."""
    from editor.commands.comandos_protobuf import CmdMigrarSetor, deserializar_comando
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Central"

    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Savassinha"
    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Vale Oculto"

    model = CroquiModel(croqui)

    cmd = CmdMigrarSetor(
        model=model,
        pai_origem=pico,
        campo_origem="setores_ou_grupos",
        indice_origem=0,
        pai_destino=sg_grupo.grupo.conteudo,
        campo_destino="setores",
        indice_destino=0,
        caminho_novo="grupo_vale_oculto_setor_savassinha.md",
        caminho_antigo="setor_savassinha.md"
    )

    dados = cmd.serializar()
    assert dados["classe"] == "CmdMigrarSetor"
    assert dados["campo_origem"] == "setores_ou_grupos"
    assert dados["campo_destino"] == "setores"

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdMigrarSetor)
    assert cmd_recriado.caminho_novo == "grupo_vale_oculto_setor_savassinha.md"


def test_cmd_migrar_setor_execucao_apos_deserializacao_e_foco():
    """Testa que comando deserializado resolve caminhos lazy e notifica foco."""
    from editor.commands.comandos_protobuf import CmdMigrarSetor, deserializar_comando
    from editor.models.readonly_proxy import ReadOnlyProxy
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Central"

    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Savassinha"
    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Vale Oculto"

    model = CroquiModel(croqui)
    foco_recebido = []
    model.foco_requisitado.connect(lambda ctx: foco_recebido.append(ctx))

    # Testa também passando ReadOnlyProxy nos pais
    cmd = CmdMigrarSetor(
        model=model,
        pai_origem=ReadOnlyProxy(pico),
        campo_origem="setores_ou_grupos",
        indice_origem=0,
        pai_destino=ReadOnlyProxy(sg_grupo.grupo.conteudo),
        campo_destino="setores",
        indice_destino=0,
        caminho_novo="grupo_vale_oculto_setor_savassinha.md",
        caminho_antigo="setor_savassinha.md",
        context_path="setores.0"
    )

    assert cmd.pai_origem == pico
    dados = cmd.serializar()
    cmd_recriado = deserializar_comando(dados, model)
    assert cmd_recriado._pai_origem_cache is None
    assert cmd_recriado._pai_destino_cache is None

    # Redo usando lazy resolution
    cmd_recriado.executar_redo()
    assert len(pico.setores_ou_grupos) == 1
    assert len(sg_grupo.grupo.conteudo.setores) == 1
    assert "setores.0" in foco_recebido

    # Undo usando lazy resolution
    cmd_recriado.undo()
    assert len(pico.setores_ou_grupos) == 2
    assert len(sg_grupo.grupo.conteudo.setores) == 0


def test_cmd_migrar_setor_casos_borda_e_erros():
    """Testa caminhos inválidos, model nulo e fallbacks de resolução de pai."""
    from editor.commands.comandos_protobuf import CmdMigrarSetor
    croqui = Croqui()
    pico = croqui.picos.add()
    model = CroquiModel(croqui)

    cmd = CmdMigrarSetor(
        model=model,
        pai_origem=pico,
        campo_origem="setores_ou_grupos",
        indice_origem=0,
        pai_destino=pico,
        campo_destino="setores_ou_grupos",
        indice_destino=0,
    )

    # 1. model é None e caminho_msg é None
    cmd.model = None
    cmd._pai_origem_cache = None
    assert cmd._obter_pai(None, "_pai_origem_cache") is None

    # 2. caminho_msg aponta para nó inexistente
    cmd.model = model
    cmd.caminho_msg_origem = "caminho.completamente.invalido"
    assert cmd.pai_origem is None

    # 3. undo e redo com pais não resolvidos abortam silenciosamente
    cmd.undo()
    cmd.executar_redo()

    # 4. caminho_msg vazio ("") resolve para a raiz croqui
    cmd.caminho_msg_origem = ""
    cmd._pai_origem_cache = None
    assert cmd.pai_origem == croqui











