import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from editor.core.storage import GerenciadorCaminhos

class TestStorage(unittest.TestCase):
    @patch("PyQt6.QtCore.QStandardPaths.writableLocation")
    def test_resolver_diretorio_appdata(self, mock_writable_location):
        # Configura o mock para retornar um caminho fictício
        mock_writable_location.return_value = "C:/fake/appdata"
        
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_diretorio_base()
        
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/aresta_editor")

    @patch("PyQt6.QtCore.QStandardPaths.writableLocation")
    def test_obter_caminho_lixeira(self, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_caminho_lixeira()
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/aresta_editor/.trash_interna")

    @patch("PyQt6.QtCore.QStandardPaths.writableLocation")
    @patch("editor.core.storage.Path.mkdir")
    def test_inicializar_diretorios_cria_pastas(self, mock_mkdir, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        
        gerenciador = GerenciadorCaminhos()
        gerenciador.inicializar_diretorios()
        
        # Deve chamar mkdir para a pasta base, base_repo, croquis_experimentais e .trash_interna
        self.assertGreaterEqual(mock_mkdir.call_count, 4)

if __name__ == "__main__":
    unittest.main()
