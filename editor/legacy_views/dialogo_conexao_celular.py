# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QBuffer, QIODevice
import base64
from PyQt6.QtGui import QPixmap, QFont, QGuiApplication
import qtawesome as qta
from editor.views.estilo import Icones
from ..core.worker import TarefaDadosConexao

class DialogoConexaoCelular(QDialog):
    """Diálogo com instruções e QR Code para conectar o celular ao editor."""
    solicitar_encerrar = pyqtSignal()
    
    def __init__(self, servidor_celular, parent=None):
        super().__init__(parent)
        self.servidor = servidor_celular
        self.setWindowTitle("Conectar ao Celular")
        self.setFixedSize(550, 750)
        self.setStyleSheet("background-color: #ffffff;")
        
        self._setup_ui()
        self._conectar_sinais()
        
        # Inicia carregamento em background
        self.tarefa_dados = TarefaDadosConexao(self.servidor)
        self.tarefa_dados.concluido.connect(self._ao_dados_carregados)
        self.tarefa_dados.start()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 1. Título e Instruções
        self.label_titulo = QLabel("Sincronização em Tempo Real")
        self.label_titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        self.label_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_titulo)
        
        # Gera o ícone real (selo com check) para mostrar nas instruções
        icon_b64 = self._icon_para_base64('fa5s.certificate', 'fa5s.check')
        
        self.label_instrucoes = QLabel(
            "1. Garanta que o celular está na <b>mesma rede Wi-Fi</b>.<br><br>"
            "2. No aplicativo Aresta, vá em <b>Configurações</b>.<br><br>"
            f"3. Aperte no ícone <img src='data:image/png;base64,{icon_b64}' style='vertical-align: middle;'> (à esquerda de \"Modo Oficial Ativo\") <b>7 vezes</b>.<br><br>"
            "4. Aperte em <b>'Conectar como Editor'</b> e escaneie o QR Code abaixo."
        )
        self.label_instrucoes.setWordWrap(True)
        self.label_instrucoes.setStyleSheet("font-size: 13px; color: #666; line-height: 1.4;")
        layout.addWidget(self.label_instrucoes)
        
        layout.addSpacing(10)
        
        # 2. Área do QR Code (Tamanho fixo para evitar saltos na UI)
        self.frame_qr = QFrame()
        self.frame_qr.setFixedSize(300, 300)
        # Usamos seletor QFrame para evitar que o estilo seja herdado pelos filhos (causando bordas duplas)
        self.frame_qr.setStyleSheet("QFrame { border: 1px solid #eee; border-radius: 12px; background-color: #ffffff; }")
        layout.addWidget(self.frame_qr, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout_qr = QVBoxLayout(self.frame_qr)
        layout_qr.setContentsMargins(10, 10, 10, 10)
        layout_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        self.label_qr = QLabel()
        self.label_qr.setFixedSize(280, 280)
        self.label_qr.setScaledContents(True)
        self.label_qr.hide()
        layout_qr.addWidget(self.label_qr)
    
        # Spinner de carregamento
        self.widget_carregando = QWidget()
        self.widget_carregando.setStyleSheet("border: none; background: transparent;")
        layout_carregando = QVBoxLayout(self.widget_carregando)
        layout_carregando.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.icon_loading_qr = qta.IconWidget()
        # Ajustado para 80x80 (tamanho médio equilibrado)
        self.icon_loading_qr.setFixedSize(80, 80)
        self.icon_loading_qr.setIconSize(QSize(80, 80))
        self.icon_loading_qr.setIcon(qta.icon('fa5s.spinner', color=Icones.COR_DESTAQUE, animation=qta.Spin(self.icon_loading_qr)))
        layout_carregando.addWidget(self.icon_loading_qr, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.label_loading_qr = QLabel("Inicializando servidor...")
        self.label_loading_qr.setStyleSheet(f"color: {Icones.COR_DESTAQUE}; font-size: 16px; font-weight: bold; border: none;")
        self.label_loading_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_carregando.addWidget(self.label_loading_qr)
        
        layout_qr.addWidget(self.widget_carregando)
        
        # 3. Endereço por extenso (Selecionável) + Botão Copiar
        self.layout_url = QHBoxLayout()
        self.layout_url.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_url.setSpacing(8)
        
        self.label_endereco = QLabel("Aguardando IP...")
        self.label_endereco.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label_endereco.setStyleSheet("""
            QLabel {
                font-family: 'Consolas', monospace;
                color: #444;
                font-size: 13px;
                padding: 6px 12px;
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
        
        layout.addSpacing(5)
        
        # 4. Status da Conexão
        self.container_status = QHBoxLayout()
        self.container_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ícone animado usando IconWidget
        self.icon_status = qta.IconWidget()
        self.icon_status.setIcon(qta.icon('fa5s.spinner', color=Icones.COR_DESTAQUE, animation=qta.Spin(self.icon_status)))
        self.icon_status.setFixedSize(24, 24)
        
        self.label_status = QLabel("Esperando por conexão...")
        self.label_status.setStyleSheet(f"font-weight: bold; color: {Icones.COR_DESTAQUE}; font-size: 14px;")
        
        self.container_status.addWidget(self.icon_status)
        self.container_status.addSpacing(10)
        self.container_status.addWidget(self.label_status)
        layout.addLayout(self.container_status)
        
        # 5. Botões
        botoes = QHBoxLayout()
        self.btn_encerrar = QPushButton("Encerrar Conexão")
        self.btn_encerrar.setStyleSheet(f"""
            QPushButton {{
                background-color: {Icones.COR_ERRO};
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
        """)
        self.btn_encerrar.clicked.connect(self._ao_clicar_encerrar)
        
        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1;
                color: #333;
                border-radius: 5px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #bdc3c7;
            }
        """)
        self.btn_fechar.clicked.connect(self.accept)
        
        botoes.addStretch()
        botoes.addWidget(self.btn_encerrar)
        botoes.addWidget(self.btn_fechar)
        layout.addLayout(botoes)

    def _conectar_sinais(self):
        self.servidor.dispositivo_conectado.connect(self._ao_dispositivo_conectado)

    def _ao_dados_carregados(self, url, qr_bytes):
        """Preenche os dados do servidor e o QR Code recebidos do background."""
        self.widget_carregando.hide()
        self.label_endereco.setText(url)
        
        pixmap = QPixmap()
        pixmap.loadFromData(qr_bytes)
        self.label_qr.setPixmap(pixmap)
        self.label_qr.show()

    def _gerar_conteudo(self):
        # Removido em favor do _ao_dados_carregados
        pass

    def _ao_dispositivo_conectado(self):
        """Atualiza a UI para o estado conectado."""
        # Troca o ícone para um tick verde e para a animação
        self.icon_status.setIcon(qta.icon('fa5s.check-circle', color=Icones.COR_SUCESSO))
        self.label_status.setText("Conectado!")
        self.label_status.setStyleSheet(f"font-weight: bold; color: {Icones.COR_SUCESSO}; font-size: 16px;")

    def _ao_clicar_copiar(self):
        """Copia a URL para a área de transferência."""
        url = self.label_endereco.text()
        if url and url != "Aguardando IP...":
            cb = QGuiApplication.clipboard()
            cb.setText(url)

    def _ao_clicar_encerrar(self):
        self.solicitar_encerrar.emit()
        self.accept()

    def _icon_para_base64(self, icon_base, icon_check, cor="#666", tamanho=24):
        """Converte um ícone composto para string Base64 para uso em HTML."""
        icon = qta.icon(icon_base, icon_check, options=[
            {'color': cor},
            {'color': '#ffffff', 'scale_factor': 0.45} # Check branco sobre fundo escuro
        ])
        pixmap = icon.pixmap(tamanho, tamanho)
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        return base64.b64encode(buffer.data().data()).decode()
