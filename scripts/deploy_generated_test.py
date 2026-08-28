# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

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
                        {"tradicional": {"nome": "Via Normal"}},
                        {"tradicional": {"nome": "Fenda do Desespero"}},
                    ]
                },
                {
                    "faces": [
                        {
                            "escaladas": [
                                {"tradicional": {"nome": "Via Normal"}}, # Duplicado!
                                {"tradicional": {"nome": "Teto do Macaco"}}
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

    def test_passo_c_gerar_indice_precomputados(self):
        # Configurar um croqui_data com picos e precomputados
        croqui_data = {
            "publicar_croqui": True,
            "picos": [
                {
                    "precomputados": {
                        "total_escaladas": 10,
                        "total_setores": 2,
                        "total_grupos": 1,
                        "total_esportivas": 5,
                        "total_moveis": 3,
                        "total_boulders": 2,
                        "total_multiplas_enfiadas": 0,
                        "total_highlines": 0
                    }
                },
                {
                    "precomputados": {
                        "total_escaladas": 5,
                        "total_setores": 1,
                        "total_grupos": 0,
                        "total_esportivas": 0,
                        "total_moveis": 0,
                        "total_boulders": 0,
                        "total_multiplas_enfiadas": 5,
                        "total_highlines": 0
                    }
                }
            ]
        }
        
        compilados = [("croqui_teste", croqui_data, Path("dummy_pb"))]
        checksums = {"croqui_teste": "dummy_checksum"}
        
        import tempfile
        # Inicializa a variável global que é esperada pela função passo_c
        with tempfile.TemporaryDirectory() as tmp_dir:
            deploy_generated.GENERATED_DIR = Path(tmp_dir)
            
            # Chama a função passo_c_gerar_indice e verifica o índice gerado
            indice = deploy_generated.passo_c_gerar_indice(compilados, checksums, is_producao=False)
            
            # Verifica se o resumo foi criado e os precomputados agregados corretamente
            self.assertEqual(len(indice.croquis), 1)
            resumo = indice.croquis[0]
            self.assertTrue(resumo.HasField("precomputados"))
            self.assertEqual(resumo.precomputados.total_escaladas, 15)
            self.assertEqual(resumo.precomputados.total_setores, 3)
            self.assertEqual(resumo.precomputados.total_grupos, 1)
            self.assertEqual(resumo.precomputados.total_esportivas, 5)
            self.assertEqual(resumo.precomputados.total_moveis, 3)
            self.assertEqual(resumo.precomputados.total_boulders, 2)
            self.assertEqual(resumo.precomputados.total_multiplas_enfiadas, 5)
            self.assertEqual(resumo.precomputados.total_highlines, 0)

if __name__ == '__main__':
    unittest.main()
