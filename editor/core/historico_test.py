# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from PyQt6.QtGui import QUndoCommand
from editor.core.historico import GerenciadorHistorico

class ComandoTeste(QUndoCommand):
    def __init__(self, estado, valor_antigo, valor_novo, id_merge=None):
        super().__init__()
        self.estado = estado
        self.valor_antigo = valor_antigo
        self.valor_novo = valor_novo
        self._id_merge = id_merge

    def undo(self):
        self.estado["valor"] = self.valor_antigo

    def redo(self):
        self.estado["valor"] = self.valor_novo

    def id(self):
        return self._id_merge if self._id_merge is not None else -1

    def mergeWith(self, outro):
        if self.id() != -1 and self.id() == outro.id():
            self.valor_novo = outro.valor_novo
            return True
        return False


class TestGerenciadorHistorico(unittest.TestCase):
    def test_fluxo_basico_undo_redo(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}
        
        cmd = ComandoTeste(estado, 0, 10)
        gerenciador.executar(cmd)
        self.assertEqual(estado["valor"], 10)
        
        gerenciador.desfazer()
        self.assertEqual(estado["valor"], 0)
        
        gerenciador.refazer()
        self.assertEqual(estado["valor"], 10)

    def test_merge_de_comandos(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}
        
        cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
        cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)
        
        gerenciador.executar(cmd1)
        self.assertEqual(estado["valor"], 5)
        
        gerenciador.executar(cmd2)
        self.assertEqual(estado["valor"], 10)
        
        # Como houve merge, a pilha deve conter apenas 1 comando.
        # Desfazer deve voltar direto para 0.
        gerenciador.desfazer()
        self.assertEqual(estado["valor"], 0)
        
        gerenciador.refazer()
        self.assertEqual(estado["valor"], 10)

    def test_foco_requisitado_emitido(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}
        
        cmd = ComandoTeste(estado, 0, 10)
        cmd.contexto_ui = "page:mapas/file:teste.md"
        
        focos_recebidos = []
        gerenciador.sinal_foco_requisitado.connect(focos_recebidos.append)
        
        gerenciador.executar(cmd) # Push não emite undo/redo na pilha de indexChanged? Push actually emits indexChanged!
        # Wait, push increases index from 0 to 1. diff > 0.
        # But should push emit foco_requisitado? Usually we want it on undo/redo.
        # Wait, if push emits it, it just re-focuses what the user just clicked. That's fine.
        
        # We will just assert that the signal was emitted at least once with the correct path.
        self.assertIn("page:mapas/file:teste.md", focos_recebidos)
        
        focos_recebidos.clear()
        gerenciador.desfazer()
        self.assertIn("page:mapas/file:teste.md", focos_recebidos)

    def test_cmd_remover_arquivo_fisico(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock
        from editor.core.historico import CmdRemoverArquivoFisico
        from editor.core.storage import GerenciadorCaminhos
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Prepara os caminhos
            arq_original = temp_path / "imagem.png"
            arq_original.write_text("conteudo da imagem", encoding="utf-8")
            
            lixeira_dir = temp_path / ".trash_interna"
            lixeira_dir.mkdir()
            
            # Mock do GerenciadorCaminhos
            gerenciador = MagicMock(spec=GerenciadorCaminhos)
            gerenciador.obter_caminho_lixeira.return_value = lixeira_dir
            
            # Cria o comando
            cmd = CmdRemoverArquivoFisico(arq_original, gerenciador)
            
            # Inicialmente, o arquivo existe no original
            self.assertTrue(arq_original.exists())
            
            # Executa o comando (redo) -> Deve mover para a lixeira
            cmd.redo()
            self.assertFalse(arq_original.exists())
            # Verifica que o arquivo foi para a lixeira
            arquivos_lixeira = list(lixeira_dir.glob("*"))
            self.assertEqual(len(arquivos_lixeira), 1)
            self.assertEqual(arquivos_lixeira[0].read_text(encoding="utf-8"), "conteudo da imagem")
            
            # Desfaz o comando (undo) -> Deve voltar para o original
            cmd.undo()
            self.assertTrue(arq_original.exists())
            self.assertEqual(arq_original.read_text(encoding="utf-8"), "conteudo da imagem")
            self.assertEqual(len(list(lixeira_dir.glob("*"))), 0)

    def test_gerenciador_historico_persiste_no_diario(self):
        import tempfile
        from pathlib import Path
        from editor.core.diario import GerenciadorDiario
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.models.croqui_model import CroquiModel
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            gerenciador = GerenciadorHistorico(diario=diario)
            
            croqui = Croqui(nome="Nome Original")
            model = CroquiModel(croqui)
            
            cmd = CmdAlterarPrimitivo(model, croqui, "nome", "Nome Original", "Nome Alterado")
            gerenciador.executar(cmd)
            
            # Verifica que foi persistido no diário pendente
            self.assertTrue(diario.tem_alteracoes_pendentes())
            comandos_lidos = diario.ler_diario_pendente()
            self.assertEqual(len(comandos_lidos), 1)
            self.assertEqual(comandos_lidos[0]["classe"], "CmdAlterarPrimitivo")
            self.assertEqual(comandos_lidos[0]["valor_novo"], "Nome Alterado")

    def test_gerenciador_historico_restaurar_do_diario(self):
        import tempfile
        from pathlib import Path
        from editor.core.diario import GerenciadorDiario
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.models.croqui_model import CroquiModel
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            
            # Grava 2 comandos no diário pendente
            cmd1_dict = {
                "classe": "CmdAlterarPrimitivo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Inicial",
                "valor_novo": "Intermediario",
                "context_path": None
            }
            cmd2_dict = {
                "classe": "CmdAlterarPrimitivo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Intermediario",
                "valor_novo": "Final",
                "context_path": None
            }
            diario.gravar_comando_pendente(cmd1_dict)
            diario.gravar_comando_pendente(cmd2_dict)
            
            # Restaura no gerenciador de histórico
            croqui = Croqui(nome="Inicial")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico()
            
            restaurados = gerenciador.restaurar_do_diario(model, diario)
            self.assertEqual(restaurados, 2)
            self.assertEqual(croqui.nome, "Final")
            
            # Verifica que a pilha permite Undo
            self.assertTrue(gerenciador.obter_pilha().canUndo())
            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Intermediario")
            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Inicial")

    def test_gerenciador_historico_carregar_diario_salvo(self):
        import tempfile
        from pathlib import Path
        from editor.core.diario import GerenciadorDiario
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            # Grava 2 comandos salvos no diario_salvo.bin
            diario.gravar_comando_pendente({
                "classe": "CmdAlterarPrimitivo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Inicial",
                "valor_novo": "Passo 1",
                "context_path": None
            })
            diario.gravar_comando_pendente({
                "classe": "CmdAlterarPrimitivo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Passo 1",
                "valor_novo": "Passo 2",
                "context_path": None
            })
            diario.consolidar_salvamento()

            # Ao reabrir o croqui, o modelo é carregado a partir do estado salvo (Passo 2)
            croqui = Croqui(nome="Passo 2")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico()

            carregados = gerenciador.carregar_diario_salvo(model, diario)
            self.assertEqual(carregados, 2)
            self.assertEqual(croqui.nome, "Passo 2")
            self.assertTrue(gerenciador.obter_pilha().isClean())
            self.assertTrue(gerenciador.obter_pilha().canUndo())

            # Testa Desfazer (Ctrl+Z)
            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Passo 1")
            self.assertFalse(gerenciador.obter_pilha().isClean())

            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Inicial")

            # Testa Refazer (Ctrl+Y)
            gerenciador.refazer()
            self.assertEqual(croqui.nome, "Passo 1")

            gerenciador.refazer()
            self.assertEqual(croqui.nome, "Passo 2")
            self.assertTrue(gerenciador.obter_pilha().isClean())

    def test_gerenciador_historico_restaurar_pendente_com_merge_keystrokes_e_undo_imediato(self):
        import tempfile
        from pathlib import Path
        from editor.core.diario import GerenciadorDiario
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.models.croqui_model import CroquiModel
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            # Sessão 1 (Ao Vivo): Usuário digita 5 caracteres em sequência
            croqui1 = Croqui(nome="Inicial")
            model1 = CroquiModel(croqui1)
            gerenciador1 = GerenciadorHistorico(diario=diario)

            palavras = ["N", "No", "Nom", "Nome", "Nome Final"]
            v_ant = "Inicial"
            for p in palavras:
                cmd = CmdAlterarPrimitivo(model1, croqui1, "nome", v_ant, p, "page:dados/node:root", pode_mesclar=True)
                gerenciador1.executar(cmd)
                v_ant = p

            # A pilha ao vivo deve ter mesclado para 1 único comando
            self.assertEqual(gerenciador1.obter_pilha().count(), 1)
            self.assertEqual(croqui1.nome, "Nome Final")

            # O diário pendente deve ter sido sincronizado para conter apenas o comando consolidado
            self.assertTrue(diario.tem_alteracoes_pendentes())
            comandos_gravados = diario.ler_diario_pendente()
            self.assertEqual(len(comandos_gravados), 1)
            self.assertEqual(comandos_gravados[0]["valor_antigo"], "Inicial")
            self.assertEqual(comandos_gravados[0]["valor_novo"], "Nome Final")

            # Sessão 2 (Pós-Crash / Reabertura):
            croqui2 = Croqui(nome="Inicial")
            model2 = CroquiModel(croqui2)
            gerenciador2 = GerenciadorHistorico()

            gerenciador2.restaurar_do_diario(model2, diario)

            # O modelo recuperado tem o valor final
            self.assertEqual(croqui2.nome, "Nome Final")
            self.assertEqual(gerenciador2.obter_pilha().count(), 1)

            # Com apenas 1 Undo, desfaz direto para o valor inicial antes de começar a digitar!
            gerenciador2.desfazer()
            self.assertEqual(croqui2.nome, "Inicial")

            # Com Redo, refaz para o valor final completo
            gerenciador2.refazer()
            self.assertEqual(croqui2.nome, "Nome Final")

    def test_gerenciador_historico_merge_repeated_item_e_sincronizacao_modelo_em_memoria(self):
        import tempfile
        from pathlib import Path
        from editor.core.diario import GerenciadorDiario
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.models.croqui_model import CroquiModel
        from editor.commands.comandos_protobuf import CmdAlterarRepeatedItem

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui = Croqui()
            croqui.creditos.append("Credito Original")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico(diario=diario)

            # Usuário digita alterações consecutivas no campo repetido creditos
            cmd1 = CmdAlterarRepeatedItem(model, croqui, "creditos", 0, "Credito Original", "Credito O", pode_mesclar=True)
            gerenciador.executar(cmd1)
            self.assertEqual(croqui.creditos[0], "Credito O")

            cmd2 = CmdAlterarRepeatedItem(model, croqui, "creditos", 0, "Credito O", "Credito Original Editado", pode_mesclar=True)
            gerenciador.executar(cmd2)
            # O modelo em memória DEVE ser mutado imediatamente mesmo com a mesclagem!
            self.assertEqual(croqui.creditos[0], "Credito Original Editado")
            self.assertEqual(gerenciador.obter_pilha().count(), 1)

            # 1 Undo restaura o estado inicial
            gerenciador.desfazer()
            self.assertEqual(croqui.creditos[0], "Credito Original")

