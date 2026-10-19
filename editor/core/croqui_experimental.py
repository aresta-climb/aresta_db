# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pygit2
from google.protobuf.json_format import MessageToDict, ParseDict

from aresta_api.proto.generated.croqui_experimental_pb2 import CroquiExperimental
from editor.core.serializacao_util import (
    carregar_yaml,
    escrever_texto_se_modificado,
    serializar_yaml,
)
from editor.core.storage import GerenciadorCaminhos
from scripts.deploy_generated import deploy
from scripts.gerenciar_uids_lib import gerar_uid
from scripts.migrador import obter_ultima_versao_migracao


class GerenciadorCroquiExperimental:
    """
    Gerencia o ciclo de vida dos croquis experimentais no storage local.
    """

    def __init__(self, gerenciador_caminhos: GerenciadorCaminhos) -> None:
        self.caminhos: GerenciadorCaminhos = gerenciador_caminhos

    def _criar_estrutura_croqui(
        self,
        id_croqui: str,
        nome_usuario: str,
        resumo_edicao: str = "",
        id_original: str | None = None,
        commit_base_sha: str = "",
    ) -> Path:
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

        now = datetime.now(UTC)
        meta.data_criacao.FromDatetime(now)
        meta.ultima_edicao.FromDatetime(now)

        dict_meta = MessageToDict(meta, preserving_proto_field_name=True)

        yaml_path = caminho_raiz / "croqui_experimental.yaml"
        escrever_texto_se_modificado(
            yaml_path,
            serializar_yaml(dict_meta, incluir_cabecalho_spdx=False),
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

    def criar_novo_croqui(
        self, id_croqui: str, pico: str, estado: str, nome_usuario: str, log_dialog: Any = None
    ) -> Path:
        """
        Cria um novo croqui a partir de metadados, inicializa o croqui.yaml e realiza o primeiro build.
        """
        commit_base_sha = self._obter_commit_base_sha()
        # 1. Cria a estrutura base de pastas e metadados
        caminho_raiz = self._criar_estrutura_croqui(
            id_croqui,
            nome_usuario,
            "Inicialização automática",
            id_croqui,
            commit_base_sha=commit_base_sha,
        )

        # 2. Cria o arquivo database/croqui.yaml seguindo a estrutura do proto
        croqui_data = {
            "id": id_croqui,
            "uid": gerar_uid(),
            "nome": pico,
            "ultima_migracao": obter_ultima_versao_migracao(),
            "picos": [{"nome": pico, "estado": estado}],
        }

        caminho_database = caminho_raiz / "database"
        yaml_path = caminho_database / "croqui.yaml"

        escrever_texto_se_modificado(
            yaml_path,
            serializar_yaml(croqui_data, incluir_cabecalho_spdx=True),
        )

        # 3. Executa a compilação inicial para garantir ambiente funcional
        if log_dialog:
            log_dialog.adicionar_log(f"Inicializando compilação de setup para '{id_croqui}'...")

        self.compilar_croqui(caminho_raiz)

        return caminho_raiz

    def criar_croqui_a_partir_de_oficial(
        self, id_oficial: str, nome_usuario: str, resumo_edicao: str = ""
    ) -> Path:
        """
        Cria um croqui experimental a partir de um croqui oficial, copiando os arquivos.
        """
        commit_base_sha = self._obter_commit_base_sha()
        # 1. Inicializa o croqui experimental (cria pastas e metadados)
        caminho_experimental = self._criar_estrutura_croqui(
            id_oficial, nome_usuario, resumo_edicao, id_oficial, commit_base_sha=commit_base_sha
        )

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

            # 4. Compila o croqui localmente para gerar a pasta compilado
            self.compilar_croqui(caminho_experimental)

            return caminho_experimental
        except Exception as e:
            # Se falhar em qualquer ponto da importação/compilação, removemos a pasta incompleta
            self.excluir_croqui(caminho_experimental)
            raise e

    def abrir_croqui(self, caminho_raiz: Path, nome_usuario: str) -> None:
        """
        Abre um croqui experimental, atualizando a lista de autores se necessário
        e a data da última edição.
        """
        yaml_path = caminho_raiz / "croqui_experimental.yaml"
        if not yaml_path.is_file():
            return

        dados = carregar_yaml(yaml_path.read_text(encoding="utf-8")) or {}

        meta = CroquiExperimental()
        ParseDict(dados, meta, ignore_unknown_fields=True)

        if nome_usuario not in meta.autores:
            meta.autores.append(nome_usuario)

        meta.ultima_edicao.FromDatetime(datetime.now(UTC))

        dict_meta = MessageToDict(meta, preserving_proto_field_name=True)
        escrever_texto_se_modificado(
            yaml_path,
            serializar_yaml(dict_meta, incluir_cabecalho_spdx=False),
        )

    def compilar_croqui(self, caminho_raiz: Path) -> bool:
        """
        Compila o croqui experimental usando o script de deploy oficial.
        """

        caminho_database = caminho_raiz / "database"
        caminho_compilado = caminho_raiz / "compilado"

        # Garante que a pasta compilado exista
        caminho_compilado.mkdir(parents=True, exist_ok=True)

        try:
            # Limpa eventual repositório .git local legado para liberar espaço e evitar overhead
            self.excluir_croqui(caminho_raiz / ".git")

            pb_compactado = caminho_compilado / "compilado.binarypb"
            if pb_compactado.is_file():
                from aresta_api.proto.generated import croqui_pb2

                croqui_anterior = croqui_pb2.Croqui()
                croqui_anterior.ParseFromString(pb_compactado.read_bytes())
                pasta_previa = caminho_compilado / croqui_anterior.id
                pasta_previa.mkdir(parents=True, exist_ok=True)
                for nome_artefato in ("compilado.binarypb", "compilado.yaml", "imagens", "anexos"):
                    origem_artefato = caminho_compilado / nome_artefato
                    if origem_artefato.exists():
                        shutil.move(str(origem_artefato), str(pasta_previa / nome_artefato))

            database_modificado = deploy(
                output_dir=caminho_compilado,
                target_paths=[str(caminho_database)],
                force_thumbnails=False,
                is_producao=False,
                sair_ao_falhar=False,
            )

            # Compacta a saída movendo os artefatos de compilado/<croqui_id>/* diretamente para compilado/
            # eliminando o aninhamento redundante de pasta e economizando caracteres de caminho no Windows
            pastas_para_compactar = [
                d
                for d in caminho_compilado.iterdir()
                if d.is_dir()
                and d.name not in ("imagens", "anexos", "thumbnails")
                and (d / "compilado.binarypb").is_file()
            ]
            for pasta_croqui in pastas_para_compactar:
                for sub_item in list(pasta_croqui.iterdir()):
                    destino = caminho_compilado / sub_item.name
                    shutil.move(str(sub_item), str(destino))
                shutil.rmtree(pasta_croqui, ignore_errors=True)

            return bool(database_modificado)
        except Exception as e:
            # Re-lança como RuntimeError para ser capturado pela UI
            raise RuntimeError(f"Erro durante a compilação do croqui: {e!s}")

    def excluir_croqui(self, caminho_raiz: Path) -> None:
        """
        Exclui permanentemente um croqui experimental do disco.
        """
        if caminho_raiz.is_dir():

            def remover_somente_leitura(func: Any, path: str, _: Any) -> None:
                # Limpa o atributo somente-leitura e tenta novamente
                # Comum no Windows dentro de pastas .git/objects
                Path(path).chmod(0o777)
                func(path)

            shutil.rmtree(caminho_raiz, onerror=remover_somente_leitura)

    def renomear_pasta_croqui(self, caminho_raiz: Path, novo_id: str) -> Path:
        """
        Atualiza o diretório de compilação quando o ID do croqui muda,
        pois a pasta raiz agora é opaca (UUID) e não precisa ser renomeada fisicamente.
        Retorna o mesmo Path raiz.
        """
        # Limpeza do compilado antigo para não gerar duplicação local.
        # Ao apenas apagar a pasta compilado, forçamos a recompilação limpa na próxima vez.
        caminho_compilado = caminho_raiz / "compilado"
        if caminho_compilado.is_dir():
            shutil.rmtree(caminho_compilado, ignore_errors=True)

        return caminho_raiz
