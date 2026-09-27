# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Diálogo moderno e robusto para adicionar um novo mapa ao croqui.
Suporta seleção por botão, arrastar e soltar (drag & drop), painel de metadados ricos,
pré-processamento automático para WebP em memória RAM e validação contínua de nomes/colisões.
"""

from pathlib import Path
from typing import Optional, Tuple, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QDialogButtonBox,
    QWidget,
    QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QImage

from editor.core.processamento_imagem_campo import (
    sanitizar_nome_imagem,
    obter_metadados_imagem,
    comprimir_imagem_para_bytes_webp,
    verificar_conflito_nome_imagem,
    garantir_suporte_heif,
    AREA_MAXIMA_PADRAO,
    QUALIDADE_WEBP_PADRAO,
    METODO_WEBP_PADRAO,
    AREA_MAXIMA_ESCALADA,
    QUALIDADE_WEBP_ESCALADA,
)
from editor.core.transformacoes_imagem import cortar_imagem_bytes


from editor.views.componentes.area_drop_imagem import (
    AreaDropImagem,
    EXTENSOES_IMAGEM_SUPORTADAS,
    FILTRO_ARQUIVOS_IMAGEM,
)


class DialogoAdicionarMapa(QDialog):
    """
    Diálogo para cadastro de novo mapa com pré-processamento WebP, validação contínua de nomes
    e ferramenta de recorte interativo (rubber-band crop) com perfil otimizado para escaladas.
    """
    def __init__(
        self,
        nome_sugerido: str,
        db_dir: Optional[Path] = None,
        model: Optional[Any] = None,
        parent: Optional[QWidget] = None,
        eh_escalada: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Adicionar Novo Mapa")
        self.db_dir: Optional[Path] = Path(db_dir) if db_dir else None
        self.model: Optional[Any] = model
        self.bytes_processados_webp: Optional[bytes] = None
        self.dimensoes: Optional[Tuple[int, int]] = None
        self.bytes_originais_carregados: Optional[bytes] = None
        self.nome_sugerido_origem: Optional[str] = None
        self.corte_ativo: bool = False

        # Identifica se o mapa é para o contexto de escalada individual
        self.eh_escalada: bool = (
            eh_escalada
            or nome_sugerido.startswith("boulder_")
            or nome_sugerido.startswith("via_")
        )
        self.max_area: int = AREA_MAXIMA_ESCALADA if self.eh_escalada else AREA_MAXIMA_PADRAO
        self.qualidade_webp: int = QUALIDADE_WEBP_ESCALADA if self.eh_escalada else QUALIDADE_WEBP_PADRAO
        self.metodo_webp: int = METODO_WEBP_PADRAO

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Cabeçalho com botão explícito
        linha_cabecalho = QHBoxLayout()
        lbl_instrucao = QLabel("Selecione ou arraste a imagem do mapa para convertê-la para WebP:")
        lbl_instrucao.setStyleSheet("color: #333; font-weight: 500;")
        self.btn_selecionar = QPushButton("Selecionar Imagem...")
        self.btn_selecionar.setStyleSheet("padding: 6px 12px; font-weight: bold;")
        self.btn_selecionar.clicked.connect(self._abrir_seletor_arquivos)
        linha_cabecalho.addWidget(lbl_instrucao)
        linha_cabecalho.addStretch()
        linha_cabecalho.addWidget(self.btn_selecionar)
        layout.addLayout(linha_cabecalho)

        # Banner informativo de dica de qualidade para escaladas
        self.banner_dica = QLabel(
            "💡 Dica de Qualidade: Selecione a área desejada da imagem para focar (ex: saída do boulder, agarras ou crux) "
            "e preservar a maior nitidez possível dentro do limite de 1.0 MP."
        )
        self.banner_dica.setWordWrap(True)
        self.banner_dica.setStyleSheet(
            "background-color: #e8f4fd; color: #0c5460; border: 1px solid #bee5eb; "
            "border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: 500;"
        )
        if not self.eh_escalada:
            self.banner_dica.hide()
        layout.addWidget(self.banner_dica)

        # Área de drag & drop com seleção rubber-band
        self.area_drop = AreaDropImagem(self)
        self.area_drop.imagem_selecionada.connect(self.carregar_imagem_arquivo)
        self.area_drop.regiao_selecionada.connect(self._ao_selecionar_regiao)
        layout.addWidget(self.area_drop)

        # Barra de ferramentas para recorte
        layout_corte = QHBoxLayout()
        self.btn_recortar = QPushButton("✂ Recortar Área Selecionada")
        self.btn_recortar.setEnabled(False)
        self.btn_recortar.clicked.connect(self._ao_clicar_recortar)
        self.btn_reverter_corte = QPushButton("↺ Reverter Imagem Original")
        self.btn_reverter_corte.setEnabled(False)
        self.btn_reverter_corte.clicked.connect(self.reverter_corte)
        layout_corte.addWidget(self.btn_recortar)
        layout_corte.addWidget(self.btn_reverter_corte)
        layout_corte.addStretch()
        layout.addLayout(layout_corte)

        # Painel de metadados da imagem
        self.rotulo_metadados = QLabel("")
        self.rotulo_metadados.setStyleSheet("color: #444; font-size: 12px; background: #f0f0f0; padding: 6px; border-radius: 4px;")
        self.rotulo_metadados.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_metadados.hide()
        layout.addWidget(self.rotulo_metadados)

        # Divisor
        divisor = QFrame()
        divisor.setFrameShape(QFrame.Shape.HLine)
        divisor.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(divisor)

        # Campo de nome do arquivo de destino
        layout_nome = QHBoxLayout()
        lbl_nome = QLabel("Nome do Arquivo (Destino):")
        lbl_nome.setMinimumWidth(160)
        self.input_nome = QLineEdit(nome_sugerido)
        self.input_nome.textChanged.connect(self._ao_alterar_nome)
        layout_nome.addWidget(lbl_nome)
        layout_nome.addWidget(self.input_nome)
        layout.addLayout(layout_nome)

        # Rótulo de caminho final relativo
        self.rotulo_caminho_destino = QLabel()
        self.rotulo_caminho_destino.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.rotulo_caminho_destino)

        # Rótulo de aviso de erro/conflito
        self.rotulo_aviso = QLabel("")
        self.rotulo_aviso.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.rotulo_aviso)

        # Botões de confirmação
        self.bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_ok = self.bbox.button(QDialogButtonBox.StandardButton.Ok)
        self.btn_ok.setText("Adicionar Mapa")
        self.btn_ok.setEnabled(False)

        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        layout.addWidget(self.bbox)

        self.resize(540, 480)
        self._validar_estado()

    def _abrir_seletor_arquivos(self) -> None:
        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem do Mapa",
            "",
            FILTRO_ARQUIVOS_IMAGEM,
        )
        if arquivo:
            self.carregar_imagem_arquivo(arquivo)

    def carregar_imagem_arquivo(self, caminho_arquivo: str) -> None:
        caminho = Path(caminho_arquivo)
        if not caminho.exists() or not caminho.is_file():
            QMessageBox.warning(self, "Erro", "Arquivo não encontrado.")
            return

        try:
            bytes_originais = caminho.read_bytes()
            self.carregar_imagem_bytes(bytes_originais, nome_sugerido_origem=caminho.name)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao ler arquivo: {e}")

    def carregar_imagem_bytes(self, bytes_originais: bytes, nome_sugerido_origem: Optional[str] = None) -> None:
        w_orig, h_orig, tam_orig, txt_tam_orig = obter_metadados_imagem(bytes_originais)
        if w_orig <= 0 or h_orig <= 0:
            ext = Path(nome_sugerido_origem or "").suffix.lower()
            eh_heic = (ext in (".heic", ".heif")) or (len(bytes_originais) > 12 and b"ftyp" in bytes_originais[4:12])
            if eh_heic and not garantir_suporte_heif():
                QMessageBox.warning(
                    self,
                    "Erro",
                    "O suporte a imagens HEIC/HEIF requer a biblioteca 'pillow-heif'.\n"
                    "Reinicie o editor ou instale via 'pip install pillow-heif'."
                )
                return
            QMessageBox.warning(self, "Erro", "Formato de imagem inválido ou não suportado.")
            return

        self.bytes_originais_carregados = bytes_originais
        self.nome_sugerido_origem = nome_sugerido_origem
        self.corte_ativo = False
        self.btn_reverter_corte.setEnabled(False)
        self.btn_recortar.setEnabled(False)

        bytes_webp, w_final, h_final = comprimir_imagem_para_bytes_webp(
            bytes_originais,
            quality=self.qualidade_webp,
            max_area=self.max_area,
            method=self.metodo_webp,
        )
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

        # Atualiza nome do arquivo caso sugerido
        if nome_sugerido_origem and (not self.input_nome.text() or self.input_nome.text() == "novo_mapa.webp"):
            slug = sanitizar_nome_imagem(nome_sugerido_origem)
            self.input_nome.setText(slug)

        self._validar_estado()

    def _ao_selecionar_regiao(self, _rect: Tuple[int, int, int, int]) -> None:
        self.btn_recortar.setEnabled(True)

    def _ao_clicar_recortar(self) -> None:
        rect = self.area_drop.obter_retangulo_selecionado_imagem()
        if rect:
            self.aplicar_corte(rect)

    def aplicar_corte(self, retangulo: Tuple[int, int, int, int]) -> None:
        """
        Recorta a imagem original na região retangular especificada (x1, y1, x2, y2)
        e a re-processa mantendo máxima fidelidade e orçamento estrito.
        """
        if not self.bytes_originais_carregados:
            return

        try:
            bytes_cortados = cortar_imagem_bytes(
                self.bytes_originais_carregados,
                retangulo,
                qualidade=self.qualidade_webp,
                sem_perdas=False,
            )
            bytes_webp, w_final, h_final = comprimir_imagem_para_bytes_webp(
                bytes_cortados,
                quality=self.qualidade_webp,
                max_area=self.max_area,
                method=self.metodo_webp,
            )
            self.bytes_processados_webp = bytes_webp
            self.dimensoes = (w_final, h_final)
            self.corte_ativo = True

            self.area_drop.definir_preview_bytes(bytes_webp)
            self.btn_recortar.setEnabled(False)
            self.btn_reverter_corte.setEnabled(True)

            _, _, tam_webp, txt_tam_webp = obter_metadados_imagem(bytes_webp)
            self.rotulo_metadados.setText(
                f"Dimensões: {w_final} x {h_final} px (Recortado)  |  "
                f"Tamanho WebP: {txt_tam_webp}"
            )
            self._validar_estado()
        except Exception as e:
            QMessageBox.warning(self, "Erro no Recorte", f"Não foi possível aplicar o recorte: {e}")

    def reverter_corte(self) -> None:
        """Reverte a imagem recortada para a imagem original inteira."""
        if not self.bytes_originais_carregados:
            return

        self.area_drop.limpar_selecao()
        bytes_webp, w_final, h_final = comprimir_imagem_para_bytes_webp(
            self.bytes_originais_carregados,
            quality=self.qualidade_webp,
            max_area=self.max_area,
            method=self.metodo_webp,
        )
        self.bytes_processados_webp = bytes_webp
        self.dimensoes = (w_final, h_final)
        self.corte_ativo = False

        self.area_drop.definir_preview_bytes(bytes_webp)
        self.btn_recortar.setEnabled(False)
        self.btn_reverter_corte.setEnabled(False)

        w_orig, h_orig, tam_orig, txt_tam_orig = obter_metadados_imagem(self.bytes_originais_carregados)
        _, _, tam_webp, txt_tam_webp = obter_metadados_imagem(bytes_webp)
        self.rotulo_metadados.setText(
            f"Dimensões: {w_final} x {h_final} px  |  "
            f"Tamanho WebP: {txt_tam_webp} (Original: {txt_tam_orig})"
        )
        self._validar_estado()

    def _ao_alterar_nome(self, _texto: str) -> None:
        self._validar_estado()

    def obter_caminho_final_relativo(self) -> str:
        txt = self.input_nome.text().strip()
        slug = sanitizar_nome_imagem(txt or "mapa")
        return f"imagens/{slug}"

    def obter_caminho_final_absoluto(self) -> Optional[Path]:
        if self.db_dir:
            return self.db_dir / self.obter_caminho_final_relativo()
        return None

    def obter_bytes_imagem_processada(self) -> Optional[bytes]:
        return self.bytes_processados_webp

    def obter_dimensoes_imagem(self) -> Optional[Tuple[int, int]]:
        return self.dimensoes

    def _validar_estado(self) -> None:
        caminho_rel = self.obter_caminho_final_relativo()
        self.rotulo_caminho_destino.setText(f"Destino no croqui: {caminho_rel}")

        # 1. Verifica se tem imagem selecionada
        if not self.bytes_processados_webp:
            self.rotulo_aviso.setText("")
            self.btn_ok.setEnabled(False)
            return

        # 2. Verifica se o nome já existe na RAM
        if self.model and hasattr(self.model, "obter_imagens_em_memoria"):
            imagens_ram = self.model.obter_imagens_em_memoria()
            caminho_padrao = str(caminho_rel).replace("\\", "/")
            if caminho_padrao in imagens_ram:
                self.rotulo_aviso.setText(
                    f"⚠ O arquivo '{Path(caminho_rel).name}' já existe na memória RAM. Escolha outro nome."
                )
                self.btn_ok.setEnabled(False)
                return

        # 3. Verifica se o nome já existe no disco
        if self.db_dir:
            caminho_abs = self.db_dir / caminho_rel
            if caminho_abs.exists():
                self.rotulo_aviso.setText(
                    f"⚠ O arquivo '{caminho_abs.name}' já existe na pasta imagens/. Escolha outro nome."
                )
                self.btn_ok.setEnabled(False)
                return

        # Válido e livre
        self.rotulo_aviso.setText("")
        self.btn_ok.setEnabled(True)

    def accept(self) -> None:
        if not self.bytes_processados_webp:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma imagem.")
            return

        self._validar_estado()
        if not self.btn_ok.isEnabled():
            return

        super().accept()

