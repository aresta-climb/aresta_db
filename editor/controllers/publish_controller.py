# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtWidgets import QMessageBox, QProgressDialog, QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices
from editor.views.publish_dialog import PublishDialog
from editor.core.worker import TarefaPublicacao
from editor.core.servico_loja import ServicoLoja
from editor.core.servico_submissao import ServicoSubmissao
from editor.views.estilo import Icones
import requests

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
        
        self.btn_abrir_link = QPushButton(" Visualizar Proposta na Web")
        self.btn_abrir_link.setIcon(Icones.obter("externo", cor="#ffffff", cor_ativa="#ffffff"))
        self.btn_abrir_link.setIconSize(QSize(20, 20))
        self.btn_abrir_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abrir_link.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #218838; }
        """)
        self.btn_abrir_link.clicked.connect(self.abrir_link)
        self.btn_abrir_github = self.btn_abrir_link
        layout.addWidget(self.btn_abrir_link, alignment=Qt.AlignmentFlag.AlignCenter)

    def abrir_link(self):
        QDesktopServices.openUrl(QUrl(self.pr_url))
        self.accept()

class PublishController:
    """
    Controlador responsável pelo fluxo de publicação de sugestões (Pull Request).
    Gerencia as validações pré-envio, interface de diálogo e acionamento da TarefaPublicacao.
    """
    def __init__(self, workspace, auth=None, historico=None, storage=None, parent=None, servico_loja=None, servico_submissao=None):
        self.workspace = workspace
        if auth is None:
            from editor.core.gerenciador_sessao import GerenciadorSessao
            auth = GerenciadorSessao()
        self.auth = auth
        self.historico = historico
        self.storage = storage
        self.parent = parent
        self.servico_loja = servico_loja or ServicoLoja()
        self.servico_submissao = servico_submissao
        self.croqui_data = getattr(parent, "croqui_data", None)
        self._worker_pr = None

    def _ler_meta_experimental(self):
        if not hasattr(self.workspace, "caminho_raiz") or not self.workspace.caminho_raiz:
            return {}
        yaml_meta = self.workspace.caminho_raiz / "croqui_experimental.yaml"
        if yaml_meta.is_file():
            import yaml
            with open(yaml_meta, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _salvar_meta_experimental(self, meta):
        if not hasattr(self.workspace, "caminho_raiz") or not self.workspace.caminho_raiz:
            return
        yaml_meta = self.workspace.caminho_raiz / "croqui_experimental.yaml"
        import yaml
        with open(yaml_meta, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)

    def _obter_resumo_arquivos(self) -> list[str]:
        """Retorna a lista de arquivos modificados na pasta database do croqui."""
        if not hasattr(self.workspace, "obter_caminho_database"):
            return []
        caminho_db = self.workspace.obter_caminho_database()
        if not caminho_db or not caminho_db.is_dir():
            return []

        id_croqui = self.croqui_data.get("id") if self.croqui_data else (self.workspace.caminho_raiz.name if getattr(self.workspace, "caminho_raiz", None) else "")
        if not id_croqui:
            return []

        servico = self.servico_submissao
        if not servico and hasattr(self.storage, "obter_caminho_base_repo"):
            from editor.core.servico_submissao import ServicoSubmissao
            caminho_repo = self.storage.obter_caminho_base_repo()
            servico = ServicoSubmissao(caminho_repo_base=caminho_repo)

        if servico and hasattr(servico, "obter_arquivos_modificados"):
            return servico.obter_arquivos_modificados(caminho_db, id_croqui)

        return []

    def _validar_compilacao_limpa(self) -> bool:
        """Verifica se o croqui compila sem erros."""
        try:
            if hasattr(self.workspace, "processar_renomeacao_e_compilacao"):
                id_atual = self.croqui_data.get("id", "") if self.croqui_data else ""
                _, mensagens = self.workspace.processar_renomeacao_e_compilacao(id_atual, id_atual, self.storage)
                erros = [m for m in mensagens if "erro" in m.lower() or "error" in m.lower()]
                if erros:
                    QMessageBox.critical(
                        self.parent,
                        "Erro de Compilação",
                        "O croqui possui erros de compilação e não pode ser enviado:\n\n" + "\n".join(erros)
                    )
                    return False
            return True
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Erro de Compilação",
                f"Falha ao validar compilação do croqui:\n{e}"
            )
            return False

    def iniciar_publicacao(self):
        """
        Inicia o fluxo de publicação. 
        Valida a versão da Store, autenticação, compilação e modificações não salvas antes de prosseguir.
        """
        if not self.workspace or not self.auth:
            return

        # Guarda de Publicação: Valida se há atualização na Microsoft Store
        resultado_update = self.servico_loja.verificar_atualizacoes_disponiveis()
        if resultado_update.tem_atualizacao:
            versao_txt = f" (versão {resultado_update.versao_disponivel})" if resultado_update.versao_disponivel else ""
            resposta = QMessageBox.warning(
                self.parent,
                "Atualização Necessária",
                f"Existe uma nova versão do Aresta Editor{versao_txt} disponível na Microsoft Store.\n\n"
                "Para manter a integridade do banco de dados, é necessário atualizar o aplicativo antes de publicar alterações.\n\n"
                "Deseja atualizar agora?",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            if resposta == QMessageBox.StandardButton.Ok:
                self.servico_loja.solicitar_instalacao_atualizacao(resultado_update)
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

        if not self._validar_compilacao_limpa():
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
                    partes = pr_url.split("/")
                    if "pull" in partes:
                        pr_number = int(partes[-1])
                        resp = requests.get(
                            f"https://api.github.com/repos/aresta-climb/aresta_db/pulls/{pr_number}",
                            headers={"User-Agent": "Aresta-Editor"},
                            timeout=5,
                        )
                        if resp.status_code == 200:
                            dados = resp.json()
                            if dados.get("state") != "open":
                                pr_aberto = False
                        elif resp.status_code == 404:
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
            titulo_sugerido = ""
            if self.croqui_data:
                titulo_sugerido = self.croqui_data.get("nome") or self.croqui_data.get("id", "")
            if not titulo_sugerido and getattr(self.workspace, "caminho_raiz", None):
                titulo_sugerido = self.workspace.caminho_raiz.name
            resumo_arquivos = self._obter_resumo_arquivos()
            dialogo = PublishDialog(titulo_padrao=titulo_sugerido, resumo_arquivos=resumo_arquivos, parent=self.parent)
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
        self.progresso_pr.setWindowTitle("Enviando Sugestão")
        self.progresso_pr.setWindowModality(Qt.WindowModality.WindowModal)
        self.progresso_pr.setAutoClose(True)
        self.progresso_pr.show()

        id_croqui = self.croqui_data.get("id") if self.croqui_data else (self.workspace.caminho_raiz.name if getattr(self.workspace, "caminho_raiz", None) else "")
        meta = self._ler_meta_experimental()

        token = None
        sessao = None
        if hasattr(self.auth, "obter_sessao"):
            sessao = self.auth.obter_sessao()
            token = sessao.jwt_supabase if sessao else None
        elif hasattr(self.auth, "recuperar_token"):
            token = self.auth.recuperar_token()

        self._worker_pr = TarefaPublicacao(
            token=token,
            sessao=sessao,
            storage=self.storage,
            caminho_database_croqui=self.workspace.obter_caminho_database() if hasattr(self.workspace, "obter_caminho_database") else None,
            id_croqui=id_croqui,
            dados_pr=dados_pr,
            modo_atualizacao=modo_atualizacao,
            pr_branch=meta.get("pull_request_branch"),
            servico_submissao=self.servico_submissao,
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
        meta = self._ler_meta_experimental()
        if pr_url and pr_url != "atualizado":
            meta["pull_request_url"] = pr_url
        if pr_branch:
            meta["pull_request_branch"] = pr_branch
        if pr_owner:
            meta["pull_request_fork_owner"] = pr_owner
        self._salvar_meta_experimental(meta)

        url_final = meta.get("pull_request_url", pr_url if pr_url != "atualizado" else "")
        mensagem = (
            "Proposta de mudança publicada com sucesso!"
            if pr_url and pr_url != "atualizado"
            else "Proposta de mudança atualizada com sucesso!"
        )

        dialogo = DialogoSucessoPR(url_final, self.parent, titulo="Sucesso", mensagem_personalizada=mensagem)
        dialogo.exec()
        
    def _on_erro(self, erro):
        """Callback acionado por falha no worker."""
        self.progresso_pr.close()
        if "sessão expirada" in erro.lower() or "sessao expirada" in erro.lower():
            QMessageBox.warning(
                self.parent,
                "Sessão Expirada",
                "Sua sessão de login expirou.\n\nPor favor, salve suas alterações locais e faça login novamente no aplicativo para enviar sua proposta de mudança."
            )
        else:
            QMessageBox.critical(self.parent, "Erro na Publicação", f"Falha ao enviar proposta de mudança:\n{erro}")

