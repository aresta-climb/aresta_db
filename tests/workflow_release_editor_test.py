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

    def test_workflow_artefatos_beta_possuem_editor_arestabeta_appinstaller(self) -> None:
        """Garante que o artefato publicado do AppInstaller utiliza o nome EditorArestaBeta.appinstaller."""
        passos = self.conteudo_yaml["jobs"]["release"]["steps"]
        passo_upload = next(
            (
                s for s in passos
                if "upload-artifact" in s.get("uses", "")
                and "Beta" in s.get("name", "")
            ),
            None,
        )
        self.assertIsNotNone(passo_upload, "Passo upload-artifact do canal Beta não encontrado no workflow.")
        assert passo_upload is not None
        caminhos_artefatos = passo_upload.get("with", {}).get("path", "")
        self.assertIn("EditorArestaBeta.appinstaller", caminhos_artefatos)
        self.assertNotIn("EditorAresta.appinstaller", caminhos_artefatos)

    def test_inputs_workflow_possui_publicar_microsoft_store_e_remove_should_publish(self) -> None:
        """Garante que o input publicar_microsoft_store existe como booleano default false e should_publish foi removido."""
        on_block = self.conteudo_yaml.get("on", self.conteudo_yaml.get(True, {}))
        inputs = on_block.get("workflow_dispatch", {}).get("inputs", {})
        self.assertIn("publicar_microsoft_store", inputs, "O input 'publicar_microsoft_store' deve existir.")
        self.assertNotIn("should_publish", inputs, "O input legado 'should_publish' deve ser removido.")
        self.assertEqual(inputs["publicar_microsoft_store"].get("type"), "boolean")
        self.assertFalse(inputs["publicar_microsoft_store"].get("default"))

    def test_passos_microsoft_store_possuem_condicional_e_publicacao_sem_no_commit(self) -> None:
        """Garante que os passos da Microsoft Store possuem condicional do input e não utilizam --noCommit."""
        passos = self.conteudo_yaml["jobs"]["release"]["steps"]

        passos_ms_store = [
            s for s in passos
            if "Microsoft Store" in s.get("name", "")
            or "MS Store" in s.get("name", "")
            or ("Build PyInstaller" in s.get("name", "") and "Beta" not in s.get("name", ""))
            or ("Build MSIX Package" in s.get("name", "") and "Beta" not in s.get("name", ""))
            or ("Disponibilizar pacote MSIX no GitHub" in s.get("name", "") and "Beta" not in s.get("name", ""))
        ]

        self.assertTrue(len(passos_ms_store) >= 4, "Devem existir passos dedicados à compilação e publicação da MS Store.")

        for passo in passos_ms_store:
            condicao = str(passo.get("if", ""))
            self.assertIn(
                "publicar_microsoft_store",
                condicao,
                f"O passo '{passo.get('name')}' deve ter condicional com 'publicar_microsoft_store'.",
            )

        passo_publish = next((s for s in passos if "Publish to MS Store" in s.get("name", "")), None)
        self.assertIsNotNone(passo_publish, "Passo 'Publish to MS Store' não encontrado.")
        assert passo_publish is not None
        run_script = passo_publish.get("run", "")
        self.assertNotIn("--noCommit", run_script, "O passo de publicação não deve usar a flag --noCommit.")

    def test_ordenacao_etapas_executa_canal_beta_antes_da_microsoft_store(self) -> None:
        """Garante que a compilação e publicação do canal Beta ocorrem antes da compilação de produção e MS Store."""
        passos = self.conteudo_yaml["jobs"]["release"]["steps"]
        nomes_passos = [s.get("name", "") for s in passos]

        idx_beta_build = next(i for i, n in enumerate(nomes_passos) if "Build PyInstaller (Canal Beta)" in n)
        idx_beta_publish = next(i for i, n in enumerate(nomes_passos) if "Publicar Canal Beta no Cloudflare R2" in n)

        idx_ms_build = next(i for i, n in enumerate(nomes_passos) if "Build PyInstaller" in n and "Beta" not in n)
        idx_ms_publish = next(i for i, n in enumerate(nomes_passos) if "Publish to MS Store" in n)

        self.assertLess(
            idx_beta_build,
            idx_ms_build,
            "A compilação do canal Beta deve ocorrer antes da compilação de produção para MS Store.",
        )
        self.assertLess(
            idx_beta_publish,
            idx_ms_publish,
            "A publicação do canal Beta deve ocorrer antes da publicação na MS Store.",
        )

