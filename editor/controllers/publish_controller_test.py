# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QLabel

from editor.controllers.publish_controller import PublishController, DialogoSucessoPR
from editor.views.publish_dialog import PublishDialog

class TestPublishController(unittest.TestCase):
    """Testes de integração para o PublishController."""

    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.workspace_mock = MagicMock()
        self.auth_mock = MagicMock()
        self.historico_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.parent_mock = MagicMock()

        # Configura o histórico e compilação como limpos por padrão
        self.historico_mock.obter_pilha().isClean.return_value = True
        self.auth_mock.recuperar_token.return_value = "fake_token"
        self.workspace_mock.processar_renomeacao_e_compilacao.return_value = (Path("/fake"), [])
        self.workspace_mock.obter_caminho_database.return_value = Path("/fake/database")
        self.workspace_mock.caminho_raiz = None

        self.controller = PublishController(
            workspace=self.workspace_mock,
            auth=self.auth_mock,
            historico=self.historico_mock,
            storage=self.storage_mock,
            parent=self.parent_mock
        )

    def test_dialogo_sucesso_pr_abrir_link(self):
        """Testa abertura de link no DialogoSucessoPR."""
        dialogo = DialogoSucessoPR(pr_url="https://github.com/fake/pr/1")
        with patch("editor.controllers.publish_controller.QDesktopServices.openUrl") as mock_open:
            dialogo.abrir_link()
            mock_open.assert_called_once()
            args, _ = mock_open.call_args
            self.assertEqual(args[0].toString(), "https://github.com/fake/pr/1")

    def test_ler_salvar_meta_experimental_sem_caminho_raiz(self):
        """Testa _ler e _salvar_meta_experimental quando workspace não tem caminho_raiz."""
        self.controller.workspace = MagicMock(spec=[])
        self.assertEqual(self.controller._ler_meta_experimental(), {})
        # Não deve lançar erro ao salvar
        self.controller._salvar_meta_experimental({"teste": 1})

    def test_ler_salvar_meta_experimental_com_arquivo(self):
        """Testa leitura e escrita no arquivo croqui_experimental.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            self.controller.workspace.caminho_raiz = tmp_path
            
            # Inicialmente vazio
            self.assertEqual(self.controller._ler_meta_experimental(), {})
            
            # Salva dados
            meta_dados = {"pull_request_branch": "branch1", "pull_request_url": "url1"}
            self.controller._salvar_meta_experimental(meta_dados)
            
            # Lê de volta
            lido = self.controller._ler_meta_experimental()
            self.assertEqual(lido, meta_dados)

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_nao_deve_publicar_se_nao_autenticado(self, messagebox_mock):
        """Se auth ou workspace não existirem, não deve prosseguir."""
        self.controller.auth = None
        self.controller.iniciar_publicacao()
        self.historico_mock.obter_pilha().isClean.assert_not_called()

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_deve_perguntar_salvamento_se_historico_sujo(self, messagebox_mock):
        """Se o histórico tiver modificações, deve perguntar se quer salvar."""
        self.historico_mock.obter_pilha().isClean.return_value = False
        messagebox_mock.question.return_value = messagebox_mock.StandardButton.Cancel

        self.controller.iniciar_publicacao()

        messagebox_mock.question.assert_called_once()
        self.parent_mock.salvar_croqui.assert_not_called()

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_deve_salvar_e_prosseguir_se_usuario_confirmar_salvamento(self, messagebox_mock):
        """Se o usuário clicar em Salvar no diálogo de histórico sujo, deve acionar salvar_croqui."""
        self.historico_mock.obter_pilha().isClean.return_value = False
        messagebox_mock.question.return_value = messagebox_mock.StandardButton.Save

        with patch.object(self.controller, "_prosseguir_publicacao") as mock_prosseguir:
            def mock_salvar(callback_sucesso=None):
                if callback_sucesso:
                    callback_sucesso()
            self.parent_mock.salvar_croqui.side_effect = mock_salvar

            self.controller.iniciar_publicacao()

            self.parent_mock.salvar_croqui.assert_called_once()
            mock_prosseguir.assert_called_once()

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    def test_deve_abrir_dialogo_se_pr_nao_existe(self, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se o croqui não tem PR aberta, deve pedir título e descrição."""
        ler_meta_mock.return_value = {}
        self.controller.croqui_data = {"id": "novo_croqui"}
        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.return_value = 1  # Accepted
        dialog_mock.obter_dados.return_value = {"titulo": "Test", "descricao": "Desc"}

        with patch("editor.controllers.publish_controller.TarefaPublicacao") as tarefa_mock_class:
            tarefa_mock = tarefa_mock_class.return_value
            self.controller.iniciar_publicacao()

            dialog_mock_class.assert_called_once()
            dialog_mock.exec.assert_called_once()
            tarefa_mock_class.assert_called_once()
            tarefa_mock.start.assert_called_once()

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.requests.get")
    def test_deve_pular_dialogo_se_pr_ja_existe_e_esta_aberta(self, mock_requests_get, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se o croqui já tem PR aberta, não deve pedir título de novo, vai atualizar silenciosamente."""
        ler_meta_mock.return_value = {
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/1"
        }
        self.controller.croqui_data = {
            "id": "meu_croqui"
        }
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"state": "open"}
        mock_requests_get.return_value = mock_resp
        
        with patch("editor.controllers.publish_controller.TarefaPublicacao") as tarefa_mock_class:
            tarefa_mock = tarefa_mock_class.return_value
            self.controller.iniciar_publicacao()

            dialog_mock_class.assert_not_called() # Não abriu diálogo!
            tarefa_mock_class.assert_called_once()
            
            # A tarefa deve ser iniciada com modo atualização
            args, kwargs = tarefa_mock_class.call_args
            self.assertTrue(kwargs.get("modo_atualizacao", False))
            tarefa_mock.start.assert_called_once()

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.requests.get")
    def test_prosseguir_publicacao_erro_api_github_continua_aberto(self, mock_requests_get, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se der erro ao verificar status do PR no GitHub, trata exceção e continua."""
        ler_meta_mock.return_value = {
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/1"
        }
        self.controller.croqui_data = {"id": "meu_croqui"}
        
        mock_requests_get.side_effect = Exception("API rate limit ou network error")
        
        with patch("editor.controllers.publish_controller.TarefaPublicacao") as tarefa_mock_class:
            self.controller._prosseguir_publicacao()
            tarefa_mock_class.assert_called_once()

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.PublishController._salvar_meta_experimental")
    @patch("editor.controllers.publish_controller.requests.get")
    def test_deve_abrir_dialogo_se_pr_fechado_ou_merged(self, mock_requests_get, salvar_meta_mock, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se o PR já existe mas foi fechado ou merged, deve pedir título para novo PR e limpar o meta antigo."""
        ler_meta_mock.return_value = {
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/1",
            "pull_request_fork_owner": "renato"
        }
        self.controller.croqui_data = {
            "id": "meu_croqui"
        }
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"state": "closed"}
        mock_requests_get.return_value = mock_resp
        
        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.return_value = 1  # Accepted
        dialog_mock.obter_dados.return_value = {"titulo": "Test", "descricao": "Desc"}

        with patch("editor.controllers.publish_controller.TarefaPublicacao") as tarefa_mock_class:
            tarefa_mock = tarefa_mock_class.return_value
            self.controller.iniciar_publicacao()

            # Deve limpar meta
            salvar_meta_mock.assert_called_once_with({})
            
            dialog_mock_class.assert_called_once()
            dialog_mock.exec.assert_called_once()
            tarefa_mock_class.assert_called_once()
            
            # A tarefa deve ser iniciada com modo atualização FALSO
            args, kwargs = tarefa_mock_class.call_args
            self.assertFalse(kwargs.get("modo_atualizacao", True))
            tarefa_mock.start.assert_called_once()

    @patch("editor.controllers.publish_controller.DialogoSucessoPR")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.PublishController._salvar_meta_experimental")
    def test_on_sucesso_deve_exibir_dialogo_sucesso(self, salvar_meta_mock, ler_meta_mock, dialog_mock_class):
        """No sucesso, deve salvar yaml direto e abrir DialogoSucessoPR."""
        ler_meta_mock.return_value = {}
        self.controller.croqui_data = {"id": "meu_croqui"}
        
        self.controller._on_sucesso("https://github.com/fake/pr/1", "minha_branch", "renato")
        
        salvar_meta_mock.assert_called_once()
        dados_salvos = salvar_meta_mock.call_args[0][0]
        self.assertEqual(dados_salvos["pull_request_url"], "https://github.com/fake/pr/1")
        
        # Verifica se o dialogo foi aberto com a mensagem de criacao
        dialog_mock_class.assert_called_once_with(
            "https://github.com/fake/pr/1", 
            self.parent_mock, 
            titulo="Sucesso", 
            mensagem_personalizada="Proposta de mudança publicada com sucesso!"
        )

    @patch("editor.controllers.publish_controller.DialogoSucessoPR")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.PublishController._salvar_meta_experimental")
    def test_on_sucesso_deve_exibir_dialogo_sucesso_para_atualizacao(self, salvar_meta_mock, ler_meta_mock, dialog_mock_class):
        """Ao receber 'atualizado', deve ler a URL original do YAML e usar msg de atualizacao."""
        ler_meta_mock.return_value = {"pull_request_url": "https://github.com/fake/pr/existente"}
        self.controller.croqui_data = {"id": "meu_croqui"}
    
        self.controller._on_sucesso("atualizado", "branch_existente", "renato")
    
        salvar_meta_mock.assert_called_once()
        dados_salvos = salvar_meta_mock.call_args[0][0]
        self.assertEqual(dados_salvos["pull_request_branch"], "branch_existente")
        self.assertEqual(dados_salvos["pull_request_fork_owner"], "renato")
        self.assertEqual(dados_salvos["pull_request_url"], "https://github.com/fake/pr/existente")
    
        dialog_mock_class.assert_called_once_with(
            "https://github.com/fake/pr/existente", 
            self.parent_mock, 
            titulo="Sucesso", 
            mensagem_personalizada="Proposta de mudança atualizada com sucesso!"
        )
        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.assert_called_once()

    @patch("editor.controllers.publish_controller.DialogoSucessoPR")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    def test_on_aviso_deve_exibir_dialogo_sucesso(self, ler_meta_mock, dialog_mock_class):
        """Quando ocorre aviso, deve exibir o DialogoSucessoPR mas com mensagem de aviso."""
        ler_meta_mock.return_value = {"pull_request_url": "https://github.com/fake/pr/1"}
        
        # Simula progresso instanciado
        self.controller.progresso_pr = MagicMock()
        
        mensagem_aviso = "Nenhuma alteração foi detectada."
        self.controller._on_aviso(mensagem_aviso)
        
        self.controller.progresso_pr.close.assert_called_once()
        
        dialog_mock_class.assert_called_once_with(
            "https://github.com/fake/pr/1", 
            self.parent_mock, 
            titulo="Tudo Atualizado", 
            mensagem_personalizada=mensagem_aviso
        )
        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.assert_called_once()

    @patch("editor.controllers.publish_controller.DialogoSucessoPR")
    @patch("editor.controllers.publish_controller.QMessageBox")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    def test_on_aviso_sem_pr_url_exibe_information(self, ler_meta_mock, messagebox_mock, dialog_mock_class):
        """Testa aviso sem PR salvo exibindo QMessageBox.information."""
        ler_meta_mock.return_value = {}
        self.controller.progresso_pr = MagicMock()

        self.controller._on_aviso("Aviso sem PR")

        messagebox_mock.information.assert_called_once_with(
            self.parent_mock, "Tudo Atualizado", "Aviso sem PR"
        )

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_on_erro_exibe_critical(self, messagebox_mock):
        """Testa exibição de erro crítico no callback _on_erro."""
        self.controller.progresso_pr = MagicMock()
        self.controller._on_erro("Erro de teste na publicação")
        messagebox_mock.critical.assert_called_once_with(
            self.parent_mock, "Erro na Publicação", "Falha ao enviar proposta de mudança:\nErro de teste na publicação"
        )

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_on_erro_sessao_expirada_exibe_warning(self, messagebox_mock):
        """Testa exibição de warning quando a sessão do usuário estiver expirada."""
        self.controller.progresso_pr = MagicMock()
        self.controller._on_erro("Sessão expirada. Por favor, entre novamente no app.")
        messagebox_mock.warning.assert_called_once()
        self.assertIn("Sessão Expirada", messagebox_mock.warning.call_args[0][1])

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_iniciar_publicacao_bloqueia_quando_detectada_atualizacao_na_store(self, messagebox_mock):
        """Se o ServicoLoja detectar nova versão, deve bloquear a publicação e permitir atualizar."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        
        self.controller.servico_loja = MagicMock()
        res = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            versao_disponivel="2.0.0.0"
        )
        self.controller.servico_loja.verificar_atualizacoes_disponiveis.return_value = res
        
        # Simula usuário clicando no botão de atualizar (Sim/Ok)
        messagebox_mock.warning.return_value = messagebox_mock.StandardButton.Ok

        self.controller.iniciar_publicacao()

        self.controller.servico_loja.verificar_atualizacoes_disponiveis.assert_called_once()
        messagebox_mock.warning.assert_called_once()
        self.controller.servico_loja.solicitar_instalacao_atualizacao.assert_called_once_with(res)
        # O histórico nem deve ter sido checado para salvar
        self.historico_mock.obter_pilha().isClean.assert_not_called()

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_iniciar_publicacao_bloqueia_e_cancela_se_usuario_recusar_atualizar(self, messagebox_mock):
        """Se o usuário cancelar o diálogo de atualização da Store, não chama a instalação."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        
        self.controller.servico_loja = MagicMock()
        res = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            versao_disponivel="2.0.0.0"
        )
        self.controller.servico_loja.verificar_atualizacoes_disponiveis.return_value = res
        
        # Simula usuário clicando em Cancelar
        messagebox_mock.warning.return_value = messagebox_mock.StandardButton.Cancel

        self.controller.iniciar_publicacao()

        messagebox_mock.warning.assert_called_once()
        self.controller.servico_loja.solicitar_instalacao_atualizacao.assert_not_called()
        self.historico_mock.obter_pilha().isClean.assert_not_called()

    @patch.object(PublishController, "_prosseguir_publicacao")
    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_iniciar_publicacao_bypass_quando_fora_da_store(self, messagebox_mock, mock_prosseguir):
        """Quando fora da Store (NAO_APLICAVEL), deve prosseguir com a verificação de histórico/salvamento."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        
        self.controller.servico_loja = MagicMock()
        self.controller.servico_loja.verificar_atualizacoes_disponiveis.return_value = ResultadoAtualizacao(
            status=StatusAtualizacao.NAO_APLICAVEL
        )
        
        self.controller.iniciar_publicacao()

        self.controller.servico_loja.verificar_atualizacoes_disponiveis.assert_called_once()
        # Segue para checar o histórico e prosseguir normalmente
        self.historico_mock.obter_pilha().isClean.assert_called_once()
        mock_prosseguir.assert_called_once()

    @patch.object(PublishController, "_prosseguir_publicacao")
    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_iniciar_publicacao_bypass_em_erro_de_conexao(self, messagebox_mock, mock_prosseguir):
        """Em caso de falha de conexão na checagem da Store (ERRO_CHECAGEM), concede fallback aberto."""
        from editor.core.servico_loja import ResultadoAtualizacao, StatusAtualizacao
        
        self.controller.servico_loja = MagicMock()
        self.controller.servico_loja.verificar_atualizacoes_disponiveis.return_value = ResultadoAtualizacao(
            status=StatusAtualizacao.ERRO_CHECAGEM,
            mensagem="Timeout"
        )
        
        self.controller.iniciar_publicacao()

        self.controller.servico_loja.verificar_atualizacoes_disponiveis.assert_called_once()
        self.historico_mock.obter_pilha().isClean.assert_called_once()
        mock_prosseguir.assert_called_once()

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_iniciar_publicacao_bloqueia_se_houver_erro_de_compilacao(self, messagebox_mock):
        """Se a compilação do croqui falhar com erro, deve exibir critical e não prosseguir."""
        self.controller.workspace.processar_renomeacao_e_compilacao.return_value = (
            Path("/fake"),
            ["[ERRO] Campo obrigatório ausente no croqui.yaml"]
        )
        self.controller.croqui_data = {"id": "meu_croqui"}

        with patch.object(self.controller, "_prosseguir_publicacao") as mock_prosseguir:
            self.controller.iniciar_publicacao()

            messagebox_mock.critical.assert_called_once()
            self.assertIn("possui erros de compilação", messagebox_mock.critical.call_args[0][2])
            mock_prosseguir.assert_not_called()

    @patch("editor.controllers.publish_controller.QMessageBox")
    def test_iniciar_publicacao_bloqueia_se_compilacao_lancar_excecao(self, messagebox_mock):
        """Se a compilação lançar exceção, deve exibir critical e bloquear."""
        self.controller.workspace.processar_renomeacao_e_compilacao.side_effect = Exception("Falha grave de parser")
        self.controller.croqui_data = {"id": "meu_croqui"}

        with patch.object(self.controller, "_prosseguir_publicacao") as mock_prosseguir:
            self.controller.iniciar_publicacao()

            messagebox_mock.critical.assert_called_once()
            self.assertIn("Falha ao validar compilação", messagebox_mock.critical.call_args[0][2])
            mock_prosseguir.assert_not_called()

    def test_obter_resumo_arquivos_com_servico_injetado(self):
        """Testa _obter_resumo_arquivos delegando para servico_submissao."""
        self.controller.servico_submissao = MagicMock()
        self.controller.servico_submissao.obter_arquivos_modificados.return_value = [
            "croqui.yaml",
            "imagens/nova_foto.jpg"
        ]
        self.controller.croqui_data = {"id": "meu_croqui"}
        self.controller.workspace.obter_caminho_database.return_value = Path("/fake/dir")

        with patch("pathlib.Path.is_dir", return_value=True):
            resumo = self.controller._obter_resumo_arquivos()
            self.assertEqual(resumo, ["croqui.yaml", "imagens/nova_foto.jpg"])
            self.controller.servico_submissao.obter_arquivos_modificados.assert_called_once_with(
                Path("/fake/dir"), "meu_croqui"
            )

    def test_obter_resumo_arquivos_com_storage_fallback(self):
        """Testa instanciação automática de ServicoSubmissao a partir do storage."""
        self.controller.servico_submissao = None
        self.controller.storage.obter_caminho_base_repo.return_value = Path("/fake/repo")
        self.controller.croqui_data = {"id": "meu_croqui"}
        self.controller.workspace.obter_caminho_database.return_value = Path("/fake/dir")

        with patch("pathlib.Path.is_dir", return_value=True):
            with patch("editor.core.servico_submissao.ServicoSubmissao.obter_arquivos_modificados", return_value=["croqui.yaml"]):
                resumo = self.controller._obter_resumo_arquivos()
                self.assertEqual(resumo, ["croqui.yaml"])

    def test_obter_resumo_arquivos_sem_database_ou_id(self):
        """Testa retorno vazio quando caminho_db ou id_croqui não existem."""
        self.controller.croqui_data = None
        self.controller.workspace.caminho_raiz = None
        self.controller.workspace.obter_caminho_database.return_value = None
        self.assertEqual(self.controller._obter_resumo_arquivos(), [])

        # Sem método obter_caminho_database no workspace
        self.controller.workspace = MagicMock(spec=[])
        self.assertEqual(self.controller._obter_resumo_arquivos(), [])

        # caminho_db não é diretório
        self.controller.workspace = MagicMock()
        self.controller.workspace.obter_caminho_database.return_value = Path("/nao_diretorio")
        with patch("pathlib.Path.is_dir", return_value=False):
            self.assertEqual(self.controller._obter_resumo_arquivos(), [])

        # storage sem obter_caminho_base_repo
        self.controller.croqui_data = {"id": "croqui"}
        self.controller.servico_submissao = None
        self.controller.storage = MagicMock(spec=[])
        with patch("pathlib.Path.is_dir", return_value=True):
            self.assertEqual(self.controller._obter_resumo_arquivos(), [])

    def test_publish_dialog_com_resumo_arquivos(self):
        """Testa instanciação do PublishDialog com lista de arquivos e DCO."""
        dialogo = PublishDialog(
            titulo_padrao="Meu Croqui",
            resumo_arquivos=["croqui.yaml", "foto.jpg"],
        )
        self.assertEqual(dialogo.windowTitle(), "Enviar Proposta de Mudança")
        self.assertEqual(dialogo.edit_titulo.text(), "Croqui: Meu Croqui")
        dados = dialogo.obter_dados()
        self.assertEqual(dados["titulo"], "Croqui: Meu Croqui")

        # Verifica se o link do DCO aponta para CONTRIBUINDO.md
        labels = [c for c in dialogo.findChildren(QLabel) if "CONTRIBUINDO.md" in c.text()]
        self.assertTrue(len(labels) > 0)
        self.assertIn("https://github.com/aresta-climb/aresta_db/blob/main/CONTRIBUINDO.md", labels[0].text())

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.PublishController._salvar_meta_experimental")
    @patch("editor.controllers.publish_controller.requests.get")
    def test_deve_abrir_dialogo_se_pr_retornar_404(self, mock_requests_get, salvar_meta_mock, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se o status do PR retornar 404 na API pública, trata como fechado e abre diálogo."""
        ler_meta_mock.return_value = {
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/999"
        }
        self.controller.croqui_data = {"id": "meu_croqui"}
        
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_requests_get.return_value = mock_resp
        
        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.return_value = 1
        dialog_mock.obter_dados.return_value = {"titulo": "Test", "descricao": "Desc"}

        with patch("editor.controllers.publish_controller.TarefaPublicacao") as tarefa_mock_class:
            self.controller.iniciar_publicacao()
            salvar_meta_mock.assert_called_once_with({})
            dialog_mock_class.assert_called_once()

    def test_init_com_auth_none_instancia_gerenciador_sessao(self):
        """PublishController(workspace, auth=None) deve instanciar GerenciadorSessao padrão."""
        controller = PublishController(
            workspace=self.workspace_mock,
            auth=None,
            historico=self.historico_mock,
            storage=self.storage_mock,
            parent=self.parent_mock
        )
        self.assertIsNotNone(controller.auth)

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.TarefaPublicacao")
    def test_prosseguir_publicacao_com_obter_sessao(self, tarefa_mock_class, dialog_mock_class, progress_mock):
        """Testa _prosseguir_publicacao quando auth tem método obter_sessao."""
        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.return_value = 1
        dialog_mock.obter_dados.return_value = {"titulo": "T", "descricao": "D"}
        
        mock_sessao = MagicMock()
        mock_sessao.jwt_supabase = "jwt_ativo"
        self.controller.auth = MagicMock(spec=["obter_sessao"])
        self.controller.auth.obter_sessao.return_value = mock_sessao

        self.controller._prosseguir_publicacao()
        
        args, kwargs = tarefa_mock_class.call_args
        self.assertEqual(kwargs.get("token"), "jwt_ativo")
        self.assertEqual(kwargs.get("sessao"), mock_sessao)

    @patch("editor.controllers.publish_controller.QProgressDialog")
    @patch("editor.controllers.publish_controller.PublishDialog")
    @patch("editor.controllers.publish_controller.TarefaPublicacao")
    def test_prosseguir_publicacao_sem_croqui_data_usa_caminho_raiz(self, tarefa_mock_class, dialog_mock_class, progress_mock):
        """Quando croqui_data é None, usa o nome do caminho_raiz."""
        self.controller.croqui_data = None
        self.controller.workspace.caminho_raiz = Path("/caminho/meu_croqui_pasta")
        
        self.controller.auth = MagicMock(spec=["obter_sessao"])
        self.controller.auth.obter_sessao.return_value = None

        dialog_mock = dialog_mock_class.return_value
        dialog_mock.exec.return_value = 1
        dialog_mock.obter_dados.return_value = {"titulo": "T", "descricao": "D"}

        self.controller._prosseguir_publicacao()
        
        # Verifica se o diálogo foi chamado com o nome da pasta como título padrão
        dialog_mock_class.assert_called_once_with(
            titulo_padrao="meu_croqui_pasta",
            resumo_arquivos=unittest.mock.ANY,
            parent=self.parent_mock
        )

if __name__ == "__main__":
    unittest.main()
