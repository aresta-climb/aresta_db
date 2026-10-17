# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.dirname(__file__))

import medir_saude_croquis


class TestMedirSaudeCroquis(unittest.TestCase):
    def test_check_status_desenho_extraivel_missing_file(self):
        with patch("pathlib.Path.exists", return_value=False):
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
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=yaml_content)):
                    result = medir_saude_croquis.check_status_desenho_extraivel(Path("test"))
                    self.assertEqual(result, expected_emoji, f"Failed for {input_val}")

    def test_check_croqui_yaml(self):
        with patch("pathlib.Path.exists", return_value=True):
            self.assertTrue(medir_saude_croquis.check_croqui_yaml(Path("test")))
        with patch("pathlib.Path.exists", return_value=False):
            self.assertFalse(medir_saude_croquis.check_croqui_yaml(Path("test")))

    def test_check_publicar_croqui(self):
        # YAML com publicar_croqui = true
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="publicar_croqui: true")):
                self.assertTrue(medir_saude_croquis.check_publicar_croqui(Path("test")))

        # YAML com publicar_croqui = false
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="publicar_croqui: false")):
                self.assertFalse(medir_saude_croquis.check_publicar_croqui(Path("test")))

        # YAML sem publicar_croqui
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="nome: 'Teste'")):
                self.assertFalse(medir_saude_croquis.check_publicar_croqui(Path("test")))

        # Sem YAML
        with patch("pathlib.Path.exists", return_value=False):
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
                "PDF Original": "✅",
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
                "PDF Original": "✅",
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
                "Betas Pendentes": "✅",
                "URL Google Maps": "✅ (1/1)",
                "croqui.yaml": "❌",
                "Conteúdo PDF": "❌",
                "partes.json": "❌",
                "PDF Original": "❌",
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
                "URL Google Maps": "❌ (0/1)",
                "Mapas Gerais": "❌",
                "Betas Pendentes": "⚠️ (2)",
                "croqui.yaml": "❌",
                "Conteúdo PDF": "❌",
                "partes.json": "❌",
                "PDF Original": "❌",
            },
        ]

        # Preenche "Betas Pendentes" e "URL Google Maps" nos itens 1 e 2
        report_data[0]["Betas Pendentes"] = "✅"
        report_data[1]["Betas Pendentes"] = "✅"
        report_data[0]["URL Google Maps"] = "✅ (1/1)"
        report_data[1]["URL Google Maps"] = "❌ (0/1)"

        table = medir_saude_croquis.generate_report_table(report_data)

        # Verifica se o cabeçalho de Desenho Extraível está correto:
        self.assertIn("Desenho Extraível (2/1/1)", table)
        self.assertIn("Revisado Manual (1/4)", table)
        self.assertIn("Publicado (1/4)", table)
        self.assertIn("Betas Pendentes (3/4)", table)
        self.assertIn("URL Google Maps (2/4)", table)

    def test_checar_url_google_maps(self):
        # Sem YAML -> N/A
        with patch("pathlib.Path.exists", return_value=False):
            self.assertEqual(medir_saude_croquis.checar_url_google_maps(Path("test")), "N/A")

        # YAML sem picos -> N/A
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="nome: 'Croqui sem picos'")):
                self.assertEqual(medir_saude_croquis.checar_url_google_maps(Path("test")), "N/A")

        # YAML com picos todos preenchidos -> ✅ (1/1)
        yaml_valido = """
picos:
  - nome: Pico 1
    url_google_maps: https://maps.app.goo.gl/abc123xyz
"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=yaml_valido)):
                self.assertEqual(
                    medir_saude_croquis.checar_url_google_maps(Path("test")), "✅ (1/1)"
                )
                self.assertEqual(
                    medir_saude_croquis.check_url_google_maps(Path("test")), "✅ (1/1)"
                )

        # YAML com múltiplos picos onde apenas parte possui URL -> ⚠️ (1/2)
        yaml_parcial = """
picos:
  - nome: Pico 1
    url_google_maps: https://maps.app.goo.gl/abc123xyz
  - nome: Pico 2
    url_google_maps: ""
"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=yaml_parcial)):
                self.assertEqual(
                    medir_saude_croquis.checar_url_google_maps(Path("test")), "⚠️ (1/2)"
                )

        # YAML com picos sem URL -> ❌ (0/1)
        yaml_sem_url = """
picos:
  - nome: Pico 1
"""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=yaml_sem_url)):
                self.assertEqual(
                    medir_saude_croquis.checar_url_google_maps(Path("test")), "❌ (0/1)"
                )

        # YAML corrompido / exceção -> ❌ (Erro)
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=Exception("Erro de leitura")):
                self.assertEqual(
                    medir_saude_croquis.checar_url_google_maps(Path("test")), "❌ (Erro)"
                )

    def test_check_betas_pendentes(self):
        # Sem arquivo staging -> Saudável (✅)
        with patch("pathlib.Path.exists", return_value=False):
            self.assertEqual(medir_saude_croquis.check_betas_pendentes(Path("test")), "✅")

        # Com arquivo staging e itens pendentes -> ⚠️
        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "coleta_de_betas.inteligencia.avaliador.carregar_betas_pendentes"
            ) as mock_load:
                mock_msg = MagicMock()
                mock_esc = MagicMock()
                mock_esc.candidatos = [1, 2, 3]
                mock_msg.candidatos_por_escalada = [mock_esc]
                mock_load.return_value = mock_msg

                self.assertEqual(medir_saude_croquis.check_betas_pendentes(Path("test")), "⚠️ (3)")

    def test_salvar_relatorio_saude_se_modificado_preserva_timestamp_e_escreve_lf(self):
        import shutil
        import tempfile
        from datetime import datetime

        tmp_dir = Path(tempfile.mkdtemp())
        try:
            arq = tmp_dir / "STATUS_CROQUIS.md"
            tabela_1 = "| Croqui | Publicado |\n| --- | --- |\n| croqui_a | ✅ |"
            t1 = datetime(2026, 1, 1, 10, 0, 0)
            t2 = datetime(2026, 1, 2, 15, 30, 0)

            # 1. Criação inicial em LF
            modificado = medir_saude_croquis.salvar_relatorio_saude_se_modificado(
                arq, tabela_1, agora=t1
            )
            self.assertTrue(modificado)
            raw_bytes = arq.read_bytes()
            self.assertNotIn(b"\r\n", raw_bytes)
            self.assertIn("Relatório gerado em: 01/01/2026 10:00:00", raw_bytes.decode("utf-8"))

            # 2. Mesma tabela não deve atualizar o timestamp nem reescrever o arquivo
            mtime_antigo = 1_600_000_000
            os.utime(arq, (mtime_antigo, mtime_antigo))
            modificado_2 = medir_saude_croquis.salvar_relatorio_saude_se_modificado(
                arq, tabela_1, agora=t2
            )
            self.assertFalse(modificado_2)
            self.assertEqual(int(arq.stat().st_mtime), mtime_antigo)
            self.assertIn("Relatório gerado em: 01/01/2026 10:00:00", arq.read_text("utf-8"))

            # 3. Tabela diferente atualiza o timestamp e mantém LF
            tabela_2 = "| Croqui | Publicado |\n| --- | --- |\n| croqui_a | ❌ |"
            modificado_3 = medir_saude_croquis.salvar_relatorio_saude_se_modificado(
                arq, tabela_2, agora=t2
            )
            self.assertTrue(modificado_3)
            raw_bytes_3 = arq.read_bytes()
            self.assertNotIn(b"\r\n", raw_bytes_3)
            self.assertIn("Relatório gerado em: 02/01/2026 15:30:00", raw_bytes_3.decode("utf-8"))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

