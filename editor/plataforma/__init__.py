# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca de integração nativa e abstração de plataforma do Editor Aresta.
Fornece uma fachada agnóstica para serviços específicos do sistema operacional (Windows, Linux, macOS).
"""

import sys
from pathlib import Path
from typing import Optional
from editor.plataforma.contrato import (
    AdaptadorPlataforma,
    StatusAtualizacao,
    ResultadoAtualizacao,
)

__all__ = [
    "AdaptadorPlataforma",
    "StatusAtualizacao",
    "ResultadoAtualizacao",
    "obter_adaptador_plataforma",
    "configurar_ambiente_plataforma",
    "configurar_presenca_barra_de_tarefas",
    "configurar_identidade_processo",
    "trazer_janela_para_frente",
    "obter_diretorio_dados_usuario",
    "verificar_atualizacoes_disponiveis",
    "solicitar_instalacao_atualizacao",
    "obter_nome_icone_preferencial",
    "configurar_cofre_credenciais",
    "normalizar_caminho_estendido",
]


class _AdaptadorPadraoFallback:
    """Adaptador padrão neutro para ambientes de testes ou plataformas genéricas."""

    def configurar_ambiente_plataforma(self) -> None:
        pass

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        return True

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        return True

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        return True

    def obter_diretorio_dados_usuario(self) -> Path:
        return Path.home() / ".local" / "share" / "EditorAresta"

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        return ResultadoAtualizacao(status=StatusAtualizacao.NAO_APLICAVEL)

    def solicitar_instalacao_atualizacao(
        self, resultado: Optional[ResultadoAtualizacao] = None
    ) -> bool:
        return False

    def obter_nome_icone_preferencial(self) -> str:
        return "logo_app.png"

    def configurar_cofre_credenciais(self) -> bool:
        return False

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        if not caminho:
            return ""
        return str(Path(caminho).resolve())


_ADAPTADORES_POR_PLATAFORMA: dict[str, AdaptadorPlataforma] = {}


def obter_adaptador_plataforma() -> AdaptadorPlataforma:
    """
    Retorna o adaptador concreto correspondente ao sistema operacional em execução.
    Carrega sob demanda o módulo correspondente preservando o arranque rápido.
    """
    plataforma = sys.platform
    if plataforma.startswith("win"):
        chave = "win32"
    elif plataforma.startswith("linux"):
        chave = "linux"
    elif plataforma == "darwin":
        chave = "darwin"
    else:
        chave = "padrao"

    if chave in _ADAPTADORES_POR_PLATAFORMA:
        return _ADAPTADORES_POR_PLATAFORMA[chave]

    adaptador: AdaptadorPlataforma
    if chave == "win32":
        try:
            from editor.plataforma.windows.integracao import AdaptadorWindows

            adaptador = AdaptadorWindows()
        except ImportError:
            adaptador = _AdaptadorPadraoFallback()
    elif chave == "linux":
        try:
            from editor.plataforma.linux.integracao import AdaptadorLinux

            adaptador = AdaptadorLinux()
        except ImportError:
            adaptador = _AdaptadorPadraoFallback()
    elif chave == "darwin":
        try:
            from editor.plataforma.macos.integracao import AdaptadorMacOS

            adaptador = AdaptadorMacOS()
        except ImportError:
            adaptador = _AdaptadorPadraoFallback()
    else:
        adaptador = _AdaptadorPadraoFallback()

    _ADAPTADORES_POR_PLATAFORMA[chave] = adaptador
    return adaptador


def configurar_ambiente_plataforma() -> None:
    """Configura o ambiente do subsistema gráfico antes da criação da aplicação Qt."""
    obter_adaptador_plataforma().configurar_ambiente_plataforma()


def configurar_presenca_barra_de_tarefas(identificador_janela: int) -> bool:
    """Qualifica janelas sem bordas na barra de tarefas e alternador de janelas."""
    return obter_adaptador_plataforma().configurar_presenca_barra_de_tarefas(identificador_janela)


def configurar_identidade_processo(identificador_app: str) -> bool:
    """Configura o identificador explícito do processo para o sistema operacional."""
    return obter_adaptador_plataforma().configurar_identidade_processo(identificador_app)


def trazer_janela_para_frente(identificador_janela: int) -> bool:
    """Traz uma janela para o primeiro plano da área de trabalho."""
    return obter_adaptador_plataforma().trazer_janela_para_frente(identificador_janela)


def obter_diretorio_dados_usuario() -> Path:
    """Retorna o caminho canônico do diretório de dados do usuário."""
    return obter_adaptador_plataforma().obter_diretorio_dados_usuario()


def verificar_atualizacoes_disponiveis() -> ResultadoAtualizacao:
    """Consulta o canal da plataforma por atualizações disponíveis."""
    return obter_adaptador_plataforma().verificar_atualizacoes_disponiveis()


def solicitar_instalacao_atualizacao(resultado: Optional[ResultadoAtualizacao] = None) -> bool:
    """Dispara a instalação da atualização disponível."""
    return obter_adaptador_plataforma().solicitar_instalacao_atualizacao(resultado)


def obter_nome_icone_preferencial() -> str:
    """Retorna o nome do arquivo de ícone nativo prioritário para o sistema operacional corrente."""
    return obter_adaptador_plataforma().obter_nome_icone_preferencial()


def configurar_cofre_credenciais() -> bool:
    """Configura o backend seguro do cofre de credenciais delegando ao adaptador ativo."""
    return bool(obter_adaptador_plataforma().configurar_cofre_credenciais())


def normalizar_caminho_estendido(caminho: Path | str) -> str:
    """Normaliza o caminho estendido para manipulação resiliente no sistema operacional ativo."""
    return obter_adaptador_plataforma().normalizar_caminho_estendido(caminho)
