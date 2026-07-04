import unittest
import sys
from io import StringIO
from pathlib import Path
import os

# Adiciona a raiz do projeto ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from scripts import deploy_generated

class DeployGeneratedTest(unittest.TestCase):
    def test_aviso_escalada_duplicada(self):
        # Configurar um croqui compilado fictício
        compiled_data = {
            "picos": [
                {
                    "escaladas": [
                        {"nome": "Via Normal"},
                        {"nome": "Fenda do Desespero"},
                    ]
                },
                {
                    "faces": [
                        {
                            "escaladas": [
                                {"nome": "Via Normal"}, # Duplicado!
                                {"nome": "Teto do Macaco"}
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Redirecionar stdout para capturar o aviso
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Chamar a função (que ainda vamos implementar)
            deploy_generated.verificar_nomes_duplicados_de_escalada("croqui_teste", compiled_data)
        finally:
            sys.stdout = sys.__stdout__
            
        saida = captured_output.getvalue()
        
        self.assertIn("Aviso: A escalada 'Via Normal' aparece mais de uma vez no croqui 'croqui_teste'", saida)
        self.assertNotIn("Fenda do Desespero", saida)

if __name__ == '__main__':
    unittest.main()
