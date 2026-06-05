# Copyright (C) 2026 ARESTA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sys
import os

# Adiciona o diretório raiz ao path para permitir importação do módulo 'editor'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication, QMainWindow
from editor.legacy_views.editor_mapas import WidgetEditorMapas, CenaDesenho as DrawingScene
from editor.core.mapas_lib import converter_box_para_circulo as logic_convert_box_to_circle

# Exporta nomes para manter compatibilidade com scripts/editar_mapas_test.py
__all__ = ['DrawingScene', 'logic_convert_box_to_circle', 'MainWindow']

class MainWindow(QMainWindow):
    def __init__(self, caminho_pasta):
        super().__init__()
        self.setWindowTitle(f"ARESTA Batch Bounding Box Editor - {caminho_pasta}")
        self.resize(1280, 800)
        self.widget = WidgetEditorMapas(caminho_pasta, self, standalone=True)
        self.setCentralWidget(self.widget)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python editar_mapas.py <caminho_da_pasta_do_croqui>")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    janela = MainWindow(sys.argv[1])
    janela.show()
    sys.exit(app.exec())
