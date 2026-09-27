# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Diálogo para inserção de botões ou links em textos Markdown.
Permite selecionar um arquivo anexo existente no croqui, importar um novo arquivo
para a pasta anexos/ ou apontar para uma URL externa (link web).
"""

import re
import unicodedata
from pathlib import Path
from typing import Optional, Union, Any
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
    QFrame,
)
from PySide6.QtCore import Qt


def sanitizar_nome_arquivo_anexo(nome_arquivo: str) -> str:
    """
    Sanitiza o nome de um arquivo anexo para uso no repositório:
    - Converte para minúsculas;
    - Remove acentos;
    - Substitui espaços e traços por sublinhados;
    - Remove caracteres não alfanuméricos exceto ponto e sublinhado.
    """
    p = Path(nome_arquivo)
    ext = p.suffix.lower()
    tronco = p.stem

    # Normaliza unicode e remove acentuação
    tronco_normalizado = unicodedata.normalize("NFKD", tronco)
    tronco_limpo = "".join(c for c in tronco_normalizado if not unicodedata.combining(c))
    tronco_limpo = tronco_limpo.lower().strip()

    # Substitui espaços e hífens por sublinhado
    tronco_limpo = re.sub(r"[\s\-]+", "_", tronco_limpo)
    # Remove qualquer caractere fora de a-z, 0-9 e _
    tronco_limpo = re.sub(r"[^a-z0-9_]", "", tronco_limpo)

    if not tronco_limpo:
        tronco_limpo = "documento_anexo"

    return f"{tronco_limpo}{ext}"


class DialogoInserirBotaoMarkdown(QDialog):
    """
    Diálogo modal para inserção de botões/links no editor de Markdown.
    """

    def __init__(
        self,
        caminho_db: Path,
        model: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Inserir Botão ou Link no Markdown")
        self.resize(520, 480)

        self.caminho_db: Path = Path(caminho_db)
        self.model: Optional[Any] = model
        self.pasta_anexos: Path = self.caminho_db / "anexos"

        self.caminho_anexo_selecionado: Optional[str] = None
        self.bytes_anexo_importado: Optional[bytes] = None

        self._criar_layout()
        self._carregar_anexos_existentes()
        self._atualizar_estado_botao_inserir()

    def _criar_layout(self) -> None:
        layout_principal = QVBoxLayout(self)
        layout_principal.setSpacing(12)

        # 1. Campo de texto/rótulo do botão
        label_texto = QLabel("Texto do Botão (Rótulo):")
        label_texto.setStyleSheet("font-weight: bold; font-size: 9pt;")
        self.input_texto = QLineEdit(self)
        self.input_texto.setPlaceholderText("Ex: Baixar Ficha de Autorização, Acessar Site...")
        layout_principal.addWidget(label_texto)
        layout_principal.addWidget(self.input_texto)

        # Separador visual
        linha = QFrame(self)
        linha.setFrameShape(QFrame.Shape.HLine)
        linha.setFrameShadow(QFrame.Shadow.Sunken)
        layout_principal.addWidget(linha)

        # 2. Abas: Documento Anexo vs Link Externo
        self.tab_widget = QTabWidget(self)

        # --- Aba 0: Documento Anexo ---
        tab_anexos = QWidget()
        layout_anexos = QVBoxLayout(tab_anexos)
        layout_anexos.setSpacing(8)

        # Botão Importar Arquivo
        self.btn_importar_anexo = QPushButton("📁 Importar Novo Arquivo...", tab_anexos)
        self.btn_importar_anexo.clicked.connect(self._ao_clicar_importar_anexo)
        layout_anexos.addWidget(self.btn_importar_anexo)

        self.label_anexo_importado = QLabel("", tab_anexos)
        self.label_anexo_importado.setStyleSheet("color: #2b579a; font-size: 8.5pt;")
        self.label_anexo_importado.hide()
        layout_anexos.addWidget(self.label_anexo_importado)

        # Campo de busca de anexos existentes
        self.input_busca_anexo = QLineEdit(tab_anexos)
        self.input_busca_anexo.setPlaceholderText("🔍 Filtrar anexos existentes...")
        self.input_busca_anexo.textChanged.connect(self._ao_filtrar_anexos)
        layout_anexos.addWidget(self.input_busca_anexo)

        # Lista de anexos existentes
        self.lista_anexos = QListWidget(tab_anexos)
        self.lista_anexos.currentRowChanged.connect(self._ao_selecionar_anexo_lista)
        layout_anexos.addWidget(self.lista_anexos)

        self.tab_widget.addTab(tab_anexos, "📎 Documento Anexo")

        # --- Aba 1: Link Externo (Web) ---
        tab_web = QWidget()
        layout_web = QVBoxLayout(tab_web)
        layout_web.setSpacing(8)

        label_url = QLabel("Endereço Web (URL):")
        label_url.setStyleSheet("font-weight: bold; font-size: 9pt;")
        layout_web.addWidget(label_url)

        self.input_url = QLineEdit(tab_web)
        self.input_url.setPlaceholderText("https://exemplo.com ou mailto:contato@exemplo.com")
        layout_web.addWidget(self.input_url)
        layout_web.addStretch()

        self.tab_widget.addTab(tab_web, "🌐 Link Externo (Web)")

        layout_principal.addWidget(self.tab_widget)

        # 3. Botões de Ação na parte inferior
        layout_botoes = QHBoxLayout()
        layout_botoes.addStretch()

        self.btn_cancelar = QPushButton("Cancelar", self)
        self.btn_cancelar.clicked.connect(self.reject)
        layout_botoes.addWidget(self.btn_cancelar)

        self.btn_inserir = QPushButton("Inserir Botão", self)
        self.btn_inserir.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 5px 15px;
                background-color: #2b579a;
                color: white;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.btn_inserir.clicked.connect(self.accept)
        layout_botoes.addWidget(self.btn_inserir)

        layout_principal.addLayout(layout_botoes)

        # Conecta sinais após todos os widgets estarem prontos
        self.input_texto.textChanged.connect(self._atualizar_estado_botao_inserir)
        self.tab_widget.currentChanged.connect(self._atualizar_estado_botao_inserir)
        self.input_url.textChanged.connect(self._atualizar_estado_botao_inserir)

    def _carregar_anexos_existentes(self) -> None:
        """Lista os arquivos anexos do disco e também da memória do CroquiModel."""
        self.lista_anexos.clear()
        arquivos_vistos = set()

        # 1. Anexos no disco
        if self.pasta_anexos.exists() and self.pasta_anexos.is_dir():
            for f in sorted(self.pasta_anexos.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(self.pasta_anexos).as_posix()
                    caminho_completo = f"anexos/{rel}"
                    arquivos_vistos.add(caminho_completo)
                    item = QListWidgetItem(f"📄 {rel}")
                    item.setData(Qt.ItemDataRole.UserRole, caminho_completo)
                    self.lista_anexos.addItem(item)

        # 2. Anexos na memória RAM do CroquiModel
        if self.model and hasattr(self.model, "obter_anexos_em_memoria"):
            anexos_mem = self.model.obter_anexos_em_memoria()
            for caminho_rel in sorted(anexos_mem.keys()):
                if caminho_rel not in arquivos_vistos:
                    arquivos_vistos.add(caminho_rel)
                    rel = caminho_rel[len("anexos/"):] if caminho_rel.startswith("anexos/") else caminho_rel
                    item = QListWidgetItem(f"📄 {rel} (novo)")
                    item.setData(Qt.ItemDataRole.UserRole, caminho_rel)
                    self.lista_anexos.addItem(item)

    def _ao_filtrar_anexos(self, texto_busca: str) -> None:
        texto = texto_busca.lower().strip()
        for i in range(self.lista_anexos.count()):
            item = self.lista_anexos.item(i)
            caminho = item.data(Qt.ItemDataRole.UserRole) or ""
            ocultar = bool(texto and texto not in item.text().lower() and texto not in caminho.lower())
            item.setHidden(ocultar)

    def _ao_selecionar_anexo_lista(self, row: int) -> None:
        if row >= 0:
            item = self.lista_anexos.item(row)
            if item:
                self.caminho_anexo_selecionado = item.data(Qt.ItemDataRole.UserRole)
                self.bytes_anexo_importado = None
                self.label_anexo_importado.hide()
        self._atualizar_estado_botao_inserir()

    def _ao_clicar_importar_anexo(self) -> None:
        caminho_arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Documento Anexo",
            "",
            "Documentos (*.pdf *.doc *.docx *.txt *.zip);;Todos os arquivos (*.*)",
        )
        if caminho_arquivo:
            self.importar_arquivo_anexo(Path(caminho_arquivo))

    def importar_arquivo_anexo(self, caminho_arquivo: Union[Path, str]) -> None:
        """Processa e importa um arquivo externo para inclusão em anexos/."""
        path = Path(caminho_arquivo)
        if not path.is_file():
            return

        nome_sanitizado = sanitizar_nome_arquivo_anexo(path.name)
        caminho_relativo = f"anexos/{nome_sanitizado}"
        conteudo = path.read_bytes()

        self.caminho_anexo_selecionado = caminho_relativo
        self.bytes_anexo_importado = conteudo

        # Limpa seleção da lista para priorizar o importado
        self.lista_anexos.setCurrentRow(-1)

        self.label_anexo_importado.setText(f"Arquivo importado pronto para inserção:\n{nome_sanitizado}")
        self.label_anexo_importado.show()
        self._atualizar_estado_botao_inserir()

    def _atualizar_estado_botao_inserir(self) -> None:
        """Habilita o botão Inserir apenas se houver texto e um destino válido."""
        if not hasattr(self, "btn_inserir") or not hasattr(self, "input_texto"):
            return

        tem_texto = bool(self.input_texto.text().strip())
        destino_valido = False

        indice_aba = self.tab_widget.currentIndex()
        if indice_aba == 0:
            # Aba Anexos
            destino_valido = bool(self.caminho_anexo_selecionado)
        elif indice_aba == 1:
            # Aba Link Externo
            destino_valido = bool(self.input_url.text().strip())

        self.btn_inserir.setEnabled(tem_texto and destino_valido)

    def obter_tag_markdown(self) -> str:
        """Gera a tag Markdown no formato [Texto](Destino)."""
        texto = self.obter_texto_botao()
        indice_aba = self.tab_widget.currentIndex()
        if indice_aba == 0:
            destino = self.obter_caminho_anexo() or ""
        else:
            destino = self.input_url.text().strip()
        return f"[{texto}]({destino})"

    def obter_texto_botao(self) -> str:
        """Retorna o rótulo/texto definido para o botão."""
        return self.input_texto.text().strip()

    def obter_caminho_anexo(self) -> Optional[str]:
        """Retorna o caminho relativo do anexo (ex: 'anexos/ficha.pdf') ou None se for link externo."""
        if self.tab_widget.currentIndex() == 0:
            return self.caminho_anexo_selecionado
        return None

    def obter_bytes_anexo(self) -> Optional[bytes]:
        """Retorna os bytes do arquivo anexo se foi importado de fora, ou None."""
        if self.tab_widget.currentIndex() == 0:
            return self.bytes_anexo_importado
        return None

    def accept(self) -> None:
        """Valida que campos obrigatórios foram preenchidos antes de fechar."""
        tem_texto = bool(self.input_texto.text().strip())
        indice_aba = self.tab_widget.currentIndex()
        destino_valido = False
        if indice_aba == 0:
            destino_valido = bool(self.caminho_anexo_selecionado)
        elif indice_aba == 1:
            destino_valido = bool(self.input_url.text().strip())

        if not (tem_texto and destino_valido):
            return

        super().accept()
