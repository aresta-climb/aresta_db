# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import unittest
from io import StringIO
from pathlib import Path

# Adiciona a raiz do projeto ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from editor.core.serializacao_util import carregar_yaml, serializar_yaml
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
                                {"tradicional": {"nome": "Via Normal"}},  # Duplicado!
                                {"tradicional": {"nome": "Teto do Macaco"}},
                            ]
                        }
                    ]
                },
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

        self.assertIn(
            "Aviso: A escalada 'Via Normal' aparece mais de uma vez no croqui 'croqui_teste'", saida
        )
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
                                        "mapas": [{"caminho_imagem_mapa": "imagens/parede.webp"}],
                                    }
                                ],
                            }
                        }
                    ],
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
        self.assertIn(
            "Aviso: O mapa 'imagens/parede.webp' no croqui 'croqui_teste' está sendo exibido em mais de um local",
            saida,
        )
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
                        "total_highlines": 0,
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
                        "total_highlines": 0,
                    }
                },
            ],
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
            ],
        }
        checksums = {"croqui_teste": "dummy_checksum"}

        import tempfile

        from editor.core.serializacao_util import carregar_yaml

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
            dados_yaml = carregar_yaml(indice_yaml_path.read_text(encoding="utf-8"))
            self.assertIn("croquis", dados_yaml)
            self.assertIn("precomputados", dados_yaml["croquis"][0])
            self.assertEqual(
                dados_yaml["croquis"][0]["precomputados"].get("tamanho_download_bytes"), 600
            )

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

    def test_passo_e_gerar_catalogo_sqlite(self):
        import tempfile

        from aresta_api.proto.generated import croqui_pb2

        with tempfile.TemporaryDirectory() as tmp_dir:
            deploy_generated.GENERATED_DIR = Path(tmp_dir)
            croqui_dir = Path(tmp_dir) / "br_mg_bh_teste"
            croqui_dir.mkdir()

            croqui = croqui_pb2.Croqui()
            croqui.uid = "croqui_teste_1"
            croqui.id = "br_mg_bh_teste"
            croqui.nome = "Pico Teste"
            (croqui_dir / "compilado.binarypb").write_bytes(croqui.SerializeToString())

            caminho_db = deploy_generated.passo_e_gerar_catalogo_sqlite(verbose=True)
            self.assertTrue(caminho_db.is_file())
            self.assertFalse((Path(tmp_dir) / "catalogo.db.gz").exists())

    def test_passo_d_inclui_apenas_catalogo_db(self):
        import tempfile

        from aresta_api.proto.generated import indice_pb2
        from editor.core.serializacao_util import carregar_yaml

        with tempfile.TemporaryDirectory() as tmp_dir:
            deploy_generated.GENERATED_DIR = Path(tmp_dir)
            (Path(tmp_dir) / "catalogo.db").write_bytes(b"sqlite_fake_content")
            (Path(tmp_dir) / "catalogo.db.gz").write_bytes(b"gzip_fake_content")

            indice = indice_pb2.Indice()
            deploy_generated.passo_d_gerar_manifesto_serving(indice)

            manifesto_yaml = Path(tmp_dir) / "arquivos_serving.yaml"
            dados = carregar_yaml(manifesto_yaml.read_text(encoding="utf-8"))
            caminhos = [arq["caminho_relativo"] for arq in dados.get("arquivos", [])]

            self.assertIn("catalogo.db", caminhos)
            self.assertNotIn("catalogo.db.gz", caminhos)

    def test_deploy_gera_catalogo_sqlite_e_manifesto_integrado(self):
        import sqlite3
        import tempfile

        from aresta_api.proto.generated import indice_pb2
        from scripts.gerar_catalogo_sqlite_lib import obter_versao_catalogo

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            db_dir = Path(tmp_dir) / "database"
            croqui_dir = db_dir / "br_mg_bh_real"
            croqui_dir.mkdir(parents=True)

            (croqui_dir / "setor_real.md").write_text(
                "---\n"
                "uid: setorReal12345\n"
                "nome: Setor Real\n"
                "escaladas:\n"
                "  - uid: viaReal1234567\n"
                "    via_esportiva:\n"
                "      nome: Via Real\n"
                "      dificuldade: BR_7A\n"
                "---\n"
                "Descricao do setor real.\n",
                encoding="utf-8",
            )
            (croqui_dir / "croqui.yaml").write_text(
                "id: br_mg_bh_real\n"
                "uid: croquiReal1234\n"
                "nome: Pico Real\n"
                "publicar_croqui: true\n"
                "ultima_migracao: 5\n"
                "picos:\n"
                "  - nome: Pico Real\n"
                "    estado: MG\n"
                "    setores_ou_grupos:\n"
                "      - setor:\n"
                "          caminho: setor_real.md\n",
                encoding="utf-8",
            )

            deploy_generated.deploy(
                out_dir,
                database_dir=db_dir,
                is_producao=True,
                verbose=False,
            )

            # Verifica catalogo.db
            db_path = out_dir / "catalogo.db"
            gz_path = out_dir / "catalogo.db.gz"
            self.assertTrue(db_path.is_file())
            self.assertFalse(gz_path.exists())

            versao_esperada = obter_versao_catalogo(db_path)
            self.assertEqual(len(versao_esperada), 16)

            # Verifica versao_catalogo em indice.binarypb e indice.yaml
            idx_pb = indice_pb2.Indice()
            idx_pb.ParseFromString((out_dir / "indice.binarypb").read_bytes())
            self.assertEqual(idx_pb.versao_catalogo, versao_esperada)

            idx_yaml = carregar_yaml((out_dir / "indice.yaml").read_text(encoding="utf-8"))
            self.assertEqual(idx_yaml.get("versao_catalogo"), versao_esperada)

            con = sqlite3.connect(db_path)
            try:
                cur = con.cursor()
                cur.execute("SELECT nome FROM catalogo_croquis WHERE croqui_uid = 'croquiReal1234'")
                self.assertEqual(cur.fetchone()[0], "Pico Real")
                cur.execute(
                    "SELECT nome, escalada_grau, tipo FROM catalogo_aresta WHERE uid = 'viaReal1234567'"
                )
                linha_via = cur.fetchone()
                self.assertEqual(linha_via[0], "Via Real")
                self.assertEqual(linha_via[1], "7a")
                self.assertEqual(linha_via[2], "escalada")
            finally:
                con.close()

            # Verifica arquivos_serving.yaml
            manifesto = carregar_yaml(
                (out_dir / "arquivos_serving.yaml").read_text(encoding="utf-8")
            )
            caminhos = [arq["caminho_relativo"] for arq in manifesto.get("arquivos", [])]
            self.assertIn("catalogo.db", caminhos)
            self.assertNotIn("catalogo.db.gz", caminhos)

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
                                                        {
                                                            "x": 10,
                                                            "y": 20,
                                                            "tipo": 1,
                                                            "rotulo": "1",
                                                        },
                                                        {"x": 50, "y": 80, "tipo": 0, "rotulo": ""},
                                                        {
                                                            "x": 100,
                                                            "y": 200,
                                                            "tipo": 5,
                                                            "rotulo": "",
                                                        },
                                                    ]
                                                },
                                            },
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
                {"id": "v1", "linha": {"conteudo": {"nos": [{"x": 0, "y": 0}, {"x": 10, "y": 10}]}}}
            ]
        }
        validar_pontos_de_interesse_recursivo(croqui_valido, "raiz")

        # Inválido: menos de 2 nós
        croqui_poucos_nos = {
            "pontos_de_interesse": [
                {"id": "v1", "linha": {"conteudo": {"nos": [{"x": 0, "y": 0}]}}}
            ]
        }
        with self.assertRaises(ValueError):
            validar_pontos_de_interesse_recursivo(croqui_poucos_nos, "raiz")

        # Válido com compilado
        croqui_compilado = {
            "pontos_de_interesse": [
                {"id": "v1", "linha": {"compilado": {"caminho_svg": "M 0 0 C 1 1 2 2 3 3"}}}
            ]
        }
        validar_pontos_de_interesse_recursivo(croqui_compilado, "raiz")

    def test_deploy_com_erros_e_sair_ao_falhar_falso_lanca_runtime_error(self):
        """Testa que deploy() com sair_ao_falhar=False não encerra o processo via sys.exit(1), mas lança RuntimeError."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_dir = Path(tmp_dir) / "database"
            croqui_dir = db_dir / "croqui_invalido"
            croqui_dir.mkdir(parents=True)
            (croqui_dir / "croqui.yaml").write_text(
                "id: croqui_invalido\nnome: Croqui Invalido\nultima_migracao: 5\ncampo_inexistente_proto: 123\n",
                encoding="utf-8",
            )
            out_dir = Path(tmp_dir) / "out"
            with self.assertRaises(RuntimeError) as ctx:
                deploy_generated.deploy(out_dir, database_dir=db_dir, sair_ao_falhar=False)
            self.assertIn("campo_inexistente_proto", str(ctx.exception))

    def test_deploy_com_erros_encadeia_excecao_original(self):
        """Testa que deploy() encadeia a exceção original causalmente via raise ... from e."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_dir = Path(tmp_dir) / "database"
            croqui_dir = db_dir / "croqui_invalido"
            croqui_dir.mkdir(parents=True)
            (croqui_dir / "croqui.yaml").write_text(
                "id: croqui_invalido\nnome: Croqui Invalido\nultima_migracao: 5\ncampo_inexistente_proto: 123\n",
                encoding="utf-8",
            )
            out_dir = Path(tmp_dir) / "out"
            with self.assertRaises(RuntimeError) as ctx:
                deploy_generated.deploy(out_dir, database_dir=db_dir, sair_ao_falhar=False)
            self.assertIsInstance(ctx.exception.__cause__, ValueError)

    def test_passo_a_compilar_croquis_captura_excecao_e_registra_traceback(self):
        """Testa que passo_a_compilar_croquis registra o traceback completo no console e retorna a exceção."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir) / "croqui_teste_erro"
            croqui_dir.mkdir(parents=True)
            croqui_data = {
                "id": "croqui_teste_erro",
                "nome": "Teste Erro",
                "ultima_migracao": 5,
                "campo_desconhecido_protobuf": True,
            }
            (croqui_dir / "croqui.yaml").write_text(
                serializar_yaml(croqui_data, incluir_cabecalho_spdx=True),
                encoding="utf-8",
            )
            deploy_generated.GENERATED_DIR = Path(tmp_dir) / "generated"
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                resultado = deploy_generated.passo_a_compilar_croquis([(croqui_dir, croqui_data)])
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn("ValueError", saida)
            self.assertIn("Traceback", saida)

            self.assertEqual(len(resultado), 4)
            compilados, erros, excecoes, database_modificado = resultado
            self.assertEqual(len(erros), 1)
            self.assertEqual(len(excecoes), 1)
            self.assertIsInstance(excecoes[0], ValueError)

    def test_deploy_aviso_referencia_sem_identificador_nao_aborta_compilacao(self):
        """Testa que aviso de referência sem identificador é emitido sem abortar o fluxo de compilação."""
        import tempfile

        from scripts.preparar_submissao_lib import compilar_croqui

        croqui_data = {
            "id": "teste_sem_id",
            "uid": "croquiSemId123",
            "nome": "Teste Sem ID",
            "picos": [
                {
                    "nome": "Pico 1",
                    "setores_ou_grupos": [
                        {
                            "setor": {
                                "conteudo": {
                                    "uid": "setorSemId1234",
                                    "nome": "Setor 1",
                                    "mapas": [
                                        {
                                            "pontos_de_interesse": [
                                                {
                                                    "id": "p1",
                                                    "uid": "poiSemId123456",
                                                    "circulo": {"x": 10, "y": 10, "raio": 5},
                                                }
                                            ],
                                            "referencias": [{"escalada": "Via 1", "ids": ["p1"]}],
                                        }
                                    ],
                                    "escaladas": [
                                        {
                                            "uid": "viaSemId123456",
                                            "via_esportiva": {"nome": "Via 1"},
                                        }
                                    ],
                                }
                            }
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            pico_dir = Path(tmp_dir) / "pico"
            pico_dir.mkdir()
            (pico_dir / "croqui.yaml").write_text(
                serializar_yaml(croqui_data, incluir_cabecalho_spdx=True),
                encoding="utf-8",
            )
            dest_pb = Path(tmp_dir) / "out" / "compilado.binarypb"

            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                compilar_croqui(pico_dir, None, dest_pb)
            finally:
                sys.stdout = sys.__stdout__

            self.assertTrue(dest_pb.is_file())
            self.assertIn("não possui label ou rótulo", captured_output.getvalue())

    def test_passo_a_compilar_croquis_migra_mapas_gerais_raw_pdf_contents(self):
        """Testa se a compilação completa via passo_a_compilar_croquis migra imagens de mapas gerais."""
        import tempfile

        from PIL import Image

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
                encoding="utf-8",
            )

            # 3. croqui.yaml
            croqui_yaml = croqui_dir / "croqui.yaml"
            croqui_data = {
                "id": "lenheiro_fake",
                "nome": "Lenheiro Fake",
                "picos": [{"nome": "Pico 1", "mapas_gerais": {"caminho": "mapas_gerais.md"}}],
            }
            croqui_yaml.write_text(
                serializar_yaml(croqui_data, incluir_cabecalho_spdx=True),
                encoding="utf-8",
            )

            generated_dir = tmp_path / "generated"
            deploy_generated.GENERATED_DIR = generated_dir

            compilados, erros, excecoes, database_modificado = (
                deploy_generated.passo_a_compilar_croquis([(croqui_dir, croqui_data)])
            )

            self.assertEqual(len(erros), 0, f"Erros durante compilação: {erros}")
            self.assertEqual(len(excecoes), 0)
            self.assertTrue(database_modificado)

            # Imagem no database deve ter sido migrada
            img_db_migrada = croqui_dir / "imagens" / "mapas_gerais_p0_i3.webp"
            self.assertTrue(img_db_migrada.exists())

            # Imagem no generated deve ter sido copiada
            img_gen_migrada = (
                generated_dir / "lenheiro_fake" / "imagens" / "mapas_gerais_p0_i3.webp"
            )
            self.assertTrue(img_gen_migrada.exists())

            # compilado.yaml deve ser gerado; compilado.md NÃO deve ser gerado
            comp_yaml = generated_dir / "lenheiro_fake" / "compilado.yaml"
            comp_md = generated_dir / "lenheiro_fake" / "compilado.md"
            self.assertTrue(comp_yaml.exists())
            self.assertFalse(comp_md.exists())

            # compilado.binarypb deve conter o novo caminho
            comp_pb = generated_dir / "lenheiro_fake" / "compilado.binarypb"
            self.assertTrue(comp_pb.exists())
            croqui_pb = croqui_pb2.Croqui()
            with open(comp_pb, "rb") as f:
                croqui_pb.ParseFromString(f.read())
            self.assertEqual(
                croqui_pb.picos[0].mapas_gerais.conteudo.mapas[0].caminho_imagem_mapa,
                "imagens/mapas_gerais_p0_i3.webp",
            )

    def test_passo_a_compilar_croqui_com_anexos(self):
        import tempfile

        from PIL import Image

        from aresta_api.proto.generated import croqui_pb2
        from editor.core.serializacao_util import serializar_yaml

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
                "picos": [
                    {
                        "nome": "Pico Teste",
                        "mapas_gerais": {
                            "conteudo": {"mapas": [{"caminho_imagem_mapa": "imagens/foto.webp"}]}
                        },
                    }
                ],
            }
            with open(croqui_yaml, "w", encoding="utf-8") as f:
                serializar_yaml(croqui_data, f)

            generated_dir = tmp_path / "generated"
            deploy_generated.GENERATED_DIR = generated_dir

            compilados, erros, excecoes, database_modificado = (
                deploy_generated.passo_a_compilar_croquis(
                    [(croqui_dir, croqui_data)], gerar_arquivos_de_debug=True
                )
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

            caminhos_externos = {
                arq.caminho: arq.checksum_sha256 for arq in croqui_pb.arquivos_externos
            }
            self.assertIn("anexos/ficha.pdf", caminhos_externos)
            self.assertIn("anexos/termo.pdf", caminhos_externos)
            self.assertIn("imagens/foto.webp", caminhos_externos)

            # Checksums devem bater com o cálculo real
            self.assertEqual(
                caminhos_externos["anexos/ficha.pdf"], deploy_generated.calcular_sha256(pdf_ficha)
            )
            self.assertEqual(
                caminhos_externos["anexos/termo.pdf"], deploy_generated.calcular_sha256(pdf_termo)
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
                deploy_generated.verificar_imagens_inexistentes(
                    croqui_dir, "croqui_teste", compiled_data
                )
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn(
                "Aviso: A imagem 'imagens/mapa_inexistente.webp' referenciada no croqui 'croqui_teste'",
                saida,
            )
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
                        },
                    }
                ]
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(
                    croqui_dir, "croqui_teste", compiled_data
                )
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn(
                "Aviso: A imagem 'imagens/pedra_inexistente.webp' referenciada no croqui 'croqui_teste'",
                saida,
            )

    def test_verificar_imagens_inexistentes_avisa_thumbnail_inexistente(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            croqui_dir = Path(tmp_dir)
            compiled_data = {"caminho_thumbnail": "imagens/thumb_inexistente.webp"}
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(
                    croqui_dir, "croqui_teste", compiled_data
                )
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertIn(
                "Aviso: A imagem 'imagens/thumb_inexistente.webp' referenciada no croqui 'croqui_teste'",
                saida,
            )

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
                deploy_generated.verificar_imagens_inexistentes(
                    croqui_dir, "croqui_teste", compiled_data
                )
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
                                    "mapas": [{"caminho_imagem_mapa": "imagens/mapa_ok.webp"}],
                                }
                            }
                        ]
                    }
                ]
            }
            captured_output = StringIO()
            sys.stdout = captured_output
            try:
                deploy_generated.verificar_imagens_inexistentes(
                    croqui_dir, "croqui_teste", compiled_data
                )
            finally:
                sys.stdout = sys.__stdout__

            saida = captured_output.getvalue()
            self.assertNotIn("Aviso:", saida)

    def test_deploy_retorna_booleano_database_modificado(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            db_vazio = Path(tmp_dir) / "db_vazio"
            db_vazio.mkdir()

            # Sem croquis para compilar, deve retornar False
            resultado = deploy_generated.deploy(out_dir, database_dir=db_vazio)
            self.assertIs(resultado, False)

            # Com um croqui sem UID no croqui.yaml, o saneamento modifica o database na 1ª vez -> True
            db_dir = Path(tmp_dir) / "db"
            croqui_dir = db_dir / "br_mg_mod"
            croqui_dir.mkdir(parents=True)
            (croqui_dir / "croqui.yaml").write_text(
                "id: br_mg_mod\nnome: Mod\nultima_migracao: 5\npicos:\n  - nome: Mod\n    estado: MG\n",
                encoding="utf-8",
            )
            resultado1 = deploy_generated.deploy(out_dir, database_dir=db_dir, is_producao=False)
            self.assertIs(resultado1, True)

            # Na 2ª vez já está saneado e com cabeçalho SPDX -> False
            resultado2 = deploy_generated.deploy(out_dir, database_dir=db_dir, is_producao=False)
            self.assertIs(resultado2, False)

    def test_deploy_sem_alvos_compila_todos_os_croquis(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "out"
            db_dir = Path(tmp_dir) / "db"
            for cid in ("croqui_a", "croqui_b"):
                cdir = db_dir / cid
                cdir.mkdir(parents=True)
                (cdir / "croqui.yaml").write_text(
                    f"id: {cid}\nnome: {cid}\npublicar_croqui: true\nultima_migracao: 5\n"
                    f"picos:\n  - nome: {cid}\n    estado: MG\n",
                    encoding="utf-8",
                )

            deploy_generated.deploy(out_dir, database_dir=db_dir, target_paths=None)
            self.assertTrue((out_dir / "croqui_a" / "compilado.binarypb").is_file())
            self.assertTrue((out_dir / "croqui_b" / "compilado.binarypb").is_file())

    def test_passo_c_gerar_indice_com_croqui_uid(self):
        import tempfile

        from scripts.gerenciar_uids_lib import gerar_uid

        croqui_uid_esperado = gerar_uid()
        croqui_data = {
            "id": "croqui_com_uid",
            "uid": croqui_uid_esperado,
            "nome": "Croqui com UID",
            "publicar_croqui": True,
            "picos": [],
        }
        compilados = [("croqui_com_uid", croqui_data, Path("dummy_pb"))]
        checksums = {"croqui_com_uid": "dummy_hash"}

        with tempfile.TemporaryDirectory() as tmp_dir:
            deploy_generated.GENERATED_DIR = Path(tmp_dir)
            indice = deploy_generated.passo_c_gerar_indice(compilados, checksums, is_producao=False)

            self.assertEqual(len(indice.croquis), 1)
            resumo = indice.croquis[0]
            self.assertEqual(resumo.id, "croqui_com_uid")
            self.assertEqual(resumo.croqui_uid, croqui_uid_esperado)

            indice_yaml = Path(tmp_dir) / "indice.yaml"
            self.assertTrue(indice_yaml.is_file())
            dados_yaml = carregar_yaml(indice_yaml.read_text(encoding="utf-8"))
            self.assertEqual(dados_yaml["croquis"][0]["croqui_uid"], croqui_uid_esperado)

    def test_serving_versao_permanece_v4_com_migracoes_database_only(self):
        from serving.update_serving import get_db_version

        versao = get_db_version()
        self.assertEqual(versao, "v4")

    def test_copiar_imagens_normaliza_caminhos_e_ignora_raw_mapas(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / "imagens_src"
            dest = Path(tmp_dir) / "imagens_dest"
            src.mkdir()
            (src / "foto.webp").write_bytes(b"foto")
            raw_dir = src / "raw_mapas"
            raw_dir.mkdir()
            (raw_dir / "raw.webp").write_bytes(b"raw")

            deploy_generated.copiar_imagens(src, dest)

            self.assertTrue((dest / "foto.webp").exists())
            self.assertFalse((dest / "raw_mapas").exists())

    def test_copiar_anexos_normaliza_caminhos(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / "anexos_src"
            dest = Path(tmp_dir) / "anexos_dest"
            src.mkdir()
            (src / "documento.pdf").write_bytes(b"pdf")

            deploy_generated.copiar_anexos(src, dest)

            self.assertTrue((dest / "documento.pdf").exists())

    def test_force_rmtree_normaliza_caminho_e_remove_diretorio(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            pasta = Path(tmp_dir) / "pasta_teste"
            pasta.mkdir()
            (pasta / "arquivo.txt").write_text("conteudo")

            deploy_generated.force_rmtree(pasta)

            self.assertFalse(pasta.exists())

    def test_verificar_titulos_em_descricao_setor_grupo_avisa_se_tiver_h1(self):
        compiled_data = {
            "picos": [
                {
                    "nome": "Pico Teste",
                    "setores_ou_grupos": [
                        {
                            "setor": {
                                "nome": "Setor Bem-vindo",
                                "descricao": "# Setor Bem-vindo\n\nTexto descritivo do setor.",
                            }
                        },
                        {
                            "grupo": {
                                "nome": "Grupo Vale Oculto",
                                "descricao": "# Grupo Vale Oculto",
                                "setores": [
                                    {
                                        "nome": "Sub Setor 1",
                                        "descricao": "# Sub Setor 1\n\nOutro texto.",
                                    }
                                ],
                            }
                        },
                    ],
                }
            ]
        }
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            deploy_generated.verificar_titulos_em_descricao_setor_grupo(
                "croqui_teste", compiled_data
            )
        finally:
            sys.stdout = sys.__stdout__

        saida = captured_output.getvalue()
        self.assertIn(
            "Aviso: A descrição do setor 'Setor Bem-vindo' no croqui 'croqui_teste' contém título Markdown H1 ('# Setor Bem-vindo').",
            saida,
        )
        self.assertIn(
            "Aviso: A descrição do grupo 'Grupo Vale Oculto' no croqui 'croqui_teste' contém título Markdown H1 ('# Grupo Vale Oculto').",
            saida,
        )
        self.assertIn(
            "Aviso: A descrição do setor 'Sub Setor 1' no croqui 'croqui_teste' contém título Markdown H1 ('# Sub Setor 1').",
            saida,
        )

    def test_verificar_titulos_em_descricao_setor_grupo_sem_aviso_se_sem_h1(self):
        compiled_data = {
            "picos": [
                {
                    "nome": "Pico Teste",
                    "setores_ou_grupos": [
                        {
                            "setor": {
                                "nome": "Setor Limpo",
                                "descricao": "Texto sem título no topo.\n\n## Acesso\nSiga pela trilha.",
                            }
                        }
                    ],
                }
            ]
        }
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            deploy_generated.verificar_titulos_em_descricao_setor_grupo(
                "croqui_teste", compiled_data
            )
        finally:
            sys.stdout = sys.__stdout__

        saida = captured_output.getvalue()
        self.assertEqual(saida.strip(), "")

    def test_verificar_titulos_em_descricao_setor_grupo_ignora_sem_descricao(self):
        compiled_data = {
            "picos": [
                {
                    "nome": "Pico Teste",
                    "setores_ou_grupos": [{"setor": {"nome": "Setor Sem Descricao"}}],
                }
            ]
        }
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            deploy_generated.verificar_titulos_em_descricao_setor_grupo(
                "croqui_teste", compiled_data
            )
        finally:
            sys.stdout = sys.__stdout__

        saida = captured_output.getvalue()
        self.assertEqual(saida.strip(), "")

    def test_verificar_titulos_em_descricao_setor_grupo_estrutura_invalida(self):
        compiled_data = {
            "picos": [
                "pico_invalido",
                {
                    "nome": "Pico Valido",
                    "setores_ou_grupos": [
                        "item_invalido",
                        {"grupo": {"nome": "Grupo Sem Lista Setores", "setores": "invalido"}},
                    ],
                },
            ]
        }
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            deploy_generated.verificar_titulos_em_descricao_setor_grupo(
                "croqui_teste", compiled_data
            )
        finally:
            sys.stdout = sys.__stdout__

        saida = captured_output.getvalue()
        self.assertEqual(saida.strip(), "")

    def test_calcular_sha256_computa_digest_correto(self):
        import hashlib
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            arq = Path(tmp_dir) / "amostra.bin"
            conteudo = b"aresta climb sha256 test\n" * 500
            arq.write_bytes(conteudo)

            esperado = hashlib.sha256(conteudo).hexdigest()
            self.assertEqual(deploy_generated.calcular_sha256(arq), esperado)

    def test_sincronizacao_incremental_imagens_e_anexos_reaproveita_checksum_e_remove_orfaos(self):
        import os
        import tempfile

        from PIL import Image

        from aresta_api.proto.generated import croqui_pb2

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_dir = tmp_path / "database"
            croqui_dir = db_dir / "br_mg_sync"
            imagens_dir = croqui_dir / "imagens"
            anexos_dir = croqui_dir / "anexos"
            imagens_dir.mkdir(parents=True)
            anexos_dir.mkdir(parents=True)

            img1 = imagens_dir / "img1.webp"
            Image.new("RGB", (40, 40), color="red").save(img1, "WEBP")
            os.utime(img1, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

            anexo1 = anexos_dir / "guia.pdf"
            anexo1.write_bytes(b"%PDF-1.4 guia")
            os.utime(anexo1, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

            (croqui_dir / "croqui.yaml").write_text(
                "id: br_mg_sync\n"
                "uid: syncCroqui1234\n"
                "nome: Croqui Sync\n"
                "descricao: '[Guia](anexos/guia.pdf)'\n"
                "caminho_thumbnail: imagens/img1.webp\n"
                "publicar_croqui: true\n"
                "ultima_migracao: 5\n"
                "picos:\n"
                "  - nome: Pico Sync\n"
                "    estado: MG\n",
                encoding="utf-8",
            )

            out_dir = tmp_path / "generated"
            deploy_generated.deploy(
                out_dir,
                target_paths=[croqui_dir],
                database_dir=db_dir,
                is_producao=True,
            )

            dest_img1 = out_dir / "br_mg_sync" / "imagens" / "img1.webp"
            dest_anexo1 = out_dir / "br_mg_sync" / "anexos" / "guia.pdf"
            self.assertTrue(dest_img1.is_file())
            self.assertTrue(dest_anexo1.is_file())
            self.assertEqual(dest_img1.stat().st_mtime_ns, img1.stat().st_mtime_ns)
            self.assertEqual(dest_anexo1.stat().st_mtime_ns, anexo1.stat().st_mtime_ns)

            # Cria um arquivo órfão na pasta gerada e injeta um hash sentinela no compilado.binarypb
            # para comprovar que o segundo deploy reaproveita o hash sem reler/recomputar img1 quando stat() bate,
            # e remove o órfão sem apagar a pasta inteira.
            orfao_img = out_dir / "br_mg_sync" / "imagens" / "orfao.webp"
            orfao_img.write_bytes(b"orfao")
            orfao_anexo = out_dir / "br_mg_sync" / "anexos" / "orfao.pdf"
            orfao_anexo.write_bytes(b"orfao")

            pb_path = out_dir / "br_mg_sync" / "compilado.binarypb"
            croqui_pb = croqui_pb2.Croqui()
            croqui_pb.ParseFromString(pb_path.read_bytes())
            for ext in croqui_pb.arquivos_externos:
                if ext.caminho == "imagens/img1.webp":
                    ext.checksum_sha256 = "hash_sentinela_reaproveitado"
            pb_path.write_bytes(croqui_pb.SerializeToString())

            deploy_generated.deploy(
                out_dir,
                target_paths=[croqui_dir],
                database_dir=db_dir,
                is_producao=True,
            )

            self.assertFalse(orfao_img.exists())
            self.assertFalse(orfao_anexo.exists())

            croqui_pb_depois = croqui_pb2.Croqui()
            croqui_pb_depois.ParseFromString(pb_path.read_bytes())
            mapa_ext = {
                ext.caminho: ext.checksum_sha256 for ext in croqui_pb_depois.arquivos_externos
            }
            self.assertEqual(mapa_ext["imagens/img1.webp"], "hash_sentinela_reaproveitado")

            # Com --force (force=True), deve recalcular o SHA-256 real ignorando o sentinela
            deploy_generated.deploy(
                out_dir,
                target_paths=[croqui_dir],
                database_dir=db_dir,
                force=True,
                is_producao=True,
            )
            croqui_pb_forcado = croqui_pb2.Croqui()
            croqui_pb_forcado.ParseFromString(pb_path.read_bytes())
            mapa_ext_forcado = {
                ext.caminho: ext.checksum_sha256 for ext in croqui_pb_forcado.arquivos_externos
            }
            self.assertEqual(
                mapa_ext_forcado["imagens/img1.webp"],
                deploy_generated.calcular_sha256(img1),
            )

    def test_deploy_atualiza_dimensoes_mapa_quando_imagem_modificada_mesmo_com_dimensoes_positivas(
        self,
    ):
        import os
        import tempfile

        from PIL import Image

        from aresta_api.proto.generated import croqui_pb2

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_dir = tmp_path / "database"
            croqui_dir = db_dir / "br_mg_dim"
            (croqui_dir / "imagens").mkdir(parents=True)

            img_mapa = croqui_dir / "imagens" / "mapa_setor.webp"
            Image.new("RGB", (400, 300), color="red").save(img_mapa, "WEBP")
            os.utime(img_mapa, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

            setor_md = croqui_dir / "setor_1.md"
            setor_md.write_text(
                "---\n"
                "uid: setorDim123456\n"
                "nome: Setor Dimensões\n"
                "mapas:\n"
                "  - caminho_imagem_mapa: imagens/mapa_setor.webp\n"
                "    largura_mapa: 400\n"
                "    altura_mapa: 300\n"
                "escaladas: []\n"
                "---\n"
                "Corpo.\n",
                encoding="utf-8",
            )
            (croqui_dir / "croqui.yaml").write_text(
                "id: br_mg_dim\n"
                "uid: croquiDim12345\n"
                "nome: Croqui Dim\n"
                "caminho_thumbnail: imagens/mapa_setor.webp\n"
                "publicar_croqui: true\n"
                "ultima_migracao: 5\n"
                "picos:\n"
                "  - nome: Pico Dim\n"
                "    estado: MG\n"
                "    setores_ou_grupos:\n"
                "      - setor:\n"
                "          caminho: setor_1.md\n",
                encoding="utf-8",
            )

            out_dir = tmp_path / "generated"
            deploy_generated.deploy(
                out_dir,
                target_paths=[croqui_dir],
                database_dir=db_dir,
                is_producao=True,
            )

            pb_path = out_dir / "br_mg_dim" / "compilado.binarypb"
            croqui_pb1 = croqui_pb2.Croqui()
            croqui_pb1.ParseFromString(pb_path.read_bytes())
            mapa_pb1 = croqui_pb1.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
            self.assertEqual(mapa_pb1.largura_mapa, 400)
            self.assertEqual(mapa_pb1.altura_mapa, 300)

            # Substitui a imagem por uma de 800x600 (mudando tamanho/mtime/sha256)
            Image.new("RGB", (800, 600), color="blue").save(img_mapa, "WEBP")
            os.utime(img_mapa, ns=(1_700_000_500_000_000_000, 1_700_000_500_000_000_000))

            # Novo deploy incremental: como a imagem foi copiada, deve atualizar largura_mapa/altura_mapa para 800x600
            deploy_generated.deploy(
                out_dir,
                target_paths=[croqui_dir],
                database_dir=db_dir,
                is_producao=True,
            )

            croqui_pb2_msg = croqui_pb2.Croqui()
            croqui_pb2_msg.ParseFromString(pb_path.read_bytes())
            mapa_pb2 = croqui_pb2_msg.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
            self.assertEqual(mapa_pb2.largura_mapa, 800)
            self.assertEqual(mapa_pb2.altura_mapa, 600)

            # Terceiro deploy incremental (agora a imagem não mudou mais entre database e generated):
            # deve continuar com 800x600 porque setor_1.md também teve suas dimensões atualizadas!
            deploy_generated.deploy(
                out_dir,
                target_paths=[croqui_dir],
                database_dir=db_dir,
                is_producao=True,
            )
            croqui_pb3_msg = croqui_pb2.Croqui()
            croqui_pb3_msg.ParseFromString(pb_path.read_bytes())
            mapa_pb3 = croqui_pb3_msg.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
            self.assertEqual(mapa_pb3.largura_mapa, 800)
            self.assertEqual(mapa_pb3.altura_mapa, 600)

    def test_processar_thumbnail_incremental_sincroniza_mtime_e_pula_quando_inalterada(self):
        import os
        import tempfile

        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            croqui_dir = tmp_path / "croqui_thumb"
            (croqui_dir / "imagens").mkdir(parents=True)
            src_img = croqui_dir / "imagens" / "capa.webp"
            Image.new("RGB", (200, 200), color="green").save(src_img, "WEBP")
            os.utime(src_img, ns=(1_650_000_000_000_000_000, 1_650_000_000_000_000_000))

            generated_dir = tmp_path / "generated"
            deploy_generated.GENERATED_DIR = generated_dir
            croqui_data = {"id": "croqui_thumb", "caminho_thumbnail": "imagens/capa.webp"}

            # 1ª execução gera a thumbnail e sincroniza st_mtime_ns com a origem
            gerou1 = deploy_generated.processar_thumbnail(
                croqui_dir, generated_dir, croqui_data, force_thumbnails=False
            )
            self.assertTrue(gerou1)
            dest_thumb = generated_dir / "thumbnails" / "croqui_thumb.webp"
            self.assertTrue(dest_thumb.is_file())
            self.assertEqual(dest_thumb.stat().st_mtime_ns, src_img.stat().st_mtime_ns)

            # 2ª execução com mesmo mtime pula geração
            gerou2 = deploy_generated.processar_thumbnail(
                croqui_dir, generated_dir, croqui_data, force_thumbnails=False
            )
            self.assertFalse(gerou2)

            # Alterando mtime da imagem de origem, regenera automaticamente mesmo com force_thumbnails=False
            os.utime(src_img, ns=(1_660_000_000_000_000_000, 1_660_000_000_000_000_000))
            gerou3 = deploy_generated.processar_thumbnail(
                croqui_dir, generated_dir, croqui_data, force_thumbnails=False
            )
            self.assertTrue(gerou3)
            self.assertEqual(dest_thumb.stat().st_mtime_ns, src_img.stat().st_mtime_ns)

    def test_deploy_target_isola_carregamento_e_atualiza_manifesto_serving_incrementalmente(self):
        import tempfile

        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_dir = tmp_path / "database"
            out_dir = tmp_path / "generated"

            # Cria dois croquis válidos e faz deploy inicial completo
            for cid in ("croqui_1", "croqui_2"):
                cdir = db_dir / cid
                (cdir / "imagens").mkdir(parents=True)
                Image.new("RGB", (30, 30), color="purple").save(
                    cdir / "imagens" / f"{cid}.webp", "WEBP"
                )
                (cdir / "croqui.yaml").write_text(
                    f"id: {cid}\nnome: {cid}\npublicar_croqui: true\n"
                    f"caminho_thumbnail: imagens/{cid}.webp\nultima_migracao: 5\n"
                    f"picos:\n  - nome: {cid}\n    estado: MG\n",
                    encoding="utf-8",
                )

            deploy_generated.deploy(out_dir, database_dir=db_dir, is_producao=True)

            # Corrompe o croqui.yaml de croqui_2 no database e remove seu compilado.binarypb? Não, mantém compilado.binarypb
            # em generated/croqui_2 mas corrompe database/croqui_2/croqui.yaml para provar que --target croqui_1
            # NÃO lê database/croqui_2/croqui.yaml!
            (db_dir / "croqui_2" / "croqui.yaml").write_text(
                "yaml: [invalido: sem fechar", encoding="utf-8"
            )

            # Executa deploy incremental apenas de croqui_1
            deploy_generated.deploy(
                out_dir,
                target_paths=[db_dir / "croqui_1"],
                database_dir=db_dir,
                is_producao=True,
            )

            manifesto = carregar_yaml(
                (out_dir / "arquivos_serving.yaml").read_text(encoding="utf-8")
            )
            caminhos = {arq["caminho_relativo"] for arq in manifesto.get("arquivos", [])}
            self.assertIn("croqui_1/compilado.binarypb", caminhos)
            self.assertIn("croqui_1/imagens/croqui_1.webp", caminhos)
            self.assertIn("croqui_2/compilado.binarypb", caminhos)
            self.assertIn("croqui_2/imagens/croqui_2.webp", caminhos)

    def test_sincronizar_arquivo_individual_mtime_alterado_mesmo_conteudo_vs_conteudo_diferente(
        self,
    ):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src = tmp_path / "src.webp"
            dest = tmp_path / "dest.webp"
            src.write_bytes(b"conteudo_original")
            os.utime(src, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

            hash_orig = deploy_generated._sincronizar_arquivo_individual(
                src, dest, "imagens/src.webp", {}, force=False
            )
            self.assertEqual(dest.stat().st_mtime_ns, src.stat().st_mtime_ns)

            # Muda mtime da origem mantendo mesmo conteúdo -> atualiza mtime do destino sem mudar hash e registra como inalterado
            os.utime(src, ns=(1_700_000_100_000_000_000, 1_700_000_100_000_000_000))
            inalterados_mesmo: set[str] = set()
            hash_mesmo = deploy_generated._sincronizar_arquivo_individual(
                src,
                dest,
                "imagens/src.webp",
                {"imagens/src.webp": hash_orig},
                force=False,
                arquivos_inalterados_out=inalterados_mesmo,
            )
            self.assertEqual(hash_mesmo, hash_orig)
            self.assertEqual(dest.stat().st_mtime_ns, src.stat().st_mtime_ns)
            self.assertIn("imagens/src.webp", inalterados_mesmo)

            # Muda conteúdo da origem mantendo mesmo tamanho -> recalcula SHA-256, copia novo conteúdo e NÃO registra como inalterado
            src.write_bytes(b"conteudo_alterado")
            os.utime(src, ns=(1_700_000_200_000_000_000, 1_700_000_200_000_000_000))
            inalterados_novo: set[str] = set()
            hash_novo = deploy_generated._sincronizar_arquivo_individual(
                src,
                dest,
                "imagens/src.webp",
                {"imagens/src.webp": hash_orig},
                force=False,
                arquivos_inalterados_out=inalterados_novo,
            )
            self.assertNotEqual(hash_novo, hash_orig)
            self.assertEqual(dest.read_bytes(), b"conteudo_alterado")
            self.assertNotIn("imagens/src.webp", inalterados_novo)

    def test_validar_sem_extensoes_vazadas_em_memoria_detecta_croqui_e_markdown(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            pico_dir = Path(tmp_dir)
            with self.assertRaises(ValueError) as ctx_yaml:
                deploy_generated.validar_sem_extensoes_vazadas(
                    pico_dir,
                    dados_croqui_memoria={"id": "c1", "ext_metadados": {"x": 1}},
                    cache_md_memoria={},
                )
            self.assertIn("croqui.yaml", str(ctx_yaml.exception))

            with self.assertRaises(ValueError) as ctx_md:
                deploy_generated.validar_sem_extensoes_vazadas(
                    pico_dir,
                    dados_croqui_memoria={"id": "c1"},
                    cache_md_memoria={"setor.md": ({"ext_metadados": {"x": 1}}, "corpo")},
                )
            self.assertIn("setor.md", str(ctx_md.exception))

    def test_atualizar_saude_croquis_e_create_parser(self):
        import tempfile

        parser = deploy_generated.create_parser()
        args = parser.parse_args(["--target", "database/meu_croqui", "--force"])
        self.assertEqual(args.target, ["database/meu_croqui"])
        self.assertTrue(args.force)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_dir = tmp_path / "database"
            cdir = db_dir / "croqui_saude"
            cdir.mkdir(parents=True)
            dados_croqui = {
                "id": "croqui_saude",
                "nome": "Croqui Saude",
                "publicar_croqui": True,
                "picos": [{"nome": "Pico Saude", "estado": "MG", "setores_ou_grupos": []}],
            }
            (cdir / "croqui.yaml").write_text(
                serializar_yaml(dados_croqui, incluir_cabecalho_spdx=True),
                encoding="utf-8",
            )
            out_md = tmp_path / "STATUS_CROQUIS.md"
            ok = deploy_generated.atualizar_saude_croquis(
                alvos=["croqui_saude"],
                base_path=db_dir,
                output_path=out_md,
                dados_em_memoria={"croqui_saude": (dados_croqui, {})},
            )
            self.assertTrue(ok)
            self.assertTrue(out_md.is_file())
            self.assertIn("croqui_saude", out_md.read_text(encoding="utf-8"))

    def test_deploy_com_contexto_memoria_processa_em_ram_e_persiste_uma_vez(self):
        import tempfile

        from scripts.gerenciar_uids_lib import gerar_uid
        from scripts.migrador import obter_ultima_versao_migracao

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            db_dir = tmp_path / "database"
            cdir = db_dir / "croqui_ram"
            cdir.mkdir(parents=True)
            out_dir = tmp_path / "generated"

            # Nenhum croqui.yaml ou setor_ram.md existe no disco antes do deploy!
            dados_croqui = {
                "uid": gerar_uid(),
                "id": "croqui_ram",
                "nome": "Croqui RAM",
                "ultima_migracao": obter_ultima_versao_migracao(),
                "publicar_croqui": True,
                "botoes": [
                    {
                        "uid": gerar_uid(),
                        "texto": "Sobre",
                        "destino": {"secao_textual": {"caminho": "secao_sobre.md"}},
                    }
                ],
                "picos": [
                    {
                        "nome": "Pico RAM",
                        "estado": "MG",
                        "setores_ou_grupos": [{"setor": {"caminho": "setor_ram.md"}}],
                    }
                ],
            }
            cache_md = {
                "setor_ram.md": (
                    {
                        "uid": gerar_uid(),
                        "nome": "Setor RAM",
                        "escaladas": [
                            {
                                "uid": gerar_uid(),
                                "via_esportiva": {"nome": "Via RAM"},
                            }
                        ],
                    },
                    "Descrição do setor RAM",
                ),
                "secao_sobre.md": (None, "Texto da seção sobre"),
            }
            corpos_brutos = {
                "setor_ram.md": "Descrição do setor RAM\n",
                "secao_sobre.md": "Texto da seção sobre\n",
            }

            with deploy_generated.usar_contexto_memoria_deploy(
                [cdir],
                dados_croqui,
                cache_md=cache_md,
                corpos_brutos_md=corpos_brutos,
            ) as ctx:
                modificado = deploy_generated.deploy(
                    out_dir,
                    target_paths=[cdir],
                    database_dir=db_dir,
                    is_producao=False,
                )
                self.assertFalse(modificado)
                self.assertTrue(ctx.persistido_no_disco)

            # Após o deploy, croqui.yaml, setor_ram.md e secao_sobre.md foram persistidos uma única vez
            self.assertTrue((cdir / "croqui.yaml").is_file())
            self.assertTrue((cdir / "setor_ram.md").is_file())
            self.assertTrue((cdir / "secao_sobre.md").is_file())
            self.assertTrue((out_dir / "croqui_ram" / "compilado.binarypb").is_file())
            self.assertTrue(
                (cdir / "setor_ram.md")
                .read_text(encoding="utf-8")
                .endswith("---\nDescrição do setor RAM\n")
            )
            self.assertEqual(
                (cdir / "secao_sobre.md").read_text(encoding="utf-8"),
                "Texto da seção sobre\n",
            )

            # Caso 2: mutação de corpo/dimensões em RAM e fallback sem corpos_brutos
            from PIL import Image

            (cdir / "imagens").mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (60, 40), color="green").save(
                cdir / "imagens" / "mapa.webp", "WEBP"
            )
            cache_md_mutado = {
                "setor_ram.md": (
                    {
                        "uid": gerar_uid(),
                        "nome": "Setor RAM",
                        "descricao": "Extra movido",
                        "mapas": [
                            {
                                "caminho_imagem_mapa": "imagens/mapa.webp",
                                "largura_mapa": 10,
                                "altura_mapa": 10,
                                "pontos_de_interesse": [],
                                "referencias": [],
                            }
                        ],
                    },
                    "Corpo base",
                ),
                "secao_sobre.md": (None, "Corpo alterado"),
            }
            with deploy_generated.usar_contexto_memoria_deploy(
                [cdir],
                dados_croqui,
                cache_md=cache_md_mutado,
                corpos_brutos_md={"secao_sobre.md": "Corpo antigo diferente"},
            ) as ctx2:
                modificado2 = deploy_generated.deploy(
                    out_dir,
                    target_paths=[cdir],
                    database_dir=db_dir,
                    is_producao=False,
                )
                self.assertTrue(modificado2)
                self.assertTrue(ctx2.persistido_no_disco)

            # Caso 3: erro em corrigir_database com contexto em memória ainda persiste arquivos no disco
            cdir_erro = db_dir / "croqui_erro_ram"
            cdir_erro.mkdir(parents=True)
            dados_erro = {
                "uid": "uid_invalido",
                "id": "croqui_erro_ram",
                "nome": "Croqui Erro",
                "ultima_migracao": obter_ultima_versao_migracao(),
                "caminho_thumbnail": "imagens/inexistente.webp",
                "picos": [],
            }
            with deploy_generated.usar_contexto_memoria_deploy(
                [cdir_erro],
                dados_erro,
            ) as ctx_erro:
                with self.assertRaises(RuntimeError):
                    deploy_generated.deploy(
                        out_dir,
                        target_paths=[cdir_erro],
                        database_dir=db_dir,
                        is_producao=False,
                    )
                self.assertTrue(ctx_erro.persistido_no_disco)
                self.assertTrue((cdir_erro / "croqui.yaml").is_file())

    def test_persistir_contexto_memoria_no_disco_usa_snapshot_para_evitar_reserializacao(
        self,
    ) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            cdir = Path(tmp) / "croqui_snap"
            cdir.mkdir(parents=True)
            dados_croqui = {
                "uid": "00000000-0000-4000-8000-000000000001",
                "id": "croqui_snap",
                "nome": "Croqui Snap",
                "picos": [{"uid": "00000000-0000-4000-8000-000000000002", "nome": "Pico A"}],
            }
            fm_setor_a = {
                "uid": "00000000-0000-4000-8000-000000000003",
                "nome": "Setor A",
                "escaladas": [{"uid": "00000000-0000-4000-8000-000000000004", "nome": "Via 1"}],
            }
            fm_setor_b = {
                "uid": "00000000-0000-4000-8000-000000000005",
                "nome": "Setor B",
                "escaladas": [],
            }
            ctx1 = deploy_generated.ContextoMemoriaDeploy(
                croqui_data=dados_croqui,
                cache_md={
                    "setor_a.md": (fm_setor_a, "Corpo A"),
                    "setor_b.md": (fm_setor_b, "Corpo B"),
                },
                corpos_brutos_md={
                    "setor_a.md": "\nCorpo A\n",
                    "setor_b.md": "\nCorpo B\n",
                },
            )

            # Antes de persistir, o snapshot não existe
            self.assertFalse(
                deploy_generated._arquivo_inalterado_no_snapshot(
                    cdir / "croqui.yaml", dados_croqui, None
                )
            )

            deploy_generated.persistir_contexto_memoria_no_disco(cdir, ctx1)

            # Agora os snapshots de croqui.yaml, setor_a.md e setor_b.md devem acusar inalterado
            self.assertTrue(
                deploy_generated._arquivo_inalterado_no_snapshot(
                    cdir / "croqui.yaml", dados_croqui, None
                )
            )
            self.assertTrue(
                deploy_generated._arquivo_inalterado_no_snapshot(
                    cdir / "setor_a.md", fm_setor_a, "\nCorpo A\n"
                )
            )

            # Mudança de ordem de chaves, tipo ou lista deve invalidar a comparação estrutural
            self.assertFalse(
                deploy_generated._estruturas_identicas_com_ordem(
                    {"nome": "Setor A", "uid": "00000000-0000-4000-8000-000000000003"},
                    {"uid": "00000000-0000-4000-8000-000000000003", "nome": "Setor A"},
                )
            )
            self.assertFalse(
                deploy_generated._estruturas_identicas_com_ordem(
                    fm_setor_a, "nao_eh_dict"
                )
            )
            self.assertFalse(
                deploy_generated._estruturas_identicas_com_ordem(
                    [1, 2], [1, 3]
                )
            )

            # Segunda persistência: setor_a e croqui.yaml inalterados, setor_b modificado
            fm_setor_b_mod = {
                "uid": "00000000-0000-4000-8000-000000000005",
                "nome": "Setor B Modificado",
                "escaladas": [],
            }
            ctx2 = deploy_generated.ContextoMemoriaDeploy(
                croqui_data=dados_croqui,
                cache_md={
                    "setor_a.md": (fm_setor_a, "Corpo A"),
                    "setor_b.md": (fm_setor_b_mod, "Corpo B"),
                },
                corpos_brutos_md={
                    "setor_a.md": "\nCorpo A\n",
                    "setor_b.md": "\nCorpo B\n",
                },
            )
            deploy_generated.persistir_contexto_memoria_no_disco(cdir, ctx2)
            self.assertIn(
                "Setor B Modificado",
                (cdir / "setor_b.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()

