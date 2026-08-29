# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import uuid
import shutil
import filecmp
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, cast

import requests
import pygit2


from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.cliente_auth_supabase import ClienteAuthSupabase
from editor.core.storage import GerenciadorCaminhos


_URL_SUPABASE_PADRAO = os.getenv(
    "ARESTA_SUPABASE_URL", "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"
)
_CHAVE_PUBLICA_PADRAO = os.getenv(
    "ARESTA_SUPABASE_PUBLISHABLE_KEY",
    "sb_publishable_ZOrO8ix2EsWlSHEWrZr42A_JycWrAV3",
)


class ErroSubmissao(Exception):
    """Exceção levantada em falhas no processo de submissão de sugestões."""
    pass


@dataclass
class ResultadoSubmissao:
    """Representa o resultado da operação de submissão de sugestão."""
    sucesso: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    nome_branch: str = ""
    mensagem: str = ""
    sem_alteracoes: bool = False


def gerar_nome_branch(id_croqui: str) -> str:
    """Gera nome único de branch no formato edicao-<id_croqui>-<uuid8>."""
    sufixo_unico = uuid.uuid4().hex[:8]
    return f"edicao-{id_croqui}-{sufixo_unico}"


class ServicoSubmissao:
    """
    Biblioteca pura para empacotamento, commit assinado com pygit2,
    push via Git Proxy e formalização de Pull Requests no Aresta DB.
    """

    def __init__(
        self,
        caminho_repo_base: Optional[Path] = None,
        url_supabase: Optional[str] = None,
        chave_publica: Optional[str] = None,
        cliente_auth: Optional[ClienteAuthSupabase] = None,
    ) -> None:
        self.caminho_repo_base: Path = caminho_repo_base or GerenciadorCaminhos().obter_caminho_base_repo()
        self.url_supabase: str = (url_supabase or _URL_SUPABASE_PADRAO).rstrip("/")
        self.chave_publica: str = chave_publica or _CHAVE_PUBLICA_PADRAO
        self.cliente_auth: ClienteAuthSupabase = cliente_auth or ClienteAuthSupabase(
            url_supabase=self.url_supabase, chave_publica=self.chave_publica
        )


    def sincronizar_arquivos_croqui(
        self, origem: Path, destino_repo: Path, id_croqui: str
    ) -> Path:
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
            if f.is_file() and not f.name.startswith(".") and not any(p.startswith(".") for p in f.relative_to(caminho_database_croqui).parts)
        }

        # 2. Se a base não existe, todos os arquivos locais são novas adições
        if not caminho_base_croqui.is_dir():
            return sorted(list(arquivos_origem.keys()))

        # 3. Arquivos existentes na base oficial
        arquivos_base = {
            f.relative_to(caminho_base_croqui).as_posix(): f
            for f in caminho_base_croqui.rglob("*")
            if f.is_file() and not f.name.startswith(".") and not any(p.startswith(".") for p in f.relative_to(caminho_base_croqui).parts)
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
    ) -> Optional[pygit2.Commit]:
        """
        Realiza staging dos arquivos em database/<id_croqui>/ e cria o commit assinado.
        Retorna o Commit criado ou None se não houver modificações reais na árvore.
        """
        caminho_relativo = f"database/{id_croqui}"
        index = repo.index
        index.add_all([caminho_relativo])
        index.write()

        tree_id = index.write_tree()
        head_commit = cast(pygit2.Commit, repo.head.peel())

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
        self, jwt: str, callback_progresso: Optional[Callable[[float], None]] = None
    ) -> pygit2.RemoteCallbacks:
        """Configura credenciais HTTP e callback de progresso para o push."""
        class CallbacksProxy(pygit2.RemoteCallbacks):
            def __init__(self, token_jwt: str, prog_cb: Optional[Callable[[float], None]]) -> None:
                super().__init__()
                self.token_jwt: str = token_jwt
                self.prog_cb: Optional[Callable[[float], None]] = prog_cb
                self._tentativas: int = 0

            def credentials(self, url: str, username_from_url: str | None, allowed_types: int) -> Any:
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
        callback_progresso: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Configura o remote efêmero proxy e realiza o push via Git Smart HTTP."""
        url_proxy = f"{self.url_supabase}/functions/v1/git-proxy"
        
        try:
            remote = repo.remotes["proxy"]
            repo.remotes.set_url("proxy", url_proxy)
        except (KeyError, ValueError):
            remote = repo.remotes.create("proxy", url_proxy)

        callbacks = self._obter_callbacks_push(jwt, callback_progresso)
        try:
            remote.push([f"refs/heads/{nome_branch}"], callbacks=callbacks)
        except Exception as e:
            msg = str(e)
            if (
                "too many redirects" in msg.lower()
                or "authentication" in msg.lower()
                or "auth schemes" in msg.lower()
                or "credential does not implement" in msg.lower()
            ):
                raise ErroSubmissao(
                    f"Falha na autenticação com o Git Proxy (sessão inválida ou expirada):\n{e}"
                )
            raise ErroSubmissao(f"Falha ao enviar proposta de mudança para o Git Proxy:\n{e}")

    def _executar_push_git(
        self,
        nome_branch: str,
        jwt: str,
        repo: pygit2.Repository,
        callback_progresso: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Método auxiliar encapsulado para o comando de push do Git."""
        self.fazer_push_proxy(repo, nome_branch, jwt, callback_progresso)

    def solicitar_abertura_pr(
        self,
        jwt: str,
        branch: str,
        titulo: str,
        descricao: str,
        token_usuario_github: Optional[str] = None,
    ) -> Dict[str, Any]:
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

        try:
            resposta = requests.post(url_endpoint, json=payload, headers=cabecalhos, timeout=15)
        except Exception as e:
            raise ErroSubmissao(f"Falha na comunicação com o servidor ao abrir Pull Request:\n{e}")

        if resposta.status_code != 200:
            msg = resposta.text
            try:
                msg = resposta.json().get("erro", msg)
            except Exception:
                pass
            raise ErroSubmissao(f"Erro ao formalizar proposta de mudança no GitHub ({resposta.status_code}):\n{msg}")

        try:
            dados = resposta.json()
        except Exception as e:
            raise ErroSubmissao(f"Resposta inválida do servidor ao abrir Pull Request:\n{e}")

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
        branch_existente: Optional[str] = None,
        callback_progresso: Optional[Callable[[int, str], None]] = None,
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
                sessao.token_atualizacao = novos_tokens.get("refresh_token", sessao.token_atualizacao)
            except Exception as e:
                raise ErroSubmissao(
                    f"Sessão expirada. Por favor, salve seu croqui e entre novamente no aplicativo:\n{e}"
                )

        reportar(20, "Preparando repositório e branch...")
        repo = pygit2.Repository(str(self.caminho_repo_base))

        if branch_existente and (branch_existente.startswith("edicao-") or branch_existente.startswith("sugestao-") or branch_existente.startswith("proposta-")):
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

        reportar(40, "Sincronizando arquivos modificados...")
        self.sincronizar_arquivos_croqui(caminho_database_croqui, self.caminho_repo_base, id_croqui)

        reportar(60, "Gerando commit assinado...")
        commit = self.criar_commit_sugestao(
            repo=repo,
            nome_branch=nome_branch,
            id_croqui=id_croqui,
            titulo=titulo,
            descricao=descricao,
            sessao=sessao,
        )

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
