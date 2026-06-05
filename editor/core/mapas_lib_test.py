# Copyright (C) 2026 ARESTA
import unittest
import os
import tempfile
from .mapas_lib import converter_box_para_circulo, GerenciadorArquivosMapa

class TestMapasLib(unittest.TestCase):
    def test_converter_box_para_circulo_quadrado(self):
        # Box 100x100 -> Raio 50
        pt_dict = {
            'id': 'teste',
            'label': 'Label Teste',
            'box': {'x': 500, 'y': 500, 'comprimento': 100, 'largura': 100}
        }
        esperado = {
            'id': 'teste',
            'label': 'Label Teste',
            'circular': {'x': 500, 'y': 500, 'raio': 50}
        }
        self.assertEqual(converter_box_para_circulo(pt_dict), esperado)

    def test_converter_box_para_circulo_retangulo(self):
        # Box 100x80 -> Média 90 -> Raio 45 (diâmetro 90, r=45)
        # (100 + 80) / 4 = 180 / 4 = 45
        pt_dict = {
            'id': '1',
            'box': {'x': 10, 'y': 20, 'comprimento': 100, 'largura': 80}
        }
        resultado = converter_box_para_circulo(pt_dict)
        self.assertEqual(resultado['circular']['raio'], 45)
        self.assertEqual(resultado['circular']['x'], 10)
        self.assertEqual(resultado['circular']['y'], 20)

    def test_converter_box_para_circulo_arredondamento(self):
        # Box 10x11 -> Média 10.5 -> (10+11)/4 = 5.25 -> round 5
        pt_dict = {
            'box': {'x': 0, 'y': 0, 'comprimento': 10, 'largura': 11}
        }
        resultado = converter_box_para_circulo(pt_dict)
        self.assertEqual(resultado['circular']['raio'], 5)

    def test_entrada_invalida(self):
        self.assertIsNone(converter_box_para_circulo({}))
        self.assertIsNone(converter_box_para_circulo({'circular': {}}))

class TestGerenciadorArquivosMapa(unittest.TestCase):
    def setUp(self):
        self.gerenciador = GerenciadorArquivosMapa()
        self.temp_dir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ler_e_salvar_arquivo(self):
        caminho = os.path.join(self.temp_dir.name, "teste.md")
        conteudo_original = "---\nnome: Teste\nmapas: []\n---\nCorpo do Markdown"
        
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo_original)
            
        dados_yaml, corpo = self.gerenciador.ler_arquivo(caminho)
        self.assertEqual(dados_yaml['nome'], 'Teste')
        self.assertEqual(corpo, 'Corpo do Markdown')
        
        dados_yaml['nome'] = 'Alterado'
        self.gerenciador.salvar_arquivo(caminho, dados_yaml, corpo)
        
        with open(caminho, 'r', encoding='utf-8') as f:
            novo_conteudo = f.read()
            
        self.assertIn('nome: Alterado', novo_conteudo)
        self.assertIn('Corpo do Markdown', novo_conteudo)

if __name__ == '__main__':
    unittest.main()
