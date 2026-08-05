# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

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
                    sync.clonar(url_clone, progresso_callback=lambda p: self.progresso.emit(40 + int(p * 0.3)))
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
                print(f"[INFO] Repositório encontrado em {caminho_repo}. Configurando remotes...")
            
            # Configura Remotes (Origin=Fork, Upstream=Base)
            sync.configurar_remotes(g)
            
            # Fetch Origin e Upstream
            self.status.emit("Fazendo fetch de dados (origin e upstream)...")
            sync.fazer_fetch(progresso_callback=lambda p: self.progresso.emit(70 + int(p * 0.15)))
            
            # Checkout do upstream/main
            self.status.emit("Aplicando estado oficial mais recente...")
            sync.fazer_checkout_main_upstream()

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
    sucesso = pyqtSignal(str, str, str)
    aviso = pyqtSignal(str)
    erro = pyqtSignal(str)
    progresso = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, token, storage, caminho_database_croqui, id_croqui, dados_pr, modo_atualizacao=False, pr_branch=None):
        super().__init__()
        self.token = token
        self.storage = storage
        self.caminho_database_croqui = caminho_database_croqui
        self.id_croqui = id_croqui
        self.dados_pr = dados_pr
        self.modo_atualizacao = modo_atualizacao
        self.pr_branch = pr_branch

    def run(self):
        try:
            self.status.emit("Iniciando publicação...")
            self.progresso.emit(5)
            
            merge_realizado = False
            
            g = github.Github(auth=github.Auth.Token(self.token))
            sync = GerenciadorSincronizacao(self.storage.obter_caminho_base_repo(), token=self.token)
            
            # 1. Sincronizar Repo Base
            self.status.emit("Sincronizando repositório base...")
            sync.configurar_remotes(g)
            sync.fazer_fetch()
            self.progresso.emit(20)
            
            repo = pygit2.Repository(str(self.storage.obter_caminho_base_repo()))
            
            if self.modo_atualizacao and self.pr_branch:
                # Fazer checkout da branch existente no origin
                nome_branch = self.pr_branch.replace("editor/", "") if "editor/" in self.pr_branch else self.pr_branch # limpar owner:branch? Nao, pr_branch é a branch local
                # Ajuste se for do tipo 'owner:branch' -> nós criamos com nome_branch local igual ao remoto
                if ":" in nome_branch:
                    nome_branch = nome_branch.split(":")[-1]
                    
                self.status.emit(f"Fazendo checkout da branch {nome_branch}...")
                
                if nome_branch in repo.branches.local:
                    branch = repo.branches.local[nome_branch]
                    remote_branch = repo.branches.remote[f"origin/{nome_branch}"]
                    # Descarta commits locais não enviados e sincroniza com o remoto
                    branch.set_target(remote_branch.target)
                else:
                    remote_branch = repo.branches.remote[f"origin/{nome_branch}"]
                    branch = repo.branches.local.create(nome_branch, repo[remote_branch.target])
                
                repo.checkout(branch)
                
                self.status.emit("Sincronizando Pull Request com a main...")
                commit_base = repo.branches.remote["upstream/main"].peel()
                repo.merge(commit_base.id)
                
                if repo.index.conflicts is not None:
                    repo.reset(repo.head.target, pygit2.GIT_RESET_HARD)
                    repo.state_cleanup()
                    raise Exception("Há conflitos com a branch main. Por favor, resolva-os atualizando a branch do PR pelo GitHub antes de publicar aqui.")
                
                tree_id = repo.index.write_tree()
                head_commit = repo.head.peel()
                
                if tree_id != head_commit.tree_id:
                    autor = pygit2.Signature(g.get_user().name or g.get_user().login, g.get_user().email or "editor@aresta.local")
                    repo.create_commit(
                        'HEAD',
                        autor, autor,
                        f"Merge branch 'main' into {nome_branch}\n\nSigned-off-by: {autor.name} <{autor.email}>",
                        tree_id,
                        [head_commit.id, commit_base.id]
                    )
                    merge_realizado = True
                repo.state_cleanup()
            else:
                # 2. Criar Nova Branch a partir de upstream/main
                nome_branch = f"edicao_{self.id_croqui}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                sync.fazer_checkout_main_upstream()
                commit_base = repo.lookup_reference('refs/heads/main').peel()
                branch = repo.create_branch(nome_branch, commit_base)
                self.status.emit(f"Criada branch: {nome_branch}")
                repo.checkout(branch)

            self.progresso.emit(40)
            
            # 3. Copiar Arquivos
            self.status.emit("Copiando alterações...")
            
            # Verificar se houve mudança de ID para remover o antigo
            import yaml
            from google.protobuf.json_format import ParseDict
            from aresta_api.proto.generated.croqui_experimental_pb2 import CroquiExperimental
            
            id_original = None
            yaml_meta = self.caminho_database_croqui.parent / "croqui_experimental.yaml"
            if yaml_meta.is_file():
                try:
                    with open(yaml_meta, "r", encoding="utf-8") as f:
                        dados_meta = yaml.safe_load(f) or {}
                        meta = CroquiExperimental()
                        ParseDict(dados_meta, meta, ignore_unknown_fields=True)
                        id_original = meta.id_original if meta.id_original else None
                except Exception:
                    pass
                    
            if id_original:
                id_publicacao = id_original
            else:
                id_publicacao = self.id_croqui
                    
            import filecmp
            
            def sync_dir(src: Path, dst: Path):
                if not dst.exists():
                    dst.mkdir(parents=True)
                
                # Copiar ou atualizar arquivos
                for item in src.iterdir():
                    dst_item = dst / item.name
                    if item.is_dir():
                        sync_dir(item, dst_item)
                    else:
                        if not dst_item.exists() or not filecmp.cmp(item, dst_item, shallow=False):
                            shutil.copy2(item, dst_item)
                            
                # Remover arquivos/pastas que não existem mais na origem
                for item in dst.iterdir():
                    src_item = src / item.name
                    if not src_item.exists():
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()

            destino = self.storage.obter_caminho_base_repo() / "database" / id_publicacao
            sync_dir(self.caminho_database_croqui, destino)
            self.progresso.emit(60)
            
            # 4. Checar modificações, Commit e Push
            self.status.emit("Checando modificações...")
            index = repo.index
            index.add_all([f"database/{id_publicacao}"])
            index.write()
            
            tree_id = index.write_tree()
            head_commit = repo.head.peel()
            
            if tree_id == head_commit.tree_id:
                if not merge_realizado:
                    self.aviso.emit("Nenhuma alteração foi detectada no croqui.\nO Pull Request já está atualizado!")
                    return
                else:
                    self.status.emit("Enviando merge para o GitHub...")
            else:
                self.status.emit("Enviando para o GitHub...")
                tree = index.write_tree()
                autor = pygit2.Signature(g.get_user().name or g.get_user().login, g.get_user().email or "editor@aresta.local")
                
                repo.create_commit(
                    'refs/heads/' + nome_branch,
                    autor, autor,
                    f"Atualização do croqui {self.id_croqui} via Editor Aresta\n\nSigned-off-by: {autor.name} <{autor.email}>",
                    tree,
                    [repo.head.peel().id]
                )
            
            # Push
            remoto = repo.remotes["origin"]
            callbacks = sync._obter_callbacks()
            remoto.push([f'refs/heads/{nome_branch}'], callbacks=callbacks)
            self.progresso.emit(80)
            
            # 5. Criar/Atualizar PR
            if not self.modo_atualizacao:
                self.status.emit("Criando Pull Request...")
                pr = sync.criar_pull_request(
                    g, nome_branch, 
                    self.dados_pr["titulo"], 
                    self.dados_pr["descricao"]
                )
                html_url = pr.html_url
                pr_owner = g.get_user().login
                if "aresta-climb/aresta_db" in repo.remotes["origin"].url:
                    pr_owner = "aresta-climb"
            else:
                self.status.emit("Atualizando Pull Request (Push completo)...")
                # Se for atualização, não precisa de nova PR na API, apenas confirmamos os dados
                # pr_owner e html_url já devem estar gravados lá, mas vamos passar os mesmos que temos localmente
                # ou não passar pra frente
                html_url = "atualizado"
                pr_owner = "atualizado"
            
            self.progresso.emit(100)
            self.sucesso.emit(html_url, nome_branch, pr_owner)
            
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

class TarefaSalvamento(QThread):
    """
    Thread responsável por salvar em background (I/O intensivo e compilação).
    """
    sucesso = pyqtSignal(object, object, bool, int) # caminho_retornado, erros, houve_renomeacao, undo_index
    erro = pyqtSignal(str)

    def __init__(self, workspace, storage, caminho_db, croqui_data, novo_id, id_atual, undo_index):
        super().__init__()
        self.workspace = workspace
        self.storage = storage
        self.caminho_db = caminho_db
        self.croqui_data = croqui_data
        self.novo_id = novo_id
        self.id_atual = id_atual
        self.undo_index = undo_index

    def run(self):
        try:
            import yaml
            
            yaml_path = self.caminho_db / "croqui.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(self.croqui_data, f, allow_unicode=True, sort_keys=False)
                
            houve_renomeacao = False
            if self.novo_id and self.id_atual and self.novo_id != self.id_atual:
                houve_renomeacao = True
                
            caminho_retornado, erros = self.workspace.processar_renomeacao_e_compilacao(self.novo_id, self.id_atual, self.storage)
            
            self.sucesso.emit(caminho_retornado, erros, houve_renomeacao, self.undo_index)
        except Exception as e:
            traceback.print_exc()
            self.erro.emit(str(e))
