# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes automatizados para validação do arquivo de configuração do DCO (.github/dco.yml)
e do workflow do integrador de Pull Requests (.github/workflows/pr-integrator.yml).
"""

import unittest
from pathlib import Path

from editor.core.serializacao_util import carregar_yaml


class TestWorkflowPrIntegratorDco(unittest.TestCase):
    """Testa a configuração do DCO e a delegação do workflow do integrador para `serving/integrador_pr_lib.py`."""

    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.caminho_dco = self.raiz_projeto / ".github" / "dco.yml"
        self.caminho_workflow = self.raiz_projeto / ".github" / "workflows" / "pr-integrator.yml"

    def test_arquivo_dco_config_existe_e_desativa_exigencia_para_membros(self) -> None:
        """Garante que .github/dco.yml existe e possui a diretiva require.members configurada como false."""
        self.assertTrue(
            self.caminho_dco.exists(), "O arquivo .github/dco.yml deve existir na raiz."
        )

        with open(self.caminho_dco, encoding="utf-8") as f:
            conteudo = carregar_yaml(f)

        self.assertIsInstance(
            conteudo, dict, "O conteúdo de .github/dco.yml deve ser um dicionário YAML."
        )
        self.assertIn(
            "require", conteudo, "A chave 'require' deve estar presente no .github/dco.yml."
        )
        self.assertIn(
            "members",
            conteudo["require"],
            "A subchave 'members' deve estar presente sob 'require'.",
        )
        self.assertFalse(
            conteudo["require"]["members"],
            "A diretiva require.members deve ser explicitamente False para isentar membros com commits verificados.",
        )

    def test_workflow_pr_integrator_possui_passo_verificacao_dco_antes_do_merge(self) -> None:
        """Garante que pr-integrator.yml possui uma etapa dedicada para verificar o DCO antes do merge."""
        self.assertTrue(
            self.caminho_workflow.exists(), "O workflow pr-integrator.yml deve existir."
        )

        with open(self.caminho_workflow, encoding="utf-8") as f:
            conteudo_workflow = carregar_yaml(f)

        passos = conteudo_workflow["jobs"]["integrate"]["steps"]
        nomes_passos = [p.get("name", "") for p in passos]

        passo_dco = next((p for p in passos if "DCO" in p.get("name", "")), None)
        self.assertIsNotNone(
            passo_dco,
            f"Passo de verificação de DCO não encontrado em pr-integrator.yml. Passos atuais: {nomes_passos}",
        )
        assert passo_dco is not None

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

        env_dco = passo_dco.get("env", {})
        self.assertEqual(
            env_dco.get("GH_TOKEN"),
            "${{ steps.app-token.outputs.token }}",
            "O token usado deve ser o app-token com credenciais do bot.",
        )

        script_dco = passo_dco.get("run", "")
        self.assertIn("serving/integrador_pr_lib.py", script_dco)
        self.assertIn("verificar-dco", script_dco)

    def test_workflow_pr_integrator_possui_passo_aguardar_e_validar_checagens_antes_do_deploy(
        self,
    ) -> None:
        """Garante que pr-integrator.yml valida todos os checks ativos antes de instalar dependências e rodar deploy."""
        self.assertTrue(
            self.caminho_workflow.exists(), "O workflow pr-integrator.yml deve existir."
        )

        with open(self.caminho_workflow, encoding="utf-8") as f:
            conteudo_workflow = carregar_yaml(f)

        passos = conteudo_workflow["jobs"]["integrate"]["steps"]
        nomes_passos = [p.get("name", "") for p in passos]

        passo_checks = next(
            (
                p
                for p in passos
                if "Aguardar e Validar Checagens do Pull Request" in p.get("name", "")
            ),
            None,
        )
        self.assertIsNotNone(
            passo_checks,
            f"Passo 'Aguardar e Validar Checagens do Pull Request' não encontrado. Passos atuais: {nomes_passos}",
        )
        assert passo_checks is not None

        indice_checks = passos.index(passo_checks)
        passo_deps = next((p for p in passos if "Instalar Dependências" in p.get("name", "")), None)
        self.assertIsNotNone(passo_deps, "Passo 'Instalar Dependências' não encontrado.")
        assert passo_deps is not None
        indice_deps = passos.index(passo_deps)

        self.assertLess(
            indice_checks,
            indice_deps,
            "A etapa de validação de checks deve ocorrer antes da instalação de dependências para garantir fail-fast.",
        )

        env_checks = passo_checks.get("env", {})
        self.assertEqual(
            env_checks.get("GH_TOKEN"),
            "${{ steps.app-token.outputs.token }}",
            "O token usado deve ser o app-token com credenciais do bot.",
        )

        script_checks = passo_checks.get("run", "")
        self.assertIn("serving/integrador_pr_lib.py", script_checks)
        self.assertIn("validar-checks", script_checks)

    def test_workflow_pr_integrator_sincroniza_branch_base_e_delega_commit_e_merge(
        self,
    ) -> None:
        """Garante que pr-integrator.yml delega sincronização da base, commit e merge para integrador_pr_lib.py."""
        self.assertTrue(
            self.caminho_workflow.exists(), "O workflow pr-integrator.yml deve existir."
        )

        with open(self.caminho_workflow, encoding="utf-8") as f:
            conteudo_workflow = carregar_yaml(f)

        passos = conteudo_workflow["jobs"]["integrate"]["steps"]
        nomes_passos = [p.get("name", "") for p in passos]

        passo_sync = next(
            (p for p in passos if "Sincronizar Branch com a Branch Base" in p.get("name", "")),
            None,
        )
        self.assertIsNotNone(
            passo_sync,
            f"Passo 'Sincronizar Branch com a Branch Base' não encontrado. Passos atuais: {nomes_passos}",
        )
        assert passo_sync is not None

        passo_deploy = next(
            (p for p in passos if "Executar Deploy Generated" in p.get("name", "")), None
        )
        self.assertIsNotNone(passo_deploy)
        assert passo_deploy is not None

        self.assertLess(
            passos.index(passo_sync),
            passos.index(passo_deploy),
            "A sincronização com a branch base deve ocorrer antes da execução do deploy_generated.py.",
        )

        script_sync = passo_sync.get("run", "")
        self.assertIn("serving/integrador_pr_lib.py", script_sync)
        self.assertIn("sincronizar-base", script_sync)

        passo_commit = next((p for p in passos if "Commitar" in p.get("name", "")), None)
        self.assertIsNotNone(passo_commit)
        assert passo_commit is not None
        script_commit = passo_commit.get("run", "")
        self.assertIn("serving/integrador_pr_lib.py", script_commit)
        self.assertIn("commitar-e-enviar", script_commit)

        passo_merge = next((p for p in passos if "Realizar Merge do PR" in p.get("name", "")), None)
        self.assertIsNotNone(passo_merge)
        assert passo_merge is not None
        script_merge = passo_merge.get("run", "")
        self.assertIn("serving/integrador_pr_lib.py", script_merge)
        self.assertIn("realizar-merge", script_merge)


if __name__ == "__main__":
    unittest.main()
