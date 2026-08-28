# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize
from .estilo import Icones

class NotificacaoToast(QWidget):
    """
    Um widget de notificação flutuante (Toast) que aparece e desaparece suavemente.
    """
    def __init__(self, mensagem, timeout_ms=3000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self._setup_ui(mensagem)
        
        # Timer para iniciar o fechamento
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fechar_com_animacao)
        self.timer.setSingleShot(True)
        self.timer.start(timeout_ms)
        
    def _setup_ui(self, mensagem):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container com fundo estilizado (reduzido)
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(45, 45, 45, 235);
                border-radius: 4px;
            }
        """)
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(8, 4, 10, 4)
        container_layout.setSpacing(6)
        
        # Ícone de Sucesso (menor)
        self.label_icone = QLabel()
        pixmap = Icones.obter("salvar", cor=Icones.COR_SUCESSO).pixmap(14, 14)
        self.label_icone.setPixmap(pixmap)
        container_layout.addWidget(self.label_icone)
        
        # Texto da Mensagem (menor)
        self.label_texto = QLabel(mensagem)
        self.label_texto.setStyleSheet("color: white; font-size: 11px; font-family: 'Segoe UI', sans-serif;")
        container_layout.addWidget(self.label_texto)
        
        layout.addWidget(self.container)
        
        # Efeito de Opacidade para Animação
        self.efeito_opacidade = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.efeito_opacidade)
        self.efeito_opacidade.setOpacity(1.0)
        
    def fechar_com_animacao(self):
        """Inicia a animação de fade-out e fecha o widget."""
        self.animacao = QPropertyAnimation(self.efeito_opacidade, b"opacity")
        self.animacao.setDuration(400)
        self.animacao.setStartValue(1.0)
        self.animacao.setEndValue(0.0)
        self.animacao.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animacao.finished.connect(self.close)
        self.animacao.start()

    def posicionar_no_canto(self, widget_pai):
        """Posiciona o toast no canto inferior direito do widget pai (coordenadas globais)."""
        if not widget_pai:
            return
            
        self.adjustSize()
        tamanho_proprio = self.size()
        
        # Obtém o canto inferior direito da janela pai em coordenadas globais
        ponto_base = widget_pai.mapToGlobal(QPoint(widget_pai.width(), widget_pai.height()))
        
        # Margem de 20px das bordas da janela
        x = ponto_base.x() - tamanho_proprio.width() - 20
        y = ponto_base.y() - tamanho_proprio.height() - 20
        
        self.move(x, y)
        self.raise_()
