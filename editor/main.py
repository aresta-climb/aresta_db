import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path para permitir imports do pacote 'editor'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from PyQt6.QtCore import Qt

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
            
        self.app.setWindowIcon(Icones.obter("logo", cor="#556b2f"))
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
            
        self.janela_principal = JanelaPrincipal(
            storage=self.tarefa.storage,
            auth=self.tarefa.auth,
            caminho_croqui=self.tela_carregamento.caminho_croqui_selecionado
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

if __name__ == "__main__":
    controlador = ControladorAplicativo()
    sys.exit(controlador.executar())
