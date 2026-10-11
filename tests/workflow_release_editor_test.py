# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from pathlib import Path

import yaml


class TestWorkflowReleaseEditor(unittest.TestCase):
    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.dir_workflows = self.raiz_projeto / ".github" / "workflows"
        self.workflow_path = self.dir_workflows / "release-editor.yml"
        self.windows_path = self.dir_workflows / "build_editor_windows.yml"
        self.macos_path = self.dir_workflows / "build_editor_macos.yml"
        self.linux_path = self.dir_workflows / "build_editor_linux.yml"

        if not self.workflow_path.exists():
            self.skipTest(f"Workflow {self.workflow_path} não encontrado no checkout.")

        with open(self.workflow_path, encoding="utf-8") as f:
            self.conteudo_yaml = yaml.safe_load(f)

        with open(self.windows_path, encoding="utf-8") as f:
            self.conteudo_windows = yaml.safe_load(f)

        with open(self.macos_path, encoding="utf-8") as f:
            self.conteudo_macos = yaml.safe_load(f)

        with open(self.linux_path, encoding="utf-8") as f:
            self.conteudo_linux = yaml.safe_load(f)

    def test_workflow_possui_sparse_checkout_com_tests_e_github(self) -> None:
        """Garante que o sparse-checkout do workflow inclui as pastas tests e .github para testes arquiteturais."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_checkout = next((s for s in passos if "Checkout" in s.get("name", "")), None)
        self.assertIsNotNone(passo_checkout, "Passo com 'Checkout' não encontrado no workflow.")
        assert passo_checkout is not None
        sparse_checkout = passo_checkout.get("with", {}).get("sparse-checkout", "")
        linhas_sparse = [linha.strip() for linha in sparse_checkout.splitlines() if linha.strip()]
        self.assertIn("tests", linhas_sparse, "A pasta 'tests' deve constar no sparse-checkout.")
        self.assertIn(
            ".github", linhas_sparse, "A pasta '.github' deve constar no sparse-checkout."
        )

    def test_workflow_possui_supressao_werfault(self) -> None:
        """Garante que o passo de supressão do Windows Error Reporting está configurado no build Windows."""
        passos = self.conteudo_windows["jobs"]["build_windows"]["steps"]
        passo_wer = next(
            (
                s
                for s in passos
                if "WerFault" in s.get("name", "") or "Falhas do Windows" in s.get("name", "")
            ),
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
        e sem bufferização (-v -s) no runner Linux de preparação,
        além de definir a variável CI=true para acionar o fast exit limpo.
        """
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_testes = next((s for s in passos if "Executar Testes" in s.get("name", "")), None)
        self.assertIsNotNone(passo_testes, "Passo 'Executar Testes' não encontrado no workflow.")
        assert passo_testes is not None
        run_cmd = passo_testes.get("run", "")
        env_vars = passo_testes.get("env", {})

        self.assertIn(
            "-n 0", run_cmd, "A etapa deve rodar com '-n 0' para rastreabilidade sequencial clara."
        )
        self.assertIn("-v", run_cmd, "A etapa deve rodar com '-v' para listar nomes de cada teste.")
        self.assertTrue(
            "-s" in run_cmd or "--capture=no" in run_cmd,
            "A etapa deve desativar captura de saída para streaming em tempo real.",
        )
        self.assertIn("uv run pytest", run_cmd)
        self.assertEqual(
            str(env_vars.get("CI", "")).lower(),
            "true",
            "A variável CI=true deve estar configurada no step.",
        )
        self.assertEqual(
            str(env_vars.get("PYTHONUNBUFFERED", "")),
            "1",
            "PYTHONUNBUFFERED=1 deve estar configurado.",
        )

    def test_job_prepare_release_instala_dependencias_graficas_qt_no_ubuntu(self) -> None:
        """
        Garante que o job prepare_release instala as dependências gráficas necessárias (libegl1, libgl1, etc.)
        no Ubuntu antes da execução dos testes com PySide6 / pytest-qt.
        """
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_deps_qt = next(
            (
                s
                for s in passos
                if "dependências gráficas" in s.get("name", "").lower()
                or "qt" in s.get("name", "").lower()
            ),
            None,
        )
        self.assertIsNotNone(
            passo_deps_qt,
            "Passo de instalação de dependências do Qt não encontrado em prepare_release.",
        )
        assert passo_deps_qt is not None
        run_cmd = passo_deps_qt.get("run", "")
        self.assertIn("libegl1", run_cmd)
        self.assertIn("libgl1", run_cmd)

    def test_workflow_artefatos_beta_possuem_editor_arestabeta_appinstaller(self) -> None:
        """Garante que o artefato publicado do AppInstaller utiliza o nome EditorArestaBeta.appinstaller."""
        passos = self.conteudo_windows["jobs"]["build_windows"]["steps"]
        passo_upload = next(
            (s for s in passos if "upload-artifact" in s.get("uses", "")),
            None,
        )
        self.assertIsNotNone(
            passo_upload, "Passo upload-artifact do canal Windows não encontrado no workflow."
        )
        assert passo_upload is not None
        caminhos_artefatos = passo_upload.get("with", {}).get("path", "")
        self.assertIn("EditorArestaBeta.appinstaller", caminhos_artefatos)
        self.assertNotIn("EditorAresta.appinstaller", caminhos_artefatos)

    def test_inputs_workflow_possui_publicar_microsoft_store_e_remove_should_publish(self) -> None:
        """Garante que o input publicar_microsoft_store existe como booleano default true e should_publish foi removido."""
        on_block = self.conteudo_yaml.get("on", self.conteudo_yaml.get(True, {}))
        inputs = on_block.get("workflow_dispatch", {}).get("inputs", {})
        self.assertIn(
            "publicar_microsoft_store", inputs, "O input 'publicar_microsoft_store' deve existir."
        )
        self.assertNotIn(
            "should_publish", inputs, "O input legado 'should_publish' deve ser removido."
        )
        self.assertEqual(inputs["publicar_microsoft_store"].get("type"), "boolean")
        self.assertTrue(inputs["publicar_microsoft_store"].get("default"))

    def test_passos_microsoft_store_possuem_condicional_e_publicacao_sem_no_commit(self) -> None:
        """Garante que os passos da Microsoft Store possuem condicional do input e não utilizam --noCommit."""
        passos = self.conteudo_windows["jobs"]["build_windows"]["steps"]

        passos_ms_store = [
            s
            for s in passos
            if "Microsoft Store" in s.get("name", "")
            or "MS Store" in s.get("name", "")
            or ("Build PyInstaller" in s.get("name", "") and "Beta" not in s.get("name", ""))
            or ("Build MSIX Package" in s.get("name", "") and "Beta" not in s.get("name", ""))
        ]

        self.assertTrue(
            len(passos_ms_store) >= 3,
            "Devem existir passos dedicados à compilação e publicação da MS Store.",
        )

        for passo in passos_ms_store:
            condicao = str(passo.get("if", ""))
            self.assertIn(
                "publicar_microsoft_store",
                condicao,
                f"O passo '{passo.get('name')}' deve ter condicional com 'publicar_microsoft_store'.",
            )

        passo_publish = next(
            (s for s in passos if "Publish to MS Store" in s.get("name", "")), None
        )
        self.assertIsNotNone(passo_publish, "Passo 'Publish to MS Store' não encontrado.")
        assert passo_publish is not None
        run_script = passo_publish.get("run", "")
        self.assertNotIn(
            "--noCommit", run_script, "O passo de publicação não deve usar a flag --noCommit."
        )
        self.assertIn("EditorAresta.msix", run_script)

    def test_ordenacao_etapas_executa_canal_beta_antes_da_microsoft_store(self) -> None:
        """Garante que a compilação e publicação do canal Beta ocorrem antes da compilação de produção e MS Store."""
        passos = self.conteudo_windows["jobs"]["build_windows"]["steps"]
        nomes_passos = [s.get("name", "") for s in passos]

        idx_beta_build = next(
            i for i, n in enumerate(nomes_passos) if "Build PyInstaller (Canal Beta)" in n
        )
        idx_beta_publish = next(
            i for i, n in enumerate(nomes_passos) if "Publicar Canal Beta no Cloudflare R2" in n
        )

        idx_ms_build = next(
            i for i, n in enumerate(nomes_passos) if "Build PyInstaller" in n and "Beta" not in n
        )
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

    def test_passos_versao_executam_uv_lock(self) -> None:
        """Garante que as etapas de injeção de versão oficial e dev executam 'uv lock' para sincronizar o uv.lock."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_oficial = next(
            (s for s in passos if "Injetar Versão Oficial" in s.get("name", "")), None
        )
        passo_dev = next(
            (s for s in passos if "Injetar Ciclo de Desenvolvimento" in s.get("name", "")), None
        )

        self.assertIsNotNone(passo_oficial, "Passo 'Injetar Versão Oficial' não encontrado.")
        assert passo_oficial is not None
        linhas_oficial = [linha.strip() for linha in passo_oficial.get("run", "").splitlines()]
        self.assertIn(
            "uv lock", linhas_oficial, "O passo 'Injetar Versão Oficial' deve executar 'uv lock'."
        )

        self.assertIsNotNone(passo_dev, "Passo 'Injetar Ciclo de Desenvolvimento' não encontrado.")
        assert passo_dev is not None
        linhas_dev = [linha.strip() for linha in passo_dev.get("run", "").splitlines()]
        self.assertIn(
            "uv lock",
            linhas_dev,
            "O passo 'Injetar Ciclo de Desenvolvimento' deve executar 'uv lock'.",
        )

    def test_workflow_exporta_versao_como_output_do_job_release(self) -> None:
        """Garante que o job prepare_release exporta a versão e tag_name para consumo das sub-actions dependentes."""
        outputs = self.conteudo_yaml["jobs"]["prepare_release"].get("outputs", {})
        self.assertIn("versao", outputs, "O job 'prepare_release' deve declarar 'outputs.versao'.")
        self.assertIn(
            "tag_name", outputs, "O job 'prepare_release' deve declarar 'outputs.tag_name'."
        )

    def test_workflow_possui_subactions_paralelas(self) -> None:
        """Garante que o orquestrador possui os 3 sub-jobs paralelos chamando os workflows reutilizáveis."""
        jobs = self.conteudo_yaml.get("jobs", {})
        self.assertIn("prepare_release", jobs)
        self.assertIn("build_windows", jobs)
        self.assertIn("build_macos", jobs)
        self.assertIn("build_linux", jobs)

        for sub_job_name in ["build_windows", "build_macos", "build_linux"]:
            job = jobs[sub_job_name]
            self.assertEqual(
                job.get("needs"),
                "prepare_release",
                f"O sub-job {sub_job_name} deve depender de prepare_release.",
            )
            self.assertIn("uses", job, f"O sub-job {sub_job_name} deve usar workflow reutilizável.")

    def test_subaction_macos_configurada_em_macos_14(self) -> None:
        """Garante que o sub-workflow build_editor_macos roda em macos-14 com PyInstaller, Sparkle e DMG."""
        job = self.conteudo_macos["jobs"]["build_macos"]
        self.assertEqual(job.get("runs-on"), "macos-14")
        nomes_passos = [p.get("name", "") for p in job.get("steps", [])]
        self.assertTrue(
            any("PyInstaller" in n for n in nomes_passos),
            "Deve haver compilação PyInstaller no macOS.",
        )
        self.assertTrue(
            any("Sparkle" in n for n in nomes_passos),
            "Deve haver download ou configuração do Sparkle.",
        )
        self.assertTrue(
            any("DMG" in n for n in nomes_passos), "Deve haver empacotamento DMG no macOS."
        )
        self.assertTrue(
            any("Cloudflare R2" in n for n in nomes_passos),
            "Deve haver publicação no Cloudflare R2.",
        )

    def test_passo_download_sparkle_obtem_versao_mais_recente_dinamicamente(self) -> None:
        """Garante que o Sparkle é baixado em sua versão mais recente via gh release download sem versão fixa."""
        passos = self.conteudo_macos["jobs"]["build_macos"]["steps"]
        passo_sparkle = next((s for s in passos if "Sparkle" in s.get("name", "")), None)
        self.assertIsNotNone(passo_sparkle, "Passo de download do Sparkle não encontrado.")
        assert passo_sparkle is not None
        run_cmd = passo_sparkle.get("run", "")
        self.assertIn(
            "gh release download",
            run_cmd,
            "Deve utilizar gh release download para obter a versão mais recente.",
        )
        self.assertIn(
            "sparkle-project/Sparkle",
            run_cmd,
            "Deve baixar do repositório oficial sparkle-project/Sparkle.",
        )
        self.assertIn(
            "Sparkle-*.tar.xz",
            run_cmd,
            "Deve usar pattern para pegar o tarball da release mais recente.",
        )
        self.assertNotIn(
            "2.6.4", run_cmd, "Não deve haver versão fixa/hardcoded no download do Sparkle."
        )

    def test_subaction_linux_publica_repositorio_ostree_r2(self) -> None:
        """Garante que o sub-workflow build_editor_linux publica o repositório OSTree no Cloudflare R2."""
        job = self.conteudo_linux["jobs"]["build_linux"]
        self.assertEqual(job.get("runs-on"), "ubuntu-latest")
        nomes_passos = [p.get("name", "") for p in job.get("steps", [])]
        self.assertTrue(
            any("Cloudflare R2" in n for n in nomes_passos),
            "Deve haver publicação do repositório no Cloudflare R2.",
        )

    def test_subaction_linux_utiliza_flatpak_builder_action_com_cache(self) -> None:
        """Garante que o sub-workflow build_editor_linux utiliza a action oficial flatpak-builder com cache habilitado e build-bundle desativado."""
        job = self.conteudo_linux["jobs"]["build_linux"]
        passos = job.get("steps", [])
        passo_builder = next(
            (
                p
                for p in passos
                if "flatpak-github-actions/flatpak-builder" in str(p.get("uses", ""))
            ),
            None,
        )
        self.assertIsNotNone(
            passo_builder, "Passo com flatpak-builder action oficial não encontrado."
        )
        assert passo_builder is not None
        com_parametros = passo_builder.get("with", {})
        self.assertTrue(
            com_parametros.get("cache"), "O cache da action flatpak-builder deve estar habilitado."
        )
        self.assertFalse(
            com_parametros.get("build-bundle", True),
            "O parâmetro 'build-bundle' deve estar desabilitado para publicação direta via OSTree.",
        )

    def test_orquestrador_cria_github_release_oficial(self) -> None:
        """Garante que o orquestrador cria a GitHub Release oficial com gh release create."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_release = next(
            (s for s in passos if "Criar GitHub Release" in s.get("name", "")), None
        )
        self.assertIsNotNone(
            passo_release, "Passo 'Criar GitHub Release Oficial' não encontrado no orquestrador."
        )
        assert passo_release is not None
        run_cmd = passo_release.get("run", "")
        self.assertIn("gh release create", run_cmd)

    def test_subaction_linux_gera_e_publica_source_tarball(self) -> None:
        """Garante que o build Linux gera e publica o source tarball na GitHub Release."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        passo_tarball = next((s for s in passos if "Source Tarball" in s.get("name", "")), None)
        self.assertIsNotNone(
            passo_tarball,
            "Passo 'Gerar e Publicar Source Tarball' não encontrado no workflow Linux.",
        )
        assert passo_tarball is not None
        run_cmd = passo_tarball.get("run", "")
        self.assertIn("editor/build.py source-tarball", run_cmd)
        self.assertIn("gh release upload", run_cmd)

    def test_passo_calcular_versao_exporta_versao_e_tag_name(self) -> None:
        """Garante que o passo 'Calcular Versão de Release' grava versao e tag_name no $GITHUB_OUTPUT."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_versao = next((s for s in passos if "Calcular Versão" in s.get("name", "")), None)
        self.assertIsNotNone(passo_versao)
        assert passo_versao is not None
        run_script = passo_versao.get("run", "")
        self.assertIn('echo "versao=$RELEASE_VER" >> $GITHUB_OUTPUT', run_script)
        self.assertIn('echo "tag_name=editor-v$RELEASE_VER" >> $GITHUB_OUTPUT', run_script)

    def test_prepare_release_gera_e_anexa_source_tarball(self) -> None:
        """Garante que o orquestrador prepare_release gera o source tarball e o anexa na criação da release oficial."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_tarball = next((s for s in passos if "Source Tarball" in s.get("name", "")), None)
        self.assertIsNotNone(
            passo_tarball, "Passo de gerar source tarball deve existir em prepare_release."
        )
        assert passo_tarball is not None
        run_tarball = passo_tarball.get("run", "")
        self.assertIn("editor/build.py source-tarball", run_tarball)
        self.assertIn("--versao", run_tarball)

        passo_release = next(
            (s for s in passos if "Criar GitHub Release" in s.get("name", "")), None
        )
        self.assertIsNotNone(passo_release)
        assert passo_release is not None
        run_release = passo_release.get("run", "")
        self.assertIn("gh release create", run_release)
        self.assertIn("source.tar.gz", run_release)

    def test_subactions_possuem_permissao_contents_read_e_especifica_versao_tarball(self) -> None:
        """
        Garante que os sub-workflows reutilizáveis possuem permissão restrita 'contents: read'
        para compatibilidade com a invocação pelo orquestrador (autenticando escritas via app-token),
        e que o build_linux passa --versao para source-tarball.
        """
        job_linux = self.conteudo_linux["jobs"]["build_linux"]
        self.assertEqual(job_linux.get("permissions", {}).get("contents"), "read")

        job_windows = self.conteudo_windows["jobs"]["build_windows"]
        self.assertEqual(job_windows.get("permissions", {}).get("contents"), "read")

        job_macos = self.conteudo_macos["jobs"]["build_macos"]
        self.assertEqual(job_macos.get("permissions", {}).get("contents"), "read")

        passos = job_linux["steps"]
        passo_tarball = next((s for s in passos if "Source Tarball" in s.get("name", "")), None)
        self.assertIsNotNone(passo_tarball)
        assert passo_tarball is not None
        run_cmd = passo_tarball.get("run", "")
        self.assertIn("--versao", run_cmd)

    def test_subactions_usam_inputs_versao_em_vez_de_steps_versao(self) -> None:
        """
        Garante que os sub-workflows reutilizáveis (Windows, macOS, Linux)
        referenciam inputs.versao e não o inexistente steps.versao.outputs.versao,
        prevenindo geração de manifesto AppxManifest com Version vazia.
        """
        for caminho in [self.windows_path, self.macos_path, self.linux_path]:
            texto = caminho.read_text(encoding="utf-8")
            self.assertNotIn(
                "steps.versao",
                texto,
                f"O sub-workflow {caminho.name} referencia 'steps.versao' inexistente. Deve usar 'inputs.versao'.",
            )
