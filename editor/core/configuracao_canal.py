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
        """
        base = self.diretorio_base or Path(__file__).resolve().parent.parent
        caminho_canal = base / self.subdiretorio_recursos / nome_recurso

        if self.eh_beta and caminho_canal.exists():
            return caminho_canal

        caminho_padrao = base / "recursos" / nome_recurso
        if caminho_padrao.exists():
            return caminho_padrao

        return caminho_canal


def obter_configuracao_canal(nome_canal: Optional[str] = None) -> ConfiguracaoCanal:
    """
    Obtém a instância imutável de ConfiguracaoCanal correspondente.
    Caso o parâmetro nome_canal seja omitido, consulta a variável de ambiente ARESTA_CANAL.
    """
    canal = (nome_canal or os.environ.get("ARESTA_CANAL", "")).strip().lower()

    if canal == CANAL_BETA:
        return ConfiguracaoCanal(CANAL_BETA)

    return ConfiguracaoCanal(CANAL_PRODUCAO)
