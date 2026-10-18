# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path

import scripts.markdown_frontmatter_lib as markdown_frontmatter_lib
from editor.core.serializacao_util import (
    carregar_yaml,
    escrever_texto_se_modificado,
    serializar_yaml,
)

EXPRESSAO_MIGRACAO = re.compile(r"^(\d{4})_.*(?:\.py|\.pyc)$")


def _obter_caminho_padrao_migracoes() -> Path:
    """Retorna o caminho padrão de migracoes relativo à raiz do repositório."""
    return Path(__file__).resolve().parent.parent / "migracoes"


def _obter_caminho_repo_base_fallback(
    provedor_repo_base: Callable[[], Path | None] | None = None,
) -> Path | None:
    """Tenta obter o diretório migracoes a partir do repositório base local sincronizado."""
    try:
        if provedor_repo_base is not None:
            caminho_base = provedor_repo_base()
        else:
            from editor.core.storage import GerenciadorCaminhos

            caminho_base = GerenciadorCaminhos().obter_caminho_base_repo()
        if caminho_base:
            candidato = caminho_base / "migracoes"
            if candidato.is_dir():
                return candidato
    except Exception:
        pass
    return None


def obter_caminho_migracoes(
    *,
    caminho_padrao: Path | None = None,
    provedor_repo_base: Callable[[], Path | None] | None = None,
) -> Path:
    """
    Retorna o caminho do diretório de migrações de forma resiliente para
    desenvolvimento, aplicativo congelado (PyInstaller) ou fallback de repositório.
    """
    # 1. Se executando congelado com PyInstaller
    if getattr(sys, "frozen", False):
        # No macOS (.app bundle): Contents/Resources/migracoes
        if sys.platform == "darwin":
            try:
                caminho_resources = Path(sys.executable).parent.parent / "Resources" / "migracoes"
                if caminho_resources.is_dir():
                    return caminho_resources
            except Exception:
                pass

        # Fallback padrão PyInstaller (_MEIPASS)
        if hasattr(sys, "_MEIPASS"):
            meipass_migracoes = Path(sys._MEIPASS) / "migracoes"
            if meipass_migracoes.is_dir():
                return meipass_migracoes

    # 2. Caminho padrão local do repositório
    padrao = caminho_padrao if caminho_padrao is not None else _obter_caminho_padrao_migracoes()
    if padrao.is_dir():
        return padrao

    # 3. Fallback para repositório base sincronizado localmente
    caminho_repo = _obter_caminho_repo_base_fallback(provedor_repo_base=provedor_repo_base)
    if caminho_repo is not None:
        return caminho_repo

    # 4. Fallback final se nada existir
    return padrao


def aplicar_migracoes(
    caminho_croqui: Path,
    *,
    diretorio_migracoes: Path | None = None,
) -> bool:
    """
    Identifica, ordena e executa de forma sequencial todas as migrações
    pendentes no diretório de croqui especificado.
    Retorna True se ao menos uma migração foi executada, False caso contrário.
    """
    caminho_yaml = caminho_croqui / "croqui.yaml"
    if not caminho_yaml.exists():
        return False

    # Lê o croqui.yaml como dicionário genérico para evitar quebras de schema do proto
    dados_croqui = carregar_yaml(caminho_yaml.read_text(encoding="utf-8")) or {}

    # Obtém a última migração executada (inteiro, padrão é 0 se não existir)
    ultima_migracao = dados_croqui.get("ultima_migracao", 0)
    if not isinstance(ultima_migracao, int):
        # Fallback de segurança caso estivesse em formato de string ou inválido
        try:
            ultima_migracao = int(ultima_migracao)
        except Exception:
            ultima_migracao = 0

    caminho_migracoes = (
        diretorio_migracoes if diretorio_migracoes is not None else obter_caminho_migracoes()
    )

    # Garante compatibilidade caso alguma migração tente importar scripts.finalizar_mapas
    if sys.modules.get("scripts.finalizar_mapas") is None:
        sys.modules["scripts.finalizar_mapas"] = markdown_frontmatter_lib

    # Varre a pasta de migrações em busca de scripts válidos (.py ou .pyc)
    migracoes_por_versao: dict[int, Path] = {}
    if caminho_migracoes.exists():
        for item in sorted(caminho_migracoes.iterdir()):
            if (
                item.is_file()
                and item.suffix in (".py", ".pyc")
                and not item.name.endswith(("_test.py", "_test.pyc"))
            ):
                match = EXPRESSAO_MIGRACAO.match(item.name)
                if match:
                    versao_migracao = int(match.group(1))
                    if versao_migracao > ultima_migracao:
                        # Prioriza arquivo fonte .py se ambos existirem (.py e .pyc)
                        if versao_migracao not in migracoes_por_versao or item.suffix == ".py":
                            migracoes_por_versao[versao_migracao] = item

    if not migracoes_por_versao:
        return False

    migracoes_disponiveis = sorted(migracoes_por_versao.items(), key=lambda x: x[0])

    # Executa cada migração pendente
    for versao, caminho_script in migracoes_disponiveis:
        print(f"[{caminho_croqui.name}] Aplicando migração {caminho_script.name}...")

        try:
            # Carrega dinamicamente o módulo Python da migração
            spec = importlib.util.spec_from_file_location("migracao_modulo", str(caminho_script))
            assert spec and spec.loader
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)

            # Executa o ponto de entrada da migração
            if hasattr(modulo, "migrar"):
                modulo.migrar(caminho_croqui)

            # Atualiza o arquivo local no disco com a nova versão
            dados_croqui = carregar_yaml(caminho_yaml.read_text(encoding="utf-8")) or {}
            dados_croqui["ultima_migracao"] = versao

            escrever_texto_se_modificado(
                caminho_yaml,
                serializar_yaml(dados_croqui, incluir_cabecalho_spdx=True),
            )

        except Exception as e:
            print(f"Erro ao aplicar migração {caminho_script.name}: {e}")
            raise

    return True


def obter_ultima_versao_migracao(
    *,
    diretorio_migracoes: Path | None = None,
) -> int:
    """
    Retorna o número da versão mais alta de migração disponível na pasta migracoes.
    """
    caminho_migracoes = (
        diretorio_migracoes if diretorio_migracoes is not None else obter_caminho_migracoes()
    )
    max_versao = 0
    if caminho_migracoes.exists():
        for item in caminho_migracoes.iterdir():
            if (
                item.is_file()
                and item.suffix in (".py", ".pyc")
                and not item.name.endswith(("_test.py", "_test.pyc"))
            ):
                match = EXPRESSAO_MIGRACAO.match(item.name)
                if match:
                    versao_migracao = int(match.group(1))
                    if versao_migracao > max_versao:
                        max_versao = versao_migracao
    return max_versao
