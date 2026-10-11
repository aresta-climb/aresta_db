# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import filecmp
import os
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pygit2
import requests

from editor.core.cliente_auth_supabase import ClienteAuthSupabase
from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.storage import GerenciadorCaminhos
from editor.core.telemetria import (
    capturar_falha_submissao,
    registrar_breadcrumb_submissao,
)

_URL_SUPABASE_FALLBACK = "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"
_CHAVE_PUBLICA_FALLBACK = "sb_publishable_ZOrO8ix2EsWlSHEWrZr42A_JycWrAV3"

_URL_SUPABASE_PADRAO = (os.getenv("ARESTA_SUPABASE_URL") or "").strip() or _URL_SUPABASE_FALLBACK
_CHAVE_PUBLICA_PADRAO = (
    os.getenv("ARESTA_SUPABASE_PUBLISHABLE_KEY") or ""
).strip() or _CHAVE_PUBLICA_FALLBACK
_TEMPO_LIMITE_PR_PADRAO: int = 60


class ErroSubmissao(Exception):
    """Exceção levantada em falhas no processo de submissão de sugestões."""

    pass


class StatusSincronizacao(Enum):
    """Representa os possíveis estados do processo de sincronização remota."""

    ATUALIZADO = "atualizado"
    MESCLADO = "mesclado"
    CONFLITO = "conflito"
    ERRO = "erro"


@dataclass
class ResultadoSincronizacao:
    """Representa o resultado da operação de sincronização remota de uma PR."""

    status: StatusSincronizacao
    mensagem: str = ""
    arquivos_conflito: list[str] = field(default_factory=list)
    commit_merge: str | None = None


@dataclass
class ResultadoSubmissao:
    """Representa o resultado da operação de submissão de sugestão."""

    sucesso: bool
    pr_number: int | None = None
    pr_url: str | None = None
    nome_branch: str = ""
    mensagem: str = ""
    sem_alteracoes: bool = False


def gerar_nome_branch(id_croqui: str) -> str:
    """Gera nome único de branch no formato edicao-<id_croqui>-<uuid8>."""
    sufixo_unico = uuid.uuid4().hex[:8]
    return f"edicao-{id_croqui}-{sufixo_unico}"


def _extrair_id_croqui_da_branch(branch: str) -> str:
    """Extrai o id_croqui de uma branch com prefixo edicao-, sugestao- ou proposta-."""
    for prefixo in ("edicao-", "sugestao-", "proposta-"):
        if branch.startswith(prefixo):
            resto = branch[len(prefixo) :]
            partes = resto.rsplit("-", 1)
            return partes[0] if len(partes) == 2 else resto
    return branch


class ServicoSubmissao:
    """
    Biblioteca pura para empacotamento, commit assinado com pygit2,
    push via Git Proxy e formalização de Pull Requests no Aresta DB.
    """

    def __init__(
        self,
        caminho_repo_base: Path | None = None,
        url_supabase: str | None = None,
        chave_publica: str | None = None,
        cliente_auth: ClienteAuthSupabase | None = None,
        tempo_limite_requisicao: int = _TEMPO_LIMITE_PR_PADRAO,
    ) -> None:
        self.caminho_repo_base: Path = (
            caminho_repo_base or GerenciadorCaminhos().obter_caminho_base_repo()
        )
        url = (url_supabase or "").strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = _URL_SUPABASE_PADRAO
        self.url_supabase: str = url.rstrip("/")
        chave = (chave_publica or "").strip() or _CHAVE_PUBLICA_PADRAO
        self.chave_publica: str = chave
        self.cliente_auth: ClienteAuthSupabase = cliente_auth or ClienteAuthSupabase(
            url_supabase=self.url_supabase, chave_publica=self.chave_publica
        )
        self.tempo_limite_requisicao: int = tempo_limite_requisicao

    def sincronizar_arquivos_croqui(self, origem: Path, destino_repo: Path, id_croqui: str) -> Path:
        """
        Espelha estritamente os arquivos da pasta do croqui experimental
        para database/<id_croqui>/ no repositório base local.
        """
        destino_croqui = destino_repo / "database" / id_croqui
        self._espelhar_diretorio(origem, destino_croqui)
        return destino_croqui

    def _espelhar_diretorio(self, origem: Path, destino: Path) -> None:
        """Sincroniza recursivamente o conteúdo de origem para destino."""
        destino.mkdir(parents=True, exist_ok=True)

        # 1. Copia ou atualiza arquivos/diretórios modificados
        for item in origem.iterdir():
            destino_item = destino / item.name
            if item.is_dir():
                self._espelhar_diretorio(item, destino_item)
            else:
                if not destino_item.exists() or not filecmp.cmp(item, destino_item, shallow=False):
                    shutil.copy2(item, destino_item)

        # 2. Remove arquivos/diretórios no destino que não existem mais na origem
        for item in destino.iterdir():
            origem_item = origem / item.name
            if not origem_item.exists():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    def obter_arquivos_modificados(
        self, caminho_database_croqui: Path, id_croqui: str
    ) -> list[str]:
        """
        Calcula a lista de arquivos modificados, adicionados ou removidos
        entre a pasta de trabalho do croqui e o repositório base oficial.
        """
        if not caminho_database_croqui or not caminho_database_croqui.is_dir():
            return []

        caminho_base_croqui = self.caminho_repo_base / "database" / id_croqui
        modificados: list[str] = []

        # 1. Arquivos locais presentes na pasta de trabalho
        arquivos_origem = {
            f.relative_to(caminho_database_croqui).as_posix(): f
            for f in caminho_database_croqui.rglob("*")
            if f.is_file()
            and not f.name.startswith(".")
            and not any(p.startswith(".") for p in f.relative_to(caminho_database_croqui).parts)
        }

        # 2. Se a base não existe, todos os arquivos locais são novas adições
        if not caminho_base_croqui.is_dir():
            return sorted(arquivos_origem.keys())

        # 3. Arquivos existentes na base oficial
        arquivos_base = {
            f.relative_to(caminho_base_croqui).as_posix(): f
            for f in caminho_base_croqui.rglob("*")
            if f.is_file()
            and not f.name.startswith(".")
            and not any(p.startswith(".") for p in f.relative_to(caminho_base_croqui).parts)
        }

        # 4. Compara arquivos locais com a base (adições e modificações)
        for rel_path, arquivo_origem in arquivos_origem.items():
            if rel_path not in arquivos_base:
                modificados.append(rel_path)
            else:
                arquivo_base = arquivos_base[rel_path]
                if not filecmp.cmp(arquivo_origem, arquivo_base, shallow=False):
                    modificados.append(rel_path)

        # 5. Detecta arquivos removidos
        for rel_path in arquivos_base:
            if rel_path not in arquivos_origem:
                modificados.append(rel_path)

        return sorted(modificados)

    def criar_commit_sugestao(
        self,
        repo: pygit2.Repository,
        nome_branch: str,
        id_croqui: str,
        titulo: str,
        descricao: str,
        sessao: SessaoUsuario,
    ) -> pygit2.Commit | None:
        """
        Realiza staging dos arquivos em database/<id_croqui>/ e cria o commit assinado.
        Retorna o Commit criado ou None se não houver modificações reais na árvore.
        """
        head_commit = cast(pygit2.Commit, repo.head.peel())
        caminho_relativo = f"database/{id_croqui}"
        index = repo.index

        # 1. Isola o índice carregando a árvore limpa do commit base (HEAD)
        index.read_tree(head_commit.tree_id)

        # 2. Faz staging das adições, modificações e remoções estritamente em database/<id_croqui>
        index.add_all([caminho_relativo])
        index.write()

        tree_id = index.write_tree()

        if tree_id == head_commit.tree_id:
            return None

        autor = pygit2.Signature(sessao.nome_completo, sessao.email)
        mensagem_commit = (
            f"edicao({id_croqui}): {titulo}\n\n"
            f"{descricao}\n\n"
            f"Signed-off-by: {sessao.nome_completo} <{sessao.email}>"
        )

        commit_oid = repo.create_commit(
            f"refs/heads/{nome_branch}",
            autor,
            autor,
            mensagem_commit,
            tree_id,
            [head_commit.id],
        )
        return cast(pygit2.Commit, repo[commit_oid])

    def _obter_callbacks_push(
        self, jwt: str, callback_progresso: Callable[[float], None] | None = None
    ) -> pygit2.RemoteCallbacks:
        """Configura credenciais HTTP e callback de progresso para o push."""

        class CallbacksProxy(pygit2.RemoteCallbacks):
            def __init__(self, token_jwt: str, prog_cb: Callable[[float], None] | None) -> None:
                super().__init__()
                self.token_jwt: str = token_jwt
                self.prog_cb: Callable[[float], None] | None = prog_cb
                self._tentativas: int = 0

            def credentials(
                self, url: str, username_from_url: str | None, allowed_types: int
            ) -> Any:
                if self._tentativas >= 3:
                    return None
                self._tentativas += 1
                return pygit2.UserPass("bearer", self.token_jwt)

            def transfer_progress(self, stats: Any) -> None:
                if self.prog_cb and getattr(stats, "total_objects", 0) > 0:
                    percentual = (stats.received_objects / stats.total_objects) * 100
                    self.prog_cb(percentual)

        return CallbacksProxy(jwt, callback_progresso)

    def fazer_push_proxy(
        self,
        repo: pygit2.Repository,
        nome_branch: str,
        jwt: str,
        callback_progresso: Callable[[float], None] | None = None,
    ) -> None:
        """Configura o remote efêmero proxy e realiza o push via Git Smart HTTP."""
        url_proxy = f"{self.url_supabase}/functions/v1/git-proxy"

        try:
            remote = repo.remotes["proxy"]
            repo.remotes.set_url("proxy", url_proxy)
        except (KeyError, ValueError):
            remote = repo.remotes.create("proxy", url_proxy)

        callbacks = self._obter_callbacks_push(jwt, callback_progresso)
        id_croqui_extraido = _extrair_id_croqui_da_branch(nome_branch)
        try:
            remote.push([f"refs/heads/{nome_branch}"], callbacks=callbacks)
        except Exception as e:
            msg = str(e)
            contexto = {"url_proxy": url_proxy, "branch": nome_branch}
            if (
                "too many redirects" in msg.lower()
                or "authentication" in msg.lower()
                or "auth schemes" in msg.lower()
                or "credential does not implement" in msg.lower()
            ):
                capturar_falha_submissao(
                    erro=e,
                    id_croqui=id_croqui_extraido,
                    etapa="push_proxy",
                    categoria="autenticacao",
                    contexto_extra=contexto,
                )
                raise ErroSubmissao(
                    f"Falha na autenticação com o Git Proxy (sessão inválida ou expirada):\n{e}"
                )
            capturar_falha_submissao(
                erro=e,
                id_croqui=id_croqui_extraido,
                etapa="push_proxy",
                categoria="git_proxy",
                contexto_extra=contexto,
            )
            raise ErroSubmissao(f"Falha ao enviar proposta de mudança para o Git Proxy:\n{e}")

    def _executar_push_git(
        self,
        nome_branch: str,
        jwt: str,
        repo: pygit2.Repository,
        callback_progresso: Callable[[float], None] | None = None,
    ) -> None:
        """Método auxiliar encapsulado para o comando de push do Git."""
        self.fazer_push_proxy(repo, nome_branch, jwt, callback_progresso)

    def solicitar_abertura_pr(
        self,
        jwt: str,
        branch: str,
        titulo: str,
        descricao: str,
        token_usuario_github: str | None = None,
        tempo_limite: int | None = None,
    ) -> dict[str, Any]:
        """Dispara a criação/registro da Pull Request via Edge Function create-pr."""
        url_endpoint = f"{self.url_supabase}/functions/v1/create-pr"
        cabecalhos = {
            "Authorization": f"Bearer {jwt}",
            "apikey": self.chave_publica,
            "Content-Type": "application/json",
        }
        payload = {
            "branch": branch,
            "title": titulo,
            "description": descricao,
        }
        if token_usuario_github:
            payload["token_usuario_github"] = token_usuario_github

        id_croqui_extraido = _extrair_id_croqui_da_branch(branch)
        timeout_efetivo = tempo_limite if tempo_limite is not None else self.tempo_limite_requisicao

        try:
            resposta = requests.post(
                url_endpoint, json=payload, headers=cabecalhos, timeout=timeout_efetivo
            )
        except Exception as e:
            contexto = {"url_endpoint": url_endpoint, "branch": branch, "titulo": titulo}
            categoria = (
                "rede"
                if isinstance(e, (requests.ConnectionError, requests.Timeout))
                else "github_api"
            )
            capturar_falha_submissao(
                erro=e,
                id_croqui=id_croqui_extraido,
                etapa="abertura_pr",
                categoria=categoria,
                contexto_extra=contexto,
            )
            raise ErroSubmissao(f"Falha na comunicação com o servidor ao abrir Pull Request:\n{e}")

        if resposta.status_code != 200:
            msg = resposta.text
            arquivos_invalidos = None
            try:
                corpo_json = resposta.json()
                msg = corpo_json.get("erro", msg)
                arquivos_invalidos = corpo_json.get("arquivos_invalidos")
                if isinstance(arquivos_invalidos, list):
                    if len(arquivos_invalidos) > 0:
                        itens = "\n".join(f"• {arq}" for arq in arquivos_invalidos)
                        msg = f"{msg}\n\nArquivos fora do escopo permitidos:\n{itens}"
                    else:
                        msg = f"{msg}\n\n(Nenhum arquivo modificado foi detectado pelo servidor na branch)."
            except Exception:
                pass
            erro_http = ErroSubmissao(
                f"Erro ao formalizar proposta de mudança no GitHub ({resposta.status_code}):\n{msg}"
            )
            contexto_erro: dict[str, Any] = {
                "url_endpoint": url_endpoint,
                "branch": branch,
                "codigo_status_http": resposta.status_code,
                "resposta_servidor": msg,
            }
            if arquivos_invalidos is not None:
                contexto_erro["arquivos_invalidos"] = arquivos_invalidos
            capturar_falha_submissao(
                erro=erro_http,
                id_croqui=id_croqui_extraido,
                etapa="abertura_pr",
                categoria="github_api",
                contexto_extra=contexto_erro,
            )
            raise erro_http

        try:
            dados = resposta.json()
        except Exception as e:
            erro_json = ErroSubmissao(f"Resposta inválida do servidor ao abrir Pull Request:\n{e}")
            contexto_json: dict[str, Any] = {
                "url_endpoint": url_endpoint,
                "branch": branch,
                "resposta_texto": resposta.text,
            }
            capturar_falha_submissao(
                erro=erro_json,
                id_croqui=id_croqui_extraido,
                etapa="abertura_pr",
                categoria="github_api",
                contexto_extra=contexto_json,
            )
            raise erro_json

        pr_number = dados.get("pr_number") or dados.get("numero_pr")
        pr_url = dados.get("pr_url") or dados.get("url_pr")

        return {
            "pr_number": pr_number,
            "pr_url": pr_url,
            "numero_pr": pr_number,
            "url_pr": pr_url,
        }

    def _obter_commit_base(self, repo: pygit2.Repository) -> pygit2.Commit:
        """
        Localiza o commit base para a criação da branch de proposta de mudança.
        Tenta em ordem: upstream/main, origin/main, upstream/master, origin/master, main/master local ou HEAD.
        """
        candidatos = [
            "refs/remotes/upstream/main",
            "refs/remotes/origin/main",
            "refs/remotes/upstream/master",
            "refs/remotes/origin/master",
            "refs/heads/main",
            "refs/heads/master",
        ]
        for ref_nome in candidatos:
            try:
                ref = repo.lookup_reference(ref_nome)
                if ref:
                    return cast(pygit2.Commit, ref.peel())
            except (KeyError, ValueError):
                continue

        if not repo.is_empty and not repo.head_is_unborn:
            try:
                return cast(pygit2.Commit, repo.head.peel())
            except Exception:
                pass

        raise ErroSubmissao("Não foi possível determinar o commit base do repositório.")

    def submeter_sugestao(
        self,
        caminho_database_croqui: Path,
        id_croqui: str,
        titulo: str,
        descricao: str,
        sessao: SessaoUsuario,
        branch_existente: str | None = None,
        callback_progresso: Callable[[int, str], None] | None = None,
    ) -> ResultadoSubmissao:
        """
        Orquestra o fluxo fim-a-fim de submissão:
        1. Validação/Renovação preventiva de sessão
        2. Checkout/Criação de branch local
        3. Cópia de arquivos de database/<id_croqui>/
        4. Commit assinado
        5. Push para o Git Proxy
        6. Abertura ou confirmação de PR
        """

        def reportar(porcentagem: int, mensagem: str) -> None:
            registrar_breadcrumb_submissao(
                mensagem=mensagem,
                categoria="submissao_pr",
                dados={
                    "id_croqui": id_croqui,
                    "porcentagem": porcentagem,
                    "branch": branch_existente or "",
                },
            )
            if callback_progresso:
                callback_progresso(porcentagem, mensagem)

        reportar(10, "Verificando autenticação...")
        jwt_ativo = sessao.jwt_supabase
        try:
            self.cliente_auth.obter_usuario_atual(jwt_ativo)
        except Exception:
            try:
                novos_tokens = self.cliente_auth.renovar_sessao(sessao.token_atualizacao)
                jwt_ativo = novos_tokens["access_token"]
                sessao.jwt_supabase = jwt_ativo
                sessao.token_atualizacao = novos_tokens.get(
                    "refresh_token", sessao.token_atualizacao
                )
            except Exception as e:
                capturar_falha_submissao(
                    erro=e,
                    id_croqui=id_croqui,
                    etapa="verificacao_auth",
                    categoria="autenticacao",
                    contexto_extra={"id_croqui": id_croqui},
                )
                raise ErroSubmissao(
                    f"Sessão expirada. Por favor, salve seu croqui e entre novamente no aplicativo:\n{e}"
                )

        reportar(20, "Preparando repositório e branch...")
        try:
            repo = pygit2.Repository(str(self.caminho_repo_base))

            if branch_existente and (
                branch_existente.startswith("edicao-")
                or branch_existente.startswith("sugestao-")
                or branch_existente.startswith("proposta-")
            ):
                nome_branch = branch_existente
                if nome_branch in repo.branches.local:
                    branch = repo.branches.local[nome_branch]
                else:
                    commit_base = self._obter_commit_base(repo)
                    branch = repo.create_branch(nome_branch, commit_base)
                repo.checkout(branch)
            else:
                nome_branch = gerar_nome_branch(id_croqui)
                commit_base = self._obter_commit_base(repo)
                branch = repo.create_branch(nome_branch, commit_base)
                repo.checkout(branch)
        except ErroSubmissao:
            raise
        except Exception as e:
            capturar_falha_submissao(
                erro=e,
                id_croqui=id_croqui,
                etapa="preparacao_branch",
                categoria="git_local",
                contexto_extra={
                    "id_croqui": id_croqui,
                    "caminho_repo": str(self.caminho_repo_base),
                },
            )
            raise ErroSubmissao(f"Falha ao preparar repositório e branch local:\n{e}")

        reportar(40, "Sincronizando arquivos modificados...")
        self.sincronizar_arquivos_croqui(caminho_database_croqui, self.caminho_repo_base, id_croqui)

        reportar(60, "Gerando commit assinado...")
        try:
            commit = self.criar_commit_sugestao(
                repo=repo,
                nome_branch=nome_branch,
                id_croqui=id_croqui,
                titulo=titulo,
                descricao=descricao,
                sessao=sessao,
            )
        except ErroSubmissao:
            raise
        except Exception as e:
            capturar_falha_submissao(
                erro=e,
                id_croqui=id_croqui,
                etapa="commit_local",
                categoria="git_local",
                contexto_extra={"id_croqui": id_croqui, "nome_branch": nome_branch},
            )
            raise ErroSubmissao(f"Falha ao gerar commit assinado no repositório local:\n{e}")

        if not commit:
            return ResultadoSubmissao(
                sucesso=True,
                nome_branch=nome_branch,
                mensagem="Nenhuma alteração foi detectada no croqui.",
                sem_alteracoes=True,
            )

        reportar(80, "Enviando alterações através do Git Proxy...")
        self._executar_push_git(nome_branch, jwt_ativo, repo)

        reportar(90, "Registrando Pull Request...")
        dados_pr = self.solicitar_abertura_pr(
            jwt=jwt_ativo,
            branch=nome_branch,
            titulo=titulo,
            descricao=descricao,
            token_usuario_github=sessao.token_github,
        )

        reportar(100, "Proposta de mudança enviada com sucesso!")
        return ResultadoSubmissao(
            sucesso=True,
            pr_number=dados_pr.get("pr_number"),
            pr_url=dados_pr.get("pr_url"),
            nome_branch=nome_branch,
            mensagem="Proposta de mudança publicada com sucesso!",
        )

    def verificar_atualizacoes_remotas_pr(
        self,
        id_croqui: str,
        nome_branch: str,
        nome_remote: str = "origin",
        callbacks: pygit2.RemoteCallbacks | None = None,
    ) -> tuple[bool, str | None]:
        """
        Executa fetch da branch remota e compara com a referência local.
        Retorna (tem_atualizacoes, id_commit_remoto).
        """
        repo = pygit2.Repository(str(self.caminho_repo_base))
        try:
            remote = repo.remotes[nome_remote]
        except (KeyError, ValueError):
            raise ErroSubmissao(f"Remote '{nome_remote}' não configurado no repositório base.")

        refspec = f"+refs/heads/{nome_branch}:refs/remotes/{nome_remote}/{nome_branch}"
        try:
            remote.fetch([refspec], callbacks=callbacks)
        except Exception as e:
            raise ErroSubmissao(
                f"Falha ao buscar atualizações remotas para a branch {nome_branch}:\n{e}"
            )

        ref_remota_nome = f"refs/remotes/{nome_remote}/{nome_branch}"
        try:
            ref_remota = repo.lookup_reference(ref_remota_nome)
        except (KeyError, ValueError):
            return False, None

        commit_remoto = ref_remota.peel(pygit2.Commit)
        ref_local_nome = f"refs/heads/{nome_branch}"

        try:
            ref_local = repo.lookup_reference(ref_local_nome)
            commit_local = ref_local.peel(pygit2.Commit)
        except (KeyError, ValueError):
            return True, str(commit_remoto.id)

        if commit_local.id == commit_remoto.id:
            return False, str(commit_remoto.id)

        if repo.descendant_of(commit_local.id, commit_remoto.id):
            return False, str(commit_remoto.id)

        return True, str(commit_remoto.id)

    def sincronizar_pr_remota(
        self,
        id_croqui: str,
        nome_branch: str,
        caminho_database_croqui: Path,
        nome_remote: str = "origin",
        sessao: SessaoUsuario | None = None,
        callbacks: pygit2.RemoteCallbacks | None = None,
    ) -> ResultadoSincronizacao:
        """
        Verifica novidades remotas na branch da PR e aplica mesclagem automática
        (fast-forward ou 3-way merge sem conflitos) na árvore de trabalho local.
        """
        tem_novidades, commit_remoto_sha = self.verificar_atualizacoes_remotas_pr(
            id_croqui=id_croqui,
            nome_branch=nome_branch,
            nome_remote=nome_remote,
            callbacks=callbacks,
        )

        if not tem_novidades:
            return ResultadoSincronizacao(
                status=StatusSincronizacao.ATUALIZADO,
                mensagem="O croqui já está atualizado com a versão remota.",
                commit_merge=commit_remoto_sha,
            )

        repo = pygit2.Repository(str(self.caminho_repo_base))
        ref_remota_nome = f"refs/remotes/{nome_remote}/{nome_branch}"
        commit_remoto = repo.lookup_reference(ref_remota_nome).peel(pygit2.Commit)

        ref_local_nome = f"refs/heads/{nome_branch}"
        caminho_db_repo = self.caminho_repo_base / "database" / id_croqui

        try:
            ref_local = repo.lookup_reference(ref_local_nome)
            commit_local = ref_local.peel(pygit2.Commit)
        except (KeyError, ValueError):
            branch_local = repo.create_branch(nome_branch, commit_remoto)
            repo.checkout(branch_local, strategy=pygit2.enums.CheckoutStrategy.FORCE)
            if caminho_db_repo.is_dir():
                self._espelhar_diretorio(caminho_db_repo, caminho_database_croqui)
            return ResultadoSincronizacao(
                status=StatusSincronizacao.MESCLADO,
                mensagem="Branch remota sincronizada com sucesso.",
                commit_merge=str(commit_remoto.id),
            )

        if repo.descendant_of(commit_remoto.id, commit_local.id):
            ref_local.set_target(commit_remoto.id)
            repo.checkout(ref_local, strategy=pygit2.enums.CheckoutStrategy.FORCE)
            if caminho_db_repo.is_dir():
                self._espelhar_diretorio(caminho_db_repo, caminho_database_croqui)
            return ResultadoSincronizacao(
                status=StatusSincronizacao.MESCLADO,
                mensagem="Atualizações remotas aplicadas com sucesso (fast-forward).",
                commit_merge=str(commit_remoto.id),
            )

        idx = repo.merge_commits(commit_local, commit_remoto, favor=pygit2.enums.MergeFavor.NORMAL)
        if idx.conflicts is not None:
            arquivos_conflito: list[str] = []
            for tupla in idx.conflicts:
                for entry in tupla:
                    if entry is not None and getattr(entry, "path", None):
                        if entry.path not in arquivos_conflito:
                            arquivos_conflito.append(entry.path)
            return ResultadoSincronizacao(
                status=StatusSincronizacao.CONFLITO,
                mensagem="Conflitos detectados entre as alterações locais e remotas.",
                arquivos_conflito=arquivos_conflito,
            )

        tree_merge = idx.write_tree(repo)
        autor = self._obter_autor_assinatura(repo, sessao)
        mensagem_commit = (
            f"merge({id_croqui}): sincronizacao com branch remota {nome_branch}\n\n"
            f"Signed-off-by: {autor.name} <{autor.email}>"
        )
        commit_merge_oid = repo.create_commit(
            f"refs/heads/{nome_branch}",
            autor,
            autor,
            mensagem_commit,
            tree_merge,
            [commit_local.id, commit_remoto.id],
        )
        repo.checkout(f"refs/heads/{nome_branch}", strategy=pygit2.enums.CheckoutStrategy.FORCE)
        if caminho_db_repo.is_dir():
            self._espelhar_diretorio(caminho_db_repo, caminho_database_croqui)
        return ResultadoSincronizacao(
            status=StatusSincronizacao.MESCLADO,
            mensagem="Alterações remotas mescladas com sucesso.",
            commit_merge=str(commit_merge_oid),
        )

    def _obter_autor_assinatura(
        self, repo: pygit2.Repository, sessao: SessaoUsuario | None
    ) -> pygit2.Signature:
        """Obtém a assinatura do autor a partir da sessão ativa ou da configuração local do Git."""
        if sessao and sessao.nome_completo and sessao.email:
            return pygit2.Signature(sessao.nome_completo, sessao.email)

        nome = "Aresta Editor"
        email = "editor@aresta.local"
        try:
            cfg_nome = repo.config["user.name"]
            if cfg_nome:
                nome = str(cfg_nome)
        except (KeyError, ValueError):
            pass
        try:
            cfg_email = repo.config["user.email"]
            if cfg_email:
                email = str(cfg_email)
        except (KeyError, ValueError):
            pass
        return pygit2.Signature(nome, email)

    def resolver_conflito_pr(
        self,
        id_croqui: str,
        nome_branch: str,
        caminho_database_croqui: Path,
        manter_local: bool,
        nome_remote: str = "origin",
        sessao: SessaoUsuario | None = None,
    ) -> ResultadoSincronizacao:
        """
        Resolve conflito de sincronização criando commit de merge com 2 pais,
        escolhendo explicitamente a versão local ou remota (favor=OURS vs THEIRS).
        """
        repo = pygit2.Repository(str(self.caminho_repo_base))
        ref_local = repo.lookup_reference(f"refs/heads/{nome_branch}")
        commit_local = ref_local.peel(pygit2.Commit)

        ref_remota = repo.lookup_reference(f"refs/remotes/{nome_remote}/{nome_branch}")
        commit_remoto = ref_remota.peel(pygit2.Commit)

        favor = pygit2.enums.MergeFavor.OURS if manter_local else pygit2.enums.MergeFavor.THEIRS
        idx = repo.merge_commits(commit_local, commit_remoto, favor=favor)
        tree_merge = idx.write_tree(repo)

        autor = self._obter_autor_assinatura(repo, sessao)
        resolucao = "mantendo versao local" if manter_local else "adotando versao remota"
        mensagem_commit = (
            f"merge({id_croqui}): resolucao de conflito {resolucao}\n\n"
            f"Signed-off-by: {autor.name} <{autor.email}>"
        )
        commit_merge_oid = repo.create_commit(
            f"refs/heads/{nome_branch}",
            autor,
            autor,
            mensagem_commit,
            tree_merge,
            [commit_local.id, commit_remoto.id],
        )
        repo.checkout(f"refs/heads/{nome_branch}", strategy=pygit2.enums.CheckoutStrategy.FORCE)
        caminho_db_repo = self.caminho_repo_base / "database" / id_croqui
        if caminho_db_repo.is_dir():
            self._espelhar_diretorio(caminho_db_repo, caminho_database_croqui)

        return ResultadoSincronizacao(
            status=StatusSincronizacao.MESCLADO,
            mensagem=f"Conflito resolvido ({resolucao}).",
            commit_merge=str(commit_merge_oid),
        )
