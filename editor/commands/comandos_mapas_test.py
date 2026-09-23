# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from pathlib import Path
import tempfile
import os
import shutil
from unittest.mock import MagicMock

from PySide6.QtGui import QUndoStack

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

    def test_cmd_adicionar_mapa_arquivo_serializacao_e_deserializacao(self):
        img_bytes = b"bytes_mapa_original"
        caminho_imagem = self.imagens_dir / "mapa_teste.webp"
        
        novo_mapa = croqui_pb2.Mapa()
        novo_mapa.caminho_imagem_mapa = "imagens/mapa_teste.webp"
        novo_mapa.largura_mapa = 200
        novo_mapa.altura_mapa = 150
        
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
        
        # Serialização normal
        dados = cmd.serializar(anonimizado=False)
        self.assertEqual(dados["classe"], "CmdAdicionarMapaArquivo")
        self.assertEqual(dados["img_bytes"], img_bytes)
        self.assertEqual(dados["caminho_absoluto"], str(caminho_imagem))
        
        # Deserialização e execução
        cmd_recriado = CmdAdicionarMapaArquivo.deserializar(dados, self.model)
        cmd_recriado.redo()
        self.assertEqual(len(self.setor.mapas), 1)
        self.assertEqual(self.model.obter_bytes_imagem("imagens/mapa_teste.webp"), img_bytes)
        
        # Serialização anonimizada
        dados_anon = cmd.serializar(anonimizado=True)
        self.assertEqual(dados_anon["caminho_absoluto"], "[ARQUIVO_MAPA_ANONIMIZADO]")


    def test_cmd_adicionar_mapa_arquivo_com_caminho_msg(self):
        img_bytes = b"bytes_mapa_lazy"
        caminho_imagem = self.imagens_dir / "mapa_lazy.webp"
        
        novo_mapa = croqui_pb2.Mapa()
        novo_mapa.caminho_imagem_mapa = "imagens/mapa_lazy.webp"
        novo_mapa.largura_mapa = 300
        novo_mapa.altura_mapa = 250

        caminho = "picos.0.setores_ou_grupos.0.setor.conteudo"
        cmd = CmdAdicionarMapaArquivo(
            model=self.model,
            caminho_msg=caminho,
            campo_nome="mapas",
            index=0,
            valor=novo_mapa,
            caminho_absoluto=caminho_imagem,
            img_bytes=img_bytes,
        )
        self.assertEqual(cmd.caminho_msg, caminho)

        # Redo
        cmd.redo()
        self.assertEqual(len(self.setor.mapas), 1)
        self.assertEqual(self.model.obter_bytes_imagem("imagens/mapa_lazy.webp"), img_bytes)

        # Undo
        cmd.undo()
        self.assertEqual(len(self.setor.mapas), 0)
        self.assertIsNone(self.model.obter_bytes_imagem("imagens/mapa_lazy.webp"))

    def test_cmd_adicionar_mapa_arquivo_deserializacao_sem_navegacao_ansiosa(self):
        dados = {
            "classe": "CmdAdicionarMapaArquivo",
            "caminho_msg": "picos.99.setores_ou_grupos.0.setor.conteudo",
            "campo_nome": "mapas",
            "index": 0,
            "valor": {
                "__tipo_protobuf__": "Mapa",
                "__bytes__": croqui_pb2.Mapa().SerializeToString(),
            },
            "caminho_absoluto": "",
            "img_bytes": b"bytes_inexistentes",
        }

        # Deserializar não deve navegar ansiosamente e nem falhar mesmo que o pico 99 não exista
        cmd = CmdAdicionarMapaArquivo.deserializar(dados, self.model)
        self.assertEqual(cmd.caminho_msg, "picos.99.setores_ou_grupos.0.setor.conteudo")

        # Redo e Undo devem registrar erro no logger e não lançar exceções não tratadas
        with self.assertLogs("editor.commands.comandos_protobuf", level="ERROR") as cm:
            cmd.redo()
            cmd.undo()
        self.assertTrue(any("Falha ao resolver mensagem alvo" in log for log in cm.output))


if __name__ == '__main__':
    unittest.main()

