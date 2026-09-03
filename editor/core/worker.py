# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QThread, Signal
from pathlib import Path
import traceback
import sys
import shutil
from datetime import datetime
import threading
import pygit2

from editor.core.gerenciador_sessao import GerenciadorSessao, SessaoUsuario
from editor.core.cliente_auth_supabase import ClienteAuthSupabase
from editor.core.servico_submissao import ServicoSubmissao
from editor.core.sync import GerenciadorSincronizacao
from editor.core.storage import GerenciadorCaminhos
from editor.core.servico_loja import ServicoLoja
from typing import Optional, Any, Dict
from collections.abc import Callable

class TarefaInicializacao(QThread):
    """
    Thread responsável por coordenar a inicialização:
    1. Storage check
    2. Microsoft Store Update check
    3. Autenticação Supabase / GitHub
    4. Git Sync (Clone ou Pull/Reset)
    """
    
    progresso: Signal = Signal(int)
    mostrar_progresso: Signal = Signal(bool)
    status: Signal = Signal(str)
    atualizacao_disponivel: Signal = Signal(object) # ResultadoAtualizacao
    auth_requerida: Signal = Signal(str) # mantido para compatibilidade
    solicitar_login_ui: Signal = Signal()
    auth_concluida: Signal = Signal()
    sucesso: Signal = Signal()
    erro: Signal = Signal(str)

    def __init__(self, id_cliente: str = "") -> None:
        super().__init__()
        self.id_cliente: str = id_cliente
        self.storage: GerenciadorCaminhos = GerenciadorCaminhos()
        self.gerenciador_sessao: GerenciadorSessao = GerenciadorSessao()
        self.cliente_auth: ClienteAuthSupabase = ClienteAuthSupabase()
        self.servico_loja: ServicoLoja = ServicoLoja()
        self.sessao_usuario: Optional[SessaoUsuario] = None
        self._evento_autenticacao: threading.Event = threading.Event()
        self._login_cancelado: bool = False

    def definir_sessao_concluida(self, sessao: Optional[SessaoUsuario]) -> None:
        """Desbloqueia a thread de inicialização com o resultado do diálogo de login."""
        if sessao:
            self.sessao_usuario = sessao
            self._login_cancelado = False
        else:
            self._login_cancelado = True
        self._evento_autenticacao.set()

    def run(self) -> None:
        try:
            from editor.core.registro_log import logger
            logger.info("Iniciando tarefa de inicialização...")
            
            # 1. Inicializar diretórios
            self.status.emit("Verificando pastas locais...")
            self.storage.inicializar_diretorios()
            self.progresso.emit(10)

            # 2. Verificação de Atualização na Microsoft Store
            self.status.emit("Verificando atualizações na Microsoft Store...")
            resultado_update = self.servico_loja.verificar_atualizacoes_disponiveis()
            if resultado_update.tem_atualizacao:
                logger.info(f"Atualização detectada na Microsoft Store: {resultado_update.versao_disponivel}")
                self.atualizacao_disponivel.emit(resultado_update)
                return

            self.progresso.emit(20)

            # 3. Autenticação
            self.status.emit("Verificando autenticação...")
            sessao = self.gerenciador_sessao.obter_sessao()

            if sessao and sessao.jwt_supabase:
                try:
                    self.cliente_auth.obter_usuario_atual(sessao.jwt_supabase)
                    self.sessao_usuario = sessao
                except Exception:
                    try:
                        novos_dados = self.cliente_auth.renovar_sessao(sessao.token_atualizacao)
                        sessao.jwt_supabase = novos_dados["access_token"]
                        sessao.token_atualizacao = novos_dados.get("refresh_token", sessao.token_atualizacao)
                        self.gerenciador_sessao.salvar_sessao(sessao)
                        self.sessao_usuario = sessao
                    except Exception:
                        sessao = None

            if not self.sessao_usuario:
                self.status.emit("Autenticação necessária...")
                self._evento_autenticacao.clear()
                self._login_cancelado = False
                self.auth_requerida.emit("")
                self.solicitar_login_ui.emit()

                # Bloqueia a thread de inicialização até o usuário concluir ou cancelar o login
                self._evento_autenticacao.wait()

                if self._login_cancelado or not self.sessao_usuario:
                    logger.warning("Autenticação não concluída ou cancelada pelo usuário.")
                    self.erro.emit("Autenticação necessária para utilizar o Aresta Editor.")
                    return

            self.progresso.emit(40)
            usuario_identificado = self.sessao_usuario.nome_completo if self.sessao_usuario else "Convidado"
            self.status.emit(f"Logado como: {usuario_identificado}")

            # 4. Sincronização Git
            self.status.emit("Sincronizando repositório base...")
            self.mostrar_progresso.emit(True)
            
            token_git = self.sessao_usuario.token_github if self.sessao_usuario else None
            sync = GerenciadorSincronizacao(self.storage.obter_caminho_base_repo(), token=token_git)
            
            caminho_repo = self.storage.obter_caminho_base_repo()
            if not caminho_repo.exists() or not any(caminho_repo.iterdir()):
                logger.info(f"Repositório não encontrado em {caminho_repo}. Clonando...")
                url_clone = sync.obter_url_clone()
                logger.info(f"URL de clone obtida: {url_clone}")
                sync.clonar(url_clone, progresso_callback=lambda p: self.progresso.emit(40 + int(p * 0.3)))
            else:
                logger.info(f"Repositório existente em {caminho_repo}. Configurando remotes...")
                sync.configurar_remotes()
            
            # Fetch Origin e Upstream
            logger.info("Executando fetch de dados dos remotes...")
            self.status.emit("Fazendo fetch de dados...")
            sync.fazer_fetch(progresso_callback=lambda p: self.progresso.emit(70 + int(p * 0.15)))
            
            # Checkout do upstream/main
            logger.info("Fazendo checkout do upstream/main...")
            self.status.emit("Aplicando estado oficial mais recente...")
            sync.fazer_checkout_main_upstream()

            logger.info("[Worker] Inicialização e sincronização finalizadas com sucesso!")
            self.progresso.emit(100)
            self.status.emit("Inicialização concluída!")
            self.sucesso.emit()

        except Exception as e:
            from editor.core.registro_log import logger
            logger.critical(f"Erro durante a inicialização: {e}", exc_info=True)
            self.erro.emit(str(e))

class TarefaPublicacao(QThread):
    """
    Thread responsável por coordenar a publicação de sugestões de croquis
    via ServicoSubmissao em segundo plano, emitindo sinais de progresso para a UI.
    """
    sucesso: Signal = Signal(str, str, str)
    aviso: Signal = Signal(str)
    erro: Signal = Signal(str)
    progresso: Signal = Signal(int)
    status: Signal = Signal(str)

    def __init__(
        self,
        token: Optional[str] = None,
        storage: Optional[GerenciadorCaminhos] = None,
        caminho_database_croqui: Optional[Path] = None,
        id_croqui: str = "",
        dados_pr: Optional[Dict[str, Any]] = None,
        modo_atualizacao: bool = False,
        pr_branch: Optional[str] = None,
        sessao: Optional[SessaoUsuario] = None,
        servico_submissao: Optional[ServicoSubmissao] = None,
    ) -> None:
        super().__init__()
        self.storage: GerenciadorCaminhos = storage or GerenciadorCaminhos()
        self.caminho_database_croqui: Optional[Path] = caminho_database_croqui
        self.id_croqui: str = id_croqui
        self.dados_pr: Dict[str, Any] = dados_pr or {}
        self.modo_atualizacao: bool = modo_atualizacao
        self.pr_branch: Optional[str] = pr_branch
        
        if sessao is None:
            gerenciador = GerenciadorSessao()
            sessao = gerenciador.obter_sessao()
            if not sessao:
                sessao = SessaoUsuario(
                    email="anonimo@arestaclimb.com",
                    nome_completo="Colaborador Aresta",
                    jwt_supabase=token or "",
                    token_atualizacao="",
                    token_github=token,
                )
        self.sessao: SessaoUsuario = sessao
        self.servico_submissao: ServicoSubmissao = servico_submissao or ServicoSubmissao(
            caminho_repo_base=self.storage.obter_caminho_base_repo()
        )

    def run(self) -> None:
        try:
            self.status.emit("Iniciando publicação...")
            self.progresso.emit(5)

            def callback_progresso(pct: int, msg: str) -> None:
                self.progresso.emit(pct)
                self.status.emit(msg)

            dados = self.dados_pr or {}
            titulo = dados.get("titulo", f"Atualização do croqui {self.id_croqui}")
            descricao = dados.get("descricao", "Alterações enviadas via Aresta Editor")

            branch_alvo = self.pr_branch if self.modo_atualizacao else None

            if not self.caminho_database_croqui:
                self.erro.emit("Caminho do banco de dados do croqui não informado para submissão.")
                return

            resultado = self.servico_submissao.submeter_sugestao(
                caminho_database_croqui=self.caminho_database_croqui,
                id_croqui=self.id_croqui,
                titulo=titulo,
                descricao=descricao,
                sessao=self.sessao,
                branch_existente=branch_alvo,
                callback_progresso=callback_progresso,
            )

            if resultado.sem_alteracoes:
                self.aviso.emit(
                    resultado.mensagem
                    or "Nenhuma alteração foi detectada no croqui.\nO Pull Request já está atualizado!"
                )
            else:
                self.sucesso.emit(
                    resultado.pr_url or "atualizado",
                    resultado.nome_branch,
                    "aresta-climb",
                )
        except Exception as e:
            from editor.core.registro_log import logger
            from editor.core.telemetria import capturar_falha_submissao
            logger.critical(f"Erro durante a publicação do croqui {self.id_croqui}: {e}", exc_info=True)
            capturar_falha_submissao(
                erro=e,
                id_croqui=self.id_croqui,
                etapa="execucao_tarefa_publicacao",
                categoria="inesperado",
                contexto_extra={"id_croqui": self.id_croqui, "modo_atualizacao": self.modo_atualizacao},
            )
            self.erro.emit(str(e))

class TarefaExportacao(QThread):
    """
    Thread responsável por exportar um croqui para um arquivo .croqui ofuscado.
    """
    sucesso: Signal = Signal()
    erro: Signal = Signal(str)
    
    def __init__(self, caminho_raiz: Path, caminho_destino: Path) -> None:
        super().__init__()
        self.caminho_raiz: Path = Path(caminho_raiz)
        self.caminho_destino: Path = Path(caminho_destino)
        
    def run(self) -> None:
        try:
            from editor.core.croqui_format import empacotar_croqui
            empacotar_croqui(self.caminho_raiz, self.caminho_destino)
            self.sucesso.emit()
        except Exception as e:
            traceback.print_exc()
            self.erro.emit(str(e))

class TarefaDadosConexao(QThread):
    """
    Thread responsável por obter a URL canônica de prévia, IP local e gerar o QR Code de conexão.
    Evita travamentos da UI durante a abertura do diálogo.
    """
    concluido: Signal = Signal(str, bytes, str) # url, qr_bytes, codigo_formatado
    
    def __init__(self, servidor: Any) -> None:
        super().__init__()
        self.servidor: Any = servidor
        
    def run(self) -> None:
        try:
            # Aguarda o servidor fazer o bind da porta em background
            import time
            tentativas = 0
            while self.servidor.porta is None and tentativas < 100:
                time.sleep(0.05)
                tentativas += 1
                
            if self.servidor.porta is None:
                return # Falha ao iniciar servidor

            if hasattr(self.servidor, "solicitar_sessao_servidor"):
                if not getattr(self.servidor, "codigo_sessao", None):
                    self.servidor.solicitar_sessao_servidor()

            from editor.core.codigo_sessao import formatar_codigo
            if hasattr(self.servidor, "obter_url_previa_canonica"):
                url = self.servidor.obter_url_previa_canonica()
            else:
                ip = self.servidor.obter_ip_local()
                porta = self.servidor.porta
                url = f"http://{ip}:{porta}"

            codigo_raw = getattr(self.servidor, "codigo_sessao", None)
            if codigo_raw:
                try:
                    codigo_formatado = formatar_codigo(codigo_raw)
                except Exception:
                    codigo_formatado = str(codigo_raw)
            else:
                codigo_formatado = ""

            qr_bytes = self.servidor.gerar_qr_code(url)
            self.concluido.emit(url, qr_bytes, codigo_formatado)
        except Exception:
            traceback.print_exc()

class TarefaSalvamento(QThread):
    """
    Thread responsável por salvar em background (I/O intensivo e compilação).
    """
    sucesso: Signal = Signal(object, object, bool, int) # caminho_retornado, erros, houve_renomeacao, undo_index
    erro: Signal = Signal(str)

    def __init__(
        self,
        workspace: Any,
        storage: Optional[GerenciadorCaminhos],
        caminho_db: Path,
        croqui_data: Dict[str, Any],
        novo_id: str,
        id_atual: str,
        undo_index: int,
    ) -> None:
        super().__init__()
        self.workspace: Any = workspace
        self.storage: Optional[GerenciadorCaminhos] = storage
        self.caminho_db: Path = Path(caminho_db)
        self.croqui_data: Dict[str, Any] = croqui_data
        self.novo_id: str = novo_id
        self.id_atual: str = id_atual
        self.undo_index: int = undo_index

    def run(self) -> None:
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
        except BaseException as e:
            traceback.print_exc()
            from editor.core.registro_log import logger
            from editor.core.telemetria import capturar_excecao
            logger.critical(f"Erro durante o salvamento do croqui {self.novo_id or self.id_atual}: {e}", exc_info=True)
            capturar_excecao(
                erro=e,
                id_croqui=self.novo_id or self.id_atual,
                etapa="tarefa_salvamento",
                contexto_extra={"novo_id": self.novo_id, "id_atual": self.id_atual, "caminho_db": str(self.caminho_db)},
            )
            self.erro.emit(str(e))

