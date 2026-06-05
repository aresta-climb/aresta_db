from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path
import traceback
import sys
import shutil
from datetime import datetime
import pygit2
import github

from editor.core.auth import GerenciadorAutenticacao
from editor.core.sync import GerenciadorSincronizacao
from editor.core.storage import GerenciadorCaminhos
import github

class TarefaInicializacao(QThread):
    """
    Thread responsável por coordenar a inicialização:
    1. Storage check
    2. GitHub Auth (Token check ou Device Flow)
    3. Git Sync (Clone ou Pull/Reset)
    """
    
    progresso = pyqtSignal(int)
    mostrar_progresso = pyqtSignal(bool)
    status = pyqtSignal(str)
    auth_requerida = pyqtSignal(str) # user_code
    auth_concluida = pyqtSignal()
    sucesso = pyqtSignal()
    erro = pyqtSignal(str)

    def __init__(self, id_cliente: str):
        super().__init__()
        self.id_cliente = id_cliente
        self.storage = GerenciadorCaminhos()
        self.auth = GerenciadorAutenticacao(id_cliente)

    def run(self):
        try:
            print(f"\n[INFO] Iniciando tarefa de inicialização (Client ID: {self.id_cliente})...")
            
            # 1. Inicializar diretórios
            self.status.emit("Verificando pastas locais...")
            print("[INFO] Verificando diretórios locais...")
            self.storage.inicializar_diretorios()
            self.progresso.emit(10)

            # 2. Autenticação
            self.status.emit("Verificando autenticação...")
            print("[INFO] Verificando token no keyring...")
            token = self.auth.recuperar_token()
            if not token or not self.auth.validar_token(token):
                print("[WARN] Token não encontrado ou inválido. Iniciando Device Flow...")
                self.status.emit("Autenticação necessária...")
                dados = self.auth.solicitar_codigo_dispositivo()
                print(f"[INFO] Código recebido: {dados['user_code']}")
                self.auth_requerida.emit(dados["user_code"])
                
                print("[INFO] Aguardando autorização do usuário no GitHub...")
                token = self.auth.aguardar_token()
                if not token:
                    print("[ERROR] Usuário cancelou ou tempo limite esgotado.")
                    self.erro.emit("Autenticação cancelada ou expirada.")
                    return
                
                print("[INFO] Token recebido com sucesso. Salvando...")
                self.auth.salvar_token(token)
                self.auth_concluida.emit()
                if not self.auth.validar_token(token):
                    print("[ERROR] O novo token recebido falhou na validação inicial.")
                    self.erro.emit("Falha ao validar novo token.")
                    return

            self.progresso.emit(40)
            print(f"[INFO] Autenticado com sucesso como: {self.auth.usuario_logado}")
            self.status.emit(f"Logado como: {self.auth.usuario_logado}")

            # 3. Sincronização Git
            self.status.emit("Sincronizando repositório base...")
            print("[INFO] Iniciando sincronização Git...")
            self.mostrar_progresso.emit(True)
            
            token = self.auth.recuperar_token()
            g = github.Github(auth=github.Auth.Token(token))
            sync = GerenciadorSincronizacao(self.storage.obter_caminho_base_repo(), token=token)
            
            caminho_repo = self.storage.obter_caminho_base_repo()
            if not caminho_repo.exists() or not any(caminho_repo.iterdir()):
                print(f"[INFO] Repositório não encontrado em {caminho_repo}. Clonando...")
                try:
                    url_clone = sync.obter_url_clone(g)
                    print(f"[INFO] URL de clone obtida: {url_clone}")
                    sync.clonar(url_clone, progresso_callback=lambda p: self.progresso.emit(40 + int(p * 0.6)))
                except github.UnknownObjectException:
                    mensagem_erro = (
                        "Repositório 'aresta-climb/aresta_db' não encontrado (404).\n\n"
                        "Se o repositório for privado e pertencer a uma Organização, "
                        "você precisa autorizar este App nas configurações da Organização aresta-climb."
                    )
                    print(f"[ERROR] {mensagem_erro}")
                    self.erro.emit(mensagem_erro)
                    return
            else:
                print(f"[INFO] Repositório encontrado em {caminho_repo}. Sincronizando...")
                sync.sincronizar(progresso_callback=lambda p: self.progresso.emit(40 + int(p * 0.6)))

            self.progresso.emit(100)
            print("[INFO] Inicialização concluída com sucesso!")
            self.status.emit("Inicialização concluída!")
            self.sucesso.emit()

        except Exception as e:
            print(f"\n[FATAL] Erro durante a inicialização:")
            traceback.print_exc()
            self.erro.emit(f"Erro: {str(e)}")

class TarefaPublicacao(QThread):
    """
    Thread responsável por:
    1. Sincronizar o repositório base local.
    2. Criar uma nova branch.
    3. Copiar as mudanças do croqui experimental para o repositório base.
    4. Commit e Push para o fork do usuário.
    5. Criar o Pull Request no GitHub.
    """
    sucesso = pyqtSignal(str)
    erro = pyqtSignal(str)
    progresso = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, token, storage, caminho_database_croqui, id_croqui, dados_pr):
        super().__init__()
        self.token = token
        self.storage = storage
        self.caminho_database_croqui = caminho_database_croqui
        self.id_croqui = id_croqui
        self.dados_pr = dados_pr

    def run(self):
        try:
            self.status.emit("Iniciando publicação...")
            self.progresso.emit(5)
            
            g = github.Github(auth=github.Auth.Token(self.token))
            sync = GerenciadorSincronizacao(self.storage.obter_caminho_base_repo(), token=self.token)
            
            # 1. Sincronizar Repo Base
            self.status.emit("Sincronizando repositório base...")
            sync.sincronizar()
            self.progresso.emit(20)
            
            # 2. Criar Branch
            repo = pygit2.Repository(str(self.storage.obter_caminho_base_repo()))
            nome_branch = f"edicao_{self.id_croqui}_{datetime.now().strftime('%H%M%S')}"
            
            # Pega o commit da branch principal (main/master)
            try:
                commit_base = repo.lookup_reference('refs/heads/main').peel()
            except KeyError:
                commit_base = repo.lookup_reference('refs/heads/master').peel()
                
            branch = repo.create_branch(nome_branch, commit_base)
            self.status.emit(f"Criada branch: {nome_branch}")
            
            # Switch para a nova branch (soft reset + checkout)
            repo.checkout(branch)
            self.progresso.emit(40)
            
            # 3. Copiar Arquivos
            self.status.emit("Copiando alterações...")
            destino = self.storage.obter_caminho_base_repo() / "database" / self.id_croqui
            if destino.exists():
                shutil.rmtree(destino)
            shutil.copytree(self.caminho_database_croqui, destino)
            self.progresso.emit(60)
            
            # 4. Commit e Push
            self.status.emit("Enviando para o GitHub...")
            index = repo.index
            index.add_all([f"database/{self.id_croqui}"])
            index.write()
            
            tree = index.write_tree()
            autor = pygit2.Signature(g.get_user().name or g.get_user().login, g.get_user().email or "editor@aresta.local")
            
            repo.create_commit(
                'refs/heads/' + nome_branch,
                autor, autor,
                f"Atualização do croqui {self.id_croqui} via Aresta Editor",
                tree,
                [commit_base.id]
            )
            
            # Push
            remoto = repo.remotes["origin"]
            callbacks = sync._obter_callbacks()
            remoto.push([f'refs/heads/{nome_branch}'], callbacks=callbacks)
            self.progresso.emit(80)
            
            # 5. Criar PR
            self.status.emit("Criando Pull Request...")
            pr = sync.criar_pull_request(
                g, nome_branch, 
                self.dados_pr["titulo"], 
                self.dados_pr["descricao"]
            )
            
            self.progresso.emit(100)
            self.sucesso.emit(pr.html_url)
            
        except Exception as e:
            traceback.print_exc()
            self.erro.emit(str(e))

class TarefaExportacao(QThread):
    """
    Thread responsável por exportar um croqui para um arquivo .croqui ofuscado.
    """
    sucesso = pyqtSignal()
    erro = pyqtSignal(str)
    
    def __init__(self, caminho_raiz, caminho_destino):
        super().__init__()
        self.caminho_raiz = caminho_raiz
        self.caminho_destino = caminho_destino
        
    def run(self):
        try:
            from editor.core.croqui_format import empacotar_croqui
            empacotar_croqui(self.caminho_raiz, self.caminho_destino)
            self.sucesso.emit()
        except Exception as e:
            traceback.print_exc()
            self.erro.emit(str(e))

class TarefaDadosConexao(QThread):
    """
    Thread responsável por obter o IP local e gerar o QR Code de conexão.
    Evita travamentos da UI durante a abertura do diálogo.
    """
    concluido = pyqtSignal(str, bytes) # ip, qr_bytes
    
    def __init__(self, servidor):
        super().__init__()
        self.servidor = servidor
        
    def run(self):
        try:
            # Aguarda o servidor fazer o bind da porta em background
            import time
            tentativas = 0
            while self.servidor.porta is None and tentativas < 100:
                time.sleep(0.05)
                tentativas += 1
                
            if self.servidor.porta is None:
                return # Falha ao iniciar servidor

            ip = self.servidor.obter_ip_local()
            porta = self.servidor.porta
            url = f"http://{ip}:{porta}"
            qr_bytes = self.servidor.gerar_qr_code(url)
            self.concluido.emit(url, qr_bytes)
        except Exception:
            traceback.print_exc()
