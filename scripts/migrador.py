# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import importlib.util
import re
import sys
from pathlib import Path

import yaml

EXPRESSAO_MIGRACAO = re.compile(r"^(\d{4})_.*\.py$")


def _obter_caminho_padrao_migracoes() -> Path:
    """Retorna o caminho padrão de migracoes relativo à raiz do repositório."""
    return Path(__file__).resolve().parent.parent / "migracoes"


def _obter_caminho_repo_base_fallback() -> Path | None:
    """Tenta obter o diretório migracoes a partir do repositório base local sincronizado."""
    try:
        from editor.core.storage import GerenciadorCaminhos

        caminho_base = GerenciadorCaminhos().obter_caminho_base_repo()
        if caminho_base:
            candidato = caminho_base / "migracoes"
            if candidato.is_dir():
                return candidato
    except Exception:
        pass
    return None


def obter_caminho_migracoes() -> Path:
    """
    Retorna o caminho do diretório de migrações de forma resiliente para
    desenvolvimento, aplicativo congelado (PyInstaller) ou fallback de repositório.
    """
    # 1. Se executando congelado com PyInstaller (_MEIPASS)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_migracoes = Path(sys._MEIPASS) / "migracoes"
        if meipass_migracoes.is_dir():
            return meipass_migracoes

    # 2. Caminho padrão local do repositório
    caminho_padrao = _obter_caminho_padrao_migracoes()
    if caminho_padrao.is_dir():
        return caminho_padrao

    # 3. Fallback para repositório base sincronizado localmente
    try:
        caminho_repo = _obter_caminho_repo_base_fallback()
        if caminho_repo is not None:
            return caminho_repo
    except Exception:
        pass

    # 4. Fallback final se nada existir
    return caminho_padrao


def aplicar_migracoes(caminho_croqui: Path) -> None:
    """
    Identifica, ordena e executa de forma sequencial todas as migrações
    pendentes no diretório de croqui especificado.
    """
    caminho_yaml = caminho_croqui / "croqui.yaml"
    if not caminho_yaml.exists():
        return

    # Lê o croqui.yaml como dicionário genérico para evitar quebras de schema do proto
    with open(caminho_yaml, encoding="utf-8") as f:
        dados_croqui = yaml.safe_load(f) or {}

    # Obtém a última migração executada (inteiro, padrão é 0 se não existir)
    ultima_migracao = dados_croqui.get("ultima_migracao", 0)
    if not isinstance(ultima_migracao, int):
        # Fallback de segurança caso estivesse em formato de string ou inválido
        try:
            ultima_migracao = int(ultima_migracao)
        except Exception:
            ultima_migracao = 0

    caminho_migracoes = obter_caminho_migracoes()

    # Varre a pasta de migrações em busca de scripts válidos
    migracoes_disponiveis = []
    if caminho_migracoes.exists():
        for item in caminho_migracoes.iterdir():
            if item.is_file() and item.suffix == ".py" and not item.name.endswith("_test.py"):
                match = EXPRESSAO_MIGRACAO.match(item.name)
                if match:
                    try:
                        versao_migracao = int(match.group(1))
                        if versao_migracao > ultima_migracao:
                            migracoes_disponiveis.append((versao_migracao, item))
                    except Exception:
                        continue

    if not migracoes_disponiveis:
        return

    # Ordena numericamento para garantir a sequência exata de desenvolvimento
    migracoes_disponiveis.sort(key=lambda x: x[0])

    # Executa cada migração pendente
    for versao, caminho_script in migracoes_disponiveis:
        print(f"[{caminho_croqui.name}] Aplicando migração {caminho_script.name}...")

        try:
            # Carrega dinamicamente o módulo Python da migração
            spec = importlib.util.spec_from_file_location("migracao_modulo", str(caminho_script))
            if not spec or not spec.loader:
                continue
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)

            # Executa o ponto de entrada da migração
            if hasattr(modulo, "migrar"):
                modulo.migrar(caminho_croqui)

            # Atualiza o arquivo local no disco com a nova versão
            import ruamel.yaml

            ryaml = ruamel.yaml.YAML()
            ryaml.preserve_quotes = True
            ryaml.width = 90

            with open(caminho_yaml, encoding="utf-8") as f:
                dados_croqui = ryaml.load(f) or {}
            dados_croqui["ultima_migracao"] = versao

            with open(caminho_yaml, "w", encoding="utf-8") as f:
                ryaml.dump(dados_croqui, f)

        except Exception as e:
            print(f"Erro ao aplicar migração {caminho_script.name}: {e}")
            raise


def obter_ultima_versao_migracao() -> int:
    """
    Retorna o número da versão mais alta de migração disponível na pasta migracoes.
    """
    caminho_migracoes = obter_caminho_migracoes()
    max_versao = 0
    if caminho_migracoes.exists():
        for item in caminho_migracoes.iterdir():
            if item.is_file() and item.suffix == ".py" and not item.name.endswith("_test.py"):
                match = EXPRESSAO_MIGRACAO.match(item.name)
                if match:
                    try:
                        versao_migracao = int(match.group(1))
                        if versao_migracao > max_versao:
                            max_versao = versao_migracao
                    except Exception:
                        continue
    return max_versao
