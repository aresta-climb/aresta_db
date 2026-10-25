# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Sequence

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from editor.core.topologia_trajeto import OpcaoCaminhoConfluencia


class PopoverConfluenciaRota(QFrame):
    """
    Popover contextual flutuante exibido no canvas de mapas quando o usuário clica
    sobre um nó ou segmento de uma rota existente durante o desenho de uma nova rota.

    Permite escolher intuitivamente entre:
    - Confluir e encerrar a nova rota seguindo um dos caminhos existentes até o topo
      (com pré-visualização Ghost Preview em tempo real);
    - Apenas adicionar um ponto intermediário e continuar desenhando livremente;
    - Cancelar o último clique com `Esc` ou clicando fora.
    """

    opcao_focada = Signal(object)  # OpcaoCaminhoConfluencia | None
    opcao_confirmada = Signal(object)  # OpcaoCaminhoConfluencia
    apenas_adicionar_ponto = Signal()
    cancelado = Signal()

    QSS_POPOVER: str = """
        QFrame#PopoverConfluenciaRota {
            background-color: #1e242b;
            border: 1px solid #3b4654;
            border-radius: 8px;
        }
        QLabel#TituloPopoverConfluencia {
            color: #9fb3c8;
            font-size: 8.5pt;
            font-weight: bold;
            padding: 2px 6px 4px 6px;
        }
        QPushButton {
            text-align: left;
            color: #f0f4f8;
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 5px;
            padding: 6px 10px;
            font-size: 9.5pt;
        }
        QPushButton[selecionado="true"] {
            background-color: #1b4332;
            border: 1px solid #40c057;
            color: #ffffff;
            font-weight: bold;
        }
    """

    def __init__(
        self,
        opcoes: Sequence[OpcaoCaminhoConfluencia],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("PopoverConfluenciaRota")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(self.QSS_POPOVER)

        self._opcoes: tuple[OpcaoCaminhoConfluencia, ...] = tuple(opcoes)
        self._indice_selecionado: int = 0
        self._acao_disparada: bool = False
        self.botoes_opcoes: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        rotulo_titulo = QLabel("Confluência de Rota — Escolha o caminho:", self)
        rotulo_titulo.setObjectName("TituloPopoverConfluencia")
        layout.addWidget(rotulo_titulo)

        for idx, opcao in enumerate(self._opcoes):
            texto = f"[{idx + 1}] {opcao.rotulo_exibicao}"
            botao = self._criar_botao_opcao(texto, idx)
            layout.addWidget(botao)

        idx_adicionar = len(self._opcoes)
        texto_adicionar = f"[{idx_adicionar + 1}] Apenas adicionar ponto e continuar desenhando"
        botao_adicionar = self._criar_botao_opcao(texto_adicionar, idx_adicionar)
        layout.addWidget(botao_adicionar)

        self._atualizar_estilo_selecao()

    def _criar_botao_opcao(self, texto: str, indice: int) -> QPushButton:
        botao = QPushButton(texto, self)
        botao.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        botao.setCursor(Qt.CursorShape.PointingHandCursor)
        botao.installEventFilter(self)
        botao.clicked.connect(lambda _checked=False, idx=indice: self.confirmar_indice(idx))
        self.botoes_opcoes.append(botao)
        return botao

    @property
    def indice_selecionado(self) -> int:
        return self._indice_selecionado

    def exibir_em(self, pos_global: QPoint) -> None:
        """Posiciona o popover próximo ao cursor, exibe-o e emite o foco inicial para Ghost Preview."""
        self.adjustSize()
        self.move(pos_global + QPoint(14, 14))
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.PopupFocusReason)
        self._emitir_foco_atual()

    def definir_indice_selecionado(self, novo_indice: int) -> None:
        """Atualiza o item selecionado e emite `opcao_focada` quando houver mudança."""
        if novo_indice == self._indice_selecionado:
            return
        self._indice_selecionado = novo_indice
        self._atualizar_estilo_selecao()
        self._emitir_foco_atual()

    def _atualizar_estilo_selecao(self) -> None:
        for idx, botao in enumerate(self.botoes_opcoes):
            botao.setProperty("selecionado", idx == self._indice_selecionado)
            botao.style().unpolish(botao)
            botao.style().polish(botao)

    def _emitir_foco_atual(self) -> None:
        if 0 <= self._indice_selecionado < len(self._opcoes):
            self.opcao_focada.emit(self._opcoes[self._indice_selecionado])
        else:
            self.opcao_focada.emit(None)

    def confirmar_indice(self, indice: int) -> None:
        """Confirma a opção de índice informado e fecha o popover."""
        self._acao_disparada = True
        if 0 <= indice < len(self._opcoes):
            self.opcao_confirmada.emit(self._opcoes[indice])
        else:
            self.apenas_adicionar_ponto.emit()
        self.close()

    def cancelar(self) -> None:
        """Cancela a interação sem adicionar pontos e fecha o popover."""
        self._acao_disparada = True
        self.cancelado.emit()
        self.close()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter and isinstance(watched, QPushButton):
            if watched in self.botoes_opcoes:
                idx = self.botoes_opcoes.index(watched)
                self.definir_indice_selecionado(idx)
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        tecla = event.key()
        total = len(self.botoes_opcoes)

        if tecla == Qt.Key.Key_Down:
            self.definir_indice_selecionado((self._indice_selecionado + 1) % total)
            event.accept()
            return

        if tecla == Qt.Key.Key_Up:
            self.definir_indice_selecionado((self._indice_selecionado - 1) % total)
            event.accept()
            return

        if tecla in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirmar_indice(self._indice_selecionado)
            event.accept()
            return

        if tecla == Qt.Key.Key_Escape:
            self.cancelar()
            event.accept()
            return

        if Qt.Key.Key_1 <= tecla <= Qt.Key.Key_9:
            numero = int(tecla - Qt.Key.Key_1) + 1
            if 1 <= numero <= total:
                self.confirmar_indice(numero - 1)
                event.accept()
                return

        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._acao_disparada:
            self._acao_disparada = True
            self.cancelado.emit()
        super().closeEvent(event)
