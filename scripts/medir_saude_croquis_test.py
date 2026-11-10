# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes orientados a comportamento para scripts/medir_saude_croquis.py (dump do Painel de Qualidade)."""

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts import medir_saude_croquis


class TestMedirSaudeCroquis(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_avaliar_saude_croqui_reflete_painel_de_qualidade_e_suporta_memoria(self) -> None:
        croqui_dir = self.tmp_path / "croqui_memoria"
        croqui_dir.mkdir()

        # Corrompe croqui.yaml no disco para provar que avaliar_saude_croqui usa dados_yaml em memória
        (croqui_dir / "croqui.yaml").write_text("yaml: [corrompido", encoding="utf-8")

        dados_yaml_memoria = {
            "id": "croqui_memoria",
            "nome": "Serra da Memória",
            "descricao": "Descrição do croqui em memória.",
            "publicar_croqui": True,
            "revisado_manualmente": True,
            "revisado_bounding_circle": False,
            "caminho_thumbnail": "imagens/thumb.webp",
            "creditos": ["Equipe Aresta"],
            "picos": [
                {
                    "nome": "Pico Memória",
                    "descricao": "Acesso pela trilha principal.",
                    "localizacao": {"latitude": -210000000, "longitude": -440000000},
                    "url_google_maps": "https://maps.app.goo.gl/xyz",
                    "malha_estrada": {
                        "conteudo": {
                            "latitude_referencia_e7": -210000000,
                            "longitude_referencia_e7": -440000000,
                            "versao": 2,
                            "nos": [
                                {
                                    "no_osm_id": 10,
                                    "latitude_e7": -210000000,
                                    "longitude_e7": -440000000,
                                    "distancia_metros": 0,
                                    "duracao_minutos": 0,
                                }
                            ],
                        }
                    },
                    "setores_ou_grupos": [{"setor": {"caminho": "setor_1.md"}}],
                }
            ],
        }
        cache_md_memoria = {
            "setor_1.md": (
                {
                    "uid": "uid_setor_1",
                    "nome": "Setor 1",
                    "mapas": [
                        {
                            "caminho_imagem_mapa": "imagens/m.webp",
                            "pontos_de_interesse": [
                                {"uid": "pt1", "circulo": {"x": 10, "y": 10, "raio": 5}}
                            ],
                            "referencias": [{"alvo_uid": "esc1", "pontos_uids": ["pt1"]}],
                        }
                    ],
                    "escaladas": [
                        {
                            "uid": "esc1",
                            "via_esportiva": {
                                "nome": "Via Memória",
                                "dificuldade": "BR_7A",
                            },
                        }
                    ],
                },
                "Corpo do setor",
            ),
        }

        linha = medir_saude_croquis.avaliar_saude_croqui(
            croqui_dir,
            dados_yaml=dados_yaml_memoria,
            cache_md=cache_md_memoria,
        )

        self.assertEqual(linha["Nome"], "croqui_memoria")
        self.assertEqual(linha["Publicado"], "✅")
        self.assertEqual(linha["Pronto Publicar"], "✅")
        # Etapa 1 completa (8000) + créditos (10) + revisão parcial (5) = 8015
        self.assertEqual(linha["Nota Qualidade"], "8015")
        self.assertEqual(linha["Etapa 1"], "✅ 8000/8000 (8/8)")
        self.assertEqual(linha["1.1 Identidade e Capa"], "✅ (3/3)")
        self.assertEqual(linha["1.8 Malha Estrada"], "✅ (1/1)")
        self.assertEqual(linha["3.1 Créditos"], "✅ (1/1)")
        self.assertEqual(linha["3.6 Revisão Final"], "⚠️ (1/2)")

    def test_atualizar_relatorio_saude_croquis_incremental_atualiza_apenas_alvo_e_cabecalho(
        self,
    ) -> None:
        base_dir = self.tmp_path / "database"
        output_file = self.tmp_path / "STATUS_CROQUIS.md"

        for cid, publicado in (("croqui_a", False), ("croqui_b", True)):
            cdir = base_dir / cid
            cdir.mkdir(parents=True)
            (cdir / "croqui.yaml").write_text(
                f"id: {cid}\nnome: {cid}\ndescricao: Desc\ncaminho_thumbnail: img.webp\n"
                f"publicar_croqui: {'true' if publicado else 'false'}\n",
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
        self.assertIn("Nota Qualidade (máx 8860)", texto_inicial)
        self.assertIn("1.8 Malha Estrada (0/2)", texto_inicial)
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
                        "nome": "croqui_a",
                        "descricao": "Desc",
                        "caminho_thumbnail": "img.webp",
                        "publicar_croqui": True,
                    },
                    {},
                )
            },
            agora=t2,
        )
        self.assertTrue(modificou_inc)
        texto_inc = output_file.read_text(encoding="utf-8")
        self.assertIn("Publicado (2/2)", texto_inc)
        self.assertIn("1.1 Identidade e Capa (2/2)", texto_inc)
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
                        "nome": "croqui_a",
                        "descricao": "Desc",
                        "caminho_thumbnail": "img.webp",
                        "publicar_croqui": True,
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
        # Croqui sem croqui.yaml e croqui com croqui.yaml corrompido
        c_sem_yaml = base_dir / "sem_yaml"
        c_sem_yaml.mkdir(parents=True)
        res_sem = medir_saude_croquis.avaliar_saude_croqui(c_sem_yaml)
        self.assertEqual(res_sem["Publicado"], "❌")
        self.assertEqual(res_sem["Nota Qualidade"], "0")
        self.assertEqual(res_sem["1.1 Identidade e Capa"], "❌ (0/3)")

        c_corrompido = base_dir / "corrompido"
        c_corrompido.mkdir(parents=True)
        (c_corrompido / "croqui.yaml").write_text("yaml: [invalido", encoding="utf-8")
        res_corr = medir_saude_croquis.avaliar_saude_croqui(c_corrompido)
        self.assertEqual(res_corr["Nota Qualidade"], "0")

        # CLI main() e atualização incremental removendo alvo deletado + dict direto em memória
        out_cli = self.tmp_path / "STATUS_CLI.md"
        medir_saude_croquis.main(["--base-dir", str(base_dir), "--output", str(out_cli)])
        self.assertTrue(out_cli.is_file())

        shutil.rmtree(c_sem_yaml)
        medir_saude_croquis.atualizar_relatorio_saude_croquis(
            base_path=base_dir,
            output_path=out_cli,
            alvos=["sem_yaml", "corrompido"],
            dados_em_memoria={"corrompido": {"id": "corrompido", "publicar_croqui": True}},
        )
        texto_final = out_cli.read_text(encoding="utf-8")
        self.assertNotIn("| sem_yaml |", texto_final)
        self.assertIn("| corrompido | ✅ |", texto_final)


if __name__ == "__main__":
    unittest.main()
