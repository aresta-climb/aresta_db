# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para exibição de miniatura, metadados e troca de imagens
armazenadas em memória RAM ou em disco no editor.
"""

from pathlib import Path
from typing import Optional, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QDialog,
    QLineEdit,
    QDialogButtonBox,
    QFrame,
)

from editor.models.croqui_model import CroquiModel
from editor.core.processamento_imagem_campo import (
    sanitizar_nome_arquivo_imagem,
    verificar_conflito_nome_imagem,
    obter_metadados_imagem,
    comprimir_imagem_para_bytes_webp,
)


class DialogoNomeImagem(QDialog):
    """
    Diálogo para escolha do nome de destino da imagem quando o campo não possui nome fixo.
    Informa sobre possíveis conflitos com arquivos já existentes.
    """
    def __init__(
        self,
        nome_sugerido: str,
        pasta_imagens: Optional[Path] = None,
        imagens_em_memoria: Optional[Dict[str, bytes]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Nome do Arquivo da Imagem")
        self.setModal(True)
        self.pasta_imagens = pasta_imagens
        self.imagens_em_memoria = imagens_em_memoria

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Informe o nome do arquivo que será salvo na pasta 'imagens/':"))

        self.input_nome = QLineEdit()
        self.input_nome.setText(nome_sugerido)
        self.input_nome.textChanged.connect(self._ao_alterar_nome)
        layout.addWidget(self.input_nome)

        self.rotulo_aviso = QLabel()
        self.rotulo_aviso.setStyleSheet("color: #d97706; font-size: 11px;")
        layout.addWidget(self.rotulo_aviso)

        self.botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        layout.addWidget(self.botoes)

        self._ao_alterar_nome(nome_sugerido)

    def _ao_alterar_nome(self, texto: str):
        nome_sanitizado = sanitizar_nome_arquivo_imagem(texto)
        tem_conflito = verificar_conflito_nome_imagem(
            nome_sanitizado, self.pasta_imagens, self.imagens_em_memoria
        )
        if tem_conflito:
            self.rotulo_aviso.setText("⚠️ Já existe um arquivo com este nome. Ele será substituído ao salvar o croqui.")
        else:
            self.rotulo_aviso.setText("")

    def obter_nome_escolhido(self) -> str:
        return sanitizar_nome_arquivo_imagem(self.input_nome.text())

    def definir_nome(self, nome: str):
        self.input_nome.setText(nome)

    def possui_conflito(self) -> bool:
        return bool(self.rotulo_aviso.text())


class WidgetCampoImagem(QWidget):
    """
    Widget de exibição de miniatura, metadados e controle de troca de imagem.
    """
    imagem_alterada = pyqtSignal(str, bytes)  # caminho_relativo, bytes_conteudo
    imagem_removida = pyqtSignal()
    abrir_no_editor = pyqtSignal(str)  # caminho_relativo

    def __init__(
        self,
        model: Optional[CroquiModel] = None,
        caminho_imagem: str = "",
        nome_arquivo_fixo: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.model = model
        self._caminho_atual = caminho_imagem
        self.nome_arquivo_fixo = nome_arquivo_fixo

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        # Card container
        self.frame_card = QFrame()
        self.frame_card.setFrameShape(QFrame.Shape.StyledPanel)
        layout_card = QHBoxLayout(self.frame_card)
        layout_card.setContentsMargins(8, 8, 8, 8)
        layout_card.setSpacing(12)

        # Preview miniatura
        self.rotulo_preview = QLabel()
        self.rotulo_preview.setFixedSize(140, 100)
        self.rotulo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_preview.setStyleSheet("background-color: rgba(0, 0, 0, 0.05); border-radius: 4px;")
        layout_card.addWidget(self.rotulo_preview)

        # Informações e botões
        layout_info = QVBoxLayout()
        layout_info.setSpacing(4)

        self.rotulo_status = QLabel()
        self.rotulo_status.setStyleSheet("font-weight: bold;")
        self.rotulo_metadados = QLabel()
        self.rotulo_metadados.setStyleSheet("color: #6b7280; font-size: 11px;")

        layout_botoes = QHBoxLayout()
        layout_botoes.setSpacing(6)

        self.btn_trocar = QPushButton("Trocar Imagem...")
        self.btn_trocar.clicked.connect(self.selecionar_e_trocar_imagem)

        self.btn_remover = QPushButton("Remover Imagem")
        self.btn_remover.clicked.connect(self.remover_imagem)

        self.btn_abrir_editor = QPushButton("Abrir no Editor")
        self.btn_abrir_editor.clicked.connect(self._ao_clicar_abrir_editor)

        layout_botoes.addWidget(self.btn_trocar)
        layout_botoes.addWidget(self.btn_remover)
        layout_botoes.addWidget(self.btn_abrir_editor)
        layout_botoes.addStretch()

        layout_info.addWidget(self.rotulo_status)
        layout_info.addWidget(self.rotulo_metadados)
        layout_info.addStretch()
        layout_info.addLayout(layout_botoes)

        layout_card.addLayout(layout_info, stretch=1)
        layout_principal.addWidget(self.frame_card)

        self.atualizar_visualizacao()

    def obter_caminho_atual(self) -> str:
        return self._caminho_atual

    def definir_caminho_atual(self, caminho: str):
        self._caminho_atual = caminho
        self.atualizar_visualizacao()

    def atualizar_visualizacao(self):
        if not self._caminho_atual:
            self.rotulo_preview.clear()
            self.rotulo_preview.setText("Sem Imagem")
            self.rotulo_status.setText("Nenhuma imagem selecionada")
            self.rotulo_metadados.setText("Selecione um arquivo de imagem (WebP, PNG, JPG)")
            self.btn_remover.setEnabled(False)
            self.btn_abrir_editor.setEnabled(False)
            return

        bytes_img = self.model.obter_bytes_imagem(self._caminho_atual) if self.model else None

        if bytes_img:
            pixmap = QPixmap()
            pixmap.loadFromData(bytes_img)
            if not pixmap.isNull():
                pixmap_redimensionado = pixmap.scaled(
                    self.rotulo_preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.rotulo_preview.setPixmap(pixmap_redimensionado)
            else:
                self.rotulo_preview.setText("Erro Img")

            w, h, _, tam_fmt = obter_metadados_imagem(bytes_img)
            nome_arquivo = Path(self._caminho_atual).name
            self.rotulo_status.setText(nome_arquivo)
            self.rotulo_metadados.setText(f"{w} x {h} px • {tam_fmt} • {self._caminho_atual}")
            self.btn_remover.setEnabled(True)
            self.btn_abrir_editor.setEnabled(True)
        else:
            self.rotulo_preview.setText("Ausente")
            nome_arquivo = Path(self._caminho_atual).name
            self.rotulo_status.setText(f"{nome_arquivo} (Não encontrada)")
            self.rotulo_metadados.setText(f"Arquivo não encontrado: {self._caminho_atual}")
            self.btn_remover.setEnabled(True)
            self.btn_abrir_editor.setEnabled(False)

    def aplicar_nova_imagem(self, caminho_relativo: str, bytes_conteudo: bytes):
        """Aplica os novos bytes da imagem na memória e atualiza o widget."""
        self._caminho_atual = caminho_relativo
        if self.model:
            self.model.definir_imagem_memoria(caminho_relativo, bytes_conteudo)
        self.atualizar_visualizacao()
        self.imagem_alterada.emit(caminho_relativo, bytes_conteudo)

    def remover_imagem(self):
        """Limpa o campo de imagem atual."""
        self._caminho_atual = ""
        self.atualizar_visualizacao()
        self.imagem_removida.emit()

    def selecionar_e_trocar_imagem(self):
        """Abre diálogo para seleção de imagem e processamento WebP em memória."""
        caminho_arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem",
            "",
            "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;Todos os Arquivos (*)",
        )
        if not caminho_arquivo:
            return

        pasta_imagens = None
        imagens_memoria = None
        if self.model:
            if hasattr(self.model, "_caminho_db_atual") and self.model._caminho_db_atual:
                pasta_imagens = self.model._caminho_db_atual / "imagens"
            imagens_memoria = self.model.obter_imagens_em_memoria()

        if self.nome_arquivo_fixo:
            nome_final = self.nome_arquivo_fixo
        else:
            nome_sugerido = sanitizar_nome_arquivo_imagem(Path(caminho_arquivo).name)
            dialogo = DialogoNomeImagem(
                nome_sugerido=nome_sugerido,
                pasta_imagens=pasta_imagens,
                imagens_em_memoria=imagens_memoria,
                parent=self,
            )
            if dialogo.exec() != QDialog.DialogCode.Accepted:
                return
            nome_final = dialogo.obter_nome_escolhido()

        caminho_relativo = f"imagens/{nome_final}"
        bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(caminho_arquivo, quality=85)

        self.aplicar_nova_imagem(caminho_relativo, bytes_webp)

    def _ao_clicar_abrir_editor(self):
        if self._caminho_atual:
            self.abrir_no_editor.emit(self._caminho_atual)
