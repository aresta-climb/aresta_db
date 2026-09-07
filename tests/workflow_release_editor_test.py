# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from pathlib import Path
import yaml


class TestWorkflowReleaseEditor(unittest.TestCase):
    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.workflow_path = self.raiz_projeto / ".github" / "workflows" / "release-editor.yml"
        if not self.workflow_path.exists():
            self.skipTest(f"Workflow {self.workflow_path} não encontrado no checkout.")
        with open(self.workflow_path, "r", encoding="utf-8") as f:
            self.conteudo_yaml = yaml.safe_load(f)

    def test_workflow_possui_sparse_checkout_com_tests_e_github(self) -> None:
        """Garante que o sparse-checkout do workflow inclui as pastas tests e .github para testes arquiteturais."""
        passos = self.conteudo_yaml["jobs"]["release"]["steps"]
        passo_checkout = next((s for s in passos if "Checkout" in s.get("name", "")), None)
        self.assertIsNotNone(passo_checkout, "Passo com 'Checkout' não encontrado no workflow.")
        assert passo_checkout is not None
        sparse_checkout = passo_checkout.get("with", {}).get("sparse-checkout", "")
        linhas_sparse = [linha.strip() for linha in sparse_checkout.splitlines() if linha.strip()]
        self.assertIn("tests", linhas_sparse, "A pasta 'tests' deve constar no sparse-checkout.")
        self.assertIn(".github", linhas_sparse, "A pasta '.github' deve constar no sparse-checkout.")

    def test_workflow_possui_supressao_werfault(self) -> None:
        """Garante que o passo de supressão do Windows Error Reporting está configurado."""
        passos = self.conteudo_yaml["jobs"]["release"]["steps"]
        passo_wer = next(
            (s for s in passos if "WerFault" in s.get("name", "") or "Falhas do Windows" in s.get("name", "")),
            None,
        )
        self.assertIsNotNone(passo_wer, "Passo de supressão de falhas do Windows não encontrado.")
        assert passo_wer is not None
        run_script = passo_wer.get("run", "")
        self.assertIn("DontShowUI", run_script)
        self.assertIn("Disabled", run_script)

    def test_etapa_testes_executa_sequencialmente_com_saida_imediata(self) -> None:
        """
        Garante que a etapa de testes do workflow de release executa sequencialmente (-n 0)
        e sem bufferização (-v -s) para identificar imediatamente qualquer teste que travar ou falhar,
        além de definir a variável CI=true para acionar o fast exit limpo.
        """
        passos = self.conteudo_yaml["jobs"]["release"]["steps"]
        passo_testes = next((s for s in passos if "Executar Testes" in s.get("name", "")), None)
        self.assertIsNotNone(passo_testes, "Passo 'Executar Testes' não encontrado no workflow.")
        assert passo_testes is not None
        run_cmd = passo_testes.get("run", "")
        env_vars = passo_testes.get("env", {})

        self.assertIn("-n 0", run_cmd, "A etapa deve rodar com '-n 0' para rastreabilidade sequencial clara.")
        self.assertIn("-v", run_cmd, "A etapa deve rodar com '-v' para listar nomes de cada teste.")
        self.assertTrue("-s" in run_cmd or "--capture=no" in run_cmd, "A etapa deve desativar captura de saída para streaming em tempo real.")
        self.assertIn("uv run pytest", run_cmd)
        self.assertEqual(str(env_vars.get("CI", "")).lower(), "true", "A variável CI=true deve estar configurada no step.")
        self.assertEqual(str(env_vars.get("PYTHONUNBUFFERED", "")), "1", "PYTHONUNBUFFERED=1 deve estar configurado.")
