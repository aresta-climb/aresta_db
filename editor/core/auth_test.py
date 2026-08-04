import unittest
from unittest.mock import patch, MagicMock
from editor.core.auth import GerenciadorAutenticacao

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.auth = GerenciadorAutenticacao(id_cliente="fake_id")

    @patch("requests.post")
    def test_solicitar_codigo_dispositivo(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "device_code": "dev123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5
        }
        mock_post.return_value = mock_response
        
        dados = self.auth.solicitar_codigo_dispositivo()
        
        self.assertEqual(dados["user_code"], "ABCD-1234")
        self.assertEqual(self.auth.codigo_dispositivo, "dev123")

    @patch("requests.post")
    def test_aguardar_token_sucesso(self, mock_post):
        self.auth.codigo_dispositivo = "dev123"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_token123",
            "token_type": "bearer",
            "scope": "repo"
        }
        mock_post.return_value = mock_response
        
        token = self.auth.aguardar_token(tempo_limite=1)
        self.assertEqual(token, "gho_token123")

    @patch("requests.post")
    def test_aguardar_token_pendente(self, mock_post):
        self.auth.codigo_dispositivo = "dev123"
        
        # Simula uma resposta de "authorization_pending" seguida de sucesso
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "authorization_pending"}
        mock_post.return_value = mock_response
        
        # Testar apenas uma iteração para não travar o teste
        token = self.auth.aguardar_token(tempo_limite=0.1, intervalo_poll=0.05)
        self.assertIsNone(token)

    @patch("keyring.set_password")
    def test_salvar_token(self, mock_set):
        self.auth.salvar_token("token123")
        mock_set.assert_called_with("editor_aresta", "github_token", "token123")

    @patch("keyring.get_password")
    def test_recuperar_token(self, mock_get):
        mock_get.return_value = "token123"
        token = self.auth.recuperar_token()
        self.assertEqual(token, "token123")
        mock_get.assert_called_with("editor_aresta", "github_token")

    @patch("github.Github")
    def test_validar_token_sucesso(self, mock_github):
        mock_instance = mock_github.return_value
        mock_usuario = mock_instance.get_user.return_value
        mock_usuario.login = "renato"
        
        valido = self.auth.validar_token("token123")
        self.assertTrue(valido)
        self.assertEqual(self.auth.usuario_logado, "renato")

    @patch("github.Github")
    def test_validar_token_falha(self, mock_github):
        mock_instance = mock_github.return_value
        mock_instance.get_user.side_effect = Exception("Invalid token")
        
        valido = self.auth.validar_token("token_ruim")
        self.assertFalse(valido)

if __name__ == "__main__":
    unittest.main()
