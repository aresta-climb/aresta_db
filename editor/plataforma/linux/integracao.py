# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração com o ambiente de desktop Linux (XDG e Flatpak).
Implementa o AdaptadorLinux conforme o protocolo AdaptadorPlataforma.
"""

import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("aresta_editor")
from editor.plataforma.contrato import (
    AdaptadorPlataforma,
    ResultadoAtualizacao,
    StatusAtualizacao,
)


class AdaptadorLinux(AdaptadorPlataforma):
    """Adaptador de integração nativa com o sistema operacional Linux."""

    def configurar_ambiente_plataforma(self) -> None:
        """Configura variáveis de ambiente do subsistema gráfico antes da inicialização do Qt."""
        # Suprime avisos e erros diagnósticos não-críticos de parse de keysyms (ex: dead_hamza) no libxkbcommon
        os.environ.setdefault("XKB_LOG_LEVEL", "critical")

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        """No Linux, a barra de tarefas é gerida nativamente pelo compositor/WM."""
        return True

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        """Configura o nome do arquivo desktop no QGuiApplication para o shell Linux."""
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
        """Retorna o diretório canônico XDG ($XDG_DATA_HOME/EditorAresta ou ~/.local/share/EditorAresta)."""
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            return Path(xdg_data) / "EditorAresta"
        return Path.home() / ".local" / "share" / "EditorAresta"

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """No Linux/Flatpak, atualizações são gerenciadas pelo sistema operacional."""
        return ResultadoAtualizacao(status=StatusAtualizacao.NAO_APLICAVEL)

    def solicitar_instalacao_atualizacao(
        self, resultado: Optional[ResultadoAtualizacao] = None
    ) -> bool:
        """No Linux/Flatpak, o ciclo de vida e updates ocorrem fora do aplicativo."""
        return False

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone nativo prioritário para o Linux (.png)."""
        return "logo_app.png"

    def configurar_cofre_credenciais(self) -> None:
        """Garante a seleção do PortalKeyring ou SecretService/KWallet no Linux."""
        try:
            import keyring
            from keyring.backends import fail
        except Exception as exc:
            log.warning("Falha ao carregar keyring: %s", exc)
            return

        try:
            from editor.plataforma.linux.portal_keyring import PortalKeyring

            if PortalKeyring.is_available():
                backend_atual = keyring.get_keyring()
                if not isinstance(backend_atual, PortalKeyring):
                    caminho_cofre = self.obter_diretorio_dados_usuario() / "keyring.enc"
                    keyring.set_keyring(PortalKeyring(storage_path=caminho_cofre))
                    log.info("Cofre de credenciais configurado com PortalKeyring em: %s", caminho_cofre)
                return
            else:
                log.debug("PortalKeyring indisponível no ambiente atual.")
        except Exception as exc:
            log.warning("Falha ao inicializar PortalKeyring: %s", exc)

        try:
            backend_atual = keyring.get_keyring()
            if not isinstance(backend_atual, fail.Keyring):
                log.info("Usando backend de keyring padrão: %s", backend_atual)
                return
        except Exception:
            return

        try:
            from keyring.backends import SecretService

            keyring.set_keyring(SecretService.Keyring())  # type: ignore[no-untyped-call]
            log.info("Cofre de credenciais configurado com SecretService")
            return
        except Exception:
            pass

        try:
            from keyring.backends import kwallet

            keyring.set_keyring(kwallet.DBusKeyring())  # type: ignore[no-untyped-call]
            log.info("Cofre de credenciais configurado com KWallet")
            return
        except Exception:
            pass

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        """Em sistemas POSIX Linux, resolve e retorna o caminho absoluto canônico."""
        if not caminho:
            return ""
        return str(Path(caminho).resolve())
