# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QLineEdit, QPushButton, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QDesktopServices, QPixmap
from .estilo import Icones

class TelaDeAbertura(QWidget):
    """
    Janela de abertura com barra de progresso e status.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        from PyQt6.QtGui import QIcon
        from editor.core.storage import GerenciadorCaminhos
        caminho_logo_janela = GerenciadorCaminhos().obter_caminho_recurso_interno("recursos/logo_app.png")
        self.setWindowIcon(QIcon(str(caminho_logo_janela)))
        self.setFixedSize(450, 650)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        # Container principal com bordas arredondadas e fundo escuro
        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: #ffffff;
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        layout.addWidget(self.container)
        
        # Botão de fechar no canto superior direito
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #adb5bd;
                font-size: 24px;
                border: none;
                margin-top: -10px;
                margin-right: -10px;
            }
            QPushButton:hover { color: #dc3545; }
        """)
        self.btn_close.clicked.connect(QApplication.quit)
        container_layout.addWidget(self.btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Header com Logo Aresta e Título
        header_layout = QVBoxLayout()
        header_layout.setSpacing(15)
        
        self.label_logo = QLabel()
        self.label_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from editor.core.storage import GerenciadorCaminhos
        caminho_logo = GerenciadorCaminhos().obter_caminho_recurso_interno("recursos/logo_splash.png")
        pixmap = QPixmap(str(caminho_logo))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label_logo.setPixmap(pixmap)
        header_layout.addWidget(self.label_logo)
        
        container_layout.addLayout(header_layout)
        container_layout.addSpacing(10)
        
        # Status
        self.label_status = QLabel("Iniciando...")
        self.label_status.setStyleSheet("color: #495057; font-size: 14px; margin-bottom: 15px;")
        self.label_status.setWordWrap(True)
        container_layout.addWidget(self.label_status, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Barra de progresso (Oculta por padrão)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #e9ecef;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #495057;
                border-radius: 5px;
            }
        """)
        self.progress_bar.hide()
        container_layout.addWidget(self.progress_bar)
        
        # Widgets de Autenticação (inicialmente ocultos)
        self.auth_container = QWidget()
        self.auth_layout = QVBoxLayout(self.auth_container)
        self.auth_layout.setContentsMargins(0, 10, 0, 10)
        self.auth_layout.setSpacing(15)
        
        self.label_auth_instrucao = QLabel(
            "O editor precisa de conectar à sua conta do GitHub para poder recuperar croquis e publicar novos croquis.\n\n"
            "Por favor, acesse o link abaixo e insira o código para autenticar:"
        )
        self.label_auth_instrucao.setWordWrap(True)
        self.label_auth_instrucao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_auth_instrucao.setStyleSheet("color: #495057; font-size: 14px; line-height: 1.4;")
        self.auth_layout.addWidget(self.label_auth_instrucao)
        
        # Container para Código + Botão Copiar
        self.codigo_layout = QHBoxLayout()
        self.codigo_layout.setSpacing(5)
        
        self.edit_auth_code = QLineEdit()
        self.edit_auth_code.setReadOnly(True)
        self.edit_auth_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_auth_code.setFixedWidth(150)
        self.edit_auth_code.setStyleSheet("""
            QLineEdit {
                background: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', monospace;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.setFixedWidth(80)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background: #e9ecef;
                color: #495057;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover { background: #dee2e6; }
        """)
        self.btn_copy.clicked.connect(self.copiar_codigo)
        
        self.codigo_layout.addStretch()
        self.codigo_layout.addWidget(self.edit_auth_code)
        self.codigo_layout.addWidget(self.btn_copy)
        self.codigo_layout.addStretch()
        self.auth_layout.addLayout(self.codigo_layout)
        
        self.btn_abrir_github = QPushButton(" Abrir GitHub")
        self.btn_abrir_github.setIcon(Icones.obter("github", cor="#ffffff", cor_ativa="#ffffff"))
        self.btn_abrir_github.setIconSize(QSize(20, 20))
        self.btn_abrir_github.setFixedWidth(200)
        self.btn_abrir_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_github.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #5a6268; }
        """)
        self.btn_abrir_github.clicked.connect(self.abrir_link_github)
        self.auth_layout.addWidget(self.btn_abrir_github, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.auth_container.hide()
        container_layout.addWidget(self.auth_container)

    def atualizar_status(self, texto: str):
        self.label_status.setText(texto)

    def atualizar_progresso(self, valor: int):
        self.progress_bar.setValue(valor)

    def exibir_barra_progresso(self, visivel):
        """
        Mostra ou oculta a barra de progresso.
        """
        self.progress_bar.setVisible(visivel)

    def exibir_codigo_auth(self, codigo: str):
        self.edit_auth_code.setText(codigo)
        self.label_status.hide() # Esconde o status para evitar duplicidade
        self.auth_container.show()

    def esconder_auth(self):
        self.auth_container.hide()
        self.label_status.show()

    def copiar_codigo(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.edit_auth_code.text())
        self.btn_copy.setText("Copiado!")

    def abrir_link_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/login/device"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
