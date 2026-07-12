from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt
from editor.views.publish_dialog import PublishDialog
from editor.core.worker import TarefaPublicacao

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
        self.croqui_data = None
        
        # Referência interna para manter a tarefa viva
        self._worker_pr = None

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
                # O parent.salvar_croqui() deve ser ajustado para chamar o _prosseguir_publicacao após sucesso.
                # No design atual, se a gente usa um diálogo de espera, o controller pode pedir ao parent
                # para salvar de forma bloqueante, ou o parent sinaliza quando terminar.
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
        # Checa se a PR já existe
        pr_branch = self.croqui_data.get("pull_request_branch") if self.croqui_data else None
        
        if pr_branch:
            # Fluxo Silencioso de Atualização
            # Aqui poderíamos checar na API se a PR está aberta. 
            # Assumiremos "modo_atualizacao=True" para enviar ao worker
            self._iniciar_worker(dados_pr=None, modo_atualizacao=True)
        else:
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

        self._worker_pr = TarefaPublicacao(
            token=self.auth.recuperar_token(),
            storage=self.storage,
            caminho_database_croqui=self.workspace.obter_caminho_database(),
            id_croqui=id_croqui,
            dados_pr=dados_pr,
            modo_atualizacao=modo_atualizacao,
            pr_branch=self.croqui_data.get("pull_request_branch") if self.croqui_data else None
        )
        
        self._worker_pr.status.connect(self.progresso_pr.setLabelText)
        self._worker_pr.progresso.connect(self.progresso_pr.setValue)
        self._worker_pr.sucesso.connect(self._on_sucesso)
        self._worker_pr.erro.connect(self._on_erro)
        
        self._worker_pr.start()

    def _on_sucesso(self, pr_url, pr_branch, pr_owner):
        """Callback acionado pelo sucesso do worker."""
        if self.croqui_data:
            self.croqui_data["pull_request_url"] = pr_url
            self.croqui_data["pull_request_branch"] = pr_branch
            self.croqui_data["pull_request_fork_owner"] = pr_owner
            # Precisamos salvar o YAML aqui
            self.workspace.salvar_yaml_direto(self.croqui_data)

        QMessageBox.information(self.parent, "Sucesso", f"Pull Request publicada com sucesso!\n\nLink: {pr_url}")
        
    def _on_erro(self, erro):
        """Callback acionado por falha no worker."""
        QMessageBox.critical(self.parent, "Erro na Publicação", f"Falha ao criar Pull Request:\n{erro}")
