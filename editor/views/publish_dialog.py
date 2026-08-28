# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Sequence
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QHBoxLayout, QPushButton, QLabel, QTextBrowser
)

class PublishDialog(QDialog):
    """
    Diálogo para coletar informações para a submissão da sugestão de Pull Request.
    Permite ao usuário definir o título, descrição e visualizar resumo das alterações.
    """
    def __init__(self, titulo_padrao: str = "", resumo_arquivos: Optional[Sequence[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enviar Proposta de Mudança")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        if resumo_arquivos:
            qtd = len(resumo_arquivos)
            label_resumo = QLabel(f"📦 <b>Alterações incluídas nesta proposta de mudança ({qtd} {'arquivo' if qtd == 1 else 'arquivos'}):</b>")
            layout.addWidget(label_resumo)
            
            texto_arquivos = QTextBrowser()
            texto_arquivos.setReadOnly(True)
            texto_arquivos.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            texto_arquivos.setMaximumHeight(80)
            texto_arquivos.setPlainText("\n".join(f"• {arq}" for arq in resumo_arquivos))
            texto_arquivos.setStyleSheet("""
                QTextBrowser {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    padding: 6px 8px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 11px;
                    line-height: 120%;
                    color: #212529;
                }
            """)
            layout.addWidget(texto_arquivos)
        
        form = QFormLayout()
        self.edit_titulo = QLineEdit(f"Croqui: {titulo_padrao}")
        self.edit_descricao = QTextEdit()
        self.edit_descricao.setPlaceholderText("Descreva as alterações feitas...")
        self.edit_descricao.setMinimumHeight(80)
        
        form.addRow("Título:", self.edit_titulo)
        form.addRow("Descrição:", self.edit_descricao)
        layout.addLayout(form)
        
        texto_dco = QLabel("Ao enviar, você certifica que tem o direito de compartilhar este conteúdo<br>e concorda com o <a href='https://github.com/aresta-climb/aresta_db/blob/main/CONTRIBUINDO.md'>Developer Certificate of Origin (DCO)</a>.")
        texto_dco.setOpenExternalLinks(True)
        texto_dco.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(texto_dco)
        
        botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_publicar = QPushButton("Enviar Proposta de Mudança")
        self.btn_publicar.setDefault(True)
        self.btn_publicar.clicked.connect(self.accept)
        
        botoes.addStretch()
        botoes.addWidget(self.btn_cancelar)
        botoes.addWidget(self.btn_publicar)
        layout.addLayout(botoes)

    def obter_dados(self) -> dict:
        """
        Retorna os dados inseridos pelo usuário.
        
        Returns:
            dict: Dicionário contendo as chaves 'titulo' e 'descricao'.
        """
        return {
            "titulo": self.edit_titulo.text(),
            "descricao": self.edit_descricao.toPlainText()
        }
