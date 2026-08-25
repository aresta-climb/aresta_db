# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import os
from pathlib import Path
from typing import Optional, Union
from PIL import Image

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QTabWidget, QWidget, QFileDialog,
    QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QImage, QDragEnterEvent, QDropEvent

from editor.core.imagens_markdown import (
    sanitizar_nome_imagem,
    gerar_nome_imagem_padrao,
    gerar_nome_imagem_clipboard,
    formatar_tag_markdown,
    salvar_imagem_otimizada,
)


class AreaDropImagemMarkdown(QWidget):
    """
    Área interativa para arrastar e soltar ou clicar para selecionar uma nova imagem.
    """
    imagem_carregada = pyqtSignal(object)  # Emite caminho str ou QImage

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QWidget {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            QWidget:hover {
                background-color: #f0f0f0;
                border-color: #2b579a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label_info = QLabel("Arraste e solte uma imagem aqui\nou clique para escolher um arquivo do computador", self)
        self.label_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_info.setStyleSheet("border: none; background: transparent; color: #555; font-size: 10pt;")

        self.label_preview = QLabel(self)
        self.label_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_preview.setStyleSheet("border: none; background: transparent;")
        self.label_preview.hide()

        layout.addWidget(self.label_info)
        layout.addWidget(self.label_preview)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            arquivo, _ = QFileDialog.getOpenFileName(
                self, "Selecionar Imagem", "",
                "Imagens (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            if arquivo:
                self.processar_caminho(arquivo)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                ext = Path(urls[0].toLocalFile()).suffix.lower()
                if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            arquivo = urls[0].toLocalFile()
            self.processar_caminho(arquivo)
            event.acceptProposedAction()

    def processar_caminho(self, caminho_arquivo: str):
        pixmap = QPixmap(str(caminho_arquivo))
        if pixmap.isNull():
            QMessageBox.warning(self, "Erro", "Não foi possível carregar o arquivo de imagem selecionado.")
            return
        self.exibir_pixmap(pixmap)
        self.imagem_carregada.emit(str(caminho_arquivo))

    def processar_qimage(self, qimage: QImage):
        pixmap = QPixmap.fromImage(qimage)
        if pixmap.isNull():
            return
        self.exibir_pixmap(pixmap)
        self.imagem_carregada.emit(qimage)

    def exibir_pixmap(self, pixmap: QPixmap):
        pixmap_escalado = pixmap.scaled(
            QSize(240, 160),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.label_preview.setPixmap(pixmap_escalado)
        self.label_info.hide()
        self.label_preview.show()


class DialogoInserirImagemMarkdown(QDialog):
    """
    Diálogo modal para selecionar uma imagem existente do croqui ou importar uma nova
    imagem externa, formatando e inserindo a tag Markdown correspondente.
    """
    def __init__(
        self,
        caminho_db: Path,
        model=None,
        imagem_inicial: Optional[Union[Path, str, QImage, bytes]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Inserir Imagem no Markdown")
        self.resize(580, 520)

        self.caminho_db = Path(caminho_db)
        self.model = model
        self.pasta_imagens = self.caminho_db / "imagens"
        self.pasta_imagens.mkdir(parents=True, exist_ok=True)

        self.fonte_imagem_importacao: Optional[Union[str, Path, QImage, bytes]] = None
        self.nome_imagem_selecionada: str = ""

        self._criar_layout()
        self._carregar_imagens_existentes()

        if imagem_inicial is not None:
            eh_interna = False
            if isinstance(imagem_inicial, (str, Path)):
                p = Path(imagem_inicial)
                try:
                    if self.pasta_imagens.resolve() in p.resolve().parents or (self.pasta_imagens / p.name).resolve() == p.resolve():
                        eh_interna = True
                        self.tab_widget.setCurrentIndex(0)
                        for i in range(self.lista_imagens.count()):
                            item = self.lista_imagens.item(i)
                            if item.text() == p.name:
                                self.lista_imagens.setCurrentItem(item)
                                self.nome_imagem_selecionada = p.name
                                break
                except Exception:
                    eh_interna = False

            if not eh_interna:
                self.carregar_imagem_externa(imagem_inicial)
                self.tab_widget.setCurrentIndex(1)
            
            self.input_legenda.setFocus()
        else:
            self._atualizar_estado_botao()

    def _criar_layout(self):
        layout_principal = QVBoxLayout(self)

        self.tab_widget = QTabWidget(self)

        # Aba 1: Imagens do Croqui
        self.aba_galeria = QWidget()
        layout_galeria = QVBoxLayout(self.aba_galeria)

        layout_busca = QHBoxLayout()
        layout_busca.addWidget(QLabel("Buscar:", self.aba_galeria))
        self.input_busca = QLineEdit(self.aba_galeria)
        self.input_busca.setPlaceholderText("Filtrar por nome de arquivo...")
        self.input_busca.textChanged.connect(self._filtrar_imagens)
        layout_busca.addWidget(self.input_busca)
        layout_galeria.addLayout(layout_busca)

        self.lista_imagens = QListWidget(self.aba_galeria)
        self.lista_imagens.setViewMode(QListWidget.ViewMode.IconMode)
        self.lista_imagens.setIconSize(QSize(96, 96))
        self.lista_imagens.setSpacing(10)
        self.lista_imagens.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.lista_imagens.setMovement(QListWidget.Movement.Static)
        self.lista_imagens.itemSelectionChanged.connect(self._ao_selecionar_item_galeria)
        self.lista_imagens.itemDoubleClicked.connect(self._ao_duplo_clique_galeria)
        layout_galeria.addWidget(self.lista_imagens)

        # Aba 2: Importar Nova Imagem
        self.aba_importar = QWidget()
        layout_importar = QVBoxLayout(self.aba_importar)

        self.area_drop = AreaDropImagemMarkdown(self.aba_importar)
        self.area_drop.imagem_carregada.connect(self._ao_carregar_imagem_drop)
        layout_importar.addWidget(self.area_drop)

        layout_nome = QHBoxLayout()
        layout_nome.addWidget(QLabel("Nome do arquivo (.webp):", self.aba_importar))
        self.input_nome_arquivo = QLineEdit(self.aba_importar)
        self.input_nome_arquivo.setPlaceholderText("ex: entrada_do_setor.webp")
        self.input_nome_arquivo.textChanged.connect(self._atualizar_estado_botao)
        layout_nome.addWidget(self.input_nome_arquivo)
        layout_importar.addLayout(layout_nome)

        self.tab_widget.addTab(self.aba_galeria, "Imagens do Croqui")
        self.tab_widget.addTab(self.aba_importar, "Importar Nova Imagem")
        self.tab_widget.currentChanged.connect(self._atualizar_estado_botao)
        layout_principal.addWidget(self.tab_widget)

        # Rodapé: Legenda Obrigatória e Botões
        layout_legenda = QHBoxLayout()
        layout_legenda.addWidget(QLabel("Legenda (obrigatória):", self))
        self.input_legenda = QLineEdit(self)
        self.input_legenda.setPlaceholderText("Texto descritivo obrigatório da imagem...")
        self.input_legenda.textChanged.connect(self._atualizar_estado_botao)
        layout_legenda.addWidget(self.input_legenda)
        layout_principal.addLayout(layout_legenda)

        layout_botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_inserir = QPushButton("Inserir Imagem", self)
        self.btn_inserir.setDefault(True)
        self.btn_inserir.clicked.connect(self.accept)

        layout_botoes.addStretch()
        layout_botoes.addWidget(self.btn_cancelar)
        layout_botoes.addWidget(self.btn_inserir)
        layout_principal.addLayout(layout_botoes)

    def _carregar_imagens_existentes(self):
        self.lista_imagens.clear()
        nomes_adicionados = set()
        extensoes = {".webp", ".png", ".jpg", ".jpeg", ".bmp"}

        if self.pasta_imagens.exists():
            for arquivo in sorted(self.pasta_imagens.iterdir()):
                if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
                    bytes_img = None
                    if self.model and hasattr(self.model, "obter_bytes_imagem"):
                        bytes_img = self.model.obter_bytes_imagem(f"imagens/{arquivo.name}")
                    if not bytes_img:
                        try:
                            bytes_img = arquivo.read_bytes()
                        except Exception:
                            bytes_img = None
                    
                    if bytes_img:
                        pixmap = QPixmap()
                        pixmap.loadFromData(bytes_img)
                        if not pixmap.isNull():
                            item = QListWidgetItem(arquivo.name)
                            item.setIcon(QIcon(pixmap))
                            item.setData(Qt.ItemDataRole.UserRole, arquivo.name)
                            self.lista_imagens.addItem(item)
                            nomes_adicionados.add(arquivo.name)

        if self.model and hasattr(self.model, "obter_imagens_em_memoria"):
            for caminho_rel, bytes_img in sorted(self.model.obter_imagens_em_memoria().items()):
                if caminho_rel.startswith("imagens/"):
                    nome = caminho_rel.split("/", 1)[1]
                    if nome not in nomes_adicionados and any(nome.lower().endswith(ext) for ext in extensoes):
                        pixmap = QPixmap()
                        pixmap.loadFromData(bytes_img)
                        if not pixmap.isNull():
                            item = QListWidgetItem(nome)
                            item.setIcon(QIcon(pixmap))
                            item.setData(Qt.ItemDataRole.UserRole, nome)
                            self.lista_imagens.addItem(item)
                            nomes_adicionados.add(nome)

    def _filtrar_imagens(self, texto: str):
        termo = texto.strip().lower()
        for i in range(self.lista_imagens.count()):
            item = self.lista_imagens.item(i)
            nome = item.text().lower()
            item.setHidden(termo not in nome if termo else False)

    def _ao_selecionar_item_galeria(self):
        itens = self.lista_imagens.selectedItems()
        if itens:
            self.nome_imagem_selecionada = itens[0].text()
        else:
            self.nome_imagem_selecionada = ""
        self._atualizar_estado_botao()

    def _ao_duplo_clique_galeria(self, item):
        self.nome_imagem_selecionada = item.text()
        self._atualizar_estado_botao()
        if not self.input_legenda.text().strip():
            self.input_legenda.setFocus()
            return
        self.accept()

    def _ao_carregar_imagem_drop(self, objeto_imagem):
        self.carregar_imagem_externa(objeto_imagem)

    def _gerar_nome_unico(self, nome_orig: str) -> str:
        nome_sanitizado = sanitizar_nome_imagem(nome_orig)
        stem = nome_sanitizado[:-5]
        
        imagens_memoria = set(self.model.obter_imagens_em_memoria().keys()) if (self.model and hasattr(self.model, "obter_imagens_em_memoria")) else set()
        
        def existe(nome):
            return (self.pasta_imagens / nome).exists() or f"imagens/{nome}" in imagens_memoria

        if not existe(nome_sanitizado):
            return nome_sanitizado

        contador = 1
        while existe(f"{stem}_{contador}.webp"):
            contador += 1
        return f"{stem}_{contador}.webp"

    def carregar_imagem_externa(self, objeto_imagem: Union[str, Path, QImage, bytes]):
        self.fonte_imagem_importacao = objeto_imagem
        if isinstance(objeto_imagem, (str, Path)):
            caminho = Path(objeto_imagem)
            pix = QPixmap(str(caminho))
            if not pix.isNull():
                self.area_drop.exibir_pixmap(pix)
            nome_sugerido = self._gerar_nome_unico(caminho.name)
        elif isinstance(objeto_imagem, QImage):
            pix = QPixmap.fromImage(objeto_imagem)
            if not pix.isNull():
                self.area_drop.exibir_pixmap(pix)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_sugerido = self._gerar_nome_unico(f"imagem_{timestamp}")
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_sugerido = self._gerar_nome_unico(f"imagem_{timestamp}")

        self.input_nome_arquivo.setText(nome_sugerido)
        self._atualizar_estado_botao()

    def _atualizar_estado_botao(self):
        tem_legenda = bool(self.input_legenda.text().strip())
        aba_atual = self.tab_widget.currentIndex()
        if aba_atual == 0:
            habilitado = bool(self.nome_imagem_selecionada) and tem_legenda
        else:
            tem_fonte = self.fonte_imagem_importacao is not None
            tem_nome = bool(self.input_nome_arquivo.text().strip())
            habilitado = tem_fonte and tem_nome and tem_legenda
        self.btn_inserir.setEnabled(habilitado)

    def accept(self):
        legenda = self.input_legenda.text().strip()
        if not legenda:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Legenda Obrigatória", "Por favor, informe a legenda da imagem antes de inserir.")
            self.input_legenda.setFocus()
            return

        aba_atual = self.tab_widget.currentIndex()
        if aba_atual == 0:
            if not self.nome_imagem_selecionada:
                return
        else:
            if not self.fonte_imagem_importacao:
                return
            nome_digitado = self.input_nome_arquivo.text().strip()
            if not nome_digitado:
                return
            nome_final = sanitizar_nome_imagem(nome_digitado)
            caminho_final = self.pasta_imagens / nome_final

            # Converte QImage para bytes PNG temporários se necessário
            fonte = self.fonte_imagem_importacao
            if isinstance(fonte, QImage):
                from PyQt6.QtCore import QBuffer, QIODevice
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                fonte.save(buffer, "PNG")
                fonte = bytes(buffer.data())

            if self.model and hasattr(self.model, "definir_imagem_memoria"):
                from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp
                bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(fonte, quality=85, max_area=4194304)
                self.model.definir_imagem_memoria(f"imagens/{nome_final}", bytes_webp)
            else:
                salvar_imagem_otimizada(fonte, caminho_final)
            self.nome_imagem_selecionada = nome_final

        super().accept()

    def obter_nome_imagem(self) -> str:
        return self.nome_imagem_selecionada

    def obter_tag_markdown(self) -> str:
        legenda = self.input_legenda.text().strip()
        return formatar_tag_markdown(self.nome_imagem_selecionada, legenda)
