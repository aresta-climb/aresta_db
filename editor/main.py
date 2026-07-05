import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path para permitir imports do pacote 'editor'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from pathlib import Path

from editor.core.storage import GerenciadorCaminhos
from editor.core.worker import TarefaInicializacao
from editor.legacy_views.tela_de_carregamento import TelaDeCarregamento
from editor.views.tela_de_abertura import TelaDeAbertura
from editor.legacy_views.area_principal import JanelaPrincipal
from editor.views.estilo import Icones

# Fix para o ícone na barra de tarefas do Windows
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("aresta.editor.v1")
except Exception:
    pass

# Placeholder para o Client ID do GitHub (deve ser substituído por um real em produção)
ID_CLIENTE_GITHUB = "Iv23li5kcnSYgMgEfvAC"

class ControladorAplicativo:
    """
    Controla o ciclo de vida da aplicação (Abertura -> Diálogo de Seleção -> Janela Principal).
    Permite a navegação de retorno da Janela Principal para a Seleção.
    """
    def __init__(self):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            
        storage = GerenciadorCaminhos()
        caminho_logo_app = storage.obter_caminho_recurso_interno("recursos/logo_app.png")
        self.app.setWindowIcon(QIcon(str(caminho_logo_app)))
        self.abertura = TelaDeAbertura()
        self.janela_principal = None
        self.tela_carregamento = None
        
        # Inicia a tarefa de inicialização
        self.tarefa = TarefaInicializacao(ID_CLIENTE_GITHUB)
        self.tarefa.status.connect(self.abertura.atualizar_status)
        self.tarefa.progresso.connect(self.abertura.atualizar_progresso)
        self.tarefa.mostrar_progresso.connect(self.abertura.exibir_barra_progresso)
        self.tarefa.auth_requerida.connect(self.abertura.exibir_codigo_auth)
        self.tarefa.auth_concluida.connect(self.abertura.esconder_auth)
        self.tarefa.sucesso.connect(self.executar_selecao)
        self.tarefa.erro.connect(self.mostrar_erro)
        
        self.abertura.show()
        self.tarefa.start()

    def executar_selecao(self):
        """
        Exibe a Tela de Carregamento como um diálogo modal.
        """
        # Garante que a tela de abertura esteja fechada
        if self.abertura:
            self.abertura.close()
        
        self.tela_carregamento = TelaDeCarregamento(
            self.tarefa.storage, 
            usuario=self.tarefa.auth.usuario_logado
        )
        
        if self.tela_carregamento.exec() == QDialog.DialogCode.Accepted:
            self.mostrar_janela_principal()
        else:
            # Se cancelar na tela de seleção e não houver janela principal aberta, sai do app
            if not self.janela_principal:
                QApplication.quit()

    def mostrar_janela_principal(self):
        """
        Cria e exibe a Janela Principal do Editor.
        """
        if self.janela_principal:
            self.janela_principal.close()
            
        from editor.core.workspace import ExperimentalWorkspace
        workspace = ExperimentalWorkspace(self.tela_carregamento.caminho_croqui_selecionado)
        
        self.janela_principal = JanelaPrincipal(
            storage=self.tarefa.storage,
            auth=self.tarefa.auth,
            workspace=workspace
        )
        # Conecta o sinal para permitir voltar para a seleção
        self.janela_principal.solicitar_abrir_novo.connect(self.executar_selecao)
        self.janela_principal.show()

    def mostrar_erro(self, mensagem):
        if self.abertura:
            self.abertura.hide()
        QMessageBox.critical(None, "Erro de Inicialização", mensagem)
        if self.abertura:
            self.abertura.close()
        QApplication.quit()

    def executar(self):
        return self.app.exec()

def main():
    # Verificação de modo LocalRepo: sys.argv[1] começa apontando para algo com 'database'
    # E é de fato um diretório que contém croqui.yaml
    if len(sys.argv) > 1 and "database" in sys.argv[1]:
        caminho_str = sys.argv[1]
        caminho_path = Path(caminho_str).resolve()
        
        if caminho_path.is_dir() and (caminho_path / "croqui.yaml").exists():
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
                
            storage = GerenciadorCaminhos()
            caminho_logo_app = storage.obter_caminho_recurso_interno("recursos/logo_app.png")
            if not caminho_logo_app.exists() and hasattr(storage, 'obter_caminho_recurso'):
                # fallback em caso de testes/diferenças
                pass
            
            # QIcon precisa receber string
            try:
                app.setWindowIcon(QIcon(str(caminho_logo_app)))
            except Exception:
                pass
            
            from editor.core.workspace import LocalRepoWorkspace
            workspace = LocalRepoWorkspace(caminho_path)
            
            janela = JanelaPrincipal(storage=storage, auth=None, workspace=workspace)
            janela.show()
            sys.exit(app.exec())
            
    # Inicialização Padrão (Experimental Workspace com Autenticação e Sync)
    controlador = ControladorAplicativo()
    sys.exit(controlador.executar())

if __name__ == "__main__":
    main()
