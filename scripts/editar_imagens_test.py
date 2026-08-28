# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

# Adiciona o diretório de scripts e a raiz ao path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_script_pode_ser_importado_e_instancia_janela(qtbot):
    with patch("os.path.exists", return_value=True), \
         patch("sys.argv", ["scripts/editar_imagens.py", "dummy_folder"]), \
         patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical"):
        
        # Importação direta do arquivo no diretório scripts
        from editar_imagens import MainWindow
        window = MainWindow("dummy_folder")
        qtbot.addWidget(window)
        assert window.windowTitle().startswith("ARESTA Batch Image Editor")
        assert window.widget is not None

def test_script_uso_sem_argumentos():
    # Teste de fumaça para importação
    import editar_imagens
    assert editar_imagens.MainWindow is not None
