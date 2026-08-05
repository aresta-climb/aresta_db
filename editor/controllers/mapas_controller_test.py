# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import unittest
from unittest.mock import Mock, MagicMock
from PyQt6.QtGui import QUndoStack
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.controllers.mapas_controller import MapasController

class MapasControllerTest(unittest.TestCase):
    def setUp(self):
        self.croqui = croqui_pb2.Croqui()
        # Setup basic hierarchy
        pico = self.croqui.picos.add()
        sg = pico.setores_ou_grupos.add()
        self.mapa = sg.setor.conteudo.mapas.add()
        
        self.model = CroquiModel(self.croqui)
        self.undo_stack = QUndoStack()
        self.controller = MapasController(self.model, self.undo_stack)
        
        self.msg_mapa_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]

    def test_adicionar_poi(self):
        # A test to ensure we can add a POI
        novo_poi = croqui_pb2.Mapa.PontoDeInteresse(id="poi1", label="Ponto 1")
        self.controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)
        
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        self.assertEqual(self.mapa.pontos_de_interesse[0].id, "poi1")

        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 0)

    def test_deletar_poi(self):
        # Setup initial
        poi = self.mapa.pontos_de_interesse.add(id="poi1")
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        
        self.controller.deletar_poi(self.msg_mapa_proxy, 0)
        self.assertEqual(len(self.mapa.pontos_de_interesse), 0)
        
        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)

    def test_mover_poi(self):
        poi_antigo = croqui_pb2.Mapa.PontoDeInteresse(id="poi1")
        self.mapa.pontos_de_interesse.append(poi_antigo)
        
        poi_novo = croqui_pb2.Mapa.PontoDeInteresse(id="poi1", label="Movel")
        
        self.controller.mover_poi(self.msg_mapa_proxy, 0, poi_antigo, poi_novo)
        self.assertEqual(self.mapa.pontos_de_interesse[0].label, "Movel")
        
        self.undo_stack.undo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].label, "")

    def test_adicionar_referencia(self):
        nova_ref = croqui_pb2.Mapa.Referencia(setor="Setor Teste")
        nova_ref.ids.extend(["poi1", "poi2"])
        
        self.controller.adicionar_referencia(self.msg_mapa_proxy, nova_ref)
        
        self.assertEqual(len(self.mapa.referencias), 1)
        self.assertEqual(self.mapa.referencias[0].setor, "Setor Teste")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["poi1", "poi2"])

        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.referencias), 0)

    def test_deletar_referencia(self):
        ref = self.mapa.referencias.add(setor="Setor Teste")
        self.assertEqual(len(self.mapa.referencias), 1)
        
        self.controller.deletar_referencia(self.msg_mapa_proxy, 0)
        self.assertEqual(len(self.mapa.referencias), 0)
        
        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.referencias), 1)

    def test_alterar_referencia(self):
        ref_antiga = croqui_pb2.Mapa.Referencia(setor="Setor Antigo")
        ref_antiga.ids.extend(["poi1"])
        self.mapa.referencias.append(ref_antiga)
        
        ref_nova = croqui_pb2.Mapa.Referencia(setor="Setor Novo")
        ref_nova.ids.extend(["poi1", "poi2"])
        
        self.controller.alterar_referencia(self.msg_mapa_proxy, 0, ref_antiga, ref_nova)
        self.assertEqual(self.mapa.referencias[0].setor, "Setor Novo")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["poi1", "poi2"])
        
        self.undo_stack.undo()
        self.assertEqual(self.mapa.referencias[0].setor, "Setor Antigo")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["poi1"])


    def test_obter_caminho_imagem_mapa(self):
        self.mapa.caminho_imagem_mapa = "mapa.png"
        # We need a way for the controller to know the base path, maybe it queries it from somewhere?
        # Typically the app knows the base db path. We'll pass it to the controller.
        self.controller.set_caminho_db("/fake/path")
        
        path = self.controller.obter_caminho_imagem_mapa(self.msg_mapa_proxy)
        self.assertEqual(str(path).replace('\\', '/'), "/fake/path/mapa.png") # Adjust slashes based on OS in real test, but we can use Path objects

    def test_converter_boxes_para_circulos(self):
        poi1 = self.mapa.pontos_de_interesse.add()
        poi1.id = "poi1"
        poi1.retangulo.x = 10
        poi1.retangulo.y = 10
        poi1.retangulo.comprimento = 40
        poi1.retangulo.largura = 40

        poi2 = self.mapa.pontos_de_interesse.add()
        poi2.id = "poi2"
        poi2.retangulo.x = 100
        poi2.retangulo.y = 100
        poi2.retangulo.comprimento = 80
        poi2.retangulo.largura = 80
        
        self.controller.converter_boxes_para_circulos(self.msg_mapa_proxy, [0, 1])
        
        self.assertTrue(self.mapa.pontos_de_interesse[0].HasField('circulo'))
        self.assertEqual(self.mapa.pontos_de_interesse[0].circulo.raio, 20)
        self.assertTrue(self.mapa.pontos_de_interesse[1].HasField('circulo'))
        self.assertEqual(self.mapa.pontos_de_interesse[1].circulo.raio, 40)
        
        self.undo_stack.undo()
        self.assertTrue(self.mapa.pontos_de_interesse[0].HasField('retangulo'))
        self.assertTrue(self.mapa.pontos_de_interesse[1].HasField('retangulo'))

    def test_macro_undo_redo_agrupa_comandos(self):
        """Verifica se iniciar_grupo_undo e finalizar_grupo_undo agrupam comandos corretamente."""
        from aresta_api.proto.generated import croqui_pb2
        
        # Inicia o grupo
        self.controller.iniciar_grupo_undo("Adicionar Dois Pontos")
        
        # Executa dois comandos separados
        poi1 = croqui_pb2.Mapa.PontoDeInteresse(id="poi1")
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi1)
        
        poi2 = croqui_pb2.Mapa.PontoDeInteresse(id="poi2")
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi2)
        
        # Finaliza o grupo
        self.controller.finalizar_grupo_undo()
        
        # A stack deve considerar tudo como 1 único passo de undo
        self.assertEqual(self.undo_stack.count(), 1)
        
        # Um único undo desfaz os dois (o count não muda, mas o index sim)
        self.undo_stack.undo()
        self.assertEqual(self.undo_stack.index(), 0)
        
        # Um único redo refaz os dois
        self.undo_stack.redo()
        self.assertEqual(self.undo_stack.index(), 1)

    def test_foco_requisitado_on_undo(self):
        # Configura o contexto do controller
        test_path = "page:mapas/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:mapas/item:0"
        self.controller.set_contexto(test_path)
        
        # Prepara a captura do sinal
        sinal_emitido = []
        def _on_foco(path):
            sinal_emitido.append(path)
        
        self.model.foco_requisitado.connect(_on_foco)
        
        # Adiciona um POI e desfaz
        novo_poi = croqui_pb2.Mapa.PontoDeInteresse(id="poi_foco")
        self.controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)
        
        self.undo_stack.undo()
        
        self.assertTrue(len(sinal_emitido) > 0)
        # O último sinal deve ser igual ao contexto que gravamos
        self.assertEqual(sinal_emitido[-1], test_path)
        
        # Testar no redo também
        self.undo_stack.redo()
        self.assertEqual(sinal_emitido[-1], test_path)

    def test_converter_circulos_para_boxes(self):
        """[TDD] Verifica conversao de circulo para retangulo."""
        poi1 = croqui_pb2.Mapa.PontoDeInteresse()
        poi1.circulo.x = 100
        poi1.circulo.y = 200
        poi1.circulo.raio = 50
        
        poi2 = croqui_pb2.Mapa.PontoDeInteresse()
        poi2.retangulo.x = 10
        poi2.retangulo.y = 10
        
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi1)
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi2)
        
        self.controller.converter_circulos_para_boxes(self.msg_mapa_proxy, [0, 1])
        
        poi_convertido = self.msg_mapa_proxy.pontos_de_interesse[0]
        self.assertTrue(poi_convertido.HasField('retangulo'))
        self.assertFalse(poi_convertido.HasField('circulo'))
        
        self.assertEqual(poi_convertido.retangulo.x, 100)
        self.assertEqual(poi_convertido.retangulo.y, 200)
        self.assertEqual(poi_convertido.retangulo.comprimento, 100)
        self.assertEqual(poi_convertido.retangulo.largura, 100)

if __name__ == '__main__':
    unittest.main()
