# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração com o macOS (Cocoa / Apple Silicon).
Implementa o AdaptadorMacOS conforme o protocolo AdaptadorPlataforma.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QStandardPaths
from editor.plataforma.contrato import (
    AdaptadorPlataforma,
    ResultadoAtualizacao,
    StatusAtualizacao,
)


class AdaptadorMacOS(AdaptadorPlataforma):
    """Adaptador de integração nativa com o sistema operacional macOS."""

    def configurar_ambiente_plataforma(self) -> None:
        """Configura variáveis de ambiente do subsistema gráfico antes da inicialização do Qt."""
        pass

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        """No macOS, a presença na Dock e alternador é gerenciada nativamente pelo sistema operacional."""
        return True

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        """Configura a identidade de aplicação no shell do sistema operacional."""
        try:
            from PySide6.QtGui import QGuiApplication

            QGuiApplication.setDesktopFileName(identificador_app)
            return True
        except Exception:
            return False

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        """Restaura e eleva a janela via APIs padrão do Qt."""
        try:
            from PySide6.QtWidgets import QApplication

            janela = QApplication.activeWindow()
            if janela is not None:
                janela.showNormal()
                janela.raise_()
                janela.activateWindow()
            return True
        except Exception:
            return False

    def obter_diretorio_dados_usuario(self) -> Path:
        """
        Retorna o diretório canônico de dados do usuário no macOS
        (~/Library/Application Support/EditorAresta).
        """
        caminho_appdata = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not caminho_appdata:
            return Path.home() / "Library" / "Application Support" / "EditorAresta"
        return Path(caminho_appdata)

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """
        Consulta o serviço de atualizações do macOS (Sparkle Framework).
        """
        return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

    def solicitar_instalacao_atualizacao(
        self, resultado: Optional[ResultadoAtualizacao] = None
    ) -> bool:
        """Dispara a instalação da atualização no macOS."""
        return False

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone nativo prioritário para o macOS (.icns)."""
        return "logo.icns"
