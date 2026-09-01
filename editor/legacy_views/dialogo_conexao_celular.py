# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

import base64
from typing import Optional, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QBuffer, QIODevice
import base64
from PySide6.QtGui import QPixmap, QFont, QGuiApplication
import qtawesome as qta
from editor.views.estilo import Icones
from ..core.worker import TarefaDadosConexao


class DialogoConexaoCelular(QDialog):
    """Diálogo com instruções, QR Code e código alfanumérico para conectar o celular ao editor."""
    solicitar_encerrar = Signal()
    
    def __init__(self, servidor_celular: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.servidor = servidor_celular
        self.setWindowTitle("Conectar ao Celular")
        self.setFixedSize(550, 780)
        self.setStyleSheet("background-color: #ffffff;")
        
        self._setup_ui()
        self._conectar_sinais()
        
        # Inicia carregamento em background
        self.tarefa_dados = TarefaDadosConexao(self.servidor)
        self.tarefa_dados.concluido.connect(self._ao_dados_carregados)
        self.tarefa_dados.start()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # 1. Título e Instruções
        self.label_titulo = QLabel("Sincronização em Tempo Real (Live Review)")
        self.label_titulo.setStyleSheet("font-size: 19px; font-weight: bold; color: #222;")
        self.label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_titulo)
        
        self.label_instrucoes = QLabel(
            "1. No aplicativo Aresta, abra a aba <b>Configurações</b>.<br>"
            "2. No card de <b>Prévia de Croqui</b>, toque em <b>'Conectar ao Editor'</b>.<br>"
            "3. Escaneie o QR Code com a câmera ou digite o código abaixo."
        )
        self.label_instrucoes.setWordWrap(True)
        self.label_instrucoes.setStyleSheet("font-size: 13px; color: #555; line-height: 1.4;")
        layout.addWidget(self.label_instrucoes)
        
        # 2. Área do QR Code
        self.frame_qr = QFrame()
        self.frame_qr.setFixedSize(260, 260)
        self.frame_qr.setStyleSheet("QFrame { border: 1px solid #e0e0e0; border-radius: 12px; background-color: #ffffff; }")
        layout.addWidget(self.frame_qr, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout_qr = QVBoxLayout(self.frame_qr)
        layout_qr.setContentsMargins(8, 8, 8, 8)
        layout_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        self.label_qr = QLabel()
        self.label_qr.setFixedSize(240, 240)
        self.label_qr.setScaledContents(True)
        self.label_qr.hide()
        layout_qr.addWidget(self.label_qr)
    
        # Spinner de carregamento
        self.widget_carregando = QWidget()
        self.widget_carregando.setStyleSheet("border: none; background: transparent;")
        layout_carregando = QVBoxLayout(self.widget_carregando)
        layout_carregando.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_loading_qr = qta.IconWidget()
        self.icon_loading_qr.setFixedSize(60, 60)
        self.icon_loading_qr.setIconSize(QSize(60, 60))
        self.icon_loading_qr.setIcon(qta.icon('fa5s.spinner', color=Icones.COR_DESTAQUE, animation=qta.Spin(self.icon_loading_qr)))
        layout_carregando.addWidget(self.icon_loading_qr, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.label_loading_qr = QLabel("Inicializando conexão...")
        self.label_loading_qr.setStyleSheet(f"color: {Icones.COR_DESTAQUE}; font-size: 15px; font-weight: bold; border: none;")
        self.label_loading_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_carregando.addWidget(self.label_loading_qr)
        
        layout_qr.addWidget(self.widget_carregando)

        # 3. Código Alfanumérico em Destaque (Estilo Pareamento)
        self.container_codigo = QVBoxLayout()
        self.container_codigo.setSpacing(4)
        self.container_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_codigo_subtitulo = QLabel("CÓDIGO DE PAREAMENTO MANUAL")
        self.label_codigo_subtitulo.setStyleSheet("font-size: 11px; font-weight: bold; color: #888; letter-spacing: 1px;")
        self.label_codigo_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container_codigo.addWidget(self.label_codigo_subtitulo)

        self.label_codigo = QLabel("---- - ----")
        self.label_codigo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_codigo.setStyleSheet("""
            QLabel {
                font-family: 'Consolas', monospace;
                font-size: 24px;
                font-weight: bold;
                color: #2b8a3e;
                padding: 4px 16px;
                background-color: #f4fbf6;
                border: 1px dashed #69db7c;
                border-radius: 8px;
            }
        """)
        self.label_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container_codigo.addWidget(self.label_codigo)
        layout.addLayout(self.container_codigo)
        
        # 4. Endereço por extenso + Botão Copiar
        self.layout_url = QHBoxLayout()
        self.layout_url.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_url.setSpacing(8)
        
        self.label_endereco = QLabel("Aguardando link...")
        self.label_endereco.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_endereco.setStyleSheet("""
            QLabel {
                font-family: 'Consolas', monospace;
                color: #444;
                font-size: 12px;
                padding: 5px 10px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
            }
        """)
        
        self.btn_copiar = QPushButton("Copiar")
        self.btn_copiar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copiar.setFixedWidth(65)
        self.btn_copiar.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                color: #666;
                font-size: 11px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
                color: #333;
            }
        """)
        self.btn_copiar.clicked.connect(self._ao_clicar_copiar)
        
        self.layout_url.addWidget(self.label_endereco)
        self.layout_url.addWidget(self.btn_copiar)
        layout.addLayout(self.layout_url)
        
        # 5. Status da Conexão
        self.container_status = QHBoxLayout()
        self.container_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_status = qta.IconWidget()
        self.icon_status.setIcon(qta.icon('fa5s.spinner', color=Icones.COR_DESTAQUE, animation=qta.Spin(self.icon_status)))
        self.icon_status.setFixedSize(22, 22)
        
        self.label_status = QLabel("Aguardando conexão...")
        self.label_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #666;")
        
        self.container_status.addWidget(self.icon_status)
        self.container_status.addSpacing(8)
        self.container_status.addWidget(self.label_status)
        layout.addLayout(self.container_status)
        
        layout.addStretch()
        
        # 6. Botões inferiores
        botoes = QHBoxLayout()
        self.btn_encerrar = QPushButton("Encerrar Conexão")
        self.btn_encerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_encerrar.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #dc2626;
                border: 1px solid #fca5a5;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fecaca;
            }
        """)
        self.btn_encerrar.clicked.connect(self._ao_clicar_encerrar)
        
        self.btn_fechar = QPushButton("Manter em Segundo Plano")
        self.btn_fechar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                color: #333;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bdc3c7;
            }
        """)
        self.btn_fechar.clicked.connect(self.accept)
        
        botoes.addWidget(self.btn_encerrar)
        botoes.addStretch()
        botoes.addWidget(self.btn_fechar)
        layout.addLayout(botoes)

    def _conectar_sinais(self) -> None:
        self.servidor.dispositivo_conectado.connect(self._ao_dispositivo_conectado)

    def _ao_dados_carregados(self, url: str, qr_bytes: bytes, codigo_formatado: str = "") -> None:
        """Preenche os dados do servidor e o QR Code recebidos do background."""
        self.widget_carregando.hide()
        self.label_endereco.setText(url)
        if codigo_formatado:
            self.label_codigo.setText(codigo_formatado)
        
        pixmap = QPixmap()
        pixmap.loadFromData(qr_bytes)
        self.label_qr.setPixmap(pixmap)
        self.label_qr.show()

    def _ao_dispositivo_conectado(self) -> None:
        """Atualiza a UI para o estado conectado."""
        self.icon_status.setIcon(qta.icon('fa5s.check-circle', color=Icones.COR_SUCESSO))
        self.label_status.setText("Celular Conectado!")
        self.label_status.setStyleSheet(f"font-weight: bold; color: {Icones.COR_SUCESSO}; font-size: 15px;")

    def _ao_clicar_copiar(self) -> None:
        """Copia a URL para a área de transferência."""
        url = self.label_endereco.text()
        if url and not url.startswith("Aguardando"):
            cb = QGuiApplication.clipboard()
            if cb:
                cb.setText(url)

    def _ao_clicar_encerrar(self) -> None:
        self.solicitar_encerrar.emit()
        self.accept()

    def _icon_para_base64(self, icon_base: str, icon_check: str, cor: str = "#666", tamanho: int = 24) -> str:
        """Converte um ícone composto para string Base64 para uso em HTML."""
        icon = qta.icon(icon_base, icon_check, options=[
            {'color': cor},
            {'color': '#ffffff', 'scale_factor': 0.45}
        ])
        pixmap = icon.pixmap(tamanho, tamanho)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        return str(base64.b64encode(buffer.data().data()).decode())
