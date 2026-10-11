# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração com o ambiente de desktop Linux (XDG e Flatpak).
Implementa o AdaptadorLinux conforme o protocolo AdaptadorPlataforma.
"""

import logging
import os
from pathlib import Path

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
        """
        Consulta o endpoint remoto version.json para verificar se há atualizações
        disponíveis ou obrigatórias para o canal Linux Flatpak.
        """
        import requests
        from packaging.version import parse as parse_version

        from editor.core.version import VERSION

        url_versao = "https://serving.arestaclimb.com/flatpak/version.json"
        try:
            resposta = requests.get(url_versao, timeout=3)
            if resposta.status_code != 200:
                log.warning(
                    "Falha ao consultar versão remota no Linux: HTTP %d", resposta.status_code
                )
                return ResultadoAtualizacao(status=StatusAtualizacao.ERRO_CHECAGEM)
            dados = resposta.json()
            versao_remota = str(dados.get("versao", "")).strip()
            obrigatoria = bool(dados.get("obrigatoria", False))
            if not versao_remota:
                return ResultadoAtualizacao(status=StatusAtualizacao.ERRO_CHECAGEM)

            if parse_version(versao_remota) > parse_version(VERSION):
                status = (
                    StatusAtualizacao.ATUALIZACAO_OBRIGATORIA
                    if obrigatoria
                    else StatusAtualizacao.ATUALIZACAO_DISPONIVEL
                )
                return ResultadoAtualizacao(
                    status=status,
                    versao_disponivel=versao_remota,
                    mensagem=dados.get("mensagem"),
                )
            return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)
        except Exception as exc:
            log.warning("Erro ao verificar atualizações no Linux: %s", exc)
            return ResultadoAtualizacao(status=StatusAtualizacao.ERRO_CHECAGEM)

    def solicitar_instalacao_atualizacao(
        self, resultado: ResultadoAtualizacao | None = None
    ) -> bool:
        """No Linux/Flatpak, o ciclo de vida e updates ocorrem fora do aplicativo."""
        return False

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone nativo prioritário para o Linux (.png)."""
        return "logo_app.png"

    def configurar_cofre_credenciais(self) -> bool:
        """Garante a seleção do PortalKeyring ou SecretService/KWallet no Linux, retornando True se operacional."""
        try:
            import keyring
            from keyring.backends import fail
        except Exception as exc:
            log.warning("Falha ao carregar keyring: %s", exc)
            return False

        try:
            from editor.plataforma.linux.portal_keyring import PortalKeyring

            if PortalKeyring.is_available():
                backend_atual = keyring.get_keyring()
                if not isinstance(backend_atual, PortalKeyring):
                    caminho_cofre = self.obter_diretorio_dados_usuario() / "keyring.enc"
                    backend_atual = PortalKeyring(storage_path=caminho_cofre)
                    keyring.set_keyring(backend_atual)
                    log.info(
                        "Cofre de credenciais configurado com PortalKeyring em: %s", caminho_cofre
                    )

                try:
                    backend_atual.get_master_key()
                    return True
                except Exception as exc:
                    log.warning(
                        "PortalKeyring presente, mas chaveiro trancado ou inacessível: %s", exc
                    )
                    return False
            else:
                log.debug("PortalKeyring indisponível no ambiente atual.")
        except Exception as exc:
            log.warning("Falha ao inicializar PortalKeyring: %s", exc)

        try:
            backend_atual = keyring.get_keyring()
            if not isinstance(backend_atual, fail.Keyring):
                log.info("Usando backend de keyring padrão: %s", backend_atual)
                return True
        except Exception:
            return False

        try:
            from keyring.backends import SecretService

            keyring.set_keyring(SecretService.Keyring())  # type: ignore[no-untyped-call]
            log.info("Cofre de credenciais configurado com SecretService")
            return True
        except Exception:
            pass

        try:
            from keyring.backends import kwallet

            keyring.set_keyring(kwallet.DBusKeyring())  # type: ignore[no-untyped-call]
            log.info("Cofre de credenciais configurado com KWallet")
            return True
        except Exception:
            pass

        return False

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        """Em sistemas POSIX Linux, resolve e retorna o caminho absoluto canônico."""
        if not caminho:
            return ""
        return str(Path(caminho).resolve())
