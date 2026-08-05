# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

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

