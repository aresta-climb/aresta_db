# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para exibição de cartão de mapa em coleções repetidas.
Exibe miniatura da imagem, metadados de resolução, caminho do arquivo e controles de ação/reordenação.
"""

from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.views.componentes.alca_arraste_item import AlcaArrasteItem


class WidgetCardMapa(QFrame):
    """
    Card aberto e visual para exibição de um Mapa em coleções repetidas.
    Substitui accordions genéricos, permitindo pré-visualização direta e reordenação intuitiva.
    """

    def __init__(
        self,
        msg_mapa: Any,
        indice: int,
        model: Optional[Any] = None,
        controller: Optional[Any] = None,
        formulario: Optional[Any] = None,
        extra_path: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.msg_mapa = msg_mapa
        self.indice = indice
        self.model = model
        self.controller = controller
        self.formulario = formulario
        self.extra_path = extra_path

        self.setProperty("repeated_index", indice)
        self.setObjectName("WidgetCardMapa")
        self.setStyleSheet("""
            QFrame#WidgetCardMapa {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background-color: #f6f8fa;
            }
        """)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(10, 8, 10, 8)
        layout_principal.setSpacing(8)

        # --- Cabeçalho Superior ---
        layout_cabecalho = QHBoxLayout()
        layout_cabecalho.setContentsMargins(0, 0, 0, 0)
        layout_cabecalho.setSpacing(6)

        # Alça de arraste
        self.alca = AlcaArrasteItem(self)
        layout_cabecalho.addWidget(self.alca)

        # Rótulo de título
        self.rotulo_titulo = QLabel()
        self.rotulo_titulo.setStyleSheet("font-weight: bold; color: #24292f; font-size: 10pt;")
        layout_cabecalho.addWidget(self.rotulo_titulo)

        layout_cabecalho.addStretch()

        # Botões de reordenação e remoção
        self.btn_subir = QPushButton("▲")
        self.btn_subir.setToolTip("Mover para cima")
        self.btn_subir.setStyleSheet(
            "QPushButton { padding: 4px 8px; font-size: 8pt; border-radius: 4px; } "
            "QPushButton:disabled { color: #aaaaaa; }"
        )

        self.btn_descer = QPushButton("▼")
        self.btn_descer.setToolTip("Mover para baixo")
        self.btn_descer.setStyleSheet(
            "QPushButton { padding: 4px 8px; font-size: 8pt; border-radius: 4px; } "
            "QPushButton:disabled { color: #aaaaaa; }"
        )

        self.btn_remover = QPushButton("Remover")
        self.btn_remover.setStyleSheet(
            "background-color: #d9534f; color: white; border-radius: 4px; padding: 4px 8px;"
        )

        layout_cabecalho.addWidget(self.btn_subir)
        layout_cabecalho.addWidget(self.btn_descer)
        layout_cabecalho.addWidget(self.btn_remover)

        layout_principal.addLayout(layout_cabecalho)

        # --- Corpo (Miniatura + Informações + Ação) ---
        layout_corpo = QHBoxLayout()
        layout_corpo.setContentsMargins(0, 0, 0, 0)
        layout_corpo.setSpacing(12)

        # Miniatura da imagem
        self.rotulo_miniatura = QLabel()
        self.rotulo_miniatura.setFixedSize(160, 100)
        self.rotulo_miniatura.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_miniatura.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.05); border: 1px solid #d0d7de; border-radius: 4px; color: #57606a;"
        )
        layout_corpo.addWidget(self.rotulo_miniatura)

        # Informações e botão de ação
        layout_info = QVBoxLayout()
        layout_info.setSpacing(4)

        self.rotulo_arquivo = QLabel()
        self.rotulo_arquivo.setStyleSheet("font-weight: bold; color: #24292f; font-size: 9pt;")
        layout_info.addWidget(self.rotulo_arquivo)

        self.rotulo_resolucao = QLabel()
        self.rotulo_resolucao.setStyleSheet("color: #57606a; font-size: 9pt;")
        layout_info.addWidget(self.rotulo_resolucao)

        layout_info.addStretch()

        self.btn_abrir_editor = QPushButton("Abrir no Editor de Mapas")
        self.btn_abrir_editor.setStyleSheet(
            "QPushButton { padding: 6px 12px; font-weight: bold; background-color: #2ea44f; color: white; border-radius: 4px; } "
            "QPushButton:hover { background-color: #2c974b; }"
        )
        self.btn_abrir_editor.clicked.connect(self._ao_clicar_abrir_editor)
        layout_info.addWidget(self.btn_abrir_editor)

        layout_corpo.addLayout(layout_info, stretch=1)
        layout_principal.addLayout(layout_corpo)

        # Conecta sinal de imagem alterada no modelo se disponível
        if self.model and hasattr(self.model, "imagem_alterada"):
            self.model.imagem_alterada.connect(self._ao_alterar_imagem)

        self.atualizar_dados()

    def definir_indice(self, novo_indice: int) -> None:
        """Atualiza o índice posicional do cartão e seu título."""
        self.indice = novo_indice
        self.setProperty("repeated_index", novo_indice)
        self._atualizar_titulo()

    def _atualizar_titulo(self) -> None:
        caminho = getattr(self.msg_mapa, "caminho_imagem_mapa", "")
        nome_arq = Path(caminho).name if caminho else "Sem arquivo"
        self.rotulo_titulo.setText(f"Mapa [{self.indice}] - {nome_arq}")

    def atualizar_dados(self) -> None:
        """Carrega os dados mais recentes da mensagem e atualiza miniatura e metadados."""
        self._atualizar_titulo()

        caminho = getattr(self.msg_mapa, "caminho_imagem_mapa", "")
        self.rotulo_arquivo.setText(caminho if caminho else "Nenhum arquivo associado")

        largura = getattr(self.msg_mapa, "largura_mapa", 0)
        altura = getattr(self.msg_mapa, "altura_mapa", 0)
        if largura > 0 and altura > 0:
            self.rotulo_resolucao.setText(f"Resolução: {largura} × {altura} px")
        else:
            self.rotulo_resolucao.setText("Resolução não informada")

        bytes_img = self.model.obter_bytes_imagem(caminho) if (self.model and caminho) else None
        if bytes_img and isinstance(bytes_img, (bytes, bytearray, memoryview)):
            pixmap = QPixmap()
            pixmap.loadFromData(bytes_img)
            if not pixmap.isNull():
                pixmap_redimensionado = pixmap.scaled(
                    self.rotulo_miniatura.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.rotulo_miniatura.setPixmap(pixmap_redimensionado)
            else:
                self.rotulo_miniatura.clear()
                self.rotulo_miniatura.setText("Erro Imagem")
        else:
            self.rotulo_miniatura.clear()
            self.rotulo_miniatura.setText("Sem Imagem")

    def _ao_alterar_imagem(self, caminho_relativo: str) -> None:
        caminho_atual = getattr(self.msg_mapa, "caminho_imagem_mapa", "")
        if caminho_atual and (caminho_relativo == caminho_atual or Path(caminho_relativo).name == Path(caminho_atual).name):
            self.atualizar_dados()

    def _ao_clicar_abrir_editor(self) -> None:
        """Navega diretamente para a visualização deste mapa no editor de mapas."""
        if not self.formulario or not self.controller:
            return

        from editor.views.widget_editor_dados import get_node_path

        current_node = getattr(self.formulario, "current_node", None)
        if current_node:
            path = "page:mapas/" + get_node_path(current_node)
            if self.extra_path:
                path += "/" + self.extra_path
            self.controller.set_contexto(path)
            if self.model and hasattr(self.model, "notificar_foco_requisitado"):
                self.model.notificar_foco_requisitado(path)
