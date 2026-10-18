# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from pathlib import Path

from editor.core.serializacao_util import carregar_yaml


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
            self.conteudo_yaml = carregar_yaml(f)

        with open(self.windows_path, encoding="utf-8") as f:
            self.conteudo_windows = carregar_yaml(f)

        with open(self.macos_path, encoding="utf-8") as f:
            self.conteudo_macos = carregar_yaml(f)

        with open(self.linux_path, encoding="utf-8") as f:
            self.conteudo_linux = carregar_yaml(f)

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

    def test_subaction_macos_configurada_em_macos_latest(self) -> None:
        """Garante que o sub-workflow build_editor_macos compila com PyInstaller, Sparkle e DMG e publica no R2 usando macos-latest."""
        job_compilar = self.conteudo_macos["jobs"]["compilar_macos"]
        self.assertEqual(job_compilar.get("runs-on"), "macos-latest")
        nomes_compilar = [p.get("name", "") for p in job_compilar.get("steps", [])]
        self.assertTrue(
            any("PyInstaller" in n for n in nomes_compilar),
            "Deve haver compilação PyInstaller no macOS.",
        )
        self.assertTrue(
            any("Sparkle" in n for n in nomes_compilar),
            "Deve haver download ou configuração do Sparkle.",
        )
        self.assertTrue(
            any("DMG" in n for n in nomes_compilar), "Deve haver empacotamento DMG no macOS."
        )

        # Validação do setup-uv com python-arch
        passo_setup_uv = next(
            (s for s in job_compilar.get("steps", []) if "setup-uv" in str(s.get("uses", ""))),
            None,
        )
        self.assertIsNotNone(passo_setup_uv, "Deve existir o passo de setup-uv no macOS.")
        assert passo_setup_uv is not None
        self.assertEqual(passo_setup_uv.get("uses"), "astral-sh/setup-uv@v10.3.0")
        with_uv = passo_setup_uv.get("with", {})
        self.assertEqual(with_uv.get("python-arch"), "${{ matrix.arch }}")

        job_publicar = self.conteudo_macos["jobs"]["publicar_macos"]
        self.assertEqual(job_publicar.get("runs-on"), "macos-latest")
        nomes_publicar = [p.get("name", "") for p in job_publicar.get("steps", [])]
        self.assertTrue(
            any("Cloudflare R2" in n for n in nomes_publicar),
            "Deve haver publicação no Cloudflare R2.",
        )

    def test_subaction_macos_utiliza_modulo_dedicado_para_configurar_certificado_apple(
        self,
    ) -> None:
        """Garante que a configuração do certificado Apple no macOS utiliza a biblioteca dedicada para compatibilidade de cifras PBKDF2/Keychain."""
        passos = self.conteudo_macos["jobs"]["compilar_macos"]["steps"]
        passo_cert = next(
            (s for s in passos if "Configurar Certificado Apple Developer ID" in s.get("name", "")),
            None,
        )
        self.assertIsNotNone(
            passo_cert, "Passo de configuração de certificado Apple não encontrado."
        )
        assert passo_cert is not None
        run_cmd = passo_cert.get("run", "")
        self.assertIn("editor.release_tools.configurar_certificado_macos", run_cmd)
        self.assertNotIn("security create-keychain", run_cmd)
        env = passo_cert.get("env", {})
        self.assertEqual(env.get("PYTHONPATH"), ".")

    def test_subaction_macos_disponibiliza_artefatos_dmg_e_outputs(self) -> None:
        """Garante que o sub-workflow build_editor_macos disponibiliza artefatos DMG e appcast.xml no GitHub Actions."""
        passos_compilar = self.conteudo_macos["jobs"]["compilar_macos"].get("steps", [])
        passos_publicar = self.conteudo_macos["jobs"]["publicar_macos"].get("steps", [])
        passos_artifact = [
            s
            for s in (passos_compilar + passos_publicar)
            if "upload-artifact" in str(s.get("uses", ""))
        ]
        self.assertTrue(
            len(passos_artifact) >= 2,
            "Devem existir steps de upload-artifact para o DMG no macOS.",
        )
        caminhos_artefatos = "\n".join(
            str(s.get("with", {}).get("path", "")) for s in passos_artifact
        )
        self.assertIn(
            "*.dmg", caminhos_artefatos, "O arquivo *.dmg deve estar no path do upload-artifact."
        )

    def test_subactions_etapa_testes_configurada_com_offscreen_e_ci(self) -> None:
        """Garante que a etapa de testes nos workflows do macOS e Windows define QT_QPA_PLATFORM offscreen e CI true."""
        for conteudo, nome in [
            (self.conteudo_macos, "build_editor_macos.yml"),
            (self.conteudo_windows, "build_editor_windows.yml"),
        ]:
            job_key = "compilar_macos" if "macos" in nome else "build_windows"
            passos = conteudo["jobs"][job_key]["steps"]
            passo_testes = next((s for s in passos if "Executar Testes" in s.get("name", "")), None)
            self.assertIsNotNone(
                passo_testes, f"Passo 'Executar Testes' não encontrado no workflow {nome}."
            )
            assert passo_testes is not None
            env_vars = passo_testes.get("env", {})
            self.assertEqual(
                env_vars.get("QT_QPA_PLATFORM"),
                "offscreen",
                f"O workflow {nome} deve definir QT_QPA_PLATFORM como 'offscreen' para evitar falhas gráficas.",
            )
            self.assertEqual(
                str(env_vars.get("CI", "")).lower(),
                "true",
                f"O workflow {nome} deve definir CI=true.",
            )

    def test_passo_download_sparkle_obtem_versao_mais_recente_dinamicamente(self) -> None:
        """Garante que o Sparkle é baixado em sua versão mais recente via gh release download sem versão fixa."""
        passos = self.conteudo_macos["jobs"]["compilar_macos"]["steps"]
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

    def test_orquestrador_marca_tag_sem_criar_github_release(self) -> None:
        """Garante que o orquestrador cria e faz push da tag Git, mas não cria GitHub Releases nem gera source tarball."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        comandos_run = "\n".join(str(s.get("run", "")) for s in passos)
        self.assertIn("git tag editor-v${{ steps.versao.outputs.versao }}", comandos_run)
        self.assertIn("git push origin editor-v${{ steps.versao.outputs.versao }}", comandos_run)
        self.assertNotIn("gh release create", comandos_run)
        self.assertNotIn("gh release upload", comandos_run)
        self.assertNotIn("source-tarball", comandos_run)

    def test_subaction_linux_nao_publica_github_release_nem_source_tarball(self) -> None:
        """Garante que o build Linux não gera source tarball nem faz upload para GitHub Release."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        comandos_run = "\n".join(str(s.get("run", "")) for s in passos)
        self.assertNotIn("gh release upload", comandos_run)
        self.assertNotIn("source-tarball", comandos_run)

    def test_passo_calcular_versao_exporta_versao_e_tag_name(self) -> None:
        """Garante que o passo 'Calcular Versão de Release' grava versao e tag_name no $GITHUB_OUTPUT."""
        passos = self.conteudo_yaml["jobs"]["prepare_release"]["steps"]
        passo_versao = next((s for s in passos if "Calcular Versão" in s.get("name", "")), None)
        self.assertIsNotNone(passo_versao)
        assert passo_versao is not None
        run_script = passo_versao.get("run", "")
        self.assertIn('echo "versao=$RELEASE_VER" >> $GITHUB_OUTPUT', run_script)
        self.assertIn('echo "tag_name=editor-v$RELEASE_VER" >> $GITHUB_OUTPUT', run_script)

    def test_subactions_possuem_permissao_contents_read(self) -> None:
        """
        Garante que os sub-workflows reutilizáveis possuem permissão restrita 'contents: read'
        para compatibilidade com a invocação pelo orquestrador (autenticando escritas via app-token).
        """
        job_linux = self.conteudo_linux["jobs"]["build_linux"]
        self.assertEqual(job_linux.get("permissions", {}).get("contents"), "read")

        job_windows = self.conteudo_windows["jobs"]["build_windows"]
        self.assertEqual(job_windows.get("permissions", {}).get("contents"), "read")

        job_compilar_macos = self.conteudo_macos["jobs"]["compilar_macos"]
        self.assertEqual(job_compilar_macos.get("permissions", {}).get("contents"), "read")

        job_publicar_macos = self.conteudo_macos["jobs"]["publicar_macos"]
        self.assertEqual(job_publicar_macos.get("permissions", {}).get("contents"), "read")

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

    def test_subaction_linux_instala_ferramentas_e_dependencias_flatpak_com_sudo_para_sistema(
        self,
    ) -> None:
        """Garante que o passo de instalação do Flatpak no Linux utiliza sudo para registrar o Flathub no escopo do sistema."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        passo_flatpak = next((s for s in passos if "Instalar Flatpak" in s.get("name", "")), None)
        self.assertIsNotNone(passo_flatpak, "Passo de instalação de Flatpak não encontrado.")
        assert passo_flatpak is not None
        run_cmd = passo_flatpak.get("run", "")
        self.assertIn("sudo flatpak remote-add", run_cmd)
        self.assertIn("sudo flatpak install", run_cmd)
        self.assertNotIn("--user", run_cmd)
        self.assertIn("/run/user/$(id -u)", run_cmd)

    def test_subaction_linux_exige_chave_gpg_e_falha_se_ausente(self) -> None:
        """Garante que a subaction Linux falha com exit 1 caso a secret ARESTA_FLATPAK_GPG_PRIVATE_KEY esteja ausente."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        passo_gpg = next((s for s in passos if "Configurar Chave GPG" in s.get("name", "")), None)
        self.assertIsNotNone(passo_gpg, "Passo de configuração de GPG não encontrado.")
        assert passo_gpg is not None
        run_cmd = passo_gpg.get("run", "")
        self.assertIn('-z "$GPG_PRIVATE_KEY"', run_cmd)
        self.assertIn("exit 1", run_cmd)
        self.assertNotIn("Repositório será gerado sem assinatura GPG", run_cmd)

    def test_subaction_linux_passa_gpg_sign_no_flatpak_builder_e_no_update_repo(self) -> None:
        """Garante que flatpak-builder e flatpak build-update-repo assinam commits e índices com a chave GPG."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        passo_builder = next(
            (
                s
                for s in passos
                if "flatpak-github-actions/flatpak-builder" in str(s.get("uses", ""))
            ),
            None,
        )
        self.assertIsNotNone(passo_builder)
        assert passo_builder is not None
        self.assertEqual(
            passo_builder.get("with", {}).get("gpg-sign"),
            "${{ env.GPG_KEY_ID }}",
            "flatpak-builder deve receber gpg-sign com a chave GPG.",
        )
        self.assertEqual(
            passo_builder.get("with", {}).get("branch"),
            "stable",
            "flatpak-builder deve receber branch: stable explicitamente para evitar fallback para master.",
        )

        passo_update = next(
            (s for s in passos if "Atualizar Índices do Repositório OSTree" in s.get("name", "")),
            None,
        )
        self.assertIsNotNone(passo_update)
        assert passo_update is not None
        run_update = passo_update.get("run", "")
        self.assertIn("--gpg-sign", run_update)
        self.assertNotIn('GPG_OPTS=""', run_update)

    def test_subaction_linux_utiliza_script_dedicado_para_bootstrap_e_publicacao(self) -> None:
        """Garante que bootstrap e publicação no Linux usam o script dedicado publicar_flatpak_cli.py sem scripts inline."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        passo_bootstrap = next(
            (s for s in passos if "Configurar Chave GPG" in s.get("name", "")), None
        )
        self.assertIsNotNone(passo_bootstrap)
        assert passo_bootstrap is not None
        run_boot = passo_bootstrap.get("run", "")
        self.assertIn("editor/release_tools/publicar_flatpak_cli.py bootstrap", run_boot)
        self.assertNotIn("python3 -c", run_boot)

        passo_publicar = next(
            (s for s in passos if "Publicar Repositório Flatpak" in s.get("name", "")), None
        )
        self.assertIsNotNone(passo_publicar)
        assert passo_publicar is not None
        run_pub = passo_publicar.get("run", "")
        self.assertIn("editor/release_tools/publicar_flatpak_cli.py publicar", run_pub)
        self.assertNotIn("python3 -c", run_pub)

    def test_subaction_linux_empacota_bundle_flatpak_e_disponibiliza_artefato_sem_incluir_na_release(
        self,
    ) -> None:
        """Garante que o bundle .flatpak é gerado assinado, disponibilizado como artefato/output e não anexado à release do GitHub."""
        passos = self.conteudo_linux["jobs"]["build_linux"]["steps"]
        passo_bundle = next(
            (s for s in passos if "Gerar Pacote Flatpak Bundle" in s.get("name", "")), None
        )
        self.assertIsNotNone(passo_bundle, "Passo de gerar bundle Flatpak não encontrado.")
        assert passo_bundle is not None
        run_bundle = passo_bundle.get("run", "")
        self.assertIn("editor/release_tools/publicar_flatpak_cli.py empacotar", run_bundle)
        self.assertIn("--chave-gpg-id", run_bundle)
        self.assertEqual(
            passo_bundle.get("env", {}).get("PYTHONPATH"),
            ".",
            "Passo de gerar bundle Flatpak deve definir PYTHONPATH: .",
        )

        # Valida que o bundle .flatpak está nos artefatos disponibilizados no GitHub Actions
        passos_artifact = [s for s in passos if "upload-artifact" in str(s.get("uses", ""))]
        self.assertTrue(len(passos_artifact) > 0, "Deve haver step de upload-artifact.")
        caminhos_artefatos = "\n".join(
            str(s.get("with", {}).get("path", "")) for s in passos_artifact
        )
        self.assertIn(
            "*.flatpak",
            caminhos_artefatos,
            "O bundle .flatpak deve estar no path do upload-artifact.",
        )

        # Valida que o bundle .flatpak NÃO é enviado para a release oficial do GitHub
        passo_release = next(
            (s for s in passos if "gh release upload" in str(s.get("run", ""))), None
        )
        if passo_release:
            run_release = passo_release.get("run", "")
            self.assertNotIn(
                ".flatpak",
                run_release,
                "O bundle .flatpak não deve ser enviado na release do GitHub.",
            )
