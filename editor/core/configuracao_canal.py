# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca de configuração e identidade do canal de execução do Editor Aresta.
Permite alternar de forma transparente entre o canal oficial de produção e o
canal de testes Beta com isolamento de recursos, títulos e identificadores do SO.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

CANAL_PRODUCAO: str = "producao"
CANAL_BETA: str = "beta"


def obter_diretorio_base_recursos(diretorio_base: Optional[Path] = None) -> Path:
    """
    Retorna o diretório base para localização de recursos gráficos.
    Lida corretamente com o sys._MEIPASS quando o executável é congelado via PyInstaller.
    """
    if diretorio_base:
        return diretorio_base
    import sys
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ConfiguracaoCanal:
    """Representa a configuração e metadados de identidade de um canal do editor."""

    nome_canal: str
    diretorio_base: Optional[Path] = None

    @property
    def eh_beta(self) -> bool:
        """Indica se a configuração atual corresponde ao canal de testes Beta."""
        return self.nome_canal == CANAL_BETA

    @property
    def nome_aplicativo(self) -> str:
        """Nome de exibição formal da aplicação."""
        if self.eh_beta:
            return "Editor Aresta (Beta)"
        return "Editor Aresta"

    @property
    def app_user_model_id(self) -> str:
        """Identificador de aplicação explícito para a barra de tarefas do Windows."""
        if self.eh_beta:
            return "aresta.editor.beta"
        return "aresta.editor.v1"

    @property
    def subdiretorio_recursos(self) -> str:
        """Nome da pasta de recursos gráficos prioritária para o canal."""
        if self.eh_beta:
            return "recursos_beta"
        return "recursos"

    def titulo_janela(self, versao: Optional[str] = None) -> str:
        """
        Retorna o título formatado para janelas do editor incluindo sufixo
        de canal e versão semântica, se fornecida.
        """
        prefixo = self.nome_aplicativo
        if versao:
            return f"{prefixo} v{versao}"
        return prefixo

    def obter_caminho_recurso(self, nome_recurso: str) -> Path:
        """
        Resolve o caminho absoluto de um recurso gráfico respeitando a pasta prioritária
        do canal e realizando fallback transparente para a pasta padrão de recursos.
        Suporta tanto ambiente de desenvolvimento quanto executável empacotado (PyInstaller sys._MEIPASS).
        """
        base = self.diretorio_base or obter_diretorio_base_recursos()

        candidatos_canal = [
            base / self.subdiretorio_recursos / nome_recurso,
            base / "editor" / self.subdiretorio_recursos / nome_recurso,
        ]
        if self.eh_beta:
            for cand in candidatos_canal:
                if cand.exists():
                    return cand

        candidatos_padrao = [
            base / "recursos" / nome_recurso,
            base / "editor" / "recursos" / nome_recurso,
        ]
        for cand in candidatos_padrao:
            if cand.exists():
                return cand

        return candidatos_canal[0]


def obter_configuracao_canal(
    nome_canal: Optional[str] = None,
    diretorio_base: Optional[Path] = None,
) -> ConfiguracaoCanal:
    """
    Obtém a instância imutável de ConfiguracaoCanal correspondente.
    Prioridade de detecção:
    1. Parâmetro explícito nome_canal
    2. Variável de ambiente ARESTA_CANAL
    3. Arquivo canal.txt embutido no pacote (PyInstaller)
    4. Presença do subdiretório recursos_beta quando empacotado
    5. Padrão: CANAL_PRODUCAO
    """
    import sys

    canal = (nome_canal or os.environ.get("ARESTA_CANAL", "")).strip().lower()

    if not canal:
        base = diretorio_base or obter_diretorio_base_recursos()
        # 1. Tenta ler canal.txt na raiz ou em editor/
        for p in [base / "canal.txt", base / "editor" / "canal.txt"]:
            if p.exists():
                canal = p.read_text(encoding="utf-8").strip().lower()
                break

        # 2. Se empacotado e recursos_beta existir na raiz do bundle
        if not canal and getattr(sys, "frozen", False):
            if (base / "recursos_beta").exists() or (base / "editor" / "recursos_beta").exists():
                canal = CANAL_BETA

    if canal == CANAL_BETA:
        return ConfiguracaoCanal(CANAL_BETA, diretorio_base=diretorio_base)

    return ConfiguracaoCanal(CANAL_PRODUCAO, diretorio_base=diretorio_base)
