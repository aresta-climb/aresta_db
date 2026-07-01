import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.dialogo_busca_referencia import DialogoBuscaReferencia

app = QApplication.instance() or QApplication(sys.argv)

class DialogoBuscaReferenciaTest(unittest.TestCase):
    def setUp(self):
        croqui = croqui_pb2.Croqui()
        croqui.nome = "Croqui Teste"
        
        pico = croqui.picos.add(nome="Pico Teste")
        
        sg_grupo = pico.setores_ou_grupos.add()
        grupo = sg_grupo.grupo.conteudo
        grupo.nome = "Grupo Teste"
        
        setor_msg = grupo.setores.add()
        setor = setor_msg.conteudo
        setor.nome = "Setor Teste"
        
        via = setor.escaladas.add()
        via.via_esportiva.nome = "Via Teste"
        
        self.model = CroquiModel(croqui)
        self.dialogo = DialogoBuscaReferencia(self.model)

    def test_carregar_entidades(self):
        # Deve ter carregado Grupo, Setor, e Via (3 itens no total)
        self.assertEqual(len(self.dialogo.todas_entidades), 3)
        self.assertEqual(self.dialogo.todas_entidades[0]["tipo"], "Grupo")
        self.assertEqual(self.dialogo.todas_entidades[1]["tipo"], "Setor")
        self.assertEqual(self.dialogo.todas_entidades[2]["tipo"], "Escalada")

    def test_popular_lista_e_filtrar(self):
        # Sem filtro
        self.assertEqual(self.dialogo.lista_resultados.count(), 3)
        
        # Filtrar por "Via"
        self.dialogo.input_busca.setText("Via")
        self.assertEqual(self.dialogo.lista_resultados.count(), 1)
        self.assertIn("Via Teste", self.dialogo.lista_resultados.item(0).text())

    def test_selecionar_retorna_referencia(self):
        # Filtra e seleciona a Via
        self.dialogo.input_busca.setText("Via")
        self.dialogo.lista_resultados.setCurrentRow(0)
        
        self.dialogo.accept()
        
        ref = self.dialogo.obter_referencia()
        self.assertIsNotNone(ref)
        self.assertEqual(ref.grupo, "Grupo Teste")
        self.assertEqual(ref.setor, "Setor Teste")
        self.assertEqual(ref.escalada, "Via Teste")
        self.assertEqual(len(ref.ids), 0) # Sem IDs ainda

if __name__ == '__main__':
    unittest.main()
