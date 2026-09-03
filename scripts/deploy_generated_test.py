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

            # Verifica que o indice.yaml foi gravado estritamente com quebras LF (\n)
            indice_yaml = Path(tmp_dir) / "indice.yaml"
            self.assertTrue(indice_yaml.is_file())
            self.assertNotIn(b"\r\n", indice_yaml.read_bytes())

    def test_passo_c_gerar_indice_tamanho_download_bytes(self):
        # Configurar croqui de teste com compilado.binarypb e pasta de imagens
        croqui_data = {
            "publicar_croqui": True,
            "picos": [
                {
                    "precomputados": {
                        "total_escaladas": 1,
                    }
                }
            ]
        }
        checksums = {"croqui_teste": "dummy_checksum"}

        import tempfile
        import yaml
        with tempfile.TemporaryDirectory() as tmp_dir:
            deploy_generated.GENERATED_DIR = Path(tmp_dir)
            croqui_dir = Path(tmp_dir) / "croqui_teste"
            croqui_dir.mkdir(parents=True, exist_ok=True)

            # Arquivo compilado com 100 bytes
            pb_path = croqui_dir / "compilado.binarypb"
            pb_path.write_bytes(b"x" * 100)

            # Pasta imagens com 500 bytes válidos (200 + 300) e 1000 bytes excluídos em raw_mapas
            imagens_dir = croqui_dir / "imagens"
            imagens_dir.mkdir(parents=True, exist_ok=True)
            (imagens_dir / "foto1.webp").write_bytes(b"a" * 200)
            (imagens_dir / "foto2.webp").write_bytes(b"b" * 300)

            raw_mapas_dir = imagens_dir / "raw_mapas"
            raw_mapas_dir.mkdir(parents=True, exist_ok=True)
            (raw_mapas_dir / "rascunho.png").write_bytes(b"c" * 1000)

            compilados = [("croqui_teste", croqui_data, pb_path)]

            # Executa a geração do índice
            indice = deploy_generated.passo_c_gerar_indice(compilados, checksums, is_producao=False)

            # Verifica se o tamanho total foi calculado e gravado no índice binário (100 + 200 + 300 = 600 bytes)
            self.assertEqual(len(indice.croquis), 1)
            resumo = indice.croquis[0]
            self.assertEqual(resumo.precomputados.tamanho_download_bytes, 600)

            # Verifica se a chave foi espelhada no indice.yaml
            indice_yaml_path = Path(tmp_dir) / "indice.yaml"
            self.assertTrue(indice_yaml_path.is_file())
            dados_yaml = yaml.safe_load(indice_yaml_path.read_text(encoding="utf-8"))
            self.assertIn("croquis", dados_yaml)
            self.assertIn("precomputados", dados_yaml["croquis"][0])
            self.assertEqual(dados_yaml["croquis"][0]["precomputados"].get("tamanho_download_bytes"), 600)

    def test_passo_d_gerar_manifesto_serving_salva_com_quebras_lf(self):
        import tempfile
        from aresta_api.proto.generated import indice_pb2

        with tempfile.TemporaryDirectory() as tmp_dir:
            deploy_generated.GENERATED_DIR = Path(tmp_dir)
            indice = indice_pb2.Indice()
            deploy_generated.passo_d_gerar_manifesto_serving(indice)

            manifesto_yaml = Path(tmp_dir) / "arquivos_serving.yaml"
            self.assertTrue(manifesto_yaml.is_file())
            self.assertNotIn(b"\r\n", manifesto_yaml.read_bytes())

    def test_precompilacao_linhas_mapas(self):
        from scripts.preparar_submissao_lib import precompilar_linhas_mapas_recursivo
        
        croqui_data = {
            "picos": [
                {
                    "mapas_gerais": {
                        "conteudo": {
                            "mapas": [
                                {
                                    "pontos_de_interesse": [
                                        {
                                            "id": "via_1",
                                            "cor": "#FF6D00",
                                            "linha": {
                                                "estilo": "TRACEJADO",
                                                "espessura": 3,
                                                "conteudo": {
                                                    "nos": [
                                                        {"x": 10, "y": 20, "tipo": 1, "rotulo": "1"},
                                                        {"x": 50, "y": 80, "tipo": 0, "rotulo": ""},
                                                        {"x": 100, "y": 200, "tipo": 5, "rotulo": ""}
                                                    ]
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                }
            ]
        }
        
        precompilar_linhas_mapas_recursivo(croqui_data)
        
        mapa = croqui_data["picos"][0]["mapas_gerais"]["conteudo"]["mapas"][0]
        poi = mapa["pontos_de_interesse"][0]
        self.assertNotIn("conteudo", poi["linha"])
        self.assertIn("compilado", poi["linha"])
        compilado = poi["linha"]["compilado"]
        self.assertIn("caminho_svg", compilado)
        self.assertTrue(compilado["caminho_svg"].startswith("M 10 20"))
        self.assertIn("caixa_delimitadora", compilado)
        self.assertIn("x", compilado["caixa_delimitadora"])
        self.assertIn("y", compilado["caixa_delimitadora"])
        self.assertIn("comprimento", compilado["caixa_delimitadora"])
        self.assertIn("largura", compilado["caixa_delimitadora"])
        # Nós do tipo PASSAGEM (0) não devem gerar marcadores no compilado
        self.assertEqual(len(compilado["marcadores"]), 2)
        tipos_marcadores = [m["tipo"] for m in compilado["marcadores"]]
        self.assertIn(1, tipos_marcadores)
        self.assertIn(5, tipos_marcadores)
        self.assertNotIn(0, tipos_marcadores)

    def test_validacao_linhas_mapas(self):
        from scripts.preparar_submissao_lib import validar_pontos_de_interesse_recursivo
        
        # Válido com conteúdo
        croqui_valido = {
            "pontos_de_interesse": [
                {
                    "id": "v1",
                    "linha": {
                        "conteudo": {
                            "nos": [
                                {"x": 0, "y": 0},
                                {"x": 10, "y": 10}
                            ]
                        }
                    }
                }
            ]
        }
        validar_pontos_de_interesse_recursivo(croqui_valido, "raiz")
        
        # Inválido: menos de 2 nós
        croqui_poucos_nos = {
            "pontos_de_interesse": [
                {
                    "id": "v1",
                    "linha": {
                        "conteudo": {
                            "nos": [
                                {"x": 0, "y": 0}
                            ]
                        }
                    }
                }
            ]
        }
        with self.assertRaises(ValueError):
            validar_pontos_de_interesse_recursivo(croqui_poucos_nos, "raiz")
            
        # Válido com compilado
        croqui_compilado = {
            "pontos_de_interesse": [
                {
                    "id": "v1",
                    "linha": {
                        "compilado": {
                            "caminho_svg": "M 0 0 C 1 1 2 2 3 3"
                        }
                    }
                }
            ]
        }
        validar_pontos_de_interesse_recursivo(croqui_compilado, "raiz")

    def test_deploy_com_erros_e_sair_ao_falhar_falso_lanca_runtime_error(self):
        """Testa que deploy() com sair_ao_falhar=False não encerra o processo via sys.exit(1), mas lança RuntimeError."""
        from unittest.mock import patch
        with patch("scripts.deploy_generated.encontrar_croquis", return_value=[(Path("/fake"), {"id": "fake"})]):
            with patch("scripts.deploy_generated.passo_a_compilar_croquis", return_value=([], ["Erro simulado de compilação"])):
                with patch("scripts.deploy_generated.preparar_generated"):
                    with patch("scripts.deploy_generated.carregar_dados_anteriores", return_value={}):
                        with self.assertRaises(RuntimeError) as ctx:
                            deploy_generated.deploy(Path("/fake/out"), sair_ao_falhar=False)
                        self.assertIn("Erro simulado de compilação", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
