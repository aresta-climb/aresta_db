# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import unittest
from pathlib import Path
import tempfile
import os
import shutil
from unittest.mock import MagicMock

from PyQt6.QtGui import QUndoStack

from editor.models.croqui_model import CroquiModel
from aresta_api.proto.generated import croqui_pb2
from editor.commands.comandos_mapas import CmdAdicionarMapaArquivo

class TestComandosMapas(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = Path(self.test_dir.name)
        self.imagens_dir = self.test_dir_path / "imagens"
        self.imagens_dir.mkdir(parents=True, exist_ok=True)
        
        # Cria um croqui mock
        self.croqui = croqui_pb2.Croqui()
        pico = self.croqui.picos.add()
        pico.nome = "Pico Teste"
        sg = pico.setores_ou_grupos.add()
        self.setor = sg.setor.conteudo
        self.setor.nome = "Setor Teste"
        
        self.model = CroquiModel(self.croqui)
        self.undo_stack = QUndoStack()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_cmd_adicionar_mapa_arquivo(self):
        # Preparar dados do comando
        img_bytes = b"dummy_webp_bytes"
        caminho_imagem = self.imagens_dir / "mapa_teste.webp"
        
        novo_mapa = croqui_pb2.Mapa()
        novo_mapa.caminho_imagem_mapa = "imagens/mapa_teste.webp"
        novo_mapa.largura_mapa = 100
        novo_mapa.altura_mapa = 100
        
        cmd = CmdAdicionarMapaArquivo(
            model=self.model,
            msg=self.setor,
            campo_nome="mapas",
            index=0,
            valor=novo_mapa,
            caminho_absoluto=caminho_imagem,
            img_bytes=img_bytes,
            context_path="node:Croqui/setores/item:0"
        )
        
        # Testar Redo
        cmd.redo()
        
        # Verifica se o modelo foi atualizado com a imagem na RAM
        self.assertEqual(self.model.obter_bytes_imagem("imagens/mapa_teste.webp"), img_bytes)
        self.assertEqual(len(self.setor.mapas), 1)
        self.assertEqual(self.setor.mapas[0].caminho_imagem_mapa, "imagens/mapa_teste.webp")
        self.assertEqual(self.setor.mapas[0].largura_mapa, 100)
        
        # Testar Undo
        cmd.undo()
        
        # Verifica se a imagem foi removida da RAM e o modelo esvaziado
        self.assertIsNone(self.model.obter_bytes_imagem("imagens/mapa_teste.webp"))
        self.assertEqual(len(self.setor.mapas), 0)

if __name__ == '__main__':
    unittest.main()
