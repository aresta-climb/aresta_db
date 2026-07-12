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
    def test_deve_abrir_dialogo_se_pr_nao_existe(self, dialog_mock_class, progress_mock):
        """Se o croqui não tem PR aberta, deve pedir título e descrição."""
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
    def test_deve_pular_dialogo_se_pr_ja_existe_e_esta_aberta(self, dialog_mock_class, progress_mock):
        """Se o croqui já tem PR aberta, não deve pedir título de novo, vai atualizar silenciosamente."""
        self.controller.croqui_data = {
            "id": "meu_croqui",
            "pull_request_branch": "editor/meu_croqui",
            "pull_request_url": "https://github.com/aresta-climb/aresta_db/pull/1"
        }
        
        # Simularemos que o Github API diz que a PR está aberta (Isso seria dentro da TarefaPublicacao, 
        # mas o controller deve passar o estado "atualizar" para a tarefa)
        with patch("editor.controllers.publish_controller.TarefaPublicacao") as tarefa_mock_class:
            tarefa_mock = tarefa_mock_class.return_value
            self.controller.iniciar_publicacao()

            dialog_mock_class.assert_not_called() # Não abriu diálogo!
            tarefa_mock_class.assert_called_once()
            
            # A tarefa deve ser iniciada com modo atualização
            args, kwargs = tarefa_mock_class.call_args
            self.assertTrue(kwargs.get("modo_atualizacao", False))
            tarefa_mock.start.assert_called_once()

if __name__ == "__main__":
    unittest.main()
