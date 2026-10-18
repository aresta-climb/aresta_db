# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from aresta_api.proto.generated import beta_pb2
from scripts import medir_saude_croquis


class TestMedirSaudeCroquis(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_check_arquivos_e_pastas_basicas(self) -> None:
        croqui_dir = self.tmp_path / "croqui_basico"
        croqui_dir.mkdir()

        # Ausentes inicialmente
        self.assertFalse(medir_saude_croquis.check_partes_json(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_raw_original_pdf(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_raw_pdf_contents(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_croqui_yaml(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_mapas_gerais_exists(croqui_dir))

        # partes.json vazio ou inválido vs válido
        (croqui_dir / "partes.json").write_text("{}", encoding="utf-8")
        self.assertFalse(medir_saude_croquis.check_partes_json(croqui_dir))
        (croqui_dir / "partes.json").write_text("{invalido", encoding="utf-8")
        self.assertFalse(medir_saude_croquis.check_partes_json(croqui_dir))
        (croqui_dir / "partes.json").write_text('{"partes": [1]}', encoding="utf-8")
        self.assertTrue(medir_saude_croquis.check_partes_json(croqui_dir))

        # Pastas raw vazias vs preenchidas
        (croqui_dir / "raw_original_pdf").mkdir()
        (croqui_dir / "raw_pdf_contents").mkdir()
        self.assertFalse(medir_saude_croquis.check_raw_original_pdf(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_raw_pdf_contents(croqui_dir))
        (croqui_dir / "raw_original_pdf" / "doc.pdf").write_bytes(b"%PDF")
        (croqui_dir / "raw_pdf_contents" / "page1.txt").write_text("conteudo", encoding="utf-8")
        self.assertTrue(medir_saude_croquis.check_raw_original_pdf(croqui_dir))
        self.assertTrue(medir_saude_croquis.check_raw_pdf_contents(croqui_dir))

        # croqui.yaml e mapas_gerais.md
        (croqui_dir / "croqui.yaml").write_text("id: basico\n", encoding="utf-8")
        (croqui_dir / "mapas_gerais.md").write_text("---\n---\n", encoding="utf-8")
        self.assertTrue(medir_saude_croquis.check_croqui_yaml(croqui_dir))
        self.assertTrue(medir_saude_croquis.check_mapas_gerais_exists(croqui_dir))
        self.assertTrue(
            medir_saude_croquis.check_mapas_gerais_exists(
                self.tmp_path / "inexistente",
                cache_md={"mapas_gerais.md": ({}, "")},
            )
        )

    def test_checks_campos_booleanos_e_thumbnail_do_croqui_yaml(self) -> None:
        croqui_dir = self.tmp_path / "croqui_campos"
        croqui_dir.mkdir()

        # Sem croqui.yaml
        self.assertFalse(medir_saude_croquis.check_publicar_croqui(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_revisado_manualmente(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_revisado_bounding_circle(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_caminho_thumbnail(croqui_dir))

        # Com croqui.yaml preenchido
        (croqui_dir / "croqui.yaml").write_text(
            "publicar_croqui: true\n"
            "revisado_manualmente: true\n"
            "revisado_bounding_circle: true\n"
            "caminho_thumbnail: imagens/capa.webp\n",
            encoding="utf-8",
        )
        self.assertTrue(medir_saude_croquis.check_publicar_croqui(croqui_dir))
        self.assertTrue(medir_saude_croquis.check_revisado_manualmente(croqui_dir))
        self.assertTrue(medir_saude_croquis.check_revisado_bounding_circle(croqui_dir))
        self.assertTrue(medir_saude_croquis.check_caminho_thumbnail(croqui_dir))

        # Com croqui.yaml falso/vazio
        (croqui_dir / "croqui.yaml").write_text(
            "publicar_croqui: false\nrevisado_manualmente: false\n",
            encoding="utf-8",
        )
        self.assertFalse(medir_saude_croquis.check_publicar_croqui(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_revisado_manualmente(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_revisado_bounding_circle(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_caminho_thumbnail(croqui_dir))

        # Com YAML inválido no disco
        (croqui_dir / "croqui.yaml").write_text("yaml: [invalido", encoding="utf-8")
        self.assertFalse(medir_saude_croquis.check_publicar_croqui(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_revisado_manualmente(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_revisado_bounding_circle(croqui_dir))
        self.assertFalse(medir_saude_croquis.check_caminho_thumbnail(croqui_dir))

    def test_check_status_desenho_extraivel(self) -> None:
        croqui_dir = self.tmp_path / "croqui_desenho"
        croqui_dir.mkdir()

        self.assertEqual(medir_saude_croquis.check_status_desenho_extraivel(croqui_dir), "❌")

        casos = [
            ("NAO_TEM_DESENHO", "✅ (não)"),
            ("TEM_DESENHO_MAS_NAO_EXTRAIDO", "⚠️"),
            ("DESENHO_EXTRAIDO", "✅"),
            ("OUTRO", "❌"),
            (None, "❌"),
        ]
        for valor, esperado in casos:
            conteudo = f"status_desenho_extraivel: {valor}\n" if valor else "{}\n"
            (croqui_dir / "croqui.yaml").write_text(conteudo, encoding="utf-8")
            self.assertEqual(
                medir_saude_croquis.check_status_desenho_extraivel(croqui_dir),
                esperado,
            )

        (croqui_dir / "croqui.yaml").write_text("yaml: [invalido", encoding="utf-8")
        self.assertEqual(medir_saude_croquis.check_status_desenho_extraivel(croqui_dir), "❌")

    def test_check_pico_coordinates_e_url_google_maps(self) -> None:
        croqui_dir = self.tmp_path / "croqui_coords"
        croqui_dir.mkdir()

        # Sem YAML -> N/A
        self.assertEqual(medir_saude_croquis.check_pico_coordinates(croqui_dir), "N/A")
        self.assertEqual(medir_saude_croquis.checar_url_google_maps(croqui_dir), "N/A")

        # Sem picos -> N/A
        (croqui_dir / "croqui.yaml").write_text("nome: Sem Picos\n", encoding="utf-8")
        self.assertEqual(medir_saude_croquis.check_pico_coordinates(croqui_dir), "N/A")
        self.assertEqual(medir_saude_croquis.checar_url_google_maps(croqui_dir), "N/A")

        # Todos os picos preenchidos -> ✅ (1/1)
        (croqui_dir / "croqui.yaml").write_text(
            "picos:\n"
            "  - nome: Pico 1\n"
            "    localizacao:\n"
            "      latitude: -201234567\n"
            "      longitude: -431234567\n"
            "    url_google_maps: https://maps.app.goo.gl/abc\n",
            encoding="utf-8",
        )
        self.assertEqual(medir_saude_croquis.check_pico_coordinates(croqui_dir), "✅ (1/1)")
        self.assertEqual(medir_saude_croquis.checar_url_google_maps(croqui_dir), "✅ (1/1)")
        self.assertEqual(medir_saude_croquis.check_url_google_maps(croqui_dir), "✅ (1/1)")

        # Parcial -> ⚠️ (1/2)
        (croqui_dir / "croqui.yaml").write_text(
            "picos:\n"
            "  - nome: Pico 1\n"
            "    localizacao:\n"
            "      latitude: -201234567\n"
            "      longitude: -431234567\n"
            "    url_google_maps: https://maps.app.goo.gl/abc\n"
            "  - nome: Pico 2\n"
            "    url_google_maps: ''\n",
            encoding="utf-8",
        )
        self.assertEqual(medir_saude_croquis.check_pico_coordinates(croqui_dir), "⚠️ (1/2)")
        self.assertEqual(medir_saude_croquis.checar_url_google_maps(croqui_dir), "⚠️ (1/2)")

        # Nenhum preenchido -> ❌ (0/1)
        (croqui_dir / "croqui.yaml").write_text(
            "picos:\n  - nome: Pico 1\n",
            encoding="utf-8",
        )
        self.assertEqual(medir_saude_croquis.check_pico_coordinates(croqui_dir), "❌ (0/1)")
        self.assertEqual(medir_saude_croquis.checar_url_google_maps(croqui_dir), "❌ (0/1)")

        # YAML corrompido -> ❌ (Erro)
        (croqui_dir / "croqui.yaml").write_text("yaml: [invalido", encoding="utf-8")
        self.assertEqual(medir_saude_croquis.check_pico_coordinates(croqui_dir), "❌ (Erro)")
        self.assertEqual(medir_saude_croquis.checar_url_google_maps(croqui_dir), "❌ (Erro)")

    def test_find_all_sectors_e_check_pontos_de_interesse(self) -> None:
        croqui_dir = self.tmp_path / "croqui_setores"
        croqui_dir.mkdir()

        # Sem setores -> N/A
        self.assertEqual(medir_saude_croquis.check_pontos_de_interesse(croqui_dir), "N/A")

        # Setores via grupo, string direta, caminho e conteudo inline
        (croqui_dir / "grupo_1.md").write_text(
            "---\nnome: Grupo 1\nsetores:\n  - caminho: setor_1.md\n---\n",
            encoding="utf-8",
        )
        (croqui_dir / "setor_1.md").write_text(
            "---\n"
            "nome: Setor 1\n"
            "mapas:\n"
            "  - caminho_imagem: imagens/m1.webp\n"
            "    pontos_de_interesse:\n"
            "      - id: '1'\n"
            "        tipo: ESCALADA\n"
            "---\n",
            encoding="utf-8",
        )
        (croqui_dir / "setor_2.md").write_text(
            "---\n"
            "nome: Setor 2\n"
            "mapas:\n"
            "  - caminho_imagem: imagens/m2.webp\n"
            "    pontos_de_interesse: []\n"
            "---\n",
            encoding="utf-8",
        )
        (croqui_dir / "croqui.yaml").write_text(
            "picos:\n"
            "  - nome: Pico 1\n"
            "    setores_ou_grupos:\n"
            "      - grupo:\n"
            "          caminho: grupo_1.md\n"
            "      - setor: setor_2.md\n"
            "      - grupo:\n"
            "          conteudo:\n"
            "            sub_setores:\n"
            "              - setor_1.md\n",
            encoding="utf-8",
        )
        setores = medir_saude_croquis.find_all_sectors(croqui_dir)
        self.assertEqual(
            [p.name for p in setores],
            ["grupo_1.md", "setor_1.md", "setor_2.md"],
        )
        # Apenas setor_1 tem pontos_de_interesse -> ⚠️ (1/3)
        self.assertEqual(medir_saude_croquis.check_pontos_de_interesse(croqui_dir), "⚠️ (1/3)")

        # Quando todos os arquivos referenciados têm pontos -> ✅ (1/1)
        (croqui_dir / "croqui.yaml").write_text(
            "picos:\n"
            "  - nome: Pico 1\n"
            "    setores_ou_grupos:\n"
            "      - setor:\n"
            "          caminho: setor_1.md\n",
            encoding="utf-8",
        )
        self.assertEqual(medir_saude_croquis.check_pontos_de_interesse(croqui_dir), "✅ (1/1)")

        # Quando nenhum tem pontos -> ❌ (0/1)
        (croqui_dir / "croqui.yaml").write_text(
            "picos:\n"
            "  - nome: Pico 1\n"
            "    setores_ou_grupos:\n"
            "      - setor:\n"
            "          caminho: setor_2.md\n",
            encoding="utf-8",
        )
        self.assertEqual(medir_saude_croquis.check_pontos_de_interesse(croqui_dir), "❌ (0/1)")

        # Fallback por glob quando croqui.yaml não existe ou está corrompido
        (croqui_dir / "croqui.yaml").unlink()
        setores_glob = medir_saude_croquis.find_all_sectors(croqui_dir)
        self.assertEqual([p.name for p in setores_glob], ["setor_1.md", "setor_2.md"])

    def test_check_betas_pendentes_real_protobuf(self) -> None:
        croqui_dir = self.tmp_path / "croqui_betas"
        croqui_dir.mkdir()

        # Sem arquivo -> ✅
        self.assertEqual(medir_saude_croquis.check_betas_pendentes(croqui_dir), "✅")

        # Com arquivo contendo 2 candidatos pendentes -> ⚠️ (2)
        staging = beta_pb2.BetasPendentes()
        esc = staging.candidatos_por_escalada.add()
        esc.candidatos.add()
        esc.candidatos.add()
        (croqui_dir / "betas_pendentes.binarypb").write_bytes(staging.SerializeToString())

        self.assertEqual(medir_saude_croquis.check_betas_pendentes(croqui_dir), "⚠️ (2)")

        # Com arquivo vazio (0 candidatos) -> ⚠️
        staging_vazio = beta_pb2.BetasPendentes()
        (croqui_dir / "betas_pendentes.binarypb").write_bytes(staging_vazio.SerializeToString())
        self.assertEqual(medir_saude_croquis.check_betas_pendentes(croqui_dir), "⚠️")

    def test_avaliar_saude_croqui_em_memoria_sem_reler_disco(self) -> None:
        croqui_dir = self.tmp_path / "croqui_memoria"
        croqui_dir.mkdir()
        (croqui_dir / "partes.json").write_text('{"ok": true}', encoding="utf-8")
        (croqui_dir / "raw_original_pdf").mkdir()
        (croqui_dir / "raw_original_pdf" / "a.pdf").write_bytes(b"pdf")
        (croqui_dir / "raw_pdf_contents").mkdir()
        (croqui_dir / "raw_pdf_contents" / "a.txt").write_text("txt", encoding="utf-8")

        # Corrompe croqui.yaml e setor_1.md no disco para provar que avaliar_saude_croqui
        # utiliza os dados em memória sem reler do disco
        (croqui_dir / "croqui.yaml").write_text("yaml: [corrompido", encoding="utf-8")
        (croqui_dir / "setor_1.md").write_text("---\nyaml: [corrompido\n---\n", encoding="utf-8")

        dados_yaml_memoria = {
            "id": "croqui_memoria",
            "publicar_croqui": True,
            "revisado_manualmente": True,
            "revisado_bounding_circle": False,
            "status_desenho_extraivel": "DESENHO_EXTRAIDO",
            "caminho_thumbnail": "imagens/thumb.webp",
            "picos": [
                {
                    "nome": "Pico Memória",
                    "localizacao": {"latitude": -210000000, "longitude": -440000000},
                    "url_google_maps": "https://maps.app.goo.gl/xyz",
                    "setores_ou_grupos": [{"setor": {"caminho": "setor_1.md"}}],
                }
            ],
        }
        cache_md_memoria = {
            "setor_1.md": (
                {
                    "nome": "Setor 1",
                    "mapas": [
                        {
                            "caminho_imagem": "imagens/m.webp",
                            "pontos_de_interesse": [{"id": "1", "tipo": "ESCALADA"}],
                        }
                    ],
                },
                "Corpo do setor",
            ),
            "mapas_gerais.md": ({"mapas": []}, ""),
        }

        linha = medir_saude_croquis.avaliar_saude_croqui(
            croqui_dir,
            dados_yaml=dados_yaml_memoria,
            cache_md=cache_md_memoria,
        )

        self.assertEqual(linha["Nome"], "croqui_memoria")
        self.assertEqual(linha["Publicado"], "✅")
        self.assertEqual(linha["Revisado Manual"], "✅")
        self.assertEqual(linha["Revisado Circ"], "❌")
        self.assertEqual(linha["Status Desenho"], "✅")
        self.assertEqual(linha["Pontos de Interesse"], "✅ (1/1)")
        self.assertEqual(linha["Thumbnail"], "✅")
        self.assertEqual(linha["Coordenadas Picos"], "✅ (1/1)")
        self.assertEqual(linha["URL Google Maps"], "✅ (1/1)")
        self.assertEqual(linha["Mapas Gerais"], "✅")
        self.assertEqual(linha["Betas Pendentes"], "✅")
        self.assertEqual(linha["croqui.yaml"], "✅")
        self.assertEqual(linha["Conteúdo PDF"], "✅")
        self.assertEqual(linha["partes.json"], "✅")
        self.assertEqual(linha["PDF Original"], "✅")

    def test_atualizar_relatorio_saude_croquis_incremental_atualiza_apenas_alvo_e_cabecalho(
        self,
    ) -> None:
        base_dir = self.tmp_path / "database"
        output_file = self.tmp_path / "STATUS_CROQUIS.md"

        for cid, publicado in (("croqui_a", False), ("croqui_b", True)):
            cdir = base_dir / cid
            cdir.mkdir(parents=True)
            (cdir / "croqui.yaml").write_text(
                f"id: {cid}\npublicar_croqui: {'true' if publicado else 'false'}\n"
                "status_desenho_extraivel: NAO_TEM_DESENHO\n",
                encoding="utf-8",
            )

        t1 = datetime(2026, 4, 10, 12, 0, 0)
        modificou_inicial = medir_saude_croquis.atualizar_relatorio_saude_croquis(
            base_path=base_dir,
            output_path=output_file,
            agora=t1,
        )
        self.assertTrue(modificou_inicial)
        texto_inicial = output_file.read_text(encoding="utf-8")
        self.assertIn("Publicado (1/2)", texto_inicial)
        self.assertIn("| croqui_a | ❌ |", texto_inicial)
        self.assertIn("| croqui_b | ✅ |", texto_inicial)

        # Corrompe croqui_b no disco para provar que a atualização incremental de croqui_a
        # NÃO lê os arquivos de croqui_b do disco
        (base_dir / "croqui_b" / "croqui.yaml").write_text("yaml: [corrompido", encoding="utf-8")

        # Atualiza croqui_a usando dados em memória (publicar_croqui passa a ser True)
        t2 = datetime(2026, 4, 10, 12, 5, 0)
        modificou_inc = medir_saude_croquis.atualizar_relatorio_saude_croquis(
            base_path=base_dir,
            output_path=output_file,
            alvos=[base_dir / "croqui_a"],
            dados_em_memoria={
                "croqui_a": (
                    {
                        "id": "croqui_a",
                        "publicar_croqui": True,
                        "status_desenho_extraivel": "DESENHO_EXTRAIDO",
                    },
                    {},
                )
            },
            agora=t2,
        )
        self.assertTrue(modificou_inc)
        texto_inc = output_file.read_text(encoding="utf-8")
        # O cabeçalho deve refletir 2/2 publicados e 2/0/0 em Desenho Extraível!
        self.assertIn("Publicado (2/2)", texto_inc)
        self.assertIn("Desenho Extraível (2/0/0)", texto_inc)
        self.assertIn("| croqui_a | ✅ |", texto_inc)
        self.assertIn("| croqui_b | ✅ |", texto_inc)

        # Se rodar novamente sem mudanças, retorna False e preserva o arquivo
        modificou_repetido = medir_saude_croquis.atualizar_relatorio_saude_croquis(
            base_path=base_dir,
            output_path=output_file,
            alvos=["croqui_a"],
            dados_em_memoria={
                "croqui_a": (
                    {
                        "id": "croqui_a",
                        "publicar_croqui": True,
                        "status_desenho_extraivel": "DESENHO_EXTRAIDO",
                    },
                    {},
                )
            },
        )
        self.assertFalse(modificou_repetido)

    def test_salvar_relatorio_saude_se_modificado_preserva_timestamp_e_escreve_lf(self) -> None:
        arq = self.tmp_path / "STATUS_CROQUIS.md"
        tabela_1 = "| Croqui | Publicado |\n| --- | --- |\n| croqui_a | ✅ |"
        t1 = datetime(2026, 1, 1, 10, 0, 0)
        t2 = datetime(2026, 1, 2, 15, 30, 0)

        modificado = medir_saude_croquis.salvar_relatorio_saude_se_modificado(
            arq, tabela_1, agora=t1
        )
        self.assertTrue(modificado)
        raw_bytes = arq.read_bytes()
        self.assertNotIn(b"\r\n", raw_bytes)
        self.assertIn("Relatório gerado em: 01/01/2026 10:00:00", raw_bytes.decode("utf-8"))

        mtime_antigo = 1_600_000_000
        os.utime(arq, (mtime_antigo, mtime_antigo))
        modificado_2 = medir_saude_croquis.salvar_relatorio_saude_se_modificado(
            arq, tabela_1, agora=t2
        )
        self.assertFalse(modificado_2)
        self.assertEqual(int(arq.stat().st_mtime), mtime_antigo)

        tabela_2 = "| Croqui | Publicado |\n| --- | --- |\n| croqui_a | ❌ |"
        modificado_3 = medir_saude_croquis.salvar_relatorio_saude_se_modificado(
            arq, tabela_2, agora=t2
        )
        self.assertTrue(modificado_3)
        self.assertIn("Relatório gerado em: 02/01/2026 15:30:00", arq.read_text("utf-8"))

    def test_casos_borda_avaliacao_e_cli_main(self) -> None:
        self.assertEqual(medir_saude_croquis.generate_report_table([]), "")
        self.assertEqual(
            medir_saude_croquis.extrair_dados_tabela_markdown("| col1 | col2 |\nlinha solta"),
            [],
        )

        # Pasta database inexistente
        self.assertFalse(
            medir_saude_croquis.atualizar_relatorio_saude_croquis(
                base_path=self.tmp_path / "db_inexistente",
                output_path=self.tmp_path / "out.md",
            )
        )

        base_dir = self.tmp_path / "db_borda"
        # Croqui sem croqui.yaml e com setor malformado / inexistente
        c_sem_yaml = base_dir / "sem_yaml"
        c_sem_yaml.mkdir(parents=True)
        (c_sem_yaml / "setor_invalido.md").write_text(
            "---\nyaml: [quebrado\n---\n", encoding="utf-8"
        )
        res_sem = medir_saude_croquis.avaliar_saude_croqui(c_sem_yaml)
        self.assertEqual(res_sem["croqui.yaml"], "❌")
        self.assertEqual(res_sem["Coordenadas Picos"], "N/A")

        # Croqui com croqui.yaml corrompido e betas_pendentes corrompido
        c_corrompido = base_dir / "corrompido"
        c_corrompido.mkdir(parents=True)
        (c_corrompido / "croqui.yaml").write_text("yaml: [invalido", encoding="utf-8")
        (c_corrompido / "betas_pendentes.binarypb").write_bytes(b"\xff\xff\xff\xff")
        res_corr = medir_saude_croquis.avaliar_saude_croqui(c_corrompido)
        self.assertEqual(res_corr["croqui.yaml"], "✅")
        self.assertEqual(res_corr["Coordenadas Picos"], "❌ (Erro)")
        self.assertEqual(res_corr["Betas Pendentes"], "⚠️")

        # Setores malformados no croqui.yaml e referenciando .md inexistente
        c_mal = base_dir / "malformado"
        c_mal.mkdir(parents=True)
        (c_mal / "croqui.yaml").write_text(
            "picos:\n"
            "  - setores_ou_grupos:\n"
            "      - null\n"
            "      - outro: 1\n"
            "      - setor: 123\n"
            "      - grupo:\n"
            "          caminho: nao_existe.md\n",
            encoding="utf-8",
        )
        self.assertEqual(
            medir_saude_croquis.check_pontos_de_interesse(c_mal),
            "❌ (0/1)",
        )

        # CLI main() e atualização incremental removendo alvo deletado + dict direto em memória
        out_cli = self.tmp_path / "STATUS_CLI.md"
        medir_saude_croquis.main(["--base-dir", str(base_dir), "--output", str(out_cli)])
        self.assertTrue(out_cli.is_file())

        # Remove sem_yaml do disco e atualiza incrementalmente passando sem_yaml e malformado (como dict direto)
        import shutil

        shutil.rmtree(c_sem_yaml)
        medir_saude_croquis.atualizar_relatorio_saude_croquis(
            base_path=base_dir,
            output_path=out_cli,
            alvos=["sem_yaml", "malformado"],
            dados_em_memoria={"malformado": {"id": "malformado", "publicar_croqui": True}},
        )
        texto_final = out_cli.read_text(encoding="utf-8")
        self.assertNotIn("| sem_yaml |", texto_final)
        self.assertIn("| malformado | ✅ |", texto_final)


if __name__ == "__main__":
    unittest.main()
