# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from abc import ABC, abstractmethod
from pathlib import Path
import subprocess
import io
import sys
import contextlib
from typing import Protocol

def _filtrar_mensagens(saida_str: str) -> list[str]:
    mensagens = []
    linhas = saida_str.splitlines()
    palavras_chave = ["aviso", "erro", "error", "falhou"]
    
    em_bloco = False
    for linha in linhas:
        linha_low = linha.lower()
        is_keyword = any(p in linha_low for p in palavras_chave)
        
        if is_keyword:
            em_bloco = True
            mensagens.append(linha.rstrip())
        elif em_bloco and (linha.startswith(" ") or linha.startswith("\t")):
            mensagens.append(linha.rstrip())
        elif em_bloco and not linha.strip():
            em_bloco = False
            mensagens.append("")
        else:
            em_bloco = False
            
    while mensagens and not mensagens[-1].strip():
        mensagens.pop()
        
    return mensagens

from collections.abc import Iterator
from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.core.storage import GerenciadorCaminhos
from editor.core.diario import GerenciadorDiario
from scripts.deploy_generated import deploy


@contextlib.contextmanager
def capturar_saida() -> Iterator[io.StringIO]:
    captura = io.StringIO()
    stdout_orig = sys.stdout
    stderr_orig = sys.stderr
    sys.stdout = captura
    sys.stderr = captura
    try:
        yield captura
    finally:
        sys.stdout = stdout_orig
        sys.stderr = stderr_orig


class EditorWorkspace(Protocol):
    caminho_raiz: Path
    diario: GerenciadorDiario | None
    
    def obter_caminho_database(self) -> Path: ...
    def obter_caminho_compilado(self) -> Path: ...
    def obter_pasta_servidor_celular(self) -> Path: ...
    def can_publish_pr(self) -> bool: ...
    def obter_tag_titulo(self) -> str: ...
    def obter_diario(self) -> GerenciadorDiario | None: ...
    def obter_commit_base_sha(self) -> str: ...
    
    def processar_renomeacao_e_compilacao(self, novo_id: str, id_atual: str, storage: GerenciadorCaminhos | None) -> tuple[Path, list[str]]:
        """Realiza rename se necessário, compila e retorna o caminho raiz e uma lista de msgs de warning/erro."""
        ...


class ExperimentalWorkspace:
    """
    Modo padrão operando na pasta `croquis_experimentais/<id>`.
    A estrutura possui `database/` e `compilado/` dentro da raiz.
    O gerenciamento é feito com commits locais pelo GerenciadorCroquiExperimental.
    """
    def __init__(self, caminho_raiz: Path | str) -> None:
        self.caminho_raiz: Path = Path(caminho_raiz)
        self.diario: GerenciadorDiario | None = GerenciadorDiario(self.caminho_raiz)

    def obter_caminho_database(self) -> Path:
        return self.caminho_raiz / "database"

    def obter_caminho_compilado(self) -> Path:
        return self.caminho_raiz / "compilado"

    def obter_pasta_servidor_celular(self) -> Path:
        return self.obter_caminho_compilado()

    def can_publish_pr(self) -> bool:
        return True

    def obter_tag_titulo(self) -> str:
        return ""

    def obter_diario(self) -> GerenciadorDiario | None:
        return self.diario


    def obter_commit_base_sha(self) -> str:
        meta_path = self.caminho_raiz / "metadados.json"
        if meta_path.exists():
            try:
                import json
                with open(meta_path, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    return str(dados.get("commit_base_sha", ""))
            except Exception:
                pass
        return ""


    def processar_renomeacao_e_compilacao(self, novo_id: str, id_atual: str, storage: GerenciadorCaminhos | None) -> tuple[Path, list[str]]:
        gerenciador = GerenciadorCroquiExperimental(storage or GerenciadorCaminhos())
        caminho = self.caminho_raiz
        
        if novo_id and id_atual and novo_id != id_atual:
            caminho = gerenciador.renomear_pasta_croqui(caminho, novo_id)
            self.caminho_raiz = caminho
            from editor.core.diario import GerenciadorDiario
            self.diario = GerenciadorDiario(self.caminho_raiz)
            
        with capturar_saida() as out:
            gerenciador.compilar_croqui(caminho)
            
        mensagens = _filtrar_mensagens(out.getvalue())
        if self.diario:
            self.diario.consolidar_salvamento()
        return caminho, mensagens



class LocalRepoWorkspace:
    """
    Modo operando diretamente no clone do repositório `aresta_db`.
    O `caminho_raiz` é `aresta_db/database/<id>`.
    A saída compilada é `aresta_db/generated/<id>`.
    O rename usa `git mv` nativo.
    """
    def __init__(self, caminho_raiz: Path | str, storage: GerenciadorCaminhos | None = None) -> None:
        self.caminho_raiz: Path = Path(caminho_raiz)
        self.storage: GerenciadorCaminhos | None = storage
        
        # Registra caminho raiz do repo para sanitização de privacidade (<aresta_db>)
        from editor.core.telemetria import registrar_caminho_repo_local
        try:
            raiz_repo = self.caminho_raiz.parent.parent
            registrar_caminho_repo_local(raiz_repo)
        except Exception:
            pass
        from editor.core.storage import GerenciadorCaminhos
        from editor.core.diario import GerenciadorDiario
        gerenciador_caminhos = storage or GerenciadorCaminhos()
        pasta_diario = gerenciador_caminhos.obter_caminho_diarios_locais() / self.caminho_raiz.name
        self.diario: GerenciadorDiario | None = GerenciadorDiario(pasta_diario, apenas_pendente=True)

    def obter_commit_base_sha(self) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.caminho_raiz),
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return ""

    def obter_caminho_database(self) -> Path:
        # A própria raiz já é a pasta do database neste modo
        return self.caminho_raiz

    def obter_caminho_compilado(self) -> Path:
        nome_pasta = self.caminho_raiz.name
        # Caminho sobe database, sobe aresta_db, entra em generated e adiciona a pasta
        return self.caminho_raiz.parent.parent / "generated" / nome_pasta

    def obter_pasta_servidor_celular(self) -> Path:
        # No modo local, o servidor deve servir a raiz da pasta generated para que
        # o indice.binarypb seja encontrado na raiz do servidor
        return self.obter_caminho_compilado().parent

    def can_publish_pr(self) -> bool:
        # O usuário já está em seu repo local. Deve usar o terminal para PR.
        return False

    def obter_tag_titulo(self) -> str:
        return "[Local Mode]"

    def obter_diario(self) -> GerenciadorDiario | None:
        return self.diario

    def processar_renomeacao_e_compilacao(self, novo_id: str, id_atual: str, storage: GerenciadorCaminhos | None) -> tuple[Path, list[str]]:
        caminho = self.caminho_raiz
        
        if novo_id and id_atual and novo_id != id_atual:
            novo_caminho_db = caminho.parent / novo_id
            
            caminho_compilado_atual = self.obter_caminho_compilado()
            novo_caminho_compilado = caminho_compilado_atual.parent / novo_id
            
            try:
                # Renomeia database/<id>
                subprocess.run(["git", "mv", str(caminho), str(novo_caminho_db)], check=True)
                
                # Renomeia generated/<id> se existir
                if caminho_compilado_atual.is_dir():
                    subprocess.run(["git", "mv", str(caminho_compilado_atual), str(novo_caminho_compilado)], check=True)
                    
                caminho = novo_caminho_db
                self.caminho_raiz = caminho
                from editor.core.storage import GerenciadorCaminhos
                from editor.core.diario import GerenciadorDiario
                gerenciador_caminhos = storage or self.storage or GerenciadorCaminhos()
                pasta_diario = gerenciador_caminhos.obter_caminho_diarios_locais() / self.caminho_raiz.name
                self.diario = GerenciadorDiario(pasta_diario, apenas_pendente=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Falha ao renomear as pastas via git: {e}")

        # No modo local, invocamos a compilação local de forma explícita, sem o wrapper que commita
        # is_producao=False gera HTMLs que apontam para imagens e assets locais
        
        caminho_compilado = self.obter_caminho_compilado().parent
        caminho_base = self.obter_caminho_database()
        
        with capturar_saida() as out:
            try:
                deploy(
                    output_dir=caminho_compilado,
                    target_paths=[caminho_base],
                    force_thumbnails=True,
                    gerar_arquivos_de_debug=True,
                    is_producao=False,
                    sair_ao_falhar=False
                )
            except Exception as e:
                print(f"Erro ao compilar croqui: {e}")
                
            # Atualiza a saúde dos croquis
            script_saude = self.caminho_raiz.parent.parent / "scripts" / "medir_saude_croquis.py"
            if script_saude.exists():
                try:
                    subprocess.run([sys.executable, str(script_saude)], check=False)
                except Exception as e:
                    print(f"Erro ao medir saúde dos croquis: {e}")
                
        mensagens = _filtrar_mensagens(out.getvalue())
        if self.diario:
            self.diario.consolidar_salvamento()
        return caminho, mensagens

