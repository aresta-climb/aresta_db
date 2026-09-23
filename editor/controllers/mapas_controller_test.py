# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
import unittest
from unittest.mock import Mock, MagicMock
from PySide6.QtGui import QUndoStack
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

    def test_mover_poi_renomear_id_cascata_referencias_com_undo_redo(self):
        """[TDD] Garante que alterar o ID de um POI atualiza em cascata os IDs nas referências com Undo/Redo."""
        from editor.models.readonly_proxy import _copia_segura

        poi = self.mapa.pontos_de_interesse.add()
        poi.id = "poi_antigo"
        poi.label = "1"
        poi.circulo.x = 50
        poi.circulo.y = 50
        poi.circulo.raio = 10

        ref = self.mapa.referencias.add()
        ref.escalada = "Via Teste"
        ref.ids.extend(["poi_antigo", "outro_poi"])

        poi_antigo = _copia_segura(self.msg_mapa_proxy.pontos_de_interesse[0])
        poi_novo = _copia_segura(self.msg_mapa_proxy.pontos_de_interesse[0])
        poi_novo.id = "poi_novo"

        self.controller.mover_poi(self.msg_mapa_proxy, 0, poi_antigo, poi_novo)

        self.assertEqual(self.mapa.pontos_de_interesse[0].id, "poi_novo")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["poi_novo", "outro_poi"])

        # Undo deve reverter ambos atomicamente
        self.undo_stack.undo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].id, "poi_antigo")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["poi_antigo", "outro_poi"])

        # Redo deve reaplicar ambos
        self.undo_stack.redo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].id, "poi_novo")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["poi_novo", "outro_poi"])

    def test_obter_caminho_imagem_mapa(self):

        self.mapa.caminho_imagem_mapa = "mapa.png"
        # We need a way for the controller to know the base path, maybe it queries it from somewhere?
        # Typically the app knows the base db path. We'll pass it to the controller.
        self.controller.set_caminho_db("/fake/path")
        
        path = self.controller.obter_caminho_imagem_mapa(self.msg_mapa_proxy)
        self.assertEqual(str(path).replace('\\', '/'), "/fake/path/mapa.png")

        self.controller.set_caminho_db(None)
        self.assertIsNone(self.controller.obter_caminho_imagem_mapa(self.msg_mapa_proxy))

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

    def test_substituir_imagem(self):
        caminho_rel = "imagens/mapa.webp"
        bytes_antigo = b"antigo"
        bytes_novo = b"novo"
        self.model.definir_imagem_memoria(caminho_rel, bytes_antigo)

        self.controller.substituir_imagem(caminho_rel, bytes_novo)
        self.assertEqual(self.model.obter_bytes_imagem(caminho_rel), bytes_novo)
        self.assertEqual(self.undo_stack.count(), 1)

        self.undo_stack.undo()
        self.assertEqual(self.model.obter_bytes_imagem(caminho_rel), bytes_antigo)

        self.undo_stack.redo()
        self.assertEqual(self.model.obter_bytes_imagem(caminho_rel), bytes_novo)

        # Sem undo_stack
        self.controller.undo_stack = None
        self.controller.substituir_imagem(caminho_rel, b"direto", context_path="page:mapas/file:mapa.webp")
        self.assertEqual(self.model.obter_bytes_imagem(caminho_rel), b"direto")

    def test_mapas_controller_grava_no_diario_com_gerenciador_historico(self):
        import tempfile
        from editor.core.historico import GerenciadorHistorico
        from editor.core.diario import GerenciadorDiario

        with tempfile.TemporaryDirectory() as tmp_dir:
            diario = GerenciadorDiario(tmp_dir)
            historico = GerenciadorHistorico(diario=diario)
            controller = MapasController(self.model, historico)

            novo_poi = croqui_pb2.Mapa.PontoDeInteresse(id="poi_teste", label="Ponto Teste")
            controller.adicionar_poi(self.msg_mapa_proxy, novo_poi)

            self.assertTrue(diario.tem_alteracoes_pendentes())
            comandos = diario.ler_diario_pendente()
            self.assertEqual(len(comandos), 1)
            self.assertEqual(comandos[0]["classe"], "CmdAdicionarRepeated")
    def test_alterar_cor_poi(self):
        poi = self.mapa.pontos_de_interesse.add(id="poi1", cor="#00FF00")
        self.assertEqual(self.mapa.pontos_de_interesse[0].cor, "#00FF00")
        
        self.controller.alterar_cor_poi(self.msg_mapa_proxy, 0, "#FF6D00")
        self.assertEqual(self.mapa.pontos_de_interesse[0].cor, "#FF6D00")
        
        self.undo_stack.undo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].cor, "#00FF00")
        
        self.undo_stack.redo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].cor, "#FF6D00")

    def test_adicionar_linha(self):
        nos = [
            {"x": 100, "y": 200, "tipo": croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR, "rotulo": "01"},
            {"x": 150, "y": 100, "tipo": croqui_pb2.NoTrajeto.TipoNo.TOP_PARADA}
        ]
        self.controller.adicionar_linha(
            self.msg_mapa_proxy,
            id_linha="linha_01",
            label="Via 01",
            nos=nos,
            cor="#FF1744"
        )
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        poi = self.mapa.pontos_de_interesse[0]
        self.assertEqual(poi.id, "linha_01")
        self.assertEqual(poi.label, "Via 01")
        self.assertEqual(poi.cor, "#FF1744")
        self.assertTrue(poi.HasField("linha"))
        self.assertEqual(len(poi.linha.conteudo.nos), 2)
        self.assertEqual(poi.linha.conteudo.nos[0].x, 100)
        self.assertEqual(poi.linha.conteudo.nos[0].rotulo, "01")

        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 0)

    def test_alterar_tipo_no_e_manipulacao_de_nos(self):
        nos = [
            {"x": 100, "y": 200, "tipo": croqui_pb2.NoTrajeto.TipoNo.PASSAGEM},
            {"x": 200, "y": 100, "tipo": croqui_pb2.NoTrajeto.TipoNo.TOP_PARADA}
        ]
        self.controller.adicionar_linha(self.msg_mapa_proxy, id_linha="linha_01", label="", nos=nos)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[0].tipo, croqui_pb2.NoTrajeto.TipoNo.PASSAGEM)
        
        # Alterar tipo do nó 0 para PROTECAO_FIXA
        self.controller.alterar_tipo_no(self.msg_mapa_proxy, 0, 0, croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[0].tipo, croqui_pb2.NoTrajeto.TipoNo.PROTECAO_FIXA)
        
        self.undo_stack.undo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[0].tipo, croqui_pb2.NoTrajeto.TipoNo.PASSAGEM)
        
        # Adicionar nó intermediário
        novo_no = {"x": 150, "y": 150, "tipo": croqui_pb2.NoTrajeto.TipoNo.CRUX}
        self.controller.adicionar_no_linha(self.msg_mapa_proxy, 0, 1, novo_no)
        self.assertEqual(len(self.mapa.pontos_de_interesse[0].linha.conteudo.nos), 3)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[1].x, 150)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[1].tipo, croqui_pb2.NoTrajeto.TipoNo.CRUX)
        
        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse[0].linha.conteudo.nos), 2)
        
    def test_obter_pilha_com_gerenciador(self):
        mock_hist = Mock()
        mock_hist.obter_pilha.return_value = "pilha_interna"
        ctrl = MapasController(self.model, mock_hist)
        self.assertEqual(ctrl.obter_pilha(), "pilha_interna")

    def test_obter_pilha_direto_sem_wrapper(self):
        pilha_pura = "pilha_pura"
        ctrl = MapasController(self.model, pilha_pura)
        self.assertEqual(ctrl.obter_pilha(), "pilha_pura")

    def test_finalizar_grupo_undo_sem_macro_ativo_nao_dispara_erro(self):
        self.controller.finalizar_grupo_undo()

    def test_macro_undo_redo_aninhado(self):
        from aresta_api.proto.generated import croqui_pb2
        self.controller.iniciar_grupo_undo("Macro Pai")
        poi1 = croqui_pb2.Mapa.PontoDeInteresse(id="poi_pai")
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi1)

        self.controller.iniciar_grupo_undo("Macro Filho")
        poi2 = croqui_pb2.Mapa.PontoDeInteresse(id="poi_filho")
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi2)
        self.controller.finalizar_grupo_undo()

        self.controller.finalizar_grupo_undo()
        self.assertEqual(self.undo_stack.count(), 1)
        self.assertEqual(len(self.mapa.pontos_de_interesse), 2)

        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 0)

        self.undo_stack.redo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 2)


    def test_adicionar_linha_com_estilo_explicito(self):
        self.controller.adicionar_linha(
            self.msg_mapa_proxy,
            id_linha="linha_solida",
            label="Via 02",
            nos=[{"x": 10, "y": 20}],
            estilo=croqui_pb2.LinhaTrajeto.EstiloTraco.SOLIDO
        )
        poi = self.mapa.pontos_de_interesse[-1]
        self.assertEqual(poi.linha.estilo, croqui_pb2.LinhaTrajeto.EstiloTraco.SOLIDO)

    def test_adicionar_linha_com_texto_visivel(self):
        self.controller.adicionar_linha(
            self.msg_mapa_proxy,
            id_linha="v1",
            label="Via 01",
            nos=[{"x": 10, "y": 20}],
            texto_visivel="Texto no Mapa"
        )
        poi = self.mapa.pontos_de_interesse[-1]
        self.assertEqual(poi.texto_visivel, "Texto no Mapa")

    def test_alterar_espessura_linha(self):
        nos = [{"x": 10, "y": 20}, {"x": 30, "y": 40}]
        self.controller.adicionar_linha(self.msg_mapa_proxy, id_linha="l1", nos=nos)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.espessura, 3)
        
        self.controller.alterar_espessura_linha(self.msg_mapa_proxy, 0, nova_espessura=6)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.espessura, 6)
        
        self.undo_stack.undo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.espessura, 3)
        
        self.undo_stack.redo()
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.espessura, 6)

    def test_converter_boxes_para_circulos_com_poi_invalido(self):
        poi_circulo = croqui_pb2.Mapa.PontoDeInteresse()
        poi_circulo.circulo.x = 10
        self.controller.adicionar_poi(self.msg_mapa_proxy, poi_circulo)
        idx = len(self.mapa.pontos_de_interesse) - 1
        # Não deve lançar erro ao tentar converter um que não é retangulo
        self.controller.converter_boxes_para_circulos(self.msg_mapa_proxy, [idx])

    def test_manipulacoes_diretas_sem_proxy(self):
        poi_direto = croqui_pb2.Mapa.PontoDeInteresse(id="direto")
        poi_direto.linha.conteudo.nos.add(x=10, y=20, tipo=croqui_pb2.NoTrajeto.TipoNo.PASSAGEM)
        self.mapa.pontos_de_interesse.append(poi_direto)
        idx = len(self.mapa.pontos_de_interesse) - 1

        self.controller.alterar_cor_poi(self.mapa, idx, "#123456")
        self.assertEqual(self.mapa.pontos_de_interesse[idx].cor, "#123456")

        self.controller.alterar_tipo_no(self.mapa, idx, 0, croqui_pb2.NoTrajeto.TipoNo.CRUX)
        self.assertEqual(self.mapa.pontos_de_interesse[idx].linha.conteudo.nos[0].tipo, croqui_pb2.NoTrajeto.TipoNo.CRUX)

        self.controller.adicionar_no_linha(self.mapa, idx, 1, {"x": 50, "y": 60})
        self.assertEqual(len(self.mapa.pontos_de_interesse[idx].linha.conteudo.nos), 2)

        self.controller.remover_no_linha(self.mapa, idx, 0)
        self.assertEqual(len(self.mapa.pontos_de_interesse[idx].linha.conteudo.nos), 1)

    def test_adicionar_rota_com_tracado_nova_rota_simples(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        dados_rota = {"nome": "Via Central", "tipo": "boulder", "grau": "V4", "nova": True}
        pontos = [(100.0, 500.0), (120.0, 300.0), (140.0, 100.0)]

        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_rota, pontos)

        # Checa criação de escalada, linha e referência
        setor = self.croqui.picos[0].setores_ou_grupos[0].setor.conteudo
        self.assertEqual(len(setor.escaladas), 1)
        self.assertEqual(setor.escaladas[0].boulder.nome, "Via Central")
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        self.assertEqual(len(self.mapa.referencias), 1)
        self.assertEqual(self.mapa.referencias[0].escalada, "Via Central")

        # Rótulo de início 1, término sem TOP
        nos = self.mapa.pontos_de_interesse[0].linha.conteudo.nos
        self.assertEqual(nos[0].rotulo, "1")
        self.assertEqual(nos[0].tipo, croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR)
        self.assertEqual(nos[-1].tipo, croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
)
        self.assertEqual(nos[-1].rotulo, "")

        # Undo atômico
        self.undo_stack.undo()
        self.assertEqual(len(setor.escaladas), 0)
        self.assertEqual(len(self.mapa.pontos_de_interesse), 0)
        self.assertEqual(len(self.mapa.referencias), 0)

        # Redo atômico
        self.undo_stack.redo()
        self.assertEqual(len(setor.escaladas), 1)
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        self.assertEqual(len(self.mapa.referencias), 1)

    def test_adicionar_rota_com_tracado_existente_sem_duplicar(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        setor = self.croqui.picos[0].setores_ou_grupos[0].setor.conteudo
        e = setor.escaladas.add()
        e.boulder.nome = "Via Já Cadastrada"
        e.boulder.dificuldade = croqui_pb2.GrauBoulder.V3

        dados_rota = {"nome": "Via Já Cadastrada", "tipo": "boulder", "grau": "V3", "nova": False}
        pontos = [(50.0, 500.0), (50.0, 100.0)]

        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_rota, pontos)

        # Não deve duplicar escalada
        self.assertEqual(len(setor.escaladas), 1)
        self.assertEqual(len(self.mapa.referencias), 1)
        self.assertEqual(self.mapa.referencias[0].escalada, "Via Já Cadastrada")

    def test_adicionar_rota_com_tracado_fatiamento_em_no_e_desambiguacao(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        # Rota 1
        dados_1 = {"nome": "Via 1", "tipo": "boulder", "grau": "V4", "nova": True}
        pontos_1 = [(100.0, 500.0), (100.0, 300.0), (100.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_1, pontos_1)

        # Rota 2 compartilha (100, 500) e (100, 300) e bifurca para (150, 100)
        dados_2 = {"nome": "Via 2", "tipo": "boulder", "grau": "V6", "nova": True}
        pontos_2 = [(100.0, 500.0), (100.0, 300.0), (150.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_2, pontos_2)

        # Verifica fatiamento: a linha original foi fatiada em 2 e a variante é a 3ª linha
        self.assertEqual(len(self.mapa.pontos_de_interesse), 3)
        # Referências
        refs = {r.escalada: list(r.ids) for r in self.mapa.referencias}
        self.assertEqual(len(refs["Via 1"]), 2)
        self.assertEqual(len(refs["Via 2"]), 2)
        self.assertEqual(refs["Via 1"][0], refs["Via 2"][0])  # segmento comum

        # Rótulo compartilhado no início
        pois_por_id = {p.id: p for p in self.mapa.pontos_de_interesse}
        seg_comum = pois_por_id[refs["Via 1"][0]]
        self.assertEqual(seg_comum.linha.conteudo.nos[0].rotulo, "1, 2")

        # Topos desambiguados
        seg_fim_1 = pois_por_id[refs["Via 1"][1]]
        seg_fim_2 = pois_por_id[refs["Via 2"][1]]
        self.assertEqual(seg_fim_1.linha.conteudo.nos[-1].tipo, croqui_pb2.NoTrajeto.TipoNo.FIM_TOP)
        self.assertEqual(seg_fim_1.linha.conteudo.nos[-1].rotulo, "A")
        self.assertEqual(seg_fim_2.linha.conteudo.nos[-1].tipo, croqui_pb2.NoTrajeto.TipoNo.FIM_TOP)
        self.assertEqual(seg_fim_2.linha.conteudo.nos[-1].rotulo, "B")

        # Undo atômico
        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[0].rotulo, "1")
        self.assertEqual(self.mapa.pontos_de_interesse[0].linha.conteudo.nos[-1].tipo, croqui_pb2.NoTrajeto.TipoNo.PASSAGEM)

    def test_adicionar_rota_com_tracado_fatiamento_no_meio_da_curva(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        # Rota 1 reta vertical de 100, 500 até 100, 100 com nó intermediário em 100, 300
        dados_1 = {"nome": "Via Alpha", "tipo": "boulder", "grau": "V4", "nova": True}
        pontos_1 = [(100.0, 500.0), (100.0, 300.0), (100.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_1, pontos_1)

        # Rota 2 começa em 100, 500, dá snap no meio da curva em (100, 200) e sai para (180, 150)
        dados_2 = {"nome": "Via Beta", "tipo": "boulder", "grau": "V6", "nova": True}
        pontos_2 = [(100.0, 500.0), (100.0, 200.0), (180.0, 150.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_2, pontos_2)

        # Verifica fatiamento por curva
        self.assertEqual(len(self.mapa.pontos_de_interesse), 3)
        refs = {r.escalada: list(r.ids) for r in self.mapa.referencias}
        self.assertEqual(len(refs["Via Alpha"]), 2)
        self.assertEqual(len(refs["Via Beta"]), 2)
        self.assertEqual(refs["Via Alpha"][0], refs["Via Beta"][0])

    def test_adicionar_rota_com_tracado_travessia_triplo(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        # Rota base com 4 nós
        dados_base = {"nome": "Via Base", "tipo": "boulder", "grau": "V3", "nova": True}
        pontos_base = [(100.0, 500.0), (100.0, 400.0), (100.0, 300.0), (100.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_base, pontos_base)

        # Travessia entra em (100, 400), percorre até (100, 300) e sai para (180, 250)
        dados_trav = {"nome": "Travessia", "tipo": "boulder", "grau": "V7", "nova": True}
        pontos_trav = [(20.0, 400.0), (100.0, 400.0), (100.0, 300.0), (180.0, 250.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_trav, pontos_trav)

        refs = {r.escalada: list(r.ids) for r in self.mapa.referencias}
        self.assertEqual(len(refs["Via Base"]), 3)
        self.assertEqual(len(refs["Travessia"]), 3)
        self.assertEqual(refs["Via Base"][1], refs["Travessia"][1])

    def test_adicionar_rota_com_tracado_duplo_clique_mesmo_no_nao_quebra(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        # Rota base com 4 nós
        dados_base = {"nome": "Via Base", "tipo": "boulder", "grau": "V3", "nova": True}
        pontos_base = [(100.0, 500.0), (100.0, 400.0), (100.0, 300.0), (100.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_base, pontos_base)

        # Nova rota termina com duplo clique no nó (100, 400), gerando pontos repetidos no mesmo nó
        dados_nova = {"nome": "Via Duplo Clique", "tipo": "boulder", "grau": "V4", "nova": True}
        pontos_nova = [(20.0, 450.0), (100.0, 400.0), (100.0, 400.0)]
        # Não deve lançar ValueError de fatiamento triplo
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_nova, pontos_nova)

        refs = {r.escalada: list(r.ids) for r in self.mapa.referencias}
        # Via Base continua íntegra (não fatiada)
        self.assertEqual(len(refs["Via Base"]), 1)
        self.assertIn("Via Duplo Clique", refs)

    def test_adicionar_rota_com_tracado_travessia_sentido_inverso_fallback(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        dados_base = {"nome": "Via Base", "tipo": "boulder", "grau": "V3", "nova": True}
        pontos_base = [(100.0, 500.0), (100.0, 400.0), (100.0, 300.0), (100.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_base, pontos_base)

        # Travessia no sentido inverso (do nó 2 para o nó 1)
        dados_rev = {"nome": "Travessia Reversa", "tipo": "boulder", "grau": "V5", "nova": True}
        pontos_rev = [(20.0, 250.0), (100.0, 300.0), (100.0, 400.0), (180.0, 450.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_rev, pontos_rev)

        refs = {r.escalada: list(r.ids) for r in self.mapa.referencias}
        self.assertIn("Travessia Reversa", refs)

    def test_adicionar_rota_com_tracado_fallback_gracioso_em_excecao(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        dados_base = {"nome": "Via Base", "tipo": "boulder", "grau": "V3", "nova": True}
        pontos_base = [(100.0, 500.0), (100.0, 400.0), (100.0, 300.0), (100.0, 100.0)]
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_base, pontos_base)

        dados_trav = {"nome": "Travessia Falha", "tipo": "boulder", "grau": "V7", "nova": True}
        pontos_trav = [(20.0, 400.0), (100.0, 400.0), (100.0, 300.0), (180.0, 250.0)]

        from unittest.mock import patch
        with patch("editor.core.topologia_trajeto.fatiar_linha_triplo", side_effect=ValueError("Falha simulada")):
            self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_trav, pontos_trav)

        refs = {r.escalada: list(r.ids) for r in self.mapa.referencias}
        self.assertIn("Travessia Falha", refs)
        self.assertEqual(len(refs["Via Base"]), 1)

    def test_adicionar_rota_com_tracado_diversos_tipos(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        # Via esportiva com grau
        dados_esp = {"nome": "Via Esportiva", "tipo": "via_esportiva", "grau": "7a", "nova": True}
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_esp, [(10.0, 50.0), (10.0, 10.0)])

        # Via móvel
        dados_mov = {"nome": "Via Movel", "tipo": "via_movel", "nova": True}
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_mov, [(20.0, 50.0), (20.0, 10.0)])

        # Via múltiplas enfiadas
        dados_mult = {"nome": "Via Multiplas", "tipo": "via_multiplas_enfiadas", "nova": True}
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_mult, [(30.0, 50.0), (30.0, 10.0)])

        # Highline
        dados_hl = {"nome": "Highline Teste", "tipo": "highline", "nova": True}
        self.controller.adicionar_rota_com_tracado(self.msg_mapa_proxy, setor_proxy, dados_hl, [(40.0, 50.0), (40.0, 10.0)])

        setor = self.croqui.picos[0].setores_ou_grupos[0].setor.conteudo
        tipos = [e.WhichOneof("tipo") for e in setor.escaladas]
        self.assertIn("via_esportiva", tipos)
        self.assertIn("via_movel", tipos)
        self.assertIn("via_multiplas_enfiadas", tipos)
        self.assertIn("highline", tipos)

    def test_separar_linha_em_no_sucesso_e_undo_redo(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        nos = [
            {"x": 100, "y": 500, "tipo": 1, "rotulo": "1"},
            {"x": 120, "y": 300, "tipo": 0, "rotulo": ""},
            {"x": 140, "y": 100, "tipo": 0, "rotulo": ""},
        ]
        self.controller.adicionar_linha(self.msg_mapa_proxy, id_linha="l_original", nos=nos)
        self.controller.adicionar_referencia(
            self.msg_mapa_proxy,
            croqui_pb2.Mapa.Referencia(escalada="Via Original", ids=["l_original"])
        )

        id1, id2 = self.controller.separar_linha_em_no(self.msg_mapa_proxy, setor_proxy, "l_original", 1)
        self.assertEqual(len(self.mapa.pontos_de_interesse), 2)
        self.assertEqual(list(self.mapa.referencias[0].ids), [id1, id2])

        # Undo
        self.undo_stack.undo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 1)
        self.assertEqual(self.mapa.pontos_de_interesse[0].id, "l_original")
        self.assertEqual(list(self.mapa.referencias[0].ids), ["l_original"])

        # Redo
        self.undo_stack.redo()
        self.assertEqual(len(self.mapa.pontos_de_interesse), 2)
        self.assertEqual(list(self.mapa.referencias[0].ids), [id1, id2])

    def test_separar_linha_em_no_extremos_ou_invalido_dispara_erro(self):
        setor_proxy = self.model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
        nos = [{"x": 10, "y": 10}, {"x": 20, "y": 20}, {"x": 30, "y": 30}]
        self.controller.adicionar_linha(self.msg_mapa_proxy, id_linha="l_teste", nos=nos)

        with self.assertRaises(ValueError):
            self.controller.separar_linha_em_no(self.msg_mapa_proxy, setor_proxy, "l_teste", 0)

        with self.assertRaises(ValueError):
            self.controller.separar_linha_em_no(self.msg_mapa_proxy, setor_proxy, "l_teste", 2)

        with self.assertRaises(ValueError):
            self.controller.separar_linha_em_no(self.msg_mapa_proxy, setor_proxy, "linha_inexistente", 1)


if __name__ == '__main__':
    unittest.main()

