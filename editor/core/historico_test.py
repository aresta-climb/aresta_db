# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import tempfile
import unittest
from pathlib import Path
from typing import Any

from PySide6.QtGui import QUndoCommand
from PySide6.QtWidgets import QApplication

import editor.commands.comandos_protobuf as mod_proto
from aresta_api.proto.generated.croqui_pb2 import Croqui
from editor.commands.comandos_protobuf import (
    CmdAdicionarRepeated,
    CmdAlterarCampo,
    CmdMacro,
    CmdRemoverRepeated,
)
from editor.core.diario import GerenciadorDiario
from editor.core.historico import GerenciadorHistorico
from editor.models.croqui_model import CroquiModel


class ComandoTeste(QUndoCommand):
    def __init__(
        self, estado: dict, valor_antigo: Any, valor_novo: Any, id_merge: int | None = None
    ):
        super().__init__()
        self.estado = estado
        self.valor_antigo = valor_antigo
        self.valor_novo = valor_novo
        self._id_merge = id_merge

    def undo(self) -> None:
        self.estado["valor"] = self.valor_antigo

    def redo(self) -> None:
        self.estado["valor"] = self.valor_novo

    def id(self) -> int:
        return self._id_merge if self._id_merge is not None else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if isinstance(outro, ComandoTeste) and self.id() != -1 and self.id() == outro.id():
            self.valor_novo = outro.valor_novo
            return True
        return False

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "ComandoTeste",
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "id_merge": self._id_merge,
        }


class DiarioEspiao(GerenciadorDiario):
    """Subclasse determinística sem mock para rastrear chamadas de persistência."""

    def __init__(self, pasta_croqui: Path):
        super().__init__(pasta_croqui)
        self.chamadas_substituir: int = 0
        self.chamadas_gravar: int = 0
        self.ultimos_comandos_substituidos: list[Any] = []

    def substituir_comandos_pendentes(self, comandos: list[Any]) -> None:
        self.chamadas_substituir += 1
        self.ultimos_comandos_substituidos = list(comandos)
        super().substituir_comandos_pendentes(comandos)

    def gravar_comando_pendente(self, comando: Any) -> None:
        self.chamadas_gravar += 1
        super().gravar_comando_pendente(comando)


class TestGerenciadorHistorico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

    def test_atalho_push_e_getattr_pilha(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}
        cmd = ComandoTeste(estado, 0, 15)

        gerenciador.push(cmd)
        self.assertEqual(estado["valor"], 15)
        self.assertEqual(gerenciador.count(), 1)
        self.assertTrue(gerenciador.canUndo())

    def test_definir_e_obter_gerenciador_diario(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pasta = Path(tmpdir)
            diario1 = GerenciadorDiario(pasta / "d1")
            diario2 = GerenciadorDiario(pasta / "d2")

            gerenciador = GerenciadorHistorico(diario=diario1)
            self.assertIs(gerenciador.obter_gerenciador_diario(), diario1)
            self.assertEqual(diario1._hook_flush, gerenciador.flush_diario_pendente)

            gerenciador.definir_gerenciador_diario(diario2)
            self.assertIs(gerenciador.obter_gerenciador_diario(), diario2)
            self.assertIsNone(diario1._hook_flush)
            self.assertEqual(diario2._hook_flush, gerenciador.flush_diario_pendente)

    def test_merge_de_comandos(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}

        cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
        cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)

        gerenciador.executar(cmd1)
        self.assertEqual(estado["valor"], 5)

        gerenciador.executar(cmd2)
        self.assertEqual(estado["valor"], 10)

        self.assertEqual(gerenciador.count(), 1)
        gerenciador.desfazer()
        self.assertEqual(estado["valor"], 0)

        gerenciador.refazer()
        self.assertEqual(estado["valor"], 10)

    def test_merge_comandos_preserva_cache_diario(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            diario = GerenciadorDiario(Path(tmpdir))
            cmd_salvo = {
                "classe": "CmdAlterarCampo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_novo": "V1",
            }
            diario.gravar_comando_pendente(cmd_salvo)
            diario.consolidar_salvamento()
            diario.exportar_diario_anonimizado()

            gerenciador = GerenciadorHistorico(diario=diario)
            estado = {"valor": 0}

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

            diario.exportar_diario_anonimizado()
            self.assertEqual(len(leituras_disco), 0)

    def test_foco_requisitado_emitido(self):
        gerenciador = GerenciadorHistorico()
        estado = {"valor": 0}

        cmd = ComandoTeste(estado, 0, 10)
        cmd.contexto_ui = "page:mapas/file:teste.md"

        focos_recebidos = []
        gerenciador.sinal_foco_requisitado.connect(focos_recebidos.append)

        gerenciador.executar(cmd)
        self.assertIn("page:mapas/file:teste.md", focos_recebidos)

        focos_recebidos.clear()
        gerenciador.desfazer()
        self.assertIn("page:mapas/file:teste.md", focos_recebidos)

    def test_gerenciador_historico_persiste_no_diario(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            gerenciador = GerenciadorHistorico(diario=diario)

            croqui = Croqui(nome="Nome Original")
            model = CroquiModel(croqui)

            cmd = CmdAlterarCampo(model, croqui, "nome", "Nome Alterado")
            gerenciador.executar(cmd)

            self.assertTrue(diario.tem_alteracoes_pendentes())
            comandos_lidos = diario.ler_diario_pendente()
            self.assertEqual(len(comandos_lidos), 1)
            self.assertEqual(comandos_lidos[0]["classe"], "CmdAlterarCampo")
            self.assertEqual(comandos_lidos[0]["valor_novo"], "Nome Alterado")

    def test_gerenciador_historico_restaurar_do_diario(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            cmd1_dict = {
                "classe": "CmdAlterarCampo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Inicial",
                "valor_novo": "Intermediario",
                "context_path": None,
            }
            cmd2_dict = {
                "classe": "CmdAlterarCampo",
                "caminho_msg": "",
                "campo_nome": "nome",
                "valor_antigo": "Intermediario",
                "valor_novo": "Final",
                "context_path": None,
            }
            diario.gravar_comando_pendente(cmd1_dict)
            diario.gravar_comando_pendente(cmd2_dict)

            croqui = Croqui(nome="Inicial")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico()

            restaurados = gerenciador.restaurar_do_diario(model, diario)
            self.assertEqual(restaurados, 2)
            self.assertEqual(croqui.nome, "Final")

            self.assertTrue(gerenciador.obter_pilha().canUndo())
            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Intermediario")
            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Inicial")

    def test_restaurar_do_diario_sem_comandos_retorna_zero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            croqui = Croqui(nome="Sem Mudancas")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico()

            total = gerenciador.restaurar_do_diario(model, diario)
            self.assertEqual(total, 0)
            self.assertIs(gerenciador.obter_gerenciador_diario(), diario)

    def test_gerenciador_historico_carregar_diario_salvo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            diario.gravar_comando_pendente(
                {
                    "classe": "CmdAlterarCampo",
                    "caminho_msg": "",
                    "campo_nome": "nome",
                    "valor_antigo": "Inicial",
                    "valor_novo": "Passo 1",
                    "context_path": None,
                }
            )
            diario.gravar_comando_pendente(
                {
                    "classe": "CmdAlterarCampo",
                    "caminho_msg": "",
                    "campo_nome": "nome",
                    "valor_antigo": "Passo 1",
                    "valor_novo": "Passo 2",
                    "context_path": None,
                }
            )
            diario.consolidar_salvamento()

            croqui = Croqui(nome="Passo 2")
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico()

            carregados = gerenciador.carregar_diario_salvo(model, diario)
            self.assertEqual(carregados, 2)
            self.assertEqual(croqui.nome, "Passo 2")
            self.assertTrue(gerenciador.obter_pilha().isClean())
            self.assertTrue(gerenciador.obter_pilha().canUndo())

            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Passo 1")
            self.assertFalse(gerenciador.obter_pilha().isClean())

            gerenciador.desfazer()
            self.assertEqual(croqui.nome, "Inicial")

            gerenciador.refazer()
            self.assertEqual(croqui.nome, "Passo 1")

            gerenciador.refazer()
            self.assertEqual(croqui.nome, "Passo 2")
            self.assertTrue(gerenciador.obter_pilha().isClean())

    def test_carregar_diario_salvo_vazio_retorna_zero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)
            croqui = Croqui()
            model = CroquiModel(croqui)
            gerenciador = GerenciadorHistorico()

            total = gerenciador.carregar_diario_salvo(model, diario)
            self.assertEqual(total, 0)

    def test_carregar_diario_salvo_comando_sem_armar_silencioso(self):
        class ComandoSimplesSemArmar(QUndoCommand):
            def __init__(self):
                super().__init__()
                self.execucoes_redo = 0

            def redo(self):
                if getattr(self, "_ignorar_primeiro_redo", False):
                    self._ignorar_primeiro_redo = False
                    return
                self.execucoes_redo += 1

            def undo(self):
                pass

        class DiarioComandoSimples:
            def ler_diario_salvo(self):
                return [{"classe": "FakeCmd"}]

        class ModelComandoSimples:
            pass

        gerenciador = GerenciadorHistorico()
        orig_deserializar = mod_proto.deserializar_comando
        try:
            mod_proto.deserializar_comando = lambda d, m: ComandoSimplesSemArmar()
            total = gerenciador.carregar_diario_salvo(ModelComandoSimples(), DiarioComandoSimples())
            self.assertEqual(total, 1)
        finally:
            mod_proto.deserializar_comando = orig_deserializar

    def test_gerenciador_historico_restaurar_pendente_com_merge_keystrokes_e_undo_imediato(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui1 = Croqui(nome="Inicial")
            model1 = CroquiModel(croqui1)
            gerenciador1 = GerenciadorHistorico(diario=diario)

            palavras = ["N", "No", "Nom", "Nome", "Nome Final"]
            for p in palavras:
                cmd = CmdAlterarCampo(model1, croqui1, "nome", p, session_id="digitacao_nome")
                gerenciador1.executar(cmd)

            self.assertEqual(gerenciador1.obter_pilha().count(), 1)
            self.assertEqual(croqui1.nome, "Nome Final")

            self.assertTrue(diario.tem_alteracoes_pendentes())
            comandos_gravados = diario.ler_diario_pendente()
            self.assertEqual(len(comandos_gravados), 1)
            self.assertEqual(comandos_gravados[0]["valor_antigo"], "Inicial")
            self.assertEqual(comandos_gravados[0]["valor_novo"], "Nome Final")

            croqui2 = Croqui(nome="Inicial")
            model2 = CroquiModel(croqui2)
            gerenciador2 = GerenciadorHistorico()

            gerenciador2.restaurar_do_diario(model2, diario)

            self.assertEqual(croqui2.nome, "Nome Final")
            self.assertEqual(gerenciador2.obter_pilha().count(), 1)

            gerenciador2.desfazer()
            self.assertEqual(croqui2.nome, "Inicial")

            gerenciador2.refazer()
            self.assertEqual(croqui2.nome, "Nome Final")

    def test_restaurar_do_diario_ignora_comando_orfa_ou_corrompido(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui_orig = Croqui(nome="Original")
            croqui_orig.creditos.append("Credito 1")
            model_orig = CroquiModel(croqui_orig)

            cmd1 = CmdAlterarCampo(model_orig, croqui_orig, "nome", "Passo 1")
            diario.gravar_comando_pendente(cmd1)

            cmd_orfa = {
                "classe": "CmdAdicionarRepeated",
                "caminho_msg": "",
                "campo_nome": "pontos_de_interesse_inexistentes",
                "index": 0,
                "valor": {},
                "context_path": None,
            }
            diario.gravar_comando_pendente(cmd_orfa)

            cmd3 = CmdAlterarCampo(model_orig, croqui_orig, "nome", "Passo 2")
            diario.gravar_comando_pendente(cmd3)

            croqui_novo = Croqui(nome="Original")
            croqui_novo.creditos.append("Credito 1")
            model_novo = CroquiModel(croqui_novo)
            gerenciador = GerenciadorHistorico()

            total_restaurados = gerenciador.restaurar_do_diario(model_novo, diario)
            self.assertEqual(total_restaurados, 2)
            self.assertEqual(croqui_novo.nome, "Passo 2")

    def test_carregar_comandos_salvos_ignora_comando_corrompido(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui_orig = Croqui(nome="Original")
            model_orig = CroquiModel(croqui_orig)

            cmd1 = CmdAlterarCampo(model_orig, croqui_orig, "nome", "Passo 1")
            diario.gravar_comando_pendente(cmd1)

            cmd_invalido = {
                "classe": "CmdAlterarCampo",
                "caminho_msg": "",
                "campo_nome": "campo_inexistente",
                "valor_antigo": "A",
                "valor_novo": "B",
            }
            diario.gravar_comando_pendente(cmd_invalido)

            cmd3 = CmdAlterarCampo(model_orig, croqui_orig, "nome", "Passo 2")
            diario.gravar_comando_pendente(cmd3)

            diario.consolidar_salvamento()

            croqui_novo = Croqui(nome="Passo 2")
            model_novo = CroquiModel(croqui_novo)
            gerenciador = GerenciadorHistorico()

            total_carregados = gerenciador.carregar_diario_salvo(model_novo, diario)
            self.assertEqual(total_carregados, 2)

    def test_replay_diario_trata_excecao_generica_inesperada(self):
        with tempfile.TemporaryDirectory() as temp_dir1:
            pasta_croqui1 = Path(temp_dir1)
            diario1 = GerenciadorDiario(pasta_croqui1)
            diario1.gravar_comando_pendente({"classe": "CmdParaErro"})

            gerenciador1 = GerenciadorHistorico()
            model1 = CroquiModel(Croqui())

            def falhar_deserializar(dados, m):
                raise RuntimeError("Erro inesperado simulado")

            orig = mod_proto.deserializar_comando
            try:
                mod_proto.deserializar_comando = falhar_deserializar
                with self.assertLogs("aresta_editor.historico", level="ERROR") as cm_err:
                    res_pendente = gerenciador1.restaurar_do_diario(model1, diario1)
                    self.assertEqual(res_pendente, 0)
                self.assertTrue(
                    any("Erro inesperado ao restaurar comando" in l for l in cm_err.output)
                )
            finally:
                mod_proto.deserializar_comando = orig

        with tempfile.TemporaryDirectory() as temp_dir2:
            pasta_croqui2 = Path(temp_dir2)
            diario2 = GerenciadorDiario(pasta_croqui2)
            diario2.gravar_comando_pendente({"classe": "CmdParaErro"})
            diario2.consolidar_salvamento()

            gerenciador2 = GerenciadorHistorico()
            model2 = CroquiModel(Croqui())

            try:
                mod_proto.deserializar_comando = falhar_deserializar
                with self.assertLogs("aresta_editor.historico", level="ERROR") as cm_err_salvo:
                    res_salvo = gerenciador2.carregar_diario_salvo(model2, diario2)
                    self.assertEqual(res_salvo, 0)
                self.assertTrue(
                    any(
                        "Erro inesperado ao deserializar comando salvo" in l
                        for l in cm_err_salvo.output
                    )
                )
            finally:
                mod_proto.deserializar_comando = orig

    def test_carregar_diario_salvo_e_restaurar_tratam_index_error_como_warning(self):
        cmd_corrompido = {
            "classe": "CmdTesteIndexError",
            "caminho_msg": "",
        }

        def deserializar_index_error(dados, m):
            raise IndexError("Índice de lista fora de alcance")

        orig = mod_proto.deserializar_comando
        try:
            mod_proto.deserializar_comando = deserializar_index_error

            with tempfile.TemporaryDirectory() as temp_dir1:
                pasta_croqui1 = Path(temp_dir1)
                diario1 = GerenciadorDiario(pasta_croqui1)
                diario1.gravar_comando_pendente(cmd_corrompido)

                gerenciador1 = GerenciadorHistorico()
                model1 = CroquiModel(Croqui())

                with self.assertLogs("aresta_editor.historico", level="WARNING") as cm_warn:
                    total = gerenciador1.restaurar_do_diario(model1, diario1)
                    self.assertEqual(total, 0)
                self.assertTrue(
                    any(
                        "Comando corrompido ou órfão descartado do diário pendente" in l
                        for l in cm_warn.output
                    )
                )

            with tempfile.TemporaryDirectory() as temp_dir2:
                pasta_croqui2 = Path(temp_dir2)
                diario2 = GerenciadorDiario(pasta_croqui2)
                diario2.gravar_comando_pendente(cmd_corrompido)
                diario2.consolidar_salvamento()

                gerenciador2 = GerenciadorHistorico()
                model2 = CroquiModel(Croqui())

                with self.assertLogs("aresta_editor.historico", level="WARNING") as cm_warn_salvo:
                    total_salvo = gerenciador2.carregar_diario_salvo(model2, diario2)
                    self.assertEqual(total_salvo, 0)
                self.assertTrue(
                    any(
                        "Comando corrompido ou órfão descartado do diário salvo" in l
                        for l in cm_warn_salvo.output
                    )
                )
        finally:
            mod_proto.deserializar_comando = orig

    def test_sincronizar_diario_pendente_com_debounce(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = DiarioEspiao(pasta_croqui)

            gerenciador = GerenciadorHistorico(diario=diario)
            self.assertEqual(gerenciador.intervalo_debounce_ms, 300)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)
            cmd3 = ComandoTeste(estado, 10, 15, id_merge=42)

            gerenciador.executar(cmd1)
            self.assertEqual(diario.chamadas_substituir, 0)

            gerenciador.executar(cmd2)
            self.assertEqual(diario.chamadas_substituir, 0)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            gerenciador.executar(cmd3)
            self.assertEqual(diario.chamadas_substituir, 0)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            gerenciador.flush_diario_pendente()
            self.assertEqual(diario.chamadas_substituir, 1)
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())

    def test_comando_novo_nao_mesclado_faz_flush_antes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = DiarioEspiao(pasta_croqui)

            gerenciador = GerenciadorHistorico(diario=diario)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)
            cmd_novo = ComandoTeste(estado, 10, 20, id_merge=None)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())
            self.assertEqual(diario.chamadas_substituir, 0)

            gerenciador.executar(cmd_novo)
            self.assertEqual(diario.chamadas_substituir, 1)
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())
            self.assertEqual(diario.chamadas_gravar, 2)

    def test_debounce_zero_sincroniza_imediatamente(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = DiarioEspiao(pasta_croqui)

            gerenciador = GerenciadorHistorico(diario=diario)
            gerenciador.intervalo_debounce_ms = 0

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)

            self.assertEqual(diario.chamadas_substituir, 1)
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())

    def test_sincronizar_sem_diario_retorna_imediatamente(self):
        gerenciador = GerenciadorHistorico(diario=None)
        gerenciador._sincronizar_diario_pendente()
        gerenciador._sincronizar_diario_pendente_imediato()

    def test_desfazer_e_refazer_fazem_flush_diario(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = DiarioEspiao(pasta_croqui)

            gerenciador = GerenciadorHistorico(diario=diario)

            estado = {"valor": 0}
            cmd1 = ComandoTeste(estado, 0, 5, id_merge=42)
            cmd2 = ComandoTeste(estado, 5, 10, id_merge=42)

            gerenciador.executar(cmd1)
            gerenciador.executar(cmd2)
            self.assertTrue(gerenciador._timer_sincronizacao.isActive())

            gerenciador.desfazer()
            self.assertFalse(gerenciador._timer_sincronizacao.isActive())
            self.assertGreaterEqual(diario.chamadas_substituir, 1)

            gerenciador.refazer()
            self.assertGreaterEqual(diario.chamadas_substituir, 2)

    def test_limpar_para_timer_debounce(self):
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
            self.assertEqual(gerenciador.count(), 0)

    def test_carregar_diario_salvo_silencia_sinais_ui(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pasta_croqui = Path(temp_dir)
            diario = GerenciadorDiario(pasta_croqui)

            croqui_orig = Croqui(nome="Original")
            model_orig = CroquiModel(croqui_orig)

            cmd1 = CmdAlterarCampo(model_orig, croqui_orig, "nome", "Passo 1")
            cmd2 = CmdAlterarCampo(model_orig, croqui_orig, "nome", "Passo 2")
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
            self.assertEqual(gerenciador.count(), 2)
            self.assertEqual(len(sinais_emitidos), 0)

    def test_despachar_sinal_descarta_comando_sem_mensagem_alvo(self):
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

        cmd_campo = CmdAlterarCampo(model, croqui, "nome", "B")
        cmd_campo.caminho_msg = "picos.99.setor"
        cmd_campo._msg_cache = None

        gerenciador._despachar_sinal(cmd_campo, is_undo=False)
        gerenciador._despachar_sinal(cmd_campo, is_undo=True)

        cmd_add = CmdAdicionarRepeated(model, croqui, "creditos", "teste", 0)
        cmd_add.caminho_msg = "picos.99"
        cmd_add._msg_cache = None
        gerenciador._despachar_sinal(cmd_add, is_undo=False)
        gerenciador._despachar_sinal(cmd_add, is_undo=True)

        cmd_rem = CmdRemoverRepeated(model, croqui, "creditos", 0)
        cmd_rem.caminho_msg = "picos.99"
        cmd_rem._msg_cache = None
        gerenciador._despachar_sinal(cmd_rem, is_undo=False)
        gerenciador._despachar_sinal(cmd_rem, is_undo=True)

        gerenciador._despachar_sinal(None, is_undo=False)
        self.assertEqual(len(sinais_emitidos), 0)

    def test_despachar_sinal_sucesso_todos_comandos_canonicos(self):
        croqui = Croqui(nome="Pico")
        croqui.creditos.append("Autor")
        model = CroquiModel(croqui)
        gerenciador = GerenciadorHistorico()

        sinais_campo = []
        sinais_adicionado = []
        sinais_removido = []
        gerenciador.sinal_campo_alterado.connect(lambda *args: sinais_campo.append(args))
        gerenciador.sinal_item_adicionado.connect(lambda *args: sinais_adicionado.append(args))
        gerenciador.sinal_item_removido.connect(lambda *args: sinais_removido.append(args))

        # 1. CmdAlterarCampo (redo e undo)
        cmd_campo = CmdAlterarCampo(model, croqui, "nome", "Novo Pico")
        gerenciador._despachar_sinal(cmd_campo, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Novo Pico"))

        gerenciador._despachar_sinal(cmd_campo, is_undo=True)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Pico"))

        # 2. CmdAdicionarRepeated (redo e undo)
        cmd_add = CmdAdicionarRepeated(model, croqui, "creditos", index=0, valor="Novo Autor")
        gerenciador._despachar_sinal(cmd_add, is_undo=False)
        self.assertEqual(sinais_adicionado[-1], (id(croqui), "creditos", 0))

        gerenciador._despachar_sinal(cmd_add, is_undo=True)
        self.assertEqual(sinais_removido[-1], (id(croqui), "creditos", 0))

        # 3. CmdRemoverRepeated (redo e undo)
        cmd_rem = CmdRemoverRepeated(model, croqui, "creditos", 0)
        gerenciador._despachar_sinal(cmd_rem, is_undo=False)
        self.assertEqual(sinais_removido[-1], (id(croqui), "creditos", 0))

        gerenciador._despachar_sinal(cmd_rem, is_undo=True)
        self.assertEqual(sinais_adicionado[-1], (id(croqui), "creditos", 0))

        # 4. CmdMacro com subcomandos (redo e undo)
        macro = CmdMacro(
            [
                CmdAlterarCampo(model, croqui, "nome", "Nome Macro 1", valor_antigo="Pico"),
                CmdAlterarCampo(model, croqui, "nome", "Nome Macro 2", valor_antigo="Nome Macro 1"),
            ]
        )
        gerenciador._despachar_sinal(macro, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Nome Macro 2"))

        gerenciador._despachar_sinal(macro, is_undo=True)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Pico"))
        self.assertEqual(sinais_campo[-2], (id(croqui), "nome", "Nome Macro 1"))

        # 5. Fallback comando com atributo msg sem _obter_msg
        class CmdComMsgDireta(CmdAlterarCampo):
            _obter_msg = None
            msg = None

            def __init__(self, msg_alvo):
                self.msg = msg_alvo
                self.campo_nome = "nome"
                self.valor_antigo = "Antigo"
                self.valor_novo = "Novo"

            def childCount(self):
                return 0

        cmd_direto = CmdComMsgDireta(croqui)
        gerenciador._despachar_sinal(cmd_direto, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Novo"))

        # 6. Comando composto nativo do Qt (childCount > 0)
        pai = QUndoCommand()
        filho = CmdAlterarCampo(model, croqui, "nome", "Filho Qt", parent=pai)
        self.assertEqual(pai.childCount(), 1)
        gerenciador._despachar_sinal(pai, is_undo=False)
        self.assertEqual(sinais_campo[-1], (id(croqui), "nome", "Filho Qt"))

    def test_on_index_changed_sem_diferenca_ou_pausado(self):
        gerenciador = GerenciadorHistorico()
        # Sem diferença no índice: nada faz
        gerenciador._on_index_changed(0)

        # Com gravação pausada
        gerenciador._gravacao_pausada = True
        gerenciador._on_index_changed(5)
        self.assertEqual(gerenciador._ultimo_index, 5)

    def test_slot_on_index_changed_registrado_no_metaobject_e_getattr_protege_privados(self):
        gerenciador = GerenciadorHistorico()
        indice_slot = gerenciador.metaObject().indexOfSlot("_on_index_changed(int)")
        self.assertGreaterEqual(indice_slot, 0)

        with self.assertRaises(AttributeError) as ctx:
            _ = gerenciador._atributo_privado_inexistente
        self.assertIn("GerenciadorHistorico", str(ctx.exception))
