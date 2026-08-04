from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QDesktopServices
from editor.views.publish_dialog import PublishDialog
from editor.core.worker import TarefaPublicacao
from editor.views.estilo import Icones
import github

class DialogoSucessoPR(QDialog):
    """Diálogo de sucesso com botão customizado para abrir no GitHub."""
    def __init__(self, pr_url, parent=None, titulo="Sucesso", mensagem_personalizada="Pull Request publicada com sucesso!"):
        super().__init__(parent)
        self.pr_url = pr_url
        self.setWindowTitle(titulo)
        self.setMinimumSize(400, 160)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.label_mensagem = QLabel(mensagem_personalizada)
        self.label_mensagem.setWordWrap(True)
        self.label_mensagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_mensagem.setStyleSheet("font-size: 14px; font-weight: bold; color: #28a745;")
        layout.addWidget(self.label_mensagem)
        
        self.btn_abrir_github = QPushButton(" Abrir no GitHub")
        self.btn_abrir_github.setIcon(Icones.obter("github", cor="#ffffff", cor_ativa="#ffffff"))
        self.btn_abrir_github.setIconSize(QSize(20, 20))
        self.btn_abrir_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_github.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #5a6268; }
        """)
        self.btn_abrir_github.clicked.connect(self.abrir_link)
        layout.addWidget(self.btn_abrir_github, alignment=Qt.AlignmentFlag.AlignCenter)

    def abrir_link(self):
        QDesktopServices.openUrl(QUrl(self.pr_url))
        self.accept()

class PublishController:
    """
    Controlador responsável pelo fluxo de publicação (Pull Request) no GitHub.
    Gerencia as validações, interface de diálogo e acionamento dos workers de background.
    """
    def __init__(self, workspace, auth, historico, storage, parent):
        self.workspace = workspace
        self.auth = auth
        self.historico = historico
        self.storage = storage
        self.parent = parent
        self.croqui_data = getattr(parent, "croqui_data", None)
        self._worker_pr = None

    def _ler_meta_experimental(self):
        if not hasattr(self.workspace, "caminho_raiz"):
            return {}
        yaml_meta = self.workspace.caminho_raiz / "croqui_experimental.yaml"
        if yaml_meta.is_file():
            import yaml
            with open(yaml_meta, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _salvar_meta_experimental(self, meta):
        if not hasattr(self.workspace, "caminho_raiz"):
            return
        yaml_meta = self.workspace.caminho_raiz / "croqui_experimental.yaml"
        import yaml
        with open(yaml_meta, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)

    def iniciar_publicacao(self):
        """
        Inicia o fluxo de publicação. 
        Valida a autenticação e modificações não salvas antes de prosseguir.
        """
        if not self.workspace or not self.auth:
            return
            
        if not self.historico.obter_pilha().isClean():
            resposta = QMessageBox.question(
                self.parent, "Salvar Necessário",
                "Você precisa salvar suas alterações antes de publicar. Deseja salvar agora?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel
            )
            if resposta == QMessageBox.StandardButton.Save:
                self.parent.salvar_croqui(callback_sucesso=self._prosseguir_publicacao)
                return
            else:
                return
                
        self._prosseguir_publicacao()

    def _prosseguir_publicacao(self):
        """
        Continua o fluxo após validação de salvamento. 
        Verifica a existência de PR e exibe diálogo se necessário.
        """
        meta = self._ler_meta_experimental()
        pr_branch = meta.get("pull_request_branch")
        pr_url = meta.get("pull_request_url")
        
        pr_aberto = False
        if pr_branch:
            pr_aberto = True
            if pr_url:
                try:
                    import github
                    partes = pr_url.split("/")
                    if "pull" in partes:
                        pr_number = int(partes[-1])
                        token = self.auth.recuperar_token()
                        if token:
                            g = github.Github(auth=github.Auth.Token(token))
                            idx_pull = partes.index("pull")
                            repo_name = f"{partes[idx_pull-2]}/{partes[idx_pull-1]}"
                            repo = g.get_repo(repo_name)
                            pr = repo.get_pull(pr_number)
                            if pr.state != "open":
                                pr_aberto = False
                except Exception as e:
                    print(f"[AVISO] Erro ao verificar status do PR: {e}")
        
        if pr_aberto:
            # Fluxo Silencioso de Atualização
            self._iniciar_worker(dados_pr=None, modo_atualizacao=True)
        else:
            if pr_branch:
                # O PR foi fechado/merged. Limpar os dados antigos do meta
                meta.pop("pull_request_branch", None)
                meta.pop("pull_request_url", None)
                meta.pop("pull_request_fork_owner", None)
                self._salvar_meta_experimental(meta)
                
            # Fluxo Novo PR
            titulo_sugerido = self.croqui_data.get("nome", self.workspace.caminho_raiz.name) if self.croqui_data else self.workspace.caminho_raiz.name
            dialogo = PublishDialog(titulo_padrao=titulo_sugerido, parent=self.parent)
            if dialogo.exec() == 1: # QDialog.DialogCode.Accepted
                dados_pr = dialogo.obter_dados()
                self._iniciar_worker(dados_pr=dados_pr, modo_atualizacao=False)

    def _iniciar_worker(self, dados_pr, modo_atualizacao):
        """
        Configura e inicia a tarefa de background para publicação.
        """
        texto = "Atualizando Pull Request..." if modo_atualizacao else "Iniciando publicação..."
        
        # A janela de progresso fica amarrada ao parent para exibição modal
        self.progresso_pr = QProgressDialog(texto, "Cancelar", 0, 100, self.parent)
        self.progresso_pr.setWindowTitle("Publicando no GitHub")
        self.progresso_pr.setWindowModality(Qt.WindowModality.WindowModal)
        self.progresso_pr.setAutoClose(True)
        self.progresso_pr.show()

        id_croqui = self.croqui_data.get("id") if self.croqui_data else self.workspace.caminho_raiz.name
        
        meta = self._ler_meta_experimental()

        self._worker_pr = TarefaPublicacao(
            token=self.auth.recuperar_token(),
            storage=self.storage,
            caminho_database_croqui=self.workspace.obter_caminho_database(),
            id_croqui=id_croqui,
            dados_pr=dados_pr,
            modo_atualizacao=modo_atualizacao,
            pr_branch=meta.get("pull_request_branch")
        )
        
        self._worker_pr.status.connect(self.progresso_pr.setLabelText)
        self._worker_pr.progresso.connect(self.progresso_pr.setValue)
        self._worker_pr.sucesso.connect(self._on_sucesso)
        self._worker_pr.aviso.connect(self._on_aviso)
        self._worker_pr.erro.connect(self._on_erro)
        
        self._worker_pr.start()

    def _on_aviso(self, mensagem):
        """Callback acionado quando não há alterações para enviar."""
        self.progresso_pr.close()
        
        meta = self._ler_meta_experimental()
        pr_url = meta.get("pull_request_url")
        
        if pr_url:
            dialogo = DialogoSucessoPR(pr_url, self.parent, titulo="Tudo Atualizado", mensagem_personalizada=mensagem)
            dialogo.exec()
        else:
            QMessageBox.information(self.parent, "Tudo Atualizado", mensagem)

    def _on_sucesso(self, pr_url, pr_branch, pr_owner):
        """Callback acionado pelo sucesso do worker."""
        if pr_url and pr_url != "atualizado":
            meta = self._ler_meta_experimental()
            meta["pull_request_url"] = pr_url
            meta["pull_request_branch"] = pr_branch
            meta["pull_request_fork_owner"] = pr_owner
            self._salvar_meta_experimental(meta)
            mensagem = "Pull Request publicada com sucesso!"
        else:
            meta = self._ler_meta_experimental()
            pr_url = meta.get("pull_request_url", "")
            mensagem = "Pull Request atualizado com sucesso!"

        dialogo = DialogoSucessoPR(pr_url, self.parent, titulo="Sucesso", mensagem_personalizada=mensagem)
        dialogo.exec()
        
    def _on_erro(self, erro):
        """Callback acionado por falha no worker."""
        QMessageBox.critical(self.parent, "Erro na Publicação", f"Falha ao criar Pull Request:\n{erro}")
