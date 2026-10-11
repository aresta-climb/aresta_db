# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from pathlib import Path

import yaml


class TestWorkflowPrCodeValidator(unittest.TestCase):
    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.workflow_path = self.raiz_projeto / ".github" / "workflows" / "pr-code-validator.yml"

        if not self.workflow_path.exists():
            self.skipTest(f"Workflow {self.workflow_path} não encontrado no checkout.")

        with open(self.workflow_path, encoding="utf-8") as f:
            self.conteudo_yaml = yaml.safe_load(f)

    def test_workflow_instala_dependencias_graficas_qt(self) -> None:
        """Garante que o validador de PR instala dependências de sistema para Qt/PySide6 no Ubuntu."""
        passos = self.conteudo_yaml["jobs"]["test"]["steps"]
        passo_deps = next(
            (
                s
                for s in passos
                if "dependências gráficas" in s.get("name", "").lower()
                or "qt" in s.get("name", "").lower()
            ),
            None,
        )
        self.assertIsNotNone(
            passo_deps, "Passo de instalação de dependências do Qt não encontrado."
        )
        assert passo_deps is not None
        run_cmd = passo_deps.get("run", "")
        self.assertIn("libegl1", run_cmd)
        self.assertIn("libgl1", run_cmd)
        self.assertIn("libxkbcommon-x11-0", run_cmd)

    def test_etapa_pytest_executa_com_xvfb_e_offscreen(self) -> None:
        """Garante que os testes rodam com xvfb-run e variáveis de ambiente apropriadas para headless."""
        passos = self.conteudo_yaml["jobs"]["test"]["steps"]
        passo_pytest = next((s for s in passos if "pytest" in s.get("name", "").lower()), None)
        self.assertIsNotNone(passo_pytest, "Passo do pytest não encontrado.")
        assert passo_pytest is not None

        run_cmd = passo_pytest.get("run", "")
        env_vars = passo_pytest.get("env", {})

        self.assertIn("xvfb-run", run_cmd)
        self.assertIn("uv run pytest", run_cmd)
        self.assertEqual(str(env_vars.get("CI", "")).lower(), "true")
        self.assertEqual(str(env_vars.get("QT_QPA_PLATFORM", "")), "offscreen")

    def test_workflow_executa_checagem_qualidade_ruff(self) -> None:
        """Garante que a verificação de lint e formatação do Ruff ocorre antes das dependências do Qt."""
        passos = self.conteudo_yaml["jobs"]["test"]["steps"]
        idx_ruff = next(
            (i for i, s in enumerate(passos) if "ruff" in s.get("name", "").lower()),
            None,
        )
        self.assertIsNotNone(idx_ruff, "Passo do Ruff não encontrado.")
        assert idx_ruff is not None

        idx_qt = next(
            (
                i
                for i, s in enumerate(passos)
                if "dependências gráficas" in s.get("name", "").lower()
            ),
            None,
        )
        self.assertIsNotNone(idx_qt, "Passo do Qt não encontrado.")
        assert idx_qt is not None

        # O Ruff deve rodar antes da instalação pesada do Qt para fail-fast imediato
        self.assertLess(idx_ruff, idx_qt)

        run_cmd = passos[idx_ruff].get("run", "")
        self.assertIn("uv run ruff check --output-format=github .", run_cmd)
        self.assertIn("uv run ruff format --check .", run_cmd)
