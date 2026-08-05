# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
import os
from PyQt6.QtWidgets import QApplication
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_folder(tmp_path):
    imagens_dir = tmp_path / "imagens"
    imagens_dir.mkdir()
    (imagens_dir / "imagem1.webp").write_text("dummy")
    return str(tmp_path)

def test_widget_inicializa_em_modo_integrado(qtbot, mock_folder):
    # O widget deve aceitar o modo_integrado no construtor
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder, modo_integrado=True)
        qtbot.addWidget(widget)
        
        # Verifica se o botão de salvar está oculto
        assert widget.save_btn.isHidden()

def test_widget_inicializa_em_modo_autonomo(qtbot, mock_folder):
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder, modo_integrado=False)
        qtbot.addWidget(widget)
        
        # Verifica se o botão de salvar está visível
        assert not widget.save_btn.isHidden()

def test_widget_lista_imagens_da_pasta(qtbot, mock_folder):
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder)
        qtbot.addWidget(widget)
        
        assert widget.list_widget.count() == 1
        assert "imagem1.webp" in widget.list_widget.item(0).text()

def test_widget_expoe_metodo_salvar_alteracoes(qtbot, mock_folder):
    with patch("editor.legacy_views.widget_editor_imagens.QMessageBox.critical") as mock_critical:
        widget = WidgetEditorImagens(mock_folder)
        qtbot.addWidget(widget)
        
        # Verifica se o método existe
        assert hasattr(widget, "salvar_alteracoes")
        assert callable(widget.salvar_alteracoes)
