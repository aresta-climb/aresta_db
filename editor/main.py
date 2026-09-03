# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import os

# Define explicitamente a API PySide6 para bibliotecas auxiliares como QtAwesome e QtPy
os.environ.setdefault("QT_API", "pyside6")

# Adiciona o diretório raiz do projeto ao sys.path para permitir imports do pacote 'editor'
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from typing import Optional, Any, NoReturn
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog, QWidget
from PySide6.QtCore import Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import QIcon
from pathlib import Path

from editor.core.storage import GerenciadorCaminhos
from editor.core.worker import TarefaInicializacao
from editor.legacy_views.tela_de_carregamento import TelaDeCarregamento
from editor.views.tela_de_abertura import TelaDeAbertura
from editor.views.estilo import Icones

# Fix para o ícone na barra de tarefas do Windows
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("aresta.editor.v1")
except Exception:
    pass

# Placeholder para o Client ID do GitHub (deve ser substituído por um real em produção)
ID_CLIENTE_GITHUB: str = "Iv23li5kcnSYgMgEfvAC"

class ControladorAplicativo:
    """
    Controla o ciclo de vida da aplicação (Abertura -> Diálogo de Seleção -> Janela Principal).
    Permite a navegação de retorno da Janela Principal para a Seleção.
    """
    def __init__(self) -> None:
        inst = QApplication.instance()
        if isinstance(inst, QApplication):
            self.app: QApplication = inst
        else:
            self.app = QApplication(sys.argv)
        self.app.setApplicationName("EditorAresta")
            
        storage = GerenciadorCaminhos()
        caminho_logo_app = storage.obter_caminho_recurso_interno("recursos/logo_app.png")
        self.app.setWindowIcon(QIcon(str(caminho_logo_app)))
        
        try:
            from editor.core.version import VERSION
            self.app.setApplicationVersion(VERSION)
        except ImportError:
            pass

            
        self.abertura: TelaDeAbertura = TelaDeAbertura()
        self.janela_principal: Optional[Any] = None
        self.tela_carregamento: Optional[TelaDeCarregamento] = None
        self.tarefa: Optional[TarefaInicializacao] = None
        self._logout_em_andamento: bool = False

        self.iniciar_inicializacao()

    def iniciar_inicializacao(self) -> None:
        """Inicia ou reinicia a tarefa de inicialização e sincronização."""
        self.tarefa = TarefaInicializacao(ID_CLIENTE_GITHUB)
        self.tarefa.status.connect(self.abertura.atualizar_status)
        self.tarefa.progresso.connect(self.abertura.atualizar_progresso)
        self.tarefa.mostrar_progresso.connect(self.abertura.exibir_barra_progresso)
        self.tarefa.solicitar_login_ui.connect(self.abertura.iniciar_fluxo_login)
        self.tarefa.atualizacao_disponivel.connect(self.ao_detectar_atualizacao)
        self.tarefa.sucesso.connect(self.executar_selecao)
        self.tarefa.erro.connect(self.mostrar_erro)

        self.abertura.login_concluido.connect(self.ao_login_concluido)
        self.abertura.login_cancelado.connect(self.ao_login_cancelado)

        self.abertura.show()
        self.tarefa.start()

    def ao_login_concluido(self, sessao: Optional[Any]) -> None:
        """Persiste a sessão e desbloqueia a tarefa de inicialização."""
        if sessao and self.tarefa:
            print(f"💾 [Main] Salvando sessão de {sessao.nome_completo}...")
            self.tarefa.gerenciador_sessao.salvar_sessao(sessao)
            print("🚀 [Main] Desbloqueando thread de inicialização...")
            self.tarefa.definir_sessao_concluida(sessao)

    def ao_login_cancelado(self) -> None:
        """Cancela a inicialização se o usuário desistir do login."""
        print("⚠️ [Main] Login cancelado pelo usuário.")
        if self.tarefa:
            self.tarefa.definir_sessao_concluida(None)

    def ao_detectar_atualizacao(self, resultado: Any) -> None:
        """
        Exibe a notificação de atualização na Tela de Abertura e configura a ação de atualização.
        """
        if self.tarefa:
            self.abertura.exibir_aviso_atualizacao(
                resultado,
                callback_atualizar=lambda: self.tarefa.servico_loja.solicitar_instalacao_atualizacao(resultado) if self.tarefa else None
            )

    def executar_selecao(self) -> None:
        """
        Exibe a Tela de Carregamento como um diálogo modal.
        """
        print("✨ [Main] Inicialização de dados concluída. Abrindo TelaDeCarregamento...")
        # Garante que a tela de abertura e a janela principal estejam fechadas
        if self.abertura:
            self.abertura.close()

        if self.janela_principal:
            self.janela_principal.close()
            self.janela_principal = None

        if not self.tarefa:
            return

        usuario = (
            self.tarefa.sessao_usuario.nome_completo
            if self.tarefa.sessao_usuario
            else ""
        )
        self.tela_carregamento = TelaDeCarregamento(
            self.tarefa.storage,
            usuario=usuario,
        )
        self.tela_carregamento.solicitar_logout.connect(self.ao_solicitar_logout)

        resultado = self.tela_carregamento.exec()
        print(f"📋 [Main] TelaDeCarregamento finalizou com resultado: {resultado}")
        if resultado == QDialog.DialogCode.Accepted:
            self.mostrar_janela_principal()
        elif self._logout_em_andamento:
            self._logout_em_andamento = False
        else:
            # Se cancelar na tela de seleção, sai do app
            print("👋 [Main] Aplicação encerrada pelo usuário a partir da TelaDeCarregamento.")
            QApplication.quit()

    def ao_solicitar_logout(self) -> None:
        """Reinicia a inicialização e exibe a Tela de Abertura para novo login."""
        self._logout_em_andamento = True
        self.iniciar_inicializacao()

    def mostrar_janela_principal(self) -> None:
        """
        Cria e exibe a Janela Principal do Editor.
        """
        if self.janela_principal:
            self.janela_principal.close()
            
        from editor.core.workspace import ExperimentalWorkspace
        from editor.legacy_views.area_principal import JanelaPrincipal
        if not self.tela_carregamento or not self.tela_carregamento.caminho_croqui_selecionado or not self.tarefa:
            return
        workspace = ExperimentalWorkspace(self.tela_carregamento.caminho_croqui_selecionado)
        
        self.janela_principal = JanelaPrincipal(
            storage=self.tarefa.storage,
            auth=self.tarefa.gerenciador_sessao,
            workspace=workspace
        )
        # Conecta o sinal para permitir voltar para a seleção
        self.janela_principal.solicitar_abrir_novo.connect(self.executar_selecao)
        self.janela_principal.show()

    def mostrar_erro(self, mensagem: str) -> None:
        if self.abertura:
            self.abertura.hide()
        QMessageBox.critical(None, "Erro de Inicialização", mensagem)
        if self.abertura:
            self.abertura.close()
        QApplication.quit()

    def executar(self) -> int:
        if self.app:
            return int(self.app.exec())
        return 0

def main() -> None:
    # Inicializa telemetria Sentry com sanitização universal de dados
    from editor.core.telemetria import inicializar_telemetria
    inicializar_telemetria()

    # Garante a instância global do QApplication
    inst = QApplication.instance()
    if isinstance(inst, QApplication):
        app = inst
    else:
        app = QApplication(sys.argv)
    app.setApplicationName("EditorAresta")

    storage = GerenciadorCaminhos()
    caminho_logo_app = storage.obter_caminho_recurso_interno("recursos/logo_app.png")
    app.setWindowIcon(QIcon(str(caminho_logo_app)))


    # Previne múltiplas instâncias do editor usando QLocalServer / QLocalSocket
    # com health-check ativo e recuperação de processos zumbis
    from editor.core.instancia_unica import (
        verificar_se_ja_em_execucao,
        iniciar_servidor_instancia_unica,
        NOME_SERVIDOR_PADRAO
    )
    if verificar_se_ja_em_execucao(NOME_SERVIDOR_PADRAO):
        msg = "O Aresta Editor já está em execução. A janela ativa foi trazida para o primeiro plano."
        print(msg, file=sys.stderr)
        QMessageBox.information(None, "Aresta Editor", msg)
        sys.exit(0)

    servidor_local = iniciar_servidor_instancia_unica(NOME_SERVIDOR_PADRAO)
    if servidor_local:
        setattr(app, "servidor_local", servidor_local)

    # Verificação de modo LocalRepo: argumento fornecido na linha de comando
    if len(sys.argv) > 1:
        caminho_str = sys.argv[1]
        caminho_path = Path(caminho_str).resolve()
        
        # Se apontar diretamente para o arquivo croqui.yaml, obtém a pasta pai
        if caminho_path.is_file() and caminho_path.name == "croqui.yaml":
            caminho_path = caminho_path.parent
        
        if caminho_path.is_dir() and (caminho_path / "croqui.yaml").exists():
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
                
            try:
                from editor.core.version import VERSION
                app.setApplicationVersion(VERSION)
            except ImportError:
                pass
            
            from editor.core.workspace import LocalRepoWorkspace
            from editor.legacy_views.area_principal import JanelaPrincipal
            workspace = LocalRepoWorkspace(caminho_path)
            
            janela = JanelaPrincipal(storage=storage, auth=None, workspace=workspace)
            janela.show()
            sys.exit(app.exec())
        elif "database" in caminho_str or caminho_str.endswith("croqui.yaml"):
            msg_erro = f"Erro: O caminho especificado '{caminho_str}' não contém um croqui.yaml válido."
            print(msg_erro, file=sys.stderr)
            QMessageBox.critical(None, "Erro ao Abrir Croqui", msg_erro)
            sys.exit(1)
            
    # Inicialização Padrão (Experimental Workspace com Autenticação e Sync)
    controlador = ControladorAplicativo()
    sys.exit(controlador.executar())



if __name__ == "__main__":
    main()
