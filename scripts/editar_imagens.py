# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import os

# Adiciona o diretório raiz ao sys.path para permitir importações do pacote 'editor'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from editor.legacy_views.widget_editor_imagens import WidgetEditorImagens

class MainWindow(QMainWindow):
    def __init__(self, folder_path):
        super().__init__()
        self.setWindowTitle(f"ARESTA Batch Image Editor - {folder_path}")
        self.resize(1280, 800)
        
        # Modo integrado = False para mostrar o botão de salvar
        self.widget = WidgetEditorImagens(folder_path, modo_integrado=False, parent=self)
        self.setCentralWidget(self.widget)

    def closeEvent(self, event):
        # Verifica se há modificações não salvas no widget
        modified_count = len([s for s in self.widget.states.values() if s.is_modified])
        
        if modified_count > 0:
            reply = QMessageBox.question(self, "Alterações não salvas",
                                       f"Existem {modified_count} imagem(ns) com alterações não salvas.\nDeseja realmente sair sem salvar?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python scripts/editar_imagens.py <caminho_da_pasta_croqui>")
        print("Exemplo: python scripts/editar_imagens.py database/br_mg_santa_luzia_santuario")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    folder = sys.argv[1]
    
    if not os.path.exists(folder):
        print(f"Erro: Pasta não encontrada: {folder}")
        sys.exit(1)
        
    window = MainWindow(folder)
    window.show()
    sys.exit(app.exec())
