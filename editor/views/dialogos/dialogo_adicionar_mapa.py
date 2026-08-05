# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QDialogButtonBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

class AreaDropImagem(QWidget):
    imagem_selecionada = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("""
            QWidget {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            QWidget:hover {
                background-color: #e9e9e9;
                border-color: #888;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label_info = QLabel("Arraste e solte uma imagem aqui\nou clique para selecionar")
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_info.setStyleSheet("border: none; background: transparent; color: #555;")
        
        self.label_preview = QLabel()
        self.label_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_preview.setStyleSheet("border: none; background: transparent;")
        self.label_preview.hide()
        
        self.layout.addWidget(self.label_info)
        self.layout.addWidget(self.label_preview)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            arquivo, _ = QFileDialog.getOpenFileName(
                self, "Selecionar Imagem", "",
                "Imagens (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            if arquivo:
                self.processar_imagem(arquivo)
                
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                ext = Path(urls[0].toLocalFile()).suffix.lower()
                if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp']:
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            arquivo = urls[0].toLocalFile()
            self.processar_imagem(arquivo)
            event.acceptProposedAction()
            
    def processar_imagem(self, caminho):
        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            QMessageBox.warning(self, "Erro", "Não foi possível carregar a imagem.")
            return
            
        pixmap_scaled = pixmap.scaled(self.width() - 20, self.height() - 20, 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.label_preview.setPixmap(pixmap_scaled)
        self.label_info.hide()
        self.label_preview.show()
        
        self.imagem_selecionada.emit(caminho)

class DialogoAdicionarMapa(QDialog):
    def __init__(self, nome_sugerido: str, db_dir: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Novo Mapa")
        self.db_dir = db_dir
        self.caminho_imagem_selecionada = None
        
        self.layout = QVBoxLayout(self)
        
        # Área de drag and drop
        self.area_drop = AreaDropImagem(self)
        self.area_drop.imagem_selecionada.connect(self._on_imagem_selecionada)
        self.layout.addWidget(self.area_drop)
        
        # Campo de nome do arquivo
        layout_nome = QHBoxLayout()
        layout_nome.addWidget(QLabel("Nome do Arquivo (Destino):"))
        self.input_nome = QLineEdit(nome_sugerido)
        layout_nome.addWidget(self.input_nome)
        self.layout.addLayout(layout_nome)
        
        # Botões
        self.bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_ok = self.bbox.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_ok.setEnabled(False) # Só habilita quando selecionar a imagem
        
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        self.layout.addWidget(self.bbox)
        
        self.resize(500, 450)

    def _on_imagem_selecionada(self, caminho):
        self.caminho_imagem_selecionada = caminho
        self.btn_ok.setEnabled(True)

    def obter_caminho_final_relativo(self) -> str:
        nome_arquivo = self.input_nome.text().strip()
        if not nome_arquivo.endswith('.webp'):
            nome_arquivo += '.webp'
        return f"imagens/{nome_arquivo}"

    def obter_caminho_final_absoluto(self) -> Path:
        return self.db_dir / self.obter_caminho_final_relativo()

    def accept(self):
        # Validação
        if not self.caminho_imagem_selecionada:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma imagem.")
            return
            
        caminho_abs = self.obter_caminho_final_absoluto()
        if caminho_abs.exists():
            QMessageBox.critical(self, "Erro", f"O arquivo '{caminho_abs.name}' já existe na pasta imagens/. Por favor, escolha outro nome de arquivo para não sobrescrever.")
            return
            
        super().accept()
