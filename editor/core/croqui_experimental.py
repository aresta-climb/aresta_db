# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import sys
from pathlib import Path
import shutil
import os
import zipfile
import pygit2
import yaml
import uuid
from datetime import datetime
from google.protobuf.json_format import MessageToDict

from editor.core.storage import GerenciadorCaminhos
from editor.core.croqui_format import empacotar_croqui, ler_croqui
from aresta_api.proto.generated.croqui_experimental_pb2 import CroquiExperimental

# Adiciona a raiz do projeto ao sys.path para encontrar o módulo 'scripts'
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scripts.deploy_generated import deploy
from scripts.migrador import obter_ultima_versao_migracao

class GerenciadorCroquiExperimental:
    """
    Gerencia o ciclo de vida dos croquis experimentais no storage local.
    """
    
    def __init__(self, gerenciador_caminhos: GerenciadorCaminhos):
        self.caminhos = gerenciador_caminhos
        
    def _criar_estrutura_croqui(self, id_croqui: str, nome_usuario: str, resumo_edicao: str = "", id_original: str = None, commit_base_sha: str = "") -> Path:
        """
        Cria uma nova estrutura de pastas para um croqui experimental (privado).
        """
        nome_pasta = uuid.uuid4().hex[:8]
        caminho_raiz = self.caminhos.obter_caminho_croquis_experimentais() / nome_pasta
        
        # Criar pastas básicas
        caminho_raiz.mkdir(parents=True, exist_ok=False)
        (caminho_raiz / "database").mkdir()
        (caminho_raiz / "compilado").mkdir()
        
        # Salvar metadados
        meta = CroquiExperimental()
        meta.autores.append(nome_usuario)
        meta.resumo_edicao = resumo_edicao
        if id_original:
            meta.id_original = id_original
        if commit_base_sha:
            meta.commit_base_sha = commit_base_sha
            
        from datetime import timezone
        now = datetime.now(timezone.utc)
        meta.data_criacao.FromDatetime(now)
        meta.ultima_edicao.FromDatetime(now)
        
        dict_meta = MessageToDict(meta, preserving_proto_field_name=True)
        
        yaml_path = caminho_raiz / "croqui_experimental.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(dict_meta, f, allow_unicode=True, sort_keys=False)
            
        # Inicializar repositório Git local
        # O repositório será criado na raiz do croqui experimental
        repo = pygit2.init_repository(str(caminho_raiz), False)
        
        # Criar um commit inicial vazio ou com os arquivos base para o git existir?
        # Apenas criar os arquivos de metadados e commitar
        index = repo.index
        index.add("croqui_experimental.yaml")
        index.write()
        
        tree = index.write_tree()
        
        # Assinatura (usando autor generico já que é só local)
        autor = pygit2.Signature("Editor Aresta", "editor@aresta.local")
        
        repo.create_commit(
            "HEAD", # nome da referência a ser atualizada
            autor,
            autor,
            f"Commit inicial do croqui experimental\n\nSigned-off-by: {autor.name} <{autor.email}>",
            tree,
            [] # Sem parents para o primeiro commit
        )
        
        return caminho_raiz

    def _obter_commit_base_sha(self) -> str:
        """Retorna o hash SHA do HEAD do repositório base local se existir."""
        try:
            caminho_repo = self.caminhos.obter_caminho_base_repo()
            if caminho_repo.exists():
                repo = pygit2.Repository(str(caminho_repo))
                if not repo.head_is_unborn:
                    return str(repo.head.target)
        except Exception:
            pass
        return ""

    def criar_novo_croqui(self, id_croqui: str, pico: str, estado: str, nome_usuario: str, log_dialog=None) -> Path:
        """
        Cria um novo croqui a partir de metadados, inicializa o croqui.yaml e realiza o primeiro build.
        """
        commit_base_sha = self._obter_commit_base_sha()
        # 1. Cria a estrutura base (pastas e git inicial)
        caminho_raiz = self._criar_estrutura_croqui(id_croqui, nome_usuario, "Inicialização automática", id_croqui, commit_base_sha=commit_base_sha)
        
        try:
            # 2. Cria o arquivo database/croqui.yaml seguindo a estrutura do proto
            croqui_data = {
                "id": id_croqui,
                "nome": pico,
                "ultima_migracao": obter_ultima_versao_migracao(),
                "picos": [
                    {
                        "nome": pico,
                        "estado": estado
                    }
                ]
            }
            
            caminho_database = caminho_raiz / "database"
            yaml_path = caminho_database / "croqui.yaml"
            
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(croqui_data, f, allow_unicode=True, sort_keys=False)
                
            # 3. Executa a compilação inicial para garantir ambiente funcional
            if log_dialog:
                log_dialog.adicionar_log(f"Inicializando compilação de setup para '{id_croqui}'...")
            
            self.compilar_croqui(caminho_raiz)
            
            # 4. Commit com os arquivos criados e compilados
            repo = pygit2.Repository(str(caminho_raiz))
            index = repo.index
            index.add_all(["database"])
            if (caminho_raiz / "compilado").exists():
                index.add_all(["compilado"])
            index.write()
            
            tree = index.write_tree()
            autor = pygit2.Signature("Editor Aresta", "editor@aresta.local")
            head = repo.head.target
            repo.create_commit(
                "HEAD",
                autor,
                autor,
                f"Setup inicial: criação do croqui.yaml e compilação de sucesso\n\nSigned-off-by: {autor.name} <{autor.email}>",
                tree,
                [head]
            )
            
            return caminho_raiz
        except Exception as e:
            # Em caso de falha, limpa a pasta para não deixar lixo no storage
            self.excluir_croqui(caminho_raiz)
            raise e

    def criar_croqui_a_partir_de_oficial(self, id_oficial: str, nome_usuario: str, resumo_edicao: str = "") -> Path:

        """
        Cria um croqui experimental a partir de um croqui oficial, copiando os arquivos.
        """
        commit_base_sha = self._obter_commit_base_sha()
        # 1. Inicializa o croqui experimental (cria pastas e git inicial)
        caminho_experimental = self._criar_estrutura_croqui(id_oficial, nome_usuario, resumo_edicao, id_oficial, commit_base_sha=commit_base_sha)
        
        try:
            # 2. Localiza o croqui oficial no repo sincronizado
            caminho_repo = self.caminhos.obter_caminho_base_repo()
            caminho_oficial = caminho_repo / "database" / id_oficial
            
            if not caminho_oficial.is_dir():
                raise FileNotFoundError(f"Croqui oficial não encontrado em: {caminho_oficial}")
                
            # 3. Copia os arquivos oficiais para a pasta database do experimental
            caminho_destino_database = caminho_experimental / "database"
            
            for item in caminho_oficial.iterdir():
                if item.is_dir():
                    shutil.copytree(item, caminho_destino_database / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, caminho_destino_database / item.name)
                    
            # 3.2. Compila o croqui localmente para gerar a pasta compilado
            self.compilar_croqui(caminho_experimental)
                    
            # 4. Realiza o commit com os arquivos importados
            repo = pygit2.Repository(str(caminho_experimental))
            index = repo.index
            # Adiciona recursivamente os arquivos da pasta database e compilado
            index.add_all(["database"])
            if (caminho_experimental / "compilado").exists():
                index.add_all(["compilado"])
            index.write()
            
            tree = index.write_tree()
            autor = pygit2.Signature("Editor Aresta", "editor@aresta.local")
            
            # O criar_croqui já criou o primeiro commit. 
            # Este será o segundo commit (Importação).
            head = repo.head.target
            repo.create_commit(
                "HEAD",
                autor,
                autor,
                f"Importação do croqui oficial: {id_oficial}\n\nSigned-off-by: {autor.name} <{autor.email}>",
                tree,
                [head]
            )
            
            return caminho_experimental
        except Exception as e:
            # Se falhar em qualquer ponto da importação/compilação, removemos a pasta incompleta
            self.excluir_croqui(caminho_experimental)
            raise e

    def abrir_croqui(self, caminho_raiz: Path, nome_usuario: str):
        """
        Abre um croqui experimental, atualizando a lista de autores se necessário
        e a data da última edição.
        """
        yaml_path = caminho_raiz / "croqui_experimental.yaml"
        if not yaml_path.is_file():
            return
            
        from google.protobuf.json_format import ParseDict, MessageToDict
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f) or {}
            
        meta = CroquiExperimental()
        ParseDict(dados, meta, ignore_unknown_fields=True)
        
        if nome_usuario not in meta.autores:
            meta.autores.append(nome_usuario)
            
        from datetime import timezone
        meta.ultima_edicao.FromDatetime(datetime.now(timezone.utc))
        
        dict_meta = MessageToDict(meta, preserving_proto_field_name=True)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(dict_meta, f, allow_unicode=True, sort_keys=False)

    def compilar_croqui(self, caminho_raiz: Path):
        """
        Compila o croqui experimental usando o script de deploy oficial.
        """
        
        caminho_database = caminho_raiz / "database"
        caminho_compilado = caminho_raiz / "compilado"
        
        # Garante que a pasta compilado exista
        caminho_compilado.mkdir(parents=True, exist_ok=True)
        
        # Executa o deploy localmente
        # deploy(url_base=None, output_dir=<pasta compilado>, target_path=<pasta database>, force_thumbnails=True)
        try:
            # Garante que o diretório é um repositório Git (necessário para o histórico local)
            if not (caminho_raiz / ".git").is_dir():
                repo = pygit2.init_repository(str(caminho_raiz))
                # Cria um commit inicial vazio para ter uma base
                index = repo.index
                index.write()
                tree = index.write_tree()
                autor = pygit2.Signature("Editor Aresta", "editor@aresta.local")
                repo.create_commit("HEAD", autor, autor, f"Inicialização automática após importação\n\nSigned-off-by: {autor.name} <{autor.email}>", tree, [])
            else:
                repo = pygit2.Repository(str(caminho_raiz))
            
            deploy(
                output_dir=caminho_compilado,
                target_paths=[caminho_database],
                force_thumbnails=True,
                gerar_arquivos_de_debug=True,
                is_producao=False
            )
            
            # Commit no Git local
            index = repo.index
            # Adiciona a pasta compilado inteira ao index
            index.add_all(["compilado"])
            index.write()
            
            tree = index.write_tree()
            autor = pygit2.Signature("Editor Aresta", "editor@aresta.local")
            
            # Pega o head atual para ser o pai do novo commit
            head = repo.head.target
            repo.create_commit(
                "HEAD",
                autor,
                autor,
                f"Compilação do croqui experimental\n\nSigned-off-by: {autor.name} <{autor.email}>",
                tree,
                [head]
            )
            
            # Força liberação de handles no Windows
            del repo
        except Exception as e:
            # Re-lança como RuntimeError para ser capturado pela UI
            raise RuntimeError(f"Erro durante a compilação do croqui: {str(e)}")

    def excluir_croqui(self, caminho_raiz: Path):
        """
        Exclui permanentemente um croqui experimental do disco.
        """
        if caminho_raiz.is_dir():
            import time
            def remover_somente_leitura(func, path, _):
                # Limpa o atributo somente-leitura e tenta novamente
                # Comum no Windows dentro de pastas .git/objects
                os.chmod(path, 0o777)
                func(path)
            
            # No Windows, processos como antivírus ou indexadores podem travar pastas
            # temporariamente. Tentamos algumas vezes antes de desistir.
            for i in range(5):
                try:
                    shutil.rmtree(caminho_raiz, onerror=remover_somente_leitura)
                    return
                except PermissionError:
                    if i == 4:
                        raise
                    time.sleep(0.2)


    def exportar_croqui(self, caminho_raiz: Path, caminho_destino: Path):
        """
        Exporta o croqui experimental compactando toda a pasta num arquivo zip ofuscado (extensão .croqui).
        """
        if not caminho_raiz.is_dir():
            raise FileNotFoundError(f"A pasta do croqui não foi encontrada: {caminho_raiz}")
            
        empacotar_croqui(caminho_raiz, caminho_destino)

    def importar_croqui(self, caminho_arquivo_croqui: Path) -> Path:
        """
        Importa um arquivo .croqui descompactando para a pasta croquis_experimentais.
        """
        caminho_arquivo_croqui = Path(caminho_arquivo_croqui)
        if not caminho_arquivo_croqui.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo_croqui}")
            
        if caminho_arquivo_croqui.suffix.lower() not in [".croqui", ".zip"]:
            raise ValueError("O editor aceita apenas arquivos com as extensões .croqui ou .zip para importação.")
            
        pasta_dest = self.caminhos.obter_caminho_croquis_experimentais()
        
        nome_pasta_extraida = uuid.uuid4().hex[:8]
        caminho_extracao = pasta_dest / nome_pasta_extraida
        
        caminho_extracao.mkdir(parents=True, exist_ok=False)
        
        try:
            ler_croqui(caminho_arquivo_croqui, caminho_extracao)
                
            # Normalização: se extraiu apenas uma pasta raiz, move o conteúdo para cima
            import shutil
            conteudo = list(caminho_extracao.iterdir())
            if len(conteudo) == 1 and conteudo[0].is_dir() and (conteudo[0] / "database").is_dir():
                pasta_raiz = conteudo[0]
                for item in pasta_raiz.iterdir():
                    # No Windows, shutil.move pode falhar se o destino já existir ou por locks
                    # Mas aqui o destino (caminho_extracao) deve estar limpo
                    shutil.move(str(item), str(caminho_extracao / item.name))
                pasta_raiz.rmdir()

            # Pequena pausa para o Windows liberar os arquivos recém-extraídos
            import time
            time.sleep(0.1)
                
            # Opcional: Ler o croqui.yaml dentro de database/
            yaml_path = caminho_extracao / "database" / "croqui.yaml"
            real_id = None
            if yaml_path.is_file():
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        dados = yaml.safe_load(f)
                        real_id = dados.get("id")
                except Exception:
                    pass

            # Como a pasta é UUID, não precisamos renomear baseando no real_id.
            # Basta compilar na pasta de extração.
            self.compilar_croqui(caminho_extracao)
            return caminho_extracao
        except Exception as e:
            # Remove a pasta de extração (ou a nova pasta se já tiver renomeado) em caso de falha
            self.excluir_croqui(caminho_extracao)
            raise e

    def renomear_pasta_croqui(self, caminho_raiz: Path, novo_id: str) -> Path:
        """
        Atualiza o diretório de compilação quando o ID do croqui muda, 
        pois a pasta raiz agora é opaca (UUID) e não precisa ser renomeada fisicamente.
        Retorna o mesmo Path raiz.
        """
        if not self.caminhos:
            return caminho_raiz  # Sem storage, não faz nada
            
        # Limpeza do compilado antigo para não gerar duplicação local.
        # Ao apenas apagar a pasta compilado, forçamos a recompilação limpa na próxima vez.
        caminho_compilado = caminho_raiz / "compilado"
        if caminho_compilado.is_dir():
            shutil.rmtree(caminho_compilado, ignore_errors=True)
                
        return caminho_raiz
