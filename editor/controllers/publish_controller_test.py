# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import unittest
from unittest.mock import MagicMock, patch

from editor.controllers.publish_controller import PublishController

class TestPublishController(unittest.TestCase):
    """Testes de integração para o PublishController."""

    def setUp(self):
        self.workspace_mock = MagicMock()
        self.auth_mock = MagicMock()
        self.historico_mock = MagicMock()
        self.storage_mock = MagicMock()
        self.parent_mock = MagicMock()

        # Configura o histórico como limpo por padrão
        self.historico_mock.obter_pilha().isClean.return_value = True
        self.auth_mock.recuperar_token.return_value = "fake_token"

        self.controller = PublishController(
            workspace=self.workspace_mock,
            auth=self.auth_mock,
            historico=self.historico_mock,
            storage=self.storage_mock,
            parent=self.parent_mock
        )

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
    @patch("editor.controllers.publish_controller.github.Github")
    def test_deve_pular_dialogo_se_pr_ja_existe_e_esta_aberta(self, github_mock_class, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se o croqui já tem PR aberta, não deve pedir título de novo, vai atualizar silenciosamente."""
        ler_meta_mock.return_value = {
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/1"
        }
        self.controller.croqui_data = {
            "id": "meu_croqui"
        }
        
        mock_g = github_mock_class.return_value
        mock_repo = mock_g.get_repo.return_value
        mock_pr = mock_repo.get_pull.return_value
        mock_pr.state = "open"
        
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
    @patch("editor.controllers.publish_controller.PublishController._salvar_meta_experimental")
    @patch("editor.controllers.publish_controller.github.Github")
    def test_deve_abrir_dialogo_se_pr_fechado_ou_merged(self, github_mock_class, salvar_meta_mock, ler_meta_mock, dialog_mock_class, progress_mock):
        """Se o PR já existe mas foi fechado ou merged, deve pedir título para novo PR e limpar o meta antigo."""
        ler_meta_mock.return_value = {
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/1",
            "pull_request_fork_owner": "renato"
        }
        self.controller.croqui_data = {
            "id": "meu_croqui"
        }
        
        mock_g = github_mock_class.return_value
        mock_repo = mock_g.get_repo.return_value
        mock_pr = mock_repo.get_pull.return_value
        mock_pr.state = "closed"
        
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
            mensagem_personalizada="Pull Request publicada com sucesso!"
        )

    @patch("editor.controllers.publish_controller.DialogoSucessoPR")
    @patch("editor.controllers.publish_controller.PublishController._ler_meta_experimental")
    @patch("editor.controllers.publish_controller.PublishController._salvar_meta_experimental")
    def test_on_sucesso_deve_exibir_dialogo_sucesso_para_atualizacao(self, salvar_meta_mock, ler_meta_mock, dialog_mock_class):
        """Ao receber 'atualizado', deve ler a URL original do YAML e usar msg de atualizacao."""
        ler_meta_mock.return_value = {"pull_request_url": "https://github.com/fake/pr/existente"}
        self.controller.croqui_data = {"id": "meu_croqui"}
    
        self.controller._on_sucesso("atualizado", "atualizado", "atualizado")
    
        salvar_meta_mock.assert_not_called()
    
        dialog_mock_class.assert_called_once_with(
            "https://github.com/fake/pr/existente", 
            self.parent_mock, 
            titulo="Sucesso", 
            mensagem_personalizada="Pull Request atualizado com sucesso!"
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

if __name__ == "__main__":
    unittest.main()
