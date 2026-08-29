# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QWidget
)
from PySide6.QtCore import Qt
from editor.core.formatacao import para_snake_case


class DialogoCriarSetorOuGrupo(QDialog):
    """Diálogo modal (wizard) para criação de um novo Setor ou Grupo, com preenchimento
    do nome e auto-proposição reativa do nome de arquivo em snake_case com validação de duplicidade."""

    def __init__(self, parent: Optional[QWidget] = None, modo: str = "ambos", nome_sugerido: str = "", nomes_existentes: Optional[List[str]] = None, arquivos_existentes: Optional[List[str]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo Setor ou Grupo" if modo == "ambos" else "Novo Setor")
        self.setMinimumWidth(420)

        self.modo: str = modo
        self.nomes_existentes: List[str] = [n.strip().lower() for n in (nomes_existentes or []) if n]
        self.arquivos_existentes: List[str] = [a.strip().lower() for a in (arquivos_existentes or []) if a]
        self._arquivo_editado_manualmente: bool = False
        self._atualizando_internamente: bool = False

        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(12)

        # 1. Seleção de Tipo (Setor vs Grupo)
        self.widget_tipo = QWidget(self)
        layout_tipo = QHBoxLayout(self.widget_tipo)
        layout_tipo.setContentsMargins(0, 0, 0, 0)
        
        lbl_tipo = QLabel("Tipo:", self.widget_tipo)
        lbl_tipo.setStyleSheet("font-weight: bold;")
        layout_tipo.addWidget(lbl_tipo)

        self.grupo_botoes_tipo = QButtonGroup(self)
        self.radio_setor = QRadioButton("Setor", self.widget_tipo)
        self.radio_grupo = QRadioButton("Grupo", self.widget_tipo)
        self.radio_setor.setChecked(True)

        self.grupo_botoes_tipo.addButton(self.radio_setor)
        self.grupo_botoes_tipo.addButton(self.radio_grupo)
        layout_tipo.addWidget(self.radio_setor)
        layout_tipo.addWidget(self.radio_grupo)
        layout_tipo.addStretch()

        if self.modo == "setor":
            self.radio_grupo.setVisible(False)
            self.widget_tipo.setVisible(False)
        elif self.modo == "grupo":
            self.radio_setor.setVisible(False)
            self.radio_grupo.setChecked(True)
            self.widget_tipo.setVisible(False)

        layout_principal.addWidget(self.widget_tipo)

        # 2. Campo de Nome
        lbl_nome = QLabel("Nome:", self)
        lbl_nome.setStyleSheet("font-weight: bold;")
        self.edit_nome = QLineEdit(self)
        self.edit_nome.setPlaceholderText("Ex: Campo Escola, Falésia dos Olhos...")
        layout_principal.addWidget(lbl_nome)
        layout_principal.addWidget(self.edit_nome)

        # 3. Campo de Nome do Arquivo (.md)
        lbl_arquivo = QLabel("Nome do arquivo (.md):", self)
        lbl_arquivo.setStyleSheet("font-weight: bold;")
        self.edit_arquivo = QLineEdit(self)
        self.edit_arquivo.setPlaceholderText("Ex: setor_campo_escola.md")
        layout_principal.addWidget(lbl_arquivo)
        layout_principal.addWidget(self.edit_arquivo)

        # 4. Aviso de Validação / Duplicidade
        self.lbl_aviso = QLabel("", self)
        self.lbl_aviso.setStyleSheet("color: #d9534f; font-size: 9pt;")
        layout_principal.addWidget(self.lbl_aviso)

        # 5. Botões de Ação
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()

        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_criar = QPushButton("Criar", self)
        self.btn_criar.setDefault(True)
        self.btn_criar.setEnabled(False)
        self.btn_criar.setStyleSheet("""
            QPushButton {
                background-color: #2b579a;
                color: white;
                font-weight: bold;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e3f6f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_criar.clicked.connect(self.accept)

        layout_botoes.addWidget(self.btn_cancelar)
        layout_botoes.addWidget(self.btn_criar)
        layout_principal.addLayout(layout_botoes)

        # Conexões reativas
        self.edit_nome.textChanged.connect(self._on_nome_alterado)
        self.edit_arquivo.textChanged.connect(self._on_arquivo_alterado)
        self.radio_setor.toggled.connect(self._on_tipo_alterado)
        self.radio_grupo.toggled.connect(self._on_tipo_alterado)

        if nome_sugerido:
            self.edit_nome.setText(nome_sugerido)

    def obter_tipo_selecionado(self) -> str:
        """Retorna 'setor' ou 'grupo'."""
        if self.radio_grupo.isChecked() and self.modo != "setor":
            return "grupo"
        return "setor"

    def _on_tipo_alterado(self) -> None:
        """Atualiza a proposição do arquivo se o tipo for alternado."""
        if not self._arquivo_editado_manualmente:
            self._atualizar_proposicao_arquivo()
        self._validar()

    def _on_nome_alterado(self, texto: str) -> None:
        """Reage à digitação do nome para propor o nome do arquivo e validar."""
        if not self._arquivo_editado_manualmente:
            self._atualizar_proposicao_arquivo()
        self._validar()

    def _on_arquivo_alterado(self, texto: str) -> None:
        """Registra se o arquivo foi alterado externamente/manualmente e valida."""
        if not self._atualizando_internamente:
            self._arquivo_editado_manualmente = bool(texto.strip())
        self._validar()

    def _atualizar_proposicao_arquivo(self) -> None:
        """Gera o nome de arquivo em snake_case com o prefixo correspondente ao tipo."""
        nome = self.edit_nome.text().strip()
        self._atualizando_internamente = True
        try:
            if not nome:
                self.edit_arquivo.setText("")
                return

            slug = para_snake_case(nome)
            tipo = self.obter_tipo_selecionado()
            if slug:
                self.edit_arquivo.setText(f"{tipo}_{slug}.md")
            else:
                self.edit_arquivo.setText(f"{tipo}.md")
        finally:
            self._atualizando_internamente = False

    def _validar(self) -> None:
        """Valida campos e checa duplicidade."""
        nome = self.edit_nome.text().strip()
        arquivo = self.edit_arquivo.text().strip()

        if not nome:
            self.lbl_aviso.setText("")
            self.btn_criar.setEnabled(False)
            return

        if nome.lower() in self.nomes_existentes:
            tipo = self.obter_tipo_selecionado()
            self.lbl_aviso.setText(f"Já existe um {tipo} com este nome.")
            self.btn_criar.setEnabled(False)
            return

        nome_arquivo_completo = arquivo if arquivo.endswith(".md") else f"{arquivo}.md" if arquivo else ""
        if nome_arquivo_completo.lower() in self.arquivos_existentes:
            self.lbl_aviso.setText(f"Já existe um arquivo com o nome '{nome_arquivo_completo}'.")
            self.btn_criar.setEnabled(False)
            return

        self.lbl_aviso.setText("")
        self.btn_criar.setEnabled(True)

    def obter_dados_confirmados(self) -> Tuple[str, str, str, bool]:
        """Retorna (tipo, nome, nome_arquivo, confirmado)."""
        ok = (self.result() == QDialog.DialogCode.Accepted)
        tipo = self.obter_tipo_selecionado()
        nome = self.edit_nome.text().strip()
        arquivo = self.edit_arquivo.text().strip()

        if arquivo and not arquivo.endswith(".md"):
            arquivo = f"{arquivo}.md"

        return tipo, nome, arquivo, ok

    @classmethod
    def obter_dados(cls, parent: Optional[QWidget] = None, modo: str = "ambos", nome_sugerido: str = "", nomes_existentes: Optional[List[str]] = None, arquivos_existentes: Optional[List[str]] = None) -> Tuple[str, str, str, bool]:
        """Método estático de conveniência para instanciar e abrir o diálogo modal."""
        dialogo = cls(
            parent=parent,
            modo=modo,
            nome_sugerido=nome_sugerido,
            nomes_existentes=nomes_existentes,
            arquivos_existentes=arquivos_existentes
        )
        dialogo.exec()
        return dialogo.obter_dados_confirmados()

