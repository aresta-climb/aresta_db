# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QApplication,
    QMessageBox,
    QFrame,
    QDialog,
)
from PyQt6.QtCore import (
    Qt,
    QUrl,
    QSize,
    QTimer,
    pyqtSignal,
    QThread,
    QRegularExpression,
)
from PyQt6.QtGui import (
    QDesktopServices,
    QPixmap,
    QIcon,
    QRegularExpressionValidator,
)

from editor.core.storage import GerenciadorCaminhos
from editor.core.cliente_auth_supabase import (
    ClienteAuthSupabase,
    ErroAutenticacaoSupabase,
)
from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.servidor_oauth_callback import ServidorCallbackOAuth
from editor.views.dialogos.dialogo_perfil_autor import DialogoPerfilAutor
from editor.views.estilo import Icones


class TarefaAssincrona(QThread):
    """Thread auxiliar para executar chamadas de rede sem travar a interface gráfica."""

    sucesso = pyqtSignal(object)
    erro = pyqtSignal(Exception)

    def __init__(self, funcao, *args, **kwargs):
        super().__init__()
        self.funcao = funcao
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            resultado = self.funcao(*self.args, **self.kwargs)
            self.sucesso.emit(resultado)
        except Exception as e:
            self.erro.emit(e)


class TelaDeAbertura(QWidget):
    """
    Janela de abertura com barra de progresso, status e autenticação unificada.
    """

    login_concluido = pyqtSignal(object)
    login_cancelado = pyqtSignal()

    def __init__(self, cliente_auth: Optional[ClienteAuthSupabase] = None):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.cliente_auth = cliente_auth or ClienteAuthSupabase()
        self.servidor_oauth: Optional[ServidorCallbackOAuth] = None
        self._email_atual: str = ""
        self._segundos_reenvio: int = 60
        self._timer_reenvio = QTimer(self)
        self._timer_reenvio.timeout.connect(self._atualizar_contador_reenvio)

        caminho_logo_janela = GerenciadorCaminhos().obter_caminho_recurso_interno(
            "recursos/logo_app.png"
        )
        self.setWindowIcon(QIcon(str(caminho_logo_janela)))
        self.setFixedSize(450, 650)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Container principal com bordas arredondadas e fundo branco
        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: #ffffff;
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(30, 25, 30, 25)
        layout.addWidget(self.container)

        # Botão de fechar no canto superior direito
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #adb5bd;
                font-size: 24px;
                border: none;
                margin-top: -10px;
                margin-right: -10px;
            }
            QPushButton:hover { color: #dc3545; }
        """)
        self.btn_close.clicked.connect(self._ao_clicar_fechar)
        container_layout.addWidget(
            self.btn_close, alignment=Qt.AlignmentFlag.AlignRight
        )

        # Header com Logo Oficial Aresta
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)

        self.label_logo = QLabel()
        self.label_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caminho_logo = GerenciadorCaminhos().obter_caminho_recurso_interno(
            "recursos/logo_splash.png"
        )
        pixmap = QPixmap(str(caminho_logo))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                240,
                160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.label_logo.setPixmap(pixmap)
        header_layout.addWidget(self.label_logo)

        container_layout.addLayout(header_layout)
        container_layout.addSpacing(5)

        # Status
        self.label_status = QLabel("Iniciando...")
        self.label_status.setStyleSheet(
            "color: #495057; font-size: 14px; margin-bottom: 10px;"
        )
        self.label_status.setWordWrap(True)
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.label_status)

        # Barra de progresso (Oculta por padrão)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 5px;
                text-align: center;
                background-color: #f8f9fa;
                height: 15px;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 4px;
            }
        """)
        self.progress_bar.hide()
        container_layout.addWidget(self.progress_bar)

        # ==========================================
        # Container de Autenticação Unificada (Embebido)
        # ==========================================
        self.auth_container = QWidget()
        self.auth_layout = QVBoxLayout(self.auth_container)
        self.auth_layout.setContentsMargins(0, 0, 0, 0)
        self.auth_layout.setSpacing(12)

        # 1. Estado Seleção de Método
        self.container_auth_selecao = QWidget()
        layout_selecao = QVBoxLayout(self.container_auth_selecao)
        layout_selecao.setContentsMargins(0, 0, 0, 0)
        layout_selecao.setSpacing(12)

        lbl_desc_selecao = QLabel(
            "Conecte sua conta para catalogar, editar e colaborar com croquis da comunidade:"
        )
        lbl_desc_selecao.setWordWrap(True)
        lbl_desc_selecao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc_selecao.setStyleSheet(
            "color: #6c757d; font-size: 13px; margin-bottom: 5px;"
        )
        layout_selecao.addWidget(lbl_desc_selecao)

        self.btn_escolher_email = QPushButton("  Entrar com E-mail")
        self.btn_escolher_email.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_escolher_email.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #218838; }
        """)
        self.btn_escolher_email.clicked.connect(self.mostrar_formulario_email)
        layout_selecao.addWidget(self.btn_escolher_email)

        # Divisor "ou"
        divisor_layout = QHBoxLayout()
        linha1 = QFrame()
        linha1.setFrameShape(QFrame.Shape.HLine)
        linha1.setStyleSheet("color: #dee2e6;")
        linha2 = QFrame()
        linha2.setFrameShape(QFrame.Shape.HLine)
        linha2.setStyleSheet("color: #dee2e6;")
        lbl_ou = QLabel("ou")
        lbl_ou.setStyleSheet("color: #adb5bd; font-size: 12px; font-weight: bold;")
        divisor_layout.addWidget(linha1)
        divisor_layout.addWidget(lbl_ou)
        divisor_layout.addWidget(linha2)
        layout_selecao.addLayout(divisor_layout)

        self.btn_escolher_github = QPushButton("  Entrar com GitHub")
        self.btn_escolher_github.setIcon(
            Icones.obter("github", cor="#ffffff", cor_ativa="#ffffff")
        )
        self.btn_escolher_github.setIconSize(QSize(18, 18))
        self.btn_escolher_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_escolher_github.setStyleSheet("""
            QPushButton {
                background: #24292e;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #1b1f23; }
        """)
        self.btn_escolher_github.clicked.connect(self.iniciar_login_github)
        layout_selecao.addWidget(self.btn_escolher_github)

        self.auth_layout.addWidget(self.container_auth_selecao)

        # 2. Estado Formulário de E-mail
        self.container_auth_email = QWidget()
        layout_email = QVBoxLayout(self.container_auth_email)
        layout_email.setContentsMargins(0, 0, 0, 0)
        layout_email.setSpacing(10)

        lbl_instrucao_email = QLabel("Digite seu e-mail para receber um código de acesso:")
        lbl_instrucao_email.setStyleSheet(
            "font-weight: bold; color: #495057; font-size: 13px;"
        )
        layout_email.addWidget(lbl_instrucao_email)

        self.edit_email = QLineEdit()
        self.edit_email.setPlaceholderText("seu-email@exemplo.com")
        self.edit_email.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #80bdff; }
        """)
        self.edit_email.returnPressed.connect(self.solicitar_otp)
        layout_email.addWidget(self.edit_email)

        self.btn_enviar_otp = QPushButton("Enviar Código de Acesso")
        self.btn_enviar_otp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enviar_otp.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #218838; }
        """)
        self.btn_enviar_otp.clicked.connect(self.solicitar_otp)
        layout_email.addWidget(self.btn_enviar_otp)

        self.btn_voltar_email = QPushButton("← Voltar")
        self.btn_voltar_email.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voltar_email.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #007bff;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover { color: #0056b3; }
        """)
        self.btn_voltar_email.clicked.connect(self.voltar_para_selecao)
        layout_email.addWidget(self.btn_voltar_email)

        self.container_auth_email.hide()
        self.auth_layout.addWidget(self.container_auth_email)

        # 3. Estado Código OTP
        self.container_auth_codigo = QWidget()
        layout_codigo = QVBoxLayout(self.container_auth_codigo)
        layout_codigo.setContentsMargins(0, 0, 0, 0)
        layout_codigo.setSpacing(10)

        self.label_info_codigo = QLabel()
        self.label_info_codigo.setTextFormat(Qt.TextFormat.RichText)
        self.label_info_codigo.setWordWrap(True)
        self.label_info_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_info_codigo.setStyleSheet("color: #495057; font-size: 13px;")
        layout_codigo.addWidget(self.label_info_codigo)

        self.edit_codigo = QLineEdit()
        self.edit_codigo.setMaxLength(8)
        self.edit_codigo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_codigo.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^\d{0,8}$"), self.edit_codigo
            )
        )
        self.edit_codigo.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 22px;
                font-family: 'Consolas', monospace;
                letter-spacing: 4px;
                font-weight: bold;
            }
            QLineEdit:focus { border-color: #80bdff; }
        """)
        self.edit_codigo.returnPressed.connect(self.validar_otp)
        layout_codigo.addWidget(self.edit_codigo)

        self.btn_validar_codigo = QPushButton("Validar e Entrar")
        self.btn_validar_codigo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_validar_codigo.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #218838; }
        """)
        self.btn_validar_codigo.clicked.connect(self.validar_otp)
        layout_codigo.addWidget(self.btn_validar_codigo)

        opcoes_codigo_layout = QHBoxLayout()
        self.btn_trocar_email = QPushButton("← Trocar e-mail")
        self.btn_trocar_email.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trocar_email.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #007bff;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { color: #0056b3; }
        """)
        self.btn_trocar_email.clicked.connect(self.mostrar_formulario_email)

        self.btn_reenviar_codigo = QPushButton("Reenviar código")
        self.btn_reenviar_codigo.setEnabled(False)
        self.btn_reenviar_codigo.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #007bff;
                border: none;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #0056b3;
                text-decoration: underline;
            }
            QPushButton:disabled {
                color: #6c757d;
                text-decoration: none;
            }
        """)
        self.btn_reenviar_codigo.clicked.connect(self.solicitar_otp)

        opcoes_codigo_layout.addWidget(self.btn_trocar_email)
        opcoes_codigo_layout.addStretch()
        opcoes_codigo_layout.addWidget(self.btn_reenviar_codigo)
        layout_codigo.addLayout(opcoes_codigo_layout)

        self.container_auth_codigo.hide()
        self.auth_layout.addWidget(self.container_auth_codigo)

        # 4. Estado GitHub Aguardando
        self.container_auth_github = QWidget()
        layout_github = QVBoxLayout(self.container_auth_github)
        layout_github.setContentsMargins(0, 0, 0, 0)
        layout_github.setSpacing(12)

        self.label_info_github = QLabel(
            "Abrimos o navegador para você autorizar o Aresta no GitHub.\n\nAguardando conclusão da autorização..."
        )
        self.label_info_github.setWordWrap(True)
        self.label_info_github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_info_github.setStyleSheet("color: #495057; font-size: 13px;")
        layout_github.addWidget(self.label_info_github)

        self.btn_cancelar_github = QPushButton("← Cancelar / Voltar")
        self.btn_cancelar_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar_github.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #dc3545;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        self.btn_cancelar_github.clicked.connect(self.cancelar_login_github)
        layout_github.addWidget(self.btn_cancelar_github)

        self.container_auth_github.hide()
        self.auth_layout.addWidget(self.container_auth_github)

        self.auth_container.hide()
        container_layout.addWidget(self.auth_container)

        # Container de Atualização da Store
        self.update_container = QWidget()
        self.update_layout = QVBoxLayout(self.update_container)
        self.update_layout.setContentsMargins(0, 0, 0, 0)

        self.label_update_info = QLabel()
        self.label_update_info.setWordWrap(True)
        self.label_update_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_update_info.setStyleSheet("color: #495057; font-size: 13px; margin-bottom: 10px;")
        self.update_layout.addWidget(self.label_update_info)

        self.btn_atualizar_store = QPushButton("Atualizar Agora")
        self.btn_atualizar_store.setStyleSheet("""
            QPushButton {
                background: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #106ebe; }
        """)
        self.update_layout.addWidget(self.btn_atualizar_store, alignment=Qt.AlignmentFlag.AlignCenter)

        self.update_container.hide()
        container_layout.addWidget(self.update_container)
        self._callback_atualizar = None
        self.btn_atualizar_store.clicked.connect(self._ao_clicar_atualizar)

    def _ao_clicar_fechar(self):
        self.login_cancelado.emit()
        QApplication.quit()

    def _ao_clicar_atualizar(self):
        if callable(self._callback_atualizar):
            self._callback_atualizar()

    def exibir_aviso_atualizacao(self, resultado, callback_atualizar=None):
        self._callback_atualizar = callback_atualizar
        versao = resultado.versao_disponivel if resultado and resultado.versao_disponivel else ""
        texto_versao = f" (versão {versao})" if versao else ""
        self.label_update_info.setText(
            f"Uma nova versão do Aresta Editor{texto_versao} está disponível na Microsoft Store.\n\n"
            "Por favor, atualize o aplicativo para garantir a integridade dos dados."
        )
        self.label_status.hide()
        self.progress_bar.hide()
        self.auth_container.hide()
        self.update_container.show()

    def esconder_aviso_atualizacao(self):
        self.update_container.hide()
        self.label_status.show()

    def atualizar_status(self, texto: str):
        self.label_status.setText(texto)

    def atualizar_progresso(self, valor: int):
        self.progress_bar.setValue(valor)

    def exibir_barra_progresso(self, visivel: bool):
        self.progress_bar.setVisible(visivel)

    # --- Métodos da Máquina de Estados de Autenticação Embebida ---

    def iniciar_fluxo_login(self):
        """Inicia o fluxo exibindo a seleção de métodos dentro do card."""
        self.label_status.hide()
        self.progress_bar.hide()
        self.update_container.hide()
        self.voltar_para_selecao()
        self.auth_container.show()

    def voltar_para_selecao(self):
        self._timer_reenvio.stop()
        if self.servidor_oauth:
            self.servidor_oauth.encerrar()
            self.servidor_oauth = None

        self.container_auth_email.hide()
        self.container_auth_codigo.hide()
        self.container_auth_github.hide()
        self.container_auth_selecao.show()

    def mostrar_formulario_email(self):
        self._timer_reenvio.stop()
        self.container_auth_selecao.hide()
        self.container_auth_codigo.hide()
        self.container_auth_github.hide()
        self.container_auth_email.show()
        self.edit_email.setFocus()

    def solicitar_otp(self):
        email = self.edit_email.text().strip()
        if not email or "@" not in email:
            QMessageBox.warning(self, "E-mail Inválido", "Por favor, digite um e-mail válido.")
            return

        self._email_atual = email
        self.btn_enviar_otp.setEnabled(False)
        self.btn_enviar_otp.setText("Enviando código...")
        self.btn_reenviar_codigo.setEnabled(False)
        self.btn_reenviar_codigo.setText("Reenviando...")

        self._tarefa_otp = TarefaAssincrona(self.cliente_auth.solicitar_codigo_otp, email)
        self._tarefa_otp.sucesso.connect(self._ao_sucesso_solicitar_otp)
        self._tarefa_otp.erro.connect(self._ao_erro_solicitar_otp)
        self._tarefa_otp.start()

    def _ao_sucesso_solicitar_otp(self, _resultado):
        self.btn_enviar_otp.setEnabled(True)
        self.btn_enviar_otp.setText("Enviar Código de Acesso")
        self.label_info_codigo.setText(f"Enviamos um código de acesso para:<br><b>{self._email_atual}</b>")
        self.container_auth_email.hide()
        self.container_auth_codigo.show()
        self.edit_codigo.clear()
        self.edit_codigo.setFocus()
        self._iniciar_temporizador_reenvio()

    def _ao_erro_solicitar_otp(self, excecao: Exception):
        self.btn_enviar_otp.setEnabled(True)
        self.btn_enviar_otp.setText("Enviar Código de Acesso")
        self.btn_reenviar_codigo.setEnabled(True)
        self.btn_reenviar_codigo.setText("Reenviar código")
        QMessageBox.critical(self, "Falha no Envio", f"Não foi possível enviar o código:\n{str(excecao)}")

    def _iniciar_temporizador_reenvio(self):
        self._segundos_reenvio = 60
        self.btn_reenviar_codigo.setEnabled(False)
        self.btn_reenviar_codigo.setText(f"Reenviar em ({self._segundos_reenvio}s)")
        self._timer_reenvio.start(1000)

    def _atualizar_contador_reenvio(self):
        self._segundos_reenvio -= 1
        if self._segundos_reenvio <= 0:
            self._timer_reenvio.stop()
            self.btn_reenviar_codigo.setEnabled(True)
            self.btn_reenviar_codigo.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_reenviar_codigo.setText("Reenviar código")
        else:
            self.btn_reenviar_codigo.setText(f"Reenviar em ({self._segundos_reenvio}s)")

    def validar_otp(self):
        codigo = self.edit_codigo.text().strip()
        if len(codigo) < 6 or len(codigo) > 8:
            QMessageBox.warning(self, "Código Inválido", "O código deve conter entre 6 e 8 dígitos.")
            return

        self.btn_validar_codigo.setEnabled(False)
        self.btn_validar_codigo.setText("Validando código...")

        self._tarefa_validar = TarefaAssincrona(
            self.cliente_auth.verificar_codigo_otp, self._email_atual, codigo
        )
        self._tarefa_validar.sucesso.connect(self._ao_sucesso_validar_otp)
        self._tarefa_validar.erro.connect(self._ao_erro_validar_otp)
        self._tarefa_validar.start()

    def _ao_sucesso_validar_otp(self, dados: dict):
        self.btn_validar_codigo.setEnabled(True)
        self.btn_validar_codigo.setText("Validar e Entrar")

        jwt = dados.get("access_token", "")
        refresh_token = dados.get("refresh_token", "")
        usuario = dados.get("user", {})
        metadados = usuario.get("user_metadata", {})
        nome_completo = metadados.get("nome_completo", "")

        if not nome_completo or len(nome_completo.split()) < 2:
            dialogo_perfil = DialogoPerfilAutor(nome_sugerido=nome_completo, parent=self)
            if dialogo_perfil.exec() == QDialog.DialogCode.Accepted:
                nome_completo = dialogo_perfil.obter_nome_completo()
                try:
                    self.cliente_auth.atualizar_nome_autor(jwt, nome_completo)
                except Exception:
                    pass
            else:
                return

        sessao = SessaoUsuario(
            email=usuario.get("email", self._email_atual),
            nome_completo=nome_completo,
            jwt_supabase=jwt,
            token_atualizacao=refresh_token,
            token_github=None,
        )
        self._finalizar_login(sessao)

    def _ao_erro_validar_otp(self, excecao: Exception):
        self.btn_validar_codigo.setEnabled(True)
        self.btn_validar_codigo.setText("Validar e Entrar")
        QMessageBox.critical(self, "Falha na Validação", f"Código incorreto ou expirado:\n{str(excecao)}")

    def iniciar_login_github(self):
        self.servidor_oauth = ServidorCallbackOAuth(parent=self)
        self.servidor_oauth.tokens_recebidos.connect(self._ao_receber_tokens_github)
        porta = self.servidor_oauth.iniciar_escuta()
        url_callback = self.servidor_oauth.obter_url_redirecionamento()

        self.container_auth_selecao.hide()
        self.container_auth_github.show()

        url_auth = (
            f"{self.cliente_auth.url_supabase}/auth/v1/authorize?"
            f"provider=github&scopes=read:user,user:email,public_repo&redirect_to={url_callback}"
        )
        print(f"🐙 [OAuth GitHub] Servidor de callback escutando em: {url_callback}")
        print(f"🐙 [OAuth GitHub] Abrindo navegador: {url_auth}")
        QDesktopServices.openUrl(QUrl(url_auth))

    def _ao_receber_tokens_github(self, tokens: dict):
        if not tokens:
            return

        if self.servidor_oauth:
            self.servidor_oauth.encerrar()
            self.servidor_oauth = None

        if "erro" in tokens:
            print(f"❌ [OAuth GitHub] Falha na autorização: {tokens['erro']}")
            QMessageBox.warning(
                self,
                "Falha no Login com GitHub",
                f"Não foi possível autenticar com o GitHub:\n{tokens['erro']}",
            )
            self.voltar_para_selecao()
            return

        jwt = tokens.get("access_token", "")
        refresh_token = tokens.get("refresh_token", "")
        token_github = tokens.get("provider_token")

        print("👤 [OAuth GitHub] Processando tokens recebidos...")
        try:
            usuario = self.cliente_auth.obter_usuario_atual(jwt)
            metadados = usuario.get("user_metadata", {})
            email = usuario.get("email", "")
            print(f"👤 [OAuth GitHub] Usuário obtido: {email}")
        except Exception as e:
            print(f"⚠️ [OAuth GitHub] Falha ao obter usuário atual: {e}")
            metadados = {}
            email = ""

        nome_sugerido = (
            metadados.get("nome_completo")
            or metadados.get("full_name")
            or metadados.get("name")
            or ""
        )
        print(f"👤 [OAuth GitHub] Nome sugerido: '{nome_sugerido}'")

        if not nome_sugerido or len(nome_sugerido.split()) < 2:
            print("👤 [OAuth GitHub] Solicitando nome completo via diálogo de perfil...")
            dialogo_perfil = DialogoPerfilAutor(nome_sugerido=nome_sugerido, parent=self)
            if dialogo_perfil.exec() == QDialog.DialogCode.Accepted:
                nome_sugerido = dialogo_perfil.obter_nome_completo()
                print(f"👤 [OAuth GitHub] Nome completo preenchido: '{nome_sugerido}'")
                try:
                    self.cliente_auth.atualizar_nome_autor(jwt, nome_sugerido)
                except Exception as e:
                    print(f"⚠️ [OAuth GitHub] Falha ao atualizar nome no Supabase: {e}")
            else:
                print("⚠️ [OAuth GitHub] Diálogo de perfil cancelado pelo usuário.")
                self.voltar_para_selecao()
                return

        sessao = SessaoUsuario(
            email=email,
            nome_completo=nome_sugerido,
            jwt_supabase=jwt,
            token_atualizacao=refresh_token,
            token_github=token_github,
        )
        print(f"💾 [OAuth GitHub] Finalizando login para {nome_sugerido} ({email})...")
        self._finalizar_login(sessao)

    def cancelar_login_github(self):
        if self.servidor_oauth:
            self.servidor_oauth.encerrar()
            self.servidor_oauth = None
        self.voltar_para_selecao()

    def _finalizar_login(self, sessao: SessaoUsuario):
        self._timer_reenvio.stop()
        self.auth_container.hide()
        self.label_status.show()
        self.label_status.setText(f"Logado como: {sessao.nome_completo}")
        self.login_concluido.emit(sessao)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(
            self, "_drag_pos"
        ):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
