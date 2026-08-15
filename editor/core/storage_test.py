# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

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
        
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata")

    @patch("PyQt6.QtCore.QStandardPaths.writableLocation")
    def test_obter_caminho_lixeira(self, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_caminho_lixeira()
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/.trash_interna")

    @patch("PyQt6.QtCore.QStandardPaths.writableLocation")
    @patch("editor.core.storage.Path.mkdir")
    def test_inicializar_diretorios_cria_pastas(self, mock_mkdir, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        
        gerenciador = GerenciadorCaminhos()
        gerenciador.inicializar_diretorios()
        
        # Deve chamar mkdir para a pasta base, base_repo, croquis_experimentais e .trash_interna
        self.assertGreaterEqual(mock_mkdir.call_count, 4)

    @patch("sys._MEIPASS", "C:/Temp/_MEI12345", create=True)
    def test_obter_caminho_recurso_interno_pyinstaller(self):
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_caminho_recurso_interno("recursos/logo_splash.png")
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/Temp/_MEI12345/recursos/logo_splash.png")

    def test_obter_caminho_recurso_interno_dev_mode(self):
        # Em modo de desenvolvimento normal, sys._MEIPASS não existe
        import sys
        if hasattr(sys, '_MEIPASS'):
            del sys._MEIPASS
            
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_caminho_recurso_interno("recursos/logo_splash.png")
        from editor.core import storage
        esperado = str(Path(storage.__file__).resolve().parent.parent / "recursos/logo_splash.png")
        self.assertEqual(str(caminho), esperado)

if __name__ == "__main__":
    unittest.main()
