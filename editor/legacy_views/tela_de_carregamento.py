# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, 
    QLabel, QGroupBox, QInputDialog, QFileDialog, QProgressDialog, QMessageBox,
    QListWidgetItem, QWidget, QStyle, QPlainTextEdit, QApplication,
    QFormLayout, QLineEdit
)

import sys
import io
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from pathlib import Path
from datetime import datetime, timezone
import yaml
from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.legacy_views.dialogo_busca_croqui import DialogoBuscaCroqui
from editor.core.formatacao import para_snake_case, para_camel_case
from editor.views.estilo import Icones


class StreamToCallback(io.TextIOBase):
    """Encaminha stdout para um callback em tempo real."""
    def __init__(self, callback):
        self.callback = callback
    def write(self, s):
        if s.strip():
            self.callback(s.strip())
        return len(s)

class DialogoProgressoLog(QDialog):
    """Exibe o log de operações longas em tempo real."""
    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            background-color: #1e1e1e; 
            color: #d4d4d4; 
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 11px;
            padding: 5px;
        """)
        layout.addWidget(self.log_view)
        
        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setEnabled(False)
        self.btn_fechar.clicked.connect(self.accept)
        layout.addWidget(self.btn_fechar)
        
    def adicionar_log(self, texto):
        if getattr(self, '_in_log', False):
            return
        self._in_log = True
        try:
            self.log_view.appendPlainText(texto)
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
            QApplication.processEvents()
        finally:
            self._in_log = False

class DialogoNovoCroqui(QDialog):
    """
    Diálogo para coletar metadados e gerar o ID do novo croqui com validação visual.
    """
    def __init__(self, storage=None, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Criar Novo Croqui")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        info_label = QLabel("Preencha as informações básicas para inicializar o ambiente do croqui.")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        form_container = QGroupBox("Metadados do Pico")
        self.form_layout = QFormLayout(form_container)
        self.form_layout.setSpacing(10)
        
        self.edit_pico = QLineEdit()
        self.edit_pico.setPlaceholderText("Ex: Pedra do Baú")
        self.edit_pico.setMaxLength(60)
        self.edit_cidade = QLineEdit()
        self.edit_cidade.setPlaceholderText("Ex: São Bento do Sapucaí")
        self.edit_cidade.setMaxLength(60)
        self.edit_estado = QLineEdit()
        self.edit_estado.setPlaceholderText("Ex: SP")
        self.edit_estado.setMaxLength(2)
        self.edit_pais = QLineEdit()
        self.edit_pais.setPlaceholderText("Ex: BR")
        self.edit_pais.setText("BR")
        self.edit_pais.setMaxLength(2)
        
        self.form_layout.addRow("Nome do Pico:", self.edit_pico)
        self.form_layout.addRow("Cidade:", self.edit_cidade)
        self.form_layout.addRow("Estado (UF):", self.edit_estado)
        self.form_layout.addRow("País:", self.edit_pais)
        
        layout.addWidget(form_container)
        
        # Área do ID
        id_group = QGroupBox("Identificador Gerado")
        id_layout = QVBoxLayout(id_group)
        
        row_id = QHBoxLayout()
        self.edit_id = QLineEdit()
        self.edit_id.setReadOnly(True)
        self.edit_id.setStyleSheet("background-color: #f1f3f5; color: #495057; font-family: monospace; font-weight: bold;")
        
        self.icon_validacao = QLabel()
        self.lbl_validacao = QLabel("Aguardando dados...")
        self.lbl_validacao.setStyleSheet("font-size: 11px;")
        
        row_id.addWidget(self.edit_id)
        row_id.addWidget(self.icon_validacao)
        id_layout.addLayout(row_id)
        id_layout.addWidget(self.lbl_validacao)
        
        layout.addWidget(id_group)
        
        # Botões
        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_criar = QPushButton("Criar Croqui")
        self.btn_criar.setDefault(True)
        self.btn_criar.setEnabled(False)
        self.btn_criar.setStyleSheet("""
            QPushButton:enabled { background-color: #2da44e; color: white; border: none; font-weight: bold; }
            QPushButton:enabled:hover { background-color: #2c974b; }
            QPushButton:disabled { background-color: #ebf0f4; color: #8c959f; }
        """)
        self.btn_criar.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_criar)
        layout.addLayout(btn_layout)
        
        # Conexões
        self.edit_pico.textChanged.connect(self.atualizar_id)
        self.edit_cidade.textChanged.connect(self.atualizar_id)
        self.edit_estado.textChanged.connect(self.atualizar_id)
        self.edit_pais.textChanged.connect(self.atualizar_id)
        
    def atualizar_id(self):
        pico = self.edit_pico.text().strip()
        cidade = self.edit_cidade.text().strip()
        estado = self.edit_estado.text().strip()
        pais = self.edit_pais.text().strip()
        
        if not all([pico, cidade, estado, pais]):
            self.edit_id.setText("")
            self.lbl_validacao.setText("Preencha todos os campos para gerar o ID.")
            self.lbl_validacao.setStyleSheet("color: #666;")
            self.icon_validacao.clear()
            self.btn_criar.setEnabled(False)
            return
            
        # Geração do ID: <pais>_<estado>_<cidade>_<nome_pico_snake_case>
        id_gerado = f"{para_snake_case(pais)}_{para_snake_case(estado)}_{para_snake_case(cidade)}_{para_snake_case(pico)}"
        
        # Limita o ID gerado para evitar estourar limites do sistema de arquivos (WinError 123)
        if len(id_gerado) > 100:
            id_gerado = id_gerado[:100].rstrip("_")
            
        self.edit_id.setText(id_gerado)

        
        # Validação de existência
        disponivel = True
        if self.storage:
            caminho_exp = self.storage.obter_caminho_croquis_experimentais()
            if caminho_exp and caminho_exp.exists():
                for pasta in caminho_exp.iterdir():
                    if pasta.is_dir() and (pasta.name.endswith(f"_{id_gerado}") or pasta.name == id_gerado):
                        disponivel = False
                        break

        if disponivel:
            self.lbl_validacao.setText("ID disponível!")
            self.lbl_validacao.setStyleSheet("color: #2da44e;")
            self.icon_validacao.setPixmap(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton).pixmap(16, 16))
            self.btn_criar.setEnabled(True)
        else:
            self.lbl_validacao.setText("Este ID já existe no seu histórico.")
            self.lbl_validacao.setStyleSheet("color: #cf222e;")
            self.icon_validacao.setPixmap(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton).pixmap(16, 16))
            self.btn_criar.setEnabled(False)

    def obter_dados(self):
        return {
            "pico": self.edit_pico.text().strip(),
            "cidade": self.edit_cidade.text().strip(),
            "estado": self.edit_estado.text().strip().upper(),
            "pais": self.edit_pais.text().strip().upper(),
            "id": self.edit_id.text()
        }

class WidgetItemHistorico(QWidget):

    """
    Widget customizado para os itens da lista de histórico, exibindo metadados em múltiplas linhas.
    """
    excluir_clicado = pyqtSignal(str)

    def __init__(self, dados, caminho_pasta, parent=None):
        super().__init__(parent)
        self.caminho_pasta = caminho_pasta
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 4, 15, 4)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        # Título: Nome do Croqui
        self.label_nome = QLabel(dados.get("nome", "Sem Nome"))
        self.label_nome.setStyleSheet("font-weight: bold; font-size: 13px; color: #2c3e50;")
        text_layout.addWidget(self.label_nome)
        
        # Subtítulo: Resumo (se houver)
        if dados.get("resumo"):
            self.label_resumo = QLabel(f"\"{dados['resumo']}\"")
            self.label_resumo.setStyleSheet("color: #555; font-style: italic; font-size: 11px;")
            text_layout.addWidget(self.label_resumo)
            
        # Rodapé: ID e Datas
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(12)
        
        id_pasta = dados.get('id', 'N/A')
        texto_id = f"ID: {id_pasta}"
            
        self.lbl_id = QLabel(texto_id)
        self.lbl_id.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        
        self.lbl_edicao = QLabel(f"Última Edição: {dados.get('edicao', 'N/A')}")
        self.lbl_edicao.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        
        footer_layout.addWidget(self.lbl_id)
        footer_layout.addWidget(self.lbl_edicao)
        footer_layout.addStretch()
        
        text_layout.addLayout(footer_layout)
        main_layout.addLayout(text_layout)
        
        # Botão Excluir (Estilo GitHub Danger: Texto Vermelho, Borda Sutil)
        self.btn_excluir = QPushButton("Apagar")
        self.btn_excluir.setToolTip("Excluir croqui permanentemente")
        self.btn_excluir.setFixedHeight(32)
        self.btn_excluir.setStyleSheet("""
            QPushButton {
                color: #cf222e;
                background-color: #f6f8fa;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 0px 8px;
                font-weight: 500;
                font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #cf222e;
                border-color: #cf222e;
            }
        """)
        self.btn_excluir.clicked.connect(lambda: self.excluir_clicado.emit(self.caminho_pasta))
        main_layout.addWidget(self.btn_excluir, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

class TelaDeCarregamento(QDialog):
    """
    Tela de Carregamento (Dialog) do Editor Aresta.
    Exibe ações principais e lista de croquis experimentais.
    """
    def __init__(self, storage=None, usuario="Autor Desconhecido", parent=None):
        super().__init__(parent)
        self.storage = storage
        self.usuario = usuario
        self.gerenciador = GerenciadorCroquiExperimental(storage) if storage else None
        self.caminho_croqui_selecionado = None
        self.setWindowTitle("Iniciar Editor Aresta")
        self.setMinimumSize(650, 600)
        self.resize(750, 700)
        from PyQt6.QtGui import QIcon
        from editor.core.storage import GerenciadorCaminhos
        storage_atual = storage or GerenciadorCaminhos()
        caminho_logo_app = storage_atual.obter_caminho_recurso_interno("recursos/logo_app.png")
        self.setWindowIcon(QIcon(str(caminho_logo_app)))
        
        # Habilitar botões de minimizar/maximizar em QDialog
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        
        # Estilização
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin-top: 1.5ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                padding: 10px;
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: #ffffff;
            }
        """)

        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(20, 20, 20, 20)
        self.layout_principal.setSpacing(15)
        
        # 1. Topo: Grupo de Ações Principais
        self.grupo_acoes = QGroupBox("Começar Novo Trabalho")
        self.layout_acoes = QHBoxLayout(self.grupo_acoes)
        self.layout_acoes.setSpacing(10)
        
        self.btn_novo = QPushButton("Novo croqui")
        self.btn_importar = QPushButton("Importar croqui experimental")
        self.btn_oficial = QPushButton("Editar croqui oficial")
        
        self.layout_acoes.addWidget(self.btn_novo)
        self.layout_acoes.addWidget(self.btn_importar)
        self.layout_acoes.addWidget(self.btn_oficial)
        
        self.layout_principal.addWidget(self.grupo_acoes)
        
        # 2. Base: Histórico de Croquis Experimentais
        self.grupo_historico = QGroupBox("Continuar Trabalho em Andamento")
        self.layout_historico = QVBoxLayout(self.grupo_historico)
        self.layout_historico.setContentsMargins(5, 20, 5, 5)
        
        self.lista_croquis = QListWidget()
        self.lista_croquis.setSpacing(4)
        self.lista_croquis.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-bottom: 4px;
                padding: 4px;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
                border-color: #adb5bd;
            }
            QListWidget::item:selected {
                background-color: #f1f3f5;
                border-color: #ced4da;
                color: black;
            }
        """)
        self.layout_historico.addWidget(self.lista_croquis)
        
        self.label_historico_vazio = QLabel("Nenhum croqui no histórico")
        self.label_historico_vazio.setObjectName("label_historico_vazio")
        self.label_historico_vazio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_historico_vazio.setStyleSheet("color: #6c757d; font-style: italic; padding: 15px;")
        self.label_historico_vazio.hide()
        self.layout_historico.addWidget(self.label_historico_vazio)
        
        self.layout_principal.addWidget(self.grupo_historico)
        self.layout_principal.setStretch(1, 1) # Faz o histórico expandir
        
        # Conecta sinais
        self.btn_novo.clicked.connect(self.ao_clicar_novo)
        self.btn_importar.clicked.connect(self.ao_clicar_importar)
        self.btn_oficial.clicked.connect(self.ao_clicar_oficial)
        self.lista_croquis.itemDoubleClicked.connect(self.ao_clicar_item)
        
        # Carregamento inicial
        if self.storage:
            self.carregar_croquis()
        else:
            self.atualizar_estado_vazio()

    def carregar_croquis(self):
        self.lista_croquis.clear()
        if not self.storage:
            self.atualizar_estado_vazio()
            return
            
        caminho_croquis = self.storage.obter_caminho_croquis_experimentais()
        if not caminho_croquis or not caminho_croquis.exists():
            self.atualizar_estado_vazio()
            return
            
        lista_dados = []
        
        for pasta in caminho_croquis.iterdir():
            if pasta.is_dir():
                nome_pasta = pasta.name
                nome_legivel = nome_pasta.replace("_", " ").title()
                
                # Tenta ler as datas e resumo do YAML de metadados experimentais
                dados_historico = {
                    "nome": nome_legivel,
                    "id": nome_pasta,
                    "resumo": "",
                    "criacao": "N/A",
                    "edicao": "N/A",
                    "dt_edicao_raw": datetime.min.replace(tzinfo=timezone.utc) # Para ordenação
                }
                
                # 1. Tenta ler o nome real do croqui do database/croqui.yaml
                croqui_yaml_path = pasta / "database" / "croqui.yaml"
                if croqui_yaml_path.is_file():
                    try:
                        with open(croqui_yaml_path, "r", encoding="utf-8") as f:
                            c_yml = yaml.safe_load(f)
                            if c_yml and "nome" in c_yml:
                                dados_historico["nome"] = c_yml["nome"]
                            if c_yml and "id" in c_yml:
                                dados_historico["id_logico"] = c_yml["id"]
                    except Exception:
                        pass

                # 2. Tenta ler os metadados experimentais
                yaml_path = pasta / "croqui_experimental.yaml"
                if yaml_path.is_file():
                    try:
                        with open(yaml_path, "r", encoding="utf-8") as f:
                            yml = yaml.safe_load(f)
                            if yml:
                                if "resumo_edicao" in yml:
                                    dados_historico["resumo"] = yml["resumo_edicao"]
                                    
                                if "data_criacao" in yml:
                                    try:
                                        dt_criacao = datetime.fromisoformat(yml["data_criacao"].replace("Z", "+00:00")).astimezone()
                                        dados_historico["criacao"] = dt_criacao.strftime('%d/%m %H:%M')
                                    except Exception:
                                        pass
                                        
                                if "ultima_edicao" in yml:
                                    try:
                                        dt = datetime.fromisoformat(yml["ultima_edicao"].replace("Z", "+00:00"))
                                        dados_historico["dt_edicao_raw"] = dt
                                        dt_local = dt.astimezone()
                                        dados_historico["edicao"] = dt_local.strftime('%d/%m/%Y %H:%M')
                                    except Exception:
                                        dados_historico["edicao"] = yml["ultima_edicao"]
                    except Exception:
                        pass

                lista_dados.append((pasta, dados_historico))

        # Ordenar por data de edição decrescente
        lista_dados.sort(key=lambda x: x[1]["dt_edicao_raw"], reverse=True)
        
        for pasta, dados_historico in lista_dados:
            item = QListWidgetItem(self.lista_croquis)
            item.setSizeHint(QSize(0, 68))
            item.setData(Qt.ItemDataRole.UserRole, str(pasta))
            
            widget = WidgetItemHistorico(dados_historico, str(pasta))
            widget.excluir_clicado.connect(self.ao_clicar_excluir)
            
            self.lista_croquis.addItem(item)
            self.lista_croquis.setItemWidget(item, widget)
        
        self.atualizar_estado_vazio()

    def ao_clicar_excluir(self, caminho_str):
        caminho = Path(caminho_str)
        # Tenta pegar um nome legível para a confirmação
        partes = caminho.name.split("_", 1)
        nome_pasta = partes[1] if len(partes) > 1 and partes[0].isdigit() else caminho.name
        nome_exibicao = nome_pasta.replace("_", " ").title()
        
        resposta = QMessageBox.question(
            self, "Excluir Croqui", 
            f"Tem certeza que deseja excluir '{nome_exibicao}' permanentemente?\n\nEsta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if resposta == QMessageBox.StandardButton.Yes:
            try:
                self.gerenciador.excluir_croqui(caminho)
                self.carregar_croquis()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao excluir croqui: {e}")

    def ao_clicar_novo(self):
        dialogo = DialogoNovoCroqui(self.storage, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            metadados = dialogo.obter_dados()
            
            log_dialog = DialogoProgressoLog(f"Criando Croqui: {metadados['id']}", self)
            log_dialog.show()
            
            old_stdout = sys.stdout
            sys.stdout = StreamToCallback(log_dialog.adicionar_log)
            try:
                # O Gerenciador agora recebe parâmetros individuais
                caminho = self.gerenciador.criar_novo_croqui(
                    metadados['id'], metadados['pico'], metadados['estado'], self.usuario, log_dialog
                )

                self.caminho_croqui_selecionado = caminho
                self.carregar_croquis()
                log_dialog.adicionar_log("\n[SUCESSO] Croqui criado e compilado!")
                log_dialog.accept()
                self.accept()
            except Exception as e:

                log_dialog.adicionar_log(f"\n[ERRO] {e}")
                QMessageBox.critical(self, "Erro", f"Falha ao criar croqui: {e}")
            finally:
                sys.stdout = old_stdout
                log_dialog.btn_fechar.setEnabled(True)


    def ao_clicar_importar(self):
        arquivo, _ = QFileDialog.getOpenFileName(
            self, "Importar Croqui", "", "Arquivos Aresta (*.croqui *.zip)"
        )
        if arquivo:
            log_dialog = DialogoProgressoLog("Importando Croqui Experimental...", self)
            log_dialog.show()
            
            old_stdout = sys.stdout
            sys.stdout = StreamToCallback(log_dialog.adicionar_log)
            try:
                caminho = self.gerenciador.importar_croqui(Path(arquivo))
                self.caminho_croqui_selecionado = caminho
                log_dialog.adicionar_log("\n[SUCESSO] Croqui importado e compilado com sucesso!")
                log_dialog.accept()
                self.accept()
            except Exception as e:
                log_dialog.adicionar_log(f"\n[ERRO] Falha ao importar: {e}")
                QMessageBox.critical(self, "Erro", f"Falha ao importar croqui: {e}")
            finally:
                sys.stdout = old_stdout
                log_dialog.btn_fechar.setEnabled(True)

    def ao_clicar_oficial(self):
        dialogo = DialogoBuscaCroqui(self.storage, self)
        if dialogo.exec():
            id_oficial = dialogo.obter_id_selecionado()
            if id_oficial:
                resumo, ok = QInputDialog.getText(
                    self, "Resumo da Edição", 
                    f"O que você pretende editar em '{id_oficial}'? (Opcional):"
                )
                if not ok:
                    return

                log_dialog = DialogoProgressoLog(f"Importando Oficial: {id_oficial}", self)
                log_dialog.show()
                
                old_stdout = sys.stdout
                sys.stdout = StreamToCallback(log_dialog.adicionar_log)
                try:
                    caminho = self.gerenciador.criar_croqui_a_partir_de_oficial(id_oficial, self.usuario, resumo)
                    self.caminho_croqui_selecionado = caminho
                    log_dialog.adicionar_log("\n[SUCESSO] Croqui oficial importado e compilado com sucesso!")
                    log_dialog.accept()
                    self.accept()
                except Exception as e:
                    log_dialog.adicionar_log(f"\n[ERRO] {e}")
                    QMessageBox.critical(self, "Erro", f"Falha ao criar croqui a partir de oficial: {e}")
                finally:
                    sys.stdout = old_stdout
                    log_dialog.btn_fechar.setEnabled(True)

    def ao_clicar_item(self, item):
        caminho_str = item.data(Qt.ItemDataRole.UserRole)
        if caminho_str:
            caminho = Path(caminho_str)
            try:
                self.gerenciador.abrir_croqui(caminho, self.usuario)
                self.caminho_croqui_selecionado = caminho
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao abrir croqui: {e}")

    def atualizar_estado_vazio(self):
        tem_itens = self.lista_croquis.count() > 0
        self.lista_croquis.setVisible(tem_itens)
        self.label_historico_vazio.setVisible(not tem_itens)
