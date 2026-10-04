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

    def test_aviso_mapa_duplicado(self):
        compiled_data = {
            "picos": [
                {
                    "nome": "Pico Teste",
                    "setores_ou_grupos": [
                        {
                            "setor": {
                                "nome": "Setor 1",
                                "mapas": [{"caminho_imagem_mapa": "imagens/parede.webp"}],
                                "escaladas": [
                                    {
                                        "tradicional": {"nome": "Via 1"},
                                        "mapas": [{"caminho_imagem_mapa": "imagens/parede.webp"}]
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            deploy_generated.verificar_mapas_duplicados("croqui_teste", compiled_data)
        finally:
            sys.stdout = sys.__stdout__

        saida = captured_output.getvalue()
        self.assertIn("Aviso: O mapa 'imagens/parede.webp' no croqui 'croqui_teste' está sendo exibido em mais de um local", saida)
        self.assertIn("duplicação indevida de informação", saida)

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

    def test_deploy_com_erros_encadeia_excecao_original(self):
        """Testa que deploy() encadeia a exceção original causalmente via raise ... from e."""
        from unittest.mock import patch
        excecao_raiz = AttributeError("'NoneType' object has no attribute 'get'")
        with patch("scripts.deploy_generated.encontrar_croquis", return_value=[(Path("/fake"), {"id": "fake"})]):
            with patch("scripts.deploy_generated.passo_a_compilar_croquis", return_value=([], ["Erro simulado"], [excecao_raiz])):
                with patch("scripts.deploy_generated.preparar_generated"):
                    with patch("scripts.deploy_generated.carregar_dados_anteriores", return_value={}):
                        with self.assertRaises(RuntimeError) as ctx:
                            deploy_generated.deploy(Path("/fake/out"), sair_ao_falhar=False)
                        self.assertIs(ctx.exception.__cause__, excecao_raiz)

    def test_passo_a_compilar_croquis_captura_excecao_e_registra_traceback(self):
        """Testa que passo_a_compilar_croquis registra o traceback completo no console e retorna a exceção."""
        from unittest.mock import patch
        import tempfile
        croqui_dir = Path("/caminho/fake_croqui")
        croqui_data = {"id": "croqui_teste_erro"}

        with patch("scripts.deploy_generated.corrigir_database"):
            with patch("scripts.deploy_generated.processar_thumbnail"):
                with patch("scripts.deploy_generated.compilar_croqui", side_effect=AttributeError("Teste de falha no compilador")):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        deploy_generated.GENERATED_DIR = Path(tmp_dir)
                        captured_output = StringIO()
                        sys.stdout = captured_output
                        try:
                            resultado = deploy_generated.passo_a_compilar_croquis(
                                [(croqui_dir, croqui_data)],
                                gerar_arquivos_de_debug=False
                            )
                        finally:
                            sys.stdout = sys.__stdout__

                        saida = captured_output.getvalue()
                        self.assertIn("AttributeError: Teste de falha no compilador", saida)
                        self.assertIn("Traceback", saida)

                        # Verifica que a tupla retornada inclui a lista de exceções e a flag database_modificado
                        self.assertEqual(len(resultado), 4)
                        compilados, erros, excecoes, database_modificado = resultado
                        self.assertEqual(len(erros), 1)
                        self.assertEqual(len(excecoes), 1)
                        self.assertIsInstance(excecoes[0], AttributeError)

    def test_deploy_aviso_referencia_sem_identificador_nao_aborta_compilacao(self):
        """Testa que aviso de referência sem identificador é emitido sem abortar o fluxo de compilação."""
        from unittest.mock import patch, MagicMock
        from scripts.preparar_submissao_lib import compilar_croqui

        croqui_data = {
            "id": "teste_sem_id",
            "picos": [{
                "nome": "Pico 1",
                "setores_ou_grupos": [{
                    "setor": {
                        "conteudo": {
                            "nome": "Setor 1",
                            "mapas": [{
                                "pontos_de_interesse": [{"id": "p1", "circulo": {"x": 10, "y": 10, "raio": 5}}],
                                "referencias": [{"escalada": "Via 1", "ids": ["p1"]}]
                            }],
                            "escaladas": [{"via_esportiva": {"nome": "Via 1"}}]
                        }
                    }
                }]
            }]
        }

        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            with patch("builtins.open", MagicMock()), \
                 patch("scripts.preparar_submissao_lib.yaml.safe_load", return_value=croqui_data), \
                 patch("scripts.preparar_submissao_lib.yaml.dump"), \
                 patch("scripts.preparar_submissao_lib.Path.mkdir"), \
                 patch("scripts.preparar_submissao_lib.json_format.ParseDict"):
                resultado = compilar_croqui(Path("dummy_pico"), Path("dummy_dest.yaml"), Path("dummy_dest.binarypb"))
        finally:
            sys.stdout = sys.__stdout__

    def test_passo_a_compilar_croquis_migra_mapas_gerais_raw_pdf_contents(self):
        """Testa se a compilação completa via passo_a_compilar_croquis migra imagens de mapas gerais."""
        from PIL import Image
        import yaml
        import tempfile
        from aresta_api.proto.generated import croqui_pb2

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            croqui_dir = tmp_path / "croqui_lenheiro_fake"
            croqui_dir.mkdir()

            # 1. raw_pdf_contents com imagem
            raw_dir = croqui_dir / "raw_pdf_contents" / "imagens" / "mapas_gerais"
            raw_dir.mkdir(parents=True)
            img_raw = raw_dir / "p0_i3.webp"
            img = Image.new("RGB", (600, 400), color=(10, 20, 30))
            img.save(img_raw, format="WEBP")

            # 2. mapas_gerais.md
            mapas_md = croqui_dir / "mapas_gerais.md"
            mapas_md.write_text(
                "---\n"
                "mapas:\n"
                "  - caminho_imagem_mapa: raw_pdf_contents/imagens/mapas_gerais/p0_i3.webp\n"
                "    largura_mapa: 600\n"
                "    altura_mapa: 400\n"
                "---\n",
                encoding="utf-8"
            )

            # 3. croqui.yaml
            croqui_yaml = croqui_dir / "croqui.yaml"
            croqui_data = {
                "id": "lenheiro_fake",
                "nome": "Lenheiro Fake",
                "picos": [
                    {
                        "nome": "Pico 1",
                        "mapas_gerais": {
                            "caminho": "mapas_gerais.md"
                        }
                    }
                ]
            }
            with open(croqui_yaml, "w", encoding="utf-8") as f:
                yaml.dump(croqui_data, f)

            generated_dir = tmp_path / "generated"
            deploy_generated.GENERATED_DIR = generated_dir

            compilados, erros, excecoes, database_modificado = deploy_generated.passo_a_compilar_croquis(
                [(croqui_dir, croqui_data)],
                gerar_arquivos_de_debug=True
            )

            self.assertEqual(len(erros), 0, f"Erros durante compilação: {erros}")
            self.assertEqual(len(excecoes), 0)
            self.assertTrue(database_modificado)

            # Imagem no database deve ter sido migrada
            img_db_migrada = croqui_dir / "imagens" / "mapas_gerais_p0_i3.webp"
            self.assertTrue(img_db_migrada.exists())

            # Imagem no generated deve ter sido copiada
            img_gen_migrada = generated_dir / "lenheiro_fake" / "imagens" / "mapas_gerais_p0_i3.webp"
            self.assertTrue(img_gen_migrada.exists())

            # compilado.yaml deve apontar para o novo caminho
            comp_yaml = generated_dir / "lenheiro_fake" / "compilado.yaml"
            self.assertTrue(comp_yaml.exists())
            with open(comp_yaml, "r", encoding="utf-8") as f:
                dados_comp = yaml.safe_load(f)
            mapa_comp = dados_comp["picos"][0]["mapas_gerais"]["conteudo"]["mapas"][0]
            self.assertEqual(mapa_comp["caminho_imagem_mapa"], "imagens/mapas_gerais_p0_i3.webp")

            # compilado.binarypb deve conter o novo caminho
            comp_pb = generated_dir / "lenheiro_fake" / "compilado.binarypb"
            self.assertTrue(comp_pb.exists())
            croqui_pb = croqui_pb2.Croqui()
            with open(comp_pb, "rb") as f:
                croqui_pb.ParseFromString(f.read())
            self.assertEqual(
                croqui_pb.picos[0].mapas_gerais.conteudo.mapas[0].caminho_imagem_mapa,
                "imagens/mapas_gerais_p0_i3.webp"
            )

    def test_passo_a_compilar_croqui_com_anexos(self):
        import tempfile
        import yaml
        from PIL import Image
        from aresta_api.proto.generated import croqui_pb2

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            croqui_dir = tmp_path / "croqui_com_anexos"
            croqui_dir.mkdir()

            # 1. Pasta anexos/ com dois PDFs fictícios
            anexos_dir = croqui_dir / "anexos"
            anexos_dir.mkdir()
            pdf_ficha = anexos_dir / "ficha.pdf"
            pdf_ficha.write_bytes(b"%PDF-1.4 ficha ficticia")
            pdf_termo = anexos_dir / "termo.pdf"
            pdf_termo.write_bytes(b"%PDF-1.4 termo ficticio")

            # 2. Pasta imagens/ com uma imagem
            imagens_dir = croqui_dir / "imagens"
            imagens_dir.mkdir()
            img_path = imagens_dir / "foto.webp"
            Image.new("RGB", (100, 100), color=(50, 60, 70)).save(img_path, format="WEBP")

            # 3. croqui.yaml
            croqui_yaml = croqui_dir / "croqui.yaml"
            croqui_data = {
                "id": "croqui_com_anexos",
                "nome": "Croqui com Anexos",
                "descricao": "Documentos: [Ficha](anexos/ficha.pdf) e [Termo](anexos/termo.pdf)",
                "picos": [{
                    "nome": "Pico Teste",
                    "mapas_gerais": {
                        "conteudo": {
                            "mapas": [{"caminho_imagem_mapa": "imagens/foto.webp"}]
                        }
                    }
                }]
            }
            with open(croqui_yaml, "w", encoding="utf-8") as f:
                yaml.dump(croqui_data, f)

            generated_dir = tmp_path / "generated"
            deploy_generated.GENERATED_DIR = generated_dir

            compilados, erros, excecoes, database_modificado = deploy_generated.passo_a_compilar_croquis(
                [(croqui_dir, croqui_data)],
                gerar_arquivos_de_debug=True
            )

            self.assertEqual(len(erros), 0, f"Erros durante compilação: {erros}")
            self.assertEqual(len(excecoes), 0)

            # 1. Verifica se os anexos foram copiados para generated/croqui_com_anexos/anexos/
            dest_anexos = generated_dir / "croqui_com_anexos" / "anexos"
            self.assertTrue(dest_anexos.exists(), "Pasta anexos/ deve existir em generated")
            self.assertTrue((dest_anexos / "ficha.pdf").exists())
            self.assertTrue((dest_anexos / "termo.pdf").exists())

            # 2. Verifica se compilado.binarypb contém os anexos indexados em arquivos_externos
            dest_pb = generated_dir / "croqui_com_anexos" / "compilado.binarypb"
            self.assertTrue(dest_pb.exists())
            croqui_pb = croqui_pb2.Croqui()
            with open(dest_pb, "rb") as f:
                croqui_pb.ParseFromString(f.read())

            caminhos_externos = {arq.caminho: arq.checksum_sha256 for arq in croqui_pb.arquivos_externos}
            self.assertIn("anexos/ficha.pdf", caminhos_externos)
            self.assertIn("anexos/termo.pdf", caminhos_externos)
            self.assertIn("imagens/foto.webp", caminhos_externos)

            # Checksums devem bater com o cálculo real
            self.assertEqual(
                caminhos_externos["anexos/ficha.pdf"],
                deploy_generated.calcular_sha256(pdf_ficha)
            )
            self.assertEqual(
                caminhos_externos["anexos/termo.pdf"],
                deploy_generated.calcular_sha256(pdf_termo)
            )

    def test_verificar_imagens_inexistentes_avisa_mapa_inexistente(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir)
            compiled_data = {
                "picos": [
                    {
                        "setores_ou_grupos": [
                            {
                                "setor": {
                                    "mapas": [
                                        {"caminho_imagem_mapa": "imagens/mapa_inexistente.webp"}
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(croqui_dir, "croqui_teste", compiled_data)
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn("Aviso: A imagem 'imagens/mapa_inexistente.webp' referenciada no croqui 'croqui_teste'", saida)
            self.assertIn("não foi encontrada no disco", saida)

    def test_verificar_imagens_inexistentes_avisa_markdown_inexistente(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir)
            compiled_data = {
                "botoes": [
                    {
                        "texto": "Capa",
                        "destino": {
                            "secao_textual": {
                                "conteudo": "# Capa\n\n![Foto da Pedra](imagens/pedra_inexistente.webp)\n"
                            }
                        }
                    }
                ]
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(croqui_dir, "croqui_teste", compiled_data)
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn("Aviso: A imagem 'imagens/pedra_inexistente.webp' referenciada no croqui 'croqui_teste'", saida)

    def test_verificar_imagens_inexistentes_avisa_thumbnail_inexistente(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir)
            compiled_data = {
                "caminho_thumbnail": "imagens/thumb_inexistente.webp"
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(croqui_dir, "croqui_teste", compiled_data)
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn("Aviso: A imagem 'imagens/thumb_inexistente.webp' referenciada no croqui 'croqui_teste'", saida)

    def test_verificar_imagens_inexistentes_ignora_urls_externas(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir)
            compiled_data = {
                "descricao": "Texto com link externo: ![Logo](https://exemplo.com/logo.webp) e ![Outro](http://site.com/foto.png)"
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(croqui_dir, "croqui_teste", compiled_data)
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertNotIn("Aviso:", saida)

    def test_verificar_imagens_inexistentes_sucesso_quando_arquivo_existe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir)
            pasta_img = croqui_dir / "imagens"
            pasta_img.mkdir()
            (pasta_img / "mapa_ok.webp").write_bytes(b"dummy")
            (pasta_img / "foto_ok.webp").write_bytes(b"dummy")

            compiled_data = {
                "picos": [
                    {
                        "setores_ou_grupos": [
                            {
                                "setor": {
                                    "descricao": "![Foto](imagens/foto_ok.webp)",
                                    "mapas": [
                                        {"caminho_imagem_mapa": "imagens/mapa_ok.webp"}
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(croqui_dir, "croqui_teste", compiled_data)
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertNotIn("Aviso:", saida)

    def test_deploy_retorna_booleano_database_modificado(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            with patch("scripts.deploy_generated.encontrar_croquis", return_value=[]):
                # Sem croquis para compilar, deve retornar False
                resultado = deploy_generated.deploy(out_dir)
                self.assertIs(resultado, False)

            with patch("scripts.deploy_generated.encontrar_croquis") as mock_encontrar:
                fake_croqui_dir = Path(tmp_dir) / "fake"
                fake_croqui_dir.mkdir(exist_ok=True)
                mock_encontrar.return_value = [(fake_croqui_dir, {"id": "fake"})]
                with patch("scripts.deploy_generated.carregar_dados_anteriores", return_value={}):
                    with patch("scripts.deploy_generated.passo_a_compilar_croquis", return_value=([("fake", {"id": "fake"}, fake_croqui_dir / "compilado.binarypb")], [], [], True)):
                        with patch("scripts.deploy_generated.passo_b_calcular_checksums", return_value={"fake": "hash"}):
                            with patch("scripts.deploy_generated.passo_c_gerar_indice"):
                                with patch("scripts.deploy_generated.passo_d_gerar_manifesto_serving"):
                                    (out_dir / "fake").mkdir(parents=True, exist_ok=True)
                                    (out_dir / "fake" / "compilado.binarypb").write_bytes(b"dummy")
                                    resultado = deploy_generated.deploy(out_dir)
                                    self.assertIs(resultado, True)

    def test_deploy_sem_alvos_compila_todos_os_croquis(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            fake_croqui_dir = Path(tmp_dir) / "fake"
            fake_croqui_dir.mkdir(exist_ok=True)
            croquis_esperados = [(fake_croqui_dir, {"id": "fake"})]

            with patch("scripts.deploy_generated.encontrar_croquis", return_value=croquis_esperados):
                with patch("scripts.deploy_generated.carregar_dados_anteriores", return_value={}):
                    with patch("scripts.deploy_generated.passo_a_compilar_croquis") as mock_passo_a:
                        mock_passo_a.return_value = (
                            [("fake", {"id": "fake"}, fake_croqui_dir / "compilado.binarypb")],
                            [],
                            [],
                            False,
                        )
                        with patch("scripts.deploy_generated.passo_b_calcular_checksums", return_value={"fake": "hash"}):
                            with patch("scripts.deploy_generated.passo_c_gerar_indice"):
                                with patch("scripts.deploy_generated.passo_d_gerar_manifesto_serving"):
                                    (out_dir / "fake").mkdir(parents=True, exist_ok=True)
                                    (out_dir / "fake" / "compilado.binarypb").write_bytes(b"dummy")
                                    deploy_generated.deploy(out_dir, target_paths=None)

                                    # Verifica se passo_a_compilar_croquis recebeu todos os croquis encontrados
                                    mock_passo_a.assert_called_once()
                                    args_passados, _ = mock_passo_a.call_args
                                    self.assertEqual(args_passados[0], croquis_esperados)


if __name__ == '__main__':
    unittest.main()

