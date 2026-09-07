# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from editor.core.storage import GerenciadorCaminhos, obter_diretorio_base_app

class TestStorage(unittest.TestCase):
    @patch("PySide6.QtCore.QStandardPaths.writableLocation")
    def test_obter_diretorio_base_app_via_qstandardpaths(self, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata/EditorAresta"
        caminho = obter_diretorio_base_app()
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/EditorAresta")

    @patch("PySide6.QtCore.QStandardPaths.writableLocation", return_value="")
    @patch.dict("os.environ", {"APPDATA": "C:/fake/appdata"})
    def test_obter_diretorio_base_app_fallback_env(self, mock_writable_location):
        caminho = obter_diretorio_base_app()
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/EditorAresta")

    @patch("PySide6.QtCore.QStandardPaths.writableLocation")
    def test_resolver_diretorio_appdata(self, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_diretorio_base()
        
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata")

    @patch("PySide6.QtCore.QStandardPaths.writableLocation")
    def test_obter_caminho_lixeira(self, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_caminho_lixeira()
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/.trash_interna")

    @patch("PySide6.QtCore.QStandardPaths.writableLocation")
    def test_obter_caminho_diarios_locais(self, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        gerenciador = GerenciadorCaminhos()
        caminho = gerenciador.obter_caminho_diarios_locais()
        self.assertEqual(str(caminho).replace("\\", "/"), "C:/fake/appdata/diarios_locais")

    @patch("PySide6.QtCore.QStandardPaths.writableLocation")
    @patch("editor.core.storage.Path.mkdir")
    def test_inicializar_diretorios_cria_pastas(self, mock_mkdir, mock_writable_location):
        mock_writable_location.return_value = "C:/fake/appdata"
        
        gerenciador = GerenciadorCaminhos()
        gerenciador.inicializar_diretorios()
        
        # Deve chamar mkdir para pasta base, base_repo, croquis_experimentais, diarios_locais e .trash_interna
        self.assertGreaterEqual(mock_mkdir.call_count, 5)

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

    def test_obter_caminho_recurso_interno_canal_beta(self):
        """Garante que obter_caminho_recurso_interno prioriza recursos_beta quando em canal Beta."""
        import os
        with patch.dict(os.environ, {"ARESTA_CANAL": "beta"}):
            gerenciador = GerenciadorCaminhos()
            caminho = gerenciador.obter_caminho_recurso_interno("recursos/logo_app.png")
            self.assertIn("recursos_beta", str(caminho).replace("\\", "/"))
            self.assertEqual(caminho.name, "logo_app.png")

    def test_migrar_dados_legados_se_necessario(self):
        """Garante que dados legados de 'Editor Aresta' sejam migrados para a pasta ativa."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            pasta_legada = base_dir / "Editor Aresta"
            pasta_atual = base_dir / "Editor Aresta (Beta)"

            # Prepara estrutura legada
            croqui_legado = pasta_legada / "croquis" / "croqui_teste_123"
            croqui_legado.mkdir(parents=True)
            (croqui_legado / "croqui.yaml").write_text("nome: Teste Legado", encoding="utf-8")
            (pasta_legada / ".sessao_auth.enc").write_text("token_fake_123", encoding="utf-8")

            gerenciador = GerenciadorCaminhos()
            with patch.object(gerenciador, "obter_diretorio_base", return_value=pasta_atual):
                gerenciador.inicializar_diretorios()

                croqui_migrado = pasta_atual / "croquis" / "croqui_teste_123"
                self.assertTrue(croqui_migrado.exists())
                self.assertEqual((croqui_migrado / "croqui.yaml").read_text(encoding="utf-8"), "nome: Teste Legado")
                self.assertTrue((pasta_atual / ".sessao_auth.enc").exists())


if __name__ == "__main__":
    unittest.main()


