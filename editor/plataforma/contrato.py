# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Contrato abstrato e estruturas de dados para adaptadores de sistema operacional.
Define a interface padronizada que toda implementação de plataforma deve cumprir.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class StatusAtualizacao(Enum):
    """Estado da verificação de novas versões do editor."""

    NAO_APLICAVEL = "nao_aplicavel"
    SEM_ATUALIZACAO = "sem_atualizacao"
    ATUALIZACAO_DISPONIVEL = "atualizacao_disponivel"
    ATUALIZACAO_OBRIGATORIA = "atualizacao_obrigatoria"
    ERRO_CHECAGEM = "erro_checagem"


@dataclass
class ResultadoAtualizacao:
    """Resultado detalhado de uma consulta de atualização da aplicação."""

    status: StatusAtualizacao
    versao_disponivel: str | None = None
    mensagem: str | None = None
    pacotes_atualizacao: list[Any] = field(default_factory=list)

    @property
    def tem_atualizacao(self) -> bool:
        """Retorna True se há atualização disponível ou mandatória."""
        return self.status in (
            StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            StatusAtualizacao.ATUALIZACAO_OBRIGATORIA,
        )

    @property
    def obrigatoria(self) -> bool:
        """Retorna True se a atualização requer instalação imediata."""
        return self.status == StatusAtualizacao.ATUALIZACAO_OBRIGATORIA


@runtime_checkable
class AdaptadorPlataforma(Protocol):
    """Protocolo definindo as operações nativas de integração com o sistema operacional."""

    def configurar_ambiente_plataforma(self) -> None:
        """Configura variáveis de ambiente do subsistema gráfico antes da inicialização do Qt."""
        ...

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        """Garante que a janela sem moldura possua presença na barra de tarefas e alternador."""
        ...

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        """Configura o identificador explícito de aplicação para o shell do sistema operacional."""
        ...

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        """Restaura a janela minimizada e traz para o primeiro plano."""
        ...

    def obter_diretorio_dados_usuario(self) -> Path:
        """Retorna o diretório canônico de dados do editor para o SO ativo."""
        ...

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """Consulta o canal da plataforma por atualizações disponíveis."""
        ...

    def solicitar_instalacao_atualizacao(
        self, resultado: ResultadoAtualizacao | None = None
    ) -> bool:
        """Dispara a instalação da atualização ou abre a página de download do canal."""
        ...

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone preferencial para a plataforma (ex: logo.ico, logo.icns, logo_app.png)."""
        ...

    def configurar_cofre_credenciais(self) -> bool:
        """Configura e valida o backend seguro do chaveiro (Keyring) para a plataforma, retornando True se operacional."""
        ...

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        """
        Normaliza caminhos de sistema operacional com prefixo estendido.
        No Windows, adiciona o prefixo \\?\\ para contornar o limite MAX_PATH de 260 caracteres.
        No Linux e macOS, resolve e retorna o caminho canônico absoluto.
        """
        ...
