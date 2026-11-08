# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Wizard moderno e unificado para adição e substituição de imagens e mapas no croqui.
Oferece duas abas em todos os fluxos:
- Aba 0 ("Importar Nova Imagem"): seleção por botão, drag & drop, recorte interativo
  (rubber-band crop), painel de metadados ricos e validação contínua de nomes/colisões.
- Aba 1 ("Imagens do Croqui"): galeria pesquisável em tempo real listando todas as
  imagens existentes na pasta imagens/ do disco e no buffer em memória RAM.
Suporta modo de destino fixo (caminho_destino_fixo) e modo de substituição de mapa
com opção de reajuste proporcional de POIs (chk_reescalar_pois).
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from editor.core.processamento_imagem_campo import (
    AREA_MAXIMA_ESCALADA,
    AREA_MAXIMA_PADRAO,
    METODO_WEBP_PADRAO,
    QUALIDADE_WEBP_ESCALADA,
    QUALIDADE_WEBP_PADRAO,
    comprimir_imagem_para_bytes_webp,
    garantir_suporte_heif,
    obter_metadados_imagem,
    sanitizar_nome_imagem,
)
from editor.core.transformacoes_imagem import cortar_imagem_bytes
from editor.views.componentes.area_drop_imagem import (
    EXTENSOES_IMAGEM_SUPORTADAS as EXTENSOES_IMAGEM_SUPORTADAS,
)
from editor.views.componentes.area_drop_imagem import (
    FILTRO_ARQUIVOS_IMAGEM,
    AreaDropImagem,
)
from editor.views.dialogos.componentes_dialogo_imagem import (
    obter_bytes_imagem_croqui,
    obter_icone_miniatura_imagem,
)


class DialogoAdicionarMapa(QDialog):
    """
    Wizard unificado para entrada e substituição de mapas e imagens do croqui.
    """

    def __init__(
        self,
        nome_sugerido: str = "novo_mapa.webp",
        db_dir: Path | None = None,
        model: Any | None = None,
        parent: QWidget | None = None,
        eh_escalada: bool = False,
        max_area_override: int | None = None,
        caminho_destino_fixo: str | None = None,
        modo_substituicao_mapa: bool = False,
        largura_mapa_antiga: int = 0,
        altura_mapa_antiga: int = 0,
        qtd_pois_mapa: int = 0,
        titulo_janela: str | None = None,
        texto_botao_ok: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.db_dir: Path | None = Path(db_dir) if db_dir else None
        self.model: Any | None = model
        self.bytes_processados_webp: bytes | None = None
        self.dimensoes: tuple[int, int] | None = None
        self.bytes_originais_carregados: bytes | None = None
        self.nome_sugerido_origem: str | None = None
        self.corte_ativo: bool = False

        self.nome_imagem_galeria_selecionada: str = ""
        self.bytes_galeria_selecionada: bytes | None = None
        self.dimensoes_galeria: tuple[int, int] | None = None
        self._galeria_carregada: bool = False

        self.caminho_destino_fixo: str | None = (
            sanitizar_nome_imagem(Path(caminho_destino_fixo).name) if caminho_destino_fixo else None
        )
        self.modo_substituicao_mapa: bool = modo_substituicao_mapa
        self.largura_mapa_antiga: int = int(largura_mapa_antiga or 0)
        self.altura_mapa_antiga: int = int(altura_mapa_antiga or 0)
        self.qtd_pois_mapa: int = int(qtd_pois_mapa or 0)
        self.caminho_permitido_sobrescrever: str | None = None
        if self.caminho_destino_fixo:
            self.caminho_permitido_sobrescrever = f"imagens/{self.caminho_destino_fixo}"
        elif self.modo_substituicao_mapa and nome_sugerido:
            self.caminho_permitido_sobrescrever = f"imagens/{sanitizar_nome_imagem(nome_sugerido)}"

        if titulo_janela:
            self.setWindowTitle(titulo_janela)
        elif self.modo_substituicao_mapa or self.caminho_destino_fixo:
            self.setWindowTitle("Substituir Imagem")
        else:
            self.setWindowTitle("Adicionar Novo Mapa")

        # Identifica se o mapa/imagem usa perfil de 1.0 MP (escalada ou capa)
        self.eh_escalada: bool = (
            eh_escalada or nome_sugerido.startswith("boulder_") or nome_sugerido.startswith("via_")
        )
        if max_area_override is not None:
            self.max_area: int = int(max_area_override)
        else:
            self.max_area = AREA_MAXIMA_ESCALADA if self.eh_escalada else AREA_MAXIMA_PADRAO
        self.qualidade_webp: int = (
            QUALIDADE_WEBP_ESCALADA if self.eh_escalada else QUALIDADE_WEBP_PADRAO
        )
        self.metodo_webp: int = METODO_WEBP_PADRAO

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.tab_widget = QTabWidget(self)

        # -------------------------------------------------------------------
        # Aba 0: Importar Nova Imagem
        # -------------------------------------------------------------------
        self.aba_importar = QWidget()
        layout_importar = QVBoxLayout(self.aba_importar)
        layout_importar.setSpacing(10)
        layout_importar.setContentsMargins(10, 10, 10, 10)

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
        layout_importar.addWidget(self.banner_dica)

        self.area_drop = AreaDropImagem(self.aba_importar)
        self.area_drop.imagem_selecionada.connect(self.carregar_imagem_arquivo)
        self.area_drop.regiao_selecionada.connect(self._ao_selecionar_regiao)
        layout_importar.addWidget(self.area_drop)

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
        layout_importar.addLayout(layout_corte)

        self.rotulo_metadados = QLabel("")
        self.rotulo_metadados.setStyleSheet(
            "color: #444; font-size: 12px; background: #f0f0f0; padding: 6px; border-radius: 4px;"
        )
        self.rotulo_metadados.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_metadados.hide()
        layout_importar.addWidget(self.rotulo_metadados)

        divisor = QFrame()
        divisor.setFrameShape(QFrame.Shape.HLine)
        divisor.setFrameShadow(QFrame.Shadow.Sunken)
        layout_importar.addWidget(divisor)

        layout_nome = QHBoxLayout()
        lbl_nome = QLabel("Nome do Arquivo (Destino):")
        lbl_nome.setMinimumWidth(160)
        nome_inicial_input = (
            self.caminho_destino_fixo if self.caminho_destino_fixo else nome_sugerido
        )
        self.input_nome = QLineEdit(nome_inicial_input)
        if self.caminho_destino_fixo:
            self.input_nome.setReadOnly(True)
        self.input_nome.textChanged.connect(self._ao_alterar_nome)
        layout_nome.addWidget(lbl_nome)
        layout_nome.addWidget(self.input_nome)
        layout_importar.addLayout(layout_nome)

        self.rotulo_caminho_destino = QLabel()
        self.rotulo_caminho_destino.setStyleSheet("color: #666; font-size: 11px;")
        layout_importar.addWidget(self.rotulo_caminho_destino)

        self.rotulo_aviso = QLabel("")
        self.rotulo_aviso.setStyleSheet("color: red; font-weight: bold; font-size: 12px;")
        layout_importar.addWidget(self.rotulo_aviso)

        # -------------------------------------------------------------------
        # Aba 1: Imagens do Croqui (Galeria do disco + RAM)
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

        self.rotulo_metadados_galeria = QLabel("")
        self.rotulo_metadados_galeria.setStyleSheet(
            "color: #444; font-size: 12px; background: #f0f0f0; padding: 6px; border-radius: 4px;"
        )
        self.rotulo_metadados_galeria.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rotulo_metadados_galeria.hide()
        layout_galeria.addWidget(self.rotulo_metadados_galeria)

        self.tab_widget.addTab(self.aba_importar, "Importar Nova Imagem")
        self.tab_widget.addTab(self.aba_galeria, "Imagens do Croqui")
        self.tab_widget.currentChanged.connect(self._ao_trocar_aba)
        layout.addWidget(self.tab_widget)

        # Opção de reajuste proporcional de POIs (visível no modo substituição de mapa quando resolução muda)
        self.chk_reescalar_pois = QCheckBox(self)
        self.chk_reescalar_pois.setChecked(True)
        self.chk_reescalar_pois.hide()
        layout.addWidget(self.chk_reescalar_pois)

        # Botões de confirmação
        self.bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_ok = self.bbox.button(QDialogButtonBox.StandardButton.Ok)
        if texto_botao_ok:
            self.btn_ok.setText(texto_botao_ok)
        elif self.modo_substituicao_mapa or self.caminho_destino_fixo:
            self.btn_ok.setText("Substituir Imagem")
        else:
            self.btn_ok.setText("Adicionar Mapa")
        self.btn_ok.setEnabled(False)

        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        layout.addWidget(self.bbox)

        self.resize(560, 520)
        self._validar_estado()

    def _carregar_imagens_existentes(self) -> None:
        self.lista_imagens.clear()
        self._galeria_carregada = True
        nomes_adicionados: set[str] = set()
        extensoes = {".webp", ".png", ".jpg", ".jpeg", ".bmp"}
        pasta_imagens = (self.db_dir / "imagens") if self.db_dir else None

        if pasta_imagens and pasta_imagens.exists():
            for arquivo in sorted(pasta_imagens.iterdir()):
                if arquivo.is_file() and arquivo.suffix.lower() in extensoes:
                    icone = obter_icone_miniatura_imagem(
                        arquivo.name, pasta_imagens=pasta_imagens, model=self.model
                    )
                    if icone is not None:
                        item = QListWidgetItem(arquivo.name)
                        item.setIcon(icone)
                        item.setData(Qt.ItemDataRole.UserRole, arquivo.name)
                        self.lista_imagens.addItem(item)
                        nomes_adicionados.add(arquivo.name)

        if self.model and hasattr(self.model, "obter_imagens_em_memoria"):
            for caminho_rel in sorted(self.model.obter_imagens_em_memoria().keys()):
                caminho_norm = str(caminho_rel).replace("\\", "/")
                if caminho_norm.startswith("imagens/"):
                    nome = caminho_norm.split("/", 1)[1]
                    if nome not in nomes_adicionados and any(
                        nome.lower().endswith(ext) for ext in extensoes
                    ):
                        icone = obter_icone_miniatura_imagem(
                            nome, pasta_imagens=pasta_imagens, model=self.model
                        )
                        if icone is not None:
                            item = QListWidgetItem(nome)
                            item.setIcon(icone)
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
        pasta_imagens = (self.db_dir / "imagens") if self.db_dir else None
        if itens:
            nome_sel = str(itens[0].data(Qt.ItemDataRole.UserRole) or itens[0].text())
            bytes_brutos = obter_bytes_imagem_croqui(
                nome_sel, pasta_imagens=pasta_imagens, model=self.model
            )
            if bytes_brutos:
                self.nome_imagem_galeria_selecionada = nome_sel
                w, h, _, txt_tam = obter_metadados_imagem(bytes_brutos)
                self.bytes_galeria_selecionada = bytes_brutos
                self.dimensoes_galeria = (w, h)
                self.rotulo_metadados_galeria.setText(
                    f"Selecionado: {self.nome_imagem_galeria_selecionada}  |  "
                    f"Dimensões: {w} x {h} px  |  Tamanho: {txt_tam}"
                )
                self.rotulo_metadados_galeria.show()
                self._validar_estado()
                return

        self.nome_imagem_galeria_selecionada = ""
        self.bytes_galeria_selecionada = None
        self.dimensoes_galeria = None
        self.rotulo_metadados_galeria.hide()
        self._validar_estado()

    def _ao_duplo_clique_galeria(self, item: QListWidgetItem) -> None:
        self.lista_imagens.setCurrentItem(item)
        self._ao_selecionar_item_galeria()
        if self.btn_ok.isEnabled():
            self.accept()

    def _ao_trocar_aba(self, indice: int) -> None:
        if indice == 1 and not self._galeria_carregada:
            self._carregar_imagens_existentes()
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

    def carregar_imagem_bytes(
        self, bytes_originais: bytes, nome_sugerido_origem: str | None = None
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

        self.area_drop.definir_preview_bytes(bytes_webp)

        _, _, tam_webp, txt_tam_webp = obter_metadados_imagem(bytes_webp)
        self.rotulo_metadados.setText(
            f"Dimensões: {w_final} x {h_final} px  |  "
            f"Tamanho WebP: {txt_tam_webp} (Original: {txt_tam_orig})"
        )
        self.rotulo_metadados.show()

        if (
            not self.caminho_destino_fixo
            and nome_sugerido_origem
            and (not self.input_nome.text() or self.input_nome.text() == "novo_mapa.webp")
        ):
            slug = sanitizar_nome_imagem(nome_sugerido_origem)
            self.input_nome.setText(slug)

        self._validar_estado()

    def _ao_selecionar_regiao(self, _rect: tuple[int, int, int, int]) -> None:
        self.btn_recortar.setEnabled(True)

    def _ao_clicar_recortar(self) -> None:
        rect = self.area_drop.obter_retangulo_selecionado_imagem()
        if rect:
            self.aplicar_corte(rect)

    def aplicar_corte(self, retangulo: tuple[int, int, int, int]) -> None:
        """
        Recorta a imagem original na região retangular especificada (x1, y1, x2, y2)
        e a re-processa mantendo máxima fidelidade e orçamento estrito.
        """
        if not self.bytes_originais_carregados:
            return

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
            f"Dimensões: {w_final} x {h_final} px (Recortado)  |  Tamanho WebP: {txt_tam_webp}"
        )
        self._validar_estado()

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

        w_orig, h_orig, tam_orig, txt_tam_orig = obter_metadados_imagem(
            self.bytes_originais_carregados
        )
        _, _, tam_webp, txt_tam_webp = obter_metadados_imagem(bytes_webp)
        self.rotulo_metadados.setText(
            f"Dimensões: {w_final} x {h_final} px  |  "
            f"Tamanho WebP: {txt_tam_webp} (Original: {txt_tam_orig})"
        )
        self._validar_estado()

    def _ao_alterar_nome(self, _texto: str) -> None:
        self._validar_estado()

    def obter_caminho_final_relativo(self) -> str:
        if self.caminho_destino_fixo:
            return f"imagens/{self.caminho_destino_fixo}"
        if self.tab_widget.currentIndex() == 1 and self.nome_imagem_galeria_selecionada:
            return f"imagens/{self.nome_imagem_galeria_selecionada}"
        txt = self.input_nome.text().strip()
        slug = sanitizar_nome_imagem(txt or "mapa")
        return f"imagens/{slug}"

    def obter_caminho_final_absoluto(self) -> Path | None:
        if self.db_dir:
            return self.db_dir / self.obter_caminho_final_relativo()
        return None

    def obter_bytes_imagem_processada(self) -> bytes | None:
        if self.tab_widget.currentIndex() == 1:
            return self.bytes_galeria_selecionada
        return self.bytes_processados_webp

    def obter_dimensoes_imagem(self) -> tuple[int, int] | None:
        if self.tab_widget.currentIndex() == 1:
            return self.dimensoes_galeria
        return self.dimensoes

    def deve_reescalar_pois(self) -> bool:
        return bool(
            self.modo_substituicao_mapa
            and not self.chk_reescalar_pois.isHidden()
            and self.chk_reescalar_pois.isChecked()
        )

    def _atualizar_visibilidade_checkbox_pois(self) -> None:
        dims = self.obter_dimensoes_imagem()
        if (
            self.modo_substituicao_mapa
            and self.qtd_pois_mapa > 0
            and self.largura_mapa_antiga > 0
            and self.altura_mapa_antiga > 0
            and dims is not None
            and dims != (self.largura_mapa_antiga, self.altura_mapa_antiga)
        ):
            self.chk_reescalar_pois.setText(
                f"Reajustar proporcionalmente os {self.qtd_pois_mapa} Pontos de Interesse (POIs) "
                f"de {self.largura_mapa_antiga}x{self.altura_mapa_antiga} para {dims[0]}x{dims[1]} px"
            )
            self.chk_reescalar_pois.show()
        else:
            self.chk_reescalar_pois.hide()

    def _validar_estado(self) -> None:
        self._atualizar_visibilidade_checkbox_pois()

        if self.tab_widget.currentIndex() == 1:
            tem_sel = bool(
                self.nome_imagem_galeria_selecionada and self.bytes_galeria_selecionada is not None
            )
            self.btn_ok.setEnabled(tem_sel)
            return

        caminho_rel = self.obter_caminho_final_relativo()
        self.rotulo_caminho_destino.setText(f"Destino no croqui: {caminho_rel}")

        # 1. Verifica se tem imagem selecionada
        if not self.bytes_processados_webp:
            self.rotulo_aviso.setText("")
            self.btn_ok.setEnabled(False)
            return

        caminho_padrao = str(caminho_rel).replace("\\", "/")
        eh_mesmo_permitido = (
            self.caminho_permitido_sobrescrever is not None
            and caminho_padrao == self.caminho_permitido_sobrescrever
        )

        # 2. Verifica se o nome já existe na RAM
        if (
            not eh_mesmo_permitido
            and self.model
            and hasattr(self.model, "obter_imagens_em_memoria")
        ):
            imagens_ram = self.model.obter_imagens_em_memoria()
            if caminho_padrao in imagens_ram:
                self.rotulo_aviso.setText(
                    f"⚠ O arquivo '{Path(caminho_rel).name}' já existe na memória RAM. Escolha outro nome."
                )
                self.btn_ok.setEnabled(False)
                return

        # 3. Verifica se o nome já existe no disco
        if not eh_mesmo_permitido and self.db_dir:
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
        if not self.obter_bytes_imagem_processada():
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma imagem.")
            return

        self._validar_estado()
        if not self.btn_ok.isEnabled():
            return

        super().accept()
