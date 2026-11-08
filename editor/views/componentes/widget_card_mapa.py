# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para exibição de cartão de mapa em coleções repetidas.
Exibe miniatura da imagem, metadados de resolução, caminho do arquivo e controles de ação/reordenação.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from editor.views.componentes.alca_arraste_item import AlcaArrasteItem
from editor.views.estilo import Icones


class WidgetCardMapa(QFrame):
    """
    Card aberto e visual para exibição de um Mapa em coleções repetidas.
    Substitui accordions genéricos, permitindo pré-visualização direta e reordenação intuitiva.
    """

    def __init__(
        self,
        msg_mapa: Any,
        indice: int,
        model: Any | None = None,
        controller: Any | None = None,
        formulario: Any | None = None,
        extra_path: str | None = None,
        parent: QWidget | None = None,
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

        # Botão de remoção discreto na extrema direita
        self.btn_remover = QPushButton()
        self.btn_remover.setIcon(Icones.obter_lixeira())
        self.btn_remover.setToolTip("Remover mapa")
        self.btn_remover.setStyleSheet(Icones.QSS_BOTAO_REMOVER_DISCRETO)
        self.btn_remover.setCursor(Qt.CursorShape.PointingHandCursor)

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
            "QPushButton { padding: 6px 16px; font-weight: bold; background-color: #2ea44f; color: white; border-radius: 4px; } "
            "QPushButton:hover { background-color: #2c974b; }"
        )
        self.btn_abrir_editor.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.btn_abrir_editor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_editor.clicked.connect(self._ao_clicar_abrir_editor)

        self.btn_substituir_imagem = QPushButton("Substituir Imagem...")
        self.btn_substituir_imagem.setStyleSheet(
            "QPushButton { padding: 6px 14px; font-weight: bold; background-color: #0969da; color: white; border-radius: 4px; } "
            "QPushButton:hover { background-color: #0550ae; }"
        )
        self.btn_substituir_imagem.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        self.btn_substituir_imagem.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_substituir_imagem.clicked.connect(self._ao_clicar_substituir_imagem)

        layout_acoes = QHBoxLayout()
        layout_acoes.setContentsMargins(0, 0, 0, 0)
        layout_acoes.setSpacing(8)
        layout_acoes.addWidget(self.btn_abrir_editor)
        layout_acoes.addWidget(self.btn_substituir_imagem)
        layout_acoes.addStretch()
        layout_info.addLayout(layout_acoes)

        layout_corpo.addLayout(layout_info, stretch=1)
        layout_principal.addLayout(layout_corpo)

        # Conecta sinais de alteração no modelo se disponíveis
        if self.model and hasattr(self.model, "imagem_alterada"):
            self.model.imagem_alterada.connect(self._ao_alterar_imagem)
        if self.model and hasattr(self.model, "dado_alterado"):
            self.model.dado_alterado.connect(self._ao_alterar_dado_modelo)

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
        if caminho_atual and (
            caminho_relativo == caminho_atual
            or Path(caminho_relativo).name == Path(caminho_atual).name
        ):
            self.atualizar_dados()

    def _ao_alterar_dado_modelo(self, _msg_pai: Any, campo_nome: str) -> None:
        if campo_nome in ("caminho_imagem_mapa", "largura_mapa", "altura_mapa"):
            self.atualizar_dados()

    def _ao_clicar_substituir_imagem(self) -> None:
        """Abre o wizard unificado para substituir a imagem do mapa e atualiza modelo via histórico."""
        if not self.controller:
            return

        from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa

        db_dir = getattr(self.model, "_caminho_db_atual", None) if self.model else None

        caminho_atual = str(getattr(self.msg_mapa, "caminho_imagem_mapa", "") or "")
        nome_sugerido = Path(caminho_atual).name if caminho_atual else "novo_mapa.webp"
        largura_antiga = int(getattr(self.msg_mapa, "largura_mapa", 0) or 0)
        altura_antiga = int(getattr(self.msg_mapa, "altura_mapa", 0) or 0)
        qtd_pois = len(getattr(self.msg_mapa, "pontos_de_interesse", []))

        dialog = DialogoAdicionarMapa(
            nome_sugerido=nome_sugerido,
            db_dir=db_dir,
            model=self.model,
            parent=self,
            modo_substituicao_mapa=True,
            largura_mapa_antiga=largura_antiga,
            altura_mapa_antiga=altura_antiga,
            qtd_pois_mapa=qtd_pois,
        )
        if dialog.exec() == DialogoAdicionarMapa.DialogCode.Accepted:
            caminho_novo = dialog.obter_caminho_final_relativo()
            bytes_novo = dialog.obter_bytes_imagem_processada()
            w_novo, h_novo = dialog.obter_dimensoes_imagem() or (0, 0)
            reescalar = dialog.deve_reescalar_pois()

            self.controller.substituir_imagem_mapa(
                msg_mapa=self.msg_mapa,
                caminho_relativo_novo=caminho_novo,
                bytes_novo=bytes_novo,
                largura_nova=w_novo,
                altura_nova=h_novo,
                reescalar_pois=reescalar,
                largura_referencia_pois=largura_antiga,
                altura_referencia_pois=altura_antiga,
            )
            self.atualizar_dados()
            if self.formulario:
                if hasattr(self.formulario, "_mark_dirty"):
                    self.formulario._mark_dirty()
                if hasattr(self.formulario, "_notify_tree_changed"):
                    self.formulario._notify_tree_changed()

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
