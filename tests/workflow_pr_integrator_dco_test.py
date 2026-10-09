# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes automatizados para validação do arquivo de configuração do DCO (.github/dco.yml)
e do workflow do integrador de Pull Requests (.github/workflows/pr-integrator.yml).
"""

import unittest
from pathlib import Path
import yaml


class TestWorkflowPrIntegratorDco(unittest.TestCase):
    """Testa a configuração do DCO e a verificação de DCO no workflow do integrador."""

    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.caminho_dco = self.raiz_projeto / ".github" / "dco.yml"
        self.caminho_workflow = self.raiz_projeto / ".github" / "workflows" / "pr-integrator.yml"

    def test_arquivo_dco_config_existe_e_desativa_exigencia_para_membros(self) -> None:
        """Garante que .github/dco.yml existe e possui a diretiva require.members configurada como false."""
        self.assertTrue(self.caminho_dco.exists(), "O arquivo .github/dco.yml deve existir na raiz.")

        with open(self.caminho_dco, "r", encoding="utf-8") as f:
            conteudo = yaml.safe_load(f)

        self.assertIsInstance(conteudo, dict, "O conteúdo de .github/dco.yml deve ser um dicionário YAML.")
        self.assertIn("require", conteudo, "A chave 'require' deve estar presente no .github/dco.yml.")
        self.assertIn("members", conteudo["require"], "A subchave 'members' deve estar presente sob 'require'.")
        self.assertFalse(
            conteudo["require"]["members"],
            "A diretiva require.members deve ser explicitamente False para isentar membros com commits verificados.",
        )

    def test_workflow_pr_integrator_possui_passo_verificacao_dco_antes_do_merge(self) -> None:
        """Garante que pr-integrator.yml possui uma etapa dedicada para verificar o DCO antes do merge."""
        self.assertTrue(self.caminho_workflow.exists(), "O workflow pr-integrator.yml deve existir.")

        with open(self.caminho_workflow, "r", encoding="utf-8") as f:
            conteudo_workflow = yaml.safe_load(f)

        passos = conteudo_workflow["jobs"]["integrate"]["steps"]
        nomes_passos = [p.get("name", "") for p in passos]

        # Verifica a existência do passo de DCO
        passo_dco = next((p for p in passos if "DCO" in p.get("name", "")), None)
        self.assertIsNotNone(
            passo_dco,
            f"Passo de verificação de DCO não encontrado em pr-integrator.yml. Passos atuais: {nomes_passos}",
        )
        assert passo_dco is not None

        # Verifica a ordem dos passos: DCO deve estar depois de 'Commitar e Enviar Alterações' e antes de 'Realizar Merge do PR'
        indice_dco = passos.index(passo_dco)
        passo_push = next((p for p in passos if "Commitar" in p.get("name", "")), None)
        self.assertIsNotNone(passo_push, "Passo de commit e push não encontrado.")
        assert passo_push is not None
        indice_push = passos.index(passo_push)

        self.assertLess(
            indice_push,
            indice_dco,
            "A verificação do DCO deve ser executada após o push das compilações de deploy.",
        )

        passo_merge = next((p for p in passos if "Merge" in p.get("name", "")), None)
        self.assertIsNotNone(passo_merge, "Passo de merge do PR não encontrado.")
        assert passo_merge is not None
        indice_merge = passos.index(passo_merge)

        self.assertLess(
            indice_dco,
            indice_merge,
            "A verificação do DCO deve ser executada obrigatoriamente antes do merge do PR.",
        )

        # Verifica as credenciais e variáveis de ambiente
        env_dco = passo_dco.get("env", {})
        self.assertIn("GH_TOKEN", env_dco, "O passo de DCO deve definir GH_TOKEN.")
        self.assertEqual(
            env_dco["GH_TOKEN"],
            "${{ steps.app-token.outputs.token }}",
            "O token usado deve ser o app-token com credenciais do bot.",
        )

        # Verifica se o script do passo consulta gh pr checks e o check DCO
        script_dco = passo_dco.get("run", "")
        self.assertIn("gh pr checks", script_dco, "O passo de DCO deve utilizar 'gh pr checks'.")
        self.assertIn("DCO", script_dco, "O script do passo deve filtrar especificamente o check 'DCO'.")
        self.assertIn("exit 1", script_dco, "O passo deve abortar com exit 1 em caso de falha no DCO.")
        self.assertIn("pass", script_dco, "O passo deve tratar o bucket 'pass'.")
        self.assertIn("fail", script_dco, "O passo deve tratar o bucket 'fail'.")


if __name__ == "__main__":
    unittest.main()
