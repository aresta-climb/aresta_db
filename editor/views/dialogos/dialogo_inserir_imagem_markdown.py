# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Diálogo moderno e unificado para inserir imagem no Markdown.
Apresenta a mesma anatomia visual de DialogoAdicionarMapa (área de drop, cabeçalho com botão,
painel de metadados ricos e validação contínua de nomes contra RAM e disco) além de suporte
à seleção de imagens existentes na galeria do croqui e campo obrigatório de legenda.
"""

from pathlib import Path
from typing import Optional, Union, Tuple, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QWidget,
    QFileDialog,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QImage

from editor.views.componentes.area_drop_imagem import (
    AreaDropImagem,
    EXTENSOES_IMAGEM_SUPORTADAS,
    FILTRO_ARQUIVOS_IMAGEM,
)
from editor.core.processamento_imagem_campo import (
    sanitizar_nome_imagem,
    obter_metadados_imagem,
    comprimir_imagem_para_bytes_webp,
    garantir_suporte_heif,
)
from editor.core.imagens_markdown import formatar_tag_markdown, salvar_imagem_otimizada


class DialogoInserirImagemMarkdown(QDialog):
    """
    Diálogo modal para selecionar uma imagem existente do croqui ou importar uma nova
    imagem externa com conversão WebP, metadados ricos e validação contínua de colisões.
    """

    def __init__(
        self,
        caminho_db: Path,
        model: Optional[Any] = None,
        imagem_inicial: Optional[Union[Path, str, QImage, bytes]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Inserir Imagem no Markdown")
        self.resize(580, 560)

        self.caminho_db: Path = Path(caminho_db)
        self.model: Optional[Any] = model
        self.pasta_imagens: Path = self.caminho_db / "imagens"
        self.pasta_imagens.mkdir(parents=True, exist_ok=True)

        self.fonte_imagem_importacao: Optional[Union[str, Path, QImage, bytes]] = None
        self.bytes_processados_webp: Optional[bytes] = None
        self.dimensoes: Optional[Tuple[int, int]] = None
        self.nome_imagem_selecionada: str = ""

        self._criar_layout()
        self._carregar_imagens_existentes()

        if imagem_inicial is not None:
            eh_interna = False
            if isinstance(imagem_inicial, (str, Path)):
                p = Path(imagem_inicial)
                try:
                    if self.pasta_imagens.resolve() in p.resolve().parents or (
                        self.pasta_imagens / p.name
                    ).resolve() == p.resolve():
                        eh_interna = True
                        self.tab_widget.setCurrentIndex(1)  # Galeria
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
                self.tab_widget.setCurrentIndex(0)  # Importação

            self.input_legenda.setFocus()
        else:
            self.tab_widget.setCurrentIndex(0)  # Inicia na aba de importação unificada
            self._validar_estado()

    def _criar_layout(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(10)
        layout_principal.setContentsMargins(16, 16, 16, 16)

        self.tab_widget = QTabWidget(self)

        # -------------------------------------------------------------------
        # Aba 0: Importar Nova Imagem (Unificada com DialogoAdicionarMapa)
        # -------------------------------------------------------------------
        self.aba_importar = QWidget()
        layout_importar = QVBoxLayout(self.aba_importar)
        layout_importar.setSpacing(10)
        layout_importar.setContentsMargins(10, 10, 10, 10)

        # Cabeçalho com botão explícito "Selecionar Imagem..."
        linha_cabecalho = QHBoxLayout()
        lbl_instrucao = QLabel("Selecione ou arraste a imagem para convertê-la para WebP:")
        lbl_instrucao.setStyleSheet("color: #333; font-weight: 500;")
        self.btn_selecionar = QPushButton("Selecionar Imagem...")
        self.btn_selecionar.setStyleSheet("padding: 6px 12px; font-weight: bold;")
        self.btn_selecionar.clicked.connect(self._abrir_seletor_arquivos)
        linha_cabecalho.addWidget(lbl_instrucao)
        linha_cabecalho.addStretch()
        linha_cabecalho.addWidget(self.btn_selecionar)
        layout_importar.addLayout(linha_cabecalho)

        # Área de drag & drop
        self.area_drop = AreaDropImagem(self.aba_importar)
        self.area_drop.imagem_selecionada.connect(self.carregar_imagem_arquivo)
        layout_importar.addWidget(self.area_drop)

        # Painel de metadados da imagem
        self.rotulo_metadados = QLabel("")
        self.rotulo_metadados.setStyleSheet(
            "color: #444; font-size: 12px; background: #f0f0f0; padding: 6px; border-radius: 4px;"
        )
        self.rotulo_metadados.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_metadados.hide()
        layout_importar.addWidget(self.rotulo_metadados)

        # Divisor
        divisor = QFrame()
        divisor.setFrameShape(QFrame.Shape.HLine)
        divisor.setFrameShadow(QFrame.Shadow.Sunken)
        layout_importar.addWidget(divisor)

        # Campo de nome do arquivo de destino
        layout_nome = QHBoxLayout()
        lbl_nome = QLabel("Nome do Arquivo (Destino):")
        lbl_nome.setMinimumWidth(160)
        self.input_nome_arquivo = QLineEdit()
        self.input_nome_arquivo.setPlaceholderText("ex: entrada_do_setor.webp")
        self.input_nome_arquivo.textChanged.connect(self._ao_alterar_nome)
        self.input_nome = self.input_nome_arquivo  # alias para retrocompatibilidade
        layout_nome.addWidget(lbl_nome)
        layout_nome.addWidget(self.input_nome_arquivo)
        layout_importar.addLayout(layout_nome)

        # Rótulo de caminho final relativo
        self.rotulo_caminho_destino = QLabel()
        self.rotulo_caminho_destino.setStyleSheet("color: #666; font-size: 11px;")
        layout_importar.addWidget(self.rotulo_caminho_destino)

        # Rótulo de aviso de erro/conflito
        self.rotulo_aviso = QLabel("")
        self.rotulo_aviso.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
        layout_importar.addWidget(self.rotulo_aviso)

        # -------------------------------------------------------------------
        # Aba 1: Imagens do Croqui (Galeria existente)
        # -------------------------------------------------------------------
        self.aba_galeria = QWidget()
        layout_galeria = QVBoxLayout(self.aba_galeria)
        layout_galeria.setSpacing(8)
        layout_galeria.setContentsMargins(10, 10, 10, 10)

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

        # Adiciona as abas ao tab_widget
        self.tab_widget.addTab(self.aba_importar, "Importar Nova Imagem")
        self.tab_widget.addTab(self.aba_galeria, "Imagens do Croqui")
        self.tab_widget.currentChanged.connect(self._ao_trocar_aba)
        layout_principal.addWidget(self.tab_widget)

        # -------------------------------------------------------------------
        # Rodapé Compartilhado: Legenda Obrigatória e Botões de Ação
        # -------------------------------------------------------------------
        layout_legenda = QHBoxLayout()
        lbl_legenda = QLabel("Legenda (obrigatória):")
        lbl_legenda.setStyleSheet("font-weight: 500;")
        self.input_legenda = QLineEdit(self)
        self.input_legenda.setPlaceholderText("Texto descritivo obrigatório da imagem...")
        self.input_legenda.textChanged.connect(self._ao_alterar_legenda)
        layout_legenda.addWidget(lbl_legenda)
        layout_legenda.addWidget(self.input_legenda)
        layout_principal.addLayout(layout_legenda)

        layout_botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_inserir = QPushButton("Inserir Imagem", self)
        self.btn_inserir.setDefault(True)
        self.btn_inserir.setStyleSheet("padding: 6px 16px; font-weight: bold;")
        self.btn_inserir.clicked.connect(self.accept)

        layout_botoes.addStretch()
        layout_botoes.addWidget(self.btn_cancelar)
        layout_botoes.addWidget(self.btn_inserir)
        layout_principal.addLayout(layout_botoes)

    def _abrir_seletor_arquivos(self) -> None:
        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem",
            "",
            FILTRO_ARQUIVOS_IMAGEM,
        )
        if arquivo:
            self.carregar_imagem_arquivo(arquivo)

    def carregar_imagem_arquivo(self, caminho_arquivo: Union[str, Path]) -> None:
        caminho = Path(caminho_arquivo)
        if not caminho.exists() or not caminho.is_file():
            QMessageBox.warning(self, "Erro", "Arquivo não encontrado.")
            return

        try:
            bytes_originais = caminho.read_bytes()
            self.carregar_imagem_bytes(bytes_originais, nome_sugerido_origem=caminho.name)
            self.fonte_imagem_importacao = str(caminho)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao ler arquivo: {e}")

    def carregar_imagem_bytes(
        self, bytes_originais: bytes, nome_sugerido_origem: Optional[str] = None
    ) -> None:
        w_orig, h_orig, tam_orig, txt_tam_orig = obter_metadados_imagem(bytes_originais)
        if w_orig <= 0 or h_orig <= 0:
            ext = Path(nome_sugerido_origem or "").suffix.lower()
            eh_heic = (ext in (".heic", ".heif")) or (
                len(bytes_originais) > 12 and b"ftyp" in bytes_originais[4:12]
            )
            if eh_heic and not garantir_suporte_heif():
                QMessageBox.warning(
                    self,
                    "Erro",
                    "O suporte a imagens HEIC/HEIF requer a biblioteca 'pillow-heif'.\n"
                    "Reinicie o editor ou instale via 'pip install pillow-heif'.",
                )
                return
            try:
                bytes_webp, w_final, h_final = comprimir_imagem_para_bytes_webp(bytes_originais)
            except Exception:
                bytes_webp = bytes_originais
                w_final, h_final = (100, 100)
        else:
            bytes_webp, w_final, h_final = comprimir_imagem_para_bytes_webp(bytes_originais)

        self.bytes_processados_webp = bytes_webp
        self.dimensoes = (w_final, h_final)

        # Atualiza a pré-visualização
        self.area_drop.definir_preview_bytes(bytes_webp)

        # Atualiza rótulo de metadados
        _, _, tam_webp, txt_tam_webp = obter_metadados_imagem(bytes_webp)
        self.rotulo_metadados.setText(
            f"Dimensões: {w_final} x {h_final} px  |  "
            f"Tamanho WebP: {txt_tam_webp} (Original: {txt_tam_orig})"
        )
        self.rotulo_metadados.show()

        # Atualiza nome sugerido
        if nome_sugerido_origem:
            nome_sugerido = self._gerar_nome_unico(nome_sugerido_origem)
        else:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_sugerido = self._gerar_nome_unico(f"imagem_{timestamp}")

        self.input_nome_arquivo.setText(nome_sugerido)
        self._validar_estado()

    def carregar_imagem_externa(self, objeto_imagem: Union[str, Path, QImage, bytes]) -> None:
        self.fonte_imagem_importacao = objeto_imagem
        if isinstance(objeto_imagem, (str, Path)):
            self.carregar_imagem_arquivo(objeto_imagem)
        elif isinstance(objeto_imagem, QImage):
            from PySide6.QtCore import QBuffer, QIODevice

            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            objeto_imagem.save(buffer, "PNG")  # type: ignore[call-overload]
            bytes_png = bytes(buffer.data().data())
            self.carregar_imagem_bytes(bytes_png)
        elif isinstance(objeto_imagem, bytes):
            self.carregar_imagem_bytes(objeto_imagem)

    def _gerar_nome_unico(self, nome_orig: str) -> str:
        nome_sanitizado = sanitizar_nome_imagem(nome_orig)
        stem = nome_sanitizado[:-5] if nome_sanitizado.endswith(".webp") else nome_sanitizado

        imagens_memoria = (
            set(self.model.obter_imagens_em_memoria().keys())
            if (self.model and hasattr(self.model, "obter_imagens_em_memoria"))
            else set()
        )

        def existe(nome: str) -> bool:
            return (self.pasta_imagens / nome).exists() or f"imagens/{nome}" in imagens_memoria

        if not existe(nome_sanitizado):
            return nome_sanitizado

        contador = 1
        while existe(f"{stem}_{contador}.webp"):
            contador += 1
        return f"{stem}_{contador}.webp"

    def _carregar_imagens_existentes(self) -> None:
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
                    if nome not in nomes_adicionados and any(
                        nome.lower().endswith(ext) for ext in extensoes
                    ):
                        pixmap = QPixmap()
                        pixmap.loadFromData(bytes_img)
                        if not pixmap.isNull():
                            item = QListWidgetItem(nome)
                            item.setIcon(QIcon(pixmap))
                            item.setData(Qt.ItemDataRole.UserRole, nome)
                            self.lista_imagens.addItem(item)
                            nomes_adicionados.add(nome)

    def _filtrar_imagens(self, texto: str) -> None:
        termo = texto.strip().lower()
        for i in range(self.lista_imagens.count()):
            item = self.lista_imagens.item(i)
            nome = item.text().lower()
            item.setHidden(termo not in nome if termo else False)

    def _ao_selecionar_item_galeria(self) -> None:
        itens = self.lista_imagens.selectedItems()
        if itens:
            self.nome_imagem_selecionada = itens[0].text()
        else:
            self.nome_imagem_selecionada = ""
        self._validar_estado()

    def _ao_duplo_clique_galeria(self, item: QListWidgetItem) -> None:
        self.nome_imagem_selecionada = item.text()
        self._validar_estado()
        if not self.input_legenda.text().strip():
            self.input_legenda.setFocus()
            return
        self.accept()

    def _ao_alterar_nome(self, _texto: str) -> None:
        self._validar_estado()

    def _ao_alterar_legenda(self, _texto: str) -> None:
        self._validar_estado()

    def _ao_trocar_aba(self, _indice: int) -> None:
        self._validar_estado()

    def obter_caminho_final_relativo(self) -> str:
        txt = self.input_nome_arquivo.text().strip()
        slug = sanitizar_nome_imagem(txt or "imagem.webp")
        return f"imagens/{slug}"

    def obter_bytes_imagem_processada(self) -> Optional[bytes]:
        return self.bytes_processados_webp

    def obter_dimensoes_imagem(self) -> Optional[Tuple[int, int]]:
        return self.dimensoes

    def _validar_estado(self) -> None:
        aba_atual = self.tab_widget.currentIndex()
        tem_legenda = bool(self.input_legenda.text().strip())

        if aba_atual == 1:  # Galeria do Croqui
            tem_sel = bool(self.nome_imagem_selecionada)
            self.btn_inserir.setEnabled(tem_sel and tem_legenda)
            self.rotulo_aviso.setText("")
            return

        # Aba 0: Importar Nova Imagem
        caminho_rel = self.obter_caminho_final_relativo()
        self.rotulo_caminho_destino.setText(f"Destino no croqui: {caminho_rel}")

        # 1. Verifica se tem imagem carregada
        if not self.bytes_processados_webp and not self.fonte_imagem_importacao:
            self.rotulo_aviso.setText("")
            self.btn_inserir.setEnabled(False)
            return

        nome_txt = self.input_nome_arquivo.text().strip()
        if not nome_txt:
            self.rotulo_aviso.setText("")
            self.btn_inserir.setEnabled(False)
            return

        slug = sanitizar_nome_imagem(nome_txt)
        nome_arquivo = slug

        # 2. Verifica se o nome já existe na RAM
        if self.model and hasattr(self.model, "obter_imagens_em_memoria"):
            imagens_ram = self.model.obter_imagens_em_memoria()
            if f"imagens/{nome_arquivo}" in imagens_ram:
                self.rotulo_aviso.setText(
                    f"⚠ O arquivo '{nome_arquivo}' já existe na memória RAM. Escolha outro nome."
                )
                self.btn_inserir.setEnabled(False)
                return

        # 3. Verifica se o nome já existe no disco
        if self.caminho_db:
            caminho_abs = self.pasta_imagens / nome_arquivo
            if caminho_abs.exists():
                self.rotulo_aviso.setText(
                    f"⚠ O arquivo '{nome_arquivo}' já existe na pasta imagens/. Escolha outro nome."
                )
                self.btn_inserir.setEnabled(False)
                return

        self.rotulo_aviso.setText("")
        self.btn_inserir.setEnabled(tem_legenda)

    def accept(self) -> None:
        legenda = self.input_legenda.text().strip()
        if not legenda:
            QMessageBox.warning(
                self,
                "Legenda Obrigatória",
                "Por favor, informe a legenda da imagem antes de inserir.",
            )
            self.input_legenda.setFocus()
            return

        self._validar_estado()
        if not self.btn_inserir.isEnabled():
            return

        aba_atual = self.tab_widget.currentIndex()
        if aba_atual == 0:
            nome_digitado = self.input_nome_arquivo.text().strip()
            nome_final = sanitizar_nome_imagem(nome_digitado)

            if self.bytes_processados_webp:
                if self.model and hasattr(self.model, "definir_imagem_memoria"):
                    self.model.definir_imagem_memoria(
                        f"imagens/{nome_final}", self.bytes_processados_webp
                    )
                else:
                    caminho_final = self.pasta_imagens / nome_final
                    caminho_final.write_bytes(self.bytes_processados_webp)

            self.nome_imagem_selecionada = nome_final

        super().accept()

    def obter_nome_imagem(self) -> str:
        return self.nome_imagem_selecionada

    def obter_tag_markdown(self) -> str:
        legenda = self.input_legenda.text().strip()
        return formatar_tag_markdown(self.nome_imagem_selecionada, legenda)
