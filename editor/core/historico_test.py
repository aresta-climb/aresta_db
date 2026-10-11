# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest

from PySide6.QtGui import QUndoCommand

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
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])

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

    def test_merge_comandos_preserva_cache_diario(self):
        import tempfile
        from pathlib import Path

        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as tmpdir:
            diario = GerenciadorDiario(Path(tmpdir))
            cmd_salvo = {"classe": "CmdSalvo", "valor": 1}
            diario.gravar_comando_pendente(cmd_salvo)
            diario.consolidar_salvamento()
            diario.exportar_diario_anonimizado()

            gerenciador = GerenciadorHistorico(diario=diario)
            estado = {"valor": 0}

            # Substitui ler_diario_salvo por spy para verificar releitura
            leituras_disco = []
            orig_ler_salvo = diario.ler_diario_salvo

            def spy_ler():
                leituras_disco.append(True)
                return orig_ler_salvo()

            diario.ler_diario_salvo = spy_ler

            cmd1 = ComandoTeste(estado, 0, 5, id_merge=101)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=101)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)

            # Ao exportar após o merge, o cache de comandos salvos não deve ter sido descartado
            diario.exportar_diario_anonimizado()

            self.assertEqual(
                len(leituras_disco),
                0,
                "O histórico não deve reler diario_salvo.bin do disco após merge de comandos",
            )

    def test_foco_requisitado_emitido(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}

        cmd = ComandoTeste(estado, 0, 10)
        cmd.contexto_ui = "page:mapas/file:teste.md"

        focos_recebidos = []
        gerenciador.sinal_foco_requisitado.connect(focos_recebidos.append)

        gerenciador.executar(
            cmd
        )  # Push não emite undo/redo na pilha de indexChanged? Push actually emits indexChanged!
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

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
        from editor.core.diario import GerenciadorDiario
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

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.core.diario import GerenciadorDiario
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
                "context_path": None,
            }
            cmd2_dict = {
                "classe": "CmdAlterarPrimitivo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Intermediario",
                "valor_novo": "Final",
                "context_path": None,
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

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            # Grava 2 comandos salvos no diario_salvo.bin
            diario.gravar_comando_pendente(
                {
                    "classe": "CmdAlterarPrimitivo",
                    "caminho_msg": "",
                    "campo_nome": "nome",
                    "valor_antigo": "Inicial",
                    "valor_novo": "Passo 1",
                    "context_path": None,
                }
            )
            diario.gravar_comando_pendente(
                {
                    "classe": "CmdAlterarPrimitivo",
                    "caminho_msg": "",
                    "campo_nome": "nome",
                    "valor_antigo": "Passo 1",
                    "valor_novo": "Passo 2",
                    "context_path": None,
                }
            )
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

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

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
                cmd = CmdAlterarPrimitivo(
                    model1, croqui1, "nome", v_ant, p, "page:dados/node:root", pode_mesclar=True
                )
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

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import CmdAlterarRepeatedItem
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui = Croqui()
            croqui.creditos.append("Credito Original")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico(diario=diario)

            # Usuário digita alterações consecutivas no campo repetido creditos
            cmd1 = CmdAlterarRepeatedItem(
                model, croqui, "creditos", 0, "Credito Original", "Credito O", pode_mesclar=True
            )
            gerenciador.executar(cmd1)
            self.assertEqual(croqui.creditos[0], "Credito O")

            cmd2 = CmdAlterarRepeatedItem(
                model,
                croqui,
                "creditos",
                0,
                "Credito O",
                "Credito Original Editado",
                pode_mesclar=True,
            )
            gerenciador.executar(cmd2)
            # O modelo em memória DEVE ser mutado imediatamente mesmo com a mesclagem!
            self.assertEqual(croqui.creditos[0], "Credito Original Editado")
            self.assertEqual(gerenciador.obter_pilha().count(), 1)

            # 1 Undo restaura o estado inicial
            gerenciador.desfazer()
            self.assertEqual(croqui.creditos[0], "Credito Original")

    def test_restaurar_do_diario_ignora_comando_orfa_ou_corrompido(self):
        import tempfile
        from pathlib import Path

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui_orig = Croqui(nome="Original")
            croqui_orig.creditos.append("Credito 1")
            model_orig = CroquiModel(croqui_orig)

            # Grava comando 1: válido
            cmd1 = CmdAlterarPrimitivo(model_orig, croqui_orig, "nome", "Original", "Passo 1")
            diario.gravar_comando_pendente(cmd1)

            # Grava comando 2: corrompido / órfão (campo inexistente na raiz)
            cmd_orfa = {
                "classe": "CmdAdicionarRepeated",
                "caminho_msg": "",
                "campo_nome": "pontos_de_interesse",
                "index": 0,
                "valor": {},
                "context_path": None,
            }
            diario.gravar_comando_pendente(cmd_orfa)

            # Grava comando 3: válido
            cmd3 = CmdAlterarPrimitivo(model_orig, croqui_orig, "nome", "Passo 1", "Passo 2")
            diario.gravar_comando_pendente(cmd3)

            # Restaura em um novo modelo
            croqui_novo = Croqui(nome="Original")
            croqui_novo.creditos.append("Credito 1")
            model_novo = CroquiModel(croqui_novo)
            gerenciador = GerenciadorHistorico()

            total_restaurados = gerenciador.restaurar_do_diario(model_novo, diario)

            # O comando 2 órfão deve ser ignorado sem interromper a restauração do comando 3
            self.assertEqual(total_restaurados, 2)
            self.assertEqual(croqui_novo.nome, "Passo 2")

    def test_carregar_comandos_salvos_ignora_comando_corrompido(self):
        import tempfile
        from pathlib import Path

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui_orig = Croqui(nome="Original")
            model_orig = CroquiModel(croqui_orig)

            cmd1 = CmdAlterarPrimitivo(model_orig, croqui_orig, "nome", "Original", "Passo 1")
            diario.gravar_comando_pendente(cmd1)

            cmd_invalido = {
                "classe": "CmdAlterarPrimitivo",
                "caminho_msg": "",
                "campo_nome": "campo_inexistente",
                "valor_antigo": "A",
                "valor_novo": "B",
            }
            diario.gravar_comando_pendente(cmd_invalido)

            cmd3 = CmdAlterarPrimitivo(model_orig, croqui_orig, "nome", "Passo 1", "Passo 2")
            diario.gravar_comando_pendente(cmd3)

            diario.consolidar_salvamento()

            croqui_novo = Croqui(nome="Passo 2")
            model_novo = CroquiModel(croqui_novo)
            gerenciador = GerenciadorHistorico()

            total_carregados = gerenciador.carregar_diario_salvo(model_novo, diario)

            # Ambos os comandos válidos devem ser carregados
            self.assertEqual(total_carregados, 2)

    def test_replay_diario_trata_excecao_generica_inesperada(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            diario.gravar_comando_pendente({"classe": "CmdTeste"})

            gerenciador = GerenciadorHistorico()
            model = CroquiModel(Croqui())

            with patch(
                "editor.commands.comandos_protobuf.deserializar_comando",
                side_effect=RuntimeError("Erro inesperado"),
            ):
                res_pendente = gerenciador.restaurar_do_diario(model, diario)
                self.assertEqual(res_pendente, 0)

            diario.gravar_comando_pendente({"classe": "CmdTeste"})
            diario.consolidar_salvamento()
            with patch(
                "editor.commands.comandos_protobuf.deserializar_comando",
                side_effect=RuntimeError("Erro inesperado"),
            ):
                res_salvo = gerenciador.carregar_diario_salvo(model, diario)
                self.assertEqual(res_salvo, 0)

    def test_carregar_diario_salvo_e_restaurar_tratam_index_error_como_warning(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            diario.gravar_comando_pendente({"classe": "CmdComIndexError"})

            gerenciador = GerenciadorHistorico()
            model = CroquiModel(Croqui())

            # Testar restaurar_do_diario com IndexError
            with patch(
                "editor.commands.comandos_protobuf.deserializar_comando",
                side_effect=IndexError("list index out of range"),
            ):
                with self.assertLogs("aresta_editor.historico", level="WARNING") as cm_warn:
                    total = gerenciador.restaurar_do_diario(model, diario)
                    self.assertEqual(total, 0)
                self.assertTrue(
                    any(
                        "Comando corrompido ou órfão descartado do diário pendente" in log
                        for log in cm_warn.output
                    )
                )
                self.assertFalse(any("Erro inesperado" in log for log in cm_warn.output))

            # Testar carregar_diario_salvo com IndexError
            diario.gravar_comando_pendente({"classe": "CmdComIndexError"})
            diario.consolidar_salvamento()
            with patch(
                "editor.commands.comandos_protobuf.deserializar_comando",
                side_effect=IndexError("list index out of range"),
            ):
                with self.assertLogs("aresta_editor.historico", level="WARNING") as cm_warn:
                    total = gerenciador.carregar_diario_salvo(model, diario)
                    self.assertEqual(total, 0)
                self.assertTrue(
                    any(
                        "Comando corrompido ou órfão descartado do diário salvo" in log
                        for log in cm_warn.output
                    )
                )
                self.assertFalse(any("Erro inesperado" in log for log in cm_warn.output))

    def test_sincronizar_diario_pendente_com_debounce(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock

        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            diario.substituir_comandos_pendentes = MagicMock()

            gerenciador = GerenciadorHistorico(diario=diario)
            self.assertEqual(gerenciador.intervalo_debounce_ms, 300)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)
            cmd3 = ComandoTeste(estado, 10, 15, id_merge=42)

            # 1. Executa primeiro comando
            gerenciador.executar(cmd1)
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 0)

            # 2. Executa comandos mescláveis sucessivos: devem ser agrupados pelo debounce sem I/O imediato
            gerenciador.executar(cmd2)
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 0)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            gerenciador.executar(cmd3)
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 0)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            # 3. flush_diario_pendente força a persistência pendente no disco
            gerenciador.flush_diario_pendente()
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 1)
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())

    def test_comando_novo_nao_mesclado_faz_flush_antes(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock

        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            diario.substituir_comandos_pendentes = MagicMock()
            diario.gravar_comando_pendente = MagicMock()

            gerenciador = GerenciadorHistorico(diario=diario)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)
            cmd_novo = ComandoTeste(estado, 10, 20, id_merge=None)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 0)

            # Executar novo comando não mesclado deve chamar flush antes de gravar o novo
            gerenciador.executar(cmd_novo)
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 1)
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())
            self.assertEqual(diario.gravar_comando_pendente.call_count, 2)

    def test_debounce_zero_sincroniza_imediatamente(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock

        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            diario.substituir_comandos_pendentes = MagicMock()

            gerenciador = GerenciadorHistorico(diario=diario)
            gerenciador.intervalo_debounce_ms = 0

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)

            # Com debounce 0, a persistência deve ocorrer imediatamente na mesclagem
            self.assertEqual(diario.substituir_comandos_pendentes.call_count, 1)
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())

    def test_desfazer_e_refazer_fazem_flush_diario(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock

        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            diario.substituir_comandos_pendentes = MagicMock()

            gerenciador = GerenciadorHistorico(diario=diario)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            # Ao desfazer, deve forçar flush antes e atualizar o diário
            gerenciador.desfazer()
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())
            self.assertTrue(diario.substituir_comandos_pendentes.call_count >= 1)

            # Refazer
            gerenciador.refazer()
            self.assertTrue(diario.substituir_comandos_pendentes.call_count >= 2)

    def test_limpar_para_timer_debounce(self):
        import tempfile
        from pathlib import Path

        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            gerenciador = GerenciadorHistorico(diario=diario)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            gerenciador.limpar()
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())

    def test_carregar_diario_salvo_silencia_sinais_ui(self):
        """Verifica que carregar_diario_salvo silencia a emissão de sinais para a UI."""
        import tempfile
        from pathlib import Path

        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
        from editor.core.diario import GerenciadorDiario
        from editor.models.croqui_model import CroquiModel

        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui_orig = Croqui(nome="Original")
            model_orig = CroquiModel(croqui_orig)

            cmd1 = CmdAlterarPrimitivo(model_orig, croqui_orig, "nome", "Original", "Passo 1")
            cmd2 = CmdAlterarPrimitivo(model_orig, croqui_orig, "nome", "Passo 1", "Passo 2")
            diario.gravar_comando_pendente(cmd1)
            diario.gravar_comando_pendente(cmd2)
            diario.consolidar_salvamento()

            croqui_novo = Croqui(nome="Passo 2")
            model_novo = CroquiModel(croqui_novo)
            gerenciador = GerenciadorHistorico()

            sinais_emitidos = []
            gerenciador.sinal_campo_alterado.connect(
                lambda *args: sinais_emitidos.append(("campo", args))
            )
            gerenciador.sinal_item_adicionado.connect(
                lambda *args: sinais_emitidos.append(("adicionado", args))
            )
            gerenciador.sinal_item_removido.connect(
                lambda *args: sinais_emitidos.append(("removido", args))
            )
            gerenciador.sinal_foco_requisitado.connect(
                lambda *args: sinais_emitidos.append(("foco", args))
            )

            total_carregados = gerenciador.carregar_diario_salvo(model_novo, diario)

            self.assertEqual(total_carregados, 2)
            self.assertEqual(gerenciador._pilha.count(), 2)
            # Nenhum sinal deve ter sido emitido durante a carga do diário salvo
            self.assertEqual(len(sinais_emitidos), 0)

    def test_despachar_sinal_descarta_comando_sem_mensagem_alvo(self):
        """Verifica que _despachar_sinal descarta graciosamente comandos cuja mensagem não pode ser resolvida sem emitir com id(None)."""
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import (
            CmdAdicionarRepeated,
            CmdAlterarMultiplosRepeatedItems,
            CmdAlterarOneof,
            CmdAlterarPrimitivo,
            CmdAlterarRepeatedItem,
            CmdRemoverRepeated,
            CmdRenomearEscalada,
        )
        from editor.models.croqui_model import CroquiModel

        croqui = Croqui()
        model = CroquiModel(croqui)
        gerenciador = GerenciadorHistorico()

        sinais_emitidos = []
        gerenciador.sinal_campo_alterado.connect(
            lambda *args: sinais_emitidos.append(("campo", args))
        )
        gerenciador.sinal_item_adicionado.connect(
            lambda *args: sinais_emitidos.append(("adicionado", args))
        )
        gerenciador.sinal_item_removido.connect(
            lambda *args: sinais_emitidos.append(("removido", args))
        )

        # Comando com caminho inexistente e _msg_cache nulo
        cmd_primitivo = CmdAlterarPrimitivo(model, croqui, "nome", "A", "B")
        cmd_primitivo._caminho_msg = "picos.99.setor"
        cmd_primitivo._msg_cache = None

        gerenciador._despachar_sinal(cmd_primitivo, is_undo=False)
        gerenciador._despachar_sinal(cmd_primitivo, is_undo=True)

        cmd_renomear = CmdRenomearEscalada(
            model=model, msg_escalada=croqui, campo_nome="nome", nome_antigo="A", nome_novo="B"
        )
        cmd_renomear._caminho_msg = "picos.99.via"
        cmd_renomear._msg_cache = None
        cmd_renomear._referencias_cache = [None]
        gerenciador._despachar_sinal(cmd_renomear, is_undo=False)

        cmd_add = CmdAdicionarRepeated(
            model=model, msg=croqui, campo_nome="creditos", index=0, valor="teste"
        )
        cmd_add._caminho_msg = "picos.99"
        cmd_add._msg_cache = None
        gerenciador._despachar_sinal(cmd_add, is_undo=False)
        gerenciador._despachar_sinal(cmd_add, is_undo=True)

        cmd_rem = CmdRemoverRepeated(model=model, msg=croqui, campo_nome="creditos", index=0)
        cmd_rem._caminho_msg = "picos.99"
        cmd_rem._msg_cache = None
        gerenciador._despachar_sinal(cmd_rem, is_undo=False)
        gerenciador._despachar_sinal(cmd_rem, is_undo=True)

        cmd_item = CmdAlterarRepeatedItem(
            model=model,
            msg=croqui,
            campo_nome="creditos",
            index=0,
            valor_antigo="A",
            valor_novo="B",
        )
        cmd_item._caminho_msg = "picos.99"
        cmd_item._msg_cache = None
        gerenciador._despachar_sinal(cmd_item, is_undo=False)

        cmd_mult = CmdAlterarMultiplosRepeatedItems(
            model=model, msg=croqui, campo_nome="creditos", alteracoes=[(0, "A", "B")]
        )
        cmd_mult._caminho_msg = "picos.99"
        cmd_mult._msg_cache = None
        gerenciador._despachar_sinal(cmd_mult, is_undo=False)

        cmd_oneof = CmdAlterarOneof(
            model=model, msg=croqui, oneof_nome="detalhe", nome_antigo=None, nome_novo=None
        )
        cmd_oneof._caminho_msg = "picos.99"
        cmd_oneof._msg_cache = None
        gerenciador._despachar_sinal(cmd_oneof, is_undo=False)

        # Nenhum sinal deve ter sido emitido com id(None)
        for _tipo, args in sinais_emitidos:
            self.assertNotEqual(args[0], id(None))
        self.assertEqual(len(sinais_emitidos), 0)

    def test_despachar_sinal_sucesso_todos_comandos(self):
        """Valida que todos os tipos de comando emitem os sinais esperados ao despachar com mensagem válida."""
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        from editor.commands.comandos_protobuf import (
            CmdAdicionarRepeated,
            CmdAlterarMultiplosRepeatedItems,
            CmdAlterarOneof,
            CmdAlterarPrimitivo,
            CmdAlterarRepeatedItem,
            CmdRemoverRepeated,
            CmdRenomearEscalada,
        )
        from editor.models.croqui_model import CroquiModel

        croqui = Croqui()
        croqui.nome = "Pico"
        croqui.creditos.append("Autor")
        model = CroquiModel(croqui)
        gerenciador = GerenciadorHistorico()

        sinais_campo = []
        sinais_adicionado = []
        sinais_removido = []
        gerenciador.sinal_campo_alterado.connect(lambda *args: sinais_campo.append(args))
        gerenciador.sinal_item_adicionado.connect(lambda *args: sinais_adicionado.append(args))
        gerenciador.sinal_item_removido.connect(lambda *args: sinais_removido.append(args))

        # 1. CmdAlterarPrimitivo
        cmd_prim = CmdAlterarPrimitivo(model, croqui, "nome", "Pico", "Novo Pico")
        gerenciador._despachar_sinal(cmd_prim, is_undo=False)
        self.assertEqual(len(sinais_campo), 1)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Novo Pico"))

        # 2. CmdRenomearEscalada
        ref_mock = Croqui()
        cmd_ren = CmdRenomearEscalada(
            model=model, msg_escalada=croqui, campo_nome="nome", nome_antigo="V1", nome_novo="V2"
        )
        cmd_ren._referencias_cache = [ref_mock]
        gerenciador._despachar_sinal(cmd_ren, is_undo=False)
        self.assertEqual(sinais_campo[-2], (id(croqui), "nome", "V2"))
        self.assertEqual(sinais_campo[-1], (id(ref_mock), "escalada", "V2"))

        # 3. CmdAdicionarRepeated (redo e undo)
        cmd_add = CmdAdicionarRepeated(
            model=model, msg=croqui, campo_nome="creditos", index=0, valor="Novo Autor"
        )
        gerenciador._despachar_sinal(cmd_add, is_undo=False)
        self.assertEqual(sinais_adicionado[-1], (id(croqui), "creditos", 0))
        gerenciador._despachar_sinal(cmd_add, is_undo=True)
        self.assertEqual(sinais_removido[-1], (id(croqui), "creditos", 0))

        # 4. CmdRemoverRepeated (redo e undo)
        cmd_rem = CmdRemoverRepeated(model=model, msg=croqui, campo_nome="creditos", index=0)
        gerenciador._despachar_sinal(cmd_rem, is_undo=False)
        self.assertEqual(sinais_removido[-1], (id(croqui), "creditos", 0))
        gerenciador._despachar_sinal(cmd_rem, is_undo=True)
        self.assertEqual(sinais_adicionado[-1], (id(croqui), "creditos", 0))

        # 5. CmdAlterarRepeatedItem
        cmd_item = CmdAlterarRepeatedItem(
            model=model,
            msg=croqui,
            campo_nome="creditos",
            index=0,
            valor_antigo="Autor",
            valor_novo="Autor Editado",
        )
        gerenciador._despachar_sinal(cmd_item, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "creditos[0]", "Autor Editado"))

        # 6. CmdAlterarMultiplosRepeatedItems
        cmd_mult = CmdAlterarMultiplosRepeatedItems(
            model=model,
            msg=croqui,
            campo_nome="creditos",
            alteracoes=[(0, "Autor", "Autor Modificado")],
        )
        gerenciador._despachar_sinal(cmd_mult, is_undo=False)
        self.assertEqual(
            sinais_campo[-1], (id(croqui), "creditos", [(0, "Autor", "Autor Modificado")])
        )

        # 7. CmdAlterarOneof
        cmd_oneof = CmdAlterarOneof(
            model=model,
            msg=croqui,
            oneof_nome="detalhe",
            nome_antigo="vazio",
            nome_novo="preenchido",
        )
        gerenciador._despachar_sinal(cmd_oneof, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "detalhe", "preenchido"))

        # 8. Comando com atributo msg sem _obter_msg (cobre fallback de comando customizado)
        class MockCmd(CmdAlterarPrimitivo):
            _obter_msg = None
            msg = None

            def __init__(self, msg_val):
                self.msg = msg_val
                self.campo_nome = "nome"
                self.valor_antigo = "A"
                self.valor_novo = "B"

            def childCount(self):
                return 0

        cmd_prim_sem_obter = MockCmd(croqui)
        gerenciador._despachar_sinal(cmd_prim_sem_obter, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "B"))
