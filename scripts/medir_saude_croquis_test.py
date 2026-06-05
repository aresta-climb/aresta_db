import unittest
from unittest.mock import patch, mock_open
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import medir_saude_croquis

class TestMedirSaudeCroquis(unittest.TestCase):
    def test_check_status_desenho_extraivel_missing_file(self):
        with patch('pathlib.Path.exists', return_value=False):
            self.assertEqual(medir_saude_croquis.check_status_desenho_extraivel(Path("test")), "❌")

    def test_check_status_desenho_extraivel_values(self):
        test_cases = [
            ("NAO_TEM_DESENHO", "✅ (não)"),
            ("TEM_DESENHO_MAS_NAO_EXTRAIDO", "⚠️"),
            ("DESENHO_EXTRAIDO", "✅"),
            ("UNKNOWN", "❌"),
            (None, "❌"),
        ]
        
        for input_val, expected_emoji in test_cases:
            yaml_content = f"status_desenho_extraivel: {input_val}" if input_val else "{}"
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data=yaml_content)):
                    result = medir_saude_croquis.check_status_desenho_extraivel(Path("test"))
                    self.assertEqual(result, expected_emoji, f"Failed for {input_val}")

    def test_check_croqui_yaml(self):
        with patch('pathlib.Path.exists', return_value=True):
            self.assertTrue(medir_saude_croquis.check_croqui_yaml(Path("test")))
        with patch('pathlib.Path.exists', return_value=False):
            self.assertFalse(medir_saude_croquis.check_croqui_yaml(Path("test")))

    def test_check_publicar_croqui(self):
        # YAML com publicar_croqui = true
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="publicar_croqui: true")):
                self.assertTrue(medir_saude_croquis.check_publicar_croqui(Path("test")))
                
        # YAML com publicar_croqui = false
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="publicar_croqui: false")):
                self.assertFalse(medir_saude_croquis.check_publicar_croqui(Path("test")))
                
        # YAML sem publicar_croqui
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="nome: 'Teste'")):
                self.assertFalse(medir_saude_croquis.check_publicar_croqui(Path("test")))
                
        # Sem YAML
        with patch('pathlib.Path.exists', return_value=False):
            self.assertFalse(medir_saude_croquis.check_publicar_croqui(Path("test")))

    def test_generate_report_table(self):
        report_data = [
            {
                "Nome": "croqui1",
                "Publicado": "✅",
                "Revisado Manual": "✅",
                "Revisado Circ": "❌",
                "Status Desenho": "✅",
                "Pontos de Interesse": "✅ (1/1)",
                "Thumbnail": "✅",
                "Coordenadas Picos": "✅ (1/1)",
                "Mapas Gerais": "✅",
                "croqui.yaml": "✅",
                "Conteúdo PDF": "✅",
                "partes.json": "✅",
                "PDF Original": "✅"
            },
            {
                "Nome": "croqui2",
                "Publicado": "❌",
                "Revisado Manual": "❌",
                "Revisado Circ": "❌",
                "Status Desenho": "✅ (não)",
                "Pontos de Interesse": "❌ (0/1)",
                "Thumbnail": "❌",
                "Coordenadas Picos": "❌ (0/1)",
                "Mapas Gerais": "❌",
                "croqui.yaml": "✅",
                "Conteúdo PDF": "❌",
                "partes.json": "✅",
                "PDF Original": "✅"
            },
            {
                "Nome": "croqui3",
                "Publicado": "❌",
                "Revisado Manual": "❌",
                "Revisado Circ": "❌",
                "Status Desenho": "⚠️",
                "Pontos de Interesse": "N/A",
                "Thumbnail": "❌",
                "Coordenadas Picos": "N/A",
                "Mapas Gerais": "❌",
                "croqui.yaml": "❌",
                "Conteúdo PDF": "❌",
                "partes.json": "❌",
                "PDF Original": "❌"
            },
            {
                "Nome": "croqui4",
                "Publicado": "❌",
                "Revisado Manual": "❌",
                "Revisado Circ": "❌",
                "Status Desenho": "❌",
                "Pontos de Interesse": "N/A",
                "Thumbnail": "❌",
                "Coordenadas Picos": "N/A",
                "Mapas Gerais": "❌",
                "croqui.yaml": "❌",
                "Conteúdo PDF": "❌",
                "partes.json": "❌",
                "PDF Original": "❌"
            }
        ]
        
        table = medir_saude_croquis.generate_report_table(report_data)
        
        # Verifica se o cabeçalho de Desenho Extraível está correto:
        # ✅ = 1, ✅ (não) = 1 -> a_status_desenho = 2
        # ⚠️ = 1 -> c_sim_mas_nao = 1
        # ❌ = 1 -> c_unknown = 1
        # Formato esperado: (2/1/1)
        self.assertIn("Desenho Extraível (2/1/1)", table)
        
        # Verifica se outras partes do cabeçalho estão corretas (ex: Revisado Manual (1/4))
        self.assertIn("Revisado Manual (1/4)", table)
        
        # Verifica se o cabeçalho Publicado está correto
        self.assertIn("Publicado (1/4)", table)

if __name__ == '__main__':
    unittest.main()
