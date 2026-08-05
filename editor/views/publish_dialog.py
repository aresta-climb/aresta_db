# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QHBoxLayout, QPushButton, QLabel

class PublishDialog(QDialog):
    """
    Diálogo para coletar informações para a abertura do Pull Request.
    Permite ao usuário definir o título e a descrição da publicação.
    """
    def __init__(self, titulo_padrao="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publicar no GitHub")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.edit_titulo = QLineEdit(f"Croqui: {titulo_padrao}")
        self.edit_descricao = QTextEdit()
        self.edit_descricao.setPlaceholderText("Descreva as alterações feitas...")
        
        form.addRow("Título da PR:", self.edit_titulo)
        form.addRow("Descrição:", self.edit_descricao)
        layout.addLayout(form)
        
        texto_dco = QLabel("Ao publicar, você certifica que tem o direito de enviar este conteúdo<br>e concorda com o <a href='https://github.com/aresta-climb/aresta_db/blob/main/CONTRIBUTING.md'>Developer Certificate of Origin (DCO)</a>.")
        texto_dco.setOpenExternalLinks(True)
        texto_dco.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(texto_dco)
        
        botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_publicar = QPushButton("Publicar Agora")
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
